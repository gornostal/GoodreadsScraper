from datetime import datetime
from typing import Optional, TypedDict, List


class RawBook(TypedDict):
    url: str
    title: str
    titleComplete: str
    description: str
    imageUrl: str
    genres: List[str]
    series: Optional[List[str]]
    author: List[str]
    publishDate: Optional[int]  # in milliseconds
    ratingHistogram: List[
        int
    ]  # [<number of 5 stars>, ..., <number of 1 stars>] e.g. [30, 20, 10, 5, 2]
    ratingsCount: int
    reviewsCount: Optional[int]
    numPages: Optional[int]
    language: str


class Book(TypedDict):
    url: str
    title: str
    titleComplete: str
    description: str
    imageUrl: str
    genres: List[str]
    series: Optional[List[str]]
    author: List[str]
    publishYear: Optional[int]
    averageRating: float
    fiveRatingsLeadingPercentage: (
        float  # difference between 5-star ratings and the next highest rating
    )
    ratingsCount: int
    reviewsCount: Optional[int]
    numPages: Optional[int]
    language: str


def convert_rawbook_to_book(raw_book: RawBook) -> Book | None:
    try:
        if not raw_book.get("title"):
            return None

        publish_date = raw_book.get("publishDate")
        try:
            publishYear = (
                datetime.fromtimestamp(publish_date / 1000).year if publish_date else None
            )
        except ValueError:
            publishYear = None

        ratings_count = raw_book.get("ratingsCount", 0)
        ratings = raw_book.get("ratingHistogram", [0, 0, 0, 0, 0])
        five_star_ratings = ratings[0]
        next_highest_ratings = max(ratings[1:]) if len(ratings) > 1 else 0
        five_ratings_leading_percentage = (
            ((five_star_ratings - next_highest_ratings) / ratings_count) * 100
            if ratings_count > 0
            else 0
        )

        # calculate average rating with 1 decimal place
        average_rating = (
            sum((i + 1) * count for i, count in enumerate(ratings)) / ratings_count
            if ratings_count > 0
            else 0
        )

        # Create and return the Book object
        book = Book(
            url=raw_book["url"],
            title=raw_book["title"],
            titleComplete=raw_book["titleComplete"],
            description=raw_book.get("description", "No description available."),
            imageUrl=raw_book.get(
                "imageUrl", "https://placehold.co/400x600?text=No+image"
            ),
            genres=raw_book.get("genres", []),
            series=raw_book.get("series"),
            author=raw_book["author"],
            publishYear=publishYear,
            averageRating=average_rating,
            fiveRatingsLeadingPercentage=five_ratings_leading_percentage,
            ratingsCount=ratings_count,
            reviewsCount=raw_book.get("reviewsCount"),
            numPages=raw_book.get("numPages"),
            language=raw_book.get("language"),
        )

        return book
    except:
        print(raw_book)
        print()
        raise
