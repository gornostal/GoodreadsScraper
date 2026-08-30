"""Spider to extract URLs of books from a public shelf on Goodreads"""

import scrapy
from scrapy import signals
from .book_spider import BookSpider


class ShelfSpider(scrapy.Spider):
    """Extract and crawl URLs of books from a public Goodreads shelf.

    This subsequently passes on the URLs to BookSpider.
    Consequently, this spider also yields BookItem's and AuthorItem's.
    """
    name = "shelf"

    goodreads_shelf_url = "https://www.goodreads.com/shelf/show/{}?page={}"

    def _set_crawler(self, crawler):
        super()._set_crawler(crawler)
        crawler.signals.connect(self.item_scraped_callback, signal=signals.item_scraped)

    def __init__(self, shelf_name, start_page_no, end_page_no, item_scraped_callback=None):
        super().__init__()
        self.book_spider = BookSpider()
        self.item_scraped_callback = item_scraped_callback

        self.start_urls = []
        for page_no in range(int(start_page_no), int(end_page_no) + 1):
            shelf_url = self.goodreads_shelf_url.format(shelf_name, page_no)
            self.start_urls.append(shelf_url)

    def parse(self, response):
        book_urls = response.css("a.bookTitle::attr(href)").extract()

        for book_url in book_urls:
            yield response.follow(book_url, callback=self.book_spider.parse)
