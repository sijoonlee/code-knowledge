# file discovery and type classification
from __future__ import annotations
import fnmatch
import json
import os
import re
from enum import Enum
from pathlib import Path


class FileType(str, Enum):
    CODE = "code"


_MANIFEST_PATH = "code-knowledge-out/manifest.json"

CODE_EXTENSIONS = {'.py', '.ts', '.js', '.jsx', '.tsx', '.mjs', '.ejs', '.go', '.rs', '.java', '.cpp', '.cc', '.cxx', '.c', '.h', '.hpp', '.rb', '.swift', '.kt', '.kts', '.cs', '.scala', '.php', '.lua', '.toc', '.zig', '.ps1', '.ex', '.exs', '.m', '.mm', '.jl', '.vue', '.svelte', '.dart', '.v', '.sv'}

# Files that may contain secrets - skip silently
_SENSITIVE_PATTERNS = [
    re.compile(r'(^|[\\/])\.(env|envrc)(\.|$)', re.IGNORECASE),
    re.compile(r'\.(pem|key|p12|pfx|cert|crt|der|p8)$', re.IGNORECASE),
    re.compile(r'(credential|secret|passwd|password|token|private_key)', re.IGNORECASE),
    re.compile(r'(id_rsa|id_dsa|id_ecdsa|id_ed25519)(\.pub)?$'),
    re.compile(r'(\.netrc|\.pgpass|\.htpasswd)$', re.IGNORECASE),
    re.compile(r'(aws_credentials|gcloud_credentials|service.account)', re.IGNORECASE),
]


def _is_sensitive(path: Path) -> bool:
    """Return True if this file likely contains secrets and should be skipped."""
    name = path.name
    return any(p.search(name) for p in _SENSITIVE_PATTERNS)


# Directory names to always skip - venvs, caches, build artifacts, deps
_SKIP_DIRS = {
    "venv", ".venv", "env", ".env",
    "node_modules", "__pycache__", ".git",
    "dist", "build", "target", "out",
    "site-packages", "lib64",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", ".eggs", "*.egg-info",
    "code-knowledge-out",  # never treat own output as source input
}

# Large generated files that are never useful to extract
_SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Cargo.lock", "poetry.lock", "Gemfile.lock",
    "composer.lock", "go.sum", "go.work.sum",
}

def _is_noise_dir(part: str) -> bool:
    """Return True if this directory name looks like a venv, cache, or dep dir."""
    if part in _SKIP_DIRS:
        return True
    if part.endswith("_venv") or part.endswith("_env"):
        return True
    if part.endswith(".egg-info"):
        return True
    return False


def classify_file(path: Path) -> FileType | None:
    """Classify file as CODE if it matches CODE_EXTENSIONS, else None."""
    if path.name.lower().endswith(".blade.php"):
        return FileType.CODE
    ext = path.suffix.lower()
    if ext in CODE_EXTENSIONS:
        return FileType.CODE
    return None


def _load_graphifyignore(root: Path) -> list[tuple[Path, str]]:
    """Read .graphifyignore from root and ancestor directories.

    Returns a list of (anchor_dir, pattern) pairs. Walks upward from *root*
    towards the filesystem root, stopping at a ``.git`` boundary.
    """
    patterns: list[tuple[Path, str]] = []
    current = root.resolve()
    while True:
        ignore_file = current / ".graphifyignore"
        if ignore_file.exists():
            for line in ignore_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append((current, line))
        if (current / ".git").exists():
            break
        parent = current.parent
        if parent == current:
            break
        current = parent
    return patterns


def _is_ignored(path: Path, root: Path, patterns: list[tuple[Path, str]]) -> bool:
    """Return True if path matches any .graphifyignore pattern."""
    if not patterns:
        return False

    def _matches(rel: str, p: str) -> bool:
        parts = rel.split("/")
        if fnmatch.fnmatch(rel, p):
            return True
        if fnmatch.fnmatch(path.name, p):
            return True
        for i, part in enumerate(parts):
            if fnmatch.fnmatch(part, p):
                return True
            if fnmatch.fnmatch("/".join(parts[:i + 1]), p):
                return True
        return False

    for anchor, pattern in patterns:
        p = pattern.strip("/")
        if not p:
            continue
        try:
            rel = str(path.relative_to(root)).replace(os.sep, "/")
            if _matches(rel, p):
                return True
        except ValueError:
            pass
        if anchor != root:
            try:
                rel_anchor = str(path.relative_to(anchor)).replace(os.sep, "/")
                if _matches(rel_anchor, p):
                    return True
            except ValueError:
                pass
    return False


def detect(root: Path, *, follow_symlinks: bool = False) -> dict:
    """Discover all code files under root directory."""
    root = root.resolve()
    files: list[str] = []
    skipped_sensitive: list[str] = []
    ignore_patterns = _load_graphifyignore(root)

    seen: set[Path] = set()
    all_files: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        dp = Path(dirpath)
        if follow_symlinks and os.path.islink(dirpath):
            real = os.path.realpath(dirpath)
            parent_real = os.path.realpath(os.path.dirname(dirpath))
            if parent_real == real or parent_real.startswith(real + os.sep):
                dirnames.clear()
                continue
        # Prune noise dirs in-place so os.walk never descends into them
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".")
            and not _is_noise_dir(d)
            and not _is_ignored(dp / d, root, ignore_patterns)
        ]
        for fname in filenames:
            if fname in _SKIP_FILES:
                continue
            p = dp / fname
            if p not in seen:
                seen.add(p)
                all_files.append(p)

    for p in all_files:
        if p.name.startswith("."):
            continue
        if _is_ignored(p, root, ignore_patterns):
            continue
        if _is_sensitive(p):
            skipped_sensitive.append(str(p))
            continue
        ftype = classify_file(p)
        if ftype:
            files.append(str(p))

    total_files = len(files)

    return {
        "files": files,
        "total_files": total_files,
        "skipped_sensitive": skipped_sensitive,
        "graphifyignore_patterns": len(ignore_patterns),
    }


def load_manifest(manifest_path: str = _MANIFEST_PATH) -> dict[str, float]:
    """Load the file modification time manifest from a previous run."""
    try:
        return json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_manifest(files: list[str], manifest_path: str = _MANIFEST_PATH) -> None:
    """Save current file mtimes so the next --update run can diff against them."""
    manifest: dict[str, float] = {}
    for f in files:
        try:
            manifest[f] = Path(f).stat().st_mtime
        except OSError:
            pass
    Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
    Path(manifest_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def detect_incremental(root: Path, manifest_path: str = _MANIFEST_PATH) -> dict:
    """Like detect(), but returns only new or modified files since the last run."""
    full = detect(root)
    manifest = load_manifest(manifest_path)

    if not manifest:
        full["incremental"] = True
        full["new_files"] = full["files"]
        full["unchanged_files"] = []
        full["new_total"] = full["total_files"]
        return full

    new_files: list[str] = []
    unchanged_files: list[str] = []

    for f in full["files"]:
        stored_mtime = manifest.get(f)
        try:
            current_mtime = Path(f).stat().st_mtime
        except Exception:
            current_mtime = 0
        if stored_mtime is None or current_mtime > stored_mtime:
            new_files.append(f)
        else:
            unchanged_files.append(f)

    current_files = set(full["files"])
    deleted_files = [f for f in manifest if f not in current_files]

    full["incremental"] = True
    full["new_files"] = new_files
    full["unchanged_files"] = unchanged_files
    full["new_total"] = len(new_files)
    full["deleted_files"] = deleted_files
    return full
