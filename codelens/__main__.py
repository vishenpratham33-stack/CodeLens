"""Command line entry point: 
    python -m codelens crawl <folder>
    python -m codelens tokens "some text"
    python -m codelens stats <folder>
"""

import argparse

from codelens.crawler import crawl
from codelens.tokenizer import count_terms, tokenize

def run_crawl(folder: str) -> None:
    count = 0
    total_bytes = 0
    for doc in crawl(folder):
        print(f"[{doc.doc_id:>4}] {doc.path} ({doc.size} bytes)")
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
    print(f"files read:      {files}")
    print(f"total tokens:    {total_tokens}")
    print(f"Unique words     {len(all_counts)}")
    print("\nTop 10 words:")
    top = sorted(all_counts.items(), key = lambda pair: pair[1], reverse = True)[:10]
    for word, n in top:
            print(f"  {word:<15}{n}")

def main() -> None:
    parser = argparse.ArgumentParser(prog="codelens")
    commands = parser.add_subparsers(dest="command", required=True)

    crawl_cmd = commands.add_parser("crawl", help="list the files codelens would read")
    crawl_cmd.add_argument("folder", help="folder to scan")

    token_cmd = commands.add_parser("tokens", help= "show how a text is split into words")
    token_cmd.add_argument("text", help= "the text to tokenize (use quotes)")

    stats_cmd = commands.add_parser("stats", help="word statistics for a folder")
    stats_cmd.add_argument("folder", help="folder to scan")

    args = parser.parse_args()

    if args.command == "crawl":
        run_crawl(args.folder)
    elif args.command == "tokens":
        run_tokens(args.text)
    elif args.command == "stats":
        run_stats(args.folder)

if __name__ == "__main__":
    main()