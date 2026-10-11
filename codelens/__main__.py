"""Command line entry point: python -m codelens crawl <folder>"""

import argparse

from codelens.crawler import crawl


def main() -> None:
    parser = argparse.ArgumentParser(prog="codelens")
    commands = parser.add_subparsers(dest="command", required=True)

    crawl_cmd = commands.add_parser("crawl", help="list the files codelens would read")
    crawl_cmd.add_argument("folder", help="folder to scan")
    args = parser.parse_args()

    if args.command == "crawl":
        count = 0
        total_bytes = 0
        for doc in crawl(args.folder):
            print(f"[{doc.doc_id:>4}] {doc.path} ({doc.size} bytes)")
            count += 1
            total_bytes += doc.size
        print(f"\nDone: {count} files, {total_bytes} bytes of text.")


if __name__ == "__main__":
        main()