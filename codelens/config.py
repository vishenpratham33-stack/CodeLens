"""Settings for CodeLens. Change them here, nowhere else."""

# only files with these endings are read. Everything else is skipped.
ALLOWED_EXTENSIONS ={
    ".py", ".js", ".ts",".java", ".c", ".cpp", ".h", ".cs"
, ".go", ".rs", ".html", ".css", ".json", ".md", ".txt", "sql", ".yml", ".yaml",
}

#  Folders we never enter. they hold generated or third-party files.
IGNORED_DIRS = {
    ".git", "node_modules", "_pycache_", "venv", ".venv", "env", "dist", "build", ".idea", ".vscode", ".pytest_cache",
}

# Files bigger than this are skipped (1 MB). Protects memory and speed.
MAX_FILE_SIZE_BYTES =1_000_000

# Words shorter than this are dropped when tokenizing ("a","x","l").
MIN_TOKEN_LENGTH = 2

#Very common english words. Only removed if you ask for it (see tokenizer.py)
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or", "the", "to", "to", "with",
}