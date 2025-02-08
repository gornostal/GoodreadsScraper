from .book import Book

# maps author name to number of books written by that author
prolific_authors: dict[str, int] = {}


def process_authors(book: Book):
    for author in book.get("author"):
        if book["ratingsCount"] > 10_000:
            prolific_authors[author] = prolific_authors.get(author, 0) + 1


def enrich_book_attributes(book: Book):
    book["booksByAuthor"] = prolific_authors.get(book["author"][0], 0)
