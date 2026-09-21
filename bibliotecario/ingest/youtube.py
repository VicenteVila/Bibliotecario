"""Ingesta YouTube vía yt-dlp: metadata + subtítulos (VTT/SRT). Sin dependencia de Node."""
from __future__ import annotations

import logging
import re
import urllib.parse

from bibliotecario.ingest.base import Document
from bibliotecario.ingest.url import detect_language

logger = logging.getLogger(__name__)
_SUB_LANGS = ("es", "es-ES", "es-419", "en", "en-US", "en-GB")


def video_id(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    if "youtube.com" in host:
        return urllib.parse.parse_qs(parsed.query).get("v", [None])[0]
    if "youtu.be" in host:
        return parsed.path.lstrip("/").split("?")[0] or None
    return None


def _parse_vtt(content: str) -> list[str]:
    texts, cur_start, cur = [], 0, []
    for line in content.split("\n"):
        line = line.strip()
        if "-->" in line:
            try:
                start = line.split("-->")[0].strip().split(":")
                cur_start = int(start[-2]) * 60 + int(start[-1].split(".")[0])
            except (ValueError, IndexError):
                pass
        elif line and not line.startswith(("WEBVTT", "NOTE")) and not line.startswith("<"):
            clean = re.sub(r"<[^>]+>", "", line).strip()
            if clean:
                cur.append(clean)
        elif cur:
            texts.append(f"[{cur_start // 60:02d}:{cur_start % 60:02d}] {' '.join(cur)}")
            cur = []
    if cur:
        texts.append(f"[{cur_start // 60:02d}:{cur_start % 60:02d}] {' '.join(cur)}")
    return texts


def _parse_srt_url(content: str) -> list[str]:
    texts = []
    for line in content.split("\n"):
        line = line.strip()
        if not line or "-->" in line or line.isdigit():
            continue
        texts.append(line)
    return texts


def _download_subs(subs: list[dict]) -> str:
    import requests

    for entry in subs[:3]:
        sub_url = entry.get("url", "")
        if not sub_url:
            continue
        try:
            resp = requests.get(sub_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            if not resp.ok:
                continue
            ctype = resp.headers.get("Content-Type", "").lower()
            if "vtt" in ctype or sub_url.endswith(".vtt"):
                texts = _parse_vtt(resp.text)
            else:
                texts = _parse_srt_url(resp.text)
            if texts:
                return "\n".join(texts)
        except Exception as e:
            logger.warning("Descarga de subtítulo falló: %s", e)
    return ""


def extract_youtube(url: str) -> Document:
    import yt_dlp

    opts = {"quiet": True, "skip_download": True,
            "writesubtitles": True, "writeautomaticsub": True,
            "subtitleslangs": list(_SUB_LANGS)}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    title = info.get("title", "") or url
    description = info.get("description", "") or ""
    subs, auto = info.get("subtitles", {}), info.get("automatic_captions", {})
    chosen = next((subs[l] for l in _SUB_LANGS if subs.get(l)), None)
    if not chosen:
        chosen = next((auto[l] for l in _SUB_LANGS if auto.get(l)), None)
    if not chosen and auto:
        chosen = auto[next(iter(auto))]
    transcript = _download_subs(chosen) if chosen else ""
    body = f"TRANSCRIPCIÓN:\n{transcript}" if transcript else f"DESCRIPCIÓN:\n{description}"
    if not body.strip():
        raise ValueError("Sin contenido extraíble del vídeo")
    meta = {"uploader": info.get("uploader", ""), "duration": info.get("duration", 0),
            "view_count": info.get("view_count", 0), "upload_date": info.get("upload_date", ""),
            "has_transcript": bool(transcript)}
    return Document(source=url, source_type="youtube", title=title[:200], text=body,
                    language=detect_language(body), metadata=meta)
