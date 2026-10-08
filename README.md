# 👴 Boomer CRM

> **The Ultra-Accessible, High-Visibility Desktop CRM & Field Operations Suite**  
> Built with extra-large typography, high-contrast layouts, and zero clutter — because running a field service or pest control business shouldn't require squinting at tiny spreadsheet cells.

---

## 👓 Why "Boomer CRM"?

Most modern business software is crowded with micro-fonts, hidden dropdown menus, and confusing tabs designed for teenagers. 

**Boomer CRM was built with a different philosophy:**
* **Large, Readable Typography**: Scalable 16pt–28pt typography so you can read customer details from across the desk without searching for reading glasses.
* **Big Tactile Buttons & Clean Cards**: Massive, clickable action targets — no hunting for 10-pixel icons.
* **Forgiving Search**: Fast bilingual phonetic search (Greek & Latin) that understands typos, phonetic spellings, and missing accents.
* **100% Offline & Private**: Runs locally on your computer with a lightning-fast SQLite engine. No cloud subscriptions, no forced updates, no internet required.

---

## 🌟 Key Features

* 🌐 **Bilingual Interface & Instant Language Toggle**: Full bilingual support (🇬🇧 English & 🇬🇷 Greek) with an instant language switcher in Settings that updates the entire UI in real time.
* 🔍 **Phonetic Instant Search**: Real-time C-speed database lookup across customer names, account codes, mobile/landline numbers, tax IDs (AFM), and addresses.
* 👥 **Client Management**: Full support for commercial B2B accounts and residential B2C customers, including dual addresses, dual phone numbers, tax offices (DOY), contact persons, and balance tracking.
* 🧩 **Schemaless EAV Attributes**: Need to track custom notes or unusual property traits? The dynamic modal editor saves custom JSON fields without messing up the database.
* 📅 **Dispatch Calendar & Crew Scheduling**: Visual scheduling for field teams (Pest Control, Disinfection, Rodent Control, Fumigation) with clear time slots and assignment notes.
* 🧮 **Bidirectional 24% VAT Calculator**: Type in net price or gross total — VAT and totals synchronize automatically in real time.
* 💳 **Simple Payment Ledger**: Log Cash, Bank Transfer, or Card payments in one click with live debit/credit reconciliation.
* 📈 **Clear Analytics**: High-level visual summaries of monthly turnover, collected payments, and pending balances.
* 🛡️ **Built-in Backup & Maintenance**: Automatic database indexing, one-click snapshots, and full CSV export.

---

## 📸 Core Modules

| Module | Purpose |
| :--- | :--- |
| **Client Registry** | Easy-to-read client cards with phone numbers, addresses, and balance indicators. |
| **Calendar & Dispatch** | Daily/monthly appointment planner with crew filtering and time-slot tracking. |
| **Financial Ledger** | Central payment registry linking transactions directly to customer balances. |
| **Analytics** | Big, bold summaries of business performance and service categories. |
| **Settings** | Customize crew rosters, service categories, payment methods, and font scaling. |
| **Recovery Center** | Create timestamped database backup archives and export data to CSV. |

---

## 🚀 Quick Start

### 1. Requirements
* **Python 3.10+** installed on Windows, macOS, or Linux.

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/your-username/boomer-crm.git
cd boomer-crm
pip install -r requirements.txt
```

### 3. Launching

Run directly with Python:

```bash
python run_app.py
```

Or on Windows, simply double-click the included batch launcher:

```bat
RUN_BOOMER_CRM.bat
```

---

## 🗄️ Database & Preloaded Sample Data

Boomer CRM automatically creates `company_data.db` upon initial launch.

To reset or test the database with realistic sample Greek commercial & residential clients:

```bash
python init_db.py
```

### Database Tables:
* **`clients`**: Customer records with phonetic index (`search_text`) and custom JSON attributes (`extra_fields`).
* **`jobs`**: Service operations linked to client accounts with pricing, 24% VAT, crews, and categories.
* **`payments`**: Transaction records with payment methods and balance linkages.
* **`app_config`**: Configuration table for crew members, service types, and payment options.

---

## 📦 Building Standalone Windows Executable (.exe)

Boomer CRM includes a PyInstaller build specification configured with CustomTkinter asset bundling.

To compile a standalone `.exe`:

```bash
pip install pyinstaller
pyinstaller app_gui.spec
```

The compiled binary will be generated inside the `dist/app_gui/` folder.

---

## 📂 Project Structure

```text
boomer-crm/
├── app_gui.py                # Main desktop GUI application (CustomTkinter)
├── app_gui.spec              # PyInstaller build configuration
├── company_data.db           # Local SQLite database preloaded with sample data
├── config.json               # UI font size, window size, and category preferences
├── init_db.py                # Database initializer & mock data generator
├── logic_engine.py           # Core business logic, queries & phonetic search engine
├── migrate_legacy_clients.py # Legacy data migration utility
├── requirements.txt          # Python dependencies (CustomTkinter, Pillow, DarkDetect)
├── run_app.py                # Python entrypoint launcher
├── RUN_BOOMER_CRM.bat        # Windows one-click desktop launcher
├── ui_config.py              # UI styles, theme tokens, and dynamic font scalers
└── .gitignore                # Git ignore rules
```

---

## 🛠️ Technology Stack

* **GUI Framework**: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
* **Language**: Python 3.10+
* **Database**: SQLite3 (WAL mode, custom phonetic indexing)
* **Executable Packager**: PyInstaller

---

## 📄 License

Distributed under the **[GNU General Public License v3.0 (GPLv3)](LICENSE)**. Free and open source copyleft license.
