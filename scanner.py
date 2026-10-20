"""
scanner.py - Recursive Folder Scanner for ClearSpace
===================================================
Recursively scans directories to collect file metadata, categorize files,
and calculate storage footprints without touching or modifying any files.
Strictly ignores symbolic links and handles permission errors gracefully.
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from safety import format_size, is_safe_directory, is_symlink


# Comprehensive file extension mappings for classification
CATEGORY_EXTENSIONS: Dict[str, set[str]] = {
    "Images": {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp",
        ".tiff", ".tif", ".ico", ".heic", ".raw", ".psd", ".ai"
    },
    "Documents": {
        ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md",
        ".epub", ".pages", ".tex", ".wpd"
    },
    "Videos": {
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
        ".m4v", ".mpg", ".mpeg", ".3gp", ".ts"
    },
    "Audio": {
        ".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma",
        ".aiff", ".alac", ".mid", ".midi"
    },
    "Archives": {
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
        ".iso", ".dmg", ".tgz", ".cab"
    },
    "Code": {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".htm",
        ".css", ".scss", ".json", ".xml", ".c", ".cpp", ".h",
        ".hpp", ".java", ".sh", ".bat", ".ps1", ".sql", ".rs",
        ".go", ".php", ".rb", ".yaml", ".yml", ".toml", ".ini",
        ".vue", ".dart", ".kt", ".swift"
    },
    "Spreadsheets": {
        ".xlsx", ".xls", ".csv", ".tsv", ".ods", ".numbers", ".xlsm"
    },
}


def get_file_category(extension: str) -> str:
    """
    Determine the category of a file based on its extension.

    Parameters:
        extension: File extension, with or without leading dot.

    Returns:
        One of 'Images', 'Documents', 'Videos', 'Audio', 'Archives',
        'Code', 'Spreadsheets', or 'Others'.
    """
    ext = extension.strip().lower()
    if ext and not ext.startswith("."):
        ext = f".{ext}"

    for category, extensions in CATEGORY_EXTENSIONS.items():
        if ext in extensions:
            return category

    return "Others"


def is_hidden(path: Path) -> bool:
    """
    Check if a file or directory is hidden.
    Supports Unix dot-files and Windows hidden file attribute.
    """
    # Dot-prefixed name
    if path.name.startswith("."):
        return True

    # Windows hidden attribute check
    if os.name == "nt":
        try:
            import ctypes
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            # FILE_ATTRIBUTE_HIDDEN = 0x02
            if attrs != -1 and (attrs & 0x02):
                return True
        except Exception:
            pass

    return False


def scan_folder(
    folder_path: str | Path,
    skip_hidden: bool = True,
    max_depth: Optional[int] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Scan a directory recursively and return structured metadata for every file.

    Parameters:
        folder_path: Root directory to begin scanning.
        skip_hidden: If True, skips files and directories starting with '.' or marked hidden.
        max_depth: Optional maximum recursion depth (None for unlimited).
        progress_callback: Optional callback func(file_count, current_path) for UI progress updates.

    Returns:
        dict: {
            "success": bool,
            "folder_path": str,
            "files": list[dict],
            "total_files": int,
            "total_size_bytes": int,
            "total_size_human": str,
            "category_counts": dict[str, int],
            "category_sizes": dict[str, int],
            "errors": list[dict],
            "scanned_at": str,
            "message": str
        }
    """
    is_safe, reason = is_safe_directory(folder_path)
    if not is_safe:
        return {
            "success": False,
            "folder_path": str(folder_path),
            "files": [],
            "total_files": 0,
            "total_size_bytes": 0,
            "total_size_human": "0 B",
            "category_counts": {},
            "category_sizes": {},
            "errors": [{"path": str(folder_path), "error": reason}],
            "scanned_at": datetime.datetime.now().isoformat(),
            "message": f"Scan aborted for safety: {reason}",
        }

    root_path = Path(folder_path).expanduser().resolve()
    files_list: List[Dict[str, Any]] = []
    errors_list: List[Dict[str, str]] = []
    category_counts: Dict[str, int] = {cat: 0 for cat in list(CATEGORY_EXTENSIONS.keys()) + ["Others"]}
    category_sizes: Dict[str, int] = {cat: 0 for cat in list(CATEGORY_EXTENSIONS.keys()) + ["Others"]}
    total_bytes = 0
    scanned_count = 0

    root_depth = len(root_path.parts)

    try:
        # Use os.walk with followlinks=False to prevent circular loops and traversing symlinks
        for current_dir, dirnames, filenames in os.walk(str(root_path), followlinks=False):
            current_path = Path(current_dir)

            # Check recursion depth limit
            current_depth = len(current_path.parts) - root_depth
            if max_depth is not None and current_depth > max_depth:
                dirnames.clear()
                continue

            # Filter out hidden or symlinked subdirectories in-place
            filtered_dirnames = []
            for d in dirnames:
                dir_full = current_path / d
                if is_symlink(dir_full):
                    continue
                if skip_hidden and is_hidden(dir_full):
                    continue
                filtered_dirnames.append(d)
            dirnames[:] = filtered_dirnames

            # Process files in current directory
            for fname in filenames:
                file_full = current_path / fname

                # Never follow symbolic links
                if is_symlink(file_full):
                    continue

                if skip_hidden and is_hidden(file_full):
                    continue

                try:
                    stats = file_full.stat()
                    file_size = stats.st_size
                    mtime = stats.st_mtime
                    mtime_dt = datetime.datetime.fromtimestamp(mtime)
                    mtime_str = mtime_dt.strftime("%Y-%m-%d %H:%M:%S")

                    extension = file_full.suffix.lower()
                    category = get_file_category(extension)

                    record = {
                        "path": str(file_full),
                        "filename": fname,
                        "extension": extension if extension else "(no ext)",
                        "size_bytes": file_size,
                        "size_human": format_size(file_size),
                        "category": category,
                        "directory": str(current_path),
                        "modified_time": mtime_str,
                        "modified_timestamp": mtime,
                    }

                    files_list.append(record)
                    total_bytes += file_size
                    category_counts[category] = category_counts.get(category, 0) + 1
                    category_sizes[category] = category_sizes.get(category, 0) + file_size
                    scanned_count += 1

                    if progress_callback and scanned_count % 25 == 0:
                        progress_callback(scanned_count, str(file_full))

                except (PermissionError, FileNotFoundError, OSError) as err:
                    errors_list.append({"path": str(file_full), "error": str(err)})

    except Exception as err:
        errors_list.append({"path": str(root_path), "error": f"General scan error: {err}"})

    if progress_callback:
        progress_callback(scanned_count, "Scan complete")

    return {
        "success": True,
        "folder_path": str(root_path),
        "files": files_list,
        "total_files": len(files_list),
        "total_size_bytes": total_bytes,
        "total_size_human": format_size(total_bytes),
        "category_counts": category_counts,
        "category_sizes": category_sizes,
        "errors": errors_list,
        "scanned_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": f"Successfully scanned {len(files_list)} files ({format_size(total_bytes)}) with {len(errors_list)} skipped items.",
    }
