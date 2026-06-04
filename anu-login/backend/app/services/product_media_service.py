from __future__ import annotations

import codecs
import hashlib
import json
import mimetypes
import re
import shutil
import uuid
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from app.config import settings


PRODUCT_MEDIA_DIRNAME = "product_media"
DEFAULT_IMAGE_MIME = "image/jpeg"
DEFAULT_PUBLIC_GOOGLE_DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/1E4OaYgsngarvS63yNscrRs1NtIxRBvs8?usp=sharing"
GOOGLE_DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"
GOOGLE_DRIVE_DOWNLOAD_URL = "https://drive.google.com/uc?export=download&id={file_id}"


def product_media_root() -> Path:
    """Return the writable root directory for product media assets."""
    root = settings.database_path.parent / PRODUCT_MEDIA_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", (value or "").lower().strip())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or "product"


def _safe_filename(filename: str, fallback_stem: str) -> str:
    stem = Path(filename or "").stem.strip() or fallback_stem
    ext = Path(filename or "").suffix.lower()
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", stem).strip("-_.") or fallback_stem
    if ext and len(ext) <= 10:
        return f"{stem}{ext}"
    return stem


def _infer_extension(filename: str, content_type: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext:
        return ext if len(ext) <= 10 else ".jpg"

    guessed = mimetypes.guess_extension((content_type or "").split(";", 1)[0].strip() or DEFAULT_IMAGE_MIME)
    if guessed == ".jpe":
        return ".jpg"
    return guessed or ".jpg"


def _public_base_url() -> str:
    base = (settings.public_base_url or "").strip().rstrip("/")
    return base or ""


def to_public_url(url: str) -> str:
    """Convert a relative media path into a public HTTPS URL if needed."""
    raw = (url or "").strip()
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    base = _public_base_url()
    if not base:
        return raw
    return f"{base}/{raw.lstrip('/')}"


def build_relative_media_url(product_key: str, filename: str) -> str:
    slug = _slugify(product_key)
    safe_name = urllib.parse.quote(filename)
    return f"/api/product-media/{slug}/{safe_name}"


def _image_hash(seed: str) -> str:
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]


def normalize_product_image_entries(value: Any) -> list[dict[str, Any]]:
    """Normalize catalog image metadata into a consistent list of dicts."""
    if not value:
        return []

    items = value if isinstance(value, list) else [value]
    normalized: list[dict[str, Any]] = []

    for index, raw in enumerate(items):
        entry: dict[str, Any]
        if isinstance(raw, dict):
            url = str(raw.get("url") or raw.get("public_url") or raw.get("path") or "").strip()
            filename = str(raw.get("filename") or raw.get("name") or "").strip()
            entry = {
                "id": str(raw.get("id") or _image_hash(f"{url}|{filename}|{index}")),
                "url": url,
                "filename": filename,
                "caption": str(raw.get("caption") or "").strip(),
                "source": str(raw.get("source") or "upload").strip() or "upload",
                "source_url": str(raw.get("source_url") or "").strip(),
                "is_primary": bool(raw.get("is_primary", False)),
                "sort_order": int(raw.get("sort_order") or index),
                "mime_type": str(raw.get("mime_type") or "").strip(),
                "size_bytes": int(raw.get("size_bytes") or 0),
                "uploaded_at": str(raw.get("uploaded_at") or "").strip(),
                "updated_at": str(raw.get("updated_at") or "").strip(),
            }
        else:
            url = str(raw or "").strip()
            entry = {
                "id": _image_hash(f"{url}|{index}"),
                "url": url,
                "filename": "",
                "caption": "",
                "source": "url" if url.startswith(("http://", "https://")) else "upload",
                "source_url": url,
                "is_primary": index == 0,
                "sort_order": index,
                "mime_type": "",
                "size_bytes": 0,
                "uploaded_at": "",
                "updated_at": "",
            }

        if entry["url"]:
            normalized.append(entry)

    normalized.sort(key=lambda item: (not bool(item.get("is_primary")), int(item.get("sort_order") or 0), item.get("id", "")))
    return normalized


def product_image_urls(images: Any) -> list[str]:
    """Return public URLs for the supplied image metadata."""
    normalized = normalize_product_image_entries(images)
    return [to_public_url(item.get("url", "")) for item in normalized if item.get("url")]


def primary_product_image_url(images: Any) -> str:
    normalized = normalize_product_image_entries(images)
    if not normalized:
        return ""
    primary = next((item for item in normalized if item.get("is_primary")), normalized[0])
    return to_public_url(primary.get("url", ""))


def save_product_image_bytes(
    *,
    product_key: str,
    content: bytes,
    filename: str = "",
    content_type: str = "",
    caption: str = "",
    source: str = "upload",
    source_url: str = "",
    is_primary: bool = False,
    sort_order: int = 0,
) -> dict[str, Any]:
    """Persist an uploaded image to disk and return its normalized metadata."""
    slug = _slugify(product_key)
    product_dir = product_media_root() / slug
    product_dir.mkdir(parents=True, exist_ok=True)

    image_id = f"img_{uuid.uuid4().hex[:12]}"
    extension = _infer_extension(filename, content_type)
    safe_name = _safe_filename(filename or f"{image_id}{extension}", image_id)
    if not safe_name.lower().endswith(extension.lower()):
        safe_name = f"{safe_name}{extension}"

    final_name = f"{image_id}_{safe_name}"
    file_path = product_dir / final_name
    file_path.write_bytes(content)

    relative_url = build_relative_media_url(slug, final_name)
    return {
        "id": image_id,
        "url": relative_url,
        "filename": final_name,
        "caption": caption.strip(),
        "source": source,
        "source_url": source_url.strip(),
        "is_primary": bool(is_primary),
        "sort_order": int(sort_order),
        "mime_type": content_type.strip() or DEFAULT_IMAGE_MIME,
        "size_bytes": len(content),
        "uploaded_at": "",
        "updated_at": "",
    }


