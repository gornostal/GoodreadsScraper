from typing import List
from Queries.book import Book


def book_to_html(book: Book) -> str:
    """Convert a book dictionary into an HTML card."""
    genres = ", ".join(book["genres"])
    authors = ", ".join(book["author"])

    rating_score = book["fiveRatingsLeadingPercentage"]
    # convert numbers like 3430 to 3.4K
    total_ratings_human_readable = (
        f"{book['ratingsCount'] / 1000:.0f}K" if book["ratingsCount"] > 1000 else "< 1K"
    )
    average_rating = book["averageRating"]

    return f"""
    <div class="row py-2">
        <div class="col-md-2">
            <a href="{book['url']}">
                <img src="{book['imageUrl']}" class="rounded img-fluid cover-img" alt="{book['title']}">
            </a>
        </div>
        <div class="col-md-10">
            <h4>{book['title']} {f"#{book['numberInSeries']}" if book['numberInSeries'] > 0 else ""}</h4>
            <p class="small">{book['description']}</p>
            <p>
                <strong>Year:</strong> {book['publishYear']} <br />
                <strong>Author(s):</strong> {authors} <br />
                <strong>Genres:</strong> {genres} <br />
                <strong>Rating:</strong> {average_rating:.2f}  ({rating_score:.0f}%) <br />
                <strong>Number of Ratings:</strong> {total_ratings_human_readable}
            </p>
        </div>
    </div>
    """


def generate_html_page(
    books: List[Book], output_path: str = "books.html", max_books: int = 10
):
    """Generate an HTML page for a list of books."""
    head = (
        """
    <html>
    <head>
      <title>Book Gallery</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
      <style>
        .cover-img {
            max-height: 250px;
            width: auto; /* Keeps aspect ratio */
        }
      </style>
    </head>
    <body>
      <h1 class="text-center my-4">Found """,
        str(len(books)),
        """ books</h1>
      <div class="container">
    """,
    )

    body = "".join(book_to_html(book) for book in books[:max_books])

    end = """
      </div>
    </body>
    </html>
    """

    full_html = "".join(head) + body + end

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(full_html)

    print(f"HTML page generated at: {output_path}")
