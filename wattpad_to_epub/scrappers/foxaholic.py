import re

import httpx
import typer
from bs4 import BeautifulSoup
from loguru import logger

from wattpad_to_epub.scrappers.base import StoryScrapperBase


class FoxScrapper(StoryScrapperBase):
    def __init__(self, url):
        super().__init__(url)
        self.gcache_url = "https://webcache.googleusercontent.com/search?q=cache:"
        self.headers = headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
            "Alt-Used": "webcache.googleusercontent.com",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }
        self.soup = BeautifulSoup(httpx.get(self.gcache_url + self.url, headers=headers), features="lxml")

    def get_id(self) -> str:
        match = re.match(
            r"^https://www.foxaholic.com/novel/(?P<id>[-\w]+)/$",
            self.url,
        )
        if match is None:
            logger.error(f"Cannot get information from URL {self.url}")
            raise typer.Exit()
        return match.group("id")

    def get_title(self) -> str:
        return self.soup.find_all("div", class_="post-title")[0].h1.text.strip()

    def get_author(self) -> str:
        author_content = self.soup.find_all("div", class_="author-content")[0]
        names = [link.text for link in author_content.select("a")]
        return ", ".join(names)

    def get_description(self) -> str:
        summary_container = self.soup.find("div", class_="summary__content")
        paragraphs = []
        for elem in summary_container.children:
            if elem.name == "p":
                paragraphs.append(elem.text)
            if elem.name == "hr":
                break
        return "\n".join(paragraphs)

    def get_chapters(self) -> list[dict]:
        chapters = self.soup.find_all("li", class_="wp-manga-chapter")
        chapter_list = [{"title": chap.a.text.strip(), "url": self.gcache_url + chap.a["href"]} for chap in chapters]
        chapter_list.reverse()
        return chapter_list

    def get_book_cover_content(self):
        img = self.soup.find("div", class_="summary_image").img
        url = img["data-src"]
        with open("fox-cover.jpg", "r") as file:
            return file

    def get_publisher(self) -> str:
        return "Foxaholic"

    def get_language(self) -> str:
        return "English"

    def get_chapter_content(self, chapter_soup: BeautifulSoup):
        return chapter_soup.find("div", class_="text-left")
