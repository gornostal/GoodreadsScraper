"""
Scrape reviews from Goodreads book pages and summarize what readers liked/disliked.
Output: reviews.jl (JSONL) with schema {url, id, like, dislike}
"""

import json
import re
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

DELAY = 2.5  # seconds between requests


def extract_book_id(url: str) -> str:
    m = re.search(r'/book/show/(\d+)', url)
    return m.group(1) if m else url


def fetch_reviews(url: str) -> list[dict]:
    """Fetch page and return list of {rating, text} dicts."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return []

    soup = BeautifulSoup(r.text, 'lxml')
    reviews = []

    for article in soup.find_all('article', {'class': lambda c: c and 'ReviewCard' in str(c)}):
        # Extract star rating from aria-label like "Rating 4 out of 5"
        rating_el = article.find(attrs={'aria-label': lambda a: a and 'Rating' in str(a) and 'out of 5' in str(a)})
        if rating_el:
            m = re.search(r'Rating (\d)', rating_el.get('aria-label', ''))
            stars = int(m.group(1)) if m else 0
        else:
            stars = 0

        body_el = article.find(attrs={'data-testid': 'contentContainer'})
        text = body_el.get_text(' ', strip=True) if body_el else ''
        text = re.sub(r'\s+', ' ', text).strip()

        if text:
            reviews.append({'stars': stars, 'text': text})

    return reviews


def first_sentences(text: str, max_chars: int = 300) -> str:
    """Return the first few complete sentences up to max_chars."""
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    result = []
    total = 0
    for s in sentences:
        if total + len(s) > max_chars and result:
            break
        result.append(s)
        total += len(s) + 1
    return ' '.join(result).strip()


def summarize(reviews: list[dict]) -> tuple[str, str]:
    """Produce (like_summary, dislike_summary) from list of reviews."""
    positive = [r for r in reviews if r['stars'] >= 4]
    negative = [r for r in reviews if r['stars'] <= 2]

    def combine(group: list[dict], n: int = 3) -> str:
        texts = [first_sentences(r['text']) for r in group[:n]]
        # Deduplicate and join
        seen = set()
        unique = []
        for t in texts:
            key = t[:60]
            if key not in seen:
                seen.add(key)
                unique.append(t)
        return ' | '.join(unique)

    like = combine(positive) or 'No positive reviews found.'
    dislike = combine(negative) or 'No negative reviews found.'
    return like, dislike


def main():
    with open('urls.txt') as f:
        urls = [line.strip() for line in f if line.strip()]

    with open('reviews.jl', 'w') as out:
        for url in urls:
            book_id = extract_book_id(url)
            print(f"Scraping {url} ...")

            reviews = fetch_reviews(url)
            if not reviews:
                print("  No reviews extracted, skipping.")
                record = {'url': url, 'id': book_id, 'like': '', 'dislike': ''}
            else:
                rated = [r for r in reviews if r['stars'] > 0]
                print(f"  {len(reviews)} reviews, {len(rated)} with ratings")
                like, dislike = summarize(rated if rated else reviews)
                record = {'url': url, 'id': book_id, 'like': like, 'dislike': dislike}

            out.write(json.dumps(record) + '\n')
            out.flush()
            time.sleep(DELAY)

    print("Done. Results saved to reviews.jl")


if __name__ == '__main__':
    main()
