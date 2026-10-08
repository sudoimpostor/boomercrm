import json
import customtkinter as ctk
import tkinter.messagebox as mb

# ==============================================================================
# COMPREHENSIVE GREEK -> ENGLISH TRANSLATION DICTIONARY
# ==============================================================================
TR_MAP = {
    # Navigation & Sidebar
    "👥  ΠΕΛΑΤΕΣ": "👥  CLIENTS",
    "📅  ΕΡΓΑΣΙΕΣ": "📅  JOBS & CALENDAR",
    "💰  ΠΛΗΡΩΜΕΣ": "💰  PAYMENTS & LEDGER",
    "📊  ΑΝΑΛΥΤΙΚΑ": "📊  ANALYTICS",
    "⚙️  ΡΥΘΜΙΣΕΙΣ": "⚙️  SETTINGS",
    "BOOMER CRM": "BOOMER CRM",
    "Boomer CRM - High-Visibility Operations Suite": "Boomer CRM - High-Visibility Operations Suite",
    
    # Client Registry & Profile
    "Αναζήτηση Πελατών": "Client Search",
    "Αναζήτηση Πελάτη...": "Search Client...",
    "Enter Name, Phone, or VAT (*code for exact match)...": "Enter Name, Phone, or VAT (*code for exact match)...",
    "Αναζήτηση με Όνομα, Τηλέφωνο ή ΑΦΜ (*κωδικός για ακριβή)...": "Search Name, Phone, or VAT (*code for exact)...",
    "Λίστα Πελατών": "Client List",
    "Επιλέξτε έναν πελάτη για προβολή.": "Select a client to view details.",
    "Καρτέλα Πελάτη": "Client Profile",
    "Καρτέλα Νέου Πελάτη": "New Client Profile",
    "Προσθήκη Νέου Πελάτη": "Add New Client",
    "Μητρώο & Ιστορικό Πελατών": "Client Registry & History",
    "Μη Καταχωρημένο Όνομα": "Unregistered Name",
    "Στοιχεία Νέου Πελάτη": "New Client Details",
    "Αναζήτηση Πελάτη:": "Search Client:",
    "Πληκτρολογήστε όνομα ή κωδικό...": "Type name or code...",
    "Όλοι οι πελάτες...": "All clients...",
    "Όνομα νέου πεδίου...": "New field name...",
    
    # Client Fields
    "Όνομα": "Name",
    "Όνομα:": "Name:",
    "Τηλέφωνο": "Phone",
    "Τηλ:": "Phone:",
    "📞 Τηλ:": "📞 Phone:",
    "- Τηλ:": "- Phone:",
    "Κινητό (Τηλ 2)": "Mobile (Phone 2)",
    "Κινητό:": "Mobile:",
    "Διεύθυνση": "Address",
    "Διεύθυνση:": "Address:",
    "Διεύθυνση 2": "Address 2",
    "Διεύθυνση 2:": "Address 2:",
    "Περιοχή": "Area",
    "Περιοχή:": "Area:",
    "ΑΦΜ": "VAT / Tax ID",
    "ΑΦΜ:": "VAT / Tax ID:",
    "|  📄 ΑΦΜ:": "|  📄 VAT:",
    "αφμ": "vat",
    "διεύθυνση": "address",
    "σημειώσεις": "notes",
    "καταχωρήσεις": "records",
    "Επάγγελμα": "Profession",
    "Επάγγελμα:": "Profession:",
    "Κωδικός:": "Code:",
    "Κωδικός Πελάτη": "Client Code",
    "Σημειώσεις": "Notes",
    "Σημειώσεις:": "Notes:",
    "Σημειώσεις...": "Notes...",
    "Σημ:": "Note:",
    "|  Σημ:": "|  Note:",
    
    # Financial & Balances
    "Υπόλοιπο:": "Balance:",
    "Υπόλοιπο: €": "Balance: €",
    "Υπόλοιπο: €0.00": "Balance: €0.00",
    "]   —   Υπόλοιπο: €": "]   —   Balance: €",
    "Υπόλοιπο Οφειλής:": "Outstanding Balance:",
    "Τρέχον Υπόλοιπο Οφειλής: €": "Current Outstanding Balance: €",
    "⏳ Ανεξόφλητο Υπόλοιπο": "⏳ Outstanding Balance",
    "Ανεξόφλητα Υπόλοιπα": "Outstanding Balances",
    "Τρέχοντα ανεξόφλητα παραστατικά": "Current unpaid invoices",
    "Οικονομικά": "Financials",
    "Οικονομικά:": "Financials:",
    "Ποσό Πληρωμής (€)": "Payment Amount (€)",
    "Ποσό Πληρωμής (€)...": "Payment Amount (€)...",
    "Ποσό (€)": "Amount (€)",
    "|  Ποσό: €": "|  Amount: €",
    "↕ Ποσό (€)": "↕ Amount (€)",
    "↕ Ημερομηνία": "↕ Date",
    "Τιμή προ ΦΠΑ (€)": "Price before VAT (€)",
    "προ ΦΠΑ (€):": "before VAT (€):",
    "Καθαρά (Προ ΦΠΑ): €": "Net (Before VAT): €",
    "ΦΠΑ (%):": "VAT (%):",
    "ΦΠΑ (€)": "VAT (€)",
    "ΦΠΑ (24%)": "VAT (24%)",
    "Τιμή με ΦΠΑ (€)": "Price with VAT (€)",
    "με ΦΠΑ (€):": "with VAT (€):",
    "Τελική Τιμή": "Total Price",
    "Τελική Τιμή (€)": "Total Price (€)",
    "Τιμολόγιο": "Invoice",
    "|  Τιμ:": "|  Inv:",
    "Τιμολόγιο / Ποσό:": "Invoice / Amount:",
    "Αριθμός Τιμολογίου": "Invoice Number",
    "Αριθμός Τιμολογίου:": "Invoice Number:",
    "Τρόπος Πληρωμής": "Payment Method",
    "Τρόπος Πληρωμής:": "Payment Method:",
    "|  Τρόπος:": "|  Method:",
        "ΠΟΝΤΙΚΙΑ": "RODENTS (Mice / Rats)",
    "ΚΑΤΣΑΡΙΔΕΣ": "COCKROACHES",
    "ΚΟΡΙΟΙ": "BEDBUGS",
    "ΨΥΛΛΟΙ": "FLEAS",
    "ΜΥΡΜΗΓΚΙΑ": "ANTS",
    "ΣΚΩΡΟΣ": "MOTHS",
    "ΝΙΚΟΣ": "NICK",
    "ΓΙΩΡΓΟΣ": "GEORGE",
    "ΚΩΣΤΑΣ": "KOSTAS",
    "ΔΗΜΗΤΡΗΣ": "DIMITRIS",
    "ΑΛΕΞΗΣ": "ALEX",
    "ΠΑΝΑΓΙΩΤΗΣ": "PANAGIOTIS",
    "ΓΙΟΥΡΙ": "YURI",
    "ΔΟΥΚΑΣ": "DOUKAS",
    "ΕΡΒΙΝ": "ERVIN",
    "ΝΙΚΟΣ-ΓΙΩΡΓΟΣ": "NICK-GEORGE",
    "ΓΙΩΡΓΟΣ-ΚΩΣΤΑΣ": "GEORGE-KOSTAS",
    "ΜΕΤΡΗΤΑ": "Cash",
    "ΤΡΑΠΕΖΑ": "Bank Transfer",
    "ΚΑΡΤΑ": "Card",
    "ΜΕΤΡΗΤΑ (Cash)": "Cash",
    "ΤΡΑΠΕΖΑ (Bank Transfer)": "Bank Transfer",
    "ΚΑΡΤΑ (Card)": "Card",
    
    # Calendar & Jobs
    "Ημερολόγιο Εργασιών": "Jobs Calendar",
    "Εργασίες": "Jobs",
    "Εργασίες:": "Jobs:",
    "Λίστα Εργασιών": "Jobs List",
    "Νέα Εργασία": "New Job",
    "Αποθήκευση Εργασίας": "Save Job",
    "Εισαγωγή Νέας Εργασίας Ημερολογίου": "Schedule New Job",
    "Περιγραφή Εργασίας:": "Job Description:",
    "π.χ. Εγκατάσταση Δικτύου": "e.g. Network Installation",
    "Κατηγορία Εργασίας": "Job Category",
    "Κατηγορία Εργασίας:": "Job Category:",
    "Κατηγορία:": "Category:",
    "Υποκατηγορία": "Subcategory",
    "Υποκατηγορία:": "Subcategory:",
    "Συνεργείο": "Crew",
    "Συνεργείο:": "Crew:",
    "|  Συνεργείο:": "|  Crew:",
    "Συνεργείο (Crew):": "Crew:",
    "Συνεργείο (Πολλαπλή Επιλογή):": "Crew (Multi-Select):",
    "Συνεργείο (π.χ. ΓΙΩΡΓΟΣ+ΝΙΚΟΣ)": "Crew (e.g. GEORGE+NICK)",
    "Συνεργείο Α": "Crew A",
    "Συνεργείο Β": "Crew B",
    "Εξωτερικό": "External",
    "Σημειώσεις Εργασίας": "Job Notes",
    "Σημειώσεις Εργασίας:": "Job Notes:",
    "ΑΠΕΝΤΟΜΩΣΗ": "PEST CONTROL",
    "ΜΥΟΚΤΟΝΙΑ": "RODENT CONTROL",
    "ΑΠΟΛΥΜΑΝΣΗ": "DISINFECTION",
    "ΚΑΤΣΑΡΙΔΕΣ": "COCKROACHES",
    "ΠΟΝΤΙΚΙΑ": "RODENTS",
    "ΜΙΚΡΟΒΙΑ": "PATHOGENS",
    
    # Ledger & Payments
    "Μητρώο Πληρωμών": "Payment Registry",
    "Λίστα Πληρωμών": "Payments List",
    "Νέα Πληρωμή": "New Payment",
    "Επιβεβαίωση Πελάτη": "Confirm Client",
    "✔ Επιβεβαίωση Πελάτη": "✔ Confirm Client",
    "Επιλεγμένος Πελάτης: Κανένας": "Selected Client: None",
    "Επιλεγμένος Πελάτης: Σφάλμα (Κενό)": "Selected Client: Error (Empty)",
    "Επιλεγμένος Πελάτης:": "Selected Client:",
    "Πελάτης:": "Client:",
    "|  Πελάτης:": "|  Client:",
    "🔍 Πελάτης": "🔍 Client",
    "Άγνωστος": "Unknown",
    "Άγνωστος Πελάτης": "Unknown Client",
    
    # Dates & Calendar Days
    "Ημερομηνία": "Date",
    "Ημερομηνία:": "Date:",
    "Ημερομηνία (DD-MM-YY)...": "Date (DD-MM-YY)...",
    "Ημερομηνία (DD-MM-YY):": "Date (DD-MM-YY):",
    "ΗΗ/ΜΜ/ΕΕΕΕ": "DD/MM/YYYY",
    "Ώρα": "Time",
    "Ώρα:": "Time:",
    "Ώρα (HH:MM):": "Time (HH:MM):",
    "Επιλογή Ημερομηνίας": "Select Date",
    "Σήμερα": "Today",
    "Αυτή την Εβδομάδα": "This Week",
    "Τρέχων Μήνας": "Current Month",
    "Αυτό το Έτος": "This Year",
    "Δευτέρα": "Monday",
    "Τρίτη": "Tuesday",
    "Τετάρτη": "Wednesday",
    "Πέμπτη": "Thursday",
    "Παρασκευή": "Friday",
    "Σάββατο": "Saturday",
    "Κυριακή": "Sunday",
    "Δε": "Mo", "Τρ": "Tu", "Τε": "We", "Πέ": "Th", "Πα": "Fr", "Σά": "Sa", "Κυ": "Su",
    
    # Analytics & Reports
    "Επιχειρηματική Εικόνα": "Business Overview",
    "💰 Συνολικός Τζίρος": "💰 Total Revenue",
    "📥 Εισπράξεις Ταμείου": "📥 Total Collected",
    "🚨 Ληξιπρόθεσμα & Ενεργά Υπόλοιπα": "🚨 Active Balances",
    "🔴 Κρίσιμα (90+ Ημέρες)": "🔴 Critical (90+ Days)",
    "🟡 Προσοχή (30-90 Ημέρες)": "🟡 Warning (30-90 Days)",
    "🟢 Πρόσφατα Υπόλοιπα (<30 Ημέρες)": "🟢 Recent Balances (<30 Days)",
    "👷 Κατανομή Έργου Συνεργείων (Κλικ για Αναλυτικές Εργασίες 🔍)": "👷 Crew Workload (Click for Details 🔍)",
    "👷  Εργασίες Συνεργείου / Τεχνικού:": "👷 Crew / Technician Jobs:",
    "■ Ιστορικό Εργασιών (Κλικ για Φιλτράρισμα 🔍)": "■ Job History (Click to Filter 🔍)",
    "■ Ιστορικό Πληρωμών (Κλικ για Ledger Ταμείου 🔍)": "■ Payment History (Click for Ledger 🔍)",
    "Ιστορικό Εργασιών & Πληρωμών —": "Job & Payment History —",
    "Κατάλογος Εργασιών —": "Job Catalog —",
    "Φίλτρο Πελάτη (Αναζήτηση):": "Client Filter (Search):",
    "Πληκτρολογήστε όνομα για φιλτράρισμα... (ή κενό για Όλους)": "Type name to filter... (or blank for All)",
    "Από:": "From:",
    "Έως:": "To:",
    
    # Actions & Buttons
    "Αποθήκευση": "Save",
    "💾 Αποθήκευση": "💾 Save",
    "💾 Αποθήκευση Πελάτη": "💾 Save Client",
    "💾 Αποθήκευση Αλλαγών": "💾 Save Changes",
    "✔ Αποθήκευση Πληρωμής": "✔ Save Payment",
    "Αποθήκευση Στοιχείων Πελάτη (Save)": "Save Client Details",
    "Επεξεργασία": "Edit",
    "Επεξεργασία Πελάτη": "Edit Client",
    "Επεξεργασία Εργασίας": "Edit Job",
    "Επεξεργασία Πληρωμής": "Edit Payment",
    "✏️ Πελάτη": "✏️ Client",
    "Διαγραφή": "Delete",
    "Επιβεβαίωση": "Confirm",
    "Ακύρωση": "Cancel",
    "Άκυρο": "Cancel",
    "Ναι": "Yes",
    "Όχι": "No",
    "Κλείσιμο": "Close",
    "← Πίσω": "← Back",
    "🔄 Υπολογισμός": "🔄 Calculate",
    "➕ Προσθήκη Πεδίου": "➕ Add Field",
    
    # Settings & Recovery
    "Ρυθμίσεις Συστήματος": "System Settings",
    "Ελληνικά": "Greek",
    "English": "English",
    "Γλώσσα": "Language",
    "Γλώσσα / Language": "Language / Γλώσσα",
    "Language / Γλώσσα": "Language / Γλώσσα",
    "Μέγεθος Γραμματοσειράς": "Font Size",
    "Μέγεθος Γραμματοσειράς:": "Font Size:",
    "⚙ UI Scaling & Γλώσσα": "⚙ UI Scaling & Language",
    "⚙ UI Scaling & Localization": "⚙ UI Scaling & Localization",
    "🔒 Αντίγραφα Ασφαλείας & Εξαγωγή": "🔒 Data Backup & Export",
    "🔒 Redundant Workspace Preservation Ledger": "🔒 Data Backup & CSV Export",
    "Creates a timestamped binary copy of the database plus loose CSV tables into your backups directory.": "Creates a timestamped database backup and exports CSV spreadsheets to the backups directory.",
    "🚀 Execute Snapshot & Export CSV Sheets": "🚀 Execute Backup Snapshot & Export CSV",
    "🚀 Εκτέλεση Αντιγράφου & Εξαγωγή CSV": "🚀 Execute Backup Snapshot & Export CSV",
    "🛠️ Κέντρο Ανάκτησης & Αποκατάστασης": "🛠️ Data Recovery & Restore Center",
    "🛠️ Κέντρο Ανάκτησης & Αποκατάστασης Δεδομένων": "🛠️ Data Recovery & Restore Center",
    "Επιλέξτε ένα αυτόματο σημείο ελέγχου (BACKUP - DATE) ή αναζητήστε ένα αρχείο βάσης χειροκίνητα:": "Select an automatic backup checkpoint or browse for a .db file manually:",
    "Επιλέξτε ένα αυτόματο σημείο ελέγχου από τον φάκελο backups ή αναζητήστε ένα αρχείο χειροκίνητα:": "Select an automatic backup checkpoint or browse for a .db file manually:",
    "Δεν βρέθηκαν": "Not found",
    "Δεν βρέθηκαν αντίγραφα ασφαλείας": "No backups found",
    "⏪ Ανάκτηση Σημείου": "⏪ Restore Checkpoint",
    "📁 Χειροκίνητη Επιλογή (.db)": "📁 Browse (.db file)",
    "Επιλέξτε Αρχείο Βάσης (.db)": "Select Database File (.db)",
    "Επιλέξτε Αρχείο Βάσης Δεδομένων (.db)": "Select Database File (.db)",
    "Επαναφορά στο σημείο": "Restore checkpoint",
    ";\nΤα τρέχοντα δεδομένα θα αποθηκευτούν ως .old": ";\nCurrent data will be saved as .old",
    ";\nΤα τρέχοντα δεδομένα θα μετονομαστούν σε .old": ";\nCurrent data will be renamed to .old",
    "⚠️ Διαγραφή Όλων των Δεδομένων (Wipe Application Data)": "⚠️ Wipe All Application Records",
    "⚠️ Ζώνη Κινδύνου": "⚠️ Danger Zone",
    "📋 Κατηγορίες Εργασιών": "📋 Job Categories",
    "🏷️ Υποκατηγορίες Εργασιών": "🏷️ Job Subcategories",
    "💳 Τρόποι Πληρωμής": "💳 Payment Methods",
    "👷 Μέλη Συνεργείων": "👷 Crew Members",
    
    # Dialogs & Notifications
    "Προσοχή": "Warning",
    "ΠΡΟΣΟΧΗ": "WARNING",
    "Σφάλμα": "Error",
    "Σφάλμα Συστήματος": "System Error",
    "Επιτυχία": "Success",
    "✅ Επιτυχία!": "✅ Success!",
    "Πρέπει να επιλέξετε πελάτη!": "You must select a client!",
    "Πρέπει να επιλέξετε πελάτη (Αναζήτηση & Επιβεβαίωση)!": "You must select a client (Search & Confirm)!",
    "Συμπληρώστε ποσό και ημερομηνία!": "Please enter an amount and date!",
    "Η πληρωμή καταχωρήθηκε!": "Payment recorded successfully!",
    "Η εργασία καταχωρήθηκε επιτυχώς!": "Job scheduled successfully!",
    "Η εργασία διαγράφηκε επιτυχώς!": "Job deleted successfully!",
    "Δεν υπάρχουν καταχωρημένες πληρωμές.": "No payments recorded.",
    "Δεν βρέθηκαν καταχωρημένες πληρωμές.": "No payments found.",
    "Δεν βρέθηκαν καταχωρημένες εργασίες.": "No jobs found.",
    "Δεν βρέθηκαν καταχωρημένες εργασίες ή πληρωμές.": "No jobs or payments found.",
    "Δεν βρέθηκαν εκτελεσμένες εργασίες από συνεργεία σε αυτό το διάστημα.": "No completed jobs found for this period.",
    "✔️ Όλες οι καρτέλες είναι καθαρές για τα επιλεγμένα κριτήρια.": "✔️ All accounts are balanced for selected criteria.",
    "❌ Το όνομα πελάτη είναι υποχρεωτικό.": "❌ Client name is required.",
    "❌ Αποτυχία αποθήκευσης πελάτη.": "❌ Failed to save client.",
    "❌ Πελάτης δεν βρέθηκε": "❌ Client not found",
    "❌ Σφάλμα (Κενό)": "❌ Error (Empty)",
    "❌ Σφάλμα Ανάκτησης": "❌ Recovery Error",
    "Σφάλμα κατά το άνοιγμα επεξεργασίας:": "Error opening editor:",
    "Αδυναμία καθαρισμού δεδομένων:": "Failed to wipe data:",
    "Αδυναμία φόρτωσης αρχείου:": "Failed to load file:",
    "Η βάση δεδομένων αποκαταστάθηκε με επιτυχία.\nΌλες οι καρτέλες ανανεώθηκαν!": "Database restored successfully.\nAll tabs have been refreshed!",
    "Η βάση δεδομένων αποκαταστάθηκε με επιτυχία.\nΗ εφαρμογή θα ανανεώσει τα δεδομένα τώρα.": "Database restored successfully.\nRefreshing application data now.",
    "Η βάση δεδομένων εκκαθαρίστηκε πλήρως. Έτοιμο για παράδοση!": "Database completely wiped. Clean and ready!",
    "Διαγραφή job ID": "Delete job ID",
    "Διαγραφή εργασίας ID": "Delete job ID",
    "Διαγραφή πληρωμής ID": "Delete payment ID",
    "Είστε σίγουροι για τη διαγραφή του πελάτη": "Are you sure you want to delete client",
    "Η εργασία διαγράφηκε επιτυχώς.": "Job deleted successfully.",
    "✅ Ο πελάτης αποθηκεύτηκε με κωδικό": "✅ Client saved with code",
    "Είστε σίγουροι ότι θέλετε να διαγράψετε οριστικά όλα τα δεδομένα;\n\nΑυτή η ενέργεια δεν αναιρείται.": "Are you sure you want to permanently wipe all data?\n\nThis action cannot be undone."
}

def translate_str(s):
    """Deep translator handling exact phrases and dynamic patterns."""
    if not isinstance(s, str) or not s:
        return s
    
    if s.startswith("   • "):
        return "   • " + translate_str(s[5:])
    if s.startswith("Σημ: "):
        return "Note: " + s[5:]
    if s.startswith("Καθαρά (Προ ΦΠΑ): €"):
        return "Net (Before VAT): €" + s[len("Καθαρά (Προ ΦΠΑ): €"):]
    if "Method: " in s:
        s = s.replace("Method: ΜΕΤΡΗΤΑ", "Method: Cash").replace("Method: ΤΡΑΠΕΖΑ", "Method: Bank Transfer").replace("Method: ΚΑΡΤΑ", "Method: Card")
    if s.startswith("• "):
        return "• " + translate_str(s[2:])
    if "καταχωρήσεις" in s:
        s = s.replace("Εργασίες: ", "Jobs: ").replace(" καταχωρήσεις", " records")
    
    st = s.strip()
    if st in TR_MAP:
        prefix = s[:len(s) - len(s.lstrip())]
        suffix = s[len(s.rstrip()):]
        return prefix + TR_MAP[st] + suffix
    
    # Pattern checks
    if s.startswith("Επιλεγμένος Πελάτης: "):
        rest = s[len("Επιλεγμένος Πελάτης: "):]
        return f"Selected Client: {translate_str(rest)}"
    if s.startswith("Υπόλοιπο: €"):
        return f"Balance: €{s[len('Υπόλοιπο: €'):]}"
    if s.startswith("Τηλ: "):
        return f"Phone: {s[len('Τηλ: '):]}"
    if s.startswith("Διαγραφή πληρωμής ID "):
        return f"Delete payment ID {s[len('Διαγραφή πληρωμής ID '):]}"
    if s.startswith("Διαγραφή εργασίας ID "):
        return f"Delete job ID {s[len('Διαγραφή εργασίας ID '):]}"
    if s.startswith("Διαγραφή job ID "):
        return f"Delete job ID {s[len('Διαγραφή job ID '):]}"
    if s.startswith("Είστε σίγουροι για τη διαγραφή του πελάτη "):
        return f"Are you sure you want to delete client {s[len('Είστε σίγουροι για τη διαγραφή του πελάτη '):]}"
    if s.startswith("✅ Ο πελάτης αποθηκεύτηκε με κωδικό "):
        return f"✅ Client saved with code {s[len('✅ Ο πελάτης αποθηκεύτηκε με κωδικό '):]}"
    if "Ημερομηνία: " in s and "Ποσό: €" in s:
        return s.replace("Ημερομηνία: ", "Date: ").replace("Ποσό: €", "Amount: €").replace("Τρόπος: ", "Method: ")
    if s.startswith("Δεν βρέθηκαν καταχωρημένες εργασίες για το συνεργείο"):
        return s.replace("Δεν βρέθηκαν καταχωρημένες εργασίες για το συνεργείο", "No jobs found for crew")
    
    return s


class UIConfig:
    _instance = None

    def __init__(self, config_file="config.json"):
        UIConfig._instance = self
        self.config_file = config_file
        # Default settings
        self.settings = {"font_size": 25, "lang": "el", "window_size": "1000x700"}
        self.load()
        
        # Ensure crews and categories lists exist
        if "crews" not in self.settings:
            self.settings["crews"] = ["ΝΙΚΟΣ-ΓΙΩΡΓΟΣ", "ΚΩΣΤΑΣ", "ΝΙΚΟΣ"]
        if "categories" not in self.settings:
            self.settings["categories"] = ["ΑΠΕΝΤΟΜΩΣΗ (Pest Control)", "ΜΥΟΚΤΟΝΙΑ (Rodent Control)", "ΑΠΟΛΥΜΑΝΣΗ (Disinfection)"]
        if "payment_methods" not in self.settings:
            self.settings["payment_methods"] = ["ΜΕΤΡΗΤΑ (Cash)", "ΤΡΑΠΕΖΑ (Bank Transfer)", "ΚΑΡΤΑ (Card)"]

    @classmethod
    def get_current_lang(cls):
        if cls._instance:
            return cls._instance.settings.get("lang", "el")
        return "el"

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

    def get_text(self, key_or_text):
        if self.settings.get("lang", "el") == "en":
            return translate_str(key_or_text)
        return key_or_text

    def get_client_schema(self):
        if self.settings.get("lang", "el") == "en":
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
        if self.settings.get("lang", "el") == "en":
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
        if self.settings.get("lang", "el") == "en":
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


def tr(text):
    """Global translation helper."""
    if UIConfig.get_current_lang() == "en":
        return translate_str(text)
    return text


def install_ui_translator():
    """Hooks CustomTkinter and messagebox widgets so text automatically displays in selected language."""
    # CTkLabel
    orig_label_init = ctk.CTkLabel.__init__
    orig_label_conf = ctk.CTkLabel.configure

    def new_label_init(self, *args, **kwargs):
        if 'text' in kwargs:
            kwargs['text'] = tr(kwargs['text'])
        orig_label_init(self, *args, **kwargs)

    def new_label_conf(self, **kwargs):
        if 'text' in kwargs:
            kwargs['text'] = tr(kwargs['text'])
        orig_label_conf(self, **kwargs)

    ctk.CTkLabel.__init__ = new_label_init
    ctk.CTkLabel.configure = new_label_conf

    # CTkButton
    orig_btn_init = ctk.CTkButton.__init__
    orig_btn_conf = ctk.CTkButton.configure

    def new_btn_init(self, *args, **kwargs):
        if 'text' in kwargs:
            kwargs['text'] = tr(kwargs['text'])
        orig_btn_init(self, *args, **kwargs)

    def new_btn_conf(self, **kwargs):
        if 'text' in kwargs:
            kwargs['text'] = tr(kwargs['text'])
        orig_btn_conf(self, **kwargs)

    ctk.CTkButton.__init__ = new_btn_init
    ctk.CTkButton.configure = new_btn_conf

    # CTkEntry
    orig_entry_init = ctk.CTkEntry.__init__
    orig_entry_conf = ctk.CTkEntry.configure

    def new_entry_init(self, *args, **kwargs):
        if 'placeholder_text' in kwargs:
            kwargs['placeholder_text'] = tr(kwargs['placeholder_text'])
        orig_entry_init(self, *args, **kwargs)

    def new_entry_conf(self, **kwargs):
        if 'placeholder_text' in kwargs:
            kwargs['placeholder_text'] = tr(kwargs['placeholder_text'])
        orig_entry_conf(self, **kwargs)

    ctk.CTkEntry.__init__ = new_entry_init
    ctk.CTkEntry.configure = new_entry_conf

    # CTkScrollableFrame
    orig_scroll_init = ctk.CTkScrollableFrame.__init__
    orig_scroll_conf = ctk.CTkScrollableFrame.configure

    def new_scroll_init(self, *args, **kwargs):
        if 'label_text' in kwargs:
            kwargs['label_text'] = tr(kwargs['label_text'])
        orig_scroll_init(self, *args, **kwargs)

    def new_scroll_conf(self, **kwargs):
        if 'label_text' in kwargs:
            kwargs['label_text'] = tr(kwargs['label_text'])
        orig_scroll_conf(self, **kwargs)

    ctk.CTkScrollableFrame.__init__ = new_scroll_init
    ctk.CTkScrollableFrame.configure = new_scroll_conf

    # CTkOptionMenu
    orig_opt_init = ctk.CTkOptionMenu.__init__
    orig_opt_conf = ctk.CTkOptionMenu.configure

    def new_opt_init(self, *args, **kwargs):
        if 'values' in kwargs and kwargs['values'] and isinstance(kwargs['values'], list):
            kwargs['values'] = [tr(v) for v in kwargs['values']]
        orig_opt_init(self, *args, **kwargs)

    def new_opt_conf(self, **kwargs):
        if 'values' in kwargs and kwargs['values'] and isinstance(kwargs['values'], list):
            kwargs['values'] = [tr(v) for v in kwargs['values']]
        orig_opt_conf(self, **kwargs)

    ctk.CTkOptionMenu.__init__ = new_opt_init
    ctk.CTkOptionMenu.configure = new_opt_conf

    # messagebox popups
    orig_showinfo = mb.showinfo
    orig_showwarning = mb.showwarning
    orig_showerror = mb.showerror
    orig_askyesno = mb.askyesno

    mb.showinfo = lambda title=None, message=None, **kw: orig_showinfo(title=tr(title), message=tr(message), **kw)
    mb.showwarning = lambda title=None, message=None, **kw: orig_showwarning(title=tr(title), message=tr(message), **kw)
    mb.showerror = lambda title=None, message=None, **kw: orig_showerror(title=tr(title), message=tr(message), **kw)
    mb.askyesno = lambda title=None, message=None, **kw: orig_askyesno(title=tr(title), message=tr(message), **kw)


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
