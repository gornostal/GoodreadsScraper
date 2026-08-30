from flask import Flask, Response, jsonify, render_template, request

from .file_reader import read_books

try:
    # Optional, gitignored module holding personal filters (see WebUI/filters.py).
    from .filters import filter_books
except ImportError:

    def filter_books(books):
        return books


app = Flask(__name__)


# "plain/text" is a common typo for "text/plain" - honour both.
PLAIN_TEXT_MIMETYPES = ("text/plain", "plain/text")


def wants_plain_text():
    """Return True when the client explicitly prefers plain text over HTML."""
    accept = request.accept_mimetypes
    quality = max(
        (q for mime, q in accept if mime.lower() in PLAIN_TEXT_MIMETYPES), default=0
    )
    # A wildcard "*/*" (curl's default) is not an explicit preference: keep HTML.
    return quality > 0 and quality >= accept["text/html"]


@app.route("/")
def book_gallery():
    books = read_books()
    max_results = request.args.get("max_results", default=100, type=int)

    books = filter_books(books)
    books.sort(key=lambda x: x["fiveRatingsLeadingPercentage"], reverse=True)

    if wants_plain_text():
        return Response(
            render_template("books_text.txt", books=books, max_results=max_results),
            mimetype="text/plain",
        )

    return render_template("books.html", books=books, max_results=max_results)


@app.route("/hide-book", methods=["POST"])
def hide_book():
    try:
        data = request.get_json()

        if not data or "url" not in data:
            return jsonify({"error": 'Invalid payload, "url" key missing.'}), 400

        url = data["url"]

        # Validate that url is a non-empty string
        if not isinstance(url, str) or not url.strip():
            return jsonify({"error": 'Invalid "url" value.'}), 400

        # Append the URL to hidden_books.txt
        with open("hidden_books.txt", "a") as file:
            file.write(url + "\n")

        return jsonify({"message": "URL appended successfully."}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
