"""Command line entry point.
    python -m codelens crawl <folder>
    python -m codelens tokens "some text"
    python -m codelens stats <folder>
    python -m codelens search <folder> "query" [--any] [--phrase] [--limit N]
    python -m codelens suggest <folder> <prefix> [--limit N]
    python -m codelens index <folder> [--rebuild]
    python -m codelens serve [--host H] [--port N] [--data-dir D] [--folder F]
"""

import argparse
import time 

from codelens.crawler import crawl
from codelens.search import find_snippet, ranked_phrase_search, ranked_search
from codelens.tokenizer import count_terms, tokenize
from codelens.trie import build_trie
from codelens.typo import correct_words
from codelens.updater import UpdateReport, update_index


def describe(report: UpdateReport, seconds: float) -> str:
    """One readable ;ine about what happend to the saved index."""
    if report.mode == "build":
        return f"Index built: {report.added} files in {seconds:.2f} s"
    if report.mode == "updated":
        return (f"Index updated in {seconds:.2f} s (+{report.added} new, "f"~{report.changed} changed, -{report.removed} removed")
    return f"Index loaded from disk in {seconds:.2f} s, nothing changed"


def run_crawl(folder: str) -> None:
    count = 0
    total_bytes = 0
    for doc in crawl(folder):
        print(f"[{doc.doc_id:>4}]  {doc.path} ({doc.size} bytes)")
        count += 1
        total_bytes += doc.size
    print(f"\nDone: {count} files, {total_bytes} bytes of text.")


def run_tokens(text: str) -> None:
     print(tokenize(text))


def run_stats(folder: str) -> None:
    all_counts = {}
    total_tokens = 0
    files = 0
    for doc in crawl(folder):
        tokens = tokenize(doc.text)
        total_tokens += len(tokens)
        files += 1
        for word, n in count_terms(tokens).items():
            all_counts[word] = all_counts.get(word, 0) + n

    print(f"Files read:      {files}")
    print(f"Total tokens:    {total_tokens}")
    print(f"Unique words     {len(all_counts)}")
    print("\nTop 10 words:")
    top = sorted(all_counts.items(), key = lambda pair: pair[1], reverse = True)[:10]
    for word, n in top:
            print(f"  {word:<15} {n}")


def run_search(folder: str, query: str, match_any: bool, limit: int, phrase: bool, rebuild: bool) -> None:
    start = time.perf_counter()
    index, report = update_index(folder, rebuild)
    build_seconds = time.perf_counter() - start

    typed = tokenize(query)
    fixed, changes = correct_words(index, typed)
    search_text = " ".join(fixed)

    start = time.perf_counter()
    if phrase:
        total, best = ranked_phrase_search(index, search_text, limit)
    else:
        total, best = ranked_search(index, search_text, limit, match_any)
    search_ms = (time.perf_counter() - start) * 1000

    words = list(dict.fromkeys(fixed))
    print(f"Indexed {index.doc_count} files "
          f"({index.vocabulary_size} unique words) in {build_seconds:.2f} s")
    for typed_word, new_word in changes:
        print(f"No match for '{typed_word}', showing results for '{new_word}' ")
    kind = "the phrase" if phrase else "the words"
    print(f"Found {total} file(s) with {kind} {words} in {search_ms:.3f} ms, "
          f"showing the best {len(best)}\n")

    for rank, (score, doc_id) in enumerate(best, start=1):
        path = index.docs[doc_id]["path"]
        print(f"{rank:>2}. {path}   (score {score:.2f})")
        snippet = find_snippet(folder, path, words)
        if snippet:
            print(f"     line {snippet[0]}: {snippet[1]}")


def run_index(folder: str, rebuild: bool) -> None:
    start = time.perf_counter()
    index, report = update_index(folder, rebuild)
    seconds = time.perf_counter() - start
    print(describe(report, seconds))
    print(f"{index.doc_count} files, {index.vocabulary_size} unique words.")


