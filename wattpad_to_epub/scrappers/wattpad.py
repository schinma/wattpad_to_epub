import re
from typing import Tuple

import httpx
import typer
from bs4 import BeautifulSoup
from loguru import logger

from wattpad_to_epub.scrappers.base import StoryScrapperBase
from ebooklib.epub import EpubHtml


class WattpadScrapper(StoryScrapperBase):
    URL_STORY_API = "https://www.wattpad.com/api/v3/stories"

    def __init__(self, url):
        super().__init__(url)
        self.story_id, self.story_slug = self.get_id_from_url(self.url)
        response = httpx.get(f"{self.URL_STORY_API}/{self.story_id}", headers={"user-agent": "Mozilla/5.0"})
        self.story_info = response.json()

    def get_id(self) -> Tuple[str, str]:
        match = re.match(r"^https://www.wattpad.com/story/(?P<id>\d+)-(?P<slug>.+)$", self.url)
        if match is None:
            logger.error(f"Cannot get information from URL {self.url}")
            raise typer.Exit()
        self.id, self.slug = match.group("id", "slug")
        return self.id

    def get_book_cover_content(self):
        return httpx.get(self.story_info["cover"]).content

    def get_chapters(self):
        return self.story_info["parts"]

    def get_language(self):
        return self.story_info["language"]["name"]

    def get_author(self):
        return self.story_info["user"]["name"]

    def get_description(self):
        return self.story_info["description"]

    def get_publisher(self):
        return "Wattpad"

    def get_chapter_content(self, chapter_soup: BeautifulSoup):
        text = chapter_soup.pre
        text.name = "div"
        if text is None:
            logger.error(f"Could not fin content for chapter")
            raise typer.exit()
        return text