def save_product_image_from_url(
    *,
    product_key: str,
    image_url: str,
    caption: str = "",
    source: str = "url",
    is_primary: bool = False,
    sort_order: int = 0,
) -> dict[str, Any]:
    """Download a remote image URL to local storage and return its metadata."""
    normalized_url = (image_url or "").strip()
    if not normalized_url:
        raise ValueError("Image URL is required.")

    parsed = urllib.parse.urlparse(normalized_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Image URL must be http or https.")

    request = urllib.request.Request(
        normalized_url,
        headers={
            "User-Agent": "PureLevenProductMedia/1.0",
            "Accept": "image/*,*/*;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
        content = response.read()
        content_type = response.headers.get_content_type() if hasattr(response, "headers") else DEFAULT_IMAGE_MIME
        remote_name = Path(parsed.path or "image.jpg").name or "image.jpg"

    return save_product_image_bytes(
        product_key=product_key,
        content=content,
        filename=remote_name,
        content_type=content_type,
        caption=caption,
        source=source,
        source_url=normalized_url,
        is_primary=is_primary,
        sort_order=sort_order,
    )


def delete_product_image_file(image_entry: dict[str, Any]) -> bool:
    """Delete the stored file for a catalog image entry if it is local."""
    url = str(image_entry.get("url") or "").strip()
    filename = str(image_entry.get("filename") or "").strip()
    if not url or url.startswith(("http://", "https://")):
        return False

    path = Path(settings.database_path.parent / PRODUCT_MEDIA_DIRNAME)
    product_part = Path(url.lstrip("/")).parts
    if len(product_part) >= 4:
        relative = Path(*product_part[2:])
        file_path = path / relative
    else:
        file_path = path / filename

    if file_path.exists():
        file_path.unlink()
        return True
    return False


def delete_product_media_collection(product_key: str) -> None:
    """Remove the entire local media directory for a product."""
    product_dir = product_media_root() / _slugify(product_key)
    if product_dir.exists():
        shutil.rmtree(product_dir, ignore_errors=True)


def _drive_folder_id(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Google Drive folder URL is required.")

    if re.fullmatch(r"[A-Za-z0-9_-]{10,}", raw):
        return raw

    parsed = urllib.parse.urlparse(raw)
    if "drive.google.com" not in parsed.netloc:
        raise ValueError("Google Drive folder URL is invalid.")

    match = re.search(r"/folders/([A-Za-z0-9_-]+)", parsed.path)
    if match:
        return match.group(1)

    query_id = urllib.parse.parse_qs(parsed.query).get("id", [""])[0].strip()
    if query_id:
        return query_id

    raise ValueError("Could not find a Google Drive folder id in the URL.")


def _decode_drive_ivd_payload(html: str) -> list[Any]:
    start_marker = "window['_DRIVE_ivd'] = '"
    end_marker = "';if (window['_DRIVE_ivdc'])"
    start = html.find(start_marker)
    if start == -1:
        raise ValueError("Google Drive folder payload not found.")
    start += len(start_marker)
    end = html.find(end_marker, start)
    if end == -1:
        raise ValueError("Google Drive folder payload is incomplete.")

    raw_payload = html[start:end]
    decoded = codecs.decode(raw_payload, "unicode_escape")
    payload = json.loads(decoded)
    if not isinstance(payload, list):
        raise ValueError("Unexpected Google Drive folder payload.")
    return payload


def _drive_mobile_folder_url(folder_id: str) -> str:
    return f"https://drive.google.com/drive/mobile/folders/{folder_id}?usp=sharing"


def _drive_download_url(file_id: str) -> str:
    return GOOGLE_DRIVE_DOWNLOAD_URL.format(file_id=file_id)


def list_public_google_drive_folder_entries(folder_url_or_id: str) -> list[dict[str, Any]]:
    """Return child entries for a public Google Drive folder."""
    folder_id = _drive_folder_id(folder_url_or_id)
    request = urllib.request.Request(
        _drive_mobile_folder_url(folder_id),
        headers={
            "User-Agent": "Mozilla/5.0 (PureLevenProductMedia)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
        html = response.read().decode("utf-8", errors="replace")

    payload = _decode_drive_ivd_payload(html)
    entries = payload[0] if payload and isinstance(payload[0], list) else []
    results: list[dict[str, Any]] = []

    for entry in entries:
        if not isinstance(entry, list) or len(entry) < 4:
            continue
        file_id = str(entry[0] or "").strip()
        name = str(entry[2] or "").strip()
        mime_type = str(entry[3] or "").strip()
        if not file_id or not name:
            continue
        results.append(
            {
                "id": file_id,
                "name": name,
                "mime_type": mime_type,
                "is_folder": mime_type == GOOGLE_DRIVE_FOLDER_MIME,
                "download_url": _drive_download_url(file_id),
                "folder_url": f"https://drive.google.com/drive/folders/{file_id}",
            }
        )
    return results
