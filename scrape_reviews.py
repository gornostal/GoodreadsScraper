"""
Scrape Goodreads reviews: top reviews (plain HTTP) plus 1/2/3-star reviews (playwright-cli).

Input: Goodreads book URLs as arguments, or a file (-f) where each line contains a
/book/show/ URL somewhere in it. That includes the web UI's plain-text list:
    curl -s -H 'Accept: text/plain' http://127.0.0.1:5000/ > books.txt
    python scrape_reviews.py -f books.txt

Output: JSONL (default reviews_raw.jl), one record per (book, source):
    {"url", "id", "title", "source": "top" | "1" | "2" | "3", "reviews": [{"stars", "text"}]}
The script is resumable: (url, source) pairs that are already in the output file are skipped.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}
DELAY = 3  # seconds between requests
PW_SESSION = 'goodreads-reviews'
URL_RE = re.compile(r'https://www\.goodreads\.com/book/show/[^\s/?#]+')

# Runs inside the reviews page. It clicks the star-N histogram bar, waits until the
# cards are re-rendered with only N-star reviews and the count stops changing, and
# returns them as JSON. Some ratings are fractional ("Rating 0.25 out of 5"), so a
# card counts as N-star when its rating is within 1 of N.
FILTER_JS = r'''
async () => {
  const N = __N__;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const bar = () => document.querySelector('[data-testid=ratingBar-' + N + ']');
  const cards = () => [...document.querySelectorAll('article.ReviewCard')].map(a => {
    const r = a.querySelector('[aria-label^="Rating "]');
    const m = r && r.getAttribute('aria-label').match(/Rating ([\d.]+)/);
    const t = a.querySelector('[data-testid="contentContainer"]');
    return {stars: m ? +m[1] : null, text: t ? t.innerText.trim() : ''};
  });
  const ok = c => c.length > 0 && c.every(x => x.stars !== null && Math.abs(x.stars - N) < 1);
  for (let i = 0; i < 60 && !(document.querySelector('article.ReviewCard') && bar()); i++) await sleep(500);
  if (!bar()) return JSON.stringify({error: 'no rating bar (bot check page?)', title: document.title});
  for (let attempt = 0; attempt < 3; attempt++) {
    // A login popup sometimes blocks clicks. Close it; removing it crashes the React app.
    document.querySelector('.Overlay button[aria-label=Close]')?.click();
    await sleep(300);
    bar()?.click();
    let prev = -1, stable = 0;
    for (let i = 0; i < 40; i++) {
      await sleep(500);
      const c = cards();
      if (!ok(c)) { stable = 0; continue; }
      stable = c.length === prev ? stable + 1 : 0;
      prev = c.length;
      if (stable >= 3) return JSON.stringify(c);
    }
  }
  return JSON.stringify({error: 'filter did not apply', got: cards().map(c => c.stars)});
}
'''


def book_id(url: str) -> str:
    m = re.search(r'/book/show/(\d+)', url)
    return m.group(1) if m else url


def html_to_text(html: str) -> str:
    return BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)


def parse_next_data(raw: str) -> tuple[str, list[dict]] | None:
    """Return (title, reviews) from the __NEXT_DATA__ JSON of a book page."""
    state = json.loads(raw)['props']['pageProps']['apolloState']
    title = next((v.get('title') for k, v in state.items() if k.startswith('Book:') and v.get('title')), '')
    reviews = [{'stars': v.get('rating'), 'text': html_to_text(v['text'])}
               for k, v in state.items() if k.startswith('Review:') and v.get('text')]
    return title, reviews


# --- playwright-cli helpers -------------------------------------------------

def pw(*args: str, timeout: int = 180) -> str:
    return subprocess.run(['playwright-cli', f'-s={PW_SESSION}', *args],
                          capture_output=True, text=True, timeout=timeout).stdout


def pw_eval(js: str):
    out = pw('eval', js)
    m = re.search(r'### Result\n(.*)', out)
    if not m:
        return {'error': 'no eval result', 'output': out[-500:]}
    value = json.loads(m.group(1))
    return json.loads(value) if isinstance(value, str) else value


class Browser:
    def __init__(self):
        self.opened = False

    def goto(self, url: str):
        if not self.opened:
            pw('open', url)
            self.opened = True
        else:
            pw('goto', url)

    def close(self):
        if self.opened:
            pw('close')


# --- scrapers ---------------------------------------------------------------

def fetch_top(url: str, browser: Browser) -> tuple[str, list[dict]] | None:
    """Top ~30 reviews embedded in the book page. Falls back to the browser when curl is rate limited."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        nd = BeautifulSoup(r.text, 'lxml').find('script', id='__NEXT_DATA__')
        if nd and nd.string:
            return parse_next_data(nd.string)
        print(f'  plain request returned no data (HTTP {r.status_code}), using browser')
    except Exception as e:
        print(f'  plain request failed ({e}), using browser')
    browser.goto(url)
    raw = pw_eval('''async () => {
        for (let i = 0; i < 60 && !document.getElementById('__NEXT_DATA__'); i++) await new Promise(r => setTimeout(r, 500));
        const el = document.getElementById('__NEXT_DATA__');
        return el ? el.textContent : JSON.stringify({error: 'no __NEXT_DATA__'});
    }''')
    if isinstance(raw, dict) and 'props' in raw:
        return parse_next_data(json.dumps(raw))
    print(f'  browser fallback failed: {str(raw)[:200]}')
    return None


def fetch_by_stars(url: str, stars: int, browser: Browser) -> list[dict] | None:
    """Up to 30 reviews with the given star rating, from the filtered reviews page."""
    for attempt in range(3):
        browser.goto(url + '/reviews')
        res = pw_eval(FILTER_JS.replace('__N__', str(stars)))
        if isinstance(res, list):
            return res
        print(f'  {stars}★ attempt {attempt + 1} failed: {str(res)[:200]}')
        time.sleep(3)
    return None


# --- main -------------------------------------------------------------------

def read_urls(args) -> list[str]:
    lines = list(args.urls)
    if args.file:
        with open(args.file) as f:
            lines += f.read().splitlines()
    urls = []
    for line in lines:
        m = URL_RE.search(line)
        if m and m.group(0) not in urls:
            urls.append(m.group(0))
    return urls


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('urls', nargs='*', help='Goodreads book URLs')
    ap.add_argument('-f', '--file', help='file with lines containing Goodreads book URLs')
    ap.add_argument('-o', '--out', default='reviews_raw.jl', help='output JSONL (default: reviews_raw.jl)')
    ap.add_argument('--stars', default='1,2,3',
                    help='comma-separated star filters to scrape with the browser; empty string to skip (default: 1,2,3)')
    ap.add_argument('--no-top', action='store_true', help='skip top reviews from the book page')
    args = ap.parse_args()

    urls = read_urls(args)
    if not urls:
        ap.error('no Goodreads book URLs given')
    sources = ([] if args.no_top else ['top']) + [s.strip() for s in args.stars.split(',') if s.strip()]

    done = set()
    if os.path.exists(args.out):
        with open(args.out) as f:
            done = {(d['url'], d['source']) for d in map(json.loads, f)}

    browser = Browser()
    titles: dict[str, str] = {}
    failed = []
    try:
        with open(args.out, 'a') as out:
            for i, url in enumerate(urls, 1):
                print(f'[{i}/{len(urls)}] {url}')
                for source in sources:
                    if (url, source) in done:
                        continue
                    if source == 'top':
                        res = fetch_top(url, browser)
                        if res:
                            titles[url], reviews = res
                        else:
                            reviews = None
                        time.sleep(DELAY)
                    else:
                        reviews = fetch_by_stars(url, int(source), browser)
                    if reviews is None:
                        failed.append((url, source))
                        continue
                    rec = {'url': url, 'id': book_id(url), 'title': titles.get(url, ''),
                           'source': source, 'reviews': reviews}
                    out.write(json.dumps(rec, ensure_ascii=False) + '\n')
                    out.flush()
                    print(f'  {source}: {len(reviews)} reviews')
    finally:
        browser.close()

    if failed:
        print('Failed (rerun to retry):', *[f'  {u} {s}' for u, s in failed], sep='\n')
        sys.exit(1)
    print(f'Done. Results saved to {args.out}')


if __name__ == '__main__':
    main()
