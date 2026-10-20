"""
safety.py - Safety, Validation, and Safe File Operations for ClearSpace
======================================================================
Provides path verification, collision prevention, dry-run previews,
and safe deletion via the Windows Recycle Bin or quarantine backup.

Principles:
- Never overwrite existing files without disambiguating names.
- Never scan or operate on root system drives without safeguards.
- Never follow symbolic links into arbitrary directories.
- Always provide dry-run simulation before modifying disk state.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False


# Critical Windows and system paths that must never be scanned blindly or modified
PROTECTED_FOLDER_NAMES = {
    "windows",
    "system32",
    "syswow64",
    "program files",
    "program files (x86)",
    "programdata",
    "recovery",
    "$recycle.bin",
    "system volume information",
    "boot",
    "perflogs",
}


def format_size(size_bytes: int | float) -> str:
    """
    Format a byte count into a readable human-friendly string (B, KB, MB, GB, TB).

    Examples:
        >>> format_size(1024)
        '1.00 KB'
        >>> format_size(1572864)
        '1.50 MB'
    """
    if size_bytes is None or size_bytes < 0:
        return "0 B"
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(size_bytes)
    unit_index = 0

    while value >= 1024.0 and unit_index < len(units) - 1:
        value /= 1024.0
        unit_index += 1

    if unit_index == 0:
        return f"{int(value)} B"
    return f"{value:.2f} {units[unit_index]}"


def is_symlink(path: str | Path) -> bool:
    """
    Check if a given path is a symbolic link or junction point.
    ClearSpace ignores symlinks to prevent circular loops or traversing outside targets.
    """
    try:
        p = Path(path)
        return p.is_symlink()
    except (OSError, ValueError):
        return False


def is_safe_directory(path_str: str | Path) -> Tuple[bool, str]:
    """
    Validate whether a directory path is safe for scanning and organization.

    Safety Rules:
    - Path must exist and be a directory.
    - Path must not be the system root (e.g., 'C:\\' or '/').
    - Path must not be a protected Windows system directory.
    - Path must not be a symbolic link.
    """
    if not path_str:
        return False, "Directory path cannot be empty."

    try:
        path = Path(path_str).expanduser().resolve()
    except Exception as err:
        return False, f"Invalid directory path: {err}"

    if not path.exists():
        return False, f"Directory does not exist: {path}"

    if not path.is_dir():
        return False, f"Path is a file, not a directory: {path}"

    if is_symlink(path):
        return False, "Scanning symbolic link directories is disabled for safety."

    # Check root drive (e.g. C:\ or /)
    # On Windows, path.parent == path for root (e.g. C:\)
    if path.parent == path or str(path).rstrip("\\/").endswith(":"):
        return False, "Directly scanning an entire drive root (like C:\\) is blocked for system safety."

    # Check against known system directories
    parts_lower = [p.lower() for p in path.parts]
    for protected in PROTECTED_FOLDER_NAMES:
        if protected in parts_lower:
            return False, f"Access to system folder '{protected}' is restricted for safety."

    # Check readability
    if not os.access(str(path), os.R_OK):
        return False, "Directory is not readable (Permission Denied)."

    return True, "Path is valid and safe."


def get_safe_destination(dest_dir: str | Path, filename: str) -> Path:
    """
    Generate a collision-free target path in dest_dir.
    If 'report.pdf' exists, generates 'report (1).pdf', 'report (2).pdf', etc.
    This guarantees ClearSpace never accidentally overwrites an existing file.
    """
    dest_path = Path(dest_dir)
    target = dest_path / filename

    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    counter = 1

    while target.exists():
        new_filename = f"{stem} ({counter}){suffix}"
        target = dest_path / new_filename
        counter += 1

    return target


def validate_move_path(
    source_path: str | Path,
    target_dir: str | Path,
    allowed_base_dir: Optional[str | Path] = None,
) -> Tuple[bool, str]:
    """
    Validate that a file move operation is legitimate and safe.
    Ensures source exists, is not a symlink, and doesn't escape allowed boundaries.
    """
    try:
        src = Path(source_path).resolve()
        dst_dir = Path(target_dir).resolve()
    except Exception as err:
        return False, f"Path resolution error: {err}"

    if not src.exists():
        return False, f"Source file does not exist: {src}"

    if not src.is_file():
        return False, f"Source is not a regular file: {src}"

    if is_symlink(src):
        return False, "Refusing to move symbolic links for safety."

    if allowed_base_dir is not None:
        try:
            base = Path(allowed_base_dir).resolve()
            # Ensure dst_dir is within base
            dst_dir.relative_to(base)
        except ValueError:
            return False, f"Destination '{dst_dir}' is outside the authorized base directory '{base}'."

    return True, "Move parameters are safe."


def safe_delete_file(
    file_path: str | Path,
    use_recycle_bin: bool = True,
    quarantine_dir: Optional[str | Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Safely delete or recycle a single file.

    Parameters:
        file_path: The file to remove.
        use_recycle_bin: If True, sends to the Windows Recycle Bin (preferred).
        quarantine_dir: If Recycle Bin is unavailable, files can be moved here.
        dry_run: If True, simulates the action without touching the filesystem.

    Returns:
        dict: Summary containing status ('success', 'dry_run', 'error'),
              bytes_saved, and an explanatory message.
    """
    path = Path(file_path)

    if not path.exists():
        return {
            "status": "error",
            "action": "delete",
            "path": str(path),
            "message": "File does not exist.",
            "bytes_saved": 0,
        }

    if is_symlink(path):
        return {
            "status": "error",
            "action": "delete",
            "path": str(path),
            "message": "Deletion of symbolic links is refused for safety.",
            "bytes_saved": 0,
        }

    try:
        size_bytes = path.stat().st_size
    except OSError:
        size_bytes = 0

    if dry_run:
        target_mode = "Windows Recycle Bin" if use_recycle_bin else "Permanent Deletion"
        return {
            "status": "dry_run",
            "action": "recycle" if use_recycle_bin else "delete",
            "path": str(path),
            "message": f"[Dry-Run] Would send to {target_mode} ({format_size(size_bytes)})",
            "bytes_saved": size_bytes,
        }

    # Real execution: Prefer Recycle Bin
    if use_recycle_bin:
        if HAS_SEND2TRASH:
            try:
                send2trash.send2trash(str(path))
                return {
                    "status": "success",
                    "action": "recycle",
                    "path": str(path),
                    "message": f"Successfully moved to Windows Recycle Bin ({format_size(size_bytes)} freed).",
                    "bytes_saved": size_bytes,
                }
            except Exception as err:
                return {
                    "status": "error",
                    "action": "recycle",
                    "path": str(path),
                    "message": f"Recycle Bin failed: {err}. File was not touched.",
                    "bytes_saved": 0,
                }
        elif quarantine_dir:
            # Safe alternative: Move to quarantine directory
            try:
                q_dir = Path(quarantine_dir)
                q_dir.mkdir(parents=True, exist_ok=True)
                safe_target = get_safe_destination(q_dir, path.name)
                shutil.move(str(path), str(safe_target))
                return {
                    "status": "success",
                    "action": "quarantine",
                    "path": str(path),
                    "message": f"Recycle Bin unavailable: safely moved to quarantine folder '{safe_target.name}'.",
                    "bytes_saved": size_bytes,
                }
            except Exception as err:
                return {
                    "status": "error",
                    "action": "quarantine",
                    "path": str(path),
                    "message": f"Quarantine relocation failed: {err}",
                    "bytes_saved": 0,
                }
        else:
            return {
                "status": "error",
                "action": "recycle",
                "path": str(path),
                "message": "Recycle Bin is unavailable and no quarantine directory was specified. Operation cancelled.",
                "bytes_saved": 0,
            }

    # Permanent deletion (only when explicitly requested)
    try:
        path.unlink()
        return {
            "status": "success",
            "action": "permanent_delete",
            "path": str(path),
            "message": f"Permanently deleted ({format_size(size_bytes)} freed).",
            "bytes_saved": size_bytes,
        }
    except Exception as err:
        return {
            "status": "error",
            "action": "permanent_delete",
            "path": str(path),
            "message": f"Failed to delete file: {err}",
            "bytes_saved": 0,
        }


def safe_move_file(
    source_path: str | Path,
    target_dir: str | Path,
    custom_filename: Optional[str] = None,
    allowed_base_dir: Optional[str | Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Safely relocate a file to a new directory with collision avoidance.

    Parameters:
        source_path: Source file path.
        target_dir: Destination directory.
        custom_filename: Optional custom target filename (defaults to source name).
        allowed_base_dir: Optional security barrier preventing moves outside root.
        dry_run: If True, returns the planned action without moving.
    """
    src = Path(source_path)
    dst_dir = Path(target_dir)

    is_valid, reason = validate_move_path(src, dst_dir, allowed_base_dir)
    if not is_valid:
        return {
            "status": "error",
            "action": "move",
            "source": str(src),
            "destination": None,
            "message": reason,
        }

    filename = custom_filename or src.name
    safe_destination = get_safe_destination(dst_dir, filename)

    # Check if file is already at destination
    if src.resolve() == safe_destination.resolve():
        return {
            "status": "skipped",
            "action": "move",
            "source": str(src),
            "destination": str(safe_destination),
            "message": "File is already in the target location.",
        }

    if dry_run:
        renamed = safe_destination.name != filename
        rename_note = f" (renamed to '{safe_destination.name}' to prevent overwrite)" if renamed else ""
        return {
            "status": "dry_run",
            "action": "move",
            "source": str(src),
            "destination": str(safe_destination),
            "message": f"[Dry-Run] Would move to '{safe_destination}'{rename_note}.",
        }

    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(safe_destination))
        renamed = safe_destination.name != filename
        rename_note = f" (renamed to avoid overwrite)" if renamed else ""
        return {
            "status": "success",
            "action": "move",
            "source": str(src),
            "destination": str(safe_destination),
            "message": f"Moved to '{safe_destination.name}'{rename_note}.",
        }
    except Exception as err:
        return {
            "status": "error",
            "action": "move",
            "source": str(src),
            "destination": str(safe_destination),
            "message": f"Failed to move file: {err}",
        }
