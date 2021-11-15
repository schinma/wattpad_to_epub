import asyncio
import re
from pathlib import Path
from typing import Any, Dict, Tuple

import httpx
import typer
from bs4 import BeautifulSoup
from ebooklib import epub
from loguru import logger

app = typer.Typer()

URL_STORY_API = "https://www.wattpad.com/api/v3/stories"
STYLE_FILE_PATH = Path(__file__).resolve().parent / "style.css"


def get_id_from_url(url: str) -> Tuple[str, str]:
    match = re.match(r"^https://www.wattpad.com/story/(?P<id>\d+)-(?P<slug>.+)$", url)
    if match is None:
        logger.error(f"Cannot get information from URL {url}")
        raise typer.Exit()
    return match.group("id", "slug")


async def create_chapter(client: httpx.Client, part: Dict[str, Any], index: int) -> epub.EpubHtml:

    chapter = epub.EpubHtml(title=part["title"], file_name=f"chapter_{index}.xhtml", lang="eng")

    logger.info(f"Downloading chapter {index}: {chapter.title} from {part['url']}...")
    soup = BeautifulSoup(await client.get(part["url"]), features="lxml")

    text = soup.pre
    text.name = "div"
    if text is None:
        logger.error(f"Could not fin content for chapter {chapter.title}")
        raise typer.exit()
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


@app.command()
def get_story(url: str) -> None:
    async def create_story(url: str):
        story_id = get_id_from_url(url)

        # Download story infos with the API
        async with httpx.AsyncClient() as client:
            # change the user-agent header because wattpad blocks otherwise
            client.headers["user-agent"] = "Mozilla/5.0"

            story_id, story_slug = get_id_from_url(url)
            response = await client.get(f"{URL_STORY_API}/{story_id}")
            story_info = response.json()
            parts = story_info["parts"]
            cover = await client.get(story_info["cover"])
            cover = cover

            # Making the Epub file
            epub_book = epub.EpubBook()
            epub_book.set_identifier(f"fanfiction-{story_id}")
            epub_book.set_title(story_info["title"])
            epub_book.set_language(story_info["language"]["name"])

            epub_book.add_author(story_info["user"]["name"])
            epub_book.add_metadata("DC", "description", story_info["description"])
            epub_book.add_metadata("DC", "publisher", "Wattpad")
            epub_book.add_metadata("DC", "source", url)

            epub_book.set_cover("cover_image.jpg", cover.content)

            with open(STYLE_FILE_PATH) as css_file:
                style_doc = epub.EpubItem(
                    uid="style_doc", file_name="style/main.css", media_type="text/css", content=css_file.read()
                )
            epub_book.add_item(style_doc)

            chapters = await asyncio.gather(*[create_chapter(client, part, index) for index, part in enumerate(parts)])

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

            # Write epub file
            epub.write_epub(f"{story_slug}.epub", epub_book)

    asyncio.run(create_story(url))


def main():
    app()
