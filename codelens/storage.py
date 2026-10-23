import json
import os
from pathlib import Path
from typing import Optional

from codelens import config
from codelens.index import InvertedIndex

FORMAT_VERSION = 1


def index_path(folder: str) -> Path:
    return Path(folder).resolve() / config.INDEX_DIR_NAME / config.INDEX_FILE_NAME


def save_index(index: InvertedIndex, folder: str) -> Path:
    path = index_path(folder)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {"version": FORMAT_VERSION, **index.to_dict()}
    temp = path.with_name(path.name + ".tmp")
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"))
    os.replace(temp, path)         
    return path


def load_index(folder: str) -> Optional[InvertedIndex]:
    try:
        with open(index_path(folder), "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if payload.get("version") != FORMAT_VERSION:
            return None
        return InvertedIndex.from_dict(payload)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None     
