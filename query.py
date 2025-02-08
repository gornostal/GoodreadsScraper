from Queries.file_reader import read_books
from Queries.htmlview import generate_html_page


if __name__ == "__main__":
    books = read_books()

    books = [
        book
        for book in books
        if book["averageRating"] >= 3.8
        and book["fiveRatingsLeadingPercentage"] >= -5
        and book["publishYear"] >= 2000
        and book["ratingsCount"] >= 100_000
        and book["numberInSeries"] < 2
        and (book.get("language") or "").lower() == "english"
        and "Science Fiction" in " ".join(book["genres"])
    ]

    books.sort(key=lambda x: x["fiveRatingsLeadingPercentage"], reverse=True)

    generate_html_page(books, max_books=100)
