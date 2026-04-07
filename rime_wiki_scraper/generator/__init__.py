"""词库生成模块"""
import yaml
import os
from typing import List, Tuple, Optional, Dict
from abc import ABC, abstractmethod
from pathlib import Path

try:
    from pypinyin import lazy_pinyin
except ImportError:
    lazy_pinyin = None


class Generator(ABC):
    """词库生成基类"""
    
    @abstractmethod
    def generate(self, data: List[Tuple[str, str]], output: str) -> None:
        """生成词库"""
        pass


class RimeDictGenerator(Generator):
    """Rime 词库生成器"""
    
    SITE_LICENSE = {
        "zhwiki": ("维基百科", "https://zh.wikipedia.org/wiki/Wikipedia:%E8%91%97%E4%BD%9C%E6%9D%83%E4%BF%A1%E6%81%AF", "CC BY-SA 4.0.GFDL"),
        "enwiki": ("Wikipedia", "https://en.wikipedia.org/wiki/Wikipedia:Copyrights", "CC BY-SA 4.0.GFDL"),
        "moegirl": ("萌娘百科", "https://zh.moegirl.org.cn/%E8%90%8C%E5%A8%98%E7%99%BE%E7%A7%91:%E8%91%97%E4%BD%9C%E6%9D%83%E4%BF%A1%E6%81%AF", "CC BY-NC-SA 3.0 CN"),
        "rocom": ("洛克王国：世界 Wiki", "https://wiki.biligame.com/rocom/%E6%B4%9B%E5%85%8B%E7%8E%8B%E5%9B%BD", "CC BY-NC-SA 4.0"),
    }
    
    def __init__(self, name: str = None, version: str = "1.0",
                 sort: str = "original", weight: int = 1,
                 pinyin_func=None, site_name: str = None,
                 include_license: bool = True):
        self.version = version
        self.sort = sort
        self.weight = weight
        self.pinyin_func = pinyin_func or self._default_pinyin
        self.site_name = site_name
        self.name = name or (site_name or "wiki_dict")
        self.include_license = include_license
    
    @staticmethod
    def _default_pinyin(text: str) -> str:
        """默认拼音转换"""
        if not text:
            return ""
        
        if not lazy_pinyin:
            return text.lower()
        
        if text.isascii():
            return text.lower()
        
        result = lazy_pinyin(text)
        return "".join(result)
    
    def generate(self, data: List[Tuple[str, str]], output: str) -> None:
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f"name: {self.name}\n")
            f.write(f'version: "{self.version}"\n')
            f.write(f"sort: {self.sort}\n")
            
            if self.include_license and self.site_name in self.SITE_LICENSE:
                site_name, license_url, license_name = self.SITE_LICENSE[self.site_name]
                f.write(f"license: {license_name}\n")
                f.write(f"copyright: © {site_name} 按 {license_name} 协议发布\n")
                f.write(f"license_url: {license_url}\n")
            
            f.write("---\n")
            f.write("\n")
            
            for title, _ in data:
                pinyin = self.pinyin_func(title)
                if pinyin:
                    f.write(f"{title}\t{pinyin}\t{self.weight}\n")


class PlainTextGenerator(Generator):
    """纯文本生成器"""
    
    def __init__(self, separator: str = "\t"):
        self.separator = separator
    
    def generate(self, data: List[Tuple[str, str]], output: str) -> None:
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            for title, content in data:
                f.write(f"{title}{self.separator}{content}\n")


class JsonGenerator(Generator):
    """JSON 生成器"""
    
    def __init__(self, indent: int = 2):
        self.indent = indent
    
    def generate(self, data: List[Tuple[str, str]], output: str) -> None:
        import json
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        result = [{"title": title, "content": content} for title, content in data]
        with open(output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=self.indent)


class CustomGenerator(Generator):
    """自定义格式生成器"""
    
    def __init__(self, format_func: callable):
        self.format_func = format_func
    
    def generate(self, data: List[Tuple[str, str]], output: str) -> None:
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            for title, content in data:
                f.write(self.format_func(title, content))


class DictMerger:
    """字典文件合并器"""
    
    @staticmethod
    def parse_dict_file(filepath: str) -> Tuple[Dict, List[Tuple[str, str, str]]]:
        """解析 Rime 字典文件"""
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        meta = {}
        entries = []
        in_entries = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("---"):
                if not in_entries:
                    in_entries = True
                continue
            
            if not in_entries:
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip()
            else:
                parts = line.split("\t")
                if len(parts) >= 3:
                    entries.append((parts[0], parts[1], parts[2]))
        
        return meta, entries
    
    @staticmethod
    def merge_dicts(file_paths: List[str], output: str, 
                    name: str = "merged_dict", version: str = "1.0",
                    site_name: str = None) -> int:
        """合并多个字典文件
        Args:
            file_paths: 要合并的文件路径列表
            output: 输出文件路径
            name: 合并后词库的名称
            version: 版本号
            site_name: 站点名称（如 'rocom'），如果提供则使用该站点的许可证信息
        """
        all_entries = []
        
        for filepath in file_paths:
            if os.path.exists(filepath):
                _, entries = DictMerger.parse_dict_file(filepath)
                all_entries.extend(entries)
        
        seen = set()
        unique_entries = []
        for title, pinyin, weight in all_entries:
            if title not in seen:
                seen.add(title)
                unique_entries.append((title, pinyin, weight))
        
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f"name: {name}\n")
            f.write(f'version: "{version}"\n')
            f.write("sort: original\n")
            
            # 根据站点设置许可证信息
            if site_name and site_name in RimeDictGenerator.SITE_LICENSE:
                site_display_name, license_url, license_name = RimeDictGenerator.SITE_LICENSE[site_name]
                f.write(f'license: "{license_name}"\n')
                f.write(f"copyright: © {site_display_name} 按 {license_name} 协议发布\n")
                f.write(f"license_url: {license_url}\n")
            else:
                f.write('license: "多种许可证，见原网站许可协议"\n')
                f.write("copyright: © 混合词库，源自各 Wiki 网站，遵循各自的许可协议\n")
            
            f.write("---\n")
            f.write("\n")
            
            for title, pinyin, weight in unique_entries:
                f.write(f"{title}\t{pinyin}\t{weight}\n")
        
        return len(unique_entries)


def create_generator(format_type: str = "rime", **kwargs) -> Generator:
    """创建生成器"""
    generators = {
        "rime": RimeDictGenerator,
        "txt": PlainTextGenerator,
        "json": JsonGenerator,
    }
    
    if format_type == "custom":
        return CustomGenerator(kwargs.get("format_func"))
    
    if format_type not in generators:
        raise ValueError(f"Unknown format type: {format_type}")
    
    return generators[format_type](**kwargs)


def merge_dicts(file_paths: List[str], output: str, 
                 name: str = "merged_dict", version: str = "1.0",
                 site_name: str = None) -> int:
    """合并多个字典文件"""
    return DictMerger.merge_dicts(file_paths, output, name, version, site_name)


__all__ = [
    "Generator", "RimeDictGenerator", "PlainTextGenerator",
    "JsonGenerator", "CustomGenerator", "DictMerger",
    "create_generator", "merge_dicts"
]