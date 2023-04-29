import asyncio
import http
import re
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from pydoc import source_synopsis
from typing import Any, Dict, Tuple

import httpx
import typer
from bs4 import BeautifulSoup
from ebooklib import epub
from loguru import logger
from regex import P

from wattpad_to_epub.scrappers import ChrysentemumScrapper, WattpadScrapper
from wattpad_to_epub.scrappers.base import StoryScrapperBase


class WebSite(Enum):
    WATTPAD = "WP"
    CHRYSENTEMUM = "CG"


STYLE_FILE_PATH = Path(__file__).resolve().parent / "style.css"

app = typer.Typer()


async def create_chapter(
    client: httpx.Client, part: Dict[str, Any], index: int, scrapper: StoryScrapperBase
) -> epub.EpubHtml:

    chapter = epub.EpubHtml(title=part["title"], file_name=f"chapter_{index}.xhtml", lang="eng")

    logger.info(f"Downloading chapter {index}: {chapter.title} from {part['url']}...")
    soup = BeautifulSoup(await client.get(part["url"]), features="lxml")

    text = scrapper.get_chapter_content(soup)

    title_tag = soup.new_tag("h1")
    title_tag.string = chapter.title

    chapter_content = BeautifulSoup(
        f"""
        <html>
            <head>
                <title>{chapter.title}</title>
                <link rel="stylesheet" type="text/css" href="style/main.css" />
            </head>
        <body></body>
        </html>
        """,
        features="lxml",
    )
    chapter_content.body.append(title_tag)
    chapter_content.body.append(text)
    chapter.set_content(str(chapter_content))
    return chapter


async def create_ebook(scrapper: StoryScrapperBase):
    """Create the ebook file

    Args:
        scrapper (StoryScrapperBase): _description_
    """
    title = scrapper.get_title()
    cover_content = scrapper.get_book_cover_content()
    language = scrapper.get_language()
    author = scrapper.get_author()
    story_id = scrapper.get_id()
    publisher = scrapper.get_publisher()
    description = scrapper.get_description()
    try:
        story_slug = scrapper.slug
    except AttributeError:
        story_slug = story_id

    parts = scrapper.get_chapters()

    # Making the Epub file
    epub_book = epub.EpubBook()
    epub_book.set_identifier(f"fanfiction-{story_id}")
    epub_book.set_title(title)
    epub_book.set_language(language)

    epub_book.add_author(author)
    epub_book.add_metadata(
        "DC",
        "description",
        description,
    )
    epub_book.add_metadata("DC", "publisher", publisher)
    epub_book.add_metadata("DC", "source", scrapper.url)

    epub_book.set_cover("cover_image.jpg", cover_content)

    with open(STYLE_FILE_PATH) as css_file:
        style_doc = epub.EpubItem(
            uid="style_doc", file_name="style/main.css", media_type="text/css", content=css_file.read()
        )
    epub_book.add_item(style_doc)

    async with httpx.AsyncClient() as client:
        chapters = await asyncio.gather(
            *[create_chapter(client, part, index, scrapper) for index, part in enumerate(parts)]
        )

    for chapter in chapters:
        chapter.add_item(style_doc)
        epub_book.add_item(chapter)

    epub_book.toc = (epub.Link("intro.xhtml", "Introduction", "intro"), (epub.Section("Chapters"), chapters))
    epub_book.add_item(epub.EpubNcx())
    epub_book.add_item(epub.EpubNav())

    nav_page = epub.EpubNav(uid="book_toc", file_name="toc.xhtml")
    nav_page.add_item(style_doc)
    epub_book.add_item(nav_page)
    epub_book.spine = [nav_page] + chapters

    return epub_book


@app.command()
def get_story(url: str, web_site: WebSite, output: str = typer.Option(...)) -> None:
    async def create_story(url: str, website):

        match (website):
            case WebSite.WATTPAD:
                scrapper = WattpadScrapper(url)
            case WebSite.CHRYSENTEMUM:
                scrapper = ChrysentemumScrapper(url)

        epub_book = await create_ebook(scrapper)

        # Write epub file
        epub.write_epub(f"{output}.epub", epub_book)

    asyncio.run(create_story(url, web_site))


def main():
    app()


if __name__ == "__main__":
    main()
