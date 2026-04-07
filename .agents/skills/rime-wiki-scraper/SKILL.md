---
name: rime-wiki-scraper
description: 从 Wiki 网站爬取数据生成 Rime 输入法词库。支持 Wikipedia、BWIKI 等多种 Wiki 网站，可扩展添加新的 Wiki 来源。
---

Rime Wiki Scraper 用于从 Wiki 网站爬取词条并生成 Rime 输入法词库。

**核心功能：**
- 从 Wikipedia、BWIKI 等 Wiki 网站爬取数据
- 支持多个 Wiki 源：zhwiki、enwiki、moegirl、rocom
- 特殊分类支持：rocom 站点支持 pets（精灵）、skills（技能）、items（道具）图鉴爬取
- 灵活的数据清洗和过滤规则
- 生成 Rime 格式词库 (.dict.yaml)

**项目结构：**
```
rime_wiki_scraper/
├── config/              # 配置模块
│   ├── __init__.py     # WikiConfig 基类
│   └── bwiki.py        # BWIKI 配置
├── sites/              # Wiki 站点实现
│   ├── __init__.py     # WikiSite 基类
│   ├── zhwiki.py       # 中文维基百科
│   ├── enwiki.py       # 英文维基百科
│   ├── moegirl.py      # 萌娘百科
│   └── rocom.py        # 洛克王国：世界（支持特殊分类）
├── cleaner/            # 数据清洗模块
├── generator/          # 词库生成模块
├── scraper/            # 爬取入口
└── __main__.py        # CLI 入口
```

## 快速命令

```bash
# 通用爬取命令
python -m rime_wiki_scraper scrape <wiki> "词条1" -o output.dict.yaml
python -m rime_wiki_scraper category <wiki> "分类名" --limit 50
python -m rime_wiki_scraper merge dict1.dict.yaml dict2.dict.yaml -o merged.dict.yaml
python -m rime_wiki_scraper merge dict1.dict.yaml dict2.dict.yaml -o merged.dict.yaml --site rocom  # 使用指定站点的许可证

# rocom 特殊分类（洛克王国：世界 Wiki）
python -m rime_wiki_scraper category rocom pets -o rocom_pets.dict.yaml    # 精灵图鉴
python -m rime_wiki_scraper category rocom skills -o rocom_skills.dict.yaml # 技能图鉴  
python -m rime_wiki_scraper category rocom items -o rocom_items.dict.yaml  # 道具图鉴
```

## 添加新 Wiki 网站

### 1. 配置 (config/bwiki.py)
```python
class MyWikiConfig(BWIKIConfig):
    def __init__(self):
        super().__init__("mywiki_path")
```

### 2. 网站实现 (sites/mywiki.py)
```python
from . import WikiSite
from config.bwiki import MyWikiConfig

class MyWikiSite(WikiSite):
    site_name = "mywiki"
    config_class = MyWikiConfig
    
    def get_summary(self, title: str) -> str:
        params = {"action": "query", "titles": title, 
                 "prop": "revisions", "rvprop": "content", "rvslots": "main"}
        data = self.request(params)
        content = data.get("query", {}).get("pages", {}).get("-1", {}).get("revisions", [])
        if content:
            return content[0].get("slots", {}).get("main", {}).get("*", "")[:100]
        return ""
    
    def get_links(self, title: str, limit: int = 10) -> list: ...
    def get_category_members(self, category: str, limit: int = 100) -> list: ...

from . import register_site
register_site(MyWikiSite)
```

### 3. 注册 (config/__init__.py)
```python
import sites.mywiki
```

### 4. 版权 (generator/__init__.py)
```python
"mywiki": ("我的Wiki", "https://wiki.xxx.com/版权", "CC BY-SA 3.0"),
```

## 特殊分类实现（以 rocom 为例）

对于某些 Wiki 站点（如洛克王国：世界），可能需要直接爬取图鉴页面而非使用 API 的 categorymembers。rocom 站点实现了特殊的 `pets`、`skills`、`items` 分类：

### 1. 重写分类相关方法 (sites/rocom.py)
```python
def get_category_members(self, category: str, limit: int = 100) -> List[str]:
    """获取分类成员，支持特殊图鉴分类"""
    atlas_categories = {
        'pets': {'url': '...精灵图鉴', 'type': 'pets'},
        'skills': {'url': '...技能图鉴', 'type': 'skills'},
        'items': {'url': '...道具图鉴', 'type': 'items'}
    }
    
    if category in atlas_categories:
        # 爬取图鉴页面 HTML
        return self.scrape_atlas_list(atlas_info['url'], atlas_info['type'])
    
    # 普通分类使用 Wiki API
    return super().get_category_members(category, limit)

def scrape_category(self, category: str, limit: int = 100, link_limit: int = 5):
    """爬取分类下的所有词条"""
    atlas_categories = ['pets', 'skills', 'items']
    if category in atlas_categories:
        members = self.get_category_members(category, limit)
        description = atlas_descriptions.get(category, '...')
        return [(name, description) for name in members]
    
    return super().scrape_category(category, limit, link_limit)
```

### 2. 实现图鉴爬取方法
```python
def scrape_atlas_list(self, url: str, atlas_type: str) -> List[str]:
    """爬取图鉴列表（支持精灵、技能、道具）"""
    # 处理 BWIKI 限流重试
    html = self._fetch_with_retry(url)
    soup = BeautifulSoup(html, 'html.parser')
    
    if atlas_type == 'pets':
        return self._extract_pets(soup, html)
    elif atlas_type == 'skills':
        return self._extract_skills(soup)
    elif atlas_type == 'items':
        return self._extract_items(soup)
```

### 3. 注意事项
- **避免重复访问**：直接返回图鉴列表，不进行额外的详情页爬取
- **许可证正确性**：确保使用站点正确的许可证（rocom 使用 CC BY-NC-SA 4.0）
- **HTML 结构适配**：针对不同图鉴页面的 DOM 结构编写提取逻辑

## 编写爬取脚本

```python
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import requests
from config.bwiki import MyWikiConfig

class MySpider:
    def __init__(self):
        self.config = MyWikiConfig()
        self.session = requests.Session()
        self.session.headers.update(self.config.headers)
    
    def request(self, params, retries=5):
        delay = 2
        for i in range(retries):
            resp = self.session.get(self.config.api_url, params=params, timeout=15)
            if resp.status_code == 567:  # BWIKI 限流
                if i < retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
                return {"query": {}}
            return resp.json()
    
    def get_all_pages(self):
        params = {"action": "query", "list": "allpages", "aplimit": 500}
        pages = []
        for _ in range(20):
            data = self.request(params)
            pages.extend([p["title"] for p in data.get("query", {}).get("allpages", [])])
            if "continue" not in data: break
            params["apcontinue"] = data["continue"]["apcontinue"]
            time.sleep(1)
        return pages

def main():
    spider = MySpider()
    pages = spider.get_all_pages()
    # 爬取和处理...
    from cleaner import create_default_pipeline
    from generator import create_generator
    # 生成词库...

if __name__ == "__main__":
    main()
```

## 关键要点

- **BWIKI API**: 用 `prop=revisions` 代替 `extracts`，处理 567 错误
- **内容解析**: Wikitext `|key=value` 格式提取字段
- **清洗规则**: DescriptionFilter 过滤括号描述
- **特殊分类**: 某些站点（如 rocom）需要直接爬取 HTML 图鉴页面而非使用 API
- **许可证正确性**: 不同站点使用不同许可证（维基百科 CC BY-SA 3.0，rocom CC BY-NC-SA 4.0）
- **模块化设计**: 每个 Wiki 站点独立实现，可轻松添加新站点