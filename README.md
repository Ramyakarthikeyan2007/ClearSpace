# ClearSpace — Smart Digital Declutter 🌿

A modern, safety-first desktop file management and decluttering dashboard built with **Python**, **Streamlit**, **Pandas**, and **Plotly**. Designed for local desktop productivity on Windows 11, ClearSpace helps users visualize disk usage, detect true content duplicates via SHA-256 cryptographic hashing, reorganize files into structured categories, and reclaim storage safely.

---

## 🌟 Key Features

### 📊 Modern Executive Dashboard
- **Instant Storage KPIs:** Total files, storage consumed, duplicate groups detected, and recoverable storage savings.
- **Interactive Visualizations:** Donut charts for storage distribution by file category and bar charts for top file extensions.
- **Active Workspace Status:** Displays the current scanned directory path, last scan timestamp, and directory health.
- **Zero-Config Demo Mode:** One-click synthetic demo folder creation with instant sample files and duplicates.

### 🔍 Safe Recursive Folder Scanner
- **Recursive Directory Traversal:** Scans arbitrary local directories and subfolders with real-time progress indicators.
- **Deep Metadata Extraction:** Filename, size in human-friendly units (KB, MB, GB), extension, category, folder path, and modification timestamps.
- **Interactive Filters & Sorting:** Filter by category, extension, or filename keywords, and sort by size, name, or last modified date.
- **Safety Guardrails:** Blocks scanning system drive roots (`C:\`) and protected Windows directories. Strictly ignores symbolic links and junctions to prevent infinite loops. Gracefully skips locked or permission-denied files without crashing.

### 👥 Cryptographic Duplicate File Finder
- **True Content Verification:** Uses SHA-256 chunked streaming hashes rather than relying on misleading filenames or timestamps.
- **Optimized Two-Pass Detection:** Pre-buckets files by exact byte size to eliminate unneeded disk I/O on unique files.
- **Accurate Savings Calculation:** Calculates space savings as $(N - 1) \times \text{Size}$ for $N$ copies—never falsely counting the original file as removable space.
- **Intelligent Keep Strategies:** One-click presets to **Keep Oldest (Original)**, **Keep Newest**, or **Keep Shortest Path**.
- **Data Protection Enforcement:** Automatically blocks the deletion of every copy in a duplicate set, guaranteeing at least one original copy is always preserved.

### 📁 Smart File Organizer
- **Automated Categorization:** Classifies files into 8 core categories: `Images`, `Documents`, `Videos`, `Audio`, `Archives`, `Code`, `Spreadsheets`, and `Others`.
- **Pre-Move Plan Generation:** Full preview table detailing each file's source path, intended destination, and category.
- **Zero-Overwrite Collision Avoidance:** If a file with the same name exists at the destination, ClearSpace automatically renames the incoming file to `filename (1).ext` or `filename (2).ext`.
- **Granular Category Filtering:** Choose which categories to organize and optionally enable sub-sorting by extension (e.g., `Documents/pdf/`).

### 🛡️ Safe Cleanup & Windows Recycle Bin Integration
- **Windows Recycle Bin Support:** Moves removed files to the Windows Recycle Bin using `send2trash`, allowing instant user recovery.
- **Dry-Run Simulation:** Test duplicate deletions or file relocations with 100% fidelity before committing changes to disk.
- **Transparent Action Logs:** Detailed execution reports documenting successes, skips, and errors.

### 📈 Storage Insights & Reports
- **Deep Analytics:** Pandas-powered tabular summaries showing storage percentage and file count shares.
- **Plotly Visuals:** Interactive charts of top file extensions, largest individual files, and heaviest directories.
- **Data Export:** Export full scanned file inventories to **CSV** or complete declutter audit summaries to **JSON**.

### ⚙️ Persistent Configuration
- Stores preferences and recent scan summaries in `config.json`.
- Settings include default scan directory, hidden files toggle, recursion depth limits, and Recycle Bin preferences.
- Built-in Reset Settings option with explicit confirmation.

---

## 🛠️ Technology Stack

| Technology | Purpose |
| :--- | :--- |
| **Python 3.10+** | Core application logic, path safety, and hashing |
| **Streamlit** | Responsive, modern desktop web interface |
| **Pandas** | Tabular data processing, grouping, and aggregations |
| **Plotly** | High-performance interactive data visualizations |
| **JSON** | Configuration persistence and report generation |
| **Send2Trash** | Native Windows Recycle Bin deletion integration |
| **unittest** | Standard-library unit test framework |

---

## 📁 Project Structure

```text
ClearSpace/
├── app.py                     # Streamlit desktop dashboard & user interface
├── scanner.py                 # Recursive directory scanner & categorization logic
├── duplicate_finder.py        # SHA-256 duplicate detection & savings calculation
├── organizer.py               # File organization planning & collision avoidance
├── storage_insights.py        # Pandas aggregations, Plotly charts, & CSV/JSON export
├── safety.py                  # Path guardrails, collision safety, & Recycle Bin wrapper
├── requirements.txt           # Project dependencies
├── README.md                  # Complete documentation and usage guide
├── .gitignore                 # Standard Python, IDE, and temporary ignore rules
├── config.json                # User settings and last scan summary storage
└── tests/                     # Built-in unit test suite
    ├── test_scanner.py        # Tests for scanning, categorization, and symlink safety
    ├── test_duplicates.py     # Tests for SHA-256 detection and savings calculations
    ├── test_organizer.py      # Tests for collision avoidance and dry-run execution
    └── test_storage_insights.py # Tests for DataFrame analytics and Plotly figures
```

---

## 💻 Windows 11 Installation & Quick Start

Follow these steps in **PowerShell** or **Command Prompt** on Windows 11.

### 1. Prerequisites
Ensure Python 3.10 or newer is installed on your system.
```powershell
python --version
```

### 2. Navigate to the Project Folder
```powershell
cd ClearSpace
```

### 3. Create and Activate a Virtual Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# (Or Command Prompt)
.\venv\Scripts\activate.bat
```

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5. Run the Automated Test Suite
Verify that all unit tests pass before launching the application:
```powershell
python -m unittest discover tests -v
```

### 6. Launch ClearSpace
```powershell
streamlit run app.py
```
ClearSpace will automatically launch in your default web browser at `http://localhost:8501`.

---

## 📖 Step-by-Step User Guide

### 1. Launching and Exploring the Dashboard
1. On the **📊 Dashboard**, click **"🚀 Create & Scan Synthetic Demo Workspace"** to immediately generate and inspect a mock folder with duplicates and documents in one click.
2. Review the top KPI cards and interactive Plotly storage distribution charts.

### 2. Scanning a Local Directory
1. Navigate to **🔍 Scan Files** in the sidebar.
2. Paste or type any folder path (e.g., `C:\Users\YourName\Downloads` or `C:\Users\YourName\Documents`).
3. Click **"🚀 Start Recursive Scan"**.
4. Use the search bar, category dropdown, or size sorter to browse your scanned files.

### 3. Detecting & Reclaiming Duplicate Files
1. Navigate to **👥 Duplicate Finder**.
2. Click **"🔍 Find Duplicates in Scanned Files"**.
3. Inspect duplicate groups sorted by potential space savings.
4. Use the quick presets:
   - **Mark Oldest to Keep:** Preserves original creation dates and marks subsequent copies for deletion.
   - **Mark Newest to Keep:** Keeps the latest modified version.
   - **Shortest Path to Keep:** Keeps the copy closest to the folder root.
5. In the **Safe Cleanup Review** section, select **Move to Windows Recycle Bin** (or **Dry-Run Simulation** to preview).
6. Click **"🗑️ Confirm Safe Removal"**.

### 4. Reorganizing Files into Categories
1. Navigate to **📁 File Organizer**.
2. Set your target destination folder (defaults to `<source_path>/Organized_ClearSpace`).
3. Select which categories to organize (e.g., Images, Documents, Code).
4. Click **"📋 Generate Organization Plan"**.
5. Inspect the preview table. Note any overwrite collisions that have been safely renamed to `filename (1).ext`.
6. Select **Dry-Run Mode** first to simulate, or uncheck it, check the confirmation box, and click **"📁 Execute Plan"**.

### 5. Reviewing Analytics and Exporting Reports
1. Navigate to **📈 Storage Insights**.
2. Inspect the **Donut Chart**, **Top Extensions Chart**, **Top 10 Largest Files**, and **Folder Consumption**.
3. Click **"📄 Download Scanned Files (CSV)"** to save the raw inventory, or **"📊 Download Storage Audit Report (JSON)"** to save an executive summary report.

### 6. Managing Settings
1. Navigate to **⚙️ Settings & Reports**.
2. Configure a default scan directory or recursion depth limit.
3. If necessary, use **Reset Settings** to restore factory defaults.

---

## 🛡️ Safety & Reliability Principles

1. **Strict No-Modification Guarantee During Scan:** ClearSpace only reads file metadata and content streams during scanning and hashing. Disk modifications never occur during inspection.
2. **Explicit User Confirmation:** Potentially destructive actions (moving or recycling files) require explicit button clicks and checkboxes.
3. **No Accidental Total Deletion:** ClearSpace's duplicate protection engine enforces that at least one original copy in every duplicate group remains untouched.
4. **Collision Avoidance:** Moving a file into a folder that already contains a file with that name never overwrites the existing file; ClearSpace safely appends a numbered index (`(1)`, `(2)`).
5. **No System Directory Access:** Hardcoded safety blocks prevent users from scanning `C:\`, `C:\Windows`, or system folders.
6. **No Symbolic Link Traversal:** Prevents directory recursion traps or escaping target boundaries.
7. **Native Windows Recycle Bin:** Files are moved to the Windows Recycle Bin rather than permanently erased, providing an undo safety net.

---

## 📸 Interface Preview (Placeholders)

### Dashboard & KPI Overview
```text
+-----------------------------------------------------------------------------------+
| 🌿 ClearSpace — Smart Digital Declutter                                           |
| Total Files: 1,245 | Storage: 4.82 GB | Duplicate Groups: 18 | Savings: 680 MB   |
| [ Donut Chart: Category Share ]           [ Bar Chart: Storage by Extension ]     |
+-----------------------------------------------------------------------------------+
```

### Duplicate Finder & Safe Cleanup
```text
+-----------------------------------------------------------------------------------+
| 👥 Duplicate Finder                                                               |
| Group #1 — 3 copies of Draft_v1.txt (Size: 15.2 MB | Recoverable: 30.4 MB)        |
| [ ] Draft_v1.txt (Kept Original)            - C:\Docs\Draft_v1.txt                |
| [X] Draft_Copy.txt (Marked for Recycle Bin) - C:\Downloads\Draft_Copy.txt         |
| [X] Draft_Backup.txt (Marked for Recycle)   - C:\Backup\Draft_Backup.txt          |
+-----------------------------------------------------------------------------------+
```

---

## ⚠️ Known Limitations & Edge Cases

- **Locked Files:** Files currently open with exclusive write locks in other applications (e.g., active Word documents or database files) cannot be moved or deleted until closed.
- **Cloud-Only Placeholders:** Files managed by OneDrive or iCloud that are stored purely in the cloud (stub files with 0 local hydrated bytes) will reflect local storage statistics.
- **Read-Only / Elevated Privileges:** Folders requiring elevated Administrator permissions will be safely skipped and logged in the scan errors table.

---

## 📜 License & Portfolio Attribution

Developed by a Computer Science student as a portfolio application demonstrating modern Python, clean software architecture, defensive systems programming, and Streamlit dashboard design.