def lan_address() -> str:
    """The address of this computer on the local network (for phones)."""
    import socket
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))       
        return probe.getsockname()[0]
    except OSError:
        return "your-computer-address"
    finally:
        probe.close()


def run_serve(host: str, port: int, data_dir: str, folder: str) -> None:
    import uvicorn
    from codelens.api.server import create_app
    from codelens.paths import web_dir
    app = create_app(data_dir, shared_folder=folder, web_dir=web_dir())
    print(f"CodeLens is running at http://{host}:{port}  (stop with Ctrl + C)", flush=True)
    if host == "0.0.0.0":
        print(f"From a phone on the same Wi-Fi, open http://{lan_address()}:{port}")
        print("Warning: this connection is not encrypted. Use a network you trust.")
    uvicorn.run(app, host=host, port=port)


def run_suggest(folder: str, prefix: str, limit: int) -> None:
    index, _ = update_index(folder)
    trie = build_trie(index)
    words = trie.suggest(prefix.lower(), limit)
    if not words:
        print(f"No words start with '{prefix}'.")
        return
    print(f"Words starting with '{prefix}':")
    for word in words:
        print(f"   {word:<20} in {index.doc_frequency(word)} file(s)")


def main() -> None:
    parser = argparse.ArgumentParser(prog="codelens")
    commands = parser.add_subparsers(dest="command", required=True)

    crawl_cmd = commands.add_parser("crawl", help="list the files Codelens would read")
    crawl_cmd.add_argument("folder", help="folder to scan")

    token_cmd = commands.add_parser("tokens", help= "show how a text is split into words")
    token_cmd.add_argument("text", help= "the text to tokenize (use quotes)")

    stats_cmd = commands.add_parser("stats", help="word statistics for a folder")
    stats_cmd.add_argument("folder", help="folder to scan")

    search_cmd = commands.add_parser("search", help="search a folder")
    search_cmd.add_argument("folder", help="folder to search in")
    search_cmd.add_argument("query", help="what to look for (use quotes)")
    search_cmd.add_argument("--any", action="store_true", help="match files with ANY word instead of ALL words")
    search_cmd.add_argument("--phrase", action="store_true", help="the words must appear next to each other, in order")
    search_cmd.add_argument("--limit",type=int, default=10, help="how many results to show (default 10)")
    search_cmd.add_argument("--rebuild", action="store_true", help="ignore the saved index and built it again")

    suggest_cmd = commands.add_parser("suggest", help="autocomplete a word start")
    suggest_cmd.add_argument("folder", help="folder to learn words from")
    suggest_cmd.add_argument("prefix", help="the first letter of a word")
    suggest_cmd.add_argument("--limit", type=int, default=5, help="how many suggestions (default 5)")

    index_cmd = commands.add_parser("index", help="build or update the saved index")
    index_cmd.add_argument("folder", help="folder to index")
    index_cmd.add_argument("--rebuild", action="store_true", help="ignore the saved index and build it again")

    serve_cmd = commands.add_parser("serve", help="start the web server")
    serve_cmd.add_argument("--host", default="127.0.0.1", help="127.0.0.1 = this computer only (default)")
    serve_cmd.add_argument("--port", type=int, default=8000)
    serve_cmd.add_argument("--data-dir", default="codelens_data", help="where accounts and user files are kept")
    serve_cmd.add_argument("--folder", default=None, help="search this existing folder for every user (no uploads)")

    args = parser.parse_args()

    if args.command == "crawl":
        run_crawl(args.folder)
    elif args.command == "tokens":
        run_tokens(args.text)
    elif args.command == "stats":
        run_stats(args.folder)
    elif args.command == "search":
        run_search(args.folder, args.query, args.any, args.limit, args.phrase, args.rebuild)
    elif args.command == "suggest":
        run_suggest(args.folder, args.prefix, args.limit)
    elif args.command == "index":
        run_index(args.folder, args.rebuild)
    elif args.command == "serve":
        run_serve(args.host, args.port, args.data_dir, args.folder)


if __name__ == "__main__":
    main()