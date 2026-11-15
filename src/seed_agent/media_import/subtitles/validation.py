"""Validate subtitle payloads without extraction or changes to source bytes."""

import io
import math
import re
import unicodedata
import zipfile
from pathlib import PurePosixPath

MAX_BYTES = 2_000_000


def normalized_release(value):
    """Ignore format/separators only; retain every identity/version token."""
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"(?i)\.(?:mkv|mp4|avi|m4v|ts|mov|webm|srt|ass|ssa|vtt)$", "", value)
    return re.sub(r"[\W_]", "", value).casefold()


def cue_evidence(text, fmt):
    """Return actual cue timestamps/dialogue, excluding metadata and comments."""
    timestamps, dialogue = [], []
    clock = r"(?:\d{1,2}:)?\d{2}:\d{2}[,.]\d{2,3}"
    if fmt == "ass":
        in_events, columns = False, None
        for raw in text.splitlines():
            line = raw.strip()
            if line.startswith("["):
                in_events = line.casefold() == "[events]"
            elif in_events and line.casefold().startswith("format:"):
                columns = [v.strip().casefold() for v in line.split(":", 1)[1].split(",")]
                if not {"start", "end", "text"}.issubset(columns) or columns[-1] != "text":
                    raise ValueError("unsupported ASS event format")
            elif in_events and line.casefold().startswith("dialogue:"):
                if not columns:
                    raise ValueError("ASS event format is missing")
                values = line.split(":", 1)[1].split(",", len(columns) - 1)
                if len(values) != len(columns):
                    raise ValueError("invalid ASS dialogue")
                start, end = (values[columns.index(k)].strip() for k in ("start", "end"))
                body = re.sub(r"\{[^{}]*\}", "", values[-1])
                if not body.strip():
                    continue
                timestamps.append((start, end))
                dialogue.append(body)
    else:
        arrow = re.compile(rf"^[ \t]*({clock})[ \t]+-->[ \t]+({clock})(?:[ \t]+[^\r\n]*)?$")
        for block in re.split(r"\n[ \t]*\n", text.replace("\r\n", "\n")):
            lines = block.strip().splitlines()
            if not lines or (fmt == "vtt" and lines[0].startswith(("NOTE", "STYLE", "REGION"))):
                continue
            matches = [(i, arrow.fullmatch(line)) for i, line in enumerate(lines) if "-->" in line]
            if not matches:
                continue
            if len(matches) != 1 or matches[0][1] is None:
                raise ValueError("invalid subtitle cue timing line")
            index, match = matches[0]
            body = re.sub(r"<[^<>]*>", "", "\n".join(lines[index + 1 :]))
            if body.strip():
                timestamps.append(match.groups())
                dialogue.append(body)
    for start, end in timestamps:
        if not re.fullmatch(clock, start) or not re.fullmatch(clock, end):
            raise ValueError("invalid cue timestamp")
    return timestamps, "\n".join(dialogue)


def validate(
    payload: bytes,
    *,
    duration: float,
    require_full_timeline: bool = False,
    expected_language: str | None = None,
) -> tuple[bytes, str]:
    if not isinstance(duration, int | float) or not math.isfinite(duration) or duration <= 0:
        raise ValueError("media duration is unknown")
    if not payload or len(payload) > MAX_BYTES:
        raise ValueError("subtitle size out of bounds")
    if payload.startswith(b"PK"):
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > 5 or sum(i.file_size for i in entries) > MAX_BYTES:
                raise ValueError("archive bounds exceeded")
            for item in entries:
                p = PurePosixPath(item.filename)
                if (
                    p.is_absolute()
                    or ".." in p.parts
                    or "\\" in item.filename
                    or item.flag_bits & 1
                ):
                    raise ValueError("unsafe archive path/encryption")
                if (item.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("archive symlink")
                if item.compress_size and item.file_size / item.compress_size > 100:
                    raise ValueError("archive expansion ratio exceeded")
            subtitles = [
                i
                for i in entries
                if PurePosixPath(i.filename).suffix.lower() in {".srt", ".ass", ".vtt"}
            ]
            if len(subtitles) != 1:
                raise ValueError("ambiguous archive subtitle")
            payload = archive.read(subtitles[0])
    text = None
    for encoding in ["utf-8-sig", "utf-16", "gb18030", "big5"]:
        try:
            decoded = payload.decode(encoding)
            if "\x00" not in decoded:
                text = decoded
                break
        except UnicodeError:
            continue
    if text is None or re.search(r'(?i)<(?:html|!doctype|script)|"error"\s*:', text):
        raise ValueError("not a subtitle payload")
    fmt = (
        "ass"
        if "[Events]" in text and "[Script Info]" in text
        else ("vtt" if text.startswith("WEBVTT") else "srt")
    )
    evidence_text = text
    if require_full_timeline:
        cues, evidence_text = cue_evidence(text, fmt)
        timing_text = " ".join(
            "00:" + value if value.count(":") == 1 else value for pair in cues for value in pair
        )
    else:
        timing_text = text
    timestamps = re.findall(r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{2,3})", timing_text)
    if len(timestamps) < 2:
        raise ValueError("subtitle contains no bounded timestamps")
    times = []
    for h, m, s, ms in timestamps:
        if int(m) > 59 or int(s) > 59:
            raise ValueError("invalid subtitle timestamp")
        times.append(
            int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / (100 if len(ms) == 2 else 1000)
        )
    if require_full_timeline and any(times[i] >= times[i + 1] for i in range(0, len(times), 2)):
        raise ValueError("subtitle cue end must follow its start")
    if (
        require_full_timeline
        and fmt != "ass"
        and any(times[i] < times[i - 2] for i in range(2, len(times), 2))
    ):
        raise ValueError("subtitle cues must be ordered")
    if max(times) > duration + 120:
        raise ValueError("subtitle timing exceeds media; end time does not prove synchronization")
    if require_full_timeline:
        # This is a bounded compatibility check, not dialogue synchronization proof.
        # Permit ordinary opening/end credits, but reject fragments and short editions.
        tolerance = min(300, max(120, duration * 0.05), duration * 0.2)
        if min(times) > tolerance or max(times) < duration - tolerance:
            raise ValueError("subtitle timeline does not cover media duration")
        if duration >= 600 and len(timestamps) < 20:
            raise ValueError("subtitle has insufficient full-length timing evidence")
        letters = [c for c in evidence_text if c.isalpha()]
        han = sum("\u3400" <= c <= "\u9fff" for c in letters)
        latin = sum("a" <= c.casefold() <= "z" for c in letters)
        if expected_language in {"zh", "zh-Hans", "zh-Hant"} and (
            han < 10 or han / max(len(letters), 1) < 0.1
        ):
            raise ValueError("subtitle text does not corroborate declared Chinese language")
        if expected_language == "en" and latin / max(len(letters), 1) < 0.5:
            raise ValueError("subtitle text does not corroborate declared English language")
    if fmt in {"srt", "vtt"} and "-->" not in text:
        raise ValueError("invalid subtitle cue syntax")
    return text.replace("\r\n", "\n").encode("utf-8"), fmt


def compatibility(candidate, mapping, source, profile):
    """Return evidence ordered before language/popularity; explicit mismatch always rejects."""
    if candidate.tmdb_id is not None and candidate.tmdb_id != mapping["tmdb_id"]:
        return None, "work_id_conflict"
    if candidate.imdb_id and mapping.get("imdb_id") and candidate.imdb_id != mapping["imdb_id"]:
        return None, "work_id_conflict"
    exact = candidate.tmdb_id == mapping["tmdb_id"] or (
        candidate.imdb_id and candidate.imdb_id == mapping.get("imdb_id")
    )
    if not exact:
        return None, "missing_work_identity"
    if mapping["media_type"] != "movie" and (
        candidate.season != mapping.get("season")
        or tuple(candidate.episodes) != tuple(mapping.get("episodes", []))
    ):
        return None, "episode_conflict"
    if candidate.kind != profile.subtitle_kind:
        return None, "kind_conflict"
    edition = mapping.get("edition")
    release = re.sub(r"[._-]+", " ", candidate.release.casefold()).replace("’", "'")
    explicit = candidate.edition
    if not explicit:
        for token, label in [
            (r"\bextended\b", "Extended"),
            (r"\bunrated\b", "Unrated"),
            (r"\bdirector(?:'?s)?\s*cut\b", "Director's Cut"),
        ]:
            if re.search(token, release):
                explicit = label
    if explicit and explicit != edition:
        return None, "edition_conflict"
    if edition and explicit != edition and not candidate.hash_match:
        return None, "edition_unproven"
    probe = source.get("probe", {})
    if candidate.fps and probe.get("fps") and abs(candidate.fps - probe["fps"]) > 0.1:
        return None, "fps_conflict"

    release_match = bool(
        candidate.release
        and normalized_release(candidate.release) == normalized_release(source["original_release"])
    )
    if not candidate.hash_match and not release_match:
        duration = probe.get("duration")
        if (
            profile.subtitle_kind == "full"
            and isinstance(duration, int | float)
            and math.isfinite(duration)
            and duration > 0
        ):
            # Identity is established above. Fetch privately so timeline evidence
            # can be checked before publication, without per-candidate approval.
            candidate.match_basis = "work_matched_pending_timing"
            return (
                0,
                0,
                int(bool(candidate.fps)),
                int(candidate.trusted),
                candidate.rating or 0,
                candidate.downloads or 0,
            ), candidate.match_basis
        candidate.match_basis = "needs_preview"
        return (0, 0, candidate.rating or 0, candidate.downloads or 0), "version_unproven"
    candidate.match_basis = "hash_matched" if candidate.hash_match else "release_matched"
    return (
        int(candidate.hash_match),
        int(release_match),
        int(bool(candidate.fps)),
        int(candidate.trusted),
        candidate.rating or 0,
        candidate.downloads or 0,
    ), candidate.match_basis


def compatible(candidate, mapping, source, profile):
    return compatibility(candidate, mapping, source, profile)[0]
