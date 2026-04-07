"""配置基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Type


class WikiConfig(ABC):
    """Wiki 网站配置基类"""
    
    @property
    @abstractmethod
    def api_url(self) -> str:
        """API 接口地址"""
        pass
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """基础 URL"""
        pass
    
    @property
    @abstractmethod
    def language(self) -> str:
        """语言代码"""
        pass
    
    @property
    def headers(self) -> Dict[str, str]:
        """请求头"""
        return {
            "User-Agent": "RimeWikiScraper/1.0 (github.com/input-dicts)"
        }
    
    @property
    def timeout(self) -> int:
        """请求超时时间（秒）"""
        return 30
    
    @property
    def retries(self) -> int:
        """重试次数"""
        return 3
    
    def get_category_title(self, category: str) -> str:
        """获取分类页面标题"""
        return f"Category:{category}"
    
    def normalize_title(self, title: str) -> str:
        """标准化标题"""
        return title.strip()
    
    def is_valid_title(self, title: str) -> bool:
        """检查标题是否有效"""
        return bool(title and not title.startswith("Category:"))


class WikiSiteMeta(type):
    """Wiki 网站元类，用于注册网站类"""
    
    _registry: Dict[str, Type] = {}
    
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        if hasattr(cls, 'site_name') and cls.site_name:
            WikiSiteMeta._registry[cls.site_name] = cls
        return cls
    
    @classmethod
    def get(mcs, site_name: str) -> Type:
        """获取网站类"""
        if site_name not in mcs._registry:
            raise ValueError(f"Unknown wiki site: {site_name}. Available: {list(mcs._registry.keys())}")
        return mcs._registry[site_name]
    
    @classmethod
    def list(mcs) -> Dict[str, Type]:
        """列出所有注册的网站"""
        return mcs._registry.copy()
    
    @classmethod
    def register(mcs, site_name: str, site_cls: Type):
        """手动注册网站类"""
        mcs._registry[site_name] = site_cls


def get_wiki_site(site_name: str, config: WikiConfig = None):
    """获取 Wiki 网站实例"""
    from sites import WikiSite
    site_cls = WikiSiteMeta.get(site_name)
    return site_cls(config or site_cls.config_class())


class ChineseWikiConfig(WikiConfig):
    """中文维基配置"""
    
    @property
    def api_url(self) -> str:
        return "https://zh.wikipedia.org/w/api.php"
    
    @property
    def base_url(self) -> str:
        return "https://zh.wikipedia.org/wiki/"
    
    @property
    def language(self) -> str:
        return "zh"


class EnglishWikiConfig(WikiConfig):
    """英文维基配置"""
    
    @property
    def api_url(self) -> str:
        return "https://en.wikipedia.org/w/api.php"
    
    @property
    def base_url(self) -> str:
        return "https://en.wikipedia.org/wiki/"
    
    @property
    def language(self) -> str:
        return "en"


class MoegirlConfig(WikiConfig):
    """萌娘百科配置"""
    
    @property
    def api_url(self) -> str:
        return "https://zh.moegirl.org.cn/api.php"
    
    @property
    def base_url(self) -> str:
        return "https://zh.moegirl.org.cn/"
    
    @property
    def language(self) -> str:
        return "zh"


def register_all_sites():
    """注册所有内置网站"""
    import sites.zhwiki
    import sites.enwiki
    import sites.moegirl
    import sites.rocom
    from config import bwiki


__all__ = [
    "WikiConfig", "WikiSiteMeta", "get_wiki_site", 
    "ChineseWikiConfig", "EnglishWikiConfig", "MoegirlConfig",
    "register_all_sites"
]