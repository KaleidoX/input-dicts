"""Bilibili Wiki (BWIKI) 配置"""
from config import WikiConfig


class BWIKIConfig(WikiConfig):
    """BWIKI 通用配置（需指定 wiki 路径）"""
    
    def __init__(self, wiki_path: str = "rocom"):
        self._wiki_path = wiki_path
    
    @property
    def api_url(self) -> str:
        return f"https://wiki.biligame.com/{self._wiki_path}/api.php"
    
    @property
    def base_url(self) -> str:
        return f"https://wiki.biligame.com/{self._wiki_path}/"
    
    @property
    def language(self) -> str:
        return "zh"


class RocomConfig(BWIKIConfig):
    """洛克王国：世界配置"""
    
    def __init__(self):
        super().__init__("rocom")


__all__ = ["BWIKIConfig", "RocomConfig"]