import sqlite3
import os

# Ensure the directory exists
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "company_data.db")

# Connect to SQLite (creates the file if it doesn't exist)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Create CLIENTS Table
cursor.execute('''
CREATE TABLE IF NOT EXISTS clients (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT,
    area TEXT,
    telephone TEXT,
    vat_number TEXT,
    profession TEXT,
    notes TEXT
)
''')

# 2. Create JOBS Table
cursor.execute('''
CREATE TABLE IF NOT EXISTS jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_code TEXT,
    category_1 TEXT,
    category_2 TEXT,
    crew TEXT,
    date TEXT,
    time_slot TEXT,
    invoice_number TEXT,
    price_before_vat REAL,
    vat_amount REAL,
    price_after_vat REAL,
    notes TEXT,
    is_special INTEGER DEFAULT 0,
    extra_fields TEXT DEFAULT '{}',
    FOREIGN KEY(client_code) REFERENCES clients(code) ON DELETE CASCADE
)
''')

# 3. Create PAYMENTS Table
cursor.execute('''
CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_code TEXT,
    client_name TEXT,
    date TEXT,
    amount REAL,
    method TEXT,
    notes TEXT,
    is_special INTEGER DEFAULT 0,
    extra_fields TEXT DEFAULT '{}',
    FOREIGN KEY(client_code) REFERENCES clients(code) ON DELETE CASCADE
)
''')

# 4. Inject Mock Data (Pest Control Theme)
mock_clients = [
    ('1001', 'ΕΛΛΗΝΙΚΟΝ ΑΒΕΕ', 'ΒΗΣΣΑΡΙΩΝΟΣ 9', 'ΑΘΗΝΑ', '2103641174', '094141963', 'ΕΜΠΟΡΙΑ ΑΓΡΟΤΙΚΩΝ', 'Παλιός πελάτης'),
    ('1002', 'ΜΥΛΟΙ ΣΟΓΙΑΣ ΑΕ', 'ΑΛΑΜΑΝΑΣ 1', 'ΜΑΡΟΥΣΙ', '2106384400', '094017300', 'ΒΙΟΜΗΧΑΝΙΑ ΤΡΟΦΙΜΩΝ', 'Απαιτείται συντονισμός με operations manager'),
    ('1003', 'ΕΣΤΙΑΤΟΡΙΑ ΧΟΛΑΡΓΟΥ ΑΕ', 'ΠΕΡΙΚΛΕΟΥΣ 45', 'ΧΟΛΑΡΓΟΣ', '2106512345', '099912345', 'ΕΣΤΙΑΣΗ', 'Απεντομώσεις κουζίνας')
]

mock_jobs = [
    (1, '1001', 'ΑΠΕΝΤΟΜΩΣΗ', 'ΚΑΤΣΑΡΙΔΕΣ', 'ΝΙΚΟΣ-ΓΙΩΡΓΟΣ', '2026-07-01', '10:00-12:00', 'ΤΠΥ-1234', 150.00, 36.00, 186.00, 'Χρήση σκευάσματος Americana'),
    (2, '1002', 'ΜΥΟΚΤΟΝΙΑ', 'ΠΟΝΤΙΚΙΑ', 'ΚΩΣΤΑΣ', '2026-07-02', '08:00-10:00', 'ΤΠΥ-1235', 300.00, 72.00, 372.00, 'Τοποθέτηση δολωματικών σταθμών περιμετρικά'),
    (3, '1003', 'ΑΠΟΛΥΜΑΝΣΗ', 'ΜΙΚΡΟΒΙΑ', 'ΝΙΚΟΣ', '2026-07-03', '15:00-16:00', 'ΤΠΥ-1236', 120.00, 28.80, 148.80, 'Τακτική μηνιαία εφαρμογή')
]

mock_payments = [
    ('1001', 'ΕΛΛΗΝΙΚΟΝ ΑΒΕΕ', '2026-07-01', 186.00, 'ΤΡΑΠΕΖΑ', 'Εξόφληση ΤΠΥ-1234'),
    ('1002', 'ΜΥΟΚΤΟΝΙΑ ΣΟΓΙΑΣ ΑΕ', '2026-07-04', 200.00, 'ΜΕΤΡΗΤΑ', 'Έναντι λογαριασμού')
]

cursor.executemany(
    'INSERT OR IGNORE INTO clients (code, name, address, area, telephone, vat_number, profession, notes) VALUES (?,?,?,?,?,?,?,?)',
    mock_clients
)
cursor.executemany(
    'INSERT OR IGNORE INTO jobs (job_id, client_code, category_1, category_2, crew, date, time_slot, invoice_number, price_before_vat, vat_amount, price_after_vat, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
    mock_jobs
)
cursor.executemany('INSERT OR IGNORE INTO payments (client_code, client_name, date, amount, method, notes) VALUES (?,?,?,?,?,?)', mock_payments)

# ─────────────────────────────────────────────
# SCHEMA MIGRATIONS: extra_fields & is_special columns
# ─────────────────────────────────────────────
for table in ['clients', 'jobs', 'payments']:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cursor.fetchall()]
    if 'extra_fields' not in cols:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN extra_fields TEXT DEFAULT '{{}}'")
        print(f"  -> Added extra_fields to {table}")
    if table in ['jobs', 'payments'] and 'is_special' not in cols:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN is_special INTEGER DEFAULT 0")
        print(f"  -> Added is_special to {table}")

# ─────────────────────────────────────────────
# 5. APP_CONFIG table (key-value settings)
# ─────────────────────────────────────────────
cursor.execute('''CREATE TABLE IF NOT EXISTS app_config (
    key TEXT PRIMARY KEY,
    value TEXT
)''')

# Insert default config values if not exist
cursor.execute("INSERT OR IGNORE INTO app_config (key, value) VALUES (?, ?)", ('job_categories', 'ΑΠΕΝΤΟΜΩΣΗ (Pest Control)||ΜΥΟΚΤΟΝΙΑ (Rodent Control)||ΑΠΟΛΥΜΑΝΣΗ (Disinfection)'))
cursor.execute("INSERT OR IGNORE INTO app_config (key, value) VALUES (?, ?)", ('payment_methods', 'ΜΕΤΡΗΤΑ (Cash)||ΤΡΑΠΕΖΑ (Bank Transfer)||ΚΑΡΤΑ (Card)'))
cursor.execute("INSERT OR IGNORE INTO app_config (key, value) VALUES (?, ?)", ('crew_members', 'ΝΙΚΟΣ-ΓΙΩΡΓΟΣ||ΚΩΣΤΑΣ||ΝΙΚΟΣ'))

# ─────────────────────────────────────────────
# INDEXING OPTIMIZATION — high-speed binary indexes
# ─────────────────────────────────────────────
import os as _os
cursor.execute("DROP INDEX IF EXISTS idx_clients_search")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_code ON clients(code)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_phone ON clients(telephone)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_vat ON clients(vat_number)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_date ON jobs(date)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(date)")
print("  -> Created standalone indexes (code, name, phone, vat, jobs_date, payments_date)")

conn.commit()
conn.close()
print("SUCCESS: Boomer CRM database company_data.db generated cleanly.")
