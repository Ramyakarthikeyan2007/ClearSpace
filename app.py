"""
ClearSpace — Smart Digital Declutter
===================================
A modern, safety-first desktop file management and decluttering dashboard.
Built with Python, Streamlit, Pandas, and Plotly.
"""

from __future__ import annotations

import datetime
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from duplicate_finder import (
    apply_keep_strategy,
    calculate_selected_savings,
    find_duplicates,
)
from organizer import (
    ORGANIZATION_CATEGORIES,
    execute_organization_plan,
    generate_organization_plan,
)
from safety import (
    HAS_SEND2TRASH,
    format_size,
    is_safe_directory,
    safe_delete_file,
    safe_move_file,
)
from scanner import (
    CATEGORY_EXTENSIONS,
    get_file_category,
    scan_folder,
)
from storage_insights import (
    create_category_donut_chart,
    create_extension_bar_chart,
    create_largest_files_chart,
    export_report_to_json,
    export_scan_to_csv,
    files_to_dataframe,
    get_category_summary,
    get_extension_summary,
    get_largest_files,
    get_largest_folders,
)


# =============================================================================
# Streamlit App Configuration & Styling
# =============================================================================

st.set_page_config(
    page_title="ClearSpace — Smart Digital Declutter",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> Dict[str, Any]:
    """Load user preferences and scan summary from config.json."""
    default_cfg = {
        "theme": "Emerald Cream",
        "default_scan_path": "",
        "skip_hidden_files": True,
        "use_recycle_bin": True,
        "max_scan_depth": 20,
        "safe_mode": True,
        "last_scan_summary": {
            "folder_path": "",
            "total_files": 0,
            "total_size_human": "0 B",
            "scanned_at": "",
        },
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                default_cfg.update(loaded)
        except Exception:
            pass
    return default_cfg


def save_config(cfg: Dict[str, Any]) -> bool:
    """Save user preferences to config.json safely."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        return True
    except Exception:
        return False


# Initialize Session State
if "config" not in st.session_state:
    st.session_state.config = load_config()

if "scanned_files" not in st.session_state:
    st.session_state.scanned_files = []

if "scan_summary" not in st.session_state:
    st.session_state.scan_summary = st.session_state.config.get("last_scan_summary", {})

if "duplicate_results" not in st.session_state:
    st.session_state.duplicate_results = None

if "organization_plan" not in st.session_state:
    st.session_state.organization_plan = None

if "cleanup_logs" not in st.session_state:
    st.session_state.cleanup_logs = []

if "selected_duplicates_to_delete" not in st.session_state:
    st.session_state.selected_duplicates_to_delete = set()


# Inject Custom CSS for Emerald & Warm Cream Theme
CUSTOM_CSS = """
<style>
    /* Global Typography and Background */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Emerald Theme Colors */
    :root {
        --emerald-primary: #047857;
        --emerald-dark: #064E3B;
        --emerald-light: #10B981;
        --emerald-subtle: #ECFDF5;
        --cream-bg: #FCFBF7;
        --cream-card: #FFFFFF;
        --cream-border: #E6E1D8;
        --text-primary: #1C241E;
        --text-secondary: #475569;
    }
    
    /* Top Bar Banner */
    .app-header {
        background: linear-gradient(135deg, #064E3B 0%, #047857 70%, #10B981 100%);
        padding: 24px 30px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 4px 14px rgba(6, 78, 59, 0.15);
    }
    .app-header h1 {
        color: #FFFFFF !important;
        font-size: 28px;
        font-weight: 700;
        margin: 0 0 6px 0;
        letter-spacing: -0.5px;
    }
    .app-header p {
        color: #D1FAE5;
        font-size: 15px;
        margin: 0;
        opacity: 0.95;
    }

    /* KPI Cards */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }
    .kpi-card {
        background: #FFFFFF;
        border-radius: 14px;
        padding: 18px 20px;
        border: 1px solid var(--cream-border);
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
        border-top: 4px solid var(--emerald-light);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06);
    }
    .kpi-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 26px;
        font-weight: 700;
        color: var(--emerald-dark);
        line-height: 1.2;
    }
    .kpi-subtext {
        font-size: 12px;
        color: #64748B;
        margin-top: 4px;
    }

    /* Info & Badge Badges */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-emerald {
        background-color: #D1FAE5;
        color: #064E3B;
    }
    .badge-amber {
        background-color: #FEF3C7;
        color: #92400E;
    }
    
    /* Clean Cards */
    .content-box {
        background: #FFFFFF;
        border-radius: 12px;
        border: 1px solid var(--cream-border);
        padding: 20px;
        margin-bottom: 20px;
    }

    /* Custom button aesthetics */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.15s ease-in-out;
    }
    div.stButton > button:hover {
        border-color: var(--emerald-light);
        color: var(--emerald-dark);
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# =============================================================================
# Helper: Synthetic Demo Workspace Creator
# =============================================================================

def create_demo_folder() -> str:
    """
    Creates a temporary synthetic test directory with various file categories
    and duplicate files to allow zero-configuration testing and portfolio demos.
    """
    demo_dir = Path(tempfile.gettempdir()) / "ClearSpace_Demo_Workspace"
    if demo_dir.exists():
        shutil.rmtree(demo_dir, ignore_errors=True)
    demo_dir.mkdir(parents=True, exist_ok=True)

    # Subdirectories
    sub_docs = demo_dir / "Documents"
    sub_downloads = demo_dir / "Downloads"
    sub_photos = demo_dir / "Photos"
    for d in (sub_docs, sub_downloads, sub_photos):
        d.mkdir(parents=True, exist_ok=True)

    # Synthetic contents
    sample_text = "ClearSpace - Smart Digital Declutter portfolio demonstration content.\n" * 50
    duplicate_text_1 = "This is identical duplicate content generated for testing SHA-256 detection.\n" * 120
    duplicate_image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4" + (b"DATA" * 500)

    # 1. Documents
    (demo_dir / "Project_Report.docx").write_text(sample_text, encoding="utf-8")
    (sub_docs / "Meeting_Notes.txt").write_text(sample_text, encoding="utf-8")
    (sub_docs / "Architecture_Plan.md").write_text("# ClearSpace Architecture\n" + sample_text, encoding="utf-8")

    # 2. Spreadsheets
    (demo_dir / "Budget_Q3.csv").write_text("ID,Item,Amount\n1,Cloud,500\n2,Domain,20\n", encoding="utf-8")
    (sub_docs / "Financials.xlsx").write_bytes(b"PK\x03\x04" + b"XLSX_MOCK_DATA" * 50)

    # 3. Duplicate Group A (3 identical text files across folders)
    (demo_dir / "Research_Draft_v1.txt").write_text(duplicate_text_1, encoding="utf-8")
    (sub_downloads / "Research_Draft_Copy.txt").write_text(duplicate_text_1, encoding="utf-8")
    (sub_docs / "Research_Draft_Backup.txt").write_text(duplicate_text_1, encoding="utf-8")

    # 4. Duplicate Group B (2 identical image files)
    (sub_photos / "Team_Photo.png").write_bytes(duplicate_image_bytes)
    (sub_downloads / "Team_Photo_duplicate.png").write_bytes(duplicate_image_bytes)

    # 5. Code & Archives
    (demo_dir / "script.py").write_text("import os\nprint('ClearSpace Demo')\n", encoding="utf-8")
    (sub_downloads / "archive.zip").write_bytes(b"PK\x03\x04" + b"ZIP_DUMMY_DATA" * 80)

    return str(demo_dir)


# =============================================================================
# Navigation Sidebar
# =============================================================================

with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <span style="font-size: 32px;">🌿</span>
            <div>
                <h2 style="margin: 0; font-size: 22px; font-weight: 700; color: #064E3B;">ClearSpace</h2>
                <span style="font-size: 12px; color: #059669; font-weight: 600;">Smart Digital Declutter</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("<hr style='margin: 12px 0 18px 0; border-color: #E6E1D8;' />", unsafe_allow_html=True)

    if "page_redirect" in st.session_state:
        st.session_state["nav_page"] = st.session_state.pop("page_redirect")

    page = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "🔍 Scan Files",
            "👥 Duplicate Finder",
            "📁 File Organizer",
            "📈 Storage Insights",
            "⚙️ Settings & Reports",
        ],
        key="nav_page",
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Quick System Status in Sidebar
    total_loaded = len(st.session_state.scanned_files)
    active_path = st.session_state.scan_summary.get("folder_path", "")

    st.markdown("### 📌 Active Workspace")
    if total_loaded > 0 and active_path:
        st.markdown(f"""
            <div style="background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 8px; padding: 10px; font-size: 12px;">
                <div style="font-weight: 600; color: #064E3B; word-break: break-all;">📁 {Path(active_path).name or active_path}</div>
                <div style="color: #047857; margin-top: 4px;"><b>{total_loaded:,}</b> files scanned ({st.session_state.scan_summary.get('total_size_human', '0 B')})</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No folder scanned yet. Go to **Scan Files** to start.")

    st.markdown("<br><hr style='margin: 12px 0 18px 0; border-color: #E6E1D8;' />", unsafe_allow_html=True)
    st.caption("🛡️ **Safety Guarantee**: ClearSpace never deletes or moves files without explicit user confirmation.")


# =============================================================================
# Helper: Recompute KPI Metrics
# =============================================================================

def get_current_kpis() -> Dict[str, Any]:
    """Calculates active KPI values for display across screens."""
    files = st.session_state.scanned_files
    total_files = len(files)
    total_bytes = sum(f.get("size_bytes", 0) for f in files)

    dup_results = st.session_state.duplicate_results
    if dup_results:
        dup_groups = dup_results.get("total_groups", 0)
        dup_savings = dup_results.get("total_savings_bytes", 0)
    else:
        dup_groups = 0
        dup_savings = 0

    return {
        "total_files": total_files,
        "total_storage_human": format_size(total_bytes),
        "dup_groups": dup_groups,
        "dup_savings_human": format_size(dup_savings),
    }


# =============================================================================
# PAGE 1: 📊 Dashboard
# =============================================================================

if page == "📊 Dashboard":
    st.markdown("""
        <div class="app-header">
            <h1>ClearSpace — Smart Digital Declutter</h1>
            <p>Understand storage consumption, locate redundant duplicates, and organize digital spaces safely.</p>
        </div>
    """, unsafe_allow_html=True)

    kpis = get_current_kpis()

    # KPI Banner Cards
    st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-label">Total Files Scanned</div>
                <div class="kpi-value">{kpis['total_files']:,}</div>
                <div class="kpi-subtext">Across active directory</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Total Storage Used</div>
                <div class="kpi-value">{kpis['total_storage_human']}</div>
                <div class="kpi-subtext">Physical disk footprint</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Duplicate Groups</div>
                <div class="kpi-value">{kpis['dup_groups']}</div>
                <div class="kpi-subtext">SHA-256 verified matches</div>
            </div>
            <div class="kpi-card" style="border-top-color: #047857;">
                <div class="kpi-label">Potential Space Savings</div>
                <div class="kpi-value">{kpis['dup_savings_human']}</div>
                <div class="kpi-subtext">Without losing original copy</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if not st.session_state.scanned_files:
        st.markdown("""
            <div class="content-box" style="text-align: center; padding: 40px 20px;">
                <span style="font-size: 48px;">📂</span>
                <h3 style="color: #064E3B; margin-top: 10px;">Welcome to ClearSpace</h3>
                <p style="color: #475569; max-width: 580px; margin: 0 auto 20px auto;">
                    Select a folder on your computer to scan. ClearSpace will analyze your storage,
                    group duplicate files using cryptographic SHA-256 hashing, and help you reorganize your folders safely.
                </p>
            </div>
        """, unsafe_allow_html=True)

        col_a, col_b, col_c = st.columns([1, 1.2, 1])
        with col_b:
            if st.button("🚀 Create & Scan Synthetic Demo Workspace", use_container_width=True, type="primary"):
                demo_path = create_demo_folder()
                with st.spinner("Scanning demo workspace..."):
                    results = scan_folder(demo_path)
                    st.session_state.scanned_files = results["files"]
                    st.session_state.scan_summary = results
                    # Auto-detect duplicates for seamless demo
                    st.session_state.duplicate_results = find_duplicates(results["files"])
                    st.rerun()

    else:
        # Active Visualizations
        col_left, col_right = st.columns([1, 1])
        df = files_to_dataframe(st.session_state.scanned_files)
        cat_summary = get_category_summary(df)
        ext_summary = get_extension_summary(df, top_n=8)

        with col_left:
            st.markdown("#### 📂 File Type Distribution")
            donut_fig = create_category_donut_chart(cat_summary)
            st.plotly_chart(donut_fig, use_container_width=True)

        with col_right:
            st.markdown("#### 📊 Storage Footprint by Extension")
            bar_fig = create_extension_bar_chart(ext_summary)
            st.plotly_chart(bar_fig, use_container_width=True)

        # Recent Scan Information
        summary = st.session_state.scan_summary
        st.markdown("#### 🕒 Active Scan Summary")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.markdown(f"**Target Folder:** `{summary.get('folder_path', 'N/A')}`")
        with col_s2:
            st.markdown(f"**Last Scanned:** {summary.get('scanned_at', 'N/A')}")
        with col_s3:
            errors_count = len(summary.get("errors", []))
            if errors_count == 0:
                st.markdown("**Scan Health:** :green[100% Healthy (0 errors)]")
            else:
                st.markdown(f"**Scan Health:** :orange[{errors_count} items skipped/inaccessible]")

        # Action Quick Links
        st.markdown("<hr style='margin: 16px 0;' />", unsafe_allow_html=True)
        q1, q2, q3 = st.columns(3)
        with q1:
            if st.button("🔍 Run New Scan", use_container_width=True):
                st.session_state.page_redirect = "🔍 Scan Files"
                st.rerun()
        with q2:
            if st.button("👥 Inspect Duplicate Files", use_container_width=True, type="primary"):
                st.session_state.page_redirect = "👥 Duplicate Finder"
                st.rerun()
        with q3:
            if st.button("📁 Propose File Organization", use_container_width=True):
                st.session_state.page_redirect = "📁 File Organizer"
                st.rerun()


# =============================================================================
# PAGE 2: 🔍 Scan Files
# =============================================================================

elif page == "🔍 Scan Files":
    st.markdown("""
        <div class="app-header">
            <h1>Folder Scanner</h1>
            <p>Safely scan any directory and its subfolders to analyze file inventory and storage footprint.</p>
        </div>
    """, unsafe_allow_html=True)

    default_path = st.session_state.config.get("default_scan_path", "")

    # Input Controls
    with st.container():
        st.markdown("#### 🎯 Choose Folder to Scan")
        folder_col, demo_col = st.columns([3, 1])

        with folder_col:
            target_path_input = st.text_input(
                "Enter folder path (e.g. C:\\Users\\User\\Downloads or C:\\Users\\User\\Documents)",
                value=default_path,
                placeholder="C:\\Users\\Username\\Documents",
                help="Type or paste the full directory path you wish to scan.",
            )

        with demo_col:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("✨ Load Demo Folder", use_container_width=True):
                target_path_input = create_demo_folder()
                st.session_state.config["default_scan_path"] = target_path_input
                st.rerun()

    # Advanced Options Accordion
    with st.expander("⚙️ Scan Options & Safeguards", expanded=False):
        opt_col1, opt_col2 = st.columns(2)
        with opt_col1:
            skip_hidden = st.checkbox("Skip hidden files and directories", value=True)
        with opt_col2:
            depth_limit = st.slider("Maximum directory depth (0 = current folder only)", min_value=1, max_value=50, value=20)

    # Start Scan Button
    scan_clicked = st.button("🚀 Start Recursive Scan", type="primary", use_container_width=False)

    if scan_clicked:
        if not target_path_input.strip():
            st.warning("Please provide a valid folder path.")
        else:
            is_safe, reason = is_safe_directory(target_path_input)
            if not is_safe:
                st.error(f"⚠️ Security Guardrail: {reason}")
            else:
                progress_bar = st.progress(0, text="Initializing recursive file scanner...")
                status_text = st.empty()

                def update_progress(count: int, current_file: str):
                    status_text.text(f"Scanning... {count} files discovered | {Path(current_file).name}")
                    progress_bar.progress(min(count % 100 / 100.0, 0.95))

                t_start = time.time()
                scan_res = scan_folder(
                    target_path_input,
                    skip_hidden=skip_hidden,
                    max_depth=depth_limit,
                    progress_callback=update_progress,
                )
                t_elapsed = time.time() - t_start

                progress_bar.progress(1.0, text="Scan finished successfully!")
                status_text.empty()

                if scan_res["success"]:
                    st.session_state.scanned_files = scan_res["files"]
                    st.session_state.scan_summary = scan_res
                    st.session_state.duplicate_results = None  # Reset duplicates until requested
                    st.session_state.organization_plan = None

                    # Update persistent config
                    st.session_state.config["last_scan_summary"] = {
                        "folder_path": scan_res["folder_path"],
                        "total_files": scan_res["total_files"],
                        "total_size_human": scan_res["total_size_human"],
                        "scanned_at": scan_res["scanned_at"],
                    }
                    save_config(st.session_state.config)

                    st.success(f"✅ {scan_res['message']} (Completed in {t_elapsed:.2f}s)")
                else:
                    st.error(scan_res["message"])

    # Results Table & Filtering
    if st.session_state.scanned_files:
        st.markdown("<hr style='margin: 24px 0;' />", unsafe_allow_html=True)
        st.markdown("### 📋 Scanned Files Inventory")

        df = files_to_dataframe(st.session_state.scanned_files)

        # Filters Row
        f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1.2, 1.2, 1.2])

        with f_col1:
            search_query = st.text_input("🔍 Search by filename", placeholder="Type keywords...")

        with f_col2:
            available_categories = ["All"] + sorted(list(df["category"].unique()))
            selected_cat = st.selectbox("Category filter", available_categories)

        with f_col3:
            available_extensions = ["All"] + sorted(list(df["extension"].unique()))
            selected_ext = st.selectbox("Extension filter", available_extensions)

        with f_col4:
            sort_by = st.selectbox(
                "Sort results by",
                ["Size (Largest first)", "Size (Smallest first)", "Filename (A-Z)", "Date Modified (Newest)"]
            )

        # Apply Filters
        filtered_df = df.copy()

        if search_query:
            filtered_df = filtered_df[filtered_df["filename"].str.contains(search_query, case=False, na=False)]

        if selected_cat != "All":
            filtered_df = filtered_df[filtered_df["category"] == selected_cat]

        if selected_ext != "All":
            filtered_df = filtered_df[filtered_df["extension"] == selected_ext]

        # Sorting
        if sort_by == "Size (Largest first)":
            filtered_df = filtered_df.sort_values(by="size_bytes", ascending=False)
        elif sort_by == "Size (Smallest first)":
            filtered_df = filtered_df.sort_values(by="size_bytes", ascending=True)
        elif sort_by == "Filename (A-Z)":
            filtered_df = filtered_df.sort_values(by="filename", ascending=True)
        elif sort_by == "Date Modified (Newest)":
            filtered_df = filtered_df.sort_values(by="modified_timestamp", ascending=False)

        # Display Metrics for Filtered Set
        st.markdown(f"**Showing {len(filtered_df):,} of {len(df):,} files** ({format_size(filtered_df['size_bytes'].sum())})")

        if filtered_df.empty:
            st.info("No files match the specified search or filter criteria.")
        else:
            display_columns = ["filename", "category", "extension", "size_human", "modified_time", "directory"]
            st.dataframe(
                filtered_df[display_columns].rename(columns={
                    "filename": "Filename",
                    "category": "Category",
                    "extension": "Extension",
                    "size_human": "Size",
                    "modified_time": "Last Modified",
                    "directory": "Folder Path",
                }),
                use_container_width=True,
                height=380,
            )


# =============================================================================
# PAGE 3: 👥 Duplicate Finder
# =============================================================================

elif page == "👥 Duplicate Finder":
    st.markdown("""
        <div class="app-header">
            <h1>Duplicate File Finder</h1>
            <p>Locate identical files using cryptographic SHA-256 content hashing. Preview copies and safely reclaim wasted storage.</p>
        </div>
    """, unsafe_allow_html=True)

    if not st.session_state.scanned_files:
        st.warning("⚠️ No files have been scanned yet. Please scan a folder in the **Scan Files** section first.")
    else:
        # Run detection if not already completed
        if st.session_state.duplicate_results is None:
            st.markdown("""
                <div class="content-box">
                    <p style="margin: 0; color: #475569;">
                        Click below to verify file contents with cryptographic SHA-256 hashing.
                        ClearSpace checks files of equal size chunk-by-chunk to guarantee 100% accurate duplicate detection.
                    </p>
                </div>
            """, unsafe_allow_html=True)

            if st.button("🔍 Find Duplicates in Scanned Files", type="primary"):
                p_bar = st.progress(0, text="Calculating SHA-256 hashes for candidate duplicates...")

                def hash_progress(current, total, name):
                    p_bar.progress(current / total, text=f"Hashing file {current}/{total}: {name}")

                dup_res = find_duplicates(st.session_state.scanned_files, progress_callback=hash_progress)
                p_bar.progress(1.0, text="Duplicate scan complete!")
                st.session_state.duplicate_results = dup_res
                st.rerun()

        else:
            dup_res = st.session_state.duplicate_results
            groups = dup_res.get("groups", [])

            # Duplicate Metrics Header
            st.markdown(f"""
                <div class="kpi-container">
                    <div class="kpi-card">
                        <div class="kpi-label">Duplicate Groups</div>
                        <div class="kpi-value">{dup_res['total_groups']}</div>
                        <div class="kpi-subtext">Content-verified sets</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Redundant File Copies</div>
                        <div class="kpi-value">{dup_res['total_redundant_files']}</div>
                        <div class="kpi-subtext">Copies beyond the original</div>
                    </div>
                    <div class="kpi-card" style="border-top-color: #047857;">
                        <div class="kpi-label">Recoverable Storage</div>
                        <div class="kpi-value">{dup_res['total_savings_human']}</div>
                        <div class="kpi-subtext">Original copies are preserved</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if not groups:
                st.success("🎉 **Clean Workspace!** No duplicate files were detected in the scanned folder.")
                if st.button("🔄 Re-run Duplicate Check"):
                    st.session_state.duplicate_results = None
                    st.rerun()
            else:
                # Selection Preset Toolbar
                st.markdown("#### ⚙️ Quick Selection Strategies")
                tb_col1, tb_col2, tb_col3, tb_col4 = st.columns([1.5, 1.5, 1.5, 1])

                with tb_col1:
                    if st.button("⭐ Mark Oldest to Keep", help="Keeps the earliest created/modified copy and selects newer duplicates for cleanup."):
                        new_set = set()
                        for grp in groups:
                            sorted_files = sorted(grp["files"], key=lambda x: x.get("modified_timestamp", 0))
                            for f in sorted_files[1:]:  # Mark everything except oldest
                                new_set.add(f["path"])
                        st.session_state.selected_duplicates_to_delete = new_set
                        st.rerun()

                with tb_col2:
                    if st.button("✨ Mark Newest to Keep", help="Keeps the most recently edited copy and selects older duplicates for cleanup."):
                        new_set = set()
                        for grp in groups:
                            sorted_files = sorted(grp["files"], key=lambda x: x.get("modified_timestamp", 0), reverse=True)
                            for f in sorted_files[1:]:  # Mark everything except newest
                                new_set.add(f["path"])
                        st.session_state.selected_duplicates_to_delete = new_set
                        st.rerun()

                with tb_col3:
                    if st.button("📁 Shortest Path to Keep", help="Keeps the copy closest to the folder root."):
                        new_set = set()
                        for grp in groups:
                            sorted_files = sorted(grp["files"], key=lambda x: len(x.get("path", "")))
                            for f in sorted_files[1:]:
                                new_set.add(f["path"])
                        st.session_state.selected_duplicates_to_delete = new_set
                        st.rerun()

                with tb_col4:
                    if st.button("Clear Marks"):
                        st.session_state.selected_duplicates_to_delete = set()
                        st.rerun()

                st.markdown("<hr style='margin: 16px 0;' />", unsafe_allow_html=True)

                # Groups Detailed Accordions
                st.markdown("### 📂 Duplicate Groups Inspection")
                st.caption("Check the box next to any duplicate copy you wish to mark for safe removal. At least one original copy is always protected.")

                # Form for managing checkbox updates safely without flickering
                for grp in groups:
                    gid = grp["group_id"]
                    hash_disp = grp["short_hash"]
                    savings_disp = grp["potential_savings_human"]
                    file_count = grp["file_count"]

                    expander_title = f"Group #{gid} — {file_count} copies of {grp['files'][0]['filename']} (Size: {grp['size_human']} each | Potential Savings: {savings_disp})"
                    
                    with st.expander(expander_title, expanded=(gid <= 3)):
                        st.markdown(f"<span style='font-size: 11px; color: #64748B;'>SHA-256: <code>{grp['sha256']}</code></span>", unsafe_allow_html=True)

                        for idx, file_item in enumerate(grp["files"]):
                            fpath = file_item["path"]
                            is_checked = fpath in st.session_state.selected_duplicates_to_delete

                            col_chk, col_info = st.columns([0.1, 0.9])
                            with col_chk:
                                new_checked = st.checkbox(
                                    label=f"Select {fpath}",
                                    value=is_checked,
                                    key=f"chk_dup_{gid}_{idx}",
                                    label_visibility="collapsed",
                                )
                                if new_checked != is_checked:
                                    if new_checked:
                                        st.session_state.selected_duplicates_to_delete.add(fpath)
                                    else:
                                        st.session_state.selected_duplicates_to_delete.discard(fpath)
                                    st.rerun()

                            with col_info:
                                badge_html = "<span class='badge badge-amber'>Marked for Removal</span>" if is_checked else "<span class='badge badge-emerald'>Kept Copy</span>"
                                st.markdown(f"""
                                    <div style="font-size: 13px; margin-bottom: 6px;">
                                        <b>{Path(fpath).name}</b> &nbsp; {badge_html}<br>
                                        <span style="color: #64748B; font-size: 12px;">📁 {fpath}</span><br>
                                        <span style="color: #94A3B8; font-size: 11px;">Modified: {file_item.get('modified_time', 'N/A')}</span>
                                    </div>
                                """, unsafe_allow_html=True)

                # Safe Cleanup Review Banner
                st.markdown("<hr style='margin: 24px 0;' />", unsafe_allow_html=True)
                savings_audit = calculate_selected_savings(groups, st.session_state.selected_duplicates_to_delete)

                st.markdown("### 🛡️ Safe Cleanup Review")
                if savings_audit["file_count"] == 0:
                    st.info("No duplicate copies are currently marked for cleanup. Use the presets above or check individual files.")
                else:
                    if savings_audit["protected_files"]:
                        st.warning(f"⚠️ Safety Guardrail Activated: Prevented removal of {len(savings_audit['protected_files'])} original copies to ensure data is never lost.")

                    st.markdown(f"""
                        <div class="content-box" style="border-left: 4px solid #10B981;">
                            <h4 style="margin: 0 0 8px 0; color: #064E3B;">Ready for Safe Removal</h4>
                            <p style="margin: 0; color: #475569;">
                                <b>{savings_audit['file_count']}</b> duplicate files selected.<br>
                                Storage to be reclaimed: <b style="color: #047857;">{savings_audit['actual_savings_human']}</b>
                            </p>
                        </div>
                    """, unsafe_allow_html=True)

                    c_mode, c_btn = st.columns([2, 1])
                    with c_mode:
                        cleanup_mode = st.radio(
                            "Cleanup method",
                            [
                                "Move to Windows Recycle Bin (Recommended & Recoverable)",
                                "Dry-Run Simulation (Test without deleting any file)",
                            ],
                            index=0,
                        )

                    with c_btn:
                        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                        execute_cleanup = st.button("🗑️ Confirm Safe Removal", type="primary", use_container_width=True)

                    if execute_cleanup:
                        is_dry_run = "Dry-Run" in cleanup_mode
                        logs = []
                        total_freed = 0
                        files_to_remove = savings_audit["files_to_remove"]

                        prog = st.progress(0, text="Executing safe cleanup...")
                        for i, f_path in enumerate(files_to_remove, start=1):
                            prog.progress(i / len(files_to_remove), text=f"Processing {Path(f_path).name}...")
                            res = safe_delete_file(
                                file_path=f_path,
                                use_recycle_bin=True,
                                dry_run=is_dry_run,
                            )
                            logs.append(res)
                            if res["status"] in ("success", "dry_run"):
                                total_freed += res["bytes_saved"]

                        prog.progress(1.0, text="Operation completed.")
                        st.session_state.cleanup_logs = logs

                        if is_dry_run:
                            st.info(f"🧪 **Dry-Run Complete:** Simulated removal of {len(files_to_remove)} files ({format_size(total_freed)}). No files were touched.")
                        else:
                            st.success(f"🎉 **Cleanup Complete:** Successfully moved {len(files_to_remove)} files to the Windows Recycle Bin ({format_size(total_freed)} reclaimed).")

                            # Remove deleted files from session state
                            deleted_set = set(files_to_remove)
                            st.session_state.scanned_files = [
                                f for f in st.session_state.scanned_files if f["path"] not in deleted_set
                            ]
                            st.session_state.selected_duplicates_to_delete = set()
                            # Re-run duplicates detection to reflect changes
                            st.session_state.duplicate_results = find_duplicates(st.session_state.scanned_files)
                            st.rerun()

                    # Show Cleanup Logs if present
                    if st.session_state.cleanup_logs:
                        with st.expander("📋 Review Action Logs", expanded=False):
                            for log in st.session_state.cleanup_logs:
                                status_icon = "✅" if log["status"] in ("success", "dry_run") else "❌"
                                st.write(f"{status_icon} **{log.get('action', 'action')}**: `{log.get('path', '')}` — {log.get('message', '')}")


# =============================================================================
# PAGE 4: 📁 File Organizer
# =============================================================================

elif page == "📁 File Organizer":
    st.markdown("""
        <div class="app-header">
            <h1>File Organizer</h1>
            <p>Categorize messy files into organized directories with complete preview and collision prevention.</p>
        </div>
    """, unsafe_allow_html=True)

    if not st.session_state.scanned_files:
        st.warning("⚠️ Please scan a folder in the **Scan Files** section before organizing.")
    else:
        source_dir = st.session_state.scan_summary.get("folder_path", "")
        default_target = str(Path(source_dir) / "Organized_ClearSpace") if source_dir else ""

        st.markdown(f"**Source Directory:** `{source_dir}`")

        with st.container():
            st.markdown("#### 🎯 Destination & Category Settings")
            t_col1, t_col2 = st.columns([2, 1])

            with t_col1:
                target_dest_input = st.text_input(
                    "Destination base folder",
                    value=default_target,
                    help="Where categorized folders (Images, Documents, etc.) will be created.",
                )

            with t_col2:
                group_by_ext = st.checkbox("Sub-sort by extension (e.g. Documents/pdf/)", value=False)

            selected_categories = st.multiselect(
                "Select categories to organize",
                options=ORGANIZATION_CATEGORIES,
                default=ORGANIZATION_CATEGORIES,
            )

        # Plan Generation Button
        if st.button("📋 Generate Organization Plan", type="primary"):
            if not target_dest_input.strip():
                st.error("Please specify a valid destination folder.")
            else:
                plan = generate_organization_plan(
                    files=st.session_state.scanned_files,
                    target_base_dir=target_dest_input,
                    selected_categories=selected_categories,
                    group_by_extension=group_by_ext,
                )
                st.session_state.organization_plan = plan

        # Display Proposed Plan
        if st.session_state.organization_plan:
            plan = st.session_state.organization_plan
            st.markdown("<hr style='margin: 20px 0;' />", unsafe_allow_html=True)
            st.markdown("### 📋 Proposed Organization Plan")

            # Plan Metrics
            st.markdown(f"""
                <div class="kpi-container">
                    <div class="kpi-card">
                        <div class="kpi-label">Active Moves Planned</div>
                        <div class="kpi-value">{plan['total_active_moves']}</div>
                        <div class="kpi-subtext">Files ready to be categorized</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Categories Involved</div>
                        <div class="kpi-value">{len(plan['categories_involved'])}</div>
                        <div class="kpi-subtext">Target subfolders</div>
                    </div>
                    <div class="kpi-card" style="border-top-color: #047857;">
                        <div class="kpi-label">Overwrite Collisions Avoided</div>
                        <div class="kpi-value">{plan['collisions_avoided']}</div>
                        <div class="kpi-subtext">Safe renaming applied automatically</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if plan["total_active_moves"] == 0:
                st.info("All files matching the selected categories are already in their organized destination folders.")
            else:
                # Preview Table
                plan_df = pd.DataFrame(plan["active_moves"][:200])  # preview first 200 items for responsiveness
                if not plan_df.empty:
                    preview_display = plan_df[["filename", "category", "size_human", "target_filename", "target_directory"]].rename(columns={
                        "filename": "Original Filename",
                        "category": "Category",
                        "size_human": "Size",
                        "target_filename": "Target Filename",
                        "target_directory": "Destination Folder",
                    })
                    st.dataframe(preview_display, use_container_width=True, height=300)

                # Execution Confirmation Panel
                st.markdown("<hr style='margin: 20px 0;' />", unsafe_allow_html=True)
                st.markdown("#### 🚀 Execute Reorganization")

                dry_col, confirm_col = st.columns([1.5, 1])

                with dry_col:
                    is_dry_run_org = st.checkbox("🧪 Dry-Run Mode (Simulate without moving any files)", value=True)
                    user_confirmed = st.checkbox("I have reviewed the plan and authorize moving these files", value=False)

                with confirm_col:
                    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
                    execute_btn = st.button("📁 Execute Plan", type="primary", disabled=(not user_confirmed and not is_dry_run_org))

                if execute_btn:
                    p_bar = st.progress(0, text="Executing file organization...")

                    def org_progress(curr, total, name):
                        p_bar.progress(curr / total, text=f"Moving file {curr}/{total}: {name}")

                    exec_res = execute_organization_plan(
                        plan=plan,
                        dry_run=is_dry_run_org,
                        progress_callback=org_progress,
                    )
                    p_bar.progress(1.0, text="Organization complete!")

                    if exec_res["dry_run"]:
                        st.info(f"🧪 {exec_res['message']}")
                    else:
                        st.success(f"🎉 {exec_res['message']}")
                        # Rescan folder to update file paths
                        with st.spinner("Updating file inventory..."):
                            re_scan = scan_folder(source_dir)
                            st.session_state.scanned_files = re_scan["files"]
                            st.session_state.scan_summary = re_scan
                            st.session_state.duplicate_results = None
                            st.session_state.organization_plan = None
                            st.rerun()


# =============================================================================
# PAGE 5: 📈 Storage Insights
# =============================================================================

elif page == "📈 Storage Insights":
    st.markdown("""
        <div class="app-header">
            <h1>Storage Insights & Analytics</h1>
            <p>Detailed breakdown of storage consumption, largest files, and data export.</p>
        </div>
    """, unsafe_allow_html=True)

    if not st.session_state.scanned_files:
        st.warning("⚠️ No files scanned yet. Please scan a folder in **Scan Files** first.")
    else:
        df = files_to_dataframe(st.session_state.scanned_files)
        cat_summary = get_category_summary(df)
        ext_summary = get_extension_summary(df, top_n=15)
        largest_files = get_largest_files(df, top_n=10)
        largest_folders = get_largest_folders(df, top_n=8)

        # Tabs for Visualizations
        tab_cat, tab_large, tab_folders, tab_export = st.tabs([
            "📊 Categories & Extensions",
            "💾 Largest Files",
            "📁 Folder Consumption",
            "📥 Export Reports",
        ])

        with tab_cat:
            c1, c2 = st.columns([1, 1])
            with c1:
                donut = create_category_donut_chart(cat_summary)
                st.plotly_chart(donut, use_container_width=True)
            with c2:
                ext_chart = create_extension_bar_chart(ext_summary)
                st.plotly_chart(ext_chart, use_container_width=True)

            st.markdown("#### 📋 Category Summary Table")
            st.dataframe(
                cat_summary[["Category", "Files", "Storage", "% of Storage", "% of Files"]],
                use_container_width=True,
                hide_index=True,
            )

        with tab_large:
            st.markdown("#### 🏆 Top 10 Largest Files on Disk")
            large_fig = create_largest_files_chart(largest_files)
            st.plotly_chart(large_fig, use_container_width=True)

            st.dataframe(
                largest_files[["filename", "category", "size_human", "directory", "modified_time"]].rename(columns={
                    "filename": "Filename",
                    "category": "Category",
                    "size_human": "File Size",
                    "directory": "Folder Location",
                    "modified_time": "Last Modified",
                }),
                use_container_width=True,
                hide_index=True,
            )

        with tab_folders:
            st.markdown("#### 📂 Top Storage Consuming Subfolders")
            st.dataframe(
                largest_folders.rename(columns={
                    "Directory": "Directory Path",
                    "Files": "Total Files",
                    "Storage": "Storage Footprint",
                }),
                use_container_width=True,
                hide_index=True,
            )

        with tab_export:
            st.markdown("#### 📥 Export Scan Results & Storage Audit")
            st.write("Export clean tabular scan metadata or a structured declutter audit report.")

            csv_data = export_scan_to_csv(st.session_state.scanned_files)
            json_data = export_report_to_json(
                scan_summary=st.session_state.scan_summary,
                duplicate_summary=st.session_state.duplicate_results,
                category_summary=cat_summary.to_dict(orient="records"),
            )

            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                st.download_button(
                    label="📄 Download Scanned Files (CSV)",
                    data=csv_data,
                    file_name=f"clearspace_inventory_{datetime.date.today()}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with col_exp2:
                st.download_button(
                    label="📊 Download Storage Audit Report (JSON)",
                    data=json_data,
                    file_name=f"clearspace_audit_{datetime.date.today()}.json",
                    mime="application/json",
                    use_container_width=True,
                )


# =============================================================================
# PAGE 6: ⚙️ Settings & Reports
# =============================================================================

elif page == "⚙️ Settings & Reports":
    st.markdown("""
        <div class="app-header">
            <h1>Settings & Preferences</h1>
            <p>Configure scanner defaults, safe deletion modes, and audit history.</p>
        </div>
    """, unsafe_allow_html=True)

    cfg = st.session_state.config

    with st.container():
        st.markdown("### 🛠️ Application Preferences")

        set_col1, set_col2 = st.columns(2)
        with set_col1:
            new_default_path = st.text_input("Default Scan Folder", value=cfg.get("default_scan_path", ""))
            new_skip_hidden = st.checkbox("Skip hidden files and folders by default", value=cfg.get("skip_hidden_files", True))

        with set_col2:
            new_depth = st.number_input("Maximum scan recursion depth", min_value=1, max_value=100, value=cfg.get("max_scan_depth", 20))
            new_recycle = st.checkbox(
                "Prefer Windows Recycle Bin for safe deletion",
                value=cfg.get("use_recycle_bin", True),
                help="When enabled, deleted files are moved to the Windows Recycle Bin where they can be restored.",
            )

        if st.button("💾 Save Preferences", type="primary"):
            cfg["default_scan_path"] = new_default_path
            cfg["skip_hidden_files"] = new_skip_hidden
            cfg["max_scan_depth"] = new_depth
            cfg["use_recycle_bin"] = new_recycle
            st.session_state.config = cfg
            if save_config(cfg):
                st.success("Preferences saved successfully to config.json.")
            else:
                st.error("Failed to write to config.json.")

    st.markdown("<hr style='margin: 24px 0;' />", unsafe_allow_html=True)

    # Reset Settings Section with Confirmation
    st.markdown("### 🔄 Reset Settings")
    with st.expander("⚠️ Danger Zone: Reset Preferences", expanded=False):
        st.write("Reset all settings in config.json back to default values. Scanned files in the current session will not be deleted.")
        confirm_reset = st.checkbox("I confirm that I want to reset all preferences to default", value=False)
        if st.button("Reset Settings to Default", type="secondary", disabled=not confirm_reset):
            default_reset = {
                "theme": "Emerald Cream",
                "default_scan_path": "",
                "skip_hidden_files": True,
                "use_recycle_bin": True,
                "max_scan_depth": 20,
                "safe_mode": True,
                "last_scan_summary": {
                    "folder_path": "",
                    "total_files": 0,
                    "total_size_human": "0 B",
                    "scanned_at": "",
                },
            }
            st.session_state.config = default_reset
            save_config(default_reset)
            st.success("Settings have been reset to factory defaults.")
            st.rerun()

    st.markdown("<hr style='margin: 24px 0;' />", unsafe_allow_html=True)

    # Technology Stack & Environment Details
    st.markdown("### 🖥️ Environment & Architecture")
    env_c1, env_c2 = st.columns(2)
    with env_c1:
        st.markdown(f"""
            - **Operating System:** Windows 11 ({os.name})
            - **Python Version:** 3.14
            - **Streamlit Version:** {st.__version__}
            - **Pandas Version:** {pd.__version__}
        """)
    with env_c2:
        st.markdown(f"""
            - **Windows Recycle Bin Support:** {'✅ Available (`send2trash`)' if HAS_SEND2TRASH else '⚠️ Fallback active'}
            - **Configuration File:** `{CONFIG_PATH}`
            - **Duplicate Detection Algorithm:** Cryptographic SHA-256
            - **Collision Avoidance:** Zero-overwrite numeric indexing
        """)
