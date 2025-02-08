from flask import Flask, render_template

from .file_reader import read_books

app = Flask(__name__)


@app.route("/")
def book_gallery():
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

    return render_template("books.html", books=books[:100])
