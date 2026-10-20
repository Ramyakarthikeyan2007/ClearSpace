"""
storage_insights.py - Data Processing & Interactive Visualizations for ClearSpace
================================================================================
Uses Pandas for tabular data aggregation and Plotly for responsive, elegant charts
in an emerald-green and warm-cream aesthetic. Supports CSV and JSON report exports.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from safety import format_size


# Cohesive Emerald Green & Warm Cream Color Palette
EMERALD_PALETTE = [
    "#064E3B",  # Deep Forest Emerald
    "#047857",  # Rich Emerald
    "#059669",  # Classic Emerald
    "#10B981",  # Vibrant Emerald
    "#14B8A6",  # Teal Accent
    "#34D399",  # Soft Mint
    "#6EE7B7",  # Light Mint
    "#A7F3D0",  # Pale Mint
    "#D1FAE5",  # Cream Mint
]

CATEGORY_COLOR_MAP = {
    "Images": "#10B981",
    "Documents": "#059669",
    "Videos": "#047857",
    "Audio": "#14B8A6",
    "Archives": "#0D9488",
    "Code": "#34D399",
    "Spreadsheets": "#6EE7B7",
    "Others": "#9CA3AF",
}


def files_to_dataframe(files: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert a list of file metadata dictionaries to a clean Pandas DataFrame.
    """
    if not files:
        return pd.DataFrame(columns=[
            "filename", "category", "extension", "size_bytes",
            "size_human", "directory", "modified_time", "modified_timestamp", "path"
        ])

    df = pd.DataFrame(files)
    # Ensure numeric columns are properly typed
    df["size_bytes"] = pd.to_numeric(df["size_bytes"], errors="coerce").fillna(0).astype(int)
    if "modified_timestamp" in df.columns:
        df["modified_timestamp"] = pd.to_numeric(df["modified_timestamp"], errors="coerce").fillna(0)

    return df


def get_category_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate storage size, file counts, and percentage shares by category.
    """
    if df.empty:
        return pd.DataFrame(columns=["Category", "Files", "Storage (Bytes)", "Storage", "% of Storage", "% of Files"])

    total_bytes = df["size_bytes"].sum()
    total_files = len(df)

    grouped = df.groupby("category", as_index=False).agg(
        Files=("filename", "count"),
        Total_Bytes=("size_bytes", "sum")
    ).rename(columns={"category": "Category", "Total_Bytes": "Storage (Bytes)"})

    grouped = grouped.sort_values(by="Storage (Bytes)", ascending=False).reset_index(drop=True)

    grouped["Storage"] = grouped["Storage (Bytes)"].apply(format_size)
    grouped["% of Storage"] = ((grouped["Storage (Bytes)"] / (total_bytes if total_bytes > 0 else 1)) * 100).round(1)
    grouped["% of Files"] = ((grouped["Files"] / (total_files if total_files > 0 else 1)) * 100).round(1)

    return grouped


def get_extension_summary(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Aggregate file counts and storage size by file extension.
    """
    if df.empty:
        return pd.DataFrame(columns=["Extension", "Category", "Files", "Storage (Bytes)", "Storage"])

    total_bytes = df["size_bytes"].sum()

    grouped = df.groupby(["extension", "category"], as_index=False).agg(
        Files=("filename", "count"),
        Total_Bytes=("size_bytes", "sum")
    ).rename(columns={
        "extension": "Extension",
        "category": "Category",
        "Total_Bytes": "Storage (Bytes)"
    })

    grouped = grouped.sort_values(by="Storage (Bytes)", ascending=False).head(top_n).reset_index(drop=True)
    grouped["Storage"] = grouped["Storage (Bytes)"].apply(format_size)
    grouped["% of Storage"] = ((grouped["Storage (Bytes)"] / (total_bytes if total_bytes > 0 else 1)) * 100).round(1)

    return grouped


def get_largest_files(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Extract the largest individual files in the scanned dataset.
    """
    if df.empty:
        return pd.DataFrame(columns=["filename", "category", "size_human", "directory", "modified_time"])

    largest = df.sort_values(by="size_bytes", ascending=False).head(top_n).copy()
    largest["size_mb"] = (largest["size_bytes"] / (1024 * 1024)).round(2)
    return largest.reset_index(drop=True)


def get_largest_folders(df: pd.DataFrame, top_n: int = 8) -> pd.DataFrame:
    """
    Identify which directories consume the most storage.
    """
    if df.empty:
        return pd.DataFrame(columns=["Directory", "Files", "Storage (Bytes)", "Storage"])

    grouped = df.groupby("directory", as_index=False).agg(
        Files=("filename", "count"),
        Total_Bytes=("size_bytes", "sum")
    ).rename(columns={"directory": "Directory", "Total_Bytes": "Storage (Bytes)"})

    grouped = grouped.sort_values(by="Storage (Bytes)", ascending=False).head(top_n).reset_index(drop=True)
    grouped["Storage"] = grouped["Storage (Bytes)"].apply(format_size)

    return grouped


# =============================================================================
# Plotly Visualizations (Emerald-Green & Warm Cream)
# =============================================================================

def create_category_donut_chart(category_summary_df: pd.DataFrame) -> go.Figure:
    """
    Interactive donut chart visualizing storage usage across file categories.
    """
    if category_summary_df.empty or category_summary_df["Storage (Bytes)"].sum() == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No file data available to display",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="#64748B")
        )
        fig.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
        return fig

    # Map categories to custom colors
    colors = [CATEGORY_COLOR_MAP.get(cat, "#047857") for cat in category_summary_df["Category"]]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=category_summary_df["Category"],
                values=category_summary_df["Storage (Bytes)"],
                hole=0.55,
                marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>Storage: %{value:,} bytes<br>Share: %{percent}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title=dict(text="Storage Distribution by Category", font=dict(size=16, color="#064E3B", family="sans-serif")),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        height=380,
        margin=dict(l=20, r=20, t=50, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_extension_bar_chart(extension_summary_df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar chart showing the highest storage consuming file extensions.
    """
    if extension_summary_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No extension data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="#64748B")
        )
        fig.update_layout(height=350)
        return fig

    df_sorted = extension_summary_df.sort_values(by="Storage (Bytes)", ascending=True)

    fig = go.Figure(
        go.Bar(
            x=df_sorted["Storage (Bytes)"] / (1024 * 1024),  # in MB
            y=df_sorted["Extension"],
            orientation="h",
            marker=dict(
                color=df_sorted["Storage (Bytes)"],
                colorscale=[[0, "#A7F3D0"], [0.5, "#10B981"], [1.0, "#047857"]],
                line=dict(color="#064E3B", width=1),
            ),
            customdata=df_sorted[["Files", "Storage"]].values,
            hovertemplate="<b>Extension: %{y}</b><br>Storage: %{customdata[1]}<br>File Count: %{customdata[0]}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(text="Top Storage Consuming Extensions", font=dict(size=16, color="#064E3B")),
        xaxis=dict(title="Storage Size (MB)", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(title="File Extension"),
        height=380,
        margin=dict(l=20, r=20, t=50, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_largest_files_chart(largest_df: pd.DataFrame) -> go.Figure:
    """
    Bar chart illustrating the largest files discovered in the scan.
    """
    if largest_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No files to display", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=350)
        return fig

    df_sorted = largest_df.sort_values(by="size_bytes", ascending=True)
    # Truncate long filenames for visual clarity
    display_names = [
        name if len(name) <= 25 else name[:22] + "..."
        for name in df_sorted["filename"]
    ]

    fig = go.Figure(
        go.Bar(
            x=df_sorted["size_mb"],
            y=display_names,
            orientation="h",
            marker=dict(color="#059669", line=dict(color="#064E3B", width=1)),
            customdata=df_sorted[["filename", "size_human", "category"]].values,
            hovertemplate="<b>%{customdata[0]}</b><br>Size: %{customdata[1]}<br>Category: %{customdata[2]}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(text="Largest Files on Disk", font=dict(size=16, color="#064E3B")),
        xaxis=dict(title="File Size (MB)", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(title="Filename"),
        height=380,
        margin=dict(l=20, r=20, t=50, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def export_scan_to_csv(files: List[Dict[str, Any]]) -> str:
    """
    Export the scanned files list to a CSV string.
    """
    df = files_to_dataframe(files)
    return df.to_csv(index=False)


def export_report_to_json(
    scan_summary: Dict[str, Any],
    duplicate_summary: Optional[Dict[str, Any]] = None,
    category_summary: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Export a comprehensive scan and declutter report to a formatted JSON string.
    Does NOT store sensitive contents, only structural statistics and paths.
    """
    report = {
        "report_type": "ClearSpace Storage & Declutter Report",
        "generated_at": scan_summary.get("scanned_at"),
        "scan_summary": {
            "folder_path": scan_summary.get("folder_path"),
            "total_files": scan_summary.get("total_files", 0),
            "total_storage_bytes": scan_summary.get("total_size_bytes", 0),
            "total_storage_human": scan_summary.get("total_size_human", "0 B"),
            "error_count": len(scan_summary.get("errors", [])),
        },
        "category_summary": category_summary or [],
        "duplicate_summary": {
            "duplicate_groups": duplicate_summary.get("total_groups", 0) if duplicate_summary else 0,
            "redundant_files": duplicate_summary.get("total_redundant_files", 0) if duplicate_summary else 0,
            "potential_savings_bytes": duplicate_summary.get("total_savings_bytes", 0) if duplicate_summary else 0,
            "potential_savings_human": duplicate_summary.get("total_savings_human", "0 B") if duplicate_summary else "0 B",
        },
    }
    return json.dumps(report, indent=2)
