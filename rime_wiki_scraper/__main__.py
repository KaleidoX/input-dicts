"""主入口"""
import click
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import register_all_sites
register_all_sites()

from scraper import create_scraper
from cleaner import create_default_pipeline
from generator import create_generator, merge_dicts


OUTPUT_DIR = "output"


@click.group()
def cli():
    """从 Wiki 爬取数据生成 Rime 词库"""
    pass


@cli.command()
@click.argument("wiki_type", default="zhwiki")
@click.argument("titles", nargs=-1, required=True)
@click.option("-o", "--output", default=None, help="输出文件（默认 output/{site_name}.dict.yaml）")
@click.option("--format", "format_type", default="rime", help="输出格式 (rime/txt/json)")
@click.option("--link-limit", default=10, help="每个词条获取的链接数")
def scrape(wiki_type, titles, output, format_type, link_limit):
    """爬取指定词条"""
    scraper = create_scraper(wiki_type)
    all_words = []
    
    for title in titles:
        print(f"正在爬取: {title}")
        words = scraper.scrape(title, link_limit)
        all_words.extend(words)
    
    if all_words:
        pipeline = create_default_pipeline()
        cleaned = pipeline.process(all_words)
        
        if output is None:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            output = f"{OUTPUT_DIR}/{wiki_type}.dict.yaml"
        
        generator = create_generator(format_type, site_name=wiki_type)
        generator.generate(cleaned, output)
        click.echo(f"已生成: {output}，共 {len(cleaned)} 个词条")
    else:
        click.echo("未获取到数据")


@cli.command()
@click.argument("wiki_type", default="zhwiki")
@click.argument("category")
@click.option("-o", "--output", default=None, help="输出文件（默认 output/{site_name}_{category}.dict.yaml）")
@click.option("--format", "format_type", default="rime", help="输出格式 (rime/txt/json)")
@click.option("--limit", default=50, help="最大词条数")
@click.option("--link-limit", default=5, help="每个词条获取的链接数")
def category(wiki_type, category, output, format_type, limit, link_limit):
    """从分类页面爬取"""
    scraper = create_scraper(wiki_type)
    
    print(f"正在获取分类: {category}")
    all_words = scraper.scrape_category(category, limit, link_limit)
    
    if all_words:
        pipeline = create_default_pipeline()
        cleaned = pipeline.process(all_words)
        
        if output is None:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            safe_category = "".join(c for c in category if c.isalnum())
            output = f"{OUTPUT_DIR}/{wiki_type}_{safe_category}.dict.yaml"
        
        # 自定义拼音函数，返回空格分隔的拼音
        try:
            from pypinyin import lazy_pinyin, Style
            def pinyin_func(text: str) -> str:
                if not text:
                    return ""
                if text.isascii():
                    return text.lower()
                pinyin_list = lazy_pinyin(text, style=Style.NORMAL)
                return " ".join(pinyin_list)
        except ImportError:
            def pinyin_func(text: str) -> str:
                return text.lower()
        
        # 根据格式类型传递不同的参数
        if format_type == "rime":
            generator = create_generator(format_type, site_name=wiki_type, pinyin_func=pinyin_func)
        else:
            generator = create_generator(format_type)
        
        generator.generate(cleaned, output)
        click.echo(f"已生成: {output}，共 {len(cleaned)} 个词条")
    else:
        click.echo("未获取到数据")


@cli.command()
@click.argument("inputs", nargs=-1, required=True)
@click.option("-o", "--output", default=f"{OUTPUT_DIR}/merged.dict.yaml", help="输出文件")
@click.option("--name", default="merged_dict", help="合并后的词库名称")
@click.option("--site", default=None, help="站点名称（如 'rocom'），用于使用正确的许可证")
def merge(inputs, output, name, site):
    """合并多个字典文件"""
    files = list(inputs)
    count = merge_dicts(files, output, name, site_name=site)
    click.echo(f"已合并 {len(files)} 个文件，生成: {output}，共 {count} 个词条")


@cli.command()
@click.argument("wiki_type", default="zhwiki")
@click.argument("titles", nargs=-1, required=True)
def test(wiki_type, titles):
    """测试爬取单个词条"""
    scraper = create_scraper(wiki_type)
    
    for title in titles:
        print(f"测试爬取: {title}")
        words = scraper.scrape(title, 5)
        for w, c in words[:3]:
            print(f"  - {w}: {c[:50]}...")


if __name__ == "__main__":
    cli()