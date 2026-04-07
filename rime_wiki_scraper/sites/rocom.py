"""洛克王国：世界 Wiki"""
from typing import List
import re
import requests
import time
from bs4 import BeautifulSoup
from . import WikiSite
from config.bwiki import RocomConfig


class RocomSite(WikiSite):
    """洛克王国：世界 Wiki"""
    
    site_name = "rocom"
    config_class = RocomConfig
    
    def get_summary(self, title: str) -> str:
        """获取词条摘要（使用 revisions）"""
        params = {
            "action": "query",
            "format": "json",
            "titles": self.config.normalize_title(title),
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main"
        }
        data = self.request(params)
        pages = data.get("query", {}).get("pages", {})
        
        for page_id, page in pages.items():
            if page_id != "-1":
                revisions = page.get("revisions", [])
                if revisions:
                    content = revisions[0].get("slots", {}).get("main", {}).get("*", "")
                    # 提取描述信息
                    if content:
                        # 尝试从 {{精灵信息}} 模板中提取描述
                        desc_match = re.search(r'\|精灵描述=(.+?)(?:\n|\||})', content)
                        if desc_match:
                            return desc_match.group(1).strip()[:100]
        return ""
    
    def get_links(self, title: str, limit: int = 10) -> List[str]:
        """获取词条链接"""
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
                        if self.config.is_valid_title(link_title):
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
        """获取分类成员
        
        支持特殊分类：pets, skills, items 返回对应的图鉴列表。
        其他分类使用Wiki API获取。
        """
        # 特殊图鉴分类处理
        atlas_categories = {
            'pets': {
                'url': 'https://wiki.biligame.com/rocom/%E7%B2%BE%E7%81%B5%E5%9B%BE%E9%89%B4',
                'type': 'pets'
            },
            'skills': {
                'url': 'https://wiki.biligame.com/rocom/%E6%8A%80%E8%83%BD%E5%9B%BE%E9%89%B4',
                'type': 'skills'
            },
            'items': {
                'url': 'https://wiki.biligame.com/rocom/%E9%81%93%E5%85%B7%E5%9B%BE%E9%89%B4',
                'type': 'items'
            }
        }
        
        if category in atlas_categories:
            atlas_info = atlas_categories[category]
            print(f"爬取 {category} 图鉴: {atlas_info['url']}")
            items = self.scrape_atlas_list(atlas_info['url'], atlas_type=atlas_info['type'])
            return items[:limit] if limit else items
        
        # 普通Wiki分类处理
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
    
    def scrape_pet_list(self, url: str = None) -> List[str]:
        """爬取精灵图鉴列表（兼容旧方法）"""
        return self.scrape_atlas_list(url, atlas_type='pets')
    
    def scrape_atlas_list(self, url: str = None, atlas_type: str = 'auto') -> List[str]:
        """爬取图鉴列表（支持精灵、技能、道具）
        
        Args:
            url: 图鉴页面URL
            atlas_type: 图鉴类型 ('pets', 'skills', 'items', 'auto')
        """
        if url is None:
            url = "https://wiki.biligame.com/rocom/%E7%B2%BE%E7%81%B5%E5%9B%BE%E9%89%B4"
        
        # 自动检测图鉴类型
        if atlas_type == 'auto':
            if '技能图鉴' in url:
                atlas_type = 'skills'
            elif '道具图鉴' in url:
                atlas_type = 'items'
            elif '精灵图鉴' in url:
                atlas_type = 'pets'
            else:
                # 根据页面内容检测
                atlas_type = 'auto_detect'
        
        # 使用配置的session，带重试机制
        retries = 5
        delay = 2
        html = None
        
        for i in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                if response.status_code == 567:
                    if i < retries - 1:
                        time.sleep(delay)
                        delay *= 2
                        continue
                response.raise_for_status()
                response.encoding = 'utf-8'
                html = response.text
                break
            except Exception as e:
                if i < retries - 1:
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise e
        
        if html is None:
            raise Exception(f"Failed to fetch {url} after {retries} retries")
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        if atlas_type == 'auto_detect':
            # 根据页面结构自动检测
            skill_containers = soup.find_all('div', class_='rocom_skill_bg')
            prop_containers = soup.find_all('div', class_='rocom_prop_img')
            
            if skill_containers:
                atlas_type = 'skills'
                print(f"自动检测为技能图鉴，找到 {len(skill_containers)} 个技能容器")
            elif prop_containers:
                # 检查是否有NO.编号来判断是精灵还是道具
                has_no = any(container.find('span', string=re.compile(r'NO\.\d+')) 
                           for container in prop_containers[:5])
                if has_no:
                    atlas_type = 'pets'
                    print(f"自动检测为精灵图鉴，找到 {len(prop_containers)} 个精灵容器")
                else:
                    atlas_type = 'items'
                    print(f"自动检测为道具图鉴，找到 {len(prop_containers)} 个道具容器")
            else:
                atlas_type = 'skills'  # 默认回退到技能
        
        print(f"爬取 {atlas_type} 图鉴: {url}")
        
        if atlas_type == 'pets':
            items = self._extract_pets(soup, html)
        elif atlas_type == 'skills':
            items = self._extract_skills(soup)
        elif atlas_type == 'items':
            items = self._extract_items(soup)
        
        # 去重
        unique_items = []
        seen = set()
        for item in items:
            if item not in seen:
                seen.add(item)
                unique_items.append(item)
        
        print(f"提取到 {len(items)} 个项目，去重后 {len(unique_items)} 个")
        return unique_items
    
    def _extract_pets(self, soup: BeautifulSoup, html: str) -> List[str]:
        """提取精灵"""
        pets = []
        
        # 查找所有精灵容器
        pet_containers = soup.find_all('div', class_='rocom_prop_img')
        
        if not pet_containers:
            pet_containers = soup.find_all('div', class_=re.compile(r'rocom.*prop.*img'))
        
        print(f"找到 {len(pet_containers)} 个精灵容器")
        
        for container in pet_containers:
            try:
                # 提取编号
                no_elem = container.find('span', string=re.compile(r'NO\.\d+'))
                if not no_elem:
                    block1 = container.find('p', class_='block_1')
                    if block1:
                        no_elem = block1.find('span', string=re.compile(r'NO\.\d+'))
                
                if not no_elem:
                    continue
                
                # 提取名称
                name_elem = container.find('span', class_='font-mainfeiziti')
                if not name_elem:
                    block2 = container.find('p', class_='block_2')
                    if block2:
                        name_elem = block2.find('span')
                
                if not name_elem:
                    continue
                
                pet_name = name_elem.get_text(strip=True)
                if pet_name:
                    pets.append(pet_name)
                    
            except Exception as e:
                print(f"解析精灵容器时出错: {e}")
                continue
        
        # 如果第一种方法提取不到，尝试备选方法
        if len(pets) < 10:
            print("第一种方法提取到的精灵较少，尝试备选方法...")
            pattern = r'<span[^>]*>NO\.\d+</span>.*?<span[^>]*class="[^"]*font-mainfeiziti[^"]*"[^>]*>([^<]+)</span>'
            matches = re.findall(pattern, html, re.DOTALL)
            for pet_name in matches:
                pet_name = pet_name.strip()
                if pet_name:
                    pets.append(pet_name)
            
            pattern2 = r'NO\.\d+[^<]*</span>[^<]*<span[^>]*>([^<]+)</span>'
            matches2 = re.findall(pattern2, html, re.DOTALL)
            for pet_name in matches2:
                pet_name = pet_name.strip()
                if pet_name:
                    pets.append(pet_name)
        
        return pets
    
    def _extract_skills(self, soup: BeautifulSoup) -> List[str]:
        """提取技能"""
        skills = []
        
        # 查找技能容器
        skill_containers = soup.find_all('div', class_='rocom_skill_bg')
        
        if not skill_containers:
            # 备选：直接查找包含技能名称的结构
            skill_names = soup.find_all('p', class_='rocom_skill_name')
            if skill_names:
                for name_elem in skill_names:
                    span = name_elem.find('span', class_='font-mainfeiziti')
                    if span:
                        skill_name = span.get_text(strip=True)
                        if skill_name:
                            skills.append(skill_name)
                return skills
        
        print(f"找到 {len(skill_containers)} 个技能容器")
        
        for container in skill_containers:
            try:
                # 在容器中查找技能名称
                name_elem = container.find('span', class_='font-mainfeiziti')
                if not name_elem:
                    # 尝试在rocom_skill_name中查找
                    skill_name_elem = container.find('p', class_='rocom_skill_name')
                    if skill_name_elem:
                        name_elem = skill_name_elem.find('span', class_='font-mainfeiziti')
                
                if not name_elem:
                    continue
                
                skill_name = name_elem.get_text(strip=True)
                if skill_name:
                    skills.append(skill_name)
                    
            except Exception as e:
                print(f"解析技能容器时出错: {e}")
                continue
        
        # 如果还是没找到，直接查找所有font-mainfeiziti（可能包含非技能内容）
        if len(skills) < 10:
            print("通过容器提取的技能较少，尝试直接查找...")
            all_spans = soup.find_all('span', class_='font-mainfeiziti')
            for span in all_spans:
                skill_name = span.get_text(strip=True)
                if skill_name and len(skill_name) >= 2 and len(skill_name) <= 20:
                    # 简单的启发式过滤：排除明显非技能的内容
                    # 排除纯数字、单个字符、包含特殊符号等
                    if skill_name.isdigit():
                        continue
                    if len(skill_name) == 1:
                        continue
                    if '·' in skill_name or '·' in skill_name:
                        continue
                    if 'NO.' in skill_name or 'No.' in skill_name:
                        continue
                    skills.append(skill_name)
        
        return skills
    
    def _extract_items(self, soup: BeautifulSoup) -> List[str]:
        """提取道具"""
        items = []
        
        # 查找道具容器
        item_containers = soup.find_all('div', class_='rocom_prop_img')
        
        if not item_containers:
            item_containers = soup.find_all('div', class_=re.compile(r'rocom.*prop.*img'))
        
        print(f"找到 {len(item_containers)} 个道具容器")
        
        for container in item_containers:
            try:
                # 提取名称
                name_elem = container.find('span', class_='font-mainfeiziti')
                if not name_elem:
                    # 尝试在链接中查找
                    link = container.find('a')
                    if link and link.get('title'):
                        item_name = link.get('title')
                        if item_name:
                            items.append(item_name)
                            continue
                
                if not name_elem:
                    continue
                
                item_name = name_elem.get_text(strip=True)
                if item_name:
                    items.append(item_name)
                    
            except Exception as e:
                print(f"解析道具容器时出错: {e}")
                continue
        
        return items
    
    def scrape_category(self, category: str, limit: int = 100, link_limit: int = 5):
        """爬取分类下的所有词条
        
        对于特殊图鉴分类 (pets, skills, items) 直接返回带描述的词条。
        其他分类使用父类方法。
        """
        # 特殊图鉴分类处理
        atlas_categories = ['pets', 'skills', 'items']
        atlas_descriptions = {
            'pets': '洛克王国精灵，可在游戏中捕捉和培养。',
            'skills': '洛克王国技能，精灵可以学习和使用。',
            'items': '洛克王国道具，可在游戏中使用或获取。'
        }
        
        if category in atlas_categories:
            print(f"正在爬取 {category} 图鉴...")
            members = self.get_category_members(category, limit)
            
            # 直接返回带描述的词条对，不进行额外的链接爬取
            description = atlas_descriptions.get(category, '洛克王国游戏内容。')
            return [(name, description) for name in members]
        
        # 普通分类使用父类方法
        return super().scrape_category(category, limit, link_limit)


from . import register_site
register_site(RocomSite)