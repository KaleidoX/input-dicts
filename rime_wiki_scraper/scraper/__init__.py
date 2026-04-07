"""爬取模块"""
from typing import List, Tuple
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_scraper(site_name: str):
    """创建爬取器"""
    import sites as wiki_sites
    import config
    
    site_cls = config.WikiSiteMeta.get(site_name)
    return site_cls()


__all__ = ["create_scraper"]