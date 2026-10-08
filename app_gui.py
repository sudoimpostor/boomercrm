import customtkinter as ctk
import sys
import os
import tkinter
import sqlite3
import json
from datetime import datetime, timedelta

# Allows python to look for companion scripts inside the local folder dynamically
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from logic_engine import db_path, BACKUP_DIR  # <── Import our dynamic paths!

from logic_engine import fuzzy_search_clients, get_client_jobs, get_client_payments, get_all_recorded_payments, verify_and_fetch_client, record_new_payment, search_jobs_by_date_range, record_new_job, get_revenue_by_category, get_monthly_aggregation, get_stagnant_debt_accounts, get_summary_stats, get_all_clients_summary, wipe_all_application_records, execute_safe_system_export, list_existing_backups, format_date_display, register_new_client_record, get_config_list, add_config_list_item, remove_config_list_item

from ui_config import UIConfig, get_scaled_size, set_scale_root

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ─────────────────────────────────────────────
# UNIFIED FIELD SCHEMA MATRICES
# Used by both creation panels and EAV edit modals
# ─────────────────────────────────────────────

CLIENT_FIELDS_SCHEMA = [
    ("Όνομα", "name"), ("Τηλέφωνο", "phone"), ("Κινητό (Τηλ 2)", "phone_2"),
    ("Διεύθυνση", "address"), ("Διεύθυνση 2", "address_2"), ("Περιοχή", "area"),
    ("ΑΦΜ", "vat"), ("Επάγγελμα", "profession")
]

JOB_FIELDS_SCHEMA = [
    ("Κατηγορία Εργασίας", "job_type"), ("Υποκατηγορία", "subcategory"),
    ("Ημερομηνία", "date_logged"), ("Ώρα", "time_logged"),
    ("Αριθμός Τιμολογίου", "invoice_number"), ("Σημειώσεις Εργασίας", "notes")
]

PAYMENT_FIELDS_SCHEMA = [
    ("Ποσό Πληρωμής (€)", "amount"), ("Ημερομηνία", "date_received"),
    ("Τρόπος Πληρωμής", "payment_method"), ("Κατηγορία Εργασίας", "job_category"),
    ("Σημειώσεις", "notes")
]

def apply_ui_scale(root_widget, font_name="Arial", base_size=18, scale_factor=1.0):
    """
    Surgically walks the CustomTkinter UI object graph to scale fonts,
    calibrate row actions, protect private sidebar objects from regressions,
    and expand vertical grid padding to eliminate text-clipping.
    """
    scaled_size = max(int(base_size * scale_factor), 11)

    def walk(widget):
        if not widget:
            return

        # 🛑 CRITICAL PROTECTION: Completely ignore private internal CustomTkinter components
        if any(part.startswith("_") for part in str(widget).split(".")):
            return

        # 1. RECTIFY PRIVATE SEGMENTED TAB VIEW ELEMENTS
        if hasattr(widget, "_segmented_button") and widget._segmented_button:
            try:
                widget._segmented_button.configure(font=(font_name, scaled_size))
            except Exception:
                pass

        # 2. ISOLATE AND RE-SCALE INLINE ROW ACTION BUTTONS (✏️ / 🗑️)
        is_action_btn = False
        if hasattr(widget, "cget"):
            try:
                text_val = widget.cget("text") or ""
                if any(symbol in str(text_val) for symbol in ["✏️", "🗑️", "Edit", "Delete"]):
                    is_action_btn = True
            except Exception:
                pass

        # 3. RE-CONFIG TEXT AND ENTRY INPUT HEIGHT MARGINS
        if hasattr(widget, "configure"):
            try:
                if is_action_btn:
                    action_size = max(int(scaled_size * 0.9), 12)
                    widget.configure(font=(font_name, action_size))
                else:
                    widget.configure(font=(font_name, scaled_size))
            except Exception:
                pass

        # 4. CALIBRATE VERTICAL CELL PADDING TO ELIMINATE CLIPPING (User public fields only)
        if hasattr(widget, "grid_info") and hasattr(widget, "grid_configure"):
            try:
                # Do not force re-padding on structural system containers
                typename = widget.__class__.__name__
                if typename not in ["CTkFrame", "CTkScrollableFrame", "CTkCanvas", "Canvas", "CTkOptionMenu", "CTkComboBox"]:
                    g_info = widget.grid_info()
                    if g_info:
                        pad_floor = max(int(3 * scale_factor), 5)
                        widget.grid_configure(pady=(pad_floor, pad_floor))
            except Exception:
                pass

        # 5. RECURSIVELY CASCADE THROUGH STANDARD AND CUSTOM ELEMENT TREES
        if hasattr(widget, "winfo_children"):
            try:
                for child in widget.winfo_children():
                    walk(child)
            except Exception:
                pass

    walk(root_widget)


def construct_calendar_job_form(parent_frame, font_name, base_font_size, scale_factor):
    """
    Hardened form generation structure for the Job Calendar workspace.
    Ensures absolute geometric column synchronization, eliminates row crowding,
    and applies unambiguous labeled entry bounds across Greek fields.
    """
    # 1. COMPUTE LOCAL DYNAMIC GEOMETRY SCALING PARAMETERS
    scaled_font = (font_name, max(int(base_font_size * scale_factor), 13))
    header_font = (font_name, max(int((base_font_size + 2) * scale_factor), 15), "bold")

    # Grid breathing spacing variables to absorb container stretching
    grid_padx = max(int(8 * scale_factor), 10)
    grid_pady = max(int(6 * scale_factor), 8)
    element_height = max(int(32 * scale_factor), 35)

    # 2. SEPARATE CONTAINER INNER PANEL WITH EXPLICIT COLUMN SCALE WEIGHTS
    form_container = ctk.CTkFrame(parent_frame, fg_color="transparent")
    form_container.pack(fill="x", expand=False, padx=grid_padx, pady=grid_pady)

    # Configure 4-column master balanced grid distribution matrix
    form_container.grid_columnconfigure(0, weight=0, minsize=140)  # Labels column 1
    form_container.grid_columnconfigure(1, weight=1)              # Fields column 1
    form_container.grid_columnconfigure(2, weight=0, minsize=140)  # Labels column 2
    form_container.grid_columnconfigure(3, weight=1)              # Fields column 2

    # SECTION TITLE HEADER
    title_lbl = ctk.CTkLabel(
        form_container,
        text="Εισαγωγή Νέας Εργασίας Ημερολογίου",
        font=header_font,
        anchor="w"
    )
    title_lbl.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, grid_pady * 2))

    # --- ROW 1: JOB TITLE & CLIENT LOOKUP AUTOCOMPLETE ---
    job_name_lbl = ctk.CTkLabel(form_container, text="Περιγραφή Εργασίας:", font=scaled_font, anchor="e")
    job_name_lbl.grid(row=1, column=0, padx=(0, grid_padx), pady=grid_pady, sticky="ne")

    job_name_entry = ctk.CTkEntry(form_container, font=scaled_font, height=element_height, placeholder_text="π.χ. Εγκατάσταση Δικτύου")
    job_name_entry.grid(row=1, column=1, padx=(0, grid_padx * 2), pady=grid_pady, sticky="ew")

    client_lbl = ctk.CTkLabel(form_container, text="Αναζήτηση Πελάτη:", font=scaled_font, anchor="e")
    client_lbl.grid(row=1, column=2, padx=(0, grid_padx), pady=grid_pady, sticky="ne")

    client_autocomplete = ctk.CTkComboBox(form_container, font=scaled_font, height=element_height, values=["Πληκτρολογήστε όνομα ή κωδικό..."])
    client_autocomplete.grid(row=1, column=3, pady=grid_pady, sticky="ew")

    # --- ROW 2: CREW (ΣΥΝΕΡΓΕΙΟ) & INVOICE (ΤΙΜΟΛΟΓΙΟ) CONTROLS ---
    crew_lbl = ctk.CTkLabel(form_container, text="Συνεργείο (Crew):", font=scaled_font, anchor="e")
    crew_lbl.grid(row=2, column=0, padx=(0, grid_padx), pady=grid_pady, sticky="ne")

    crew_option = ctk.CTkOptionMenu(form_container, font=scaled_font, height=element_height, values=["Συνεργείο Α", "Συνεργείο Β", "Εξωτερικό"])
    crew_option.grid(row=2, column=1, padx=(0, grid_padx * 2), pady=grid_pady, sticky="ew")

    invoice_lbl = ctk.CTkLabel(form_container, text="Τιμολόγιο / Ποσό:", font=scaled_font, anchor="e")
    invoice_lbl.grid(row=2, column=2, padx=(0, grid_padx), pady=grid_pady, sticky="ne")

    invoice_entry = ctk.CTkEntry(form_container, font=scaled_font, height=element_height, placeholder_text="0.00 €")
    invoice_entry.grid(row=2, column=3, pady=grid_pady, sticky="ew")

    # --- ROW 3: DATE SCHEDULING SELECTION WINDOW ---
    date_lbl = ctk.CTkLabel(form_container, text="Ημερομηνία:", font=scaled_font, anchor="e")
    date_lbl.grid(row=3, column=0, padx=(0, grid_padx), pady=grid_pady, sticky="ne")

    date_entry = ctk.CTkEntry(form_container, font=scaled_font, height=element_height, placeholder_text="ΗΗ/ΜΜ/ΕΕΕΕ")
    date_entry.grid(row=3, column=1, padx=(0, grid_padx * 2), pady=grid_pady, sticky="ew")

    # 3. SHIP FORM STATE HANDLERS TO MASTER CONTAINER INTERFACE
    form_fields = {
        "job_name": job_name_entry,
        "client": client_autocomplete,
        "crew": crew_option,
        "invoice": invoice_entry,
        "date": date_entry
    }
    return form_container, form_fields


    """
    Hardened multi-monitor layout constructor for the Client Registry space.
    Implements full grid column/row expandable weights and forces structural
    separation of input scrolling fields from fixed operational buttons.
    """
def construct_client_registry_tab(parent_tab, font_name, base_size, scale_factor):
    # Bump baseline for clear text layout
    scaled_font = (font_name, max(int((base_size + 2) * scale_factor), 16))
    header_font = (font_name, max(int((base_size + 4) * scale_factor), 18), "bold")

    # 1. FORCE THE MASTER TAB VIEW FRAME TO EXPAND SYMMETRICALLY
    parent_tab.grid_columnconfigure(0, weight=3)
    parent_tab.grid_columnconfigure(1, weight=2)
    parent_tab.grid_rowconfigure(0, weight=1)

    # ==========================================
    # LEFT PANEL: CLIENT TIMELINE REGISTRY CARDS
    # ==========================================
    left_panel = ctk.CTkFrame(parent_tab)
    left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    left_panel.grid_columnconfigure(0, weight=1)
    left_panel.grid_rowconfigure(1, weight=1)

    title_left = ctk.CTkLabel(left_panel, text="Μητρώο & Ιστορικό Πελατών", font=header_font, anchor="w")
    title_left.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

    timeline_scroll = ctk.CTkScrollableFrame(left_panel)
    timeline_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
    timeline_scroll.grid_columnconfigure(0, weight=1)

    # ==========================================
    # RIGHT PANEL: PROTECTED CLIENT INPUT FORM
    # ==========================================
    right_panel = ctk.CTkFrame(parent_tab)
    right_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    right_panel.grid_columnconfigure(0, weight=1)
    right_panel.grid_rowconfigure(1, weight=1)
    right_panel.grid_rowconfigure(2, weight=0)

    title_right = ctk.CTkLabel(right_panel, text="Καρτέλα Νέου Πελάτη", font=header_font, anchor="w")
    title_right.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

    form_scroll = ctk.CTkScrollableFrame(right_panel, fg_color="transparent")
    form_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
    form_scroll.grid_columnconfigure(1, weight=1)

    action_footer = ctk.CTkFrame(right_panel, fg_color="transparent")
    action_footer.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
    action_footer.grid_columnconfigure(0, weight=1)

    return left_panel, timeline_scroll, right_panel, form_scroll, action_footer



    """
    Drop-in renderer ensuring client metadata text arrays extract successfully
    and scale dynamically relative to configuration font dimensions.
    """
def render_timeline_card(container, client_data, font_name, base_size, scale_factor):
    # Bump card baseline to improve readability
    card_font = (font_name, max(int((base_size + 2) * scale_factor), 15))
    bold_card_font = (font_name, max(int((base_size + 2) * scale_factor), 15), "bold")

    card_frame = ctk.CTkFrame(container)
    card_frame.pack(fill="x", expand=True, padx=5, pady=4)
    card_frame.grid_columnconfigure(0, weight=1)

    name = client_data.get("name") or client_data.get("client_name") or "Μη Καταχωρημένο Όνομα"
    code = client_data.get("code") or client_data.get("client_code") or "---"
    phone = client_data.get("phone") or "---"

    info_lbl = ctk.CTkLabel(
        card_frame,
        text=f"[{code}] {name} - Τηλ: {phone}",
        font=bold_card_font,
        anchor="w"
    )
    info_lbl.grid(row=0, column=0, sticky="ew", padx=10, pady=6)


def setup_client_registry_tab_layout(parent_tab, font_name, base_size, scale_factor):
    """
    Hardened multi-monitor layout constructor for the Client Registry space.
    Enforces absolute horizontal/vertical expansion rules and shields
    the save buttons from viewport clipping regressions.
    """
    scaled_font = (font_name, max(int(base_size * scale_factor), 13))
    header_font = (font_name, max(int((base_size + 2) * scale_factor), 15), "bold")

    parent_tab.grid_columnconfigure(0, weight=3)
    parent_tab.grid_columnconfigure(1, weight=2)
    parent_tab.grid_rowconfigure(0, weight=1)

    left_panel = ctk.CTkFrame(parent_tab)
    left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    left_panel.grid_columnconfigure(0, weight=1)
    left_panel.grid_rowconfigure(1, weight=1)

    title_left = ctk.CTkLabel(left_panel, text="Μητρώο & Ιστορικό Πελατών", font=header_font, anchor="w")
    title_left.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

    timeline_scroll = ctk.CTkScrollableFrame(left_panel)
    timeline_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
    timeline_scroll.grid_columnconfigure(0, weight=1)

    right_panel = ctk.CTkFrame(parent_tab)
    right_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    right_panel.grid_columnconfigure(0, weight=1)
    right_panel.grid_rowconfigure(1, weight=1)
    right_panel.grid_rowconfigure(2, weight=0)

    title_right = ctk.CTkLabel(right_panel, text="Καρτέλα Νέου Πελάτη", font=header_font, anchor="w")
    title_right.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

    form_scroll = ctk.CTkScrollableFrame(right_panel, fg_color="transparent")
    form_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
    form_scroll.grid_columnconfigure(1, weight=1)

    action_footer = ctk.CTkFrame(right_panel, fg_color="transparent")
    action_footer.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
    action_footer.grid_columnconfigure(0, weight=1)

    save_btn = ctk.CTkButton(
        action_footer,
        text="Αποθήκευση Στοιχείων Πελάτη (Save)",
        font=scaled_font,
        height=40,
        fg_color="#2A8C55",
        hover_color="#1E663E"
    )
    save_btn.grid(row=0, column=0, sticky="ew")

    return timeline_scroll, form_scroll, save_btn


def initialize_eav_attribute_modal(modal_window):
    """
    Ensures container targets are scoped inside the method context
    to prevent NameError closures when fields are added dynamically.
    """
    try:
        adder_frame = ctk.CTkFrame(modal_window, fg_color="transparent")
        adder_frame.pack(fill="both", expand=True, padx=10, pady=10)
        return adder_frame
    except Exception as err:
        print(f"CRITICAL: Failed to assemble active attribute overlay scope: {err}")


class NSOFTApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.state_synced = False
        self.ui_cfg = UIConfig()
        set_scale_root(self)
        self.current_font_size = self.ui_cfg.settings.get('font_size', 25)
        self.active_client_code = None

        self.title("Boomer CRM - High-Visibility Operations Suite")
        self.geometry("1150x700")
        self.minsize(1000, 600)
        # Resilient Cross-Platform Window Maximization Staging Engine
        try:
            self.state('zoomed')
        except Exception:
            try:
                self.attributes('-zoomed', True)
            except Exception:
                try:
                    screen_w = self.winfo_screenwidth()
                    screen_h = self.winfo_screenheight()
                    self.geometry(f"{screen_w}x{screen_h}+0+0")
                except Exception:
                    self.geometry("1150x700")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- NAVIGATION SIDEBAR PANEL ---
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="BOOMER CRM", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=25)

        self.btn_registry = ctk.CTkButton(self.sidebar_frame, text="👥  ΠΕΛΑΤΕΣ", command=lambda: self.switch_frame("registry"))
        self.btn_registry.grid(row=1, column=0, padx=20, pady=8, sticky="ew")

        self.btn_calendar = ctk.CTkButton(self.sidebar_frame, text="📅  ΕΡΓΑΣΙΕΣ", command=lambda: self.switch_frame("calendar"))
        self.btn_calendar.grid(row=2, column=0, padx=20, pady=8, sticky="ew")

        self.btn_ledger = ctk.CTkButton(self.sidebar_frame, text="💰  ΠΛΗΡΩΜΕΣ", command=lambda: self.switch_frame("ledger"))
        self.btn_ledger.grid(row=3, column=0, padx=20, pady=8, sticky="ew")

        self.btn_analytics = ctk.CTkButton(self.sidebar_frame, text="📊  ΑΝΑΛΥΤΙΚΑ", command=lambda: self.switch_frame("analytics"))
        self.btn_analytics.grid(row=4, column=0, padx=20, pady=8, sticky="ew")

        self.btn_settings = ctk.CTkButton(self.sidebar_frame, text="⚙️  ΡΥΘΜΙΣΕΙΣ", command=lambda: self.switch_frame("settings"), fg_color="#4A4A4A")
        self.btn_settings.grid(row=6, column=0, padx=20, pady=20, sticky="ew")

        self.desk_container = ctk.CTkFrame(self, fg_color="transparent")
        self.desk_container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.desk_container.grid_columnconfigure(0, weight=1)
        self.desk_container.grid_rowconfigure(0, weight=1)

        self.frames = {}
        self.init_registry_frame()
        self.init_calendar_frame()
        self.init_ledger_frame()
        self.init_analytics_frame()
        self.init_settings_frame()

        self.switch_frame("registry")
        self.after(150, lambda: self.dynamic_ui_scaler())

    def hide_all_autofill_dropdowns(self):
        """ Withdraws all active CTkAutocompleteEntry popup dropdowns across the UI. """
        def _recurse_hide(w):
            if hasattr(w, '_hide_dropdown'):
                try: w._hide_dropdown()
                except Exception: pass
            if hasattr(w, 'winfo_children'):
                for child in w.winfo_children():
                    _recurse_hide(child)
        _recurse_hide(self)

    def switch_frame(self, frame_name):
        self.hide_all_autofill_dropdowns()
        # Lock window properties
        self.desk_container.pack_propagate(False)
        self.desk_container.grid_propagate(False)
        self.desk_container.grid_columnconfigure(0, weight=1)
        self.desk_container.grid_rowconfigure(0, weight=1)
        
        # Hide all existing tab frames
        for name, frm in self.frames.items():
            if hasattr(frm, "grid_forget"):
                frm.grid_forget()
                
        # Retrieve and display the active frame
        active_frame = self.frames.get(frame_name)
        if active_frame:
            active_frame.grid(row=0, column=0, sticky="nsew")
            
        # --- TAB REFRESH WIRING ---
        if frame_name == "calendar":
            self.reset_job_creation_fields()
        elif frame_name == "registry":
            if hasattr(self, "reset_client_creation_fields"):
                self.reset_client_creation_fields()
        elif frame_name == "analytics":
            # This line forces the dashboard to calculate and render when you click the tab
            if hasattr(self, "refresh_analytics_view_action"):
                self.refresh_analytics_view_action(None)

    def init_placeholder_frame(self, key, headline):
        frame = ctk.CTkFrame(self.desk_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        lbl = ctk.CTkLabel(frame, text=headline, font=ctk.CTkFont(size=18, weight="bold"))
        lbl.pack(anchor="w", padx=10, pady=10)
        stub_lbl = ctk.CTkLabel(frame, text=f"[Sub-module: {key.upper()} - Structured Frame Ready for Logic Attachment]", font=ctk.CTkFont(slant="italic"))
        stub_lbl.pack(expand=True)
        self.frames[key] = frame


    def init_ledger_frame(self):
        frame = ctk.CTkFrame(self.desk_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=7) # Main list expanded to 70% width
        frame.grid_columnconfigure(1, weight=3) # Sidebar slimmed down to 30% width
        frame.grid_rowconfigure(0, weight=1)

        left_pane = ctk.CTkFrame(frame, fg_color="transparent")
        left_pane.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        left_pane.grid_columnconfigure(0, weight=1)
        left_pane.grid_rowconfigure(4, weight=1)

        lbl_title = ctk.CTkLabel(left_pane, text="Μητρώο Πληρωμών", font=ctk.CTkFont(size=18, weight="bold"))
        lbl_title.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        search_row = ctk.CTkFrame(left_pane, fg_color="transparent")
        search_row.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        search_row.grid_columnconfigure(0, weight=1)

        self.payment_search_var = ctk.StringVar()
        self.payment_search_entry = ctk.CTkEntry(search_row, textvariable=self.payment_search_var,
            placeholder_text="Αναζήτηση Πελάτη...", width=300)
        self.payment_search_entry.pack(side="left", padx=(0, 10))

        self.payment_sort_var = ctk.StringVar(value="date")
        self.payment_sort_desc = True

        def trigger_payment_refresh(sort_mode=None, *args):
            if sort_mode:
                if self.payment_sort_var.get() == sort_mode:
                    self.payment_sort_desc = not self.payment_sort_desc
                else:
                    self.payment_sort_var.set(sort_mode)
                    self.payment_sort_desc = True
                    
            self.populate_payments_list(
                search_term=self.payment_search_var.get(),
                sort_by=self.payment_sort_var.get()
            )
            
        self.payment_search_entry.bind("<KeyRelease>", lambda e: trigger_payment_refresh())

        ctk.CTkButton(search_row, text="↕ Ημερομηνία", width=120,
            command=lambda: trigger_payment_refresh("date"),
            font=ctk.CTkFont(size=18)).pack(side="left", padx=5)
            
        ctk.CTkButton(search_row, text="↕ Ποσό (€)", width=120,
            command=lambda: trigger_payment_refresh("amount"),
            font=ctk.CTkFont(size=18)).pack(side="left", padx=5)

        self.ledger_scroll = ctk.CTkScrollableFrame(left_pane, label_text="Λίστα Πληρωμών")
        self.ledger_scroll.grid(row=4, column=0, sticky="nsew", padx=5, pady=5)

        right_pane = ctk.CTkFrame(frame, fg_color=("#E0E0E0", "#222222"), corner_radius=8)
        right_pane.grid(row=0, column=1, sticky="nsew", padx=10, pady=5)

        form_title = ctk.CTkLabel(right_pane, text="Νέα Πληρωμή", font=ctk.CTkFont(size=18, weight="bold"))
        form_title.pack(anchor="w", padx=15, pady=15)

        self.inp_code_widget = CTkAutocompleteEntry(right_pane, "Αναζήτηση Πελάτη...",
            search_callback=lambda sel: self.ledger_verify_client_action())
        self.inp_code_widget.pack(fill="x", padx=15, pady=5)

        btn_verify = ctk.CTkButton(right_pane, text="Επιβεβαίωση Πελάτη", command=self.ledger_verify_client_action)
        btn_verify.pack(fill="x", padx=15, pady=5)

        self.lbl_form_client_name = ctk.CTkLabel(right_pane, text="Επιλεγμένος Πελάτης: Κανένας", font=ctk.CTkFont(weight="bold"), anchor="w")
        self.lbl_form_client_name.pack(fill="x", padx=15, pady=5)

        self.lbl_form_owed = ctk.CTkLabel(right_pane, text="Υπόλοιπο: €0.00", anchor="w")
        self.lbl_form_owed.pack(fill="x", padx=15, pady=2)

        self.inp_amount = ctk.CTkEntry(right_pane, placeholder_text="Ποσό Πληρωμής (€)...", font=("Arial", 18), height=45)
        self.inp_amount.pack(fill="x", padx=15, pady=(15, 5))

        from logic_engine import get_config_list
        pms = get_config_list("payment_methods") or ["ΜΕΤΡΗΤΑ (Cash)"]
        self.inp_method = ctk.CTkOptionMenu(right_pane, values=pms, font=("Arial", 18), height=45)
        self.inp_method.pack(fill="x", padx=15, pady=5)
        self.inp_method.set("ΜΕΤΡΗΤΑ (Cash)")

        date_row = ctk.CTkFrame(right_pane, fg_color="transparent")
        date_row.pack(fill="x", padx=15, pady=5)
        date_row.grid_columnconfigure(0, weight=1)
        self.inp_date = ctk.CTkEntry(date_row, placeholder_text="Ημερομηνία (DD-MM-YY)...", font=("Arial", 18), height=45)
        self.inp_date.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(date_row, text="📅", width=30,
            command=lambda: CTkDatePicker(self, self.inp_date),
            fg_color=("#E0E0E0", "#3A3A3A"), text_color=("#1A1A1A", "#E0E0E0")).grid(row=0, column=1)

        self.inp_notes = ctk.CTkEntry(right_pane, placeholder_text="Σημειώσεις...", font=("Arial", 18), height=45)
        self.inp_notes.pack(fill="x", padx=15, pady=5)

        self.chk_special_payment = ctk.CTkCheckBox(right_pane, text="Special", font=("Arial", 18))
        self.chk_special_payment.pack(anchor="w", padx=15, pady=5)

        btn_submit = ctk.CTkButton(right_pane, text="✔ Αποθήκευση Πληρωμής", fg_color="#2EA44F", hover_color="#2C974B", command=self.execute_save_new_payment)
        btn_submit.pack(fill="x", padx=15, pady=20)

        self.active_form_client_data = None
        self.current_selected_client_code = "ALL"
        self.frames["ledger"] = frame
        self.populate_payments_list()


    def populate_payments_list(self, search_term="", sort_by="date"):
        from logic_engine import get_payments_with_client_data
        for w in self.ledger_scroll.winfo_children():
            w.destroy()
        payments = get_payments_with_client_data(search_term=search_term, sort_by=sort_by)
        # Local Bi-directional Sorting
        desc = getattr(self, 'payment_sort_desc', True)
        if sort_by == "date":
            payments.sort(key=lambda x: str(x.get("date", "")), reverse=desc)
        elif sort_by == "amount":
            payments.sort(key=lambda x: float(x.get("amount", 0) or 0), reverse=desc)
        if not payments:
            ctk.CTkLabel(self.ledger_scroll,
                text="Δεν υπάρχουν καταχωρημένες πληρωμές.",
                font=ctk.CTkFont(slant="italic")).pack(pady=30)
            return
        for p in payments:
            card = ctk.CTkFrame(self.ledger_scroll, fg_color=("#F0F0F0", "#2D2D2D"), corner_radius=4)
            card.pack(fill="x", padx=5, pady=3)
            card.grid_columnconfigure(0, weight=1)
            client_name = p.get("client_name", "Άγνωστος") or "Άγνωστος"
            cat1 = p.get('job_category', '')
            display_text = f"{client_name} - {cat1}" if cat1 and cat1 != "-" else client_name
            if p.get("is_special") == 1:
                display_text += "  [Special]"
            
            ctk.CTkLabel(card, text=display_text,
                font=ctk.CTkFont(size=18, weight="bold"),
                anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=(get_scaled_size(8), 0))
            date_str = format_date_display(p.get("date", ""))
            amount = p.get("amount", 0)
            method = p.get("method", "")
            details = f"Ημερομηνία: {date_str}  |  Ποσό: €{amount:.2f}  |  Τρόπος: {method}"
            ctk.CTkLabel(card, text=details,
                font=ctk.CTkFont(size=18), anchor="w").grid(row=1, column=0, sticky="w", padx=10, pady=(0, get_scaled_size(8)))
            notes = p.get("notes", "") or ""
            if notes:
                ctk.CTkLabel(card, text=f"Σημ: {notes}",
                    font=ctk.CTkFont(size=18), anchor="w", text_color="gray").grid(row=2, column=0, sticky="w", padx=10, pady=(0, 3))
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.grid(row=0, column=1, rowspan=3, sticky="ns", padx=5)
            ctk.CTkButton(btn_frame, text="✏️", width=30,
                fg_color=("#E0E0E0", "#3A3A3A"),
                text_color=("#1A1A1A", "#E0E0E0"),
                hover_color=("#D0D0D0", "#4A4A4A"),
                command=lambda pd=p: self.open_payment_edit_modal(pd.get("payment_id"))
            ).pack(pady=2)
            ctk.CTkButton(btn_frame, text="🗑️", width=30,
                fg_color="#C0392B", hover_color="#E74C3C",
                command=lambda pd=p: ConfirmationDialog(
                    self,
                    f"Διαγραφή πληρωμής ID {pd.get('payment_id')}?",
                    lambda pid=pd.get('payment_id'): self.eav_delete_payment(pid)
                )
            ).pack(pady=2)
        self.dynamic_ui_scaler(self.ledger_scroll)

    def execute_save_new_payment(self):
        from logic_engine import add_new_payment
        if not self.active_form_client_data:
            import tkinter.messagebox as mb
            mb.showwarning("Προσοχή", "Πρέπει να επιλέξετε πελάτη!")
            return
            
        code = self.active_form_client_data["code"]
        name = self.active_form_client_data["name"]
        amount = self.inp_amount.get().strip()
        raw_date = self.inp_date.get().strip()
        
        # --- SAFE DATE NORMALIZER (Converts DD-MM-YYYY or DD-MM-YY to YYYY-MM-DD silently) ---
        import re
        from datetime import datetime
        if re.match(r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$", raw_date):
            clean_str = raw_date.replace("/", "-")
            try:
                if len(clean_str.split("-")[-1]) == 2:
                    parsed = datetime.strptime(clean_str, "%d-%m-%y")
                else:
                    parsed = datetime.strptime(clean_str, "%d-%m-%Y")
                date_str = parsed.strftime("%d-%m-%Y")
            except ValueError:
                date_str = raw_date
        else:
            date_str = raw_date

        method = self.inp_method.get()
        notes = self.inp_notes.get().strip()
        is_sp = 1 if hasattr(self, 'chk_special_payment') and self.chk_special_payment.get() else 0
        
        if not amount or not date_str:
            import tkinter.messagebox as mb
            mb.showwarning("Προσοχή", "Συμπληρώστε ποσό και ημερομηνία!")
            return
            
        payload = {
            "client_code": code,
            "client_name": name,
            "date": date_str,
            "amount": amount,
            "method": method,
            "notes": notes,
            "is_special": is_sp
        }
        
        if add_new_payment(payload):
            import tkinter.messagebox as mb
            mb.showinfo("Επιτυχία", "Η πληρωμή καταχωρήθηκε!")
            self.inp_code_widget.delete(0, "end")
            self.inp_amount.delete(0, "end")
            self.inp_date.delete(0, "end")
            self.inp_notes.delete(0, "end")
            if hasattr(self, 'chk_special_payment'):
                self.chk_special_payment.deselect()
            self.lbl_form_client_name.configure(text="Επιλεγμένος Πελάτης: Κανένας", text_color="white")
            self.lbl_form_owed.configure(text="Υπόλοιπο: €0.00", text_color="white")
            self.active_form_client_data = None
            self.populate_payments_list(
                search_term=self.payment_search_var.get(),
                sort_by=self.payment_sort_var.get()
            )
            self.execute_registry_query(None)
            self.dynamic_ui_scaler(self.ledger_scroll)

    def ledger_verify_client_action(self):
        import re
        from logic_engine import verify_and_fetch_client, fuzzy_search_clients
        raw_val = self.inp_code_widget.get().strip()
        
        if not raw_val:
            self.lbl_form_client_name.configure(text="❌ Σφάλμα (Κενό)", text_color="red")
            return

        # 1. PARSE OUT THE CODE REGARDLESS OF THE INPUT STRING FORMAT
        target_code = raw_val
        if " — " in raw_val:
            target_code = raw_val.split(" —")[0].strip()
        elif " - [" in raw_val:
            target_code = raw_val.split(" - [")[-1].replace("]", "").strip()
        else:
            match = re.search(r'\[(\d+)\]', raw_val)
            if match:
                target_code = match.group(1)
                
        # 2. ATTEMPT DIRECT CODE VERIFICATION
        client_profile = verify_and_fetch_client(target_code)
        
        # 3. SMART FALLBACK: If direct lookup fails, treat input as a raw name and fuzzy search it
        if not client_profile and raw_val:
            matches = fuzzy_search_clients(raw_val)
            if matches:
                client_profile = verify_and_fetch_client(matches[0]['code'])
                
        if not client_profile:
            self.lbl_form_client_name.configure(text="❌ Πελάτης δεν βρέθηκε", text_color="#FF6B6B")
            self.lbl_form_owed.configure(text="Υπόλοιπο: €0.00", text_color="white")
            self.active_form_client_data = None
            return
            
        # 4. SUCCESS: Stamp the matching profile details into the UI
        self.active_form_client_data = client_profile
        self.lbl_form_client_name.configure(text=f"Επιλεγμένος Πελάτης: {client_profile['name']}", text_color="#6BCB77")
        bal = client_profile['balance_owed']
        bal_color = "#FF6B6B" if bal > 0 else ("#3B8ED0" if bal < 0 else "#6BCB77")
        self.lbl_form_owed.configure(text=f"Υπόλοιπο: €{bal:.2f}", text_color=bal_color)


    def init_calendar_frame(self):
        # Force top-level window constraints to unlock scrollbars
        self.desk_container.grid_columnconfigure(0, weight=1)
        self.desk_container.grid_rowconfigure(0, weight=1)

        frame = ctk.CTkFrame(self.desk_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=3) # Main list gets 60% width
        frame.grid_columnconfigure(1, weight=2) # Sidebar gets 40% width
        frame.grid_rowconfigure(0, weight=1)    # CRITICAL: Constrains frame height to window bounds

        left_pane = ctk.CTkFrame(frame, fg_color="transparent")
        left_pane.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        left_pane.grid_columnconfigure(0, weight=1)
        left_pane.grid_rowconfigure(5, weight=1) # Forces the list frame to absorb vertical space

        ctk.CTkLabel(left_pane, text="Ημερολόγιο Εργασιών", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w", padx=5, pady=5)

        range_row = ctk.CTkFrame(left_pane, fg_color="transparent")
        range_row.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        range_row.grid_columnconfigure(1, weight=1)
        range_row.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(range_row, text="Από:", anchor="w", font=ctk.CTkFont(size=18)).grid(row=0, column=0, padx=(0, 3))
        self.cal_from_entry = ctk.CTkEntry(range_row, placeholder_text="DD-MM-YY", font=ctk.CTkFont(size=18))
        self.cal_from_entry.grid(row=0, column=1, sticky="ew", padx=(0, 3))
        self.cal_from_entry.bind("<Return>", lambda e: self.execute_calendar_query_action(None))
        ctk.CTkButton(range_row, text="📅", width=30,
            command=lambda: CTkDatePicker(self, self.cal_from_entry),
            fg_color=("#E0E0E0", "#3A3A3A"), text_color=("#1A1A1A", "#E0E0E0")).grid(row=0, column=2, padx=(0, 10))

        ctk.CTkLabel(range_row, text="Έως:", anchor="w", font=ctk.CTkFont(size=18)).grid(row=0, column=3, padx=(0, 3))
        self.cal_to_entry = ctk.CTkEntry(range_row, placeholder_text="DD-MM-YY", font=ctk.CTkFont(size=18))
        self.cal_to_entry.grid(row=0, column=4, sticky="ew", padx=(0, 3))
        self.cal_to_entry.bind("<Return>", lambda e: self.execute_calendar_query_action(None))
        ctk.CTkButton(range_row, text="📅", width=30,
            command=lambda: CTkDatePicker(self, self.cal_to_entry),
            fg_color=("#E0E0E0", "#3A3A3A"), text_color=("#1A1A1A", "#E0E0E0")).grid(row=0, column=5)

        today_str = datetime.now().strftime("%d-%m-%Y")
        first_of_month = datetime.now().replace(day=1).strftime("%d-%m-%Y")
        self.cal_from_entry.insert(0, first_of_month)
        self.cal_to_entry.insert(0, today_str)

        preset_row = ctk.CTkFrame(left_pane, fg_color="transparent")
        preset_row.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, get_scaled_size(8)))
        preset_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkButton(preset_row, text="Σήμερα", font=ctk.CTkFont(size=18), command=lambda: self.set_calendar_presets("today")).grid(row=0, column=0, padx=2, sticky="ew")
        ctk.CTkButton(preset_row, text="Αυτή την Εβδομάδα", font=ctk.CTkFont(size=18), command=lambda: self.set_calendar_presets("week")).grid(row=0, column=1, padx=2, sticky="ew")
        ctk.CTkButton(preset_row, text="Τρέχων Μήνας", font=ctk.CTkFont(size=18), command=lambda: self.set_calendar_presets("month")).grid(row=0, column=2, padx=2, sticky="ew")
        ctk.CTkButton(preset_row, text="Αυτό το Έτος", font=ctk.CTkFont(size=18), command=lambda: self.set_calendar_presets("year")).grid(row=0, column=3, padx=2, sticky="ew")

        ctk.CTkLabel(left_pane, text="Φίλτρο Πελάτη (Αναζήτηση):", anchor="w", font=ctk.CTkFont(size=18)).grid(row=3, column=0, sticky="w", padx=5, pady=(5, 0))
        
        # Initialize fuzzy search autocomplete entry box for real-time customer filtering
        self.cal_filter_search = CTkAutocompleteEntry(left_pane, "Πληκτρολογήστε όνομα για φιλτράρισμα... (ή κενό για Όλους)", search_callback=lambda code: self.execute_calendar_query_action(None))
        self.cal_filter_search.grid(row=4, column=0, sticky="ew", padx=5, pady=(0, get_scaled_size(8)))
        self.cal_filter_search.entry.bind("<Return>", lambda e: self.execute_calendar_query_action(None))

        self.calendar_scroll = ctk.CTkScrollableFrame(left_pane, label_text="Λίστα Εργασιών")
        self.calendar_scroll.grid(row=5, column=0, sticky="nsew", padx=0, pady=0)
        # Force the scrollable inner frame container to stretch out to match the panel width
        

        # --- REWRITTEN DYNAMIC SIDEBAR ---
        right_pane = ctk.CTkScrollableFrame(frame, fg_color=("#E0E0E0", "#222222"), corner_radius=8, label_text="Νέα Εργασία")
        right_pane.grid(row=0, column=1, sticky="nsew", padx=10, pady=5)

        lbl_font = ctk.CTkFont(size=18, weight="bold")
        ent_font = ctk.CTkFont(size=18)
        pad_y = (0, get_scaled_size(8))

        # Search
        ctk.CTkLabel(right_pane, text="Αναζήτηση Πελάτη:", font=lbl_font, anchor="w").pack(anchor="w", padx=10, pady=(5, 0))
        self.job_inp_code_widget = CTkAutocompleteEntry(right_pane, "Αναζήτηση Πελάτη...", search_callback=lambda sel: self.calendar_verify_client_action())
        self.job_inp_code_widget.pack(fill="x", expand=False, padx=10, pady=pad_y)

        ctk.CTkButton(right_pane, text="✔ Επιβεβαίωση Πελάτη", height=get_scaled_size(38), command=self.calendar_verify_client_action).pack(fill="x", expand=False, padx=10, pady=pad_y)

        self.lbl_job_client_name = ctk.CTkLabel(right_pane, text="Επιλεγμένος Πελάτης: Κανένας", font=lbl_font, anchor="w")
        self.lbl_job_client_name.pack(anchor="w", expand=False, padx=10, pady=(0, 10))

        try:
            from logic_engine import get_config_list
            cats = get_config_list('job_categories')
            if not cats or not isinstance(cats, list):
                cats = ["ΑΠΕΝΤΟΜΩΣΗ"]
        except Exception:
            cats = ["ΑΠΕΝΤΟΜΩΣΗ"]

        # Category Layout
        ctk.CTkLabel(right_pane, text="Κατηγορία Εργασίας:", font=lbl_font, anchor="w").pack(anchor="w", padx=10, pady=(5, 0))
        self.job_inp_cat1 = ctk.CTkOptionMenu(right_pane, values=cats, font=ent_font, height=get_scaled_size(38))
        self.job_inp_cat1.pack(fill="x", expand=False, padx=10, pady=pad_y)

        # Subcategory
        from logic_engine import get_config_list
        cats2 = get_config_list("job_subcategories")
        ctk.CTkLabel(right_pane, text="Υποκατηγορία:", font=lbl_font, anchor="w").pack(anchor="w", padx=10, pady=(5, 0))
        self.job_inp_cat2 = ctk.CTkOptionMenu(right_pane, values=cats2 if cats2 else ["ΚΑΤΣΑΡΙΔΕΣ", "ΠΟΝΤΙΚΙΑ", "ΜΙΚΡΟΒΙΑ"], font=ent_font, height=get_scaled_size(38))
        self.job_inp_cat2.pack(fill="x", expand=False, padx=10, pady=pad_y)

        # Time
        ctk.CTkLabel(right_pane, text="Ώρα:", font=lbl_font, anchor="w").pack(anchor="w", padx=10, pady=(5, 0))
        time_frame = ctk.CTkFrame(right_pane, fg_color="transparent")
        time_frame.pack(fill="x", expand=False, padx=10, pady=pad_y)
        self.hour_combo = ctk.CTkComboBox(time_frame, values=[f"{i:02d}" for i in range(24)], width=115, font=ent_font, height=get_scaled_size(45))
        self.hour_combo.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(time_frame, text=":").pack(side="left")
        self.minute_combo = ctk.CTkComboBox(time_frame, values=["00", "15", "30", "45"], width=115, font=ent_font, height=get_scaled_size(45))
        self.minute_combo.pack(side="left", padx=(5, 0))

        # Crew (Multi-Select with Chips)
        ctk.CTkLabel(right_pane, text="Συνεργείο:", font=lbl_font, anchor="w").pack(anchor="w", padx=10, pady=(5, 0))
        self.new_crew_combo, self.new_crew_tags, self.new_crew_list, self.new_crew_get, self.new_crew_populate = self.create_crew_multiselect(right_pane)

        # --- FORM REBUILD (PACK DIRECTLY TO right_pane) ---
        # Ensure no child widget uses expand=True. Use only fill="x".

        # Date/Time
        ctk.CTkLabel(right_pane, text="Ημερομηνία", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=get_scaled_size(10), pady=(get_scaled_size(8), 0))
        
        date_row_job = ctk.CTkFrame(right_pane, fg_color="transparent")
        date_row_job.pack(fill="x", padx=get_scaled_size(10), pady=(0, get_scaled_size(8)))
        date_row_job.grid_columnconfigure(0, weight=1)
        
        self.job_inp_date = ctk.CTkEntry(date_row_job, font=ctk.CTkFont(size=18), height=get_scaled_size(45), placeholder_text="DD-MM-YYYY")
        self.job_inp_date.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        ctk.CTkButton(date_row_job, text="📅", width=30, height=get_scaled_size(45),
            command=lambda: CTkDatePicker(self, self.job_inp_date),
            fg_color=("#E0E0E0", "#3A3A3A"), text_color=("#1A1A1A", "#E0E0E0")
        ).grid(row=0, column=1)

        # Price & VAT Calculator
        ctk.CTkLabel(right_pane, text="Οικονομικά", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=get_scaled_size(10), pady=(get_scaled_size(8), 0))
        
        self.job_vat_calc = VerticalVatCalculatorBlock(right_pane, vat_rate=0.24)
        self.job_vat_calc.pack(fill="x", padx=get_scaled_size(10), pady=(0, get_scaled_size(8)))

        # Invoice
        ctk.CTkLabel(right_pane, text="Τιμολόγιο", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=get_scaled_size(10), pady=(get_scaled_size(8), 0))
        self.job_inp_invoice = ctk.CTkEntry(right_pane, font=ctk.CTkFont(size=18), height=get_scaled_size(45))
        self.job_inp_invoice.pack(fill="x", padx=get_scaled_size(10), pady=(0, get_scaled_size(8)))

        # Notes
        ctk.CTkLabel(right_pane, text="Σημειώσεις", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=get_scaled_size(10), pady=(get_scaled_size(8), 0))
        self.job_inp_notes = ctk.CTkTextbox(right_pane, font=ctk.CTkFont(size=18), height=get_scaled_size(100))
        self.job_inp_notes.pack(fill="x", padx=get_scaled_size(10), pady=(0, get_scaled_size(8)))

        # Special Flag Checkbox
        self.chk_special_job = ctk.CTkCheckBox(right_pane, text="Special", font=ctk.CTkFont(size=18, weight="bold"))
        self.chk_special_job.pack(anchor="w", padx=get_scaled_size(10), pady=(0, get_scaled_size(8)))

        # Save Button
        self.btn_save_job = ctk.CTkButton(right_pane, text="Αποθήκευση Εργασίας", font=ctk.CTkFont(size=18, weight="bold"), height=get_scaled_size(45), fg_color="#10B981", command=self.execute_save_new_job)
        self.btn_save_job.pack(fill="x", padx=get_scaled_size(10), pady=(get_scaled_size(8), get_scaled_size(8)))

        self.active_job_form_client_data = None
        self.frames["calendar"] = frame
        self.execute_calendar_query_action(None)

    def create_crew_multiselect(self, parent, crew_opts=None):
        """Builds a multi-select crew tag/chip selector. Returns (crew_combo, tag_container, crew_list)."""
        from logic_engine import get_config_list
        if crew_opts is None:
            crew_opts = get_config_list('crew_members') or ['-']
        crew_row = ctk.CTkFrame(parent, fg_color="transparent")
        crew_row.pack(fill="x", expand=False, padx=10, pady=(0, get_scaled_size(5)))
        crew_row.grid_columnconfigure(0, weight=1)
        crew_combo = ctk.CTkComboBox(crew_row, values=crew_opts, font=ctk.CTkFont(size=18),
            dropdown_font=ctk.CTkFont(size=18), height=get_scaled_size(38), state='readonly')
        crew_combo.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        crew_list = []
        tag_container = ctk.CTkFrame(parent, fg_color="transparent")
        tag_container.pack(fill="x", expand=False, padx=10, pady=(0, get_scaled_size(5)))
        def add_chip():
            val = crew_combo.get()
            if val and val != "-" and val not in crew_list:
                crew_list.append(val)
                chip_frame = ctk.CTkFrame(tag_container, fg_color="transparent")
                chip_frame.pack(fill="x", anchor="w", pady=1)
                ctk.CTkLabel(chip_frame, text=f"✔️ {val}", font=("Arial", 16, "bold")).pack(side="left", padx=3)
                def remove_chip(m=val, f=chip_frame):
                    crew_list.remove(m)
                    f.destroy()
                ctk.CTkButton(chip_frame, text="✕", width=22, height=22, fg_color="transparent",
                    text_color="#EF4444", hover_color="#3A3A3A", font=("Arial", 14), command=remove_chip).pack(side="left", padx=3)
        ctk.CTkButton(crew_row, text="➕", width=36, height=get_scaled_size(36), font=ctk.CTkFont(size=18),
            command=add_chip).grid(row=0, column=1)
        def get_serialized():
            return ", ".join(crew_list)
        def populate_from_string(comma_str):
            for w in tag_container.winfo_children():
                w.destroy()
            crew_list.clear()
            if comma_str:
                for name in [n.strip() for n in comma_str.split(",") if n.strip()]:
                    crew_list.append(name)
                    chip_frame = ctk.CTkFrame(tag_container, fg_color="transparent")
                    chip_frame.pack(fill="x", anchor="w", pady=1)
                    ctk.CTkLabel(chip_frame, text=f"✔️ {name}", font=("Arial", 16, "bold")).pack(side="left", padx=3)
                    def make_remove(m=name, f=chip_frame):
                        def rm():
                            crew_list.remove(m)
                            f.destroy()
                        return rm
                    ctk.CTkButton(chip_frame, text="✕", width=22, height=22, fg_color="transparent",
                        text_color="#EF4444", hover_color="#3A3A3A", font=("Arial", 14), command=make_remove()).pack(side="left", padx=3)
        return crew_combo, tag_container, crew_list, get_serialized, populate_from_string

    def calendar_verify_client_action(self):
        import re
        raw_val = self.job_inp_code_widget.get().strip()

        if not raw_val:
            self.lbl_job_client_name.configure(text="Επιλεγμένος Πελάτης: Σφάλμα (Κενό)", text_color="red")
            return

        # --- REGEX EXTRACTION FIX ---
        # Extract the code from between brackets, e.g., "Name - [1234]" -> "1234"
        match = re.search(r'\[(\d+)\]', raw_val)
        code_str = match.group(1) if match else raw_val

        from logic_engine import verify_and_fetch_client
        profile = verify_and_fetch_client(code_str)
        if not profile:
            self.lbl_job_client_name.configure(text="❌ Invalid Client Code", text_color="#FF6B6B")
            self.active_job_form_client_data = None
            return
        self.active_job_form_client_data = profile
        self.lbl_job_client_name.configure(text=f"Entity Link: {profile['name']}", text_color="#6BCB77")

    def set_calendar_presets(self, preset):
        from datetime import datetime, timedelta
        today = datetime.now()
        today_str = today.strftime("%d-%m-%Y")
        if preset == "today":
            self.cal_from_entry.delete(0, ctk.END)
            self.cal_from_entry.insert(0, today_str)
            self.cal_to_entry.delete(0, ctk.END)
            self.cal_to_entry.insert(0, today_str)
        elif preset == "week":
            monday = today - timedelta(days=today.weekday())
            sunday = monday + timedelta(days=6)
            self.cal_from_entry.delete(0, ctk.END)
            self.cal_from_entry.insert(0, monday.strftime("%d-%m-%Y"))
            self.cal_to_entry.delete(0, ctk.END)
            self.cal_to_entry.insert(0, sunday.strftime("%d-%m-%Y"))
        elif preset == "month":
            first = today.replace(day=1)
            next_month = first.replace(month=first.month % 12 + 1, day=1) if first.month < 12 else first.replace(year=first.year + 1, month=1, day=1)
            last = next_month - timedelta(days=1)
            self.cal_from_entry.delete(0, ctk.END)
            self.cal_from_entry.insert(0, first.strftime("%d-%m-%Y"))
            self.cal_to_entry.delete(0, ctk.END)
            self.cal_to_entry.insert(0, last.strftime("%d-%m-%Y"))
        elif preset == "year":
            first = today.replace(month=1, day=1)
            last = today.replace(month=12, day=31)
            self.cal_from_entry.delete(0, ctk.END)
            self.cal_from_entry.insert(0, first.strftime("%d-%m-%Y"))
            self.cal_to_entry.delete(0, ctk.END)
            self.cal_to_entry.insert(0, last.strftime("%d-%m-%Y"))
        self.execute_calendar_query_action(None)

    def execute_calendar_query_action(self, event):
        from datetime import datetime
        from logic_engine import search_jobs_by_date_range, get_client_jobs
        
        # Safe guard check
        if not hasattr(self, 'calendar_scroll') or not self.calendar_scroll:
            return
            
        for w in self.calendar_scroll.winfo_children():
            w.destroy()
            
        # --- SMART SEARCH PARSER ---
        import re
        def norm_date(d_str):
            if re.match(r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$", d_str):
                c = d_str.replace("/", "-")
                try:
                    fmt = "%d-%m-%y" if len(c.split("-")[-1]) == 2 else "%d-%m-%Y"
                    return datetime.strptime(c, fmt).strftime("%Y-%m-%d")
                except: pass
            return d_str

        # Apply the normalizer so European dates get translated for the SQLite engine
        date_from = norm_date(self.cal_from_entry.get().strip() if hasattr(self, 'cal_from_entry') else "")
        date_to = norm_date(self.cal_to_entry.get().strip() if hasattr(self, 'cal_to_entry') else "")
        
        raw_search = ""
        if hasattr(self, 'cal_filter_search') and self.cal_filter_search:
            # FIX: CTkAutocompleteEntry is a frame component; we must read from its embedded entry widget
            if hasattr(self.cal_filter_search, 'entry') and self.cal_filter_search.entry:
                raw_search = self.cal_filter_search.entry.get().strip()
            else:
                raw_search = self.cal_filter_search.get().strip()
        elif hasattr(self, 'cal_filter_var'):
            raw_search = self.cal_filter_var.get().strip()
            
        client_code = None
        if "[" in raw_search and raw_search.endswith("]"):
            try:
                client_code = raw_search.split("[")[-1].replace("]", "").strip()
            except Exception:
                client_code = None
        elif raw_search:
            # FIX: If it's a raw string typed directly or injected via deep-link jump, filter directly by it!
            client_code = raw_search

        if client_code:
            all_jobs = get_client_jobs(client_code)
            jobs = [j for j in all_jobs if date_from <= j.get('date', '') <= date_to]
        else:
            jobs = search_jobs_by_date_range(date_from, date_to)
        if not jobs:
            ctk.CTkLabel(self.calendar_scroll, text="No scheduled operations in this date range.", font=ctk.CTkFont(slant="italic")).pack(pady=30)
            return
        from collections import OrderedDict
        grouped = OrderedDict()
        for j in jobs:
            d = j.get('date', 'Unknown')
            if d not in grouped:
                grouped[d] = []
            grouped[d].append(j)
        # Force the canvas to use the full horizontal width
        self.calendar_scroll.grid_columnconfigure(0, weight=1)
        row_counter = 0

        for date_key in reversed(sorted(grouped.keys())):
            day_jobs = grouped[date_key]
            try:
                dt = datetime.strptime(date_key, "%d-%m-%Y")
                day_names = ["Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο", "Κυριακή"]
                day_name = day_names[dt.weekday()]
                divider_txt = f"📅 {day_name} - {dt.strftime('%d/%m/%Y')}"
            except ValueError:
                divider_txt = f"📅 {format_date_display(date_key)}"
            
            # Divider (Using Grid)
            divider = ctk.CTkLabel(self.calendar_scroll, text=divider_txt, font=ctk.CTkFont(size=18, weight="bold"), text_color="#3B8ED0", anchor="w")
            divider.grid(row=row_counter, column=0, sticky="ew", padx=10, pady=(10, 2))
            row_counter += 1

            for j in day_jobs:
                card = ctk.CTkFrame(self.calendar_scroll, fg_color=("#F0F0F0", "#2D2D2D"), corner_radius=5)
                # CRITICAL: Use grid and sticky="ew" to force full width expansion
                card.grid(row=row_counter, column=0, sticky="ew", padx=5, pady=3)
                row_counter += 1
                
                # Text absorbs horizontal space, buttons are locked
                card.grid_columnconfigure(0, weight=1) 
                card.grid_columnconfigure(1, weight=0) 
                card.grid_columnconfigure(2, weight=0)

                # --- 2-ROW JOB CARD ---
                client_name = j.get('client_name', '') or 'UNKNOWN'
                code = j.get('client_code', '')
                
                # FIXED: Fetch 'time_slot' instead of 'time' and handle None types safely
                raw_time = j.get('time_slot', '') or ''
                time_str = str(raw_time).strip()
                
                crew = j.get('crew', '') or '-'
                # FIXED: Checks both backend dictionary mapping formats ('cat1' or 'category_1') to ensure data is pulled
                cat1 = j.get('cat1', '') or j.get('category_1', '') or ''
                cat2 = j.get('cat2', '') or j.get('category_2', '') or ''
                top_text = f"🏢 {client_name} — [{code}] 🕒 {time_str}"
                if j.get("is_special") == 1:
                    top_text += "  [Special]"

                # Direct check to ensure no double-dash artifacts appear when data is missing
                if cat1 and cat2:
                    bottom_text = f"👷 {crew} 🛠️ - {cat1} - {cat2}"
                elif cat1:
                    bottom_text = f"👷 {crew} 🛠️ - {cat1}"
                elif cat2:
                    bottom_text = f"👷 {crew} 🛠️ - {cat2}"
                else:
                    bottom_text = f"👷 {crew} 🛠️ -"
                jd = dict(j)
                jd['job_id'] = jd.pop('id', None) or j.get('job_id')
                import json
                raw_extra = j.get('extra_fields', '{}')
                if isinstance(raw_extra, str):
                    try:
                        parsed_extra = json.loads(raw_extra or '{}')
                    except Exception:
                        parsed_extra = {}
                else:
                    parsed_extra = raw_extra if isinstance(raw_extra, dict) else {}
                    
                jd.update(parsed_extra)

                # Drop hardcoded wraplength; grid handles boundaries natively
                lbl_top = ctk.CTkLabel(card, text=top_text, font=ctk.CTkFont(size=18, weight="bold"), anchor="w", justify="left")
                lbl_top.grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 2))

                lbl_bottom = ctk.CTkLabel(card, text=bottom_text, font=ctk.CTkFont(size=18), anchor="w", justify="left", text_color=("#555555", "#AAAAAA"))
                lbl_bottom.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

                # Action Buttons
                ctk.CTkButton(card, text="✏️", width=get_scaled_size(30),
                    fg_color=("#E0E0E0", "#3A3A3A"), hover_color=("#D0D0D0", "#4A4A4A"), text_color=("#1A1A1A", "#E0E0E0"),
                    command=lambda jd=jd: self.open_job_edit_modal(jd.get('job_id'))
                ).grid(row=0, column=1, rowspan=2, sticky="ns", padx=(5, 2), pady=5)
                
                ctk.CTkButton(card, text="🗑️", width=get_scaled_size(30),
                    fg_color="#C0392B", hover_color="#E74C3C",
                    command=lambda jd=jd: ConfirmationDialog(
                        self, f"Διαγραφή job ID {jd.get('job_id')}?",
                        lambda jid=jd.get('job_id'): self.eav_delete_job(jid)
                    )).grid(row=0, column=2, rowspan=2, sticky="ns", padx=(2, 10), pady=5)
                    
        self.dynamic_ui_scaler(self.calendar_scroll)


    def reset_job_creation_fields(self):
        """Safely clears form fields without crashing if a field is missing."""
        if hasattr(self, 'job_inp_price') and self.job_inp_price:
            self.job_inp_price.delete(0, "end")
        
        if hasattr(self, 'hour_combo') and self.hour_combo:
            self.hour_combo.set("08")
            
        if hasattr(self, 'minute_combo') and self.minute_combo:
            self.minute_combo.set("00")
            
        if hasattr(self, 'job_inp_notes') and self.job_inp_notes:
            self.job_inp_notes.delete("1.0", "end")
            
        if hasattr(self, 'job_inp_invoice') and self.job_inp_invoice:
            self.job_inp_invoice.delete(0, "end")
            
        if hasattr(self, 'job_inp_code_widget') and self.job_inp_code_widget:
            self.job_inp_code_widget.delete(0, "end")
            
        if hasattr(self, 'job_inp_date') and self.job_inp_date:
            self.job_inp_date.delete(0, "end")
            
        if hasattr(self, 'chk_special_job') and self.chk_special_job:
            self.chk_special_job.deselect()

        if hasattr(self, 'new_crew_tags') and self.new_crew_tags:
            for child in self.new_crew_tags.winfo_children():
                child.destroy()
        if hasattr(self, 'new_crew_list'):
            self.new_crew_list.clear()
                
        if hasattr(self, 'lbl_job_client_name') and self.lbl_job_client_name:
            self.lbl_job_client_name.configure(text="Επιλεγμένος Πελάτης: Κανένας", text_color="white")
            
        self.active_job_form_client_data = None

    def execute_save_new_job(self):
        if not getattr(self, 'active_job_form_client_data', None):
            import tkinter.messagebox as mb
            mb.showwarning("Προσοχή", "Πρέπει να επιλέξετε πελάτη (Αναζήτηση & Επιβεβαίωση)!")
            return
            
        client_data = self.active_job_form_client_data
        
        # --- SAFE DATE NORMALIZER ---
        raw_date = self.job_inp_date.get().strip() if hasattr(self, 'job_inp_date') else ""
        import re
        from datetime import datetime
        if re.match(r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$", raw_date):
            clean_str = raw_date.replace("/", "-")
            try:
                fmt = "%d-%m-%y" if len(clean_str.split("-")[-1]) == 2 else "%d-%m-%Y"
                date_str = datetime.strptime(clean_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                date_str = raw_date
        elif re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$", raw_date):
            date_str = raw_date.replace("/", "-")
        else:
            date_str = raw_date
            
        time_slot = f"{self.hour_combo.get().strip()}:{self.minute_combo.get().strip()}"
        crew = self.new_crew_get() if hasattr(self, 'new_crew_get') else "-"
        notes = self.job_inp_notes.get("1.0", "end").strip() if hasattr(self, 'job_inp_notes') else ""
        cat1 = self.job_inp_cat1.get() if hasattr(self, 'job_inp_cat1') else ""
        cat2 = self.job_inp_cat2.get() if hasattr(self, 'job_inp_cat2') else ""
        invoice = self.job_inp_invoice.get().strip() if hasattr(self, 'job_inp_invoice') else ""
        is_sp = 1 if hasattr(self, 'chk_special_job') and self.chk_special_job.get() else 0
        
        # Extract from the new VAT Calculator
        price_before, vat_amount, price_after = self.job_vat_calc.get_values()
        
        # Map exactly to the parameter names logic_engine.py is expecting!
        payload = {
            "client_code": client_data["code"],
            "client_name": client_data["name"],
            "time_slot": time_slot,
            "notes": notes,
            "category_1": cat1,
            "category_2": cat2,
            "crew": crew,
            "invoice_number": invoice,
            "price_after_vat": str(price_after),
            "date_str": date_str,
            "is_special": is_sp
        }
        
        # Ensure time_slot is prepended to the notes if present, since logic_engine does not take time_slot directly
        combined_notes = f"[{time_slot}] {notes}" if time_slot and time_slot != ":" else notes

        from logic_engine import record_new_job
        # Send explicitly separated fields matched EXACTLY to the backend function definition
        success = record_new_job(
            client_code=client_data["code"],
            category_1=cat1,
            category_2=cat2,
            crew=crew,
            invoice_number=invoice,
            price_after_vat=str(price_after),
            date_str=date_str,
            notes=combined_notes,
            is_special=is_sp
        )
            
        if success:
            import tkinter.messagebox as mb
            mb.showinfo("Επιτυχία", "Η εργασία καταχωρήθηκε επιτυχώς!")
            self.reset_job_creation_fields()
            self.job_vat_calc.clear()
            self.execute_calendar_query_action(None)

    def reset_client_creation_fields(self):
        for entry in self.new_client_entries.values():
            entry.delete(0, "end")
        self.new_client_notes.delete("1.0", "end")
        self.lbl_new_client_status.configure(text="")

    def reset_payment_creation_fields(self):
        if hasattr(self, 'inp_code_widget'):
            self.inp_code_widget.delete(0, "end")
        if hasattr(self, 'inp_amount'):
            self.inp_amount.delete(0, "end")
        if hasattr(self, 'inp_date'):
            self.inp_date.delete(0, "end")
        if hasattr(self, 'inp_notes'):
            self.inp_notes.delete(0, "end")
        if hasattr(self, 'inp_method'):
            self.inp_method.set("ΜΕΤΡΗΤΑ (Cash)")
        if hasattr(self, 'lbl_form_client_name'):
            self.lbl_form_client_name.configure(text="Επιλεγμένος Πελάτης: Κανένας", text_color="white")
        if hasattr(self, 'lbl_form_owed'):
            self.lbl_form_owed.configure(text="Υπόλοιπο: €0.00", text_color="white")
        self.active_form_client_data = None

    def dynamic_ui_scaler(self, widget=None):
        """Delegates to the hardened apply_ui_scale engine for full UI scaling."""
        apply_ui_scale(widget if widget else self, "Arial", self.current_font_size, 1.0)

    def refresh_ui(self):
        self.dynamic_ui_scaler()
        if hasattr(self, 'search_entry'):
            self.search_entry.configure(font=self.ui_cfg.get_font(), placeholder_text=self.ui_cfg.get_text("search_placeholder"))

    def update_font_size(self, size_val):
        size_int = int(float(size_val))
        self.current_font_size = size_int
        self.ui_cfg.settings['font_size'] = size_int
        self.ui_cfg.save()
        self.dynamic_ui_scaler(self)

    def on_font_slider_changed(self, new_val):
        """Font slider callback: updates self.current_font_size and triggers full traversal."""
        self.update_font_size(new_val)

    def init_analytics_frame(self):
        frame = ctk.CTkFrame(self.desk_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(frame)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        # Column 7 absorbs extra middle space for Client search
        for c_idx in range(10):
            header.grid_columnconfigure(c_idx, weight=0)
        header.grid_columnconfigure(7, weight=1)

        # ─────────────────────────────────────────────────────────────────
        # ΣΕΙΡΑ 0: ΦΙΛΤΡΑ ΗΜΕΡΟΜΗΝΙΑΣ, ΠΕΛΑΤΗ (AUTOCOMPLETE) & ΚΑΤΗΓΟΡΙΕΣ
        # ─────────────────────────────────────────────────────────────────
        # Από: date entry
        ctk.CTkLabel(header, text="Από:", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=(10, 3), pady=8, sticky="w")
        self.ana_from_entry = ctk.CTkEntry(header, placeholder_text="DD-MM-YY", font=ctk.CTkFont(size=18), width=165, height=get_scaled_size(45))
        self.ana_from_entry.grid(row=0, column=1, padx=(0, 3), pady=8, sticky="w")
        ctk.CTkButton(header, text="📅", width=35, font=ctk.CTkFont(size=18), height=get_scaled_size(45),
            command=lambda: CTkDatePicker(self, self.ana_from_entry)).grid(row=0, column=2, padx=(0, 10), pady=8, sticky="w")

        # Έως: date entry
        ctk.CTkLabel(header, text="Έως:", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=3, padx=(0, 3), pady=8, sticky="w")
        self.ana_to_entry = ctk.CTkEntry(header, placeholder_text="DD-MM-YY", font=ctk.CTkFont(size=18), width=165, height=get_scaled_size(45))
        self.ana_to_entry.grid(row=0, column=4, padx=(0, 3), pady=8, sticky="w")
        ctk.CTkButton(header, text="📅", width=35, font=ctk.CTkFont(size=18), height=get_scaled_size(45),
            command=lambda: CTkDatePicker(self, self.ana_to_entry)).grid(row=0, column=5, padx=(0, 15), pady=8, sticky="w")

        # Πελάτης: Autocomplete Entry (A tiny bit smaller)
        ctk.CTkLabel(header, text="Πελάτης:", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=6, padx=(5, 3), pady=8, sticky="w")
        self.ana_client_search = CTkAutocompleteEntry(header, "Όλοι οι πελάτες...", search_callback=lambda sel: self.refresh_analytics_view_action(None))
        self.ana_client_search.entry.configure(width=180)
        self.ana_client_search.grid(row=0, column=7, padx=(0, 15), pady=8, sticky="w")

        # Dynamic Categories Menu Lookup Pass
        from logic_engine import get_config_list
        live_cats = get_config_list('job_categories') or []
        ctk.CTkLabel(header, text="Κατηγορία:", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=8, padx=(5, 3), pady=8, sticky="e")
        self.ana_cat_filter = ctk.CTkOptionMenu(header, values=["All"] + live_cats, font=ctk.CTkFont(size=18), width=150, height=get_scaled_size(45))
        self.ana_cat_filter.grid(row=0, column=9, padx=(0, 10), pady=8, sticky="e")

        # ─────────────────────────────────────────────────────────────────
        # ΣΕΙΡΑ 1: ΦΙΛΤΡΟ SPECIAL, ΑΝΑΖΗΤΗΣΗ ΣΥΝΕΡΓΕΙΟΥ & ΚΟΥΜΠΙ ΥΠΟΛΟΓΙΣΜΟΥ
        # ─────────────────────────────────────────────────────────────────
        ctk.CTkLabel(header, text="Special:", font=ctk.CTkFont(size=18, weight="bold")).grid(row=1, column=0, padx=(10, 3), pady=(0, 12), sticky="w")
        self.ana_special_filter = ctk.CTkOptionMenu(header, values=["All", "Special", "Non Special"], font=ctk.CTkFont(size=18), width=160, height=get_scaled_size(45))
        self.ana_special_filter.grid(row=1, column=1, columnspan=2, padx=(0, 15), pady=(0, 12), sticky="w")

        # Πεδίο Συνεργείου
        self.ana_crew_entry = ctk.CTkEntry(header, placeholder_text="Συνεργείο (π.χ. ΓΙΩΡΓΟΣ+ΝΙΚΟΣ)", font=ctk.CTkFont(size=16), height=get_scaled_size(45))
        self.ana_crew_entry.grid(row=1, column=3, columnspan=5, padx=(0, 15), pady=(0, 12), sticky="ew")

        # Κουμπί Υπολογισμού
        self.btn_recalc_analytics = ctk.CTkButton(header, text="🔄 Υπολογισμός",
            font=ctk.CTkFont(size=18, weight="bold"), width=150, height=get_scaled_size(45), fg_color="#3B8ED0",
            command=lambda: self.refresh_analytics_view_action(None))
        self.btn_recalc_analytics.grid(row=1, column=9, padx=(0, 10), pady=(0, 12), sticky="e")

        # Pre-populate dates
        today = datetime.now()
        first_of_month = today.replace(day=1).strftime("%d-%m-%y")
        self.ana_from_entry.insert(0, first_of_month)
        self.ana_to_entry.insert(0, today.strftime("%d-%m-%y"))

        self.analytics_scroll = ctk.CTkScrollableFrame(frame, label_text="Επιχειρηματική Εικόνα")
        self.analytics_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))
        self.analytics_scroll.grid_columnconfigure(0, weight=1)

        self.frames["analytics"] = frame

    def refresh_analytics_view_action(self, event=None):
        if not hasattr(self, 'analytics_scroll') or not self.analytics_scroll:
            return
        
        for child in self.analytics_scroll.winfo_children():
            child.destroy()
        
        from datetime import datetime

        if hasattr(self, 'ana_cat_filter'):
            from logic_engine import get_config_list
            live_cats = get_config_list("job_categories") or []
            new_values = ["All"] + live_cats
            current_selection = self.ana_cat_filter.get()
            self.ana_cat_filter.configure(values=new_values)
            if current_selection in new_values:
                self.ana_cat_filter.set(current_selection)
            else:
                self.ana_cat_filter.set("All")
            cat_filter = self.ana_cat_filter.get()
        else:
            cat_filter = "All"

        def clean_date_to_iso(entry_widget):
            raw = entry_widget.get().strip()
            if not raw:
                return datetime.now().strftime("%Y-%m-%d")
            if len(raw) == 10 and raw[4] == '-' and raw[7] == '-':
                return raw
            for fmt in ("%d-%m-%y", "%d-%m-%Y"):
                try:
                    parsed = datetime.strptime(raw, fmt)
                    return parsed.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return datetime.now().strftime("%Y-%m-%d")

        date_from = clean_date_to_iso(self.ana_from_entry)
        date_to = clean_date_to_iso(self.ana_to_entry)

        crew_filter = self.ana_crew_entry.get().strip() if hasattr(self, "ana_crew_entry") else ""

        raw_special = self.ana_special_filter.get() if hasattr(self, 'ana_special_filter') else "All"
        if raw_special == "Special":
            special_filter = "SPECIAL"
        elif raw_special == "Non Special":
            special_filter = "NON_SPECIAL"
        else:
            special_filter = "ALL"

        client_code_filter = "All"
        if hasattr(self, 'ana_client_search') and self.ana_client_search:
            raw_client = self.ana_client_search.get().strip()
            if raw_client and raw_client != "All" and raw_client != "Όλοι οι πελάτες...":
                import re
                match = re.search(r'\[(\d+)\]', raw_client)
                if match:
                    client_code_filter = match.group(1)
                else:
                    client_code_filter = raw_client
        
        # Pass filters down to all backend metrics operations
        from logic_engine import (
            fetch_dashboard_financial_kpis,
            fetch_crew_job_distribution,
            fetch_stagnant_aging_accounts
        )
        
        financials = fetch_dashboard_financial_kpis(date_from, date_to, cat_filter, crew_filter, special_filter=special_filter, client_filter=client_code_filter)
        crew_stats = fetch_crew_job_distribution(date_from, date_to, cat_filter, crew_filter, special_filter=special_filter, client_filter=client_code_filter)
        debtors = fetch_stagnant_aging_accounts(date_from, date_to, cat_filter, crew_filter, special_filter=special_filter, client_filter=client_code_filter)

        lbl_font = ctk.CTkFont(size=18, weight="bold")
        num_font = ctk.CTkFont(size=22, weight="bold")
        sub_font = ctk.CTkFont(size=18)
        
        # --- ROW 1: REVENUE MATRIX ---
        kpi_frame = ctk.CTkFrame(self.analytics_scroll, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=10, pady=10)
        kpi_frame.grid_columnconfigure((0, 1, 2), weight=1)

        card_a = ctk.CTkFrame(kpi_frame, fg_color=("#E0E0E0", "#2D2D2D"), corner_radius=6)
        card_a.grid(row=0, column=0, sticky="nsew", padx=5)
        ctk.CTkLabel(card_a, text="💰 Συνολικός Τζίρος", font=lbl_font, text_color="#3B8ED0").pack(pady=(10, 2))
        ctk.CTkLabel(card_a, text=f"€{financials['gross_revenue']:.2f}", font=num_font).pack()
        ctk.CTkLabel(card_a, text=f"Καθαρά (Προ ΦΠΑ): €{financials['net_revenue']:.2f}", font=ctk.CTkFont(size=14, slant="italic"), text_color="#888888").pack(pady=(0, 10))

        card_b = ctk.CTkFrame(kpi_frame, fg_color=("#E0E0E0", "#2D2D2D"), corner_radius=6)
        card_b.grid(row=0, column=1, sticky="nsew", padx=5)
        ctk.CTkLabel(card_b, text="📥 Εισπράξεις Ταμείου", font=lbl_font, text_color="#10B981").pack(pady=(10, 2))
        ctk.CTkLabel(card_b, text=f"€{financials['total_collected']:.2f}", font=num_font).pack()
        ctk.CTkLabel(card_b, text=f"Εργασίες: {financials['job_count']} καταχωρήσεις", font=ctk.CTkFont(size=14), text_color="#888888").pack(pady=(0, 10))

        card_c = ctk.CTkFrame(kpi_frame, fg_color=("#E0E0E0", "#2D2D2D"), corner_radius=6)
        card_c.grid(row=0, column=2, sticky="nsew", padx=5)
        ctk.CTkLabel(card_c, text="⏳ Ανεξόφλητο Υπόλοιπο", font=lbl_font, text_color="#F59E0B").pack(pady=(10, 2))
        ctk.CTkLabel(card_c, text=f"€{financials['floating_balance']:.2f}", font=num_font).pack()
        ctk.CTkLabel(card_c, text="Τρέχοντα ανεξόφλητα παραστατικά", font=ctk.CTkFont(size=14), text_color="#888888").pack(pady=(0, 10))

        # --- ROW 2: OPERATIONS TRACKER (SCROLLABLE & CLICKABLE) ---
        ops_frame = ctk.CTkFrame(self.analytics_scroll, fg_color=("#EAEAEA", "#252525"), corner_radius=6)
        ops_frame.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(ops_frame, text="👷 Κατανομή Έργου Συνεργείων (Κλικ για Αναλυτικές Εργασίες 🔍)", font=lbl_font, anchor="w").pack(fill="x", padx=15, pady=(10, 5))
        
        if crew_stats:
            crew_scroll = ctk.CTkScrollableFrame(ops_frame, fg_color="transparent", height=200)
            crew_scroll.pack(fill="x", padx=15, pady=(0, 10))
            for i, (member, count) in enumerate(crew_stats.items()):
                txt = f"• {member}: {count} Εργασίες"
                lbl = ctk.CTkLabel(crew_scroll, text=txt, font=sub_font, anchor="w", cursor="hand2")
                lbl.grid(row=i//2, column=i%2, sticky="w", padx=20, pady=4)
                lbl.bind("<Button-1>", lambda e, m=member: self.open_crew_detail_view(m))
        else:
            ctk.CTkLabel(ops_frame, text="Δεν βρέθηκαν εκτελεσμένες εργασίες από συνεργεία σε αυτό το διάστημα.", font=ctk.CTkFont(slant="italic"), anchor="w").pack(padx=15, pady=(0, 10))

        # --- ROW 3: DEBTORS VIEW (SCROLLABLE + CLICKABLE NAMES) ---
        debt_frame = ctk.CTkFrame(self.analytics_scroll, fg_color=("#EAEAEA", "#252525"), corner_radius=6)
        debt_frame.pack(fill="x", padx=15, pady=(10, 15))
        ctk.CTkLabel(debt_frame, text="🚨 Ληξιπρόθεσμα & Ενεργά Υπόλοιπα", font=lbl_font, text_color="#EF4444", anchor="w").pack(fill="x", padx=15, pady=(10, 5))

        critical = [d for d in debtors if d['days_stagnant'] >= 90]
        warning  = [d for d in debtors if 30 <= d['days_stagnant'] < 90]
        active   = [d for d in debtors if d['days_stagnant'] < 30]

        if not debtors:
            ctk.CTkLabel(debt_frame, text="✔️ Όλες οι καρτέλες είναι καθαρές για τα επιλεγμένα κριτήρια.", font=ctk.CTkFont(slant="italic"), text_color="#10B981", anchor="w").pack(padx=15, pady=(0, 10))
        else:
            debt_scroll = ctk.CTkScrollableFrame(debt_frame, fg_color="transparent", height=300)
            debt_scroll.pack(fill="x", padx=10, pady=(0, 10))

            def _make_debtor_label(parent, d, color=None):
                """Creates a clickable debtor label that navigates to client detail view."""
                txt = f"  • {d['name']} ({d['code']}) — €{d['debt']:.2f}"
                lbl = ctk.CTkLabel(parent, text=txt, font=sub_font, anchor="w",
                    text_color=color if color else ("black", "white"), cursor="hand2")
                lbl.pack(fill="x", padx=15)
                lbl.bind("<Button-1>", lambda e, code=d['code']: self.open_client_detail_view(code))

            if critical:
                ctk.CTkLabel(debt_scroll, text="🔴 Κρίσιμα (90+ Ημέρες)", font=ctk.CTkFont(weight="bold"), text_color="#EF4444", anchor="w").pack(fill="x", padx=15, pady=2)
                for d in critical:
                    _make_debtor_label(debt_scroll, d, "#FF8B8B")
            if warning:
                ctk.CTkLabel(debt_scroll, text="🟡 Προσοχή (30-90 Ημέρες)", font=ctk.CTkFont(weight="bold"), text_color="#F59E0B", anchor="w").pack(fill="x", padx=15, pady=2)
                for d in warning:
                    _make_debtor_label(debt_scroll, d)
            if active:
                ctk.CTkLabel(debt_scroll, text="🟢 Πρόσφατα Υπόλοιπα (<30 Ημέρες)", font=ctk.CTkFont(weight="bold"), text_color="#10B981", anchor="w").pack(fill="x", padx=15, pady=2)
                for d in active:
                    _make_debtor_label(debt_scroll, d, "#A3E635")

        self.dynamic_ui_scaler(self.analytics_scroll)


    def trigger_wipe_data_action(self):
        import tkinter.messagebox as mb
        if mb.askyesno("ΠΡΟΣΟΧΗ",
            "Είστε σίγουροι ότι θέλετε να διαγράψετε οριστικά όλα τα δεδομένα;\n\nΑυτή η ενέργεια δεν αναιρείται."):
            try:
                # ── FIRING ACTUAL DATABASE PURGE WORKER FROM BACKEND ──
                from logic_engine import wipe_all_application_records
                wipe_all_application_records()
                
                # Force-clear out the active screen layout views instantly
                if hasattr(self, 'execute_calendar_query_action'): self.execute_calendar_query_action(None)
                if hasattr(self, 'populate_payments_list'): self.populate_payments_list()
                if hasattr(self, 'execute_registry_query'): self.execute_registry_query(None)
                if hasattr(self, 'refresh_analytics_view_action'): self.refresh_analytics_view_action(None)
                
                mb.showinfo("Επιτυχία", "Η βάση δεδομένων εκκαθαρίστηκε πλήρως. Έτοιμο για παράδοση!")
            except Exception as purge_error:
                mb.showerror("Σφάλμα", f"Αδυναμία καθαρισμού δεδομένων:\n{str(purge_error)}")

    def refresh_calendar_job_categories(self):
        """Ανανεώνει αποκλειστικά το dropdown κατηγοριών στο παράθυρο Νέας Εργασίας."""
        if hasattr(self, 'job_inp_cat1') and self.job_inp_cat1:
            try:
                from logic_engine import get_config_list
                live_cats = get_config_list('job_categories')
                self.job_inp_cat1.configure(values=live_cats if live_cats else ["ΑΠΕΝΤΟΜΩΣΗ"])
                if live_cats:
                    self.job_inp_cat1.set(live_cats[0])
                else:
                    self.job_inp_cat1.set("ΑΠΕΝΤΟΜΩΣΗ")
            except Exception:
                self.job_inp_cat1.configure(values=["ΑΠΕΝΤΟΜΩΣΗ"])
                self.job_inp_cat1.set("ΑΠΕΝΤΟΜΩΣΗ")            

    def trigger_backup_execution_action(self):
        from logic_engine import execute_safe_system_export, get_available_folder_backups
        import os
        self.lbl_backup_status.configure(text="⬇ Exporting database and CSV snapshots...", text_color="#3B8ED0")
        self.update_idletasks()
        try:
            result = execute_safe_system_export()
            lines = [
                "✅ Snapshot & Export Complete", 
                f"Folder: {os.path.basename(result['backup_dir'])}", 
                "",
                "💾 Database Backup Cloned Inside.",
                "📄 all_clients.csv Compiled.",
                "📄 all_jobs.csv Compiled.",
                "📄 all_payments.csv Compiled.",
                "",
                f"Directory Location: {result['backup_dir']}"
            ]
            success_txt = "\n".join(lines)
            self.lbl_backup_status.configure(text=success_txt, text_color="#6BCB77", font=ctk.CTkFont(size=18))
            
            # Hot-refresh our recovery dropdown list options instantly
            if hasattr(self, 'backup_dropdown_menu'):
                fresh_backups = get_available_folder_backups() or ["Δεν βρέθηκαν αντίγραφα ασφαλείας"]
                self.backup_dropdown_menu.configure(values=fresh_backups)
                self.backup_dropdown_menu.set(fresh_backups[0])
                
        except Exception as err:
            msg = f"❌ PERMISSION DENIED: Cannot write to backup directory.\n{str(err)}"
            self.lbl_backup_status.configure(text=msg, text_color="#FF6B6B")

    def init_settings_frame(self):
        frame = ctk.CTkFrame(self.desk_container, fg_color="transparent")
        scroll = ctk.CTkScrollableFrame(frame, label_text="Ρυθμίσεις Συστήματος")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Panel 1: UI Scaling & Localization
        ui_panel = ctk.CTkFrame(scroll, corner_radius=8)
        ui_panel.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(ui_panel, text="⚙ UI Scaling & Localization", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w", padx=20, pady=(15, 10))
        ctk.CTkLabel(ui_panel, text=f"Font Size: {self.ui_cfg.settings['font_size']}px", font=ctk.CTkFont(size=18), anchor="w").grid(row=1, column=0, sticky="w", padx=20)
        font_slider = ctk.CTkSlider(ui_panel, from_=12, to=28, number_of_steps=16, command=self.on_font_slider_changed)
        font_slider.set(self.ui_cfg.settings['font_size'])
        font_slider.grid(row=1, column=1, padx=20, pady=5, sticky="ew")
        ctk.CTkLabel(ui_panel, text="Language / Γλώσσα", font=ctk.CTkFont(size=18), anchor="w").grid(row=3, column=0, sticky="w", padx=20)
        lang_menu = ctk.CTkOptionMenu(ui_panel, values=["Ελληνικά", "English"], command=lambda v: self.ui_cfg.settings.update({'lang': 'el' if v == "Ελληνικά" else 'en'}))
        lang_menu.grid(row=3, column=1, padx=20, pady=5, sticky="ew")

        # Panel 2: Backup / Snapshots
        backup_panel = ctk.CTkFrame(scroll, corner_radius=8)
        backup_panel.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(backup_panel, text="🔒 Redundant Workspace Preservation Ledger", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))
        lbl_desc = ctk.CTkLabel(backup_panel, text="Creates a timestamped binary copy of the database plus labelled CSV exports inside local timestamp folders.", justify="left", anchor="w", font=ctk.CTkFont(size=18), text_color="gray", wraplength=650)
        lbl_desc.pack(anchor="w", padx=20, pady=(0, 15))
        self.btn_run_backup = ctk.CTkButton(backup_panel, text="🚀 Execute Snapshot & Export CSV Sheets", height=45, fg_color="#2EA44F", hover_color="#2C974B", command=self.trigger_backup_execution_action)
        self.btn_run_backup.pack(fill="x", padx=20, pady=(0, 20))
        self.lbl_backup_status = ctk.CTkLabel(backup_panel, text="System status: Workspace preservation matrix online.", font=ctk.CTkFont(size=18, slant="italic"), anchor="w")
        self.lbl_backup_status.pack(anchor="w", padx=20, pady=(0, 15))

        # ─── PANEL 3: ΜΟΝΙΜΟ ΚΕΝΤΡΟ ΑΠΟΚΑΤΑΣΤΑΣΗΣ (INJECTED RECOVERY CENTER) ───
        recovery_panel = ctk.CTkFrame(scroll, corner_radius=8)
        recovery_panel.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(recovery_panel, text="🛠️ Κέντρο Ανάκτησης & Αποκατάστασης Δεδομένων", font=ctk.CTkFont(size=18, weight="bold"), text_color="#3B8ED0", anchor="w").pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(recovery_panel, text="Επιλέξτε ένα αυτόματο σημείο ελέγχου (BACKUP - DATE) ή αναζητήστε ένα αρχείο βάσης χειροκίνητα:", font=ctk.CTkFont(size=16), text_color="gray", anchor="w").pack(anchor="w", padx=20, pady=(0, 15))
        
        control_inner_row = ctk.CTkFrame(recovery_panel, fg_color="transparent")
        control_inner_row.pack(fill="x", padx=20, pady=(0, 20))

        from logic_engine import get_available_folder_backups, restore_database_hot_swap
        backup_checkpoints = get_available_folder_backups() or ["Δεν βρέθηκαν αντίγραφα ασφαλείας"]
        
        self.backup_dropdown_menu = ctk.CTkOptionMenu(control_inner_row, values=backup_checkpoints, font=ctk.CTkFont(size=16), width=300, height=40)
        self.backup_dropdown_menu.pack(side="left", padx=(0, 10))

        def trigger_checkpoint_restore_action():
            chosen_folder = self.backup_dropdown_menu.get()
            if chosen_folder.startswith("Δεν βρέθηκαν") or not chosen_folder: return
            from logic_engine import BACKUP_DIR
            import os
            target_path = os.path.join(BACKUP_DIR, chosen_folder, "company_data.db")
            
            from app_gui import ConfirmationDialog
            ConfirmationDialog(self, f"Επαναφορά στο σημείο {chosen_folder};\nΤα τρέχοντα δεδομένα θα μετονομαστούν σε .old", 
                lambda: execute_system_hot_swap_sequence(target_path))

        ctk.CTkButton(control_inner_row, text="⏪ Ανάκτηση Σημείου", font=ctk.CTkFont(size=16, weight="bold"), fg_color="#F59E0B", hover_color="#D97706", height=40, command=trigger_checkpoint_restore_action).pack(side="left", padx=(0, 10))

        def trigger_manual_file_picker_swap():
            from tkinter import filedialog
            selected_file = filedialog.askopenfilename(title="Επιλέξτε Αρχείο Βάσης (.db)", filetypes=[("Database Files", "*.db"), ("All Files", "*.*")])
            if selected_file: execute_system_hot_swap_sequence(selected_file)

        ctk.CTkButton(control_inner_row, text="📁 Χειροκίνητη Επιλογή (.db)", font=ctk.CTkFont(size=16, weight="bold"), fg_color=("#D0D0D0", "#3A3A3A"), text_color=("#1A1A1A", "#E0E0E0"), height=40, command=trigger_manual_file_picker_swap).pack(side="left")

        def execute_system_hot_swap_sequence(file_source_target):
            try:
                if restore_database_hot_swap(file_source_target):
                    import tkinter.messagebox as mb
                    mb.showinfo("✅ Επιτυχία!", "Η βάση δεδομένων αποκαταστάθηκε με επιτυχία.\nΌλες οι καρτέλες ανανεώθηκαν!")
                    if hasattr(self, 'execute_registry_query'): self.execute_registry_query(None)
                    if hasattr(self, 'execute_calendar_query_action'): self.execute_calendar_query_action(None)
                    if hasattr(self, 'populate_payments_list'): self.populate_payments_list()
                    if hasattr(self, 'refresh_analytics_view_action'): self.refresh_analytics_view_action(None)
                    fresh_backups = get_available_folder_backups() or ["Δεν βρέθηκαν αντίγραφα ασφαλείας"]
                    self.backup_dropdown_menu.configure(values=fresh_backups)
                    self.backup_dropdown_menu.set(fresh_backups[0])
            except Exception as error_msg:
                import tkinter.messagebox as mb
                mb.showerror("❌ Σφάλμα Ανάκτησης", str(error_msg))

        # Panel 4: System paths view
        env_panel = ctk.CTkFrame(scroll, corner_radius=8)
        env_panel.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(env_panel, text="📁 System Directory Properties", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))
        prop_txt = f"Database Path: {db_path if 'db_path' in dir() else './company_data.db'}\nBackup Directory: ./backups/"
        ctk.CTkLabel(env_panel, text=prop_txt, justify="left", anchor="w", font=ctk.CTkFont(size=18, family="monospace"), text_color="gray").pack(fill="x", padx=20, pady=(0, 15))

        # Panel 5: Crew & Category Management lists
        data_panel = ctk.CTkFrame(scroll, corner_radius=8)
        data_panel.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(data_panel, text="👥 Crew & Category Editor", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w", padx=20, pady=(15, 5))
        self.settings_list_canvas = ctk.CTkScrollableFrame(data_panel, height=160, width=550)
        self.settings_list_canvas.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        data_panel.grid_columnconfigure(0, weight=1)

        def refresh_settings_preview():
            from logic_engine import get_config_list, remove_config_list_item
            for w in self.settings_list_canvas.winfo_children(): w.destroy()
            for cfg_key in ['crew_members', 'job_categories', 'job_subcategories', 'payment_methods']:
                items = get_config_list(cfg_key)
                lbl = ctk.CTkLabel(self.settings_list_canvas, text=f"{cfg_key}:", font=ctk.CTkFont(size=18, weight="bold"), anchor="w")
                lbl.pack(fill="x", padx=10, pady=(8, 0))
                for item in items:
                    row = ctk.CTkFrame(self.settings_list_canvas, fg_color="transparent")
                    row.pack(fill="x", padx=10, pady=1)
                    ctk.CTkLabel(row, text=f"   • {item}", font=ctk.CTkFont(size=18), anchor="w").pack(side="left", fill="x", expand=True)
                    from logic_engine import remove_config_list_item
                    ctk.CTkButton(row, text="❌", width=25, height=25, fg_color="transparent", text_color="#EF4444", font=ctk.CTkFont(size=18),
                        command=lambda k=cfg_key, i=item: (remove_config_list_item(k, i), refresh_settings_preview())).pack(side="right")

        refresh_settings_preview()

        add_row = ctk.CTkFrame(data_panel, fg_color="transparent")
        add_row.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        add_row.grid_columnconfigure(1, weight=1)
        from logic_engine import add_config_list_item

        # Form Inputs Rows
        ctk.CTkLabel(add_row, text="Crew:", font=ctk.CTkFont(size=18)).grid(row=0, column=0, padx=(0, 3))
        self.settings_new_crew = ctk.CTkEntry(add_row, placeholder_text="Add crew member...", font=ctk.CTkFont(size=18))
        self.settings_new_crew.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        ctk.CTkButton(add_row, text="+", width=30, font=ctk.CTkFont(size=18), command=lambda: (add_config_list_item('crew_members', self.settings_new_crew.get().strip()), refresh_settings_preview(), self.sync_all_dropdowns())).grid(row=0, column=2, padx=(0, 10))

        ctk.CTkLabel(add_row, text="Cat:", font=ctk.CTkFont(size=18)).grid(row=1, column=0, padx=(0, 3), pady=(8, 0))
        self.settings_new_cat = ctk.CTkEntry(add_row, placeholder_text="Add category...", font=ctk.CTkFont(size=18))
        self.settings_new_cat.grid(row=1, column=1, sticky="ew", padx=(0, 5), pady=(8, 0))
        ctk.CTkButton(add_row, text="+", width=30, font=ctk.CTkFont(size=18),
            command=lambda: (add_config_list_item('job_categories', self.settings_new_cat.get().strip()), refresh_settings_preview(), self.refresh_calendar_job_categories())
        ).grid(row=1, column=2, padx=(0, 10), pady=(get_scaled_size(8), 0))

        ctk.CTkLabel(add_row, text="Pay Method:", font=ctk.CTkFont(size=18)).grid(row=2, column=0, padx=(0, 3), pady=(8, 0))
        self.settings_new_pay = ctk.CTkEntry(add_row, placeholder_text="Add payment method...", font=ctk.CTkFont(size=18))
        self.settings_new_pay.grid(row=2, column=1, sticky="ew", padx=(0, 5), pady=(8, 0))
        ctk.CTkButton(add_row, text="+", width=30, font=ctk.CTkFont(size=18), command=lambda: (add_config_list_item('payment_methods', self.settings_new_pay.get().strip()), refresh_settings_preview(), self.sync_all_dropdowns())).grid(row=2, column=2, padx=(0, 10), pady=(8, 0))

        ctk.CTkLabel(add_row, text="SubCat:", font=ctk.CTkFont(size=18)).grid(row=3, column=0, padx=(0, 3), pady=(8, 0))
        self.settings_new_subcat = ctk.CTkEntry(add_row, placeholder_text="Add subcategory...", font=ctk.CTkFont(size=18))
        self.settings_new_subcat.grid(row=3, column=1, sticky="ew", padx=(0, 5), pady=(8, 0))
        ctk.CTkButton(add_row, text="+", width=30, font=ctk.CTkFont(size=18), command=lambda: (add_config_list_item('job_subcategories', self.settings_new_subcat.get().strip()), refresh_settings_preview(), self.sync_all_dropdowns())).grid(row=3, column=2, padx=(0, 10), pady=(8, 0))

        # Big Global Wipe Button packed cleanly at base of settings stack
        ctk.CTkButton(scroll, text="⚠️ Διαγραφή Όλων των Δεδομένων (Wipe Application Data)", fg_color="#C0392B", hover_color="#E74C3C", font=("Arial", 18, "bold"), height=55, command=self.trigger_wipe_data_action).pack(fill="x", padx=15, pady=(20, 15))

        self.frames["settings"] = frame

        

    def trigger_wipe_data_action(self):
        import tkinter.messagebox as mb
        if mb.askyesno("ΠΡΟΣΟΧΗ",
            "Είστε σίγουροι ότι θέλετε να διαγράψετε οριστικά όλα τα δεδομένα;\n\nΑυτή η ενέργεια δεν αναιρείται."):
            try:
                # ── ΕΝΕΡΓΟΠΟΙΗΣΗ ΠΡΑΓΜΑΤΙΚΟΥ DATABASE PURGE WORKER ──
                from logic_engine import wipe_all_application_records
                wipe_all_application_records()
                
                # Καθαρισμός των UI πλεγμάτων στην οθόνη εκείνη τη στιγμή
                if hasattr(self, 'execute_calendar_query_action'): self.execute_calendar_query_action(None)
                if hasattr(self, 'populate_payments_list'): self.populate_payments_list()
                if hasattr(self, 'execute_registry_query'): self.execute_registry_query(None)
                if hasattr(self, 'refresh_analytics_view_action'): self.refresh_analytics_view_action(None)
                
                mb.showinfo("Επιτυχία", "Η βάση δεδομένων εκκαθαρίστηκε πλήρως από όλα τα  δεδομένα.")
            except Exception as purge_error:
                mb.showerror("Σφάλμα", f"Αδυναμία καθαρισμού δεδομένων:\n{str(purge_error)}")

    def trigger_backup_execution_action(self):
        from logic_engine import execute_safe_system_export, get_available_folder_backups
        import os
        self.lbl_backup_status.configure(text="⬇ Exporting database and CSV snapshots...", text_color="#3B8ED0")
        self.update_idletasks()
        try:
            result = execute_safe_system_export()
            lines = [
                "✅ Backup & Export Complete", 
                f"Folder: {os.path.basename(result['backup_dir'])}", 
                "",
                "💾 Database Backup Cloned Inside.",
                "📄 all_clients.csv Compiled.",
                "📄 all_jobs.csv Compiled.",
                "📄 all_payments.csv Compiled.",
                "",
                f"Directory Location: {result['backup_dir']}"
            ]
            success_txt = "\n".join(lines)
            self.lbl_backup_status.configure(text=success_txt, text_color="#6BCB77", font=ctk.CTkFont(size=18))
            
            # Ανανέωση του Dropdown επιλογής σημείων ανάκτησης live
            if hasattr(self, 'backup_dropdown_menu'):
                fresh_backups = get_available_folder_backups() or ["Δεν βρέθηκαν αντίγραφα ασφαλείας"]
                self.backup_dropdown_menu.configure(values=fresh_backups)
                self.backup_dropdown_menu.set(fresh_backups[0])
                
        except Exception as err:
            msg = f"❌ PERMISSION DENIED: Cannot write to backup directory.\n{str(err)}"
            self.lbl_backup_status.configure(text=msg, text_color="#FF6B6B")
            if hasattr(self, 'open_error_modal'):
                self.open_error_modal(str(err))

    def init_recovery_center_panel(self):
        """Κατασκευάζει το Κέντρο Ανάκτησης μόνιμα στο settings canvas κατά το boot της εφαρμογής."""
        import os
        from logic_engine import get_available_folder_backups, restore_database_hot_swap
        
        # ─────────────────────────────────────────────────────────────────
        # ΑΥΤΟΝΟΜΟ ΜΟΝΙΜΟ ΠΑΝΕΛ ΑΠΟΚΑΤΑΣΤΑΣΗΣ
        # ─────────────────────────────────────────────────────────────────
        recovery_lbl_frame = ctk.CTkFrame(self.settings_list_canvas, fg_color=("#EAEAEA", "#252525"), corner_radius=6)
        recovery_lbl_frame.pack(fill="x", padx=10, pady=(20, 10))
        
        ctk.CTkLabel(recovery_lbl_frame, text="🛠️ Κέντρο Ανάκτησης & Αποκατάστασης", 
            font=ctk.CTkFont(size=20, weight="bold"), text_color="#3B8ED0", anchor="w").pack(fill="x", padx=15, pady=(10, 5))
            
        ctk.CTkLabel(recovery_lbl_frame, text="Επιλέξτε ένα αυτόματο σημείο ελέγχου από τον φάκελο backups ή αναζητήστε ένα αρχείο χειροκίνητα:", 
            font=ctk.CTkFont(size=15), text_color="gray", anchor="w").pack(fill="x", padx=15, pady=(0, 10))

        control_inner_row = ctk.CTkFrame(recovery_lbl_frame, fg_color="transparent")
        control_inner_row.pack(fill="x", padx=15, pady=(0, 15))

        # 1. Φόρτωση Dropdown Checkpoints
        backup_checkpoints = get_available_folder_backups() or ["Δεν βρέθηκαν αντίγραφα ασφαλείας"]
        
        self.backup_dropdown_menu = ctk.CTkOptionMenu(control_inner_row, values=backup_checkpoints, font=ctk.CTkFont(size=16), width=320, height=40)
        self.backup_dropdown_menu.pack(side="left", padx=(0, 10))

        # 2. Trigger για Αυτόματη Ανάκτηση Επιλεγμένου Φακέλου
        def trigger_checkpoint_restore_action():
            chosen_folder = self.backup_dropdown_menu.get()
            if chosen_folder.startswith("Δεν βρέθηκαν") or not chosen_folder:
                return
            from logic_engine import BACKUP_DIR
            target_path = os.path.join(BACKUP_DIR, chosen_folder, "company_data.db")
            
            from app_gui import ConfirmationDialog
            if 'ConfirmationDialog' in globals():
                ConfirmationDialog(self, f"Επαναφορά στο σημείο {chosen_folder};\nΤα τρέχοντα δεδομένα θα αποθηκευτούν ως .old", 
                    lambda: execute_system_hot_swap_sequence(target_path))

        ctk.CTkButton(control_inner_row, text="⏪ Ανάκτηση Σημείου", font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#F59E0B", hover_color="#D97706", height=40, command=trigger_checkpoint_restore_action).pack(side="left", padx=(0, 15))

        # 3. Failsafe Manual File Picker (Windows Explorer Window Dialog)
        def trigger_manual_file_picker_swap():
            from tkinter import filedialog
            selected_file = filedialog.askopenfilename(
                title="Επιλέξτε Αρχείο Βάσης Δεδομένων (.db)",
                filetypes=[("Database Files", "*.db"), ("All Files", "*.*")]
            )
            if selected_file:
                execute_system_hot_swap_sequence(selected_file)

        ctk.CTkButton(control_inner_row, text="📁 Χειροκίνητη Επιλογή (.db)", font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=("#D0D0D0", "#3A3A3A"), text_color=("#1A1A1A", "#E0E0E0"), height=40, command=trigger_manual_file_picker_swap).pack(side="left")

        # 4. Κεντρικός Μηχανισμός Hot-swap Αντικατάστασης
        def execute_system_hot_swap_sequence(file_source_target):
            try:
                if restore_database_hot_swap(file_source_target):
                    from app_gui import MessagePopup
                    if 'MessagePopup' in globals():
                        MessagePopup(self, "✅ Επιτυχία!", "Η βάση δεδομένων αποκαταστάθηκε με επιτυχία.\nΗ εφαρμογή θα ανανεώσει τα δεδομένα τώρα.")
                    
                    # Άμεσο force-refresh όλων των ανοιχτών πλεγμάτων
                    if hasattr(self, 'execute_registry_query'): self.execute_registry_query(None)
                    if hasattr(self, 'execute_calendar_query_action'): self.execute_calendar_query_action(None)
                    if hasattr(self, 'populate_payments_list'): self.populate_payments_list()
                    if hasattr(self, 'refresh_analytics_view_action'): self.refresh_analytics_view_action(None)
                    
                    # Refresh της λίστας του dropdown
                    fresh_backups = get_available_folder_backups() or ["Δεν βρέθηκαν αντίγραφα ασφαλείας"]
                    self.backup_dropdown_menu.configure(values=fresh_backups)
                    self.backup_dropdown_menu.set(fresh_backups[0])
            except Exception as error_msg:
                from app_gui import MessagePopup
                if 'MessagePopup' in globals():
                    MessagePopup(self, "❌ Σφάλμα Ανάκτησης", f"Αδυναμία φόρτωσης αρχείου:\n{str(error_msg)}")


    def sync_all_dropdowns(self):
        from logic_engine import get_config_list
        crew_list = get_config_list("crew_members")
        job_cats = get_config_list("job_categories")
        job_subcats = get_config_list("job_subcategories")
        pay_methods = get_config_list("payment_methods")
        
        if not crew_list:
            crew_list = ["-"]
            
        if hasattr(self, 'new_crew_combo'):
            self.new_crew_combo.configure(values=crew_list)
        if hasattr(self, 'job_inp_cat1'):
            self.job_inp_cat1.configure(values=job_cats if job_cats else ["ΑΠΕΝΤΟΜΩΣΗ"])
        if hasattr(self, 'job_inp_cat2'):
            self.job_inp_cat2.configure(values=job_subcats if job_subcats else ["ΚΑΤΣΑΡΙΔΕΣ", "ΠΟΝΤΙΚΙΑ", "ΜΙΚΡΟΒΙΑ"])
        if hasattr(self, 'inp_method'):
            self.inp_method.configure(values=pay_methods if pay_methods else ["ΜΕΤΡΗΤΑ (Cash)"])

    def init_registry_frame(self):
        # Force top-level window constraints
        self.desk_container.grid_columnconfigure(0, weight=1)
        self.desk_container.grid_rowconfigure(0, weight=1)

        frame = ctk.CTkFrame(self.desk_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=4) # Left panel (list + profile) gets 80% width
        frame.grid_columnconfigure(1, weight=1) # Right panel (form) gets 20% width
        
        # Enforce an absolute 1:1 vertical split to eliminate artificial whitespace panels
        frame.grid_rowconfigure(2, weight=1)    # Top List Area
        frame.grid_rowconfigure(3, weight=1)    # Bottom Profile Card Area

        ctk.CTkLabel(frame, text="Αναζήτηση Πελατών", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        self.search_entry = ctk.CTkEntry(frame,
            placeholder_text="Enter Name, Phone, or VAT (*code for exact match)...")
        self.search_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
        self._search_debounce_id = None
        self.search_entry.bind("<KeyRelease>", self._debounced_registry_query)

        self.results_box = ctk.CTkScrollableFrame(frame, label_text="Λίστα Πελατών")
        self.results_box.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)

        

        self.profile_panel = ctk.CTkFrame(frame, fg_color=("#E0E0E0", "#222222"), corner_radius=8)
        self.profile_lbl = ctk.CTkLabel(self.profile_panel, text="Επιλέξτε έναν πελάτη για προβολή.", font=ctk.CTkFont(slant="italic"))
        self.profile_lbl.pack(expand=True, padx=20, pady=20)
        self.profile_panel.grid(row=3, column=0, sticky="nsew", padx=5, pady=(0, get_scaled_size(8)))

        # --- FORM REBUILD: NOW SCROLLABLE AND DYNAMIC ---
        # Convert to CTkScrollableFrame to enable scrolling and prevent clipping
        self.client_creation_frame = ctk.CTkScrollableFrame(frame, fg_color=("#E0E0E0", "#222222"), corner_radius=8, label_text="Προσθήκη Νέου Πελάτη", label_font=ctk.CTkFont(size=18, weight="bold"))
        self.client_creation_frame.grid(row=2, column=1, sticky="nsew", padx=5, pady=5, rowspan=2)

        # The form body holds the grid of inputs. NO expand=True.
        form_body = ctk.CTkFrame(self.client_creation_frame, fg_color="transparent")
        form_body.pack(fill="x", expand=False, padx=10, pady=5)
        form_body.grid_columnconfigure(0, weight=0) # Label column fixed
        form_body.grid_columnconfigure(1, weight=1) # Entry column stretches

        self.new_client_entries = {}
        fields_layout = CLIENT_FIELDS_SCHEMA
        for idx, (label_text, key) in enumerate(fields_layout):
            lbl = ctk.CTkLabel(form_body, text=label_text, font=ctk.CTkFont(size=18, weight="bold"), anchor="w")
            lbl.grid(row=idx, column=0, padx=(0, get_scaled_size(10)), pady=get_scaled_size(8), sticky="w")
            
            # Input font bumped to 20 to prevent it from looking smaller than labels
            ent = ctk.CTkEntry(form_body, font=ctk.CTkFont(size=20), height=get_scaled_size(45))
            ent.grid(row=idx, column=1, padx=0, pady=get_scaled_size(8), sticky="ew")
            self.new_client_entries[key] = ent
            if key == fields_layout[0][1]:
                setattr(self, "new_client_name", ent)

        notes_idx = len(fields_layout)
        ctk.CTkLabel(form_body, text="Σημειώσεις", font=ctk.CTkFont(size=18, weight="bold"), anchor="w").grid(row=notes_idx, column=0, padx=(0, get_scaled_size(10)), pady=get_scaled_size(8), sticky="nw")
        
        # Notes font bumped to 20
        self.new_client_notes = ctk.CTkTextbox(form_body, height=get_scaled_size(120), font=ctk.CTkFont(size=20))
        self.new_client_notes.grid(row=notes_idx, column=1, padx=0, pady=get_scaled_size(8), sticky="ew")

        # ACTION FOOTER (Packed directly below the form body to kill the gap)
        action_footer = ctk.CTkFrame(self.client_creation_frame, fg_color="transparent")
        action_footer.pack(fill="x", expand=False, padx=get_scaled_size(10), pady=(get_scaled_size(20), get_scaled_size(10)))

        self.btn_save_client = ctk.CTkButton(action_footer, text="💾 Αποθήκευση Πελάτη", height=get_scaled_size(45), fg_color="#10B981", font=ctk.CTkFont(size=18, weight="bold"), command=self.execute_save_new_client)
        self.btn_save_client.pack(fill="x", expand=False)

        self.lbl_new_client_status = ctk.CTkLabel(action_footer, text="", font=ctk.CTkFont(slant="italic"))
        self.lbl_new_client_status.pack(fill="x", expand=False, pady=(get_scaled_size(8), 0))

        self.frames["registry"] = frame
        self.execute_registry_query(None)

    def execute_save_new_client(self):
        from logic_engine import register_new_client_record
        name = self.new_client_name.get().strip()
        if not name:
            self.lbl_new_client_status.configure(text="❌ Το όνομα πελάτη είναι υποχρεωτικό.", text_color="#FF6B6B")
            return
        payload = {
            "name": name,
            "telephone": self.new_client_entries.get("phone", ctk.CTkEntry).get().strip(),
            "telephone_2": self.new_client_entries.get("phone_2", ctk.CTkEntry).get().strip(),
            "address": self.new_client_entries.get("address", ctk.CTkEntry).get().strip(),
            "address_2": self.new_client_entries.get("address_2", ctk.CTkEntry).get().strip(),
            "area": self.new_client_entries.get("area", ctk.CTkEntry).get().strip(),
            "vat_number": self.new_client_entries.get("vat", ctk.CTkEntry).get().strip(),
            "profession": self.new_client_entries.get("profession", ctk.CTkEntry).get().strip(),
            "notes": self.new_client_notes.get("0.0", "end").strip(),
        }
        new_code = register_new_client_record(payload)
        if new_code:
            for entry in self.new_client_entries.values():
                entry.delete(0, ctk.END)
            self.new_client_notes.delete("0.0", "end")
            self.lbl_new_client_status.configure(text=f"✅ Ο πελάτης αποθηκεύτηκε με κωδικό {new_code}.", text_color="#6BCB77")
            self.execute_registry_query(None)
        else:
            self.lbl_new_client_status.configure(text="❌ Αποτυχία αποθήκευσης πελάτη.", text_color="#FF6B6B")

    def _debounced_registry_query(self, event):
        """Debounce: waits 350ms after last keystroke before running the actual search."""
        if self._search_debounce_id is not None:
            self.after_cancel(self._search_debounce_id)
        self._search_debounce_id = self.after(350, lambda: self.execute_registry_query(None))

    def execute_registry_query(self, event):
        for widget in self.results_box.winfo_children():
            widget.destroy()
        search_term = self.search_entry.get().strip()
        search_results = fuzzy_search_clients(search_term)
        if not search_results:
            no_match = ctk.CTkLabel(self.results_box, text="Zero database coordinates match the query parameter.", font=ctk.CTkFont(slant="italic"))
            no_match.pack(pady=20)
            return

        # Limit UI card rendering to top 30 items for blazing fast response
        search_results = search_results[:30]

        for client in search_results:
            row_frame = ctk.CTkFrame(self.results_box, fg_color="transparent")
            # --- CRITICAL HORIZONTAL FIX: expand=True and padx=0 ---
            row_frame.pack(fill="x", expand=True, padx=0, pady=5)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=0)
            row_frame.grid_rowconfigure(0, weight=1)
            
            card = ctk.CTkFrame(row_frame, fg_color=("#F5F5F5", "#2D2D2D"), cursor="hand2")
            card.grid(row=0, column=0, sticky="nsew", padx=0)
            card.grid_columnconfigure(0, weight=1)
            
            # --- MULTI-WIDGET CLICK BINDING: frame + labels to prevent label swallow ---
            def on_card_click(event, code=client['code']):
                print(f"DEBUG: Client card row clicked for code: {code}")
                from logic_engine import get_client_by_code, get_client_balance
                fresh = get_client_by_code(code)
                if fresh:
                    fresh['balance_owed'] = get_client_balance(code)
                    self.open_profile_timeline(fresh)
            card.bind("<Button-1>", on_card_click)
            display_text = f"🏢 {client['name']} — [{client['code']}]"
            lbl_name = ctk.CTkLabel(card, text=display_text, font=("Arial", 18, "bold"),
                anchor="w", justify="left")
            lbl_name.pack(anchor="w", fill="x", expand=True, padx=(5, 2), pady=(5, 2))
            # CRITICAL: bind click to label too so it doesn't swallow clicks
            lbl_name.bind("<Button-1>", on_card_click)
            detail_text = f"📞 Τηλ: {client['telephone']}  |  📄 ΑΦΜ: {client['vat']}"
            lbl_detail = ctk.CTkLabel(card, text=detail_text, font=("Arial", 18),
                anchor="w", justify="left", text_color=("#555555", "#AAAAAA"))
            lbl_detail.pack(anchor="w", padx=10, pady=(0, get_scaled_size(8)))
            # CRITICAL: bind click to detail label too
            lbl_detail.bind("<Button-1>", on_card_click)
            ctk.CTkButton(row_frame, text="✏️", width=38,
                fg_color=("#E0E0E0", "#3A3A3A"), text_color=("#1A1A1A", "#E0E0E0"), hover_color=("#D0D0D0", "#4A4A4A"),
                command=lambda c=client: self.open_client_edit_modal(c['code'])
            ).grid(row=0, column=1, sticky="ns")
            ctk.CTkButton(row_frame, text="🗑️", width=38,
                fg_color=("#C0392B", "#922B21"), text_color=("#FFFFFF", "#E0E0E0"), hover_color=("#E74C3C", "#A93226"),
                command=lambda c=client: ConfirmationDialog(
                    self,
                    f"Είστε σίγουροι για τη διαγραφή του πελάτη {c['code']} - {c['name']};",
                    lambda cc=c['code']: self.eav_delete_client(cc)
                )
            ).grid(row=0, column=2, sticky="ns")
        self.dynamic_ui_scaler(self.results_box)


    def open_client_edit_modal(self, client_code):
        try:
            from logic_engine import get_client_by_code, update_client_record
            import json
            record = get_client_by_code(client_code)
            if not record:
                return
            modal = ctk.CTkToplevel(self)
            modal.title("Επεξεργασία Πελάτη")
            modal.geometry("550x750")
            modal.transient(self)
            modal.grab_set()
            scroll_container = ctk.CTkScrollableFrame(modal)
            scroll_container.pack(fill="both", expand=True, padx=get_scaled_size(10), pady=get_scaled_size(10))
            ctk.CTkLabel(scroll_container, text=f"Κωδικός: {record.get('code', '')}",
                font=("Arial", 18, "bold"), anchor="w").pack(anchor="w", padx=15, pady=(10, 5))
            core_fields = [
                ("Όνομα", "name"), ("Τηλέφωνο", "phone"),
                ("Κινητό (Τηλ 2)", "phone_2"), ("Διεύθυνση", "address"),
                ("Διεύθυνση 2", "address_2"), ("Περιοχή", "area"),
                ("ΑΦΜ", "vat"), ("Επάγγελμα", "profession")
            ]
            core_entries = {}
            for label_text, key in core_fields:
                ctk.CTkLabel(scroll_container, text=label_text, font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=get_scaled_size(15), pady=(get_scaled_size(8), 0))
                ent = ctk.CTkEntry(scroll_container, font=ctk.CTkFont(size=18), height=get_scaled_size(45))
                db_key = {'phone': 'telephone', 'phone_2': 'telephone_2', 'address': 'address', 'address_2': 'address_2', 'vat': 'vat_number'}.get(key, key)
                ent.insert(0, str(record.get(db_key, "") or ""))
                ent.pack(fill="x", padx=get_scaled_size(15), pady=(0, get_scaled_size(5)))
                core_entries[key] = ent
            ctk.CTkLabel(scroll_container, text="Σημειώσεις", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=get_scaled_size(15), pady=(get_scaled_size(8), 0))
            notes_text = ctk.CTkTextbox(scroll_container, height=get_scaled_size(100), font=ctk.CTkFont(size=18))
            notes_text.insert("1.0", str(record.get('notes', "") or ""))
            notes_text.pack(fill="x", padx=get_scaled_size(15), pady=(0, get_scaled_size(8)))

            # 3. DYNAMIC EXTRA METADATA FIELDS
            extra_fields_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
            extra_fields_frame.pack(fill="x", padx=get_scaled_size(15), pady=get_scaled_size(5))

            raw_extras = record.get('extra_fields', {})
            if isinstance(raw_extras, str):
                try:
                    raw_extras = json.loads(raw_extras)
                except json.JSONDecodeError:
                    raw_extras = {}
            extra_data = dict(raw_extras) if raw_extras else {}
            dynamic_entries = {}

            def draw_extra_rows():
                for child in extra_fields_frame.winfo_children():
                    child.destroy()
                for k, v in extra_data.items():
                    row = ctk.CTkFrame(extra_fields_frame, fg_color="transparent")
                    row.pack(fill="x", pady=2)
                    ctk.CTkLabel(row, text=f"{k}:", font=ctk.CTkFont(size=18, weight="bold"),
                        width=get_scaled_size(120), anchor="w").pack(side="left", padx=get_scaled_size(5))
                    ent = ctk.CTkEntry(row, font=ctk.CTkFont(size=18), height=get_scaled_size(45))
                    ent.insert(0, str(v or ""))
                    ent.pack(side="left", fill="x", expand=True, padx=get_scaled_size(5))
                    dynamic_entries[k] = ent
                    def make_delete(target_key=k):
                        def do_delete():
                            if target_key in extra_data:
                                del extra_data[target_key]
                            if target_key in dynamic_entries:
                                del dynamic_entries[target_key]
                            draw_extra_rows()
                        return do_delete
                    ctk.CTkButton(row, text="❌", width=get_scaled_size(30), height=get_scaled_size(45),
                        fg_color="transparent", text_color="#EF4444",
                        command=make_delete()
                    ).pack(side="left", padx=get_scaled_size(5))
            draw_extra_rows()

            adder_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
            adder_frame.pack(fill="x", padx=get_scaled_size(15), pady=get_scaled_size(5))
            new_key_ent = ctk.CTkEntry(adder_frame, placeholder_text="Όνομα νέου πεδίου...", font=("Arial", 18))
            new_key_ent.pack(side="left", fill="x", expand=True, padx=5)

            def add_custom_field():
                k_name = new_key_ent.get().strip()
                if k_name and k_name not in extra_data:
                    extra_data[k_name] = ""
                new_key_ent.delete(0, 'end')
                draw_extra_rows()

            ctk.CTkButton(adder_frame, text="➕ Προσθήκη Πεδίου",
                font=ctk.CTkFont(size=18, weight="bold"), height=get_scaled_size(45), command=add_custom_field).pack(side="left", padx=get_scaled_size(10), pady=get_scaled_size(10))

            # 5. SAVE HANDLER
            def save_eav_changes():
                            payload = {k: ent.get().strip() for k, ent in core_entries.items()}
                            payload['code'] = client_code
                            payload['notes'] = notes_text.get("1.0", "end").strip()
                            updated_extras = {k: ent.get().strip()
                                for k, ent in dynamic_entries.items()
                                if k in extra_data}
                            payload['extra_fields_json'] = updated_extras
                            if update_client_record(payload):
                                modal.grab_release()
                                modal.destroy()
                                self.execute_registry_query(None)
                                if hasattr(self, '_active_profile_client'):
                                    fresh = get_client_by_code(client_code)
                                    if fresh:
                                        from logic_engine import get_client_balance
                                        fresh['balance_owed'] = get_client_balance(client_code)
                                        self._active_profile_client = fresh
                                        self.open_profile_timeline(fresh)
            font_size = getattr(self, 'current_font_size', 18)
            btn_save = ctk.CTkButton(
                modal,
                text="💾 Αποθήκευση Αλλαγών",
                font=ctk.CTkFont(size=font_size, weight="bold"),
                fg_color="#10B981",
                hover_color="#059669",
                height=get_scaled_size(45),
                command=save_eav_changes
            )
            btn_save.pack(fill="x", padx=get_scaled_size(25), pady=(get_scaled_size(15), get_scaled_size(20)), side="bottom")
            if hasattr(self, 'dynamic_ui_scaler'):
                self.dynamic_ui_scaler(modal)
        except Exception as e:
            print(f"EAV Modal Error: {e}")

    def open_job_edit_modal(self, job_id):
        from logic_engine import get_job_by_id, clean_numeric_input_string, get_config_list
        import sqlite3

        # 1. Safe dict query
        record = get_job_by_id(job_id)
        if not record:
            return

        edit_win = ctk.CTkToplevel(self)
        edit_win.title("Επεξεργασία Εργασίας")
        base_f = self.ui_cfg.settings.get('font_size', 18)
        header_font = ctk.CTkFont(size=base_f, weight="bold")
        input_font = ctk.CTkFont(size=base_f)
        edit_win.geometry(f"{get_scaled_size(560)}x{get_scaled_size(750)}")
        edit_win.transient(self)
        edit_win.grab_set()

        scroll = ctk.CTkScrollableFrame(edit_win)
        scroll.pack(fill="both", expand=True, padx=15, pady=15)

        # Selected Client
        ctk.CTkLabel(scroll, text=f"Πελάτης: {record.get('client_name') or 'Άγνωστος Πελάτης'}", font=ctk.CTkFont(size=20, weight="bold"), anchor="w").pack(fill="x", pady=(10, 2), padx=10)

        # Main Category
        ctk.CTkLabel(scroll, text="Κατηγορία Εργασίας:", font=ctk.CTkFont(size=18, weight="bold"), anchor="w").pack(fill="x", pady=(10, 2), padx=10)
        cats = get_config_list("job_categories") or ["ΑΠΕΝΤΟΜΩΣΗ"]
        cat1_var = ctk.StringVar(value=record.get("category_1") or "")
        cat1_combo = ctk.CTkOptionMenu(scroll, values=cats, variable=cat1_var, font=("Arial", 18), height=get_scaled_size(42))
        cat1_combo.pack(fill="x", pady=2, padx=10)

        # Subcategory
        ctk.CTkLabel(scroll, text="Υποκατηγορία:", font=ctk.CTkFont(size=18, weight="bold"), anchor="w").pack(fill="x", pady=(10, 2), padx=10)
        subcats = get_config_list("job_subcategories") or ["ΚΑΤΣΑΡΙΔΕΣ", "ΠΟΝΤΙΚΙΑ", "ΜΙΚΡΟΒΙΑ"]
        cat2_var = ctk.StringVar(value=record.get("category_2") or "")
        cat2_combo = ctk.CTkOptionMenu(scroll, values=subcats, variable=cat2_var, font=("Arial", 18), height=get_scaled_size(42))
        cat2_combo.pack(fill="x", pady=2, padx=10)

        # Logging Date
        ctk.CTkLabel(scroll, text="Ημερομηνία (DD-MM-YY):", font=ctk.CTkFont(size=18, weight="bold"), anchor="w").pack(fill="x", pady=(10, 2), padx=10)
        date_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        date_frame.pack(fill="x", pady=2, padx=10)
        date_frame.grid_columnconfigure(0, weight=1)
        
        date_entry = ctk.CTkEntry(date_frame, font=("Arial", 18), height=get_scaled_size(42))
        # Convert YYYY-MM-DD from DB to DD-MM-YY for display
        _raw_date = str(record.get("date") or "")
        _display_date = _raw_date
        if _raw_date and "-" in _raw_date and len(_raw_date) >= 10 and _raw_date.index("-") == 4:
            try:
                from datetime import datetime as _dt
                _display_date = _dt.strptime(_raw_date, "%Y-%m-%d").strftime("%d-%m-%y")
            except ValueError:
                pass
        date_entry.insert(0, _display_date)
        date_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        date_btn = ctk.CTkButton(date_frame, text="📅", width=40, height=get_scaled_size(42), command=lambda: CTkDatePicker(edit_win, date_entry))
        date_btn.grid(row=0, column=1)

        # Safe Hour/Minute extraction
        time_slot = record.get("time_slot") or ""
        time_slot = time_slot.strip()
        current_hour = "12"
        current_minute = "00"
        if time_slot and ":" in time_slot:
            parts = time_slot.split(":")
            if len(parts) == 2:
                current_hour = parts[0].strip().zfill(2)
                current_minute = parts[1].strip().zfill(2)

        # Time Selector Dropdown Pair
        ctk.CTkLabel(scroll, text="Ώρα (HH:MM):", font=ctk.CTkFont(size=18, weight="bold"), anchor="w").pack(fill="x", pady=(10, 2), padx=10)
        time_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        time_frame.pack(fill="x", pady=2, padx=10)
        
        hour_combo = ctk.CTkComboBox(time_frame, values=[f"{i:02d}" for i in range(24)], width=100, font=("Arial", 18), height=get_scaled_size(42))
        hour_combo.set(current_hour)
        hour_combo.pack(side="left", padx=(0, 5))
        
        ctk.CTkLabel(time_frame, text=":", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=(0, 5))
        
        minute_combo = ctk.CTkComboBox(time_frame, values=["00", "15", "30", "45"], width=100, font=("Arial", 18), height=get_scaled_size(42))
        minute_combo.set(current_minute)
        minute_combo.pack(side="left")

        # Assigned Crew (Multi-Select with Chips)
        ctk.CTkLabel(scroll, text="Συνεργείο (Πολλαπλή Επιλογή):", font=ctk.CTkFont(size=18, weight="bold"), anchor="w").pack(fill="x", pady=(10, 2), padx=10)
        edit_crew_combo, edit_crew_tags, edit_crew_list, edit_crew_get, edit_crew_populate = self.create_crew_multiselect(scroll)
        edit_crew_populate(record.get("crew") or "")

        # Invoice Reference Number
        ctk.CTkLabel(scroll, text="Αριθμός Τιμολογίου:", font=ctk.CTkFont(size=18, weight="bold"), anchor="w").pack(fill="x", pady=(10, 2), padx=10)
        invoice_entry = ctk.CTkEntry(scroll, font=("Arial", 18), height=get_scaled_size(42))
        invoice_entry.insert(0, record.get("invoice_number") or "")
        invoice_entry.pack(fill="x", pady=2, padx=10)

        # Notes field
        ctk.CTkLabel(scroll, text="Σημειώσεις Εργασίας:", font=ctk.CTkFont(size=18, weight="bold"), anchor="w").pack(fill="x", pady=(10, 2), padx=10)
        notes_text = ctk.CTkTextbox(scroll, height=get_scaled_size(100), font=("Arial", 18))
        notes_text.insert("1.0", record.get("notes") or "")
        notes_text.pack(fill="x", pady=2, padx=10)

        # Pricing block
        ctk.CTkLabel(scroll, text="Οικονομικά:", font=ctk.CTkFont(size=18, weight="bold"), anchor="w").pack(fill="x", pady=(15, 2), padx=10)
        vat_calc = VerticalVatCalculatorBlock(scroll, vat_rate=0.24)
        vat_calc.pack(fill="x", pady=5, padx=10)
        
        # Populate pricing block values safely
        p_before_init = record.get('price_before_vat') or 0.0
        p_after_init = record.get('price_after_vat') or 0.0
        
        vat_calc.entry_before.delete(0, "end")
        vat_calc.entry_before.insert(0, f"{p_before_init:.2f}")
        vat_calc.entry_after.delete(0, "end")
        vat_calc.entry_after.insert(0, f"{p_after_init:.2f}")
        
        # Set trigger calculation logic
        if hasattr(vat_calc, '_on_change'):
            vat_calc._on_change("after")

        # Special Flag Checkbox
        special_chk = ctk.CTkCheckBox(scroll, text="Special", font=ctk.CTkFont(size=18, weight="bold"))
        if record.get('is_special') == 1:
            special_chk.select()
        special_chk.pack(anchor="w", pady=(10, 2), padx=10)

        # Execution layer save handler
        def save_changes():
            import re as _re
            from datetime import datetime as _dt
            cat1 = cat1_combo.get().strip()
            cat2 = cat2_combo.get().strip()
            raw_dt = date_entry.get().strip()
            # Convert DD-MM-YY or DD-MM-YYYY back to YYYY-MM-DD for storage
            if _re.match(r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$", raw_dt):
                clean_dt = raw_dt.replace("/", "-")
                try:
                    fmt = "%d-%m-%y" if len(clean_dt.split("-")[-1]) == 2 else "%d-%m-%Y"
                    dt = _dt.strptime(clean_dt, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    dt = raw_dt
            elif _re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$", raw_dt):
                dt = raw_dt.replace("/", "-")
            else:
                dt = raw_dt
            tm = f"{hour_combo.get().strip()}:{minute_combo.get().strip()}"
            cr = edit_crew_get()
            inv = invoice_entry.get().strip()
            nt = notes_text.get("1.0", "end-1c").strip()
            is_sp = 1 if special_chk.get() else 0
            
            try:
                p_after = float(clean_numeric_input_string(vat_calc.entry_after.get()))
            except ValueError:
                p_after = 0.0

            from logic_engine import update_job_record
            payload = {
                'job_id': job_id,
                'category_1': cat1,
                'category_2': cat2,
                'date': dt,
                'time_slot': tm,
                'crew': cr,
                'invoice_number': inv,
                'price_after_vat': str(p_after),
                'notes': nt,
                'is_special': is_sp
            }
            update_job_record(payload)

            if hasattr(self, 'execute_calendar_query_action'):
                self.execute_calendar_query_action(None)
            elif hasattr(self, 'execute_jobs_query'):
                self.execute_jobs_query()
            # Refresh client detail view or crew detail view if active
            if hasattr(self, '_detail_view_client_code') and "client_detail" in self.frames:
                self.after(100, lambda: self.open_client_detail_view(self._detail_view_client_code))
            if hasattr(self, '_detail_view_crew_name') and "crew_detail" in self.frames:
                self.after(100, lambda: self.open_crew_detail_view(self._detail_view_crew_name))
                
            edit_win.destroy()

        save_btn = ctk.CTkButton(scroll, text="💾 Αποθήκευση Αλλαγών", command=save_changes, font=ctk.CTkFont(size=14, weight="bold"), height=get_scaled_size(45), fg_color="#10B981")
        save_btn.pack(fill="x", pady=(15, 20), padx=10)


    def open_payment_edit_modal(self, payment_id):
        """Opens a modal window to edit an existing payment with live date normalization."""
        try:
            from logic_engine import get_payment_by_id, update_payment_record, get_config_list
            import json
            from datetime import datetime
            
            record = get_payment_by_id(payment_id)
            if not record:
                return
                
            modal = ctk.CTkToplevel(self)
            modal.title("Επεξεργασία Πληρωμής")
            modal.geometry("550x700")
            modal.transient(self)
            modal.grab_set()
            
            scroll = ctk.CTkScrollableFrame(modal)
            scroll.pack(fill="both", expand=True, padx=get_scaled_size(10), pady=get_scaled_size(10))
            
            ctk.CTkLabel(scroll, text=f"Πελάτης: {record.get('client_name', '') or record.get('client_name_full', '')}",
                font=ctk.CTkFont(size=18, weight="bold"), anchor="w").pack(anchor="w", padx=get_scaled_size(15), pady=(get_scaled_size(10), get_scaled_size(5)))
            
            ctk.CTkLabel(scroll, text=f"ID: {record.get('payment_id', '')}", font=ctk.CTkFont(size=18), anchor="w").pack(anchor="w", padx=get_scaled_size(15), pady=(0, get_scaled_size(8)))
            
            ctk.CTkLabel(scroll, text="Ποσό Πληρωμής (€)", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=get_scaled_size(15), pady=(get_scaled_size(8), 0))
            amount_e = ctk.CTkEntry(scroll, font=ctk.CTkFont(size=18), height=get_scaled_size(45))
            amount_e.insert(0, str(record.get('amount', '0.00') or '0.00'))
            amount_e.pack(fill="x", padx=get_scaled_size(15), pady=(0, get_scaled_size(5)))
            
            ctk.CTkLabel(scroll, text="Ημερομηνία", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=get_scaled_size(15), pady=(get_scaled_size(8), 0))
            date_e = ctk.CTkEntry(scroll, font=ctk.CTkFont(size=18), height=get_scaled_size(45), placeholder_text="DD-MM-YYYY")
            
            # --- LIVE EUROPEAN DATE CONVERSION FOR DISPLAY ---
            orig_date = str(record.get('date', '') or '')
            display_date = orig_date
            if orig_date and "-" in orig_date and orig_date.index("-") == 4:
                try:
                    display_date = datetime.strptime(orig_date, "%Y-%m-%d").strftime("%d-%m-%Y")
                except ValueError:
                    pass
            date_e.insert(0, display_date)
            date_e.pack(fill="x", padx=get_scaled_size(15), pady=(0, get_scaled_size(5)))
            
            pay_methods = get_config_list('payment_methods') or ["ΜΕΤΡΗΤΑ (Cash)"]
            ctk.CTkLabel(scroll, text="Τρόπος Πληρωμής", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=get_scaled_size(15), pady=(get_scaled_size(8), 0))
            pay_combo = ctk.CTkComboBox(scroll, values=pay_methods, font=ctk.CTkFont(size=18), dropdown_font=ctk.CTkFont(size=18), height=get_scaled_size(45))
            pay_combo.set(str(record.get('method', '') or ''))
            pay_combo.pack(fill="x", padx=get_scaled_size(15), pady=(0, get_scaled_size(5)))
            
            cats = get_config_list('job_categories') or ["ΑΠΕΝΤΟΜΩΣΗ"]
            subcats = get_config_list('job_subcategories') or ["ΚΑΤΣΑΡΙΔΕΣ", "ΠΟΝΤΙΚΙΑ", "ΜΙΚΡΟΒΙΑ"]
            ctk.CTkLabel(scroll, text="Κατηγορία Εργασίας", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=get_scaled_size(15), pady=(get_scaled_size(8), 0))
            cat_combo = ctk.CTkComboBox(scroll, values=cats, font=ctk.CTkFont(size=18), dropdown_font=ctk.CTkFont(size=18), height=get_scaled_size(45))
            cat_combo.set(str(record.get('job_category', '') or ''))
            cat_combo.pack(fill="x", padx=get_scaled_size(15), pady=(0, get_scaled_size(5)))
            
            ctk.CTkLabel(scroll, text="Υποκατηγορία", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=get_scaled_size(15), pady=(get_scaled_size(8), 0))
            sub_combo = ctk.CTkComboBox(scroll, values=subcats,
                font=ctk.CTkFont(size=18), dropdown_font=ctk.CTkFont(size=18), height=get_scaled_size(45))
            sub_combo.set(str(record.get('subcategory', '') or ''))
            sub_combo.pack(fill="x", padx=get_scaled_size(15), pady=(0, get_scaled_size(15)))
            
            ctk.CTkLabel(scroll, text="Σημειώσεις", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=get_scaled_size(15), pady=(get_scaled_size(8), 0))
            notes_txt = ctk.CTkTextbox(scroll, height=get_scaled_size(100), font=ctk.CTkFont(size=18))
            notes_txt.insert("1.0", str(record.get('notes', '') or ''))
            notes_txt.pack(fill="x", padx=get_scaled_size(15), pady=(0, get_scaled_size(8)))
            
            special_pay_chk = ctk.CTkCheckBox(scroll, text="Special", font=ctk.CTkFont(size=18, weight="bold"))
            if record.get('is_special') == 1:
                special_pay_chk.select()
            special_pay_chk.pack(anchor="w", padx=get_scaled_size(15), pady=(get_scaled_size(8), get_scaled_size(8)))

            def save_changes():
                raw_date = date_e.get().strip()
                import re
                
                if re.match(r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$", raw_date):
                    clean_str = raw_date.replace("/", "-")
                    try:
                        fmt = "%d-%m-%y" if len(clean_str.split("-")[-1]) == 2 else "%d-%m-%Y"
                        date_str = datetime.strptime(clean_str, fmt).strftime("%Y-%m-%d")
                    except ValueError:
                        date_str = raw_date
                elif re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$", raw_date):
                    date_str = raw_date.replace("/", "-")
                else:
                    date_str = raw_date

                payload = {
                    'payment_id': record.get('payment_id'), 
                    'amount': amount_e.get().strip(),
                    'method': pay_combo.get().strip(), 
                    'date': date_str,
                    'notes': notes_txt.get("1.0", "end").strip(),
                    'job_category': cat_combo.get().strip(), 
                    'subcategory': sub_combo.get().strip(),
                    'is_special': 1 if special_pay_chk.get() else 0
                }
                payload['extra_fields_json'] = {}
                
                if update_payment_record(payload):
                    modal.grab_release()
                    modal.destroy()
                    self.populate_payments_list()
                    self.execute_registry_query(None)
                    if hasattr(self, '_active_profile_client'):
                        self.refresh_profile_timeline()
                    # Refresh client detail view if it's active
                    if hasattr(self, '_detail_view_client_code') and "client_detail" in self.frames:
                        self.after(100, lambda: self.open_client_detail_view(self._detail_view_client_code))
                        
            ctk.CTkButton(modal, text="💾 Αποθήκευση Αλλαγών",
                font=ctk.CTkFont(size=18, weight="bold"), fg_color="#10B981", height=get_scaled_size(45), command=save_changes).pack(fill="x", padx=get_scaled_size(25), pady=get_scaled_size(15))
            self.dynamic_ui_scaler(modal)
        except Exception as e:
            print(f"Payment Edit Error: {e}")


    def open_profile_timeline(self, client_dict):
        """
        Safely unwraps customer details and renders profiles without crashing
        on missing database schema properties or alternate translation keys.
        """
        if not client_dict or not isinstance(client_dict, dict):
            print("DEBUG: Execution bypassed due to empty or corrupted client data packet.")
            return

        code = str(client_dict.get("code") or client_dict.get("client_code") or "1000")
        name = str(client_dict.get("name") or client_dict.get("client_name") or "Άγνωστος Πελάτης")
        phone = str(client_dict.get("telephone") or client_dict.get("phone") or "---")
        phone_2 = str(client_dict.get("telephone_2") or client_dict.get("phone_2") or "---")
        vat = str(client_dict.get("vat") or client_dict.get("αφμ") or client_dict.get("ΑΦΜ") or "---")
        address = str(client_dict.get("address") or client_dict.get("διεύθυνση") or "---")
        notes = str(client_dict.get("notes") or client_dict.get("σημειώσεις") or "")
        area = str(client_dict.get("area") or "---")
        profession = str(client_dict.get("profession") or "---")

        self.active_client_code = code
        self.profile_panel.grid_forget()
        for widget in self.profile_panel.winfo_children():
            widget.destroy()
        self.profile_panel.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)
        scroll_profile = ctk.CTkScrollableFrame(self.profile_panel, fg_color="transparent",
            label_text="Καρτέλα Πελάτη", label_font=ctk.CTkFont(size=18, weight="bold"))
        scroll_profile.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Header row: client name (left) + 🔍 detail button (right)
        header_row = ctk.CTkFrame(scroll_profile, fg_color="transparent")
        header_row.pack(fill="x", padx=10, pady=5)
        header_row.grid_columnconfigure(0, weight=1)
        title = ctk.CTkLabel(header_row, text=name, font=ctk.CTkFont(size=22, weight="bold"), anchor="w", justify="left")
        title.grid(row=0, column=0, sticky="w")
        detail_btn = ctk.CTkButton(header_row, text="🔍", width=40, height=35,
            font=ctk.CTkFont(size=18), fg_color=("#3B8ED0", "#1F6AA5"), hover_color=("#2D7BB8", "#185A8C"),
            command=lambda c=code: self.open_client_detail_view(c))
        detail_btn.grid(row=0, column=1, sticky="e", padx=(5, 0))
        
        # ── Core Profile Fields (matching CLIENT_FIELDS_SCHEMA) ──
        profile_frame = ctk.CTkFrame(scroll_profile, fg_color="transparent")
        profile_frame.pack(fill="x", padx=10, pady=5)

        field_display = [
            ("Κωδικός Πελάτη", code),
            ("Όνομα", name),
            ("Τηλέφωνο", phone),
            ("Κινητό (Τηλ 2)", phone_2 if phone_2 != "---" else ""),
            ("Διεύθυνση", address if address != "---" else ""),
            ("Διεύθυνση 2", client_dict.get('address_2', '')),
            ("Περιοχή", area if area != "---" else ""),
            ("ΑΦΜ", vat if vat != "---" else ""),
            ("Επάγγελμα", profession if profession != "---" else ""),
        ]
        for label, val in field_display:
            if not val:
                continue
            row = ctk.CTkFrame(profile_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=f"{label}:", font=ctk.CTkFont(size=18, weight="bold"),
                width=140, anchor="w").pack(side="left", padx=(0, 5))
            ctk.CTkLabel(row, text=str(val), font=ctk.CTkFont(size=18),
                anchor="w").pack(side="left", fill="x", expand=True)

        # ── Extra Fields (EAV — filtered) ──
        raw_extras = client_dict.get('extra_fields', {})
        if isinstance(raw_extras, str):
            try:
                raw_extras = json.loads(raw_extras)
            except (json.JSONDecodeError, TypeError):
                raw_extras = {}
        legacy_balance_keys = {'YPOLOIPO', 'LASTAPDT', 'LASTAPOL', 'LASTPAYM', 'LASTPADT',
                              'PAYDAYS', 'REMIND', 'SMPERC', 'ETPERC', 'ETPROEL',
                              'FREAT', 'FLATS', 'SMAN', 'CODE', 'DOY', 'WTAXKOD', 'HTAXKOD'}
        if raw_extras and isinstance(raw_extras, dict):
            eav_frame = ctk.CTkFrame(profile_frame, fg_color="transparent")
            eav_frame.pack(fill="x", pady=4)
            for k, v in raw_extras.items():
                # Skip empty, zero, and legacy balance fields
                if k in legacy_balance_keys:
                    continue
                sv = str(v).strip()
                if not sv or sv == "0" or sv == "0.00" or sv == "0.0":
                    continue
                row = ctk.CTkFrame(eav_frame, fg_color=("#E8E8E8", "#2A2A2A"), corner_radius=3)
                row.pack(fill="x", pady=1)
                ctk.CTkLabel(row, text=f"{k}:", font=ctk.CTkFont(size=16, weight="bold"),
                    width=140, anchor="w").pack(side="left", padx=(3, 5))
                ctk.CTkLabel(row, text=sv, font=ctk.CTkFont(size=16),
                    anchor="w").pack(side="left", fill="x", expand=True)

        # ── Balance ──
        bal = client_dict.get('balance_owed', 0)
        color = "#6BCB77"
        if bal > 0:
            color = "#FF6B6B"
        elif bal < 0:
            color = "#3B8ED0"
        lbl_bal = ctk.CTkLabel(scroll_profile, text=f"Τρέχον Υπόλοιπο Οφειλής: €{bal:.2f}",
            font=ctk.CTkFont(size=22, weight="bold"), text_color=color, anchor="w")
        lbl_bal.pack(fill="x", padx=10, pady=10)
        self._active_profile_client = client_dict
        # Unified history header
        job_hist_lbl = ctk.CTkLabel(scroll_profile, text="■ Ιστορικό Εργασιών (Κλικ για Φιλτράρισμα 🔍)",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w", text_color="#3B8ED0", cursor="hand2")
        job_hist_lbl.pack(fill="x", padx=10, pady=(15, 5))
        job_hist_lbl.bind("<Button-1>", lambda e, cc=client_dict['code']: self.jump_to_client_calendar(cc))

        from logic_engine import fetch_client_history
        history = fetch_client_history(client_dict['code'])
        client_jobs = [item for item in history if item['type'] == 'job']

        if not client_jobs:
            ctk.CTkLabel(scroll_profile, text="Δεν βρέθηκαν καταχωρημένες εργασίες.", font=ctk.CTkFont(size=18, slant="italic"), text_color="gray", anchor="w").pack(fill="x", padx=20, pady=2)
        else:
            for j in client_jobs:
                row_frame = ctk.CTkFrame(scroll_profile, fg_color=("#D9D9D9", "#1F1F1F"), corner_radius=4)
                row_frame.pack(fill="x", padx=10, pady=3)
                row_frame.grid_columnconfigure(0, weight=1)
                
                cat1 = j.get('category_1', j.get('cat1', ''))
                cat2 = j.get('category_2', j.get('cat2', ''))
                price = j.get('price_after_vat', j.get('price', 0))
                date_str = format_date_display(j.get('date', ''))
                crew = j.get('crew', '-')
                invoice = j.get('invoice_number', j.get('invoice', '')) or '-'
                notes = j.get('notes', '') or '-'
                
                j_txt = f"🔧 {cat1} - {cat2} ({crew})\n€{float(price):.2f}  |  {date_str}  |  Τιμ: {invoice}  |  Σημ: {notes}"
                j_lbl = ctk.CTkLabel(row_frame, text=j_txt, justify="left", anchor="w", font=ctk.CTkFont(size=18))
                j_lbl.grid(row=0, column=0, sticky="ew", padx=8, pady=4)
                
                item_id = j.get('job_id', j.get('id'))
                ctk.CTkButton(row_frame, text="✏️", width=30, command=lambda iid=item_id: self.open_job_edit_modal(iid)).grid(row=0, column=1, sticky="ns", padx=2)
                ctk.CTkButton(row_frame, text="🗑️", width=30, fg_color="#C0392B", hover_color="#E74C3C",
                    command=lambda iid=item_id: ConfirmationDialog(self, f"Διαγραφή job ID {iid}?", lambda jid=iid: self.eav_delete_job(jid))).grid(row=0, column=2, sticky="ns", padx=2)

        # --- SECTION 2: PAYMENT HISTORY BLOCK (CLICKABLE GREEN) ---
        pay_hist_lbl = ctk.CTkLabel(scroll_profile, text="■ Ιστορικό Πληρωμών (Κλικ για Ledger Ταμείου 🔍)",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w", text_color="#10B981", cursor="hand2")
        pay_hist_lbl.pack(fill="x", padx=10, pady=(20, 5))
        pay_hist_lbl.bind("<Button-1>", lambda e, cc=client_dict['code']: self.jump_to_client_ledger(cc))

        client_payments = [item for item in history if item['type'] == 'payment']

        if not client_payments:
            ctk.CTkLabel(scroll_profile, text="Δεν βρέθηκαν καταχωρημένες πληρωμές.", font=ctk.CTkFont(size=18, slant="italic"), text_color="gray", anchor="w").pack(fill="x", padx=20, pady=2)
        else:
            for p in client_payments:
                row_frame = ctk.CTkFrame(scroll_profile, fg_color=("#D0E8D0", "#1A3A1A"), corner_radius=4)
                row_frame.pack(fill="x", padx=10, pady=3)
                row_frame.grid_columnconfigure(0, weight=1)
                
                method = p.get('method', p.get('payment_method', ''))
                amount = p.get('amount', 0)
                date_str = format_date_display(p.get('date', ''))
                notes = p.get('notes', '') or '-'
                
                p_txt = f"💰 {method}\n€{float(amount):.2f}  |  {date_str}  |  Σημ: {notes}"
                p_lbl = ctk.CTkLabel(row_frame, text=p_txt, justify="left", anchor="w", font=ctk.CTkFont(size=18))
                p_lbl.grid(row=0, column=0, sticky="ew", padx=8, pady=4)
                
                pid = p.get('payment_id', p.get('id'))
                ctk.CTkButton(row_frame, text="✏️", width=30, command=lambda iid=pid: self.open_payment_edit_modal(iid)).grid(row=0, column=1, sticky="ns", padx=2)
                ctk.CTkButton(row_frame, text="🗑️", width=30, fg_color="#C0392B", hover_color="#E74C3C",
                    command=lambda iid=pid: ConfirmationDialog(self, f"Διαγραφή πληρωμής ID {iid}?", lambda pid2=iid: self.eav_delete_payment(pid2))).grid(row=0, column=2, sticky="ns", padx=2)

        self.dynamic_ui_scaler(scroll_profile)

    def refresh_profile_timeline(self):
        if hasattr(self, '_active_profile_client') and self._active_profile_client:
            self.open_profile_timeline(self._active_profile_client)

    def open_client_detail_view(self, client_code):
        """Opens a full-screen detail view showing ALL jobs and payments for a client,
        merged and sorted by date (newest first), with edit/delete on each item.
        Replaces the main desk_container content; sidebar stays visible."""
        from logic_engine import get_client_by_code, fetch_client_history, get_client_balance

        client = get_client_by_code(client_code)
        if not client:
            return

        client_name = client.get('name', 'Άγνωστος Πελάτης')
        balance = get_client_balance(client_code)

        # Create or recycle the detail frame
        if "client_detail" in self.frames:
            detail_frame = self.frames["client_detail"]
            for w in detail_frame.winfo_children():
                w.destroy()
        else:
            detail_frame = ctk.CTkFrame(self.desk_container, fg_color="transparent")
            self.frames["client_detail"] = detail_frame

        detail_frame.grid_columnconfigure(0, weight=1)
        detail_frame.grid_rowconfigure(1, weight=1)

        # --- HEADER BAR ---
        header = ctk.CTkFrame(detail_frame, fg_color=("#E0E0E0", "#222222"), corner_radius=8)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header.grid_columnconfigure(1, weight=1)

        back_btn = ctk.CTkButton(header, text="← Πίσω", width=100, height=38,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=("#CCCCCC", "#3A3A3A"), text_color=("#1A1A1A", "#E0E0E0"),
            hover_color=("#BBBBBB", "#4A4A4A"),
            command=lambda: self.switch_frame("registry"))
        back_btn.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        bal_color = "#6BCB77" if balance <= 0 else "#FF6B6B"
        title_txt = f"📋  {client_name}  [{client_code}]   —   Υπόλοιπο: €{balance:.2f}"
        title_lbl = ctk.CTkLabel(header, text=title_txt,
            font=ctk.CTkFont(size=20, weight="bold"), anchor="w", text_color=bal_color)
        title_lbl.grid(row=0, column=1, sticky="w", padx=10, pady=10)

        edit_client_btn = ctk.CTkButton(header, text="✏️ Πελάτη", width=100, height=38,
            font=ctk.CTkFont(size=14), fg_color="#3B8ED0",
            command=lambda cc=client_code: self.open_client_edit_modal(cc))
        edit_client_btn.grid(row=0, column=2, padx=(5, 10), pady=10, sticky="e")

        # --- SCROLLABLE HISTORY LIST ---
        history_scroll = ctk.CTkScrollableFrame(detail_frame, fg_color="transparent",
            label_text=f"Ιστορικό Εργασιών & Πληρωμών — {client_name}",
            label_font=ctk.CTkFont(size=18, weight="bold"))
        history_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        history_scroll.grid_columnconfigure(0, weight=1)

        # Store for refresh
        self._detail_view_client_code = client_code

        history = fetch_client_history(client_code)

        if not history:
            ctk.CTkLabel(history_scroll, text="Δεν βρέθηκαν καταχωρημένες εργασίες ή πληρωμές.",
                font=ctk.CTkFont(size=18, slant="italic"), text_color="gray", anchor="w").pack(fill="x", padx=20, pady=20)
        else:
            current_date_group = None
            for item in history:
                item_date = item.get('date', '')
                display_date = format_date_display(item_date)

                # Date group divider
                if item_date != current_date_group:
                    current_date_group = item_date
                    divider = ctk.CTkFrame(history_scroll, fg_color=("#C0C0C0", "#3A3A3A"), height=2)
                    divider.pack(fill="x", padx=10, pady=(12, 2))
                    ctk.CTkLabel(history_scroll, text=f"📅 {display_date}",
                        font=ctk.CTkFont(size=16, weight="bold"), anchor="w",
                        text_color=("#555555", "#AAAAAA")).pack(fill="x", padx=15, pady=(2, 5))

                row_frame = ctk.CTkFrame(history_scroll, corner_radius=6)
                row_frame.pack(fill="x", padx=10, pady=3)
                row_frame.grid_columnconfigure(0, weight=1)

                if item['type'] == 'job':
                    row_frame.configure(fg_color=("#D9D9D9", "#1F1F1F"))
                    cat1 = item.get('category_1', item.get('cat1', ''))
                    cat2 = item.get('category_2', item.get('cat2', ''))
                    price = item.get('price_after_vat', item.get('price', 0))
                    crew = item.get('crew', '-')
                    invoice = item.get('invoice_number', item.get('invoice', '')) or '-'
                    notes = item.get('notes', '') or ''
                    notes_short = (notes[:40] + '...') if len(notes) > 40 else notes
                    txt = f"🔧 {cat1} - {cat2}  |  Συνεργείο: {crew}  |  €{float(price):.2f}  |  Τιμ: {invoice}"
                    if notes_short:
                        txt += f"  |  {notes_short}"
                    lbl = ctk.CTkLabel(row_frame, text=txt, justify="left", anchor="w",
                        font=ctk.CTkFont(size=16), wraplength=900)
                    lbl.grid(row=0, column=0, sticky="ew", padx=10, pady=6)
                    item_id = item.get('job_id', item.get('id'))
                    ctk.CTkButton(row_frame, text="✏️", width=35, height=30,
                        command=lambda iid=item_id: self._detail_edit_job(iid)).grid(row=0, column=1, padx=2, pady=4)
                    ctk.CTkButton(row_frame, text="🗑️", width=35, height=30,
                        fg_color="#C0392B", hover_color="#E74C3C",
                        command=lambda iid=item_id: ConfirmationDialog(self,
                            f"Διαγραφή εργασίας ID {iid}?",
                            lambda jid=iid: self._detail_delete_job(jid))).grid(row=0, column=2, padx=2, pady=4)
                else:
                    row_frame.configure(fg_color=("#D0E8D0", "#1A3A1A"))
                    method = item.get('method', item.get('payment_method', ''))
                    amount = item.get('amount', 0)
                    notes = item.get('notes', '') or ''
                    notes_short = (notes[:40] + '...') if len(notes) > 40 else notes
                    txt = f"💰 {method}  |  €{float(amount):.2f}"
                    if notes_short:
                        txt += f"  |  {notes_short}"
                    lbl = ctk.CTkLabel(row_frame, text=txt, justify="left", anchor="w",
                        font=ctk.CTkFont(size=16), wraplength=900)
                    lbl.grid(row=0, column=0, sticky="ew", padx=10, pady=6)
                    pid = item.get('payment_id', item.get('id'))
                    ctk.CTkButton(row_frame, text="✏️", width=35, height=30,
                        command=lambda iid=pid: self._detail_edit_payment(iid)).grid(row=0, column=1, padx=2, pady=4)
                    ctk.CTkButton(row_frame, text="🗑️", width=35, height=30,
                        fg_color="#C0392B", hover_color="#E74C3C",
                        command=lambda iid=pid: ConfirmationDialog(self,
                            f"Διαγραφή πληρωμής ID {iid}?",
                            lambda pid2=iid: self._detail_delete_payment(pid2))).grid(row=0, column=2, padx=2, pady=4)

        self.dynamic_ui_scaler(history_scroll)
        self.switch_frame("client_detail")

    def _detail_edit_job(self, job_id):
        """Edit a job from the detail view, then refresh it."""
        self.open_job_edit_modal(job_id)

    def _detail_edit_payment(self, payment_id):
        """Edit a payment from the detail view, then refresh it."""
        self.open_payment_edit_modal(payment_id)

    def _detail_delete_job(self, job_id):
        """Delete a job and refresh the detail view."""
        self.eav_delete_job(job_id)
        if hasattr(self, '_detail_view_client_code'):
            self.open_client_detail_view(self._detail_view_client_code)

    def _detail_delete_payment(self, payment_id):
        """Delete a payment and refresh the detail view."""
        self.eav_delete_payment(payment_id)
        if hasattr(self, '_detail_view_client_code'):
            self.open_client_detail_view(self._detail_view_client_code)

    def open_crew_detail_view(self, crew_name):
        """Opens a full-screen detail view showing ALL jobs performed by a given crew/technician,
        sorted by date (newest first), with edit/delete and client navigation links."""
        from logic_engine import fetch_crew_jobs

        # Create or recycle the crew detail frame
        if "crew_detail" in self.frames:
            detail_frame = self.frames["crew_detail"]
            for w in detail_frame.winfo_children():
                w.destroy()
        else:
            detail_frame = ctk.CTkFrame(self.desk_container, fg_color="transparent")
            self.frames["crew_detail"] = detail_frame

        detail_frame.grid_columnconfigure(0, weight=1)
        detail_frame.grid_rowconfigure(1, weight=1)

        # --- HEADER BAR ---
        header = ctk.CTkFrame(detail_frame, fg_color=("#E0E0E0", "#222222"), corner_radius=8)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header.grid_columnconfigure(1, weight=1)

        back_btn = ctk.CTkButton(header, text="← Πίσω", width=100, height=38,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=("#CCCCCC", "#3A3A3A"), text_color=("#1A1A1A", "#E0E0E0"),
            hover_color=("#BBBBBB", "#4A4A4A"),
            command=lambda: self.switch_frame("analytics"))
        back_btn.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        title_txt = f"👷  Εργασίες Συνεργείου / Τεχνικού: {crew_name}"
        title_lbl = ctk.CTkLabel(header, text=title_txt,
            font=ctk.CTkFont(size=20, weight="bold"), anchor="w", text_color="#3B8ED0")
        title_lbl.grid(row=0, column=1, sticky="w", padx=10, pady=10)

        # --- SCROLLABLE JOBS LIST ---
        jobs_scroll = ctk.CTkScrollableFrame(detail_frame, fg_color="transparent",
            label_text=f"Κατάλογος Εργασιών — {crew_name}",
            label_font=ctk.CTkFont(size=18, weight="bold"))
        jobs_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        jobs_scroll.grid_columnconfigure(0, weight=1)

        # Store for auto-refresh
        self._detail_view_crew_name = crew_name

        jobs = fetch_crew_jobs(crew_name)

        if not jobs:
            ctk.CTkLabel(jobs_scroll, text=f"Δεν βρέθηκαν καταχωρημένες εργασίες για το συνεργείο {crew_name}.",
                font=ctk.CTkFont(size=18, slant="italic"), text_color="gray", anchor="w").pack(fill="x", padx=20, pady=20)
        else:
            current_date_group = None
            for job in jobs:
                job_date = job.get('date', '')
                display_date = format_date_display(job_date)

                if job_date != current_date_group:
                    current_date_group = job_date
                    divider = ctk.CTkFrame(jobs_scroll, fg_color=("#C0C0C0", "#3A3A3A"), height=2)
                    divider.pack(fill="x", padx=10, pady=(12, 2))
                    ctk.CTkLabel(jobs_scroll, text=f"📅 {display_date}",
                        font=ctk.CTkFont(size=16, weight="bold"), anchor="w",
                        text_color=("#555555", "#AAAAAA")).pack(fill="x", padx=15, pady=(2, 5))

                row_frame = ctk.CTkFrame(jobs_scroll, fg_color=("#D9D9D9", "#1F1F1F"), corner_radius=6)
                row_frame.pack(fill="x", padx=10, pady=3)
                row_frame.grid_columnconfigure(0, weight=1)

                cat1 = job.get('category_1', job.get('cat1', ''))
                cat2 = job.get('category_2', job.get('cat2', ''))
                price = job.get('price_after_vat', job.get('price', 0))
                crew = job.get('crew', '-')
                invoice = job.get('invoice_number', job.get('invoice', '')) or '-'
                notes = job.get('notes', '') or ''
                client_name = job.get('client_name', 'Άγνωστος Πελάτης')
                client_code = job.get('client_code', '')
                notes_short = (notes[:40] + '...') if len(notes) > 40 else notes

                txt = f"🔧 {cat1} - {cat2}  |  Πελάτης: {client_name} [{client_code}]  |  €{float(price):.2f}  |  Τιμ: {invoice}"
                if notes_short:
                    txt += f"  |  {notes_short}"

                lbl = ctk.CTkLabel(row_frame, text=txt, justify="left", anchor="w",
                    font=ctk.CTkFont(size=16), wraplength=850, cursor="hand2")
                lbl.grid(row=0, column=0, sticky="ew", padx=10, pady=6)
                if client_code:
                    lbl.bind("<Button-1>", lambda e, cc=client_code: self.open_client_detail_view(cc))

                item_id = job.get('job_id', job.get('id'))
                ctk.CTkButton(row_frame, text="🔍 Πελάτης", width=80, height=30,
                    command=lambda cc=client_code: self.open_client_detail_view(cc)).grid(row=0, column=1, padx=2, pady=4)
                ctk.CTkButton(row_frame, text="✏️", width=35, height=30,
                    command=lambda iid=item_id: self._detail_edit_job(iid)).grid(row=0, column=2, padx=2, pady=4)
                ctk.CTkButton(row_frame, text="🗑️", width=35, height=30,
                    fg_color="#C0392B", hover_color="#E74C3C",
                    command=lambda iid=item_id: ConfirmationDialog(self,
                        f"Διαγραφή εργασίας ID {iid}?",
                        lambda jid=iid: self._crew_delete_job(jid))).grid(row=0, column=3, padx=2, pady=4)

        self.dynamic_ui_scaler(jobs_scroll)
        self.switch_frame("crew_detail")

    def _crew_delete_job(self, job_id):
        """Deletes a job from crew detail view and refreshes."""
        self.eav_delete_job(job_id)
        if hasattr(self, '_detail_view_crew_name'):
            self.open_crew_detail_view(self._detail_view_crew_name)

    def jump_to_client_calendar(self, client_code):
        self.active_client_code = client_code
        self.switch_frame("calendar")
        
        # Insert client code straight into calendar autocomplete field
        if hasattr(self, 'cal_filter_search') and self.cal_filter_search:
            entry_widget = self.cal_filter_search.entry if hasattr(self.cal_filter_search, 'entry') else self.cal_filter_search
            if hasattr(entry_widget, 'delete'):
                entry_widget.delete(0, "end")
                entry_widget.insert(0, str(client_code))
            
        # Execute the search filter immediately on arrival
        if hasattr(self, 'execute_calendar_query_action'):
            self.execute_calendar_query_action(None)

    def jump_to_client_ledger(self, client_code):
        self.active_client_code = client_code
        self.switch_frame("ledger")
        
        # --- PATH 1: Direct Variable Mapping Pass ---
        # Explicitly targets your real-time input entry field widget or variable string
        for field_attr in ['payment_search_entry', 'pay_search_entry', 'ledger_search_entry', 'ledger_filter_entry', 'inp_ledger_search']:
            if hasattr(self, field_attr):
                entry_box = getattr(self, field_attr)
                if hasattr(entry_box, 'delete'):
                    entry_box.delete(0, "end")
                    entry_box.insert(0, str(client_code))
                    entry_box.event_generate("<KeyRelease>")
                    break

        # --- PATH 2: Safe Layout Tree Scan Fallback ---
        active_pane = self.frames.get("ledger") or self.frames.get("payments")
        if active_pane:
            def crawl_and_trigger(widget):
                # Target text boxes that are not date fields or numerical sliders
                if hasattr(widget, 'insert') and hasattr(widget, 'delete') and not str(widget).endswith("date"):
                    try:
                        widget.delete(0, "end")
                        widget.insert(0, str(client_code))
                        widget.event_generate("<KeyRelease>")
                        return True
                    except: pass
                if hasattr(widget, 'winfo_children'):
                    for child in widget.winfo_children():
                        if crawl_and_trigger(child):
                            return True
                return False
            crawl_and_trigger(active_pane)
            
        # Trigger table population query to draw filtered values instantly
        for populate_routine in ['populate_payments_list', 'execute_ledger_query', 'refresh_ledger_view']:
            if hasattr(self, populate_routine):
                getattr(self, populate_routine)()
                break

    def eav_save_client(self, client_code, payload):
        known = ['code', 'name', 'telephone', 'vat', 'area', 'profession', 'notes', 'address_2', 'telephone_2', 'balance_owed']
        core = {k: payload.get(k, '') for k in known if k != 'balance_owed' and k != 'code'}
        extra = {k: v for k, v in payload.items() if k not in known}
        from logic_engine import update_client_record_payload
        update_client_record_payload(client_code, core.get('name', ''), core.get('telephone', ''),
            core.get('vat', ''), core.get('area', ''), core.get('profession', ''),
            core.get('notes', ''), core.get('address_2', ''), core.get('telephone_2', ''), extra)
        self.execute_registry_query(None)
        self.populate_payments_list()
        if hasattr(self, '_active_profile_client') and self._active_profile_client:
            from logic_engine import verify_and_fetch_client
            fresh = verify_and_fetch_client(client_code)
            if fresh:
                self._active_profile_client = fresh
                self.open_profile_timeline(fresh)
        self.refresh_ui()

    def eav_save_job(self, job_id, payload):
        known = ['job_id', 'cat1', 'cat2', 'crew', 'invoice', 'price', 'date', 'time', 'notes', 'extra_fields', 'client_name', 'client_code', 'price_before', 'vat_amount']
        core = {k: payload.get(k, '') for k in known if k != 'job_id'}
        extra = {k: v for k, v in payload.items() if k not in known}
        from logic_engine import update_job_record_payload
        update_job_record_payload(job_id, core.get('cat1', ''), core.get('cat2', ''), core.get('crew', ''),
            core.get('invoice', ''), core.get('price', '0'), core.get('date', ''), core.get('notes', ''), extra)
        self.execute_calendar_query_action(None)
        self.execute_registry_query(None)
        if hasattr(self, '_active_profile_client') and self._active_profile_client:
            self.refresh_profile_timeline()
        self.refresh_ui()

    def eav_save_payment(self, payment_id, payload):
        known = ['payment_id', 'amount', 'method', 'date', 'notes', 'extra_fields', 'client_name', 'client_code']
        core = {k: payload.get(k, '') for k in known if k != 'payment_id'}
        extra = {k: v for k, v in payload.items() if k not in known}
        from logic_engine import update_payment_record_payload
        update_payment_record_payload(payment_id, core.get('amount', '0'), core.get('method', ''),
            core.get('date', ''), core.get('notes', ''), extra)
        self.populate_payments_list()
        self.execute_registry_query(None)
        if hasattr(self, '_active_profile_client') and self._active_profile_client:
            self.refresh_profile_timeline()
        self.refresh_ui()

    def eav_delete_client(self, client_code):
        from logic_engine import delete_client_record
        delete_client_record(client_code)
        self.execute_registry_query(None)
        if self.active_client_code == client_code:
            self.active_client_code = None
            self.profile_panel.grid_forget()

    def eav_delete_job(self, job_id):
        from logic_engine import delete_job_by_id
        success = delete_job_by_id(job_id)
        self.execute_calendar_query_action(None)
        self.execute_registry_query(None)
        if hasattr(self, '_active_profile_client'):
            self.refresh_profile_timeline()
        if success:
            import tkinter.messagebox as mb
            mb.showinfo("Επιτυχία", "Η εργασία διαγράφηκε επιτυχώς.")

    def eav_delete_payment(self, payment_id):
        from logic_engine import delete_payment_record
        delete_payment_record(payment_id)
        self.populate_payments_list()
        self.execute_registry_query(None)
        if hasattr(self, '_active_profile_client'):
            self.refresh_profile_timeline()


# ──────────────────────────────────────────────
# UTILITY FUNCTIONS
# ──────────────────────────────────────────────

def _show_error_dialog(parent, title, message):
    import tkinter.messagebox as mb
    mb.showerror(title, message)

def _center_popup_on_parent(popup, parent):
    popup.update_idletasks()
    pw, ph = popup.winfo_width(), popup.winfo_height()
    px, py = parent.winfo_rootx(), parent.winfo_rooty()
    pw_parent, ph_parent = parent.winfo_width(), parent.winfo_height()
    x = px + (pw_parent - pw) // 2
    y = py + (ph_parent - ph) // 2
    popup.geometry(f"+{x}+{y}")


class EAVModalEditor(ctk.CTkToplevel):
    def __init__(self, parent_app, entity_type, entity_id, current_payload, save_callback):
        super().__init__(parent_app)
        try:
            self.parent_app = parent_app
            self.entity_type = entity_type
            self.entity_id = entity_id
            self.save_callback = save_callback
            if (entity_type == "job" and (not current_payload or "category_1" not in current_payload)):
                from logic_engine import get_job_by_id
                fetched = get_job_by_id(entity_id)
                if fetched:
                    current_payload = fetched
            elif (entity_type == "payment" and (not current_payload or "amount" not in current_payload)):
                from logic_engine import get_payment_by_id
                fetched = get_payment_by_id(entity_id)
                if fetched:
                    current_payload = fetched
            elif (entity_type == "client" and (not current_payload or "name" not in current_payload)):
                from logic_engine import get_client_by_code
                fetched = get_client_by_code(entity_id)
                if fetched:
                    current_payload = fetched
            self.working_data = dict(current_payload)
            self.ui_cfg = parent_app.ui_cfg
            # A touch larger than standard, scaled cleanly
            self.modal_font = ("Arial", max(int(parent_app.current_font_size + 1), 16))
            self.title(f"Επεξεργασία {entity_type.upper()} - ID: {entity_id}")
            self.geometry("650x600")
            self.transient(parent_app)
            self.grab_set()
            self.grid_columnconfigure(0, weight=1)
            self.grid_rowconfigure(0, weight=1)
            self.setup_modal_view()
            _center_popup_on_parent(self, parent_app)
            parent_app.dynamic_ui_scaler(self)
            self.update_idletasks()
        except Exception as e:
            print(f"EAV MODAL BUILD ERROR ({entity_type}): {e}")
            import tkinter.messagebox as mb
            mb.showerror("Σφάλμα Συστήματος", f"Σφάλμα κατά το άνοιγμα επεξεργασίας:\n{str(e)}")
            self.destroy()

    def setup_modal_view(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.scroll_frame.grid_columnconfigure(1, weight=1)
        if self.entity_type == 'job':
            defaults = {'category_1': '', 'category_2': '', 'crew': '', 'invoice_number': '', 'price_after_vat': '0.00', 'date': '', 'time_slot': '', 'notes': ''}
            for k, v in defaults.items():
                if k not in self.working_data:
                    if k == 'category_1' and 'cat1' in self.working_data:
                        self.working_data[k] = self.working_data.pop('cat1')
                    elif k == 'category_2' and 'cat2' in self.working_data:
                        self.working_data[k] = self.working_data.pop('cat2')
                    elif k == 'invoice_number' and 'invoice' in self.working_data:
                        self.working_data[k] = self.working_data.pop('invoice')
                    elif k == 'time_slot' and 'time' in self.working_data:
                        self.working_data[k] = self.working_data.pop('time')
                    elif k == 'price_after_vat' and 'price_after' in self.working_data:
                        self.working_data[k] = self.working_data.pop('price_after')
                    elif k == 'price_after_vat' and 'price' in self.working_data:
                        self.working_data[k] = self.working_data.pop('price')
                    else:
                        self.working_data[k] = v
        elif self.entity_type == 'payment':
            if 'client_name' not in self.working_data:
                self.working_data['client_name'] = ''
        self.field_references = {}
        self.crew_menu_refs = []
        current_row = 0
        HIDDEN_KEYS = {
            'client': {'extra_fields'},
            'job': {'extra_fields', 'job_id', 'client_code', 'client_name'},
            'payment': {'extra_fields', 'client_code', 'client_name', 'payment_id', 'client_name_full', 'balance_owed'},
        }
        if self.entity_type == 'client':
            code_val = self.working_data.get('code', '')
            ctk.CTkLabel(self.scroll_frame, text="Κωδικός:", font=self.ui_cfg.get_font(), anchor="w").grid(row=current_row, column=0, padx=10, pady=6, sticky="w")
            ctk.CTkLabel(self.scroll_frame, text=str(code_val), font=ctk.CTkFont(weight="bold"), anchor="w").grid(row=current_row, column=1, padx=10, pady=6, sticky="w")
            current_row += 1
            key_map = {'name': 'name', 'phone': 'telephone', 'phone_2': 'telephone_2', 'address': 'address', 'address_2': 'address_2', 'area': 'area', 'vat': 'vat_number', 'profession': 'profession'}
            schema = CLIENT_FIELDS_SCHEMA
            hidden = HIDDEN_KEYS['client']
        elif self.entity_type == 'job':
            key_map = {'job_type': 'category_1', 'subcategory': 'category_2', 'date_logged': 'date', 'time_logged': 'time_slot', 'invoice_number': 'invoice_number', 'notes': 'notes'}
            schema = JOB_FIELDS_SCHEMA
            hidden = HIDDEN_KEYS['job']
            for pk, pv in [('price_before_vat', '0.00'), ('vat_amount', '0.00'), ('price_after_vat', '0.00')]:
                if pk not in self.working_data:
                    self.working_data[pk] = pv
        elif self.entity_type == 'payment':
            key_map = {'amount': 'amount', 'date_received': 'date', 'payment_method': 'method', 'job_category': 'job_category', 'notes': 'notes'}
            schema = PAYMENT_FIELDS_SCHEMA
            hidden = HIDDEN_KEYS['payment']
        else:
            schema = []
            key_map = {}
            hidden = set()
        for label_text, schema_key in schema:
            actual_key = key_map.get(schema_key, schema_key)
            if actual_key in hidden:
                continue
            attribute_val = self.working_data.get(actual_key, '')
            ctk.CTkLabel(self.scroll_frame, text=f"{label_text}:", font=self.ui_cfg.get_font(), anchor="w").grid(row=current_row, column=0, padx=10, pady=6, sticky="w")
            entry_box = ctk.CTkEntry(self.scroll_frame, font=self.ui_cfg.get_font())
            entry_box.insert(0, str(attribute_val if attribute_val is not None else ""))
            entry_box.grid(row=current_row, column=1, padx=10, pady=6, sticky="ew")
            self.field_references[actual_key] = entry_box
            current_row += 1
        if self.entity_type == 'job':
            for price_key, price_label in [('price_before_vat', 'Τιμή προ ΦΠΑ (€)'), ('vat_amount', 'ΦΠΑ (€)'), ('price_after_vat', 'Τιμή με ΦΠΑ (€)')]:
                pv = self.working_data.get(price_key, '0.00')
                ctk.CTkLabel(self.scroll_frame, text=f"{price_label}:", font=self.ui_cfg.get_font(), anchor="w").grid(row=current_row, column=0, padx=10, pady=6, sticky="w")
                entry_box = ctk.CTkEntry(self.scroll_frame, font=self.ui_cfg.get_font())
                entry_box.insert(0, str(pv if pv is not None else '0.00'))
                entry_box.grid(row=current_row, column=1, padx=10, pady=6, sticky="ew")
                self.field_references[price_key] = entry_box
                current_row += 1
        if self.entity_type == 'client' and 'balance_owed' in self.working_data:
            bal = self.working_data['balance_owed']
            bal_color = "#FF6B6B" if float(bal or 0) > 0 else ("#3B8ED0" if float(bal or 0) < 0 else "#6BCB77")
            ctk.CTkLabel(self.scroll_frame, text="Υπόλοιπο Οφειλής:", font=self.ui_cfg.get_font(), anchor="w").grid(row=current_row, column=0, padx=10, pady=6, sticky="w")
            ctk.CTkLabel(self.scroll_frame, text=f"€{float(bal or 0):.2f}", font=ctk.CTkFont(weight="bold"), text_color=bal_color, anchor="w").grid(row=current_row, column=1, padx=10, pady=6, sticky="w")
            current_row += 1
        self.control_ribbon = ctk.CTkFrame(self)
        self.control_ribbon.grid(row=1, column=0, sticky="ew", padx=15, pady=10)
        self.control_ribbon.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(self.control_ribbon, text="💾 Αποθήκευση", fg_color="#2ECC71", hover_color="#27AE60", command=self.commit_changes, font=self.ui_cfg.get_font()).grid(row=0, column=0, padx=10, pady=5)

    def commit_changes(self):
        for key in list(self.working_data.keys()):
            if key in self.field_references:
                self.working_data[key] = self.field_references[key].get()
        if hasattr(self, 'crew_menu_refs') and self.crew_menu_refs:
            crew_names = [m.get() for m in self.crew_menu_refs if m.get().strip()]
            self.working_data['crew'] = ', '.join(crew_names)
        self.save_callback(self.entity_id, self.working_data)
        self.destroy()


import calendar


class CTkDatePicker(ctk.CTkToplevel):
    def __init__(self, parent_widget, target_entry_field):
        super().__init__(parent_widget)
        self.target_field = target_entry_field
        self.title("Επιλογή Ημερομηνίας")
        self.geometry("450x450")
        self.transient(parent_widget)
        self.grab_set()
        self.resizable(False, False)
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(self.header_frame, text="◀◀", width=35, command=lambda: self.adjust_year(-1)).pack(side="left", padx=2)
        ctk.CTkButton(self.header_frame, text="◀", width=35, command=self.prev_month).pack(side="left", padx=2)
        self.month_lbl = ctk.CTkLabel(self.header_frame, text="", font=ctk.CTkFont(weight="bold"))
        self.month_lbl.pack(side="left", expand=True)
        ctk.CTkButton(self.header_frame, text="▶", width=35, command=self.next_month).pack(side="right", padx=2)
        ctk.CTkButton(self.header_frame, text="▶▶", width=35, command=lambda: self.adjust_year(1)).pack(side="right", padx=2)
        self.grid_frame = ctk.CTkFrame(self)
        self.grid_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.draw_calendar_matrix()
        _center_popup_on_parent(self, parent_widget)
        if hasattr(parent_widget, 'dynamic_ui_scaler'):
            parent_widget.dynamic_ui_scaler(self)
        self.update_idletasks()

    def draw_calendar_matrix(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self.month_lbl.configure(text=f"{self.current_month}/{self.current_year}")
        days = ["Δε", "Τρ", "Τε", "Πέ", "Πα", "Σά", "Κυ"]
        for idx, d in enumerate(days):
            ctk.CTkLabel(self.grid_frame, text=d, font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=idx, pady=2)
        month_cal = calendar.monthcalendar(self.current_year, self.current_month)
        for r_idx, row in enumerate(month_cal):
            for c_idx, day in enumerate(row):
                if day != 0:
                    btn = ctk.CTkButton(self.grid_frame, text=str(day), width=35, height=40,
                        fg_color="transparent", text_color=("#1A1A1A", "#E0E0E0"), hover_color=("#3B8ED0", "#1F538D"),
                        command=lambda d=day: self.select_date_string(d))
                    btn.grid(row=r_idx+1, column=c_idx, padx=2, pady=2)

    def prev_month(self):
        self.current_month -= 1
        if self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        self.draw_calendar_matrix()

    def next_month(self):
        self.current_month += 1
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        self.draw_calendar_matrix()

    def adjust_year(self, delta):
        self.current_year += delta
        self.draw_calendar_matrix()

    def select_date_string(self, day):
        """Formats the picked calendar day explicitly to European standard DD-MM-YYYY."""
        date_str = f"{day:02d}-{self.current_month:02d}-{self.current_year}"
        self.target_field.delete(0, ctk.END)
        self.target_field.insert(0, date_str)
        # Auto-fire Return key event to refresh lists instantly upon picking a date
        self.target_field.event_generate("<Return>")
        self.destroy()


class ConfirmationDialog(ctk.CTkToplevel):
    def __init__(self, parent_app, message, confirm_callback):
        super().__init__(parent_app)
        self.confirm_callback = confirm_callback
        self.title("Επιβεβαίωση")
        self.geometry("400x200")
        self.transient(parent_app)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=message, font=ctk.CTkFont(size=18), wraplength=360, anchor="center", justify="center").pack(padx=20, pady=30)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="Ναι", fg_color="#C0392B", hover_color="#E74C3C",
            font=ctk.CTkFont(size=18, weight="bold"), command=self.do_confirm).grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text="Άκυρο", fg_color="#4A4A4A",
            command=self.destroy, font=ctk.CTkFont(size=18)).grid(row=0, column=1, padx=10)

    def do_confirm(self):
        self.confirm_callback()
        self.destroy()


class CTkAutocompleteEntry(ctk.CTkFrame):
    def __init__(self, parent, placeholder, search_callback=None):
        super().__init__(parent, fg_color="transparent")
        self.search_callback = search_callback
        
        # Upgraded to size 20 for readability
        self.entry = ctk.CTkEntry(self, placeholder_text=placeholder, font=("Arial", 20), height=45)
        self.entry.pack(fill="x", expand=True)
        self.grid_columnconfigure(0, weight=1)

        # --- FUZZY SEARCH DROPDOWN ---
        self._dropdown = None
        self._listbox = None
        self._results = []
        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<FocusOut>", self._on_focus_out)

    def get(self):
        return self.entry.get()

    def delete(self, first, last):
        self.entry.delete(first, last)

    def insert(self, idx, text):
        self.entry.insert(idx, text)

    def configure(self, **kwargs):
        self.entry.configure(**kwargs)

    def _on_key_release(self, event):
        # Ignore navigation keys to prevent double-firing
        if event.keysym in ["Up", "Down", "Left", "Right", "Return", "Escape", "Tab"]:
            return
            
        text = self.entry.get().strip()
        if len(text) < 1:
            self._hide_dropdown()
            return
            
        from logic_engine import fuzzy_search_clients
        self._results = fuzzy_search_clients(text)
        if not self._results:
            self._hide_dropdown()
            return
            
        self._show_dropdown()

    def _show_dropdown(self):
        if self._dropdown is None:
            self._dropdown = ctk.CTkToplevel(self)
            self._dropdown.overrideredirect(True)
            self._dropdown.attributes("-topmost", True)
            
            # Upgraded to size 18, forced background colors for contrast
            self._listbox = tkinter.Listbox(
                self._dropdown,
                font=("Arial", 18),
                height=min(8, len(self._results)),
                selectmode=tkinter.SINGLE,
                borderwidth=1,
                relief="solid",
                bg="#2D2D2D",
                fg="#E0E0E0",
                selectbackground="#3B8ED0",
                selectforeground="#FFFFFF",
                highlightthickness=0
            )
            self._listbox.pack(fill="both", expand=True)
            self._listbox.bind("<ButtonRelease-1>", self._on_select)
            self._listbox.bind("<Return>", self._on_select)
            
        # Position below the entry and force width to match entry
        self.update_idletasks()
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        target_width = self.entry.winfo_width()
        self._dropdown.geometry(f"{target_width}x{min(8, len(self._results)) * 30}+{x}+{y}")

        # Populate
        self._listbox.delete(0, "end")
        display_items = []
        for r in self._results:
            display = f"{r['name']} - [{r['code']}]"
            display_items.append(display)
            self._listbox.insert("end", display)
            
        self._listbox.configure(height=min(8, len(display_items)))
        self._dropdown.deiconify()

    def _hide_dropdown(self):
        if self._dropdown is not None:
            self._dropdown.withdraw()

    def _on_select(self, event):
        selection = self._listbox.curselection()
        if selection:
            idx = selection[0]
        else:
            # Fallback tracker: fetch whichever selection item sits directly under the cursor coordinates
            idx = self._listbox.nearest(event.y)
            
        if idx < 0 or idx >= len(self._results):
            return
            
        client = self._results[idx]
        formatted_string = f"{client['name']} - [{client['code']}]"
        
        # Autofill the entry box explicitly
        self.entry.delete(0, "end")
        self.entry.insert(0, formatted_string)
        self.entry.icursor("end")
        self._hide_dropdown()
        
        # Fire the search callback with the unique code to refresh the table instantly
        if self.search_callback:
            self.search_callback(client['code'])

    def _on_focus_out(self, event):
        # Increased delay slightly to ensure click registers before destruction
        self.after(300, self._hide_dropdown)


class BidirectionalVatCalculatorBlock(ctk.CTkFrame):
    def __init__(self, parent, vat_rate=0.24, **kwargs):
        super().__init__(parent, **kwargs)
        self.VAT_RATE = vat_rate
        self.pack_propagate(False)
        self.configure(height=60)
        self._suppress_loop = False
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=1)
        self.grid_columnconfigure(5, weight=1)
        
        ctk.CTkLabel(self, text="προ ΦΠΑ (€):", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=(0, 3))
        self.entry_before = ctk.CTkEntry(self, placeholder_text="0.00")
        self.entry_before.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.entry_before.bind("<KeyRelease>", lambda e: self._on_change("before"))
        
        ctk.CTkLabel(self, text="ΦΠΑ (%):", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=2, padx=(0, 3))
        self.entry_vat = ctk.CTkEntry(self, placeholder_text="24", width=60)
        self.entry_vat.grid(row=0, column=3, sticky="ew", padx=(0, 8))
        self.entry_vat.insert(0, str(int(vat_rate * 100)))
        self.entry_vat.bind("<KeyRelease>", lambda e: self._on_change("vat"))
        
        ctk.CTkLabel(self, text="με ΦΠΑ (€):", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=4, padx=(0, 3))
        self.entry_after = ctk.CTkEntry(self, placeholder_text="0.00")
        self.entry_after.grid(row=0, column=5, sticky="ew")
        self.entry_after.bind("<KeyRelease>", lambda e: self._on_change("after"))

    def _on_change(self, trigger_type):
        if self._suppress_loop:
            return
        self._suppress_loop = True
        try:
            from logic_engine import clean_numeric_input_string
            if trigger_type == "before":
                raw = self.entry_before.get()
                val = float(clean_numeric_input_string(raw)) if raw else 0.0
                vat_pct = float(clean_numeric_input_string(self.entry_vat.get())) if self.entry_vat.get() else 24.0
                vat_val = vat_pct / 100.0
                gross = val * (1 + vat_val)
                self.entry_after.delete(0, "end")
                self.entry_after.insert(0, f"{gross:.2f}")
            elif trigger_type == "after":
                raw = self.entry_after.get()
                val = float(clean_numeric_input_string(raw)) if raw else 0.0
                vat_pct = float(clean_numeric_input_string(self.entry_vat.get())) if self.entry_vat.get() else 24.0
                vat_val = vat_pct / 100.0
                net = val / (1 + vat_val) if val > 0 else 0.0
                self.entry_before.delete(0, "end")
                self.entry_before.insert(0, f"{net:.2f}")
            elif trigger_type == "vat":
                raw = self.entry_before.get()
                val = float(clean_numeric_input_string(raw)) if raw else 0.0
                vat_pct = float(clean_numeric_input_string(self.entry_vat.get())) if self.entry_vat.get() else 24.0
                vat_val = vat_pct / 100.0
                gross = val * (1 + vat_val)
                self.entry_after.delete(0, "end")
                self.entry_after.insert(0, f"{gross:.2f}")
        except Exception as e:
            print(f"Error calculating VAT: {e}")
        finally:
            self._suppress_loop = False


class VerticalVatCalculatorBlock(ctk.CTkFrame):
    def __init__(self, parent, vat_rate=0.24, **kwargs):
        super().__init__(parent, **kwargs)
        self.VAT_RATE = vat_rate
        self._suppress_loop = False
        
        self.grid_columnconfigure(0, weight=0, minsize=90)
        self.grid_columnconfigure(1, weight=1)
        
        # Row 0: Net Price
        ctk.CTkLabel(self, text="προ ΦΠΑ (€):", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.entry_before = ctk.CTkEntry(self, placeholder_text="0.00", font=ctk.CTkFont(size=14), height=35)
        self.entry_before.grid(row=0, column=1, sticky="ew", padx=10, pady=8)
        self.entry_before.bind("<KeyRelease>", lambda e: self._on_change("before"))
        
        # Row 1: VAT %
        ctk.CTkLabel(self, text="ΦΠΑ (%):", font=ctk.CTkFont(size=14, weight="bold")).grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.entry_vat = ctk.CTkEntry(self, placeholder_text="24", width=80, font=ctk.CTkFont(size=14), height=35)
        self.entry_vat.grid(row=1, column=1, sticky="w", padx=10, pady=8)
        self.entry_vat.insert(0, str(int(vat_rate * 100)))
        self.entry_vat.bind("<KeyRelease>", lambda e: self._on_change("vat"))
        
        # Row 2: Gross Price
        ctk.CTkLabel(self, text="με ΦΠΑ (€):", font=ctk.CTkFont(size=14, weight="bold")).grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.entry_after = ctk.CTkEntry(self, placeholder_text="0.00", font=ctk.CTkFont(size=14), height=35)
        self.entry_after.grid(row=2, column=1, sticky="ew", padx=10, pady=8)
        self.entry_after.bind("<KeyRelease>", lambda e: self._on_change("after"))

    def _on_change(self, trigger_type):
        if self._suppress_loop:
            return
        self._suppress_loop = True
        try:
            from logic_engine import clean_numeric_input_string
            if trigger_type == "before":
                raw = self.entry_before.get()
                val = float(clean_numeric_input_string(raw)) if raw else 0.0
                vat_pct = float(clean_numeric_input_string(self.entry_vat.get())) if self.entry_vat.get() else 24.0
                vat_val = vat_pct / 100.0
                gross = val * (1 + vat_val)
                self.entry_after.delete(0, "end")
                self.entry_after.insert(0, f"{gross:.2f}")
            elif trigger_type == "after":
                raw = self.entry_after.get()
                val = float(clean_numeric_input_string(raw)) if raw else 0.0
                vat_pct = float(clean_numeric_input_string(self.entry_vat.get())) if self.entry_vat.get() else 24.0
                vat_val = vat_pct / 100.0
                net = val / (1 + vat_val) if val > 0 else 0.0
                self.entry_before.delete(0, "end")
                self.entry_before.insert(0, f"{net:.2f}")
            elif trigger_type == "vat":
                raw = self.entry_before.get()
                val = float(clean_numeric_input_string(raw)) if raw else 0.0
                vat_pct = float(clean_numeric_input_string(self.entry_vat.get())) if self.entry_vat.get() else 24.0
                vat_val = vat_pct / 100.0
                gross = val * (1 + vat_val)
                self.entry_after.delete(0, "end")
                self.entry_after.insert(0, f"{gross:.2f}")
        except Exception as e:
            print(f"Error calculating VAT: {e}")
        finally:
            self._suppress_loop = False

    @staticmethod
    def _clean_float(val_str):
        if not val_str:
            return 0.0
        cleaned = val_str.replace("€", "").replace(" ", "").strip()
        if "," in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
            return float(cleaned)
        import re
        match = re.match(r'^-?[\d.]+', cleaned)
        return float(match.group(0)) if match else 0.0

    def _on_change(self, source):
        if self._suppress_loop:
            return
        self._suppress_loop = True
        try:
            raw_before = self.entry_before.get().strip()
            raw_vat = self.entry_vat.get().strip()
            raw_after = self.entry_after.get().strip()
            vat_pct = self._clean_float(raw_vat) if raw_vat else (self.VAT_RATE * 100)
            vat_rate = vat_pct / 100.0
            if source == "before":
                net = self._clean_float(raw_before)
                gross = round(net * (1 + vat_rate), 2)
                self.entry_after.delete(0, ctk.END)
                self.entry_after.insert(0, f"{gross:.2f}")
            elif source == "vat":
                if raw_before:
                    net = self._clean_float(raw_before)
                    gross = round(net * (1 + vat_rate), 2)
                    self.entry_after.delete(0, ctk.END)
                    self.entry_after.insert(0, f"{gross:.2f}")
                elif raw_after:
                    gross = self._clean_float(raw_after)
                    net = round(gross / (1 + vat_rate), 2)
                    self.entry_before.delete(0, ctk.END)
                    self.entry_before.insert(0, f"{net:.2f}")
            elif source == "after":
                gross = self._clean_float(raw_after)
                net = round(gross / (1 + vat_rate), 2)
                self.entry_before.delete(0, ctk.END)
                self.entry_before.insert(0, f"{net:.2f}")
        except (ValueError, IndexError):
            pass
        self._suppress_loop = False

    def get_values(self):
        from logic_engine import clean_numeric_input_string
        raw_before = self.entry_before.get().strip()
        raw_vat = self.entry_vat.get().strip()
        raw_after = self.entry_after.get().strip()
        price_before = float(clean_numeric_input_string(raw_before)) if raw_before else 0.0
        try:
            vat_pct = float(clean_numeric_input_string(raw_vat or "24"))
            vat_rate = vat_pct / 100.0
        except ValueError:
            vat_rate = 0.24
        price_after = float(clean_numeric_input_string(raw_after)) if raw_after else round(price_before * (1 + vat_rate), 2)
        vat_amount = round(price_after - price_before, 2)
        return (price_before, vat_amount, price_after)

    def set_values(self, price_before=None, vat_pct=None, price_after=None):
        self._suppress_loop = True
        if price_before is not None:
            self.entry_before.delete(0, ctk.END)
            self.entry_before.insert(0, f"{price_before:.2f}")
        if vat_pct is not None:
            self.entry_vat.delete(0, ctk.END)
            self.entry_vat.insert(0, str(int(vat_pct)))
        if price_after is not None:
            self.entry_after.delete(0, ctk.END)
            self.entry_after.insert(0, f"{price_after:.2f}")
        self._suppress_loop = False

    def clear(self):
        self._suppress_loop = True
        self.entry_before.delete(0, ctk.END)
        self.entry_vat.delete(0, ctk.END)
        self.entry_vat.insert(0, "24")
        self.entry_after.delete(0, ctk.END)
        self._suppress_loop = False


# Alias
BidirectionalVatCalculator = BidirectionalVatCalculatorBlock


# ──────────────────────────────────────────────
# APP ENTRY POINT
# ──────────────────────────────────────────────

if __name__ == "__main__":
    app = NSOFTApp()
    app.mainloop()
