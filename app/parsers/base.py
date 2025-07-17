from abc import ABC, abstractmethod


class BaseParser(ABC):

    @abstractmethod
    def __init__(self, url):
        ...



    @abstractmethod
    async def download(self):
        ...