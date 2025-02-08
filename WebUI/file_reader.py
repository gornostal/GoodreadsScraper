import os
import json
from typing import List, cast

from .book import Book, RawBook, convert_rawbook_to_book


def get_al_jl_files() -> List[str]:
    "finds all files with prefix book_ and extension .jl"
    return [
        file
        for file in os.listdir()
        if file.startswith("book_") and file.endswith(".jl")
    ]


def read_books_from_jl(file_path: str) -> List[RawBook]:
    """Read books from a .jl file and return a list of book dictionaries."""
    books: List[RawBook] = []
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            book = cast(RawBook, json.loads(line.strip()))
            books.append(book)

    return books


def read_books() -> List[Book]:
    books: List[Book] = []
    for file in get_al_jl_files():
        books.extend(
            [
                b
                for b in map(convert_rawbook_to_book, read_books_from_jl(file))
                if b is not None
            ]
        )

    return books
