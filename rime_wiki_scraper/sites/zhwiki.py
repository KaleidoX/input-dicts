"""中文维基百科"""
from typing import List
from . import WikiSite
from config import ChineseWikiConfig


class ZhWikipediaSite(WikiSite):
    """中文维基百科"""
    
    site_name = "zhwiki"
    config_class = ChineseWikiConfig
    
    def get_summary(self, title: str) -> str:
        params = {
            "action": "query",
            "format": "json",
            "titles": self.config.normalize_title(title),
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "formatversion": "2"
        }
        data = self.request(params)
        pages = data.get("query", {}).get("pages", {})
        
        if isinstance(pages, list) and pages:
            return pages[0].get("extract", "")
        
        if isinstance(pages, dict):
            for page_id, page in pages.items():
                if page_id != "-1":
                    return page.get("extract", "")
        return ""
    
    def get_links(self, title: str, limit: int = 10) -> List[str]:
        params = {
            "action": "query",
            "format": "json",
            "titles": self.config.normalize_title(title),
            "prop": "links",
            "pllimit": "max"
        }
        
        links = []
        while len(links) < limit:
            data = self.request(params)
            pages = data.get("query", {}).get("pages", {})
            
            if isinstance(pages, list):
                break
            
            if isinstance(pages, dict):
                for page_id, page in pages.items():
                    for link in page.get("links", []):
                        link_title = link["title"]
                        if (not link_title.startswith("Wikipedia:") 
                            and not link_title.startswith("Template:")
                            and self.config.is_valid_title(link_title)):
                            if len(links) >= limit:
                                break
                            links.append(link_title)
                    if len(links) >= limit:
                        break
            
            if "continue" in data:
                params.update(data["continue"])
            else:
                break
        
        return links[:limit]
    
    def get_category_members(self, category: str, limit: int = 100) -> List[str]:
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
                if len(members) >= limit:
                    break
            
            if "continue" in data:
                params["cmcontinue"] = data["continue"]["cmcontinue"]
            else:
                break
        
        return members[:limit]


from . import register_site
register_site(ZhWikipediaSite)