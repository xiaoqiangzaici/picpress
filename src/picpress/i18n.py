"""Tiny i18n layer for the PicPress desktop UI.

Two languages ship today: English (``en``) and Simplified Chinese (``zh``).
Adding a language = add one dict below; all UI text goes through :func:`t`.
"""

from __future__ import annotations

__all__ = ["LANGUAGES", "DEFAULT_LANG", "t"]

LANGUAGES = {"en": "English", "zh": "简体中文"}
DEFAULT_LANG = "zh"

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # header
        "app.tagline": "Compress photos to the exact size you choose",
        "app.lang_tip": "Switch interface language",
        # photos card
        "photos.section": "PHOTOS",
        "photos.add": "+  Add files",
        "photos.add_folder": "Add folder",
        "photos.remove": "−  Remove selected",
        "photos.clear": "Clear all",
        "photos.drop": "Drag & drop photos here   ·   JPG / PNG / WebP / BMP / TIFF",
        "photos.stats": "{n} photo(s) · {size} total",
        "photos.skip": "{n} already ≤ target (skipped)",
        # table
        "col.file": "FILE",
        "col.original": "ORIGINAL",
        "col.target": "TARGET",
        "col.result": "RESULT",
        "col.status": "STATUS",
        "status.pending": "Pending",
        "status.skip": "— (skip)",
        "status.too_large": "⚠ Target ≥ original",
        "status.unreachable": "⚠ Cannot be reached",
        "status.error": "✗ Error",
        "status.ok": "✓  −{pct:.1f}%",
        # settings
        "settings.target": "TARGET SIZE",
        "settings.preview": "Every photo will be compressed to ≤ {size}",
        "settings.output": "OUTPUT",
        "settings.format": "Format",
        "settings.resize": "Allow downscaling to reach target",
        "settings.resize_tip": "When quality alone cannot reach the target, PicPress gently\nreduces resolution as a last resort.",
        "settings.meta": "Keep EXIF metadata",
        "settings.meta_tip": "Off by default: stripping metadata makes files smaller and\nprotects privacy (GPS location etc.).",
        "settings.nametag": "Include target size in file name",
        "settings.nametag_tip": "Names outputs like photo_500KB.jpg so different targets never\noverwrite each other. Duplicates still get \" (2)\" appended.",
        "settings.outdir": "Save to",
        "settings.placeholder": "Same folder as source (default)",
        "settings.browse": "Browse",
        # formats
        "fmt.auto": "Auto (recommended)",
        "fmt.jpg": "JPG   ·  .jpg",
        "fmt.jpeg": "JPEG   ·  .jpeg",
        "fmt.png": "PNG   ·  .png",
        "fmt.webp": "WebP   ·  .webp",
        # actions
        "btn.compress": "Compress  →",
        "btn.cancel": "Cancel",
        "btn.ok": "OK",
        "footer.open": "Open output folder",
        "footer.idle": "Nothing compressed yet.",
        "footer.compressing": "Compressing…",
        # summary
        "summary.compressed": "{n} compressed",
        "summary.saved": "saved {size}",
        "summary.warned": "{n} skipped / warned",
        "summary.failed": "{n} failed",
        # status bar
        "status.ready": "Ready · drop photos here or click Add files",
        "status.added": "{n} photo(s) added",
        "status.compressing": "Compressing {name}  ({i}/{n})",
        "status.cancelling": "Cancelling…",
        "status.done": "Done",
        "status.lang_busy": "Finish the current compression before switching language",
        # dialogs
        "dlg.no_files_title": "No photos",
        "dlg.no_files": "Add at least one photo first.",
        "dlg.warn_title": "Some photos were not compressed",
        "dlg.warn_intro": "PicPress only compresses — it never makes a file bigger.",
        "dlg.warn_too_large": "• {name}: target is not smaller than the original ({size})",
        "dlg.warn_unreachable": "• {name}: cannot reach {target} (smallest possible: {min})",
        "dlg.warn_footer": "Choose a smaller target size and try again.",
        "dlg.more": "…and {n} more",
        "dlg.err_title": "Errors",
    },
    "zh": {
        # header
        "app.tagline": "把照片压缩到你指定的体积",
        "app.lang_tip": "切换界面语言",
        # photos card
        "photos.section": "照片",
        "photos.add": "+  添加文件",
        "photos.add_folder": "添加文件夹",
        "photos.remove": "−  移除所选",
        "photos.clear": "清空列表",
        "photos.drop": "把照片拖到这里   ·   JPG / PNG / WebP / BMP / TIFF",
        "photos.stats": "共 {n} 张 · {size}",
        "photos.skip": "{n} 张已不大于目标（将跳过）",
        # table
        "col.file": "文件",
        "col.original": "原大小",
        "col.target": "目标",
        "col.result": "结果",
        "col.status": "状态",
        "status.pending": "待处理",
        "status.skip": "—（跳过）",
        "status.too_large": "⚠ 目标 ≥ 原图",
        "status.unreachable": "⚠ 无法达到",
        "status.error": "✗ 出错",
        "status.ok": "✓  −{pct:.1f}%",
        # settings
        "settings.target": "目标体积",
        "settings.preview": "每张照片都将压缩到 ≤ {size}",
        "settings.output": "输出",
        "settings.format": "格式",
        "settings.resize": "允许降低分辨率以达标",
        "settings.resize_tip": "仅靠画质达不到目标时，PicPress 会小幅降低分辨率作为最后手段。",
        "settings.meta": "保留 EXIF 元数据",
        "settings.meta_tip": "默认关闭：清除元数据可让文件更小，并保护隐私（GPS 位置等）。",
        "settings.nametag": "文件名包含目标体积",
        "settings.nametag_tip": "输出如 photo_500KB.jpg，不同目标的文件不会互相覆盖；\n重名时自动追加「 (2)」。",
        "settings.outdir": "保存到",
        "settings.placeholder": "与原图同目录（默认）",
        "settings.browse": "浏览",
        # formats
        "fmt.auto": "自动（推荐）",
        "fmt.jpg": "JPG   ·  .jpg",
        "fmt.jpeg": "JPEG   ·  .jpeg",
        "fmt.png": "PNG   ·  .png",
        "fmt.webp": "WebP   ·  .webp",
        # actions
        "btn.compress": "开始压缩  →",
        "btn.cancel": "取消",
        "btn.ok": "确定",
        "footer.open": "打开输出文件夹",
        "footer.idle": "尚未压缩。",
        "footer.compressing": "正在压缩…",
        # summary
        "summary.compressed": "已压缩 {n} 张",
        "summary.saved": "节省 {size}",
        "summary.warned": "{n} 张跳过 / 警示",
        "summary.failed": "{n} 张失败",
        # status bar
        "status.ready": "就绪 · 把照片拖进来，或点击添加文件",
        "status.added": "已添加 {n} 张照片",
        "status.compressing": "正在压缩 {name}  （{i}/{n}）",
        "status.cancelling": "正在取消…",
        "status.done": "完成",
        "status.lang_busy": "当前正在压缩，请等待完成后再切换语言",
        # dialogs
        "dlg.no_files_title": "没有照片",
        "dlg.no_files": "请先添加至少一张照片。",
        "dlg.warn_title": "部分照片未压缩",
        "dlg.warn_intro": "PicPress 只做压缩，绝不会把文件变大。",
        "dlg.warn_too_large": "• {name}：目标体积不小于原文件（{size}）",
        "dlg.warn_unreachable": "• {name}：无法达到 {target}（最小可达 {min}）",
        "dlg.warn_footer": "请选择更小的目标体积后重试。",
        "dlg.more": "…另有 {n} 张",
        "dlg.err_title": "出错了",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Look up ``key`` for ``lang`` (falls back to English, then the key)."""
    table = STRINGS.get(lang) or STRINGS["en"]
    text = table.get(key) or STRINGS["en"].get(key) or key
    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return text
