import json
import customtkinter as ctk


class UIConfig:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        # Default settings
        self.settings = {"font_size": 25, "lang": "el", "window_size": "1000x700"}
        self.load()
        self.strings = {
            "el": {"search_placeholder": "Αναζήτηση...", "settings": "Ρυθμίσεις"},
            "en": {"search_placeholder": "Search...", "settings": "Settings"}
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
            with open(self.config_file, "r") as f:
                self.settings.update(json.load(f))
        except FileNotFoundError:
            self.save()

    def save(self):
        with open(self.config_file, "w") as f:
            json.dump(self.settings, f)

    def get_font(self, size_offset=0):
        return ctk.CTkFont(family="Segoe UI", size=self.settings["font_size"] + size_offset)

    def get_text(self, key):
        return self.strings.get(self.settings["lang"], self.strings["el"]).get(key, key)


# --- DPI / window-size scaling helper -------------------------------------
# Anchored to the main window's current width vs a 1150px design baseline,
# clamped so widgets never blow up on big monitors or vanish on small ones.
_DESIGN_BASE_WIDTH = 1150
_SCALE_MIN = 0.85
_SCALE_MAX = 1.25
_root_ref = None  # set once by NSOFTApp via set_scale_root()


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
