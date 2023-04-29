import re

import httpx
import typer
from bs4 import BeautifulSoup
from loguru import logger

from wattpad_to_epub.scrappers.base import StoryScrapperBase


class ChrysentemumScrapper(StoryScrapperBase):
    def __init__(self, url):
        super().__init__(url)
        self.soup = BeautifulSoup(httpx.get(self.url), features="lxml")

    def get_id(self):
        match = re.match(r"^https://chrysanthemumgarden.com/novel-tl/(?P<id>\w+)/$", self.url)
        if match is None:
            logger.error(f"Cannot get information from URL {self.url}")
            raise typer.Exit()
        return match.group("id")

    def get_title(self) -> str:
        return self.soup.find_all("h1", class_="novel-title")[0].text

    def get_author(self) -> str:
        return self.soup.find_all(string=re.compile("Author: ((\w)+)"))[0].removeprefix("Author: ")

    def get_description(self) -> str:
        paragraphs = self.soup.find_all("div", class_="entry-content")[0].find_all("p")
        return "\n".join([p.text for p in paragraphs])

    def get_book_cover_content(self):
        img = self.soup.find("div", class_="novel-cover").find("img")
        img_src = img["src"]
        return httpx.get(img_src).content

    def get_language(self):
        return "English"

    def get_chapters(self) -> list[dict]:
        """Return the list of chapters"""
        chapters = self.soup.find("div", class_="translated-chapters").find_all("div", class_="chapter-item")
        return [{"title": chap.a.text.strip(), "url": chap.a["href"]} for chap in chapters]

    def get_publisher(self) -> str:
        return "Chrysenthemum Garden"

    def get_chapter_content(self, chapter_soup: BeautifulSoup):
        content = chapter_soup.find("div", {"id": "novel-content"})
        return content
