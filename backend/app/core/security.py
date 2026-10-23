import os
from pathlib import Path
from typing import Set
from app.core.errors import SecurityViolationError

# Permitted extensions for generated React + Vite frontend applications
ALLOWED_EXTENSIONS: Set[str] = {
    ".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".html",
    ".svg", ".png", ".jpg", ".jpeg", ".ico", ".webp", ".gif",
    ".mp3", ".wav", ".ogg", ".webm",
    ".md", ".txt", ".gitignore", ".env", ".example", ".yaml", ".yml",
}

DISALLOWED_FILENAMES: Set[str] = {
    ".bashrc", ".profile", ".zshrc", ".bash_history",
    "id_rsa", "id_rsa.pub", ".ssh", "authorized_keys",
    "/etc/passwd", "/etc/shadow", "web.config"
}


def sanitize_relative_path(raw_path: str) -> str:
    """
    Normalizes and strictly sanitizes a relative project file path.
    Rejects directory traversal (..), null bytes, and absolute paths.
    """
    if "\x00" in raw_path:
        raise SecurityViolationError("Null byte detected in file path.")
    
    # Normalize slashes to forward slashes
    clean_path = raw_path.replace("\\", "/").strip()
    
    # Check for empty path
    if not clean_path:
        raise SecurityViolationError("File path cannot be empty.")

    # Prevent absolute root paths
    if clean_path.startswith("/") or (len(clean_path) > 1 and clean_path[1] == ":"):
        raise SecurityViolationError(f"Absolute paths are forbidden: '{raw_path}'")

    # Resolve parts and detect directory traversal attempts
    parts = [p for p in clean_path.split("/") if p and p != "."]
    if ".." in parts:
        raise SecurityViolationError(f"Directory traversal ('..') is strictly forbidden: '{raw_path}'")

    sanitized = "/".join(parts)
    
    # Validate filename
    basename = parts[-1].lower()
    if basename in DISALLOWED_FILENAMES:
        raise SecurityViolationError(f"Disallowed system filename: '{basename}'")

    # Extension check
    suffix = Path(basename).suffix.lower()
    if suffix and suffix not in ALLOWED_EXTENSIONS:
        raise SecurityViolationError(f"File extension '{suffix}' is not permitted in generated projects.")

    return sanitized


def validate_workspace_path(base_dir: Path, target_path: Path) -> Path:
    """
    Validates that a resolved target path strictly resides within the base directory.
    Throws SecurityViolationError if path traversal or symlink breakout is detected.
    """
    resolved_base = base_dir.resolve()
    resolved_target = target_path.resolve()

    if not resolved_target.is_relative_to(resolved_base):
        raise SecurityViolationError(
            f"Path breakout attempt detected. Target '{resolved_target}' is outside base '{resolved_base}'."
        )

    return resolved_target
