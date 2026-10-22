"""PicPress MCP server — expose target-size image compression to AI agents.

Run over stdio so any MCP client (Claude Desktop/Code, WorkBuddy, Cursor,
VS Code, ...) can launch it as a local subprocess::

    python -m picpress.mcp_server          # or the picpress-mcp.exe binary

Client configuration example (``mcp.json`` / ``claude_desktop_config.json``)::

    {
      "mcpServers": {
        "picpress": {
          "command": "picpress-mcp.exe",
          "args": []
        }
      }
    }
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from .core import (
    SUPPORTED_INPUT,
    UNIT_CHOICES,
    compress_many,
    compress_to_target,
    format_size,
    image_info,
    parse_size,
    probe_min_size,
)

SERVER_NAME = "picpress"

server = MCPServer(
    SERVER_NAME,
    instructions=(
        "PicPress compresses images to an exact user-chosen file size. "
        "Use compress_image for one file, batch_compress for many. "
        "Targets must be smaller than the original file: if the requested size "
        "is not smaller, the result status is 'target_too_large' and no file is "
        "written. Sizes use units B, KB (1024 B) or MB (1024 KB)."
    ),
)

_FMT_MAP = {"auto": "auto", "jpeg": "jpeg", "jpg": "jpeg",
            "webp": "webp", "png": "png"}


def _normalize_format(output_format: str) -> str:
    fmt = _FMT_MAP.get(output_format.strip().lower())
    if fmt is None:
        raise ValueError(
            f"Unsupported output_format {output_format!r}; "
            f"use one of: auto, jpeg, webp, png")
    return fmt


@server.tool()
def compress_image(
    image_path: str,
    target_size: float,
    unit: str = "KB",
    output_path: str | None = None,
    output_dir: str | None = None,
    output_format: str = "auto",
    include_target_in_name: bool = True,
    allow_resize: bool = False,
    keep_metadata: bool = False,
) -> dict[str, Any]:
    """Compress one image so it fits an exact target file size.

    Args:
        image_path: Absolute path of the source image
            (jpg/jpeg/png/webp/bmp/tiff/gif).
        target_size: Desired maximum file size, e.g. ``500``.
        unit: Unit of target_size — "B", "KB" or "MB"
            (KB = 1024 B, MB = 1024 KB).
        output_path: Exact output file path. Overrides output_dir and naming.
        output_dir: Folder for the result (created if missing). The file is
            named ``<source-stem>_<target>.<ext>`` when
            include_target_in_name is true, and ``" (2)"`` is appended when
            that name already exists.
        output_format: "auto" (keeps transparency-aware best choice),
            "jpeg", "webp" or "png". JPEG can also be written as .jpeg.
        include_target_in_name: Put the target size in the file name so
            different targets never overwrite each other.
        allow_resize: If true, may downscale resolution slightly as a
            last resort to reach an aggressive target.
        keep_metadata: Keep EXIF metadata (stripped by default for size
            and privacy).

    Returns:
        A dict with status ("ok" | "target_too_large" | "unreachable" |
        "error"), message, before/after sizes and output_path. When status
        is "target_too_large" the target is NOT smaller than the original
        file, so compression is impossible by definition — ask the user
        for a smaller target.
    """
    result = compress_to_target(
        image_path, target_size, unit,
        output=output_path,
        output_dir=output_dir,
        output_format=_normalize_format(output_format),
        allow_resize=allow_resize,
        keep_metadata=keep_metadata,
        include_target_in_name=include_target_in_name,
    )
    return result.to_dict()


@server.tool()
def batch_compress(
    image_paths: list[str],
    target_size: float,
    unit: str = "KB",
    output_dir: str | None = None,
    output_format: str = "auto",
    include_target_in_name: bool = True,
    allow_resize: bool = False,
    keep_metadata: bool = False,
) -> dict[str, Any]:
    """Compress many images to the same target size.

    Args:
        image_paths: Absolute paths of source images.
        target_size: Desired maximum file size per image.
        unit: "B", "KB" or "MB".
        output_dir: Output folder (created if missing). Defaults to
            writing next to each source.
        output_format: "auto", "jpeg", "webp" or "png".
        include_target_in_name: Put the target size in each file name
            (avoids overwriting results from a different target).
        allow_resize: Allow downscaling as a last resort.
        keep_metadata: Keep EXIF metadata.

    Returns:
        {"results": [...], "summary": {...}} — one entry per file with the
        same shape as compress_image. Files whose original size is already
        <= target come back as "target_too_large" (nothing written).
    """
    fmt = _normalize_format(output_format)
    results = [r.to_dict() for r in compress_many(
        image_paths, target_size, unit,
        output_dir=output_dir, output_format=fmt,
        allow_resize=allow_resize, keep_metadata=keep_metadata,
        include_target_in_name=include_target_in_name,
    )]
    ok = [r for r in results if r["status"] == "ok"]
    return {
        "results": results,
        "summary": {
            "total": len(results),
            "compressed": len(ok),
            "skipped": len([r for r in results if r["status"] == "target_too_large"]),
            "unreachable": len([r for r in results if r["status"] == "unreachable"]),
            "errors": len([r for r in results if r["status"] == "error"]),
            "saved_bytes": sum(r["saved_bytes"] for r in ok),
            "saved_size": format_size(sum(r["saved_bytes"] for r in ok)),
        },
    }


@server.tool()
def image_info_tool(image_path: str) -> dict[str, Any]:
    """Read basic image info: dimensions, format, file size.

    Args:
        image_path: Absolute path of the image file.
    """
    return image_info(image_path)


@server.tool()
def estimate_target(
    image_path: str,
    target_size: float,
    unit: str = "KB",
    allow_resize: bool = False,
) -> dict[str, Any]:
    """Check whether a target size is achievable BEFORE compressing.

    Tells you the original size, the smallest size PicPress can produce,
    and whether the requested target is workable. Use this to validate a
    user's request and to give guidance when it is impossible.

    Args:
        image_path: Absolute path of the image file.
        target_size: Proposed maximum file size.
        unit: "B", "KB" or "MB".
        allow_resize: Whether downscaling would be allowed at compress time.
    """
    target_bytes = parse_size(target_size, unit)
    probe = probe_min_size(image_path, allow_resize=allow_resize)
    original = probe["original_bytes"]
    min_bytes = probe["min_bytes"]

    if target_bytes >= original:
        verdict = "target_too_large"
        advice = (
            f"Target {format_size(target_bytes)} is not smaller than the "
            f"original {format_size(original)}. PicPress only compresses; "
            f"choose a target below {format_size(original)}."
        )
    elif target_bytes < min_bytes:
        verdict = "unreachable"
        advice = (
            f"Target {format_size(target_bytes)} is below the smallest "
            f"achievable size {format_size(min_bytes)} "
            f"({'with' if allow_resize else 'without'} downscaling). "
            f"Choose at least {format_size(min_bytes)} or allow downscaling."
        )
    else:
        verdict = "feasible"
        advice = (
            f"Target {format_size(target_bytes)} is achievable "
            f"(smallest possible: {format_size(min_bytes)})."
        )

    return {
        **probe,
        "target_bytes": target_bytes,
        "target_size": format_size(target_bytes),
        "verdict": verdict,
        "advice": advice,
    }


@server.tool()
def supported_formats() -> dict[str, Any]:
    """List accepted input extensions, output formats and size units."""
    return {
        "input_extensions": sorted(SUPPORTED_INPUT),
        "output_formats": ["auto", "jpeg", "webp", "png"],
        "units": list(UNIT_CHOICES),
        "unit_note": "KB = 1024 B, MB = 1024 KB",
    }


def main() -> None:
    """Entry point used by the console script and the packaged exe."""
    server.run()  # stdio transport


if __name__ == "__main__":
    main()
