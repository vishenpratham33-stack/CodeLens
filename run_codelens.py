"""Double-click launcher: CodeLens finds your files by itself and opens the browser."""

import argparse
import socket
import threading
import webbrowser
from pathlib import Path


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))              # port 0 = "give me any free port"
        return probe.getsockname()[1]


def pick_folder():
    """Fallback: ask for a folder, if Documents, Desktop and Downloads were not found."""
    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        chosen = filedialog.askdirectory(title="CodeLens: choose the folder to search")
        root.destroy()
        return chosen or None
    except Exception:
        return None


def main() -> None:
    import uvicorn
    from codelens.api.server import create_app
    from codelens.library import Library, default_roots
    from codelens.paths import web_dir

    parser = argparse.ArgumentParser(description="CodeLens: find your files by typing what you remember")
    parser.add_argument("--folder", action="append", help="a folder to search (can be repeated)")
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser")
    args = parser.parse_args()

    roots = list(args.folder or []) or default_roots()
    if not roots:
        chosen = pick_folder()
        roots = [chosen] if chosen else []
    data_dir = Path.home() / ".codelens_app"
    library = Library(roots, data_dir / "library") if roots else None
    if library:
        library.start()
    app = create_app(data_dir, library=library, web_dir=web_dir())
    port = free_port()
    url = f"http://127.0.0.1:{port}"
    print(f"CodeLens is running at {url}", flush=True)
    for root in (library.roots if library else []):
        print("Finding files in:", root, flush=True)
    print("Close this window to stop.", flush=True)
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
