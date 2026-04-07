# Rime 词库爬虫项目

从 Wiki 网站爬取词条并生成 Rime 输入法词库。

## 项目结构

```
rime_wiki_scraper/
├── config/          # Wiki 网站配置
│   ├── __init__.py  # WikiConfig 基类
│   └── bwiki.py     # BWIKI 站点配置
├── sites/           # Wiki 站点实现
│   ├── __init__.py  # WikiSite 基类
│   ├── zhwiki.py    # 中文维基百科
│   ├── enwiki.py    # 英文维基百科  
│   ├── moegirl.py   # 萌娘百科
│   └── rocom.py     # 洛克王国：世界 Wiki
├── cleaner/         # 清洗模块
│   └── __init__.py  # 数据清洗流水线
├── generator/       # 生成模块
│   └── __init__.py  # 支持 Rime/TXT/JSON 格式
├── scraper/         # 爬取入口
│   └── __init__.py  # WikiScraper 基类
└── __main__.py      # CLI 入口
```

## 支持的 Wiki

- `zhwiki` - 中文维基百科
- `enwiki` - 英文维基百科
- `moegirl` - 萌娘百科
- `rocom` - 洛克王国：世界 Wiki（支持特殊图鉴分类）

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
python -m rime_wiki_scraper --help
```

### 示例

```bash
# 爬取中文维基词条
python -m rime_wiki_scraper scrape zhwiki "Python" "Java" -o programming.dict.yaml

# 爬取英文维基
python -m rime_wiki_scraper scrape enwiki "Python" "JavaScript" -o en.dict.yaml

# 从分类页面爬取
python -m rime_wiki_scraper category zhwiki "计算机科学" -o cs.dict.yaml --limit 50

# 爬取洛克王国：世界 Wiki 图鉴
python -m rime_wiki_scraper category rocom pets -o output/rocom_pets.dict.yaml    # 精灵图鉴
python -m rime_wiki_scraper category rocom skills -o output/rocom_skills.dict.yaml # 技能图鉴
python -m rime_wiki_scraper category rocom items -o output/rocom_items.dict.yaml  # 道具图鉴

# 一键生成洛奇王国混合字典（带正确许可证）
python -m rime_wiki_scraper category rocom pets -o output/rocom_pets.dict.yaml && \
python -m rime_wiki_scraper category rocom skills -o output/rocom_skills.dict.yaml && \
python -m rime_wiki_scraper category rocom items -o output/rocom_items.dict.yaml && \
python -m rime_wiki_scraper merge output/rocom_pets.dict.yaml output/rocom_skills.dict.yaml output/rocom_items.dict.yaml -o output/rocom_mixed.dict.yaml --name "rocom_mixed" --site rocom

# 输出为纯文本
python -m rime_wiki_scraper scrape zhwiki "Python" -o python.txt --format txt

# 合并多个词库（通用许可证）
python -m rime_wiki_scraper merge rocom_pets.dict.yaml rocom_skills.dict.yaml rocom_items.dict.yaml -o rocom_all.dict.yaml
# 合并多个词库并指定站点许可证
python -m rime_wiki_scraper merge rocom_pets.dict.yaml rocom_skills.dict.yaml rocom_items.dict.yaml -o rocom_all_with_license.dict.yaml --site rocom
```

### 自定义清洗

```python
from cleaner import Pipeline, TextCleaner, LengthFilter, DuplicateCleaner

pipeline = (
    Pipeline()
    .add(TextCleaner())
    .add(LengthFilter(min_title_len=2, max_title_len=20))
    .add(DuplicateCleaner())
)

cleaned = pipeline.process(data)
```

### 自定义爬取器

```python
from scraper import WikiScraper
from config import WikiConfig

class MyWikiScraper(WikiScraper):
    def get_article_summary(self, title: str) -> str:
        # 自定义实现
        pass
    
    def get_article_links(self, title: str, limit: int = 10) -> list:
        # 自定义实现
        pass
    
    def get_category_members(self, category: str, limit: int = 100) -> list:
        # 自定义实现
        pass

# 使用自定义爬取器
scraper = MyWikiScraper(MyWikiConfig())
```

## 输出格式

Rime 词库：
```yaml
---
name: wiki_dict
version: "1.0"
sort: original
---

词条	拼音	权重
```

## 内容许可证说明

爬取的词条内容遵循各自 Wiki 站点的许可协议：

- **中文维基百科 (zhwiki)**: [CC BY-SA 4.0.GFDL](https://zh.wikipedia.org/wiki/Wikipedia:%E8%91%97%E4%BD%9C%E6%9D%83%E4%BF%A1%E6%81%AF)
- **英文维基百科 (enwiki)**: [CC BY-SA 4.0.GFDL](https://en.wikipedia.org/wiki/Wikipedia:Copyrights)  
- **萌娘百科 (moegirl)**: [CC BY-NC-SA 3.0 CN](https://zh.moegirl.org.cn/%E8%90%8C%E5%A8%98%E7%99%BE%E7%A7%91:%E8%91%97%E4%BD%9C%E6%9D%83%E4%BF%A1%E6%81%AF)
- **洛克王国：世界 Wiki (rocom)**: [CC BY-NC-SA 4.0](https://wiki.biligame.com/rocom/%E6%B4%9B%E5%85%8B%E7%8E%8B%E5%9B%BD)

生成的词库文件头部包含相应的许可证信息。合并多个来源的词库时，许可证行显示为"多种许可证，见原网站许可协议"。如果合并的词库全部来自同一站点，可以使用 `--site` 参数指定站点名称（如 `--site rocom`），这样会使用该站点的许可证信息。

## 项目许可证

本项目代码采用 MIT 许可证。