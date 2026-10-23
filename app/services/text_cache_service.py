"""Text cache service for extracted document text and DOCX HTML."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Optional

from app.services.extraction_service import extract_text
from app.utils.config import UPLOAD_DIR


# Cache directory for extracted text and HTML
TEXT_CACHE_DIR = UPLOAD_DIR.parent / "text_cache"
TEXT_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Max characters for text content
MAX_TEXT_CHARS = 500_000


def _cache_path(doc_id: int, suffix: str = ".txt") -> Path:
    """Get the cache file path for a document."""
    return TEXT_CACHE_DIR / f"{doc_id}{suffix}"


def _file_hash(path: Path) -> str:
    """Compute SHA256 hash of a file for cache invalidation."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_cache_meta(doc_id: int) -> Optional[dict]:
    """Load cache metadata (file hash, etc.)."""
    meta_path = _cache_path(doc_id, ".meta.json")
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text())
        except Exception:
            return None
    return None


def _save_cache_meta(doc_id: int, file_hash: str) -> None:
    """Save cache metadata."""
    meta_path = _cache_path(doc_id, ".meta.json")
    meta_path.write_text(json.dumps({"file_hash": file_hash}))


def invalidate_text_cache(doc_id: int) -> None:
    """Invalidate all cached text and HTML for a document."""
    for suffix in [".txt", ".html", ".meta.json"]:
        path = _cache_path(doc_id, suffix)
        if path.exists():
            path.unlink(missing_ok=True)


def get_cached_text(doc_id: int, stored_path: str, file_type: str) -> tuple[str, bool]:
    """
    Get extracted text, using cache if valid.
    Returns (text, truncated).
    """
    path = Path(stored_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {stored_path}")

    current_hash = _file_hash(path)
    cached_meta = _load_cache_meta(doc_id)

    # Check if cache is valid
    if cached_meta and cached_meta.get("file_hash") == current_hash:
        cache_file = _cache_path(doc_id, ".txt")
        if cache_file.exists():
            text = cache_file.read_text(encoding="utf-8")
            return text, len(text) >= MAX_TEXT_CHARS

    # Cache miss or invalid - extract fresh
    text = extract_text(stored_path, file_type)
    text = normalize_text(text)

    # Truncate if needed
    truncated = False
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]
        truncated = True

    # Save to cache
    cache_file = _cache_path(doc_id, ".txt")
    cache_file.write_text(text, encoding="utf-8")
    _save_cache_meta(doc_id, current_hash)

    return text, truncated


def normalize_text(text: str) -> str:
    """
    Normalize extracted text:
    - Collapse excessive blank lines (more than 2 -> 2)
    - Fix hyphenated line breaks in PDFs where safe
    - Keep paragraph breaks
    """
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Fix hyphenated line breaks (word-\nword -> wordword)
    # Only when it's clearly a word break: lowercase + hyphen + newline + lowercase
    import re
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Collapse excessive blank lines (3+ newlines -> 2 newlines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip trailing whitespace from each line
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()


def get_cached_html(doc_id: int, stored_path: str, file_type: str) -> str:
    """
    Get DOCX as sanitized HTML, using cache if valid.
    Only works for DOCX files.
    """
    if file_type.lower() != "docx":
        raise ValueError("HTML conversion only supported for DOCX files")

    path = Path(stored_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {stored_path}")

    current_hash = _file_hash(path)
    cached_meta = _load_cache_meta(doc_id)

    # Check if cache is valid
    if cached_meta and cached_meta.get("file_hash") == current_hash:
        cache_file = _cache_path(doc_id, ".html")
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")

    # Cache miss or invalid - convert fresh
    html = convert_docx_to_html(stored_path)
    html = sanitize_html(html)

    # Save to cache
    cache_file = _cache_path(doc_id, ".html")
    cache_file.write_text(html, encoding="utf-8")
    _save_cache_meta(doc_id, current_hash)

    return html


def convert_docx_to_html(stored_path: str) -> str:
    """Convert DOCX to HTML using mammoth."""
    import mammoth

    with open(stored_path, "rb") as f:
        result = mammoth.convert_to_html(f)
        return result.value


def sanitize_html(html: str) -> str:
    """Sanitize HTML to allow only safe elements."""
    import nh3

    # Allowed tags and attributes
    allowed_tags = {
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "br",
        "ul", "ol", "li",
        "table", "thead", "tbody", "tr", "th", "td",
        "strong", "em", "b", "i",
        "a",
        "img",
        "div", "span",
    }

    allowed_attributes = {
        "a": {"href", "rel", "target"},
        "img": {"src", "alt", "width", "height"},
        "*": {"style"},  # Allow style on all elements for basic formatting
    }

    # Custom attribute filter for links
    def filter_attributes(tag: str, attrs: dict) -> dict:
        filtered = {}
        if tag == "a":
            href = attrs.get("href", "")
            # Only allow safe URLs
            if href.startswith("http://") or href.startswith("https://") or href.startswith("mailto:"):
                filtered["href"] = href
                filtered["rel"] = "noopener noreferrer"
                filtered["target"] = "_blank"
        elif tag == "img":
            src = attrs.get("src", "")
            # Only allow data URIs for images (embedded), with size cap
            if src.startswith("data:image/"):
                # Check size (base64 encoded, rough estimate)
                if len(src) < 500_000:  # ~500KB limit
                    filtered["src"] = src
                    if "alt" in attrs:
                        filtered["alt"] = attrs["alt"]
                    if "width" in attrs:
                        filtered["width"] = attrs["width"]
                    if "height" in attrs:
                        filtered["height"] = attrs["height"]
        else:
            # Allow style attribute
            if "style" in attrs:
                filtered["style"] = attrs["style"]
        return filtered

    return nh3.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attributes,
        attribute_filter=filter_attributes,
    )