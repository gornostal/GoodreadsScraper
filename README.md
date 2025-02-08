## Installation

For crawling, install [`requirements.txt`](./requirements.txt)

```
# Creates a virtual environment
virtualenv gscraper

# This may vary depending on your shell
. gscraper/bin/activate

pip3 install -r requirements.txt
```

### List Crawls

Run the following command to crawl all books from the first 50 pages of a Listopia list (say 1.Best_Books_Ever):

```bash
python3 crawl.py list \
  --list_name="1.Best_Books_Ever" \
  --start_page=1 \
  --end_page=50 \
  --output_file_suffix="best_001_050"
```

This will

1. crawl the first 50 pages of [this list](https://www.goodreads.com/list/show/1.Best_Books_Ever), which is ~5k books, and
1. store all books in a file called `book_best_001_050.jl`, and all authors in a file called `author_best_001_050.jl`.

The paging approach avoids hitting the Goodreads site too heavily. You should also ideally set the `DOWNLOAD_DELAY` to at least 1.

Use `python3 crawl.py list --help` for all options and defaults.

## Filter Configuration

Modify filters to your taste in WebUI/server.py

### Web UI

```bash
python webui.py
```
