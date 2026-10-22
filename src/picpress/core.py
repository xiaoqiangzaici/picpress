"""PicPress core engine — compress images to an exact target file size.

The engine is UI-agnostic: it powers both the desktop app and the MCP server.
Strategy: binary-search encoder parameters (quality, then optional downscale)
until the encoded output fits the user-requested size.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

from PIL import Image, ImageOps

__all__ = [
    "CompressResult",
    "CompressionError",
    "compact_label",
    "format_size",
    "parse_size",
    "compress_to_target",
    "probe_min_size",
    "image_info",
    "SUPPORTED_INPUT",
    "UNIT_CHOICES",
]

# ---------------------------------------------------------------- constants

UNIT_CHOICES: tuple[str, ...] = ("B", "KB", "MB")

_UNIT_BYTES = {
    "B": 1,
    "KB": 1024,
    "MB": 1024 * 1024,
}

SUPPORTED_INPUT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}

# Encoder quality band. Bottom is "worst acceptable", top is "visually lossless".
MIN_QUALITY = 5
MAX_QUALITY = 95

# Downscale floor — below ~12% of the original the image is usually useless.
MIN_SCALE = 0.05


class CompressionError(Exception):
    """Raised for invalid input (bad unit, unreadable file, ...)."""


# ---------------------------------------------------------------- utilities


def parse_size(value: float | int | str, unit: str = "KB") -> int:
    """Convert a human size (``(250, 'KB')`` or ``'1.5MB'``) to bytes."""
    if isinstance(value, str):
        text = value.strip().replace(" ", "")
        num = ""
        unit_part = ""
        for ch in text:
            if ch.isdigit() or ch == ".":
                if unit_part:
                    raise CompressionError(f"Invalid size string: {value!r}")
                num += ch
            else:
                unit_part += ch
        if not num:
            raise CompressionError(f"Invalid size string: {value!r}")
        value = float(num)
        unit = unit_part or unit

    unit = (unit or "B").strip().upper()
    if unit not in _UNIT_BYTES:
        raise CompressionError(
            f"Unknown unit {unit!r}, expected one of {', '.join(UNIT_CHOICES)}"
        )
    bytes_ = float(value) * _UNIT_BYTES[unit]
    if bytes_ <= 0:
        raise CompressionError("Target size must be positive")
    return int(round(bytes_))


def format_size(num_bytes: float | int) -> str:
    """Human-readable size, e.g. ``1.2 MB`` / ``348 KB`` / ``912 B``."""
    num = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if unit == "B":
            if num < 1024:
                return f"{int(num)} B"
        elif num < 1024 or unit == "GB":
            return f"{num:.2f} {unit}" if num < 10 else f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.2f} GB"


def compact_label(num_bytes: int) -> str:
    """Compact size label for file names: ``900B`` / ``500KB`` / ``1.5MB``."""
    n = int(num_bytes)
    for unit, factor in (("MB", 1024 ** 2), ("KB", 1024)):
        if n >= factor:
            val = n / factor
            if abs(val - round(val)) < 1e-9:
                return f"{int(round(val))}{unit}"
            return f"{val:.1f}{unit}"
    return f"{n}B"


# Output extensions allowed per output format.
_ALLOWED_EXT = {
    "jpeg": {".jpg", ".jpeg", ".jpe"},
    "png": {".png"},
    "webp": {".webp"},
}
_DEFAULT_EXT = {"jpeg": ".jpg", "png": ".png", "webp": ".webp"}


def _resolve_ext(fmt: str, ext: str | None) -> str:
    """Validate/derive the file extension for ``fmt``."""
    if ext:
        e = str(ext).lower()
        if not e.startswith("."):
            e = f".{e}"
        if e in _ALLOWED_EXT.get(fmt, set()):
            return e
    return _DEFAULT_EXT[fmt]


def _sanitize_label(label: str) -> str:
    """Strip characters Windows forbids in file names."""
    cleaned = "".join(ch for ch in label if ch not in '<>:"/\\|?*').strip()
    return cleaned or "compressed"


def unique_path(path: Path) -> Path:
    """Return ``path`` or a ``name (2).ext`` style variant that does not exist.

    Keeps repeated runs (same source, same target) from overwriting each other,
    the way Windows Explorer de-duplicates names.
    """
    if not path.exists():
        return path
    stem, ext = path.stem, path.suffix
    for i in range(2, 1000):
        candidate = path.with_name(f"{stem} ({i}){ext}")
        if not candidate.exists():
            return candidate
    raise CompressionError(f"Too many files named like {path.name}")


# ---------------------------------------------------------------- results


@dataclass
class CompressResult:
    """Outcome of one compression attempt."""

    status: str  # "ok" | "target_too_large" | "unreachable" | "error"
    message: str
    source_path: str = ""
    output_path: str | None = None
    original_bytes: int = 0
    target_bytes: int = 0
    final_bytes: int | None = None
    quality: int | None = None
    scale: float = 1.0
    output_format: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @property
    def saved_bytes(self) -> int:
        if self.final_bytes is None:
            return 0
        return max(0, self.original_bytes - self.final_bytes)

    @property
    def saved_ratio(self) -> float:
        if not self.original_bytes or self.final_bytes is None:
            return 0.0
        return 1.0 - self.final_bytes / self.original_bytes

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "message": self.message,
            "source_path": self.source_path,
            "output_path": self.output_path,
            "original_bytes": self.original_bytes,
            "original_size": format_size(self.original_bytes),
            "target_bytes": self.target_bytes,
            "target_size": format_size(self.target_bytes),
            "final_bytes": self.final_bytes,
            "final_size": format_size(self.final_bytes) if self.final_bytes else None,
            "saved_bytes": self.saved_bytes,
            "saved_ratio": round(self.saved_ratio, 4),
            "quality": self.quality,
            "scale": round(self.scale, 4),
            "output_format": self.output_format,
            "warnings": list(self.warnings),
        }


# ---------------------------------------------------------------- engine


def _encode(img: Image.Image, fmt: str, quality: int, scale: float) -> bytes:
    """Encode ``img`` at ``quality``/``scale`` and return raw file bytes."""
    work = img
    if scale < 0.999:
        w, h = img.size
        work = img.resize(
            (max(1, int(w * scale)), max(1, int(h * scale))),
            Image.Resampling.LANCZOS,
        )

    buf = io.BytesIO()
    if fmt == "jpeg":
        if work.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", work.size, (255, 255, 255))
            rgba = work.convert("RGBA")
            background.paste(rgba, mask=rgba.split()[-1])
            work = background
        elif work.mode != "RGB":
            work = work.convert("RGB")
        work.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    elif fmt == "webp":
        work.save(buf, "WEBP", quality=quality, method=6)
    elif fmt == "png":
        # PNG has no quality knob; emulate it via palette size.
        colors = max(2, min(256, int(quality * 256 / MAX_QUALITY)))
        if work.mode not in ("P", "RGB", "RGBA"):
            work = work.convert("RGBA" if "A" in work.getbands() else "RGB")
        quantized = work.quantize(colors=colors, method=Image.Quantize.FASTOCTREE)
        quantized.save(buf, "PNG", optimize=True)
    else:
        raise CompressionError(f"Unsupported output format: {fmt}")
    return buf.getvalue()


def _best_fit(
    img: Image.Image,
    fmt: str,
    target_bytes: int,
    allow_resize: bool,
    min_quality: int = MIN_QUALITY,
    max_quality: int = MAX_QUALITY,
) -> tuple[bytes, int, float] | None:
    """Find the largest quality (optionally smallest downscale) that fits.

    Returns ``(data, quality, scale)`` or ``None`` when the target is
    unreachable within the allowed parameter space.
    """

    def search_quality(scale: float) -> tuple[bytes, int] | None:
        lo, hi = min_quality, max_quality
        best: tuple[bytes, int] | None = None
        while lo <= hi:
            mid = (lo + hi) // 2
            data = _encode(img, fmt, mid, scale)
            if len(data) <= target_bytes:
                best = (data, mid)
                lo = mid + 1  # try higher quality
            else:
                hi = mid - 1
        return best

    found = search_quality(1.0)
    if found is not None:
        return found[0], found[1], 1.0

    if not allow_resize:
        return None

    # Binary-search the largest scale (least visual damage) that can fit.
    lo, hi = MIN_SCALE, 0.99
    best: tuple[bytes, int, float] | None = None
    for _ in range(8):  # ~0.4% scale precision
        mid = (lo + hi) / 2
        found = search_quality(mid)
        if found is not None:
            best = (found[0], found[1], mid)
            lo = mid  # try to keep it bigger
        else:
            hi = mid
    return best


def compress_to_target(
    source: str | os.PathLike,
    target: float | int | str,
    unit: str = "KB",
    output: str | os.PathLike | None = None,
    output_format: str = "auto",
    allow_resize: bool = False,
    keep_metadata: bool = False,
    progress: Callable[[float, str], None] | None = None,
    output_dir: str | os.PathLike | None = None,
    output_ext: str | None = None,
    include_target_in_name: bool = True,
    size_label: str | None = None,
) -> CompressResult:
    """Compress one image so its file size is at most ``target`` (in ``unit``).

    The output is never larger than the source — if the requested size is not
    smaller than the original file, the call returns ``status='target_too_large'``
    and writes nothing.

    Output naming (when ``output`` is not given)::

        <source-stem>_<target><ext>      e.g. photo_500KB.jpg

    and if that name already exists, ``photo_500KB (2).jpg`` follows, so the
    same photo compressed to 100 KB and 200 KB never collide. Pass an explicit
    ``output`` path to control the name yourself.
    """
    src = Path(source)
    if not src.is_file():
        return CompressResult("error", f"File not found: {src}", source_path=str(src))

    try:
        target_bytes = parse_size(target, unit)
    except CompressionError as exc:
        return CompressResult("error", str(exc), source_path=str(src))

    original_bytes = src.stat().st_size

    if target_bytes >= original_bytes:
        return CompressResult(
            status="target_too_large",
            message=(
                f"Target {format_size(target_bytes)} is not smaller than the original "
                f"{format_size(original_bytes)} — nothing to compress. "
                f"Choose a smaller target."
            ),
            source_path=str(src),
            target_bytes=target_bytes,
            original_bytes=original_bytes,
        )

    if progress:
        progress(0.05, "Loading image")

    try:
        with Image.open(src) as im:
            img = ImageOps.exif_transpose(im)
            img.load()
            has_alpha = "A" in img.getbands()
            src_format = (im.format or "").lower()
            exif = im.info.get("exif") if keep_metadata else None
            # Work on a plain copy so the file handle can close.
            work = img.copy()
    except Exception as exc:  # noqa: BLE001 - Pillow raises many types
        return CompressResult(
            "error", f"Cannot read image: {exc}", source_path=str(src),
            original_bytes=original_bytes, target_bytes=target_bytes,
        )

    fmt = output_format.lower()
    if fmt in ("jpg", "jpeg"):
        fmt = "jpeg"
    elif fmt == "auto":
        fmt = "webp" if has_alpha else "jpeg"
    if fmt not in ("jpeg", "webp", "png"):
        return CompressResult(
            "error", f"Unsupported output format: {output_format}",
            source_path=str(src), original_bytes=original_bytes,
            target_bytes=target_bytes,
        )

    ext = _resolve_ext(fmt, output_ext)
    if output is not None:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        base_dir = Path(output_dir) if output_dir else src.parent
        base_dir.mkdir(parents=True, exist_ok=True)
        label = _sanitize_label(size_label or compact_label(target_bytes))
        base_name = (f"{src.stem}_{label}" if include_target_in_name
                     else f"{src.stem}_compressed")
        out_path = unique_path(base_dir / f"{base_name}{ext}")

    if progress:
        progress(0.15, "Searching encoder settings")

    fit = _best_fit(work, fmt, target_bytes, allow_resize)

    if fit is None:
        # Report the smallest thing we *can* make, so the user can decide.
        smallest = _encode(work, fmt, MIN_QUALITY, MIN_SCALE if allow_resize else 1.0)
        return CompressResult(
            status="unreachable",
            message=(
                f"Cannot reach {format_size(target_bytes)} without ruining the image. "
                f"Smallest achievable: {format_size(len(smallest))} "
                f"(quality {MIN_QUALITY}"
                f"{', scaled down' if allow_resize else ''}). "
                f"Try a larger target, or allow downscaling."
            ),
            source_path=str(src),
            target_bytes=target_bytes,
            original_bytes=original_bytes,
            final_bytes=len(smallest),
            quality=MIN_QUALITY,
            scale=MIN_SCALE if allow_resize else 1.0,
            output_format=fmt,
        )

    data, quality, scale = fit
    if progress:
        progress(0.85, "Writing output")

    if exif:
        try:
            Image.open(io.BytesIO(data)).save(out_path, exif=exif)
            data = out_path.read_bytes()
        except Exception:  # noqa: BLE001 - metadata is best-effort
            out_path.write_bytes(data)
    else:
        out_path.write_bytes(data)

    final_bytes = out_path.stat().st_size
    warnings: list[str] = []
    if scale < 0.999:
        w, h = work.size
        warnings.append(
            f"Image downscaled to {max(1, int(w * scale))}x{max(1, int(h * scale))} "
            f"({scale * 100:.0f}%) to reach the target"
        )
    if fmt != (src_format or fmt) and src_format:
        warnings.append(f"Converted {src_format} -> {fmt}")

    if progress:
        progress(1.0, "Done")

    return CompressResult(
        status="ok",
        message=(
            f"{format_size(original_bytes)} -> {format_size(final_bytes)} "
            f"(-{100 - final_bytes / original_bytes * 100:.1f}%), "
            f"target {format_size(target_bytes)} met"
        ),
        source_path=str(src),
        output_path=str(out_path),
        original_bytes=original_bytes,
        target_bytes=target_bytes,
        final_bytes=final_bytes,
        quality=quality,
        scale=scale,
        output_format=fmt,
        warnings=warnings,
    )


def probe_min_size(
    source: str | os.PathLike,
    allow_resize: bool = False,
    output_format: str = "auto",
) -> dict:
    """Report the smallest file this engine can produce for ``source``."""
    src = Path(source)
    if not src.is_file():
        raise CompressionError(f"File not found: {src}")
    with Image.open(src) as im:
        img = ImageOps.exif_transpose(im)
        img.load()
        has_alpha = "A" in img.getbands()
        work = img.copy()

    fmt = output_format.lower()
    if fmt in ("jpg", "jpeg"):
        fmt = "jpeg"
    elif fmt == "auto":
        fmt = "webp" if has_alpha else "jpeg"
    if fmt not in ("jpeg", "webp", "png"):
        raise CompressionError(f"Unsupported output format: {output_format}")

    data = _encode(work, fmt, MIN_QUALITY, MIN_SCALE if allow_resize else 1.0)
    return {
        "source_path": str(src),
        "original_bytes": src.stat().st_size,
        "original_size": format_size(src.stat().st_size),
        "min_bytes": len(data),
        "min_size": format_size(len(data)),
        "output_format": fmt,
        "allow_resize": allow_resize,
    }


def image_info(source: str | os.PathLike) -> dict:
    """Basic metadata for one image file."""
    src = Path(source)
    if not src.is_file():
        raise CompressionError(f"File not found: {src}")
    with Image.open(src) as im:
        width, height = im.size
        fmt = (im.format or "").lower()
        mode = im.mode
    size = src.stat().st_size
    return {
        "source_path": str(src),
        "file_name": src.name,
        "width": width,
        "height": height,
        "format": fmt,
        "mode": mode,
        "bytes": size,
        "size": format_size(size),
    }


def compress_many(
    sources: Sequence[str | os.PathLike],
    target: float | int | str,
    unit: str = "KB",
    output_dir: str | os.PathLike | None = None,
    output_format: str = "auto",
    allow_resize: bool = False,
    keep_metadata: bool = False,
    progress: Callable[[float, str], None] | None = None,
    output_ext: str | None = None,
    include_target_in_name: bool = True,
    size_label: str | None = None,
) -> list[CompressResult]:
    """Compress a batch of images; each file gets its own result row."""
    results: list[CompressResult] = []
    items = list(sources)
    for i, source in enumerate(items):
        def one_progress(p: float, msg: str, index: int = i) -> None:
            if progress:
                progress((index + p) / max(1, len(items)), msg)

        results.append(
            compress_to_target(
                source, target, unit,
                output_dir=output_dir,
                output_format=output_format,
                allow_resize=allow_resize,
                keep_metadata=keep_metadata,
                progress=one_progress,
                output_ext=output_ext,
                include_target_in_name=include_target_in_name,
                size_label=size_label,
            )
        )
    return results
