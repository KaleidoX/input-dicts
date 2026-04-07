# Rime Wiki Scraper 项目开发指南

## 项目结构

```
rime_wiki_scraper/
├── config/              # 配置模块
│   ├── __init__.py      # WikiConfig 基类 + 内置配置
│   └── bwiki.py         # BWIKI 配置
├── sites/               # Wiki 网站实现（内聚单元）
│   ├── __init__.py      # WikiSite 基类
│   ├── zhwiki.py        # 中文维基百科
│   ├── enwiki.py        # 英文维基百科
│   ├── moegirl.py       # 萌娘百科
│   ├── rocokingdom.py  # 老版洛克王国
│   ├── rocom.py        # 洛克王国：世界
│   └── ...
├── scraper/             # 爬取入口
├── cleaner/             # 清洗模块
├── generator/           # 生成模块
├── crawl_rocom.py      # 专用爬取脚本示例
└── __main__.py         # CLI 入口
```

## 快速开始

```bash
# 爬取指定词条
python -m rime_wiki_scraper scrape <wiki_type> "词条1" "词条2" -o output.dict.yaml

# 从分类页面爬取
python -m rime_wiki_scraper category <wiki_type> "分类名" --limit 50

# 合并词库
python -m rime_wiki_scraper merge dict1.dict.yaml dict2.dict.yaml -o merged.dict.yaml
```

## 添加新的 Wiki 网站

### 步骤 1: 创建配置文件

在 `config/bwiki.py` 中添加配置类：

```python
class MyWikiConfig(BWIKIConfig):
    """我的 Wiki 配置"""
    
    def __init__(self):
        super().__init__("mywiki")  # wiki 路径
```

### 步骤 2: 创建网站实现

在 `sites/mywiki.py` 中创建：

```python
"""我的 Wiki 网站"""
from typing import List
from . import WikiSite
from config.bwiki import MyWikiConfig


class MyWikiSite(WikiSite):
    """我的 Wiki 网站"""
    
    site_name = "mywiki"  # 必须唯一
    config_class = MyWikiConfig
    
    def get_summary(self, title: str) -> str:
        """获取词条摘要"""
        # BWIKI 使用 revisions 获取内容
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main"
        }
        data = self.request(params)
        pages = data.get("query", {}).get("pages", {})
        
        if isinstance(pages, dict):
            for page_id, page in pages.items():
                if page_id != "-1":
                    revisions = page.get("revisions", [])
                    if revisions:
                        content = revisions[0].get("slots", {}).get("main", {}).get("*", "")
                        return self._parse_content(content)
        return ""
    
    def _parse_content(self, content: str) -> str:
        """解析内容获取摘要"""
        # 解析模板字段
        lines = content.split("\n")
        for line in lines:
            if line.startswith("|简介=") or line.startswith("|description="):
                return line.split("=", 1)[1].strip()
        return content[:100]
    
    def get_links(self, title: str, limit: int = 10) -> List[str]:
        """获取词条链接"""
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "links",
            "pllimit": "max"
        }
        
        links = []
        while len(links) < limit:
            data = self.request(params)
            pages = data.get("query", {}).get("pages", {})
            
            if isinstance(pages, dict):
                for page_id, page in pages.items():
                    for link in page.get("links", []):
                        link_title = link["title"]
                        if (not link_title.startswith("Template:")
                            and not link_title.startswith("BWiki:")
                            and self.config.is_valid_title(link_title)):
                            if len(links) >= limit:
                                break
                            links.append(link_title)
            
            if "continue" in data:
                params.update(data["continue"])
            else:
                break
        
        return links[:limit]
    
    def get_category_members(self, category: str, limit: int = 100) -> List[str]:
        """获取分类成员"""
        params = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": self.config.get_category_title(category),
            "cmlimit": min(limit, 500)
        }
        
        members = []
        while len(members) < limit:
            data = self.request(params)
            
            for item in data.get("query", {}).get("categorymembers", []):
                title = item["title"]
                if self.config.is_valid_title(title):
                    members.append(title)
            
            if "continue" in data:
                params["cmcontinue"] = data["continue"]["cmcontinue"]
            else:
                break
        
        return members[:limit]


from . import register_site
register_site(MyWikiSite)
```

### 步骤 3: 注册网站

在 `config/__init__.py` 的 `register_all_sites()` 函数中添加：

```python
def register_all_sites():
    import sites.zhwiki
    import sites.enwiki
    import sites.moegirl
    import sites.rocokingdom
    import sites.rocom
    import sites.mywiki  # 添加这一行
    from config import bwiki
```

### 步骤 4: 添加版权声明

在 `generator/__init__.py` 的 `SITE_LICENSE` 字典中添加：

```python
SITE_LICENSE = {
    # ... 已有配置
    "mywiki": ("我的 Wiki", "https://wiki.biligame.com/mywiki/版权声明"),
}
```

### 使用新网站

```bash
# 爬取词条
python -m rime_wiki_scraper scrape mywiki "词条名" -o output.dict.yaml

# 爬取分类
python -m rime_wiki_scraper category mywiki "分类名" --limit 50
```

## 编写专用爬取脚本

参考 `crawl_rocom.py` 的结构：

```python
"""专用爬取脚本模板"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import requests
from config.bwiki import MyWikiConfig


class MySpider:
    """专用爬虫"""
    
    def __init__(self):
        self.config = MyWikiConfig()
        self.session = requests.Session()
        self.session.headers.update(self.config.headers)
    
    def request(self, params: dict, retries: int = 5) -> dict:
        """带重试的请求（处理 567 错误）"""
        delay = 2
        for i in range(retries):
            try:
                response = self.session.get(
                    self.config.api_url,
                    params=params,
                    timeout=15
                )
                if response.status_code == 567:
                    if i < retries - 1:
                        time.sleep(delay)
                        delay *= 2
                        continue
                    return {"query": {"pages": {}}}
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if i < retries - 1:
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise e
        return {"query": {"pages": {}}}
    
    def get_all_pages(self) -> list:
        """获取所有页面"""
        params = {
            "action": "query",
            "format": "json",
            "list": "allpages",
            "aplimit": 500
        }
        
        all_pages = []
        for i in range(20):
            data = self.request(params)
            pages = data.get("query", {}).get("allpages", [])
            all_pages.extend([p["title"] for p in pages])
            
            if "continue" not in data:
                break
            params["apcontinue"] = data["continue"]["apcontinue"]
            time.sleep(1)
        
        return all_pages
    
    def filter_items(self, pages: list) -> list:
        """过滤目标条目"""
        exclude_keywords = ["任务", "攻略", "模板", "帮助"]
        
        items = []
        for title in pages:
            if len(title) < 2 or len(title) > 10:
                continue
            if any(kw in title for kw in exclude_keywords):
                continue
            items.append(title)
        
        return items
    
    def crawl_item(self, title: str) -> str:
        """爬取单个条目"""
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main"
        }
        
        data = self.request(params)
        pages = data.get("query", {}).get("pages", {})
        
        if isinstance(pages, dict):
            for page_id, page in pages.items():
                if page_id != "-1":
                    revisions = page.get("revisions", [])
                    if revisions:
                        content = revisions[0].get("slots", {}).get("main", {}).get("*", "")
                        # 解析内容...
                        return content[:100]
        return ""


def main():
    spider = MySpider()
    
    # 获取所有页面
    all_pages = spider.get_all_pages()
    
    # 过滤目标
    items = spider.filter_items(all_pages)
    
    # 爬取数据
    results = []
    for i, name in enumerate(items):
        print(f"进度: {i+1}/{len(items)} - {name}")
        summary = spider.crawl_item(name)
        if summary:
            results.append((name, summary))
        time.sleep(1)
    
    # 生成词库
    from cleaner import create_default_pipeline
    from generator import create_generator
    
    pipeline = create_default_pipeline()
    cleaned = pipeline.process(results)
    
    generator = create_generator("rime", site_name="mywiki")
    generator.generate(cleaned, "output/mywiki.dict.yaml")
    print(f"已生成词库: output/mywiki.dict.yaml")


if __name__ == "__main__":
    main()
```

## 关键点总结

1. **BWIKI API 特点**：
   - 不支持 `extracts` 属性，需使用 `revisions` 获取内容
   - 可能返回 567 错误，需要重试机制
   - 需要处理分页（`continue` 参数）

2. **内容解析**：
   - Wikitext 格式需要解析 `{{模板}}` 和 `|字段=值` 格式
   - 可以提取特定字段作为摘要

3. **错误处理**：
   - 567 错误需要指数退避重试
   - 单个词条失败不影响整体流程