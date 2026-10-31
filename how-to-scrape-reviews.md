# How to scrape Goodreads reviews

## TL;DR
```sh
# all books currently shown in the web UI
curl -s -H 'Accept: text/plain' http://127.0.0.1:5000/ > books.txt
python scrape_reviews.py -f books.txt            # top + 1/2/3★ reviews -> reviews_raw.jl
python scrape_reviews.py <book url> <book url>   # or pass URLs directly
```
- Output is `reviews_raw.jl`, with one record per book and source: `{url, id, title, source: "top"|"1"|"2"|"3", reviews: [{stars, text}]}`.
- The script can be resumed. Rerun the same command to retry anything listed as failed.
- `--stars 2,3` limits the star filters, `--stars ''` skips the browser part, and `--no-top` skips top reviews.
- A full run takes about 1 minute per book, mostly for the browser filters. 38 books took around 40 minutes and never hit a bot block.
- `reviews.jl` holds older like/dislike summaries made by a previous version of the script. `reviews_raw.jl` replaces it.

The rest of this doc explains how the script works, for debugging or manual use.

## 1. Check existing data
Look up the book in `book_*.jl` to get its URL. Check `reviews_raw.jl` to see whether its reviews were already scraped.

If the book isn't there, search `https://www.goodreads.com/search?q=<title>+<author>`. Don't just pick the result with the most ratings: some editions are mislabeled and point to a different work (e.g. "Lightning Publisher: Berkley" is actually *Angels' Blood*). Always check that the reviews mention the book's own characters and plot before going further.

## 2. Top reviews: plain HTTP request
The book page (`/book/show/<id>`) has ~30 top reviews embedded in the `__NEXT_DATA__` JSON:
`props.pageProps.apolloState` → `Review:*` entries with `rating` and `text` (HTML).
The rating breakdown is in `ratingsCountDist`.

Parse this JSON rather than the HTML, because the HTML doesn't contain per-review rating labels.
Top reviews are mostly 4–5★, so they give a good picture of what readers like but not of what they dislike.

After a few requests, curl may start getting empty responses (rate limiting). If that happens, load the book page in playwright-cli instead and read `document.getElementById('__NEXT_DATA__')` with `eval`. The script falls back to this automatically.

## 3. Critical reviews: playwright-cli
The reviews page (`/book/show/<id>/reviews`) can filter by star rating, but:
- it shows a bot-check "Loading…" page first and then navigates, so it needs a real browser. An `eval` that runs during that navigation fails with "Execution context was destroyed". Just retry it.
- the `?ratingFilter=N` URL param is ignored.

Steps (the script's `FILTER_JS` does steps 2–4 in a single async `eval`):
1. `playwright-cli open <reviews url>` (or `goto` if the browser is already open).
2. Wait until `article.ReviewCard` and the histogram bar `[data-testid=ratingBar-N]` both exist. The bar is a `div[role=button]` with `aria-label="N stars"`, not a `<button>`, and it can render after the cards.
3. Click the bar from JS: `document.querySelector('[data-testid=ratingBar-1]').click()`.
   - A login popup (`.Overlay`) sometimes blocks clicks. Close it with `document.querySelector('.Overlay button[aria-label=Close]')?.click()`. Don't remove the overlay from the DOM, because that crashes the React app.
4. Poll until every card shows the expected rating and the card count stops changing. The filter takes a few seconds, and the cards update in batches.
   - Read stars from `[aria-label^="Rating "]`. Some ratings are fractional (`Rating 0.25 out of 5`, `Rating 1.5 out of 5`), so parse them with `/Rating ([\d.]+)/` and accept anything within 1 of N. Requiring an exact match makes the filter look like it never applied.
   - Read the text from `[data-testid="contentContainer"]`.
5. Repeat for each star level. Each filter returns up to 30 reviews, and sometimes fewer, especially for 1★.

## 4. Analyze
- **Likes/dislikes:** combine the top reviews with the 1–3★ reviews, then group recurring themes into likes and dislikes.
- **A specific aspect** (e.g. the ending): grep each review for keywords (`ending|the end|finale|conclusion|last chapter|climax|twist|resolution|wrap up|epilogue`). Keep the matching sentence plus one sentence on each side, then summarize per book. For 38 books this gives about 440 KB of excerpts, so split the books into batches for parallel subagents.
- Low-star reviews are oversampled (about 90 low vs 30 top per book), so expect some complaints about any aspect even for well-liked books.
