"""数据清洗模块"""
import re
from typing import List, Tuple, Callable, Optional
from abc import ABC, abstractmethod


class Cleaner(ABC):
    """数据清洗基类"""
    
    @abstractmethod
    def clean(self, data: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """清洗数据"""
        pass


class Pipeline:
    """清洗流水线"""
    
    def __init__(self):
        self.steps: List[Cleaner] = []
    
    def add(self, cleaner: Cleaner) -> "Pipeline":
        """添加清洗步骤"""
        self.steps.append(cleaner)
        return self
    
    def process(self, data: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """执行清洗"""
        result = data
        for step in self.steps:
            result = step.clean(result)
        return result


class TextCleaner(Cleaner):
    """文本清洗"""
    
    def clean(self, data: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        result = []
        for title, content in data:
            title = self.clean_text(title)
            content = self.clean_text(content)
            if title and content:
                result.append((title, content))
        return result
    
    @staticmethod
    def clean_text(text: str) -> str:
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


class DuplicateCleaner(Cleaner):
    """去重清洗"""
    
    def clean(self, data: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        seen = set()
        result = []
        for title, content in data:
            if title not in seen:
                seen.add(title)
                result.append((title, content))
        return result


class LengthFilter(Cleaner):
    """长度过滤"""
    
    def __init__(self, min_title_len: int = 1, max_title_len: int = 50,
                 min_content_len: int = 5):
        self.min_title_len = min_title_len
        self.max_title_len = max_title_len
        self.min_content_len = min_content_len
    
    def clean(self, data: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        return [
            (title, content) for title, content in data
            if (self.min_title_len <= len(title) <= self.max_title_len
                and len(content) >= self.min_content_len)
        ]


class CategoryFilter(Cleaner):
    """分类过滤"""
    
    def __init__(self, exclude_prefixes: Optional[List[str]] = None):
        self.exclude_prefixes = exclude_prefixes or [
            "Wikipedia:", "Template:", "Help:", "File:",
            "Portal:", "Category:", "Module:", "User:"
        ]
    
    def clean(self, data: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        return [
            (title, content) for title, content in data
            if not any(title.startswith(prefix) for prefix in self.exclude_prefixes)
        ]


class PunctuationFilter(Cleaner):
    """标点符号过滤"""
    
    def __init__(self, keep_punctuation: str = ""):
        self.keep_punctuation = keep_punctuation
    
    def clean(self, data: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        result = []
        for title, content in data:
            if re.match(r'^[\u4e00-\u9fff]+$', title):
                result.append((title, content))
            elif re.match(r'^[a-zA-Z0-9\s\.\-\(\)]+$', title):
                result.append((title, content))
            elif re.match(r'^[\u4e00-\u9fa5]+$', title):
                result.append((title, content))
        return result


class CustomCleaner(Cleaner):
    """自定义清洗规则"""
    
    def __init__(self, filter_func: Callable[[str, str], bool],
                 transform_func: Optional[Callable[[str, str], Tuple[str, str]]] = None):
        self.filter_func = filter_func
        self.transform_func = transform_func
    
    def clean(self, data: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        result = []
        for title, content in data:
            if self.filter_func(title, content):
                if self.transform_func:
                    title, content = self.transform_func(title, content)
                result.append((title, content))
        return result


def create_default_pipeline() -> Pipeline:
    """创建默认清洗流水线"""
    return (
        Pipeline()
        .add(TextCleaner())
        .add(CategoryFilter())
        .add(DescriptionFilter())
        .add(LengthFilter(min_title_len=2, max_title_len=30, min_content_len=10))
        .add(DuplicateCleaner())
    )


class DescriptionFilter(Cleaner):
    """过滤描述性词语"""
    
    def __init__(self):
        self.patterns = [
            r'[\s（(].*?[)）]\s*',  # （闭眼的样子）或 (闭眼的样子)
            r'\s*\[.*?\]\s*',       # [描述]
            r'\s*-.*$',             # -描述
        ]
        self.compiled = [re.compile(p) for p in self.patterns]
    
    def clean(self, data: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        result = []
        for title, content in data:
            original = title
            for pattern in self.compiled:
                title = pattern.sub('', title)
            if title and len(title) >= 2:
                result.append((title, content))
        return result


__all__ = [
    "Cleaner", "Pipeline", "TextCleaner", "DuplicateCleaner",
    "LengthFilter", "CategoryFilter", "PunctuationFilter",
    "CustomCleaner", "DescriptionFilter", "create_default_pipeline"
]