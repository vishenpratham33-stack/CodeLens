# CodeLens

![tests](https://github.com/vishenpratham33-stack/CodeLens/actions/workflows/tests.yml/badge.svg)

**Live demo:** https://YOUR-SERVICE.onrender.com  (fictional sample files; the free server sleeps when idle, so the first load can take about a minute)

A search engine for code and documents, **built from scratch in Python**: no search library, every data structure written by hand.
Type a word or phrase you remember, and CodeLens finds the file: it **finds your files by itself** (Documents, Desktop, Downloads), reads code, text, PDF, Word and Excel, and gives ranked results with typo correction, autocomplete and phrase search. Works from a command line, a web page, or as an installed app.

<!-- Put a screenshot or a short GIF of the search bar here. This is the single most useful thing in the README. -->
![CodeLens screenshot](docs/screenshot.png)

## What it does

- **Ranked search** (TF-IDF): rare words count more than common ones.
- **Typo tolerance**: `invertd` finds `inverted`, with a "showing results for..." line.
- **Phrase search**: `"sliding window"` only matches the words side by side, in order.
- **Autocomplete** while you type.
- **Understands code names**: `getUserName` and `max_file_size` are split into words, so `user name` finds `getUserName`.
- **Finds your files by itself** ("My files" mode): no uploading. It indexes in the background, and you can search while it works.
- **Reads** `.py .js .java .md .txt ...`, plus **PDF, Word and Excel**.
- **Open or download** a result straight from the page.
- **Installable** on laptops, phones and tablets (PWA), and reachable from other devices through a private network.
- **Fast restarts**: the index is saved to disk and only changed files are read again.
- **Accounts and security**: hashed passwords, signed tokens, rate limiting, one private workspace per user.
- **A flexible search bar**: drag it, resize it, shrink it to a small orb; six switchable animated backgrounds.

## Quick start

You need Python 3.10 or newer. Run every command **inside the project folder** (the one that contains the `codelens` folder).

```bash
git clone https://github.com/vishenpratham33-stack/CodeLens.git
cd CodeLens
python -m venv .venv
.venv\Scripts\activate            # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

**Find your own files** (Documents, Desktop and Downloads, chosen automatically):

```bash
python -m codelens serve --my-files
```

Open http://127.0.0.1:8000, create an account (first time only), and type a word you remember.

**Or search specific folders.** Replace the example with a folder that really exists on your computer (use the quotes if the path has spaces):

```bash
python -m codelens serve --folder "C:\Users\YOURNAME\Documents\Projects"
```

`--folder` can be repeated. If a folder does not exist, CodeLens says so and stops.

Command line only:

```bash
python -m codelens search . "inverted index"
python -m codelens search . "sliding window" --phrase
python -m codelens suggest . tok
```

Other ways to run it:

| Way | How |
|---|---|
| Docker (demo with sample files) | `docker build -t codelens .` then `docker run -p 8000:8000 codelens` |
| Your own web link (Render) | see "Deploy a demo" below |
| Windows / Mac / Linux app | download it from the Releases page and double-click: it finds your files by itself |
| Phone or tablet, same Wi-Fi | `python -m codelens serve --my-files --host 0.0.0.0`, then open the address it prints |
| Phone or tablet, anywhere | put the computer and the phone on a private network (Tailscale), open the page over HTTPS, then "Install app" |

## Troubleshooting

| What you see | Why | Fix |
|---|---|---|
| "These folders do not exist on this computer" | the path in the command is an example, not a real folder | use a real folder, or `--my-files` |
| "No module named codelens" | you are not inside the project folder | `cd` into the folder that contains `codelens` |
| "No module named fastapi" (or pypdf...) | libraries not installed in the virtual environment | activate `.venv`, then `pip install -r requirements.txt` |
| "Looking for files..." for a while | the first scan of a big folder | you can search already; it finishes in the background |
| Open button missing | you use the page from another device | by design: "Open" works only on the computer where CodeLens runs. Use Download |
| Searching `fastapi` does not find `FastAPI` | camelCase words are split into *fast* and *api* | type the word as written, `FastAPI`, for now |

## Deploy a demo (free link on Render)

The repository contains a `Dockerfile` and a `render.yaml`. The deployed demo searches a set of fictional sample files in `sample_docs/`, with a ready-made demo account, so anybody can try it without installing anything.

1. On render.com: **New, Blueprint** (or **New, Web Service** with the Docker runtime), and connect this repository.
2. Accept the settings from `render.yaml`. Render builds the image and gives you an address like `https://codelens-xxxx.onrender.com`.
3. Put that address at the top of this README.

Suggested searches for the demo: `invoice`, `sliding window` (tick *phrase*), `masala chai`, `budget rent`, `goa beach`, `electricty` (a typo).
Free servers sleep when idle and forget accounts and data when they restart, which is fine for a demo. For private files, run CodeLens on your own computer instead.

## How it works

```
files --> crawler --> reader (text, PDF, Word, Excel) --> tokenizer --> inverted index --> saved to disk
                                                                              |
query --> tokenizer --> typo fix --> posting lists intersected --> TF-IDF --> heap (top K) --> results
```

| Part | Data structure or algorithm |
|---|---|
| Crawler | tree traversal (DFS) with pruning, generators |
| Index | hash map of hash maps, positional postings |
| Multi-word search | two-pointer intersection and merge of sorted lists |
| Ranking | TF-IDF, hand-written min-heap for the top K |
| Autocomplete | trie |
| Typos | edit distance (dynamic programming, early stop) |
| Phrases | positional index |
| Rate limiter | sliding window over a queue |
| Updates | change detection by size and modified date |

## Security

| Threat | Defence |
|---|---|
| Stolen user file | passwords stored only as scrypt hashes, with a random salt |
| Password guessing | slow hash, login rate limits, same answer for a wrong user and a wrong password |
| Forged login | tokens signed with HMAC-SHA256, with an expiry |
| Reading other people's files | one workspace per user; clients never choose a server path |
| Path tricks (`../`, shortcuts) | every path is resolved and checked to be inside the workspace |
| Malicious file names or sizes | file name checks (path tricks refused), type allow-list, size limits |
| Opening files from outside | "Open" works only for requests from the same computer (not through a tunnel); only indexed files can be opened or downloaded |
| Cloud-only files | OneDrive "online only" files are skipped so indexing never triggers a download |
| Script injection in the page | results drawn as text, never as HTML; Content-Security-Policy |
| Corrupt files | readers return nothing instead of crashing |

## Performance

Measured with `python scripts/benchmark.py 10000` on my own computer:

| What | Result |
|---|---|
| Files | 10,000 |
| Words indexed | 2,738,551 |
| First build (read + tokenize + index + save) | 168.4 s |
| Saved index size | 30.9 MB |
| Start-up with a saved index, nothing changed | 13.80 s |
| Check for changes, index already in memory | 10.19 s |
| Update after changing 50 files | 23.87 s |
| Search, median (300 random queries) | 0.20 ms |
| Search, 95th percentile | 2.67 ms |

## Honest limits

- The index lives in memory and is saved as one JSON file. For millions of files a database would be the next step.
- The server is plain HTTP. Put it behind HTTPS before using it over the internet.
- Scanned PDFs (pictures of pages) have no text and are not searchable.
- Typo search compares against the whole vocabulary, which is fine for thousands of words, not millions.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

162 Python tests, plus a browser-style check of the page, run on every push with GitHub Actions.

## License

MIT
