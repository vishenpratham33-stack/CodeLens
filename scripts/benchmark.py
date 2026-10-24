"""Measure CodeLens on a pile of generated files.

    python scripts/benchmark.py 10000
"""
import os
import random
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from codelens.search import ranked_search  # noqa: E402
from codelens.storage import index_path  # noqa: E402
from codelens.updater import update_index  # noqa: E402

SYLLABLES = ["ka", "to", "ri", "me", "su", "la", "no", "vi", "pe", "da", "ro", "xi", "bu", "fa", "gen", "tor", "ter", "ing"]


def make_vocabulary(size: int, rng: random.Random):
    words = set()
    while len(words) < size:
        words.add("".join(rng.choice(SYLLABLES) for _ in range(rng.randint(2, 4))))
    return sorted(words)


def make_files(folder: Path, count: int, vocab, rng: random.Random) -> int:
    weights = [1 / (rank + 1) for rank in range(len(vocab))]  # a few common words, many rare
    tokens = 0
    for number in range(count):
        words = rng.choices(vocab, weights, k=rng.randint(150, 400))
        tokens += len(words)
        lines = [f"def {words[i]}_{words[i + 1]}({words[i + 2]}): return {words[i + 3]}"
                 for i in range(0, len(words) - 4, 4)]
        (folder / f"file_{number:06d}.py").write_text("\n".join(lines), encoding="utf-8")
    return tokens


def main() -> None:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    rng = random.Random(42)
    folder = Path(tempfile.mkdtemp(prefix="codelens_bench_"))
    try:
        vocab = make_vocabulary(5000, rng)
        started = time.perf_counter()
        tokens = make_files(folder, count, vocab, rng)
        print(f"(made {count} files, {tokens:,} words, in {time.perf_counter() - started:.1f} s)")

        started = time.perf_counter()
        index, _ = update_index(str(folder))
        build = time.perf_counter() - started
        size_mb = index_path(str(folder)).stat().st_size / 1e6

        started = time.perf_counter()
        update_index(str(folder))
        reload = time.perf_counter() - started

        started = time.perf_counter()
        update_index(str(folder), current=index)
        in_memory = time.perf_counter() - started

        for number in rng.sample(range(count), min(50, count)):
            path = folder / f"file_{number:06d}.py"
            path.write_text(path.read_text(encoding="utf-8") + "\ndef extra_change(): pass\n", encoding="utf-8")
            os.utime(path, (time.time() + 5, time.time() + 5))
        started = time.perf_counter()
        update_index(str(folder))
        update = time.perf_counter() - started

        queries = []
        for _ in range(300):
            queries.append(" ".join(rng.choices(vocab[:200] + vocab, k=rng.randint(1, 3))))
        timings = []
        for query in queries:
            t0 = time.perf_counter()
            ranked_search(index, query, 10)
            timings.append((time.perf_counter() - t0) * 1000)
        timings.sort()

        print()
        print("| What | Result |")
        print("|---|---|")
        print(f"| Files | {count:,} |")
        print(f"| Words indexed | {tokens:,} |")
        print(f"| First build (read + tokenize + index + save) | {build:.1f} s |")
        print(f"| Saved index size | {size_mb:.1f} MB |")
        print(f"| Start-up with a saved index, nothing changed | {reload:.2f} s |")
        print(f"| Check for changes, index already in memory | {in_memory:.2f} s |")
        print(f"| Update after changing 50 files | {update:.2f} s |")
        print(f"| Search, median (300 random queries) | {statistics.median(timings):.2f} ms |")
        print(f"| Search, 95th percentile | {timings[int(len(timings) * 0.95)]:.2f} ms |")
    finally:
        shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    main()