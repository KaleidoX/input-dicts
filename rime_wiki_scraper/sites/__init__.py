"""Wiki 网站基类"""
import time
import requests
from abc import ABC, abstractmethod
from typing import List, Tuple, Type
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import WikiConfig, WikiSiteMeta


class WikiSite(ABC):
    """Wiki 网站基类"""
    
    site_name: str = ""
    config_class: Type[WikiConfig] = WikiConfig
    
    def __init__(self, config: WikiConfig = None):
        self.config = config or self.config_class()
        self.session = requests.Session()
        self.session.headers.update(self.config.headers)
    
    def request(self, params: dict, retries: int = None) -> dict:
        """发送请求"""
        retries = retries or 5
        delay = 2
        
        for i in range(retries):
            try:
                response = self.session.get(
                    self.config.api_url,
                    params=params,
                    timeout=self.config.timeout
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
    
    @abstractmethod
    def get_summary(self, title: str) -> str:
        """获取词条摘要"""
        pass
    
    @abstractmethod
    def get_links(self, title: str, limit: int = 10) -> List[str]:
        """获取词条链接"""
        pass
    
    @abstractmethod
    def get_category_members(self, category: str, limit: int = 100) -> List[str]:
        """获取分类成员"""
        pass
    
    def scrape(self, title: str, link_limit: int = 10) -> List[Tuple[str, str]]:
        """爬取词条及其关联词条"""
        words = []
        
        extract = self.get_summary(title)
        if extract:
            words.append((title, extract[:100] if len(extract) > 100 else extract))
        
        links = self.get_links(title, link_limit)
        for link in links:
            link_extract = self.get_summary(link)
            if link_extract:
                words.append((link, link_extract[:100] if len(link_extract) > 100 else link_extract))
        
        return words
    
    def scrape_category(self, category: str, limit: int = 100, link_limit: int = 5) -> List[Tuple[str, str]]:
        """爬取分类下的所有词条"""
        all_words = []
        
        members = self.get_category_members(category, limit)
        
        for i, title in enumerate(members):
            print(f"进度: {i+1}/{len(members)} - {title}")
            try:
                words = self.scrape(title, link_limit)
                all_words.extend(words)
            except Exception as e:
                print(f"爬取 {title} 失败: {e}")
        
        return all_words


def register_site(site_cls: Type[WikiSite]):
    """注册网站类"""
    if site_cls.site_name:
        WikiSiteMeta.register(site_cls.site_name, site_cls)


__all__ = ["WikiSite", "register_site"]