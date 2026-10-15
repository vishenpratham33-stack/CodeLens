"""Command line entry point: 
    python -m codelens crawl <folder>
    python -m codelens tokens "some text"
    python -m codelens stats <folder>
    python -m codelens search <folder> "query" [--any] [--limit N]
    python -m codelens suggest <folder> <prefix> [--limit N]
"""

import argparse
import time 

from codelens.crawler import crawl
from codelens.index import build_index
from codelens.search import find_snippet, ranked_search
from codelens.tokenizer import count_terms, tokenize
from codelens.trie import build_trie


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


def run_search(folder: str, query: str, match_any: bool, limit: int) -> None:
    start = time.perf_counter()
    index = build_index(folder)
    build_seconds = time.perf_counter() - start

    start = time.perf_counter()
    total, best = ranked_search(index, query, limit, match_any)
    search_ms = (time.perf_counter() - start) * 1000

    words = list(dict.fromkeys(tokenize(query)))
    print(f"Indexed {index.doc_count} files "
          f"({index.vocabulary_size} unique words) in {build_seconds:.2f} s")
    print(f"Found {total} file(s) for {words} in {search_ms:.3f} ms, "
          f"showing the best {len(best)}\n")

    for rank, (score, doc_id) in enumerate(best, start=1):
        path = index.docs[doc_id]["path"]
        print(f"{rank:>2}. {path}   (score {score:.2f})")
        snippet = find_snippet(folder, path, words)
        if snippet:
            print(f"     linr{snippet[0]}: {snippet[1]}")


def run_suggest(folder: str, prefix: str, limit: int) -> None:
    index = build_index(folder)
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

    crawl_cmd = commands.add_parser("crawl", help="list the files codelens would read")
    crawl_cmd.add_argument("folder", help="folder to scan")

    token_cmd = commands.add_parser("tokens", help= "show how a text is split into words")
    token_cmd.add_argument("text", help= "the text to tokenize (use quotes)")

    stats_cmd = commands.add_parser("stats", help="word statistics for a folder")
    stats_cmd.add_argument("folder", help="folder to scan")

    search_cmd = commands.add_parser("search", help="search a folder")
    search_cmd.add_argument("folder", help="folder to search in")
    search_cmd.add_argument("query", help="what to look for (use quotes)")
    search_cmd.add_argument("--any", action="store_true", help="match files with ANY word instead of ALL words")
    search_cmd.add_argument("--limit",type=int, default=10, help="how many results to show (default 10)")

    suggest_cmd = commands.add_parser("suggest", help="autocomplete a word start")
    suggest_cmd.add_argument("folder", help="folder to learn words from")
    suggest_cmd.add_argument("prefix", help="the first letter of a word")
    suggest_cmd.add_argument("--limit", type=int, default=5, help="how many suggestions (default 5)")

    args = parser.parse_args()

    if args.command == "crawl":
        run_crawl(args.folder)
    elif args.command == "tokens":
        run_tokens(args.text)
    elif args.command == "stats":
        run_stats(args.folder)
    elif args.command == "search":
        run_search(args.folder, args.query, args.any, args.limit)
    elif args.command == "suggest":
        run_suggest(args.folder, args.prefix, args.limit)


if __name__ == "__main__":
    main()