import json
import customtkinter as ctk


class UIConfig:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        # Default settings
        self.settings = {"font_size": 25, "lang": "el", "window_size": "1000x700"}
        self.load()
        
        self.strings = {
            "el": {
                # Sidebar Navigation
                "nav_clients": "👥  ΠΕΛΑΤΕΣ",
                "nav_calendar": "📅  ΕΡΓΑΣΙΕΣ",
                "nav_ledger": "💰  ΠΛΗΡΩΜΕΣ",
                "nav_analytics": "📊  ΑΝΑΛΥΤΙΚΑ",
                "nav_settings": "⚙️  ΡΥΘΜΙΣΕΙΣ",
                
                # Client Registry
                "search_placeholder": "Αναζήτηση με Όνομα, Τηλέφωνο ή ΑΦΜ (*κωδικός για ακριβή)...",
                "client_list_title": "Λίστα Πελατών",
                "select_client_prompt": "Επιλέξτε έναν πελάτη για προβολή.",
                "notes": "Σημειώσεις",
                "save_client": "💾  Αποθήκευση Πελάτη",
                "edit_client": "✏️  Επεξεργασία",
                "delete_client": "🗑️  Διαγραφή",
                "history": "Ιστορικό",
                "balance": "Υπόλοιπο:",
                "client_search_title": "Αναζήτηση Πελατών",
                "new_client_title": "Στοιχεία Νέου Πελάτη",
                
                # Settings Panel
                "settings_title": "Ρυθμίσεις Συστήματος",
                "ui_scaling_title": "⚙ UI Scaling & Γλώσσα",
                "font_size_label": "Μέγεθος Γραμματοσειράς:",
                "language_label": "Γλώσσα / Language",
                "backup_title": "🔒 Αντίγραφα Ασφαλείας & Εξαγωγή",
                "backup_desc": "Δημιουργεί αντίγραφο ασφαλείας της βάσης και εξάγει αρχεία CSV.",
                "backup_btn": "🚀 Εκτέλεση Αντιγράφου & Εξαγωγή CSV",
                "recovery_title": "🛠️ Κέντρο Ανάκτησης Δεδομένων",
                "recovery_desc": "Επιλέξτε ένα αυτόματο σημείο ελέγχου (BACKUP - DATE) ή αναζητήστε αρχείο .db:",
                "restore_btn": "⏪ Ανάκτηση Σημείου",
                "manual_pick_btn": "📁 Χειροκίνητη Επιλογή (.db)",
                "wipe_title": "⚠️ Ζώνη Κινδύνου",
                "wipe_btn": "🗑️ Οριστική Διαγραφή Όλων των Δεδομένων",
                "categories_title": "📋 Κατηγορίες Εργασιών",
                "subcategories_title": "🏷️ Υποκατηγορίες Εργασιών",
                "payment_methods_title": "💳 Τρόποι Πληρωμής",
                "crews_title": "👷 Μέλη Συνεργείων",
                
                # Jobs & Calendar
                "new_job_title": "Καταχώρηση Νέας Εργασίας",
                "job_date": "Ημερομηνία",
                "job_time": "Ώρα",
                "job_crew": "Συνεργείο",
                "job_cat1": "Κατηγορία 1",
                "job_cat2": "Κατηγορία 2",
                "job_price_net": "Τιμή προ ΦΠΑ (€)",
                "job_vat": "ΦΠΑ (24%)",
                "job_price_gross": "Τελική Τιμή (€)",
                "job_invoice": "Αριθμός Τιμολογίου",
                "save_job": "💾 Καταχώρηση Εργασίας",
                
                # Payments & Ledger
                "new_payment_title": "Καταχώρηση Πληρωμής",
                "payment_amount": "Ποσό Πληρωμής (€)",
                "payment_method": "Τρόπος Πληρωμής",
                "payment_date": "Ημερομηνία",
                "save_payment": "💾 Καταχώρηση Πληρωμής",
                
                # Analytics
                "analytics_title": "Οικονομικά & Επιχειρησιακά Αναλυτικά",
                "kpi_turnover": "Συνολικός Τζίρος",
                "kpi_pending": "Ανεξόφλητα Υπόλοιπα",
                "kpi_jobs": "Ολοκληρωμένες Εργασίες",
                
                # Common actions
                "save": "Αποθήκευση",
                "cancel": "Ακύρωση",
                "delete": "Διαγραφή",
                "edit": "Επεξεργασία",
                "close": "Κλείσιμο",
                "confirm": "Επιβεβαίωση"
            },
            "en": {
                # Sidebar Navigation
                "nav_clients": "👥  CLIENTS",
                "nav_calendar": "📅  JOBS & CALENDAR",
                "nav_ledger": "💰  PAYMENTS & LEDGER",
                "nav_analytics": "📊  ANALYTICS",
                "nav_settings": "⚙️  SETTINGS",
                
                # Client Registry
                "search_placeholder": "Search by Name, Phone, or VAT (*code for exact match)...",
                "client_list_title": "Client List",
                "select_client_prompt": "Select a client to view details.",
                "notes": "Notes",
                "save_client": "💾  Save Client",
                "edit_client": "✏️  Edit",
                "delete_client": "🗑️  Delete",
                "history": "History",
                "balance": "Balance:",
                "client_search_title": "Client Search",
                "new_client_title": "New Client Details",
                
                # Settings Panel
                "settings_title": "System Settings",
                "ui_scaling_title": "⚙ UI Scaling & Language",
                "font_size_label": "Font Size:",
                "language_label": "Language / Γλώσσα",
                "backup_title": "🔒 Data Backup & Export",
                "backup_desc": "Creates a timestamped database backup and exports CSV files.",
                "backup_btn": "🚀 Create Backup Snapshot & Export CSV",
                "recovery_title": "🛠️ Data Recovery & Restore Center",
                "recovery_desc": "Select an automatic backup checkpoint or browse for a .db file:",
                "restore_btn": "⏪ Restore Checkpoint",
                "manual_pick_btn": "📁 Browse (.db file)",
                "wipe_title": "⚠️ Danger Zone",
                "wipe_btn": "🗑️ Wipe All Database Records",
                "categories_title": "📋 Job Categories",
                "subcategories_title": "🏷️ Job Subcategories",
                "payment_methods_title": "💳 Payment Methods",
                "crews_title": "👷 Crew Members",
                
                # Jobs & Calendar
                "new_job_title": "Log New Job",
                "job_date": "Date",
                "job_time": "Time Slot",
                "job_crew": "Crew",
                "job_cat1": "Category 1",
                "job_cat2": "Category 2",
                "job_price_net": "Net Price (€)",
                "job_vat": "VAT (24%)",
                "job_price_gross": "Gross Price (€)",
                "job_invoice": "Invoice Number",
                "save_job": "💾 Log Job",
                
                # Payments & Ledger
                "new_payment_title": "Log New Payment",
                "payment_amount": "Payment Amount (€)",
                "payment_method": "Payment Method",
                "payment_date": "Date",
                "save_payment": "💾 Log Payment",
                
                # Analytics
                "analytics_title": "Financial & Operational Analytics",
                "kpi_turnover": "Total Revenue",
                "kpi_pending": "Pending Balances",
                "kpi_jobs": "Completed Jobs",
                
                # Common actions
                "save": "Save",
                "cancel": "Cancel",
                "delete": "Delete",
                "edit": "Edit",
                "close": "Close",
                "confirm": "Confirm"
            }
        }
        
        # Ensure crews and categories lists exist
        if "crews" not in self.settings:
            self.settings["crews"] = ["ΝΙΚΟΣ-ΓΙΩΡΓΟΣ", "ΚΩΣΤΑΣ", "ΝΙΚΟΣ"]
        if "categories" not in self.settings:
            self.settings["categories"] = ["ΑΠΕΝΤΟΜΩΣΗ (Pest Control)", "ΜΥΟΚΤΟΝΙΑ (Rodent Control)", "ΑΠΟΛΥΜΑΝΣΗ (Disinfection)"]
        if "payment_methods" not in self.settings:
            self.settings["payment_methods"] = ["ΜΕΤΡΗΤΑ (Cash)", "ΤΡΑΠΕΖΑ (Bank Transfer)", "ΚΑΡΤΑ (Card)"]

    def load(self):
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.settings.update(json.load(f))
        except FileNotFoundError:
            self.save()

    def save(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)

    def set_lang(self, lang_code):
        if lang_code in ["el", "en"]:
            self.settings["lang"] = lang_code
            self.save()

    def get_font(self, size_offset=0):
        return ctk.CTkFont(family="Segoe UI", size=self.settings.get("font_size", 25) + size_offset)

    def get_text(self, key):
        current_lang = self.settings.get("lang", "el")
        lang_dict = self.strings.get(current_lang, self.strings["el"])
        return lang_dict.get(key, self.strings["el"].get(key, key))

    def get_client_schema(self):
        is_en = self.settings.get("lang", "el") == "en"
        if is_en:
            return [
                ("Name", "name"), ("Phone", "phone"), ("Mobile (Phone 2)", "phone_2"),
                ("Address", "address"), ("Address 2", "address_2"), ("Area / City", "area"),
                ("VAT / Tax ID", "vat"), ("Profession", "profession")
            ]
        else:
            return [
                ("Όνομα", "name"), ("Τηλέφωνο", "phone"), ("Κινητό (Τηλ 2)", "phone_2"),
                ("Διεύθυνση", "address"), ("Διεύθυνση 2", "address_2"), ("Περιοχή", "area"),
                ("ΑΦΜ", "vat"), ("Επάγγελμα", "profession")
            ]

    def get_job_schema(self):
        is_en = self.settings.get("lang", "el") == "en"
        if is_en:
            return [
                ("Job Category", "job_type"), ("Subcategory", "subcategory"),
                ("Date", "date_logged"), ("Time Slot", "time_logged"),
                ("Invoice Number", "invoice_number"), ("Job Notes", "notes")
            ]
        else:
            return [
                ("Κατηγορία Εργασίας", "job_type"), ("Υποκατηγορία", "subcategory"),
                ("Ημερομηνία", "date_logged"), ("Ώρα", "time_logged"),
                ("Αριθμός Τιμολογίου", "invoice_number"), ("Σημειώσεις Εργασίας", "notes")
            ]

    def get_payment_schema(self):
        is_en = self.settings.get("lang", "el") == "en"
        if is_en:
            return [
                ("Payment Amount (€)", "amount"), ("Date Received", "date_received"),
                ("Payment Method", "payment_method"), ("Job Category", "job_category"),
                ("Notes", "notes")
            ]
        else:
            return [
                ("Ποσό Πληρωμής (€)", "amount"), ("Ημερομηνία", "date_received"),
                ("Τρόπος Πληρωμής", "payment_method"), ("Κατηγορία Εργασίας", "job_category"),
                ("Σημειώσεις", "notes")
            ]


# --- DPI / window-size scaling helper -------------------------------------
_DESIGN_BASE_WIDTH = 1150
_SCALE_MIN = 0.85
_SCALE_MAX = 1.25
_root_ref = None


def set_scale_root(root_widget):
    """Point the scaler at the live application root window."""
    global _root_ref
    _root_ref = root_widget


def get_scale_factor():
    """Return the current scale factor (clamped) based on window width."""
    width = _DESIGN_BASE_WIDTH
    if _root_ref is not None:
        try:
            width = _root_ref.winfo_width()
        except Exception:
            width = _DESIGN_BASE_WIDTH
    if width < 800:
        width = _DESIGN_BASE_WIDTH
    factor = width / _DESIGN_BASE_WIDTH
    return max(_SCALE_MIN, min(_SCALE_MAX, factor))


def get_scaled_size(base_value):
    """Scale an absolute pixel dimension by the window-width baseline factor."""
    return int(round(base_value * get_scale_factor()))
