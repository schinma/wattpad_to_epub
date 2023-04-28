from abc import ABC, abstractmethod


class StoryScrapperBase(ABC):
    def __init__(self, url):
        self.url = url

    @abstractmethod
    def get_title(self):
        pass

    @abstractmethod
    def get_author(self):
        pass

    @abstractmethod
    def get_description(self):
        pass

    @abstractmethod
    def get_chapters(self):
        pass

    @abstractmethod
    def get_book_cover_content(self):
        pass

    @abstractmethod
    def get_publisher(self):
        pass

    @abstractmethod
    def get_language():
        pass
