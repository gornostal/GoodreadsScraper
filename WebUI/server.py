from flask import Flask, render_template, request

from .file_reader import read_books

app = Flask(__name__)


@app.route("/")
def book_gallery():
    books = read_books()
    max_results = request.args.get("max_results", default=100, type=int)

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

    return render_template("books.html", books=books, max_results=max_results)
