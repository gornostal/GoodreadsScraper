from Queries.file_reader import read_books
from Queries.htmlview import generate_html_page


if __name__ == "__main__":
    books = read_books()[0:10]
    generate_html_page(books)