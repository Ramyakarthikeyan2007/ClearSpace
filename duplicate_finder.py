"""
duplicate_finder.py - Content-Based Duplicate Detection for ClearSpace
=====================================================================
Identifies duplicate files using cryptographic SHA-256 content hashing.
Never assumes duplicates based on filename or extension alone.
Accurately computes potential storage savings without counting the original.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from safety import format_size


def compute_sha256(file_path: str | Path, chunk_size: int = 65536) -> Optional[str]:
    """
    Compute the SHA-256 hash of a file efficiently in streaming chunks.

    Parameters:
        file_path: Path to the target file.
        chunk_size: Read buffer size in bytes (default 64KB).

    Returns:
        Hexadecimal SHA-256 string, or None if unreadable.
    """
    hasher = hashlib.sha256()
    path = Path(file_path)

    try:
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (PermissionError, FileNotFoundError, OSError):
        return None


def find_duplicates(
    files: List[Dict[str, Any]],
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Detect duplicate files among a scanned file list using a two-pass algorithm:
    1. Size-bucket pre-filtering (only files with matching sizes can be duplicates).
    2. SHA-256 full content verification on size matches.

    Parameters:
        files: List of file dictionaries (from scanner.py).
        progress_callback: Optional func(current, total, filename) for UI progress bar.

    Returns:
        dict: {
            "groups": list of duplicate group dicts,
            "total_groups": int,
            "total_redundant_files": int,
            "total_savings_bytes": int,
            "total_savings_human": str,
        }
    """
    if not files:
        return {
            "groups": [],
            "total_groups": 0,
            "total_redundant_files": 0,
            "total_savings_bytes": 0,
            "total_savings_human": "0 B",
        }

    # Pass 1: Bucket files by exact byte size (ignore 0-byte files from duplicate waste)
    size_buckets: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for f in files:
        size = f.get("size_bytes", 0)
        if size > 0:  # 0-byte empty files don't waste storage space
            size_buckets[size].append(f)

    # Filter candidate files that share a size with at least one other file
    candidates: List[Dict[str, Any]] = []
    for size, bucket in size_buckets.items():
        if len(bucket) > 1:
            candidates.extend(bucket)

    total_candidates = len(candidates)
    if total_candidates == 0:
        return {
            "groups": [],
            "total_groups": 0,
            "total_redundant_files": 0,
            "total_savings_bytes": 0,
            "total_savings_human": "0 B",
        }

    # Pass 2: Compute SHA-256 hash for candidates and group by (size, hash)
    hash_buckets: Dict[Tuple[int, str], List[Dict[str, Any]]] = defaultdict(list)

    for idx, cand in enumerate(candidates, start=1):
        path = cand.get("path")
        if progress_callback:
            progress_callback(idx, total_candidates, cand.get("filename", ""))

        file_hash = compute_sha256(path)
        if file_hash:
            key = (cand["size_bytes"], file_hash)
            hash_buckets[key].append(cand)

    # Build structured duplicate groups
    groups: List[Dict[str, Any]] = []
    total_redundant_files = 0
    total_savings_bytes = 0
    group_counter = 1

    for (size_bytes, file_hash), matched_files in hash_buckets.items():
        if len(matched_files) > 1:
            # Sort files by modification date ascending (oldest first by default)
            sorted_files = sorted(
                matched_files,
                key=lambda x: (x.get("modified_timestamp", 0), len(x.get("path", "")))
            )

            count = len(sorted_files)
            redundant_count = count - 1
            savings_for_group = redundant_count * size_bytes

            # Annotate files: default oldest is marked as recommended to keep
            annotated_files = []
            for i, f in enumerate(sorted_files):
                f_copy = dict(f)
                f_copy["is_recommended_keep"] = (i == 0)
                annotated_files.append(f_copy)

            group_data = {
                "group_id": group_counter,
                "sha256": file_hash,
                "short_hash": file_hash[:12],
                "size_bytes": size_bytes,
                "size_human": format_size(size_bytes),
                "file_count": count,
                "redundant_count": redundant_count,
                "potential_savings_bytes": savings_for_group,
                "potential_savings_human": format_size(savings_for_group),
                "files": annotated_files,
            }

            groups.append(group_data)
            total_redundant_files += redundant_count
            total_savings_bytes += savings_for_group
            group_counter += 1

    # Sort groups by potential savings descending (biggest wins first)
    groups.sort(key=lambda g: g["potential_savings_bytes"], reverse=True)

    # Re-assign sequential IDs after sorting
    for idx, grp in enumerate(groups, start=1):
        grp["group_id"] = idx

    return {
        "groups": groups,
        "total_groups": len(groups),
        "total_redundant_files": total_redundant_files,
        "total_savings_bytes": total_savings_bytes,
        "total_savings_human": format_size(total_savings_bytes),
    }


def apply_keep_strategy(
    group: Dict[str, Any],
    strategy: str = "keep_oldest",
) -> List[Dict[str, Any]]:
    """
    Apply a recommendation strategy for which file in a duplicate group to keep.

    Strategies:
    - 'keep_oldest': Keep original file with earliest modification time.
    - 'keep_newest': Keep most recent file with latest modification time.
    - 'keep_shortest_path': Keep the copy with the cleanest/shortest directory path.

    Enforces that exactly 1 file is kept as the protected original.
    """
    files = [dict(f) for f in group.get("files", [])]
    if not files:
        return []

    if strategy == "keep_newest":
        target = max(files, key=lambda x: x.get("modified_timestamp", 0))
    elif strategy == "keep_shortest_path":
        target = min(files, key=lambda x: len(x.get("path", "")))
    else:  # default 'keep_oldest'
        target = min(files, key=lambda x: x.get("modified_timestamp", 0))

    target_path = target.get("path")
    for f in files:
        f["is_recommended_keep"] = (f.get("path") == target_path)

    return files


def calculate_selected_savings(
    groups: List[Dict[str, Any]],
    selected_paths_to_delete: set[str],
) -> Dict[str, Any]:
    """
    Calculate the actual storage savings based on specific user-selected files.

    Safety Guarantee:
    If every single file in a group has been selected, the function rejects deleting
    the entire group and keeps at least one copy protected.
    """
    actual_savings_bytes = 0
    safe_delete_paths: List[str] = []
    blocked_paths: List[str] = []

    for grp in groups:
        grp_files = grp.get("files", [])
        size_bytes = grp.get("size_bytes", 0)

        # Files marked for deletion in this group
        marked_in_group = [f for f in grp_files if f.get("path") in selected_paths_to_delete]

        # Safety rule: Never delete every copy!
        if len(marked_in_group) == len(grp_files) and len(grp_files) > 0:
            # Protect one copy (the oldest)
            protected = min(grp_files, key=lambda x: x.get("modified_timestamp", 0))
            blocked_paths.append(protected["path"])
            marked_in_group = [f for f in marked_in_group if f["path"] != protected["path"]]

        for f in marked_in_group:
            safe_delete_paths.append(f["path"])
            actual_savings_bytes += size_bytes

    return {
        "actual_savings_bytes": actual_savings_bytes,
        "actual_savings_human": format_size(actual_savings_bytes),
        "files_to_remove": safe_delete_paths,
        "protected_files": blocked_paths,
        "file_count": len(safe_delete_paths),
    }
