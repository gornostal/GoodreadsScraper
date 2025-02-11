import re
from datetime import datetime
from typing import Optional, TypedDict, List


class Award(TypedDict):
    name: str
    category: str


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
    awards: List[Award]


class Book(TypedDict):
    url: str
    title: str
    titleComplete: str
    description: str
    imageUrl: str
    genres: List[str]
    series: Optional[List[str]]
    numberInSeries: int
    author: List[str]
    booksByAuthor: int
    publishYear: int
    averageRating: float
    fiveRatingsLeadingPercentage: (
        float  # difference between 5-star ratings and the next highest rating
    )
    ratingsCount: int
    reviewsCount: Optional[int]
    numPages: Optional[int]
    language: str
    awards: List[str]


def convert_rawbook_to_book(raw_book: RawBook) -> Book | None:
    try:
        if not raw_book.get("title"):
            return None

        publish_date = raw_book.get("publishDate")
        try:
            publishYear = (
                datetime.fromtimestamp(publish_date / 1000).year
                if publish_date
                else None
            )
        except ValueError:
            publishYear = 0

        ratings_count = raw_book.get("ratingsCount", 0)
        ratings = raw_book.get("ratingHistogram", [0, 0, 0, 0, 0])
        rating_percentage_histogram = [
            (count / ratings_count) * 100 if ratings_count > 0 else 0
            for count in ratings
        ]
        five_star_ratings = rating_percentage_histogram[-1]
        next_highest_ratings = (
            max(rating_percentage_histogram[1:-1]) if len(ratings) > 1 else 0
        )
        five_ratings_leading_percentage = five_star_ratings - next_highest_ratings

        # calculate average rating with 1 decimal place
        average_rating = (
            sum((i + 1) * count for i, count in enumerate(ratings)) / ratings_count
            if ratings_count > 0
            else 0
        )

        # find numberInSeries by parsing the number following # character in the titleComplete
        # for example "Kingdom of Ash (Throne of Glass, #7)" will have numberInSeries = 7
        number_in_series = 0
        if raw_book.get("titleComplete"):
            result = re.search(r"#(\d+)\)", raw_book["titleComplete"])
            number_in_series = int(result.group(1)) if result else 0

        awards = list(
            map(
                lambda a: (
                    f"{a['name']} - {a['category']}" if a["category"] else a["name"]
                ),
                raw_book.get("awards", []),
            )
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
            numberInSeries=number_in_series,
            author=raw_book["author"],
            booksByAuthor=0,  # this will be updated later
            publishYear=publishYear or 0,
            averageRating=average_rating,
            fiveRatingsLeadingPercentage=five_ratings_leading_percentage,
            ratingsCount=ratings_count,
            reviewsCount=raw_book.get("reviewsCount"),
            numPages=raw_book.get("numPages"),
            language=raw_book.get("language"),
            awards=awards,
        )

        return book
    except:
        print(raw_book)
        print()
        raise
