# per-file extraction cache - skip unchanged files on re-run
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def _body_content(content: bytes) -> bytes:
    """Strip YAML frontmatter from Markdown content, returning only the body."""
    text = content.decode(errors="replace")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].encode()
    return content


def file_hash(path: Path, root: Path = Path(".")) -> str:
    """SHA256 of file contents + path relative to root.

    Using a relative path (not absolute) makes cache entries portable across
    machines and checkout directories, so shared caches and CI work correctly.
    Falls back to the resolved absolute path if the file is outside root.

    For Markdown files (.md), only the body below the YAML frontmatter is hashed,
    so metadata-only changes (e.g. reviewed, status, tags) do not invalidate the cache.
    """
    p = Path(path)
    if not p.is_file():
        raise IsADirectoryError(f"file_hash requires a file, got: {p}")
    raw = p.read_bytes()
    content = _body_content(raw) if p.suffix.lower() == ".md" else raw
    h = hashlib.sha256()
    h.update(content)
    h.update(b"\x00")
    try:
        rel = p.resolve().relative_to(Path(root).resolve())
        h.update(str(rel).encode())
    except ValueError:
        h.update(str(p.resolve()).encode())
    return h.hexdigest()


def cache_dir(root: Path = Path(".")) -> Path:
    """Returns cache directory relative to root.

    If root is already the code-knowledge-out directory, returns root/cache.
    Otherwise returns root/code-knowledge-out/cache.
    """
    d = Path(root).resolve()
    if d.name == "code-knowledge-out":
        d = d / "cache"
    else:
        d = d / "code-knowledge-out" / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_cached(path: Path, root: Path = Path(".")) -> dict | None:
    """Return cached extraction for this file if hash matches, else None.

    Cache key: SHA256 of file contents.
    Cache value: stored as code-knowledge-out/cache/{hash}.json
    Returns None if no cache entry or file has changed.
    """
    try:
        h = file_hash(path, root)
    except OSError:
        return None
    entry = cache_dir(root) / f"{h}.json"
    if not entry.exists():
        return None
    try:
        return json.loads(entry.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_cached(path: Path, result: dict, root: Path = Path(".")) -> None:
    """Save extraction result for this file.

    Stores as code-knowledge-out/cache/{hash}.json where hash = SHA256 of current file contents.
    result should be a dict with 'nodes' and 'edges' lists.

    No-ops if `path` is not a regular file.
    """
    p = Path(path)
    if not p.is_file():
        return
    h = file_hash(p, root)
    entry = cache_dir(root) / f"{h}.json"
    tmp = entry.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(result), encoding="utf-8")
        try:
            os.replace(tmp, entry)
        except PermissionError:
            # Windows: os.replace can fail with WinError 5 if the target is
            # briefly locked. Fall back to copy-then-delete.
            import shutil
            shutil.copy2(tmp, entry)
            tmp.unlink(missing_ok=True)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def cached_files(root: Path = Path(".")) -> set[str]:
    """Return set of file paths that have a valid cache entry (hash still matches)."""
    d = cache_dir(root)
    return {p.stem for p in d.glob("*.json")}


def clear_cache(root: Path = Path(".")) -> None:
    """Delete all code-knowledge-out/cache/*.json files."""
    d = cache_dir(root)
    for f in d.glob("*.json"):
        f.unlink()
