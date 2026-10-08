import sqlite3
import os
import json
import csv
import shutil
from datetime import datetime, timedelta

# Automatically calculates the folder where the app is launched on Windows
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

db_path = os.path.join(BASE_DIR, "company_data.db")
DB_PATH = db_path # Keeps both casing variants synced safely
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

# ─────────────────────────────────────────────
# PHONETIC FOLDING — Latin→Greek + tone stripping
# ─────────────────────────────────────────────

def fold_text_phonetic(text):
    """ Normalizes Greek/Latin strings by folding accents, typos, and transliterating characters """
    if not text:
        return ""
    s = text.upper().strip()
    # Map common Latin phonetic profiles down to Greek matches
    latin_map = {'A':'Α','B':'Β','C':'Κ','D':'Δ','E':'Ε','F':'Φ','G':'Γ','H':'Η','I':'Ι',
                 'J':'ΤΖ','K':'Κ','L':'Λ','M':'Μ','N':'Ν','O':'Ο','P':'Π','Q':'Κ','R':'Ρ',
                 'S':'Σ','T':'Τ','U':'ΟΥ','V':'Β','W':'Β','X':'Ξ','Y':'Υ','Z':'Ζ'}
    s = "".join(latin_map.get(c, c) for c in s)
    # Strip tonal accents to tolerate spelling variants
    accents = {'Ά':'Α','Έ':'Ε','Ή':'Η','Ί':'Ι','Ό':'Ο','Ύ':'Υ','Ώ':'Ω','Ϊ':'Ι','Ϋ':'Υ',
               'ά':'α','έ':'ε','ή':'η','ί':'ι','ϊ':'ι','ΐ':'ι','ό':'ο','ύ':'υ','ϋ':'υ',
               'ΰ':'υ','ώ':'ω'}
    for k, v in accents.items():
        s = s.replace(k, v)
    # Fold out soft inner gammas for spelling tolerance
    s = s.replace("Γ", "")
    return s


def _build_search_text(code, name, telephone, telephone_2, vat_number, address, address_2, area):
    """Builds a pre-computed phonetic-folded search blob for a single client.
    This is stored in clients.search_text so SQL LIKE can pre-filter at C speed."""
    parts = [str(v or '') for v in [code, name, telephone, telephone_2, vat_number, address, address_2, area]]
    raw = ' | '.join(parts)
    folded = fold_text_phonetic(raw).lower()
    # Also include the raw lowercase version for exact-character matches
    return folded + ' | ' + raw.lower()


def ensure_schema_migrations():
    """ Safe schema migration helper using PRAGMA table_info checks. """
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        cursor = conn.cursor()
        for table in ['clients', 'jobs', 'payments']:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [r[1] for r in cursor.fetchall()]
            if 'extra_fields' not in cols:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN extra_fields TEXT DEFAULT '{{}}'")
            if table in ['jobs', 'payments'] and 'is_special' not in cols:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN is_special INTEGER DEFAULT 0")

        # --- SEARCH INDEX: add search_text column and populate it ---
        cursor.execute("PRAGMA table_info(clients)")
        client_cols = [r[1] for r in cursor.fetchall()]
        needs_rebuild = 'search_text' not in client_cols
        if needs_rebuild:
            cursor.execute("ALTER TABLE clients ADD COLUMN search_text TEXT DEFAULT ''")
            print("  -> Added search_text column to clients")

        # Check if any client is missing search_text (e.g. first run after migration)
        cursor.execute("SELECT COUNT(*) FROM clients WHERE search_text IS NULL OR search_text = ''")
        missing_count = cursor.fetchone()[0]
        if missing_count > 0:
            print(f"  -> Rebuilding search index for {missing_count} clients...")
            cursor.execute("SELECT code, name, telephone, telephone_2, vat_number, address, address_2, area FROM clients WHERE search_text IS NULL OR search_text = ''")
            rows = cursor.fetchall()
            for r in rows:
                st = _build_search_text(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7])
                cursor.execute("UPDATE clients SET search_text = ? WHERE code = ?", (st, r[0]))
            print(f"  -> Search index rebuilt for {len(rows)} clients")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Migration check error: {e}")

ensure_schema_migrations()

def get_db_connection():
    """Helper to ensure we always connect to the same file with WAL mode enabled."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA cache_size=-64000;")
        conn.execute("PRAGMA temp_store=MEMORY;")
    except Exception:
        pass
    return conn

def get_client_name_from_db(code):
    """Tries to find the client name in payments, then in the clients table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Try to find the name in the payments table
    cursor.execute("SELECT client_name FROM payments WHERE client_code = ? LIMIT 1", [code])
    row = cursor.fetchone()
    if row and row[0]:
        conn.close()
        return row[0]
        
    # 2. If not found, try a 'clients' table (if it exists)
    try:
        cursor.execute("SELECT name FROM clients WHERE code = ? LIMIT 1", [code])
        row = cursor.fetchone()
        if row and row[0]:
            conn.close()
            return row[0]
    except:
        pass # Table might not exist, proceed to fallback
        
    conn.close()
    return f"Client {code}" # Fallback



# ─────────────────────────────────────────────
# CORE BALANCE / STATS
# ─────────────────────────────────────────────

def get_client_balance(client_code, special_filter="ALL"):
    """ Calculates a client's outstanding balance — positive = debt, negative = credit.
        Applies special_filter symmetrically to both jobs and payments. """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    job_sql = "SELECT SUM(price_after_vat) FROM jobs WHERE client_code = ?"
    pay_sql = "SELECT SUM(amount) FROM payments WHERE client_code = ?"

    if special_filter == "SPECIAL":
        job_sql += " AND COALESCE(is_special, 0) = 1"
        pay_sql += " AND COALESCE(is_special, 0) = 1"
    elif special_filter == "NON_SPECIAL":
        job_sql += " AND COALESCE(is_special, 0) = 0"
        pay_sql += " AND COALESCE(is_special, 0) = 0"

    cursor.execute(job_sql, (client_code,))
    jobs_total = cursor.fetchone()[0] or 0.0
    cursor.execute(pay_sql, (client_code,))
    payments_total = cursor.fetchone()[0] or 0.0
    conn.close()
    return round(float(jobs_total) - float(payments_total), 2)


def register_new_client_record(payload_dict):
    """
    Creates a new client record with an auto-incrementing code (max+1, min 1001).
    payload_dict expects keys: name, telephone, address, area, vat_number,
    profession, notes, address_2, telephone_2.
    Returns the new client code on success, None on failure.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Auto-generate next code
    cursor.execute("SELECT MAX(CAST(code AS INTEGER)) FROM clients")
    max_code = cursor.fetchone()[0] or 1000
    new_code = str(max_code + 1)

    name = payload_dict.get("name", "Νέος Πελάτης").strip()
    telephone = payload_dict.get("telephone", "").strip()
    address = payload_dict.get("address", "").strip()
    area = payload_dict.get("area", "").strip()
    vat_number = payload_dict.get("vat_number", "").strip()
    profession = payload_dict.get("profession", "").strip()
    notes = payload_dict.get("notes", "").strip()
    address_2 = payload_dict.get("address_2", "").strip()
    telephone_2 = payload_dict.get("telephone_2", "").strip()

    search_text = _build_search_text(new_code, name, telephone, telephone_2, vat_number, address, address_2, area)

    try:
        cursor.execute("""
            INSERT INTO clients (code, name, address, area, telephone, vat_number,
                                 profession, notes, address_2, telephone_2, search_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_code, name, address, area, telephone, vat_number,
              profession, notes, address_2, telephone_2, search_text))
        conn.commit()
    except Exception:
        conn.close()
        return None
    conn.close()
    return new_code


def get_summary_stats(special_filter="ALL"):
    """ Returns aggregate dashboard statistics with symmetrical special_filter support. """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM clients")
    total_clients = cursor.fetchone()[0] or 0

    job_cond = ""
    pay_cond = ""
    if special_filter == "SPECIAL":
        job_cond = " WHERE COALESCE(is_special, 0) = 1"
        pay_cond = " WHERE COALESCE(is_special, 0) = 1"
    elif special_filter == "NON_SPECIAL":
        job_cond = " WHERE COALESCE(is_special, 0) = 0"
        pay_cond = " WHERE COALESCE(is_special, 0) = 0"

    cursor.execute(f"SELECT COUNT(*), COALESCE(SUM(price_after_vat), 0) FROM jobs{job_cond}")
    jr = cursor.fetchone()
    total_jobs = jr[0] or 0
    gross_receivables = jr[1] or 0.0

    cursor.execute(f"SELECT COALESCE(SUM(amount), 0) FROM payments{pay_cond}")
    gross_paid = cursor.fetchone()[0] or 0.0
    conn.close()
    return {
        "total_clients": total_clients, "total_jobs": total_jobs,
        "gross_receivables": round(gross_receivables, 2),
        "gross_paid": round(gross_paid, 2),
        "outstanding_debt": round(gross_receivables - gross_paid, 2)
    }


# ─────────────────────────────────────────────
# FUZZY SEARCH — phonetic + *-exact flag
# ─────────────────────────────────────────────

def fuzzy_search_clients(search_term):
    """ High-performance client search using pre-computed search_text column.
        SQL LIKE pre-filters at C speed, then Python ranks only the ~50 matches.
        Excludes notes and extra_fields from matching.
        Emphasizes prefix matches so names starting with the search term appear first. """
    is_exact = search_term.startswith("*")
    clean_term = search_term[1:].strip() if is_exact else search_term.strip()
    if not clean_term:
        return []

    folded_term = fold_text_phonetic(clean_term).lower()
    raw_term_lower = clean_term.lower()

    # --- SQL PRE-FILTER: uses the pre-computed search_text column ---
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT code, name, telephone, vat_number, area, profession, notes, address_2, telephone_2, address "
        "FROM clients WHERE search_text LIKE ? OR search_text LIKE ? LIMIT 200",
        (f'%{folded_term}%', f'%{raw_term_lower}%')
    )
    filtered_rows = cursor.fetchall()
    conn.close()

    scored_matches = []

    for r in filtered_rows:
        code = str(r[0] or "").strip()
        name = str(r[1] or "").strip()
        phone1 = str(r[2] or "").strip()
        vat = str(r[3] or "").strip()
        area = str(r[4] or "").strip()
        prof = str(r[5] or "").strip()
        notes = str(r[6] or "").strip()
        addr2 = str(r[7] or "").strip()
        phone2 = str(r[8] or "").strip()
        addr1 = str(r[9] or "").strip()

        folded_name = fold_text_phonetic(name).lower()
        folded_code = fold_text_phonetic(code).lower()

        # Determine Match Rank (Lower integer = Higher priority)
        rank = 99
        if folded_code == folded_term or code == clean_term:
            rank = 0
        elif folded_name.startswith(folded_term) or name.lower().startswith(raw_term_lower):
            rank = 1
        else:
            words = folded_name.split()
            if any(w.startswith(folded_term) for w in words):
                rank = 2
            else:
                folded_phone1 = fold_text_phonetic(phone1).lower()
                folded_phone2 = fold_text_phonetic(phone2).lower()
                folded_vat = fold_text_phonetic(vat).lower()
                folded_area = fold_text_phonetic(area).lower()
                folded_addr1 = fold_text_phonetic(addr1).lower()
                folded_addr2 = fold_text_phonetic(addr2).lower()
                if (folded_code.startswith(folded_term) or
                    folded_phone1.startswith(folded_term) or
                    folded_phone2.startswith(folded_term) or
                    folded_vat.startswith(folded_term) or
                    folded_area.startswith(folded_term) or
                    folded_addr1.startswith(folded_term) or
                    folded_addr2.startswith(folded_term)):
                    rank = 3
                else:
                    rank = 4

        scored_matches.append((
            rank,
            name.lower(),
            code,
            {
                "code": code, "name": name, "telephone": phone1,
                "vat": vat, "area": area, "profession": prof,
                "notes": notes, "address_2": addr2, "telephone_2": phone2
            }
        ))

    scored_matches.sort(key=lambda x: (x[0], x[1], x[2]))

    # Batch-compute balances in a single SQL query for top 15 (eliminates 15 DB round-trips)
    top_items = scored_matches[:15]
    if not top_items:
        return []
    codes = [item[2] for item in top_items]
    placeholders = ','.join('?' * len(codes))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT client_code, COALESCE(SUM(price_after_vat), 0) FROM jobs WHERE client_code IN ({placeholders}) GROUP BY client_code", codes)
    jobs_map = dict(cursor.fetchall())
    cursor.execute(f"SELECT client_code, COALESCE(SUM(amount), 0) FROM payments WHERE client_code IN ({placeholders}) GROUP BY client_code", codes)
    pays_map = dict(cursor.fetchall())
    conn.close()

    results = []
    for item in top_items:
        cdata = item[3]
        cdata["balance_owed"] = round(float(jobs_map.get(cdata["code"], 0)) - float(pays_map.get(cdata["code"], 0)), 2)
        results.append(cdata)

    return results


# ─────────────────────────────────────────────
# CLIENT JOBS / PAYMENTS — with extra_fields
# ─────────────────────────────────────────────

def get_client_jobs(client_code):
    """ Fetches all jobs for a specific client, bringing the client name with it. """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.*, c.name as client_name 
        FROM jobs j
        LEFT JOIN clients c ON j.client_code = c.code
        WHERE j.client_code = ? 
        ORDER BY j.date DESC, j.time_slot DESC
    """, (client_code,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_client_payments(client_code):
    """ Fetches all payment records for a client, including extra_fields JSON and is_special flag. """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT date, amount, method, notes, payment_id, extra_fields, COALESCE(is_special, 0) "
        "FROM payments WHERE client_code = ? ORDER BY date DESC",
        (client_code,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{
        "date": r[0], "amount": r[1], "method": r[2], "notes": r[3],
        "payment_id": r[4], "extra_fields": json.loads(r[5] or "{}"),
        "is_special": r[6]
    } for r in rows]


# ─────────────────────────────────────────────
# PRUNE EMPTY FIELDS — prevent empty-string reappearance
# ─────────────────────────────────────────────

def prune_empty_fields(payload):
    """
    Strips keys with empty string or None values from a payload dict.
    This prevents deleted/cleared fields from reappearing as blank
    entries inside edit modals and timeline views.
    Returns a cleaned dict with only non-empty values.
    """
    return {k: v for k, v in payload.items() if v != "" and v is not None}


def _v_or_none(val):
    """Returns val if non-empty string, else None (SQL NULL)."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


# ─────────────────────────────────────────────
# UPDATE PAYLOADS — with JSON extra_fields
# ─────────────────────────────────────────────

def update_job_record_payload(job_id, cat1, cat2, crew, invoice, price, date_str, notes, extra_fields_dict, is_special=0):
    """ Updates a job record with new field values, JSON extra_fields, and is_special. """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    clean_price = clean_numeric_input_string(str(price))
    cursor.execute("""
        UPDATE jobs
        SET category_1=?, category_2=?, crew=?, invoice_number=?,
            price_after_vat=?, date=?, notes=?, extra_fields=?, is_special=?
        WHERE job_id=?
    """, (_v_or_none(cat1), _v_or_none(cat2), _v_or_none(crew),
          _v_or_none(invoice), float(clean_price), _v_or_none(date_str),
          _v_or_none(notes), json.dumps(extra_fields_dict), int(is_special or 0), job_id))
    conn.commit()
    conn.close()


def update_payment_record_payload(payment_id, amount, method, date_str, notes, extra_fields_dict, job_category="", subcategory="", is_special=0):
    """ Updates a payment record with new field values, JSON extra_fields, categories, and is_special. """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN job_category TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN subcategory TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    clean_amount = clean_numeric_input_string(str(amount))
    cursor.execute("""
        UPDATE payments
        SET amount=?, method=?, date=?, notes=?, extra_fields=?, job_category=?, subcategory=?, is_special=?
        WHERE payment_id=?
    """, (float(clean_amount), _v_or_none(method), _v_or_none(date_str),
          _v_or_none(notes), json.dumps(extra_fields_dict), 
          _v_or_none(job_category), _v_or_none(subcategory), int(is_special or 0), payment_id))
    conn.commit()
    conn.close()


def update_client_record_payload(client_code, name, telephone, vat, area, profession, notes, address_2, telephone_2, extra_fields_dict):
    """ Updates a client record with new field values, JSON extra_fields, and refreshes search_text. """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Fetch current address for search_text rebuild (address is not passed to this function)
    cursor.execute("SELECT address FROM clients WHERE code = ?", (client_code,))
    addr_row = cursor.fetchone()
    address = addr_row[0] if addr_row else ''
    search_text = _build_search_text(client_code, name, telephone, telephone_2, vat, address, address_2, area)
    cursor.execute("""
        UPDATE clients
        SET name=?, telephone=?, vat_number=?, area=?, profession=?,
            notes=?, address_2=?, telephone_2=?, extra_fields=?, search_text=?
        WHERE code=?
    """, (_v_or_none(name), _v_or_none(telephone), _v_or_none(vat),
          _v_or_none(area), _v_or_none(profession), _v_or_none(notes),
          _v_or_none(address_2), _v_or_none(telephone_2),
          json.dumps(extra_fields_dict), search_text, client_code))
    conn.commit()
    conn.close()


def update_client_record(payload):
    """
    Dict-based wrapper around update_client_record_payload.
    Accepts a payload dict with keys: code, name, phone, phone_2,
    address, address_2, area, vat, profession, extra_fields_json.
    Returns True on success, False on error.
    """
    try:
        extra_fields = {}
        raw_extras = payload.get('extra_fields_json', {})
        if isinstance(raw_extras, dict):
            extra_fields = raw_extras
        elif isinstance(raw_extras, str):
            import json as _j
            try:
                extra_fields = _j.loads(raw_extras)
            except _j.JSONDecodeError:
                extra_fields = {}

        update_client_record_payload(
            payload.get('code', ''),
            payload.get('name', ''),
            payload.get('phone', ''),
            payload.get('vat', ''),
            payload.get('area', ''),
            payload.get('profession', ''),
            payload.get('notes', ''),
            payload.get('address_2', ''),
            payload.get('phone_2', ''),
            extra_fields
        )
        return True
    except Exception as e:
        print(f"Error in update_client_record: {e}")
        return False


def update_job_record(payload):
    """
    Dict-based wrapper around update_job_record_payload.
    Accepts payload dict with keys: job_id, category_1, category_2, crew,
    invoice_number, price_after_vat, date, time_slot, notes, extra_fields_json, is_special.
    Returns True on success, False on error.
    """
    try:
        extra = {}
        raw_extras = payload.get('extra_fields_json', {})
        if isinstance(raw_extras, dict):
            extra = raw_extras
        elif isinstance(raw_extras, str):
            import json as _j
            try:
                extra = _j.loads(raw_extras)
            except _j.JSONDecodeError:
                extra = {}

        update_job_record_payload(
            payload.get('job_id'),
            payload.get('category_1', ''),
            payload.get('category_2', ''),
            payload.get('crew', ''),
            payload.get('invoice_number', ''),
            payload.get('price_after_vat', '0'),
            payload.get('date', ''),
            payload.get('notes', ''),
            extra,
            payload.get('is_special', 0)
        )
        return True
    except Exception as e:
        print(f"Error in update_job_record: {e}")
        return False


def update_payment_record(payload):
    """ Wrapper to unpack the payload dictionary safely into the database update handler. """
    try:
        pid = payload.get('payment_id')
        amt = payload.get('amount')
        meth = payload.get('method')
        dt = payload.get('date')
        nts = payload.get('notes')
        cat = payload.get('job_category', '')
        subcat = payload.get('subcategory', '')
        extra = payload.get('extra_fields_json', {})
        is_sp = payload.get('is_special', 0)

        update_payment_record_payload(
            payment_id=pid,
            amount=amt,
            method=meth,
            date_str=dt,
            notes=nts,
            extra_fields_dict=extra,
            job_category=cat,
            subcategory=subcat,
            is_special=is_sp
        )
        return True
    except Exception as e:
        print(f"Error updating payment record: {e}")
        return False


# ─────────────────────────────────────────────
# LEGACY HELPERS (unchanged — referenced by GUI)
# ─────────────────────────────────────────────

def get_all_clients_summary():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT code, name FROM clients ORDER BY name LIMIT 1000")
    rows = cursor.fetchall()
    conn.close()
    return [{"code": r[0], "name": r[1]} for r in rows]

def verify_and_fetch_client(client_code):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT code, name, address, telephone, vat_number, area, profession, notes, "
        "address_2, telephone_2, extra_fields FROM clients WHERE code = ?",
        (client_code,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "code": row[0], "name": row[1], "address": row[2], "telephone": row[3],
        "vat": row[4], "area": row[5], "profession": row[6],
        "notes": row[7], "address_2": row[8], "telephone_2": row[9],
        "extra_fields": json.loads(row[10] or "{}"),
        "balance_owed": get_client_balance(row[0])
    }

def get_all_recorded_payments():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.date, p.amount, p.method, p.notes,
               COALESCE(c.name, 'Άγνωστος Πελάτης') AS client_name,
               p.client_code, p.payment_id
        FROM payments p
        LEFT JOIN clients c ON p.client_code = c.code
        ORDER BY p.date DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"date": r[0], "amount": r[1], "method": r[2], "notes": r[3],
             "client_name": r[4], "client_code": r[5], "payment_id": r[6]} for r in rows]


def get_payments_with_client_data(search_term="", sort_by="date"):
    """
    Fetches payments with LEFT JOIN for client name.
    Supports multi-word fuzzy search (each word matched independently) and sort by date or amount.
    Now safely extracts job_category, subcategory, and is_special for UI components.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN job_category TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN subcategory TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    query = """
        SELECT p.payment_id, p.client_code, p.amount, p.date,
               p.method, p.notes, p.job_category, p.subcategory,
               COALESCE(p.is_special, 0) AS is_special,
               COALESCE(c.name, 'Άγνωστος Πελάτης') AS client_name
        FROM payments p
        LEFT JOIN clients c ON p.client_code = c.code
        WHERE 1=1
    """
    params = []

    if search_term and search_term.strip() and search_term != "ALL":
        for word in search_term.strip().split():
            query += " AND (c.name LIKE ? OR p.client_code LIKE ?)"
            params.extend([f"%{word}%", f"%{word}%"])

    if sort_by == "amount":
        query += " ORDER BY p.amount DESC"
    else:
        query += " ORDER BY p.date DESC"

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_new_payment(payload):
    """Inserts a new payment record from a payload dict."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO payments (client_code, client_name, date, amount, method, notes, is_special)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.get("client_code", ""),
            payload.get("client_name", ""),
            payload.get("date", ""),
            float(clean_numeric_input_string(str(payload.get("amount", "0")))),
            payload.get("method", ""),
            payload.get("notes", ""),
            int(payload.get("is_special", 0) or 0),
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding payment: {e}")
        return False

def record_new_payment(client_code, client_name, date_str, amount, method, notes, is_special=0):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    clean_amount = clean_numeric_input_string(str(amount))
    cursor.execute(
        "INSERT INTO payments (client_code, client_name, date, amount, method, notes, is_special) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (client_code, client_name, date_str, float(clean_amount), method, notes, int(is_special or 0))
    )
    conn.commit()
    conn.close()
    return True

def record_payment(client_code, amount, method, date_str, notes="", is_special=0):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO payments (client_code, amount, method, date, notes, is_special) VALUES (?, ?, ?, ?, ?, ?)",
        (client_code, amount, method, date_str, notes, int(is_special or 0))
    )
    conn.commit()
    conn.close()
    return True

def search_jobs_by_date_range(start_date, end_date):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.job_id, j.time_slot, j.date, j.category_1, j.category_2, j.crew,
               j.invoice_number, j.price_after_vat, j.notes, j.client_code,
               COALESCE(j.is_special, 0) AS is_special,
               COALESCE(c.name, 'Άγνωστος Πελάτης') AS client_name
        FROM jobs j
        LEFT JOIN clients c ON c.code = j.client_code
        WHERE j.date BETWEEN ? AND ? ORDER BY j.date DESC, j.time_slot ASC
    """, (start_date, end_date))
    rows = cursor.fetchall()
    conn.close()
    return [{"job_id": r[0], "time": r[1], "date": r[2], "cat1": r[3], "cat2": r[4],
             "crew": r[5], "invoice": r[6], "price_after": r[7], "notes": r[8],
             "client_code": r[9], "is_special": r[10], "client_name": r[11]} for r in rows]


def get_jobs_for_calendar(client_code="ALL", date_from=None, date_to=None):
    """Fetches jobs for calendar view. Defaults to ALL clients, filters by date range if provided.
    Uses LEFT JOIN to ensure client names always resolve, even for deleted clients."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = """
        SELECT j.job_id, j.client_code, j.category_1, j.category_2, j.crew,
               j.date, j.time_slot, j.invoice_number, j.price_before_vat,
               j.vat_amount, j.price_after_vat, j.notes, j.extra_fields,
               COALESCE(j.is_special, 0) AS is_special,
               COALESCE(c.name, 'Άγνωστος Πελάτης') AS client_name
        FROM jobs j
        LEFT JOIN clients c ON j.client_code = c.code
    """
    params = []
    conditions = []
    if client_code != "ALL":
        conditions.append("j.client_code = ?")
        params.append(client_code)
    if date_from:
        conditions.append("j.date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("j.date <= ?")
        params.append(date_to)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY j.date DESC, j.time_slot ASC"

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [{"job_id": r[0], "client_code": r[1], "cat1": r[2], "cat2": r[3],
             "crew": r[4], "date": r[5], "time_slot": r[6], "invoice": r[7],
             "price_before_vat": r[8], "vat_amount": r[9], "price_after_vat": r[10],
             "notes": r[11], "extra_fields": r[12] or "{}", "is_special": r[13],
             "client_name": r[14], "price_after": r[10]} for r in rows]

def record_new_job(client_code, category_1, category_2, crew, invoice_number, price_after_vat, date_str, notes="", is_special=0):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    clean_price = clean_numeric_input_string(str(price_after_vat))
    cursor.execute(
        "INSERT INTO jobs (client_code, category_1, category_2, crew, invoice_number, price_after_vat, date, notes, is_special) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (client_code, category_1, category_2, crew, invoice_number, float(clean_price), date_str, notes, int(is_special or 0))
    )
    conn.commit()
    conn.close()
    return True

def get_jobs_by_exact_date(date_str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.job_id, j.client_code,
               COALESCE(c.name, 'Άγνωστος Πελάτης') AS client_name,
               j.category_1, j.category_2,
               j.crew, j.time_slot, j.invoice_number, j.price_after_vat, j.notes,
               COALESCE(j.is_special, 0) AS is_special
        FROM jobs j
        LEFT JOIN clients c ON j.client_code = c.code
        WHERE j.date = ? ORDER BY j.time_slot ASC
    """, (date_str,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "client_code": r[1], "client_name": r[2],
             "cat1": r[3], "cat2": r[4], "crew": r[5], "time": r[6],
             "invoice": r[7], "price_after": r[8], "notes": r[9], "is_special": r[10]} for r in rows]

def record_new_job_card(client_code, cat1, cat2, crew, date_str, time_slot, invoice, price_before, vat_amount, price_after, notes, is_special=0):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    clean_before = clean_numeric_input_string(str(price_before))
    clean_vat = clean_numeric_input_string(str(vat_amount))
    clean_after = clean_numeric_input_string(str(price_after))
    cursor.execute(
        "INSERT INTO jobs (client_code, category_1, category_2, crew, date, time_slot, "
        "invoice_number, price_before_vat, vat_amount, price_after_vat, notes, is_special) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (client_code, cat1, cat2, crew, date_str, time_slot,
         invoice, float(clean_before), float(clean_vat), float(clean_after), notes, int(is_special or 0))
    )
    conn.commit()
    conn.close()
    return True


def add_new_job(payload):
    """Inserts a new job record from a payload dict. Returns True on success."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        price_after = float(clean_numeric_input_string(str(payload.get("price_after_vat", "0"))))
        vat_rate = float(clean_numeric_input_string(str(payload.get("vat_pct", "24")))) / 100.0
        price_before = round(price_after / (1 + vat_rate), 2) if price_after > 0 else 0.0
        vat_amount = round(price_after - price_before, 2)

        cursor.execute("""
            INSERT INTO jobs (client_code, category_1, category_2, crew, date, time_slot,
                             invoice_number, price_before_vat, vat_amount, price_after_vat, notes, is_special)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.get("client_code", ""),
            payload.get("job_type", ""),
            payload.get("job_subtype", ""),
            payload.get("crew_list", ""),
            payload.get("date", ""),
            payload.get("time_logged", ""),
            payload.get("invoice", ""),
            price_before, vat_amount, price_after,
            payload.get("notes", ""),
            int(payload.get("is_special", 0) or 0),
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding job: {e}")
        return False


def get_client_by_code(client_code):
    """Fetches a single client by code, returns dict with column names via dict(zip(...))."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM clients WHERE code = ?", (client_code,))
        row = cursor.fetchone()
        if row:
            columns = [d[0] for d in cursor.description]
            result = dict(zip(columns, row))
            conn.close()
            return result
        conn.close()
        return None
    except Exception as e:
        print(f"Error fetching client: {e}")
        conn.close()
        return None


def get_job_by_id(job_id):
    """Fetches a single job record by its primary key, with client name via LEFT JOIN.
    Returns dict via dict(zip(...)) for robustness."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT j.job_id, j.client_code, j.category_1, j.category_2, j.crew,
                   j.date, j.time_slot, j.invoice_number, j.price_before_vat,
                   j.vat_amount, j.price_after_vat, j.notes, j.extra_fields,
                   COALESCE(j.is_special, 0) AS is_special,
                   COALESCE(c.name, 'Άγνωστος Πελάτης') AS client_name
            FROM jobs j
            LEFT JOIN clients c ON c.code = j.client_code
            WHERE j.job_id = ?
        """, (job_id,))
        row = cursor.fetchone()
        if row:
            columns = [d[0] for d in cursor.description]
            result = dict(zip(columns, row))
            result["cat1"] = result.get("category_1", "")
            result["cat2"] = result.get("category_2", "")
            result["invoice"] = result.get("invoice_number", "")
            result["price_after"] = result.get("price_after_vat", 0)
            result["price"] = result.get("price_after_vat", 0)
            result["time"] = result.get("time_slot", "")
            result["extra_fields"] = json.loads(result.get("extra_fields") or "{}")
            result["is_special"] = result.get("is_special", 0)
            conn.close()
            return result
        conn.close()
        return None
    except Exception as e:
        print(f"Error fetching job: {e}")
        conn.close()
        return None


def get_payment_by_id(payment_id):
    """Fetches a single payment record by ID, dynamically mapping all database columns."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT *, COALESCE(is_special, 0) AS is_special FROM payments WHERE payment_id = ?", (payment_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ─────────────────────────────────────────────
# ANALYTICS
# ─────────────────────────────────────────────

def get_revenue_by_category(special_filter="ALL"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    where = ""
    if special_filter == "SPECIAL":
        where = " WHERE COALESCE(is_special, 0) = 1"
    elif special_filter == "NON_SPECIAL":
        where = " WHERE COALESCE(is_special, 0) = 0"

    cursor.execute(
        f"SELECT COALESCE(category_1, 'Uncategorized'), SUM(price_after_vat), COUNT(*) "
        f"FROM jobs{where} GROUP BY category_1 ORDER BY SUM(price_after_vat) DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"category": r[0], "revenue": round(r[1] or 0, 2), "count": r[2]} for r in rows]

def get_monthly_aggregation(limit=12, special_filter="ALL"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    job_where = ""
    pay_where = ""
    if special_filter == "SPECIAL":
        job_where = " WHERE COALESCE(is_special, 0) = 1"
        pay_where = " WHERE COALESCE(is_special, 0) = 1"
    elif special_filter == "NON_SPECIAL":
        job_where = " WHERE COALESCE(is_special, 0) = 0"
        pay_where = " WHERE COALESCE(is_special, 0) = 0"

    cursor.execute(
        f"SELECT strftime('%Y-%m', date) AS month, COUNT(*), COALESCE(SUM(price_after_vat), 0) "
        f"FROM jobs{job_where} GROUP BY month ORDER BY month DESC LIMIT ?", (limit,))
    job_rows = cursor.fetchall()
    cursor.execute(
        f"SELECT strftime('%Y-%m', date) AS month, COUNT(*), COALESCE(SUM(amount), 0) "
        f"FROM payments{pay_where} GROUP BY month ORDER BY month DESC LIMIT ?", (limit,))
    pay_rows = cursor.fetchall()
    conn.close()
    months = {}
    for r in job_rows:
        months[r[0]] = {"month": r[0], "jobs": r[1], "job_revenue": round(r[2], 2), "payments": 0, "payment_total": 0.0}
    for r in pay_rows:
        if r[0] in months:
            months[r[0]]["payments"] = r[1]
            months[r[0]]["payment_total"] = round(r[2], 2)
        else:
            months[r[0]] = {"month": r[0], "jobs": 0, "job_revenue": 0.0, "payments": r[1], "payment_total": round(r[2], 2)}
    return sorted(months.values(), key=lambda m: m["month"], reverse=True)

def get_monthly_financial_summary(special_filter="ALL"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    job_where = ""
    pay_where = ""
    if special_filter == "SPECIAL":
        job_where = " WHERE COALESCE(is_special, 0) = 1"
        pay_where = " WHERE COALESCE(is_special, 0) = 1"
    elif special_filter == "NON_SPECIAL":
        job_where = " WHERE COALESCE(is_special, 0) = 0"
        pay_where = " WHERE COALESCE(is_special, 0) = 0"

    cursor.execute(
        f"SELECT strftime('%Y-%m', date) AS month, SUM(price_before_vat), SUM(vat_amount) "
        f"FROM jobs{job_where} GROUP BY month ORDER BY month DESC")
    job_rows = {r[0]: (r[1] or 0.0, r[2] or 0.0) for r in cursor.fetchall() if r[0] is not None}
    cursor.execute(
        f"SELECT strftime('%Y-%m', date) AS month, SUM(amount) "
        f"FROM payments{pay_where} GROUP BY month ORDER BY month DESC")
    pay_rows = {r[0]: (r[1] or 0.0) for r in cursor.fetchall() if r[0] is not None}
    conn.close()
    all_months = sorted(set(list(job_rows.keys()) + list(pay_rows.keys())), reverse=True)
    return [{"month": m, "net_sales": round(job_rows.get(m, (0.0, 0.0))[0], 2),
             "vat_collected": round(job_rows.get(m, (0.0, 0.0))[1], 2),
             "collected_cash": round(pay_rows.get(m, 0.0), 2)} for m in all_months]

def get_stagnant_debt_accounts(months_threshold=3):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.code, c.name, c.telephone, c.area,
               COALESCE((SELECT SUM(price_after_vat) FROM jobs WHERE client_code = c.code), 0)
               - COALESCE((SELECT SUM(amount) FROM payments WHERE client_code = c.code), 0) AS balance,
               (SELECT MAX(date) FROM payments WHERE client_code = c.code) AS last_payment
        FROM clients c
        HAVING balance > 0 AND (last_payment IS NULL OR last_payment < date('now', ?))
        ORDER BY balance DESC
    """, (f'-{months_threshold} months',))
    rows = cursor.fetchall()
    conn.close()
    return [{"code": r[0], "name": r[1], "telephone": r[2], "area": r[3],
             "balance": round(r[4], 2), "last_payment": r[5]} for r in rows]

def get_stagnant_debtors(threshold_months=3):
    import datetime as dt
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.code, c.name, c.telephone,
               (SELECT SUM(price_after_vat) FROM jobs WHERE client_code = c.code),
               (SELECT SUM(amount) FROM payments WHERE client_code = c.code),
               (SELECT MAX(date) FROM payments WHERE client_code = c.code)
        FROM clients c
    """)
    rows = cursor.fetchall()
    conn.close()
    today = dt.date.today()
    stagnant = []
    for r in rows:
        code, name, phone, charges, payments, last_pay = r
        charges = charges or 0.0
        payments = payments or 0.0
        bal = round(charges - payments, 2)
        if bal <= 0:
            continue
        is_stagnant = False
        display = last_pay or "NEVER PAID"
        if not last_pay:
            is_stagnant = True
        else:
            try:
                delta = (today - dt.datetime.strptime(last_pay, "%Y-%m-%d").date()).days
                if (delta / 30.4) >= float(threshold_months):
                    is_stagnant = True
            except ValueError:
                is_stagnant = True
                display = "INVALID DATE"
        if is_stagnant:
            stagnant.append({"code": code, "name": name, "phone": phone,
                             "balance": bal, "last_payment": display})
    return sorted(stagnant, key=lambda x: x["balance"], reverse=True)


# ─────────────────────────────────────────────
# BACKUP / EXPORT — safe, no pandas, no shutil on open DB
# ─────────────────────────────────────────────

def ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def get_table_list():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cursor.fetchall()]
    conn.close()
    return tables


def list_existing_backups():
    ensure_backup_dir()
    return sorted([os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR)], reverse=True)


def execute_safe_system_export():
    """
    Performs a safe, no-pandas backup and export.
    Consolidates data files inside a visible folder structured as:
    backups/BACKUP - DD-MM-YY - HH-MM-SS/
    """
    ensure_backup_dir()
    from datetime import datetime
    # Enforce precise naming layout template requested
    ts_folder = datetime.now().strftime("%d-%m-%y - %H-%M-%S")
    folder_name = f"BACKUP - {ts_folder}"
    target_folder = os.path.join(BACKUP_DIR, folder_name)
    os.makedirs(target_folder, exist_ok=True)

    results = {"timestamp": ts_folder, "backup_dir": target_folder, "files": []}

    # ── OUTPUT 1: Database Clone inside folder ──
    db_backup_path = os.path.join(target_folder, f"company_data.db")
    src_conn = sqlite3.connect(db_path)
    dst_conn = sqlite3.connect(db_backup_path)
    src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    results["database_backup"] = db_backup_path
    results["files"].append(db_backup_path)

    # ── OUTPUT 2, 3, 4: Standalone Greek-safe CSV logs ──
    csv_configs = [
        ("clients", "all_clients",
         ["code", "name", "address", "area", "telephone",
          "vat_number", "profession", "notes", "address_2",
          "telephone_2", "extra_fields"]),
        ("jobs", "all_jobs",
         ["job_id", "client_code", "category_1", "category_2", "crew",
          "date", "time_slot", "invoice_number", "price_before_vat",
          "vat_amount", "price_after_vat", "notes", "is_special", "extra_fields"]),
        ("payments", "all_payments",
         ["payment_id", "client_code", "client_name", "date", "amount",
          "method", "notes", "is_special", "extra_fields"]),
    ]

    read_conn = sqlite3.connect(db_path)
    read_conn.row_factory = sqlite3.Row
    read_cursor = read_conn.cursor()

    for table_name, file_name, columns in csv_configs:
        csv_path = os.path.join(target_folder, f"{file_name}.csv")
        read_cursor.execute(f"SELECT {', '.join(columns)} FROM {table_name} ORDER BY rowid")
        rows = read_cursor.fetchall()
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for row in rows:
                writer.writerow([row[col] if row[col] is not None else "" for col in columns])
        results["files"].append(csv_path)
        results[f"csv_{table_name}"] = csv_path

    read_conn.close()
    return results


def get_available_folder_backups():
    """Scans the backups directory and returns names of folders starting with BACKUP -"""
    import os
    if not os.path.exists(BACKUP_DIR):
        return []
    folders = []
    for d in os.listdir(BACKUP_DIR):
        path = os.path.join(BACKUP_DIR, d)
        if os.path.isdir(path) and d.startswith("BACKUP -"):
            folders.append(d)
    return sorted(folders, reverse=True)


def restore_database_hot_swap(source_db_file_path):
    """
    Safely unplugs active open database connections, sandboxes the live DB file 
    by renaming it to .old, and executes a clean copy write restore operation.
    """
    import os
    import shutil
    import sqlite3
    
    if not os.path.exists(source_db_file_path):
        raise FileNotFoundError(f"Source file missing: {source_db_file_path}")
        
    # 1. Unplug active thread streams by closing out connection pools
    if 'conn' in globals():
        try: globals()['conn'].close()
        except: pass
        
    # 2. Sandbox active file to avoid triggering a Windows file system access lock error
    if os.path.exists(db_path):
        backup_corrupt_path = db_path + ".old"
        if os.path.exists(backup_corrupt_path):
            try: os.remove(backup_corrupt_path)
            except: pass
        os.rename(db_path, backup_corrupt_path)
        
    # 3. Copy target database checkout straight into execution runtime root
    shutil.copy2(source_db_file_path, db_path)
    
    # 4. Re-verify connectivity safety pass
    test_conn = sqlite3.connect(db_path)
    test_conn.close()
    return True


# ─────────────────────────────────────────────
# DELETE HOOKS — safe row removal
# ─────────────────────────────────────────────

def delete_client_record(client_code):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE code = ?", (client_code,))
    conn.commit()
    conn.close()

def delete_job_record(job_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()


def delete_job_by_id(job_id):
    """Parameterized delete primitive with try/except safety. Returns True if a row was deleted."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    except Exception as e:
        print(f"SQL Delete Error: {e}")
        return False

def delete_payment_record(payment_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM payments WHERE payment_id = ?", (payment_id,))
    conn.commit()
    conn.close()


def wipe_all_application_records():
    """
    Master utility — securely purges ALL data from clients, jobs, and payments
    tables, then VACUUMs to reclaim space and reset structural indexes.
    Returns a dict with deletion counts per table.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    counts = {}
    for table in ["payments", "jobs", "clients"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        before = cursor.fetchone()[0]
        cursor.execute(f"DELETE FROM {table}")
        counts[table] = before
    conn.commit()
    cursor.execute("VACUUM")
    conn.commit()
    conn.close()
    return counts


# ─────────────────────────────────────────────
# INPUT SANITIZER — numeric string cleaning
# ─────────────────────────────────────────────

def clean_numeric_input_string(value_str):
    """
    Sanitizes localized numeric input strings for Python float() consumption.
    Handles:
      - Currency symbols (€, $, £, etc.)
      - Whitespace padding
      - European comma-as-decimal format (2.400,50 → 2400.50)
      - Trailing non-numeric junk ("2400.50abc" → "2400.50")
      - Leading non-numeric junk ("~2400" → "2400")
    Returns a clean string safe for float(), or "0" if nothing parseable.
    """
    if not value_str:
        return "0"
    s = value_str.strip()
    # Remove common currency symbols and letter suffixes
    import re
    s = re.sub(r'[€$£¥₽₩₨₪₫฿₣₤₧₶₷₸₹₺₼₾₿\s]', '', s)
    # Detect European format: has exactly one comma and at least one dot before it
    # e.g. "2.400,50" — dot is thousand separator, comma is decimal
    if "," in s:
        # Remove dots (thousand separators), then replace comma with dot
        s = s.replace(".", "").replace(",", ".")
    # Strip any trailing non-numeric characters except dot
    # Keep only digits, one dot, and optional leading minus
    sign = ""
    if s.startswith("-"):
        sign = "-"
        s = s[1:]
    cleaned = ""
    dot_seen = False
    for ch in s:
        if ch.isdigit():
            cleaned += ch
        elif ch == '.' and not dot_seen:
            cleaned += ch
            dot_seen = True
    if not cleaned:
        return "0"
    return sign + cleaned


def format_date_display(date_str):
    """
    Converts YYYY-MM-DD to DD/MM/YY for display in UI.
    Returns original string if parsing fails.
    """
    if not date_str or len(date_str) < 10:
        return date_str or ""
    try:
        parts = date_str.split("-")
        if len(parts) == 3 and len(parts[0]) == 4:
            yy = parts[0][2:]  # last 2 digits of year
            return f"{parts[2]}/{parts[1]}/{yy}"
        return date_str
    except (ValueError, IndexError):
        return date_str


# ─────────────────────────────────────────────
# SCHEMA MIGRATION — ON DELETE CASCADE
# ─────────────────────────────────────────────

def migrate_add_cascade_constraints():
    """
    Rebuilds jobs and payments tables with FOREIGN KEY ... ON DELETE CASCADE
    so that deleting a client automatically cascades to orphaned rows.
    Uses the standard SQLite pattern: create-new, copy, drop-old, rename.
    Safe to call multiple times — detects whether CASCADE is already present.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if CASCADE is already active on jobs table
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='jobs'")
    jobs_sql = (cursor.fetchone() or [None])[0] or ""
    if "ON DELETE CASCADE" in jobs_sql.upper():
        conn.close()
        return {"jobs": False, "payments": False}

    # ── Migrate jobs table ──
    cursor.execute("DROP TABLE IF EXISTS jobs_new")
    cursor.execute("CREATE TABLE IF NOT EXISTS jobs_new ("
        "job_id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "client_code TEXT, "
        "category_1 TEXT, "
        "category_2 TEXT, "
        "crew TEXT, "
        "date TEXT, "
        "time_slot TEXT, "
        "invoice_number TEXT, "
        "price_before_vat REAL, "
        "vat_amount REAL, "
        "price_after_vat REAL, "
        "notes TEXT, "
        "extra_fields TEXT DEFAULT '{}', "
        "FOREIGN KEY(client_code) REFERENCES clients(code) ON DELETE CASCADE"
    ")")
    cursor.execute("INSERT INTO jobs_new SELECT * FROM jobs")
    cursor.execute("DROP TABLE jobs")
    cursor.execute("ALTER TABLE jobs_new RENAME TO jobs")

    # ── Migrate payments table ──
    cursor.execute("DROP TABLE IF EXISTS payments_new")
    cursor.execute("CREATE TABLE IF NOT EXISTS payments_new ("
        "payment_id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "client_code TEXT, "
        "client_name TEXT, "
        "date TEXT, "
        "amount REAL, "
        "method TEXT, "
        "notes TEXT, "
        "extra_fields TEXT DEFAULT '{}', "
        "FOREIGN KEY(client_code) REFERENCES clients(code) ON DELETE CASCADE"
    ")")
    cursor.execute("INSERT INTO payments_new SELECT * FROM payments")
    cursor.execute("DROP TABLE payments")
    cursor.execute("ALTER TABLE payments_new RENAME TO payments")

    conn.commit()
    conn.close()
    return {"jobs": True, "payments": True}


# ─────────────────────────────────────────────
# APP CONFIG — key/value persistence
# ─────────────────────────────────────────────

def get_config_value(key, default=''):
    """Reads a value from the app_config table. Returns default if key missing."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS app_config "
        "(key TEXT PRIMARY KEY, value TEXT)"
    )
    cursor.execute("SELECT value FROM app_config WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default


def set_config_value(key, value):
    """Upserts a key/value pair into app_config. Returns True."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS app_config "
        "(key TEXT PRIMARY KEY, value TEXT)"
    )
    cursor.execute(
        "INSERT INTO app_config (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value)
    )
    conn.commit()
    conn.close()
    return True


def get_config_list(key):
    """Gets a config value and splits by '||'. Returns empty list if missing."""
    raw = get_config_value(key)
    if not raw:
        return []
    return [item for item in raw.split('||') if item]


def add_config_list_item(key, item):
    """Appends an item to a config list if not already present. Returns the updated list."""
    items = get_config_list(key)
    if item not in items:
        items.append(item)
        set_config_value(key, '||'.join(items))
    return items


def remove_config_list_item(key, item):
    """Removes an item from a config list if present. Returns the updated list."""
    items = get_config_list(key)
    if item in items:
        items.remove(item)
        set_config_value(key, '||'.join(items))
    return items

def get_payments_with_client_data(search_term="", sort_by="date"):
    """
    Fetches payments with LEFT JOIN for client name.
    Supports multi-word fuzzy search across client name, code, method, notes, and category.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN job_category TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN subcategory TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    query = """
        SELECT p.payment_id, p.client_code, p.amount, p.date,
               p.method, p.notes, p.job_category, p.subcategory,
               COALESCE(p.is_special, 0) AS is_special,
               COALESCE(c.name, 'Άγνωστος Πελάτης') AS client_name
        FROM payments p
        LEFT JOIN clients c ON p.client_code = c.code
        WHERE 1=1
    """
    params = []

    if search_term and search_term.strip() and search_term != "ALL":
        for word in search_term.strip().split():
            query += " AND (c.name LIKE ? OR p.client_code LIKE ? OR p.method LIKE ? OR p.notes LIKE ? OR p.job_category LIKE ? OR p.subcategory LIKE ?)"
            params.extend([f"%{word}%", f"%{word}%", f"%{word}%", f"%{word}%", f"%{word}%", f"%{word}%"])

    if sort_by == "amount":
        query += " ORDER BY p.amount DESC"
    else:
        query += " ORDER BY p.date DESC"

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_dashboard_financial_kpis(date_from, date_to, cat_filter="All", crew_filter="All", special_filter="ALL", client_filter="All"):
    conn = get_db_connection()
    cursor = conn.cursor()

    j_conditions = ["date BETWEEN ? AND ?"]
    j_params = [date_from, date_to]

    if client_filter and client_filter != "All":
        j_conditions.append("client_code = ?")
        j_params.append(client_filter)

    if cat_filter and cat_filter != "All":
        j_conditions.append("(category_1 = ? OR category_2 = ?)")
        j_params.extend([cat_filter, cat_filter])

    if crew_filter and crew_filter.strip() != "" and crew_filter != "All":
        normalized_crew = crew_filter.replace("+", ",")
        c_names = [c.strip() for c in normalized_crew.split(",") if c.strip()]
        for c_name in c_names:
            j_conditions.append("crew LIKE ?")
            j_params.append(f"%{c_name}%")

    if special_filter == "SPECIAL":
        j_conditions.append("COALESCE(is_special, 0) = 1")
    elif special_filter == "NON_SPECIAL":
        j_conditions.append("COALESCE(is_special, 0) = 0")

    j_where = " WHERE " + " AND ".join(j_conditions)
    job_query = f"SELECT client_code, price_after_vat FROM jobs{j_where}"
    cursor.execute(job_query, j_params)
    job_rows = cursor.fetchall()

    gross_revenue = sum(row[1] for row in job_rows if row[1] is not None)
    net_revenue = gross_revenue / 1.24
    job_count = len(job_rows)

    p_conditions = ["date BETWEEN ? AND ?"]
    p_params = [date_from, date_to]

    if client_filter and client_filter != "All":
        p_conditions.append("client_code = ?")
        p_params.append(client_filter)

    if special_filter == "SPECIAL":
        p_conditions.append("COALESCE(is_special, 0) = 1")
    elif special_filter == "NON_SPECIAL":
        p_conditions.append("COALESCE(is_special, 0) = 0")

    if cat_filter and cat_filter != "All":
        p_conditions.append("(job_category = ? OR subcategory = ?)")
        p_params.extend([cat_filter, cat_filter])

    if crew_filter and crew_filter.strip() != "" and crew_filter != "All":
        sub_query = f"SELECT DISTINCT client_code FROM jobs{j_where}"
        p_conditions.append(f"client_code IN ({sub_query})")
        p_params.extend(j_params)

    p_where = " WHERE " + " AND ".join(p_conditions)
    pay_query = f"SELECT client_code, amount FROM payments{p_where}"
    cursor.execute(pay_query, p_params)
    pay_rows = cursor.fetchall()

    total_collected = sum(row[1] for row in pay_rows if row[1] is not None)

    # Per-client outstanding debt balance to prevent client overpayments from wiping out unpaid client debts
    client_jobs = {}
    for code, price in job_rows:
        if code and price:
            c = str(code).strip()
            client_jobs[c] = client_jobs.get(c, 0.0) + float(price)

    client_pays = {}
    for code, amount in pay_rows:
        if code and amount:
            c = str(code).strip()
            client_pays[c] = client_pays.get(c, 0.0) + float(amount)

    all_client_codes = set(client_jobs.keys()) | set(client_pays.keys())
    floating_balance = sum(
        max(0.0, client_jobs.get(c, 0.0) - client_pays.get(c, 0.0))
        for c in all_client_codes
    )

    conn.close()

    return {
        "gross_revenue": round(gross_revenue, 2),
        "net_revenue": round(net_revenue, 2),
        "total_collected": round(total_collected, 2),
        "floating_balance": round(floating_balance, 2),
        "job_count": job_count
    }


def fetch_crew_job_distribution(date_from, date_to, category_filter="All", crew_filter="", special_filter="ALL", client_filter="All"):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT crew, COUNT(*) as count FROM jobs WHERE date BETWEEN ? AND ? AND crew IS NOT NULL AND crew != '-' AND crew != ''"
    params = [date_from, date_to]

    if client_filter and client_filter != "All":
        query += " AND client_code = ?"
        params.append(client_filter)

    if category_filter and category_filter != "All":
        query += " AND (category_1 = ? OR category_2 = ?)"
        params.extend([category_filter, category_filter])

    if crew_filter and crew_filter.strip() != "" and crew_filter != "All":
        normalized_filter = crew_filter.replace("+", ",")
        crew_names = [c.strip() for c in normalized_filter.split(",") if c.strip()]
        for crew_name in crew_names:
            query += " AND crew LIKE ?"
            params.append(f"%{crew_name}%")

    if special_filter == "SPECIAL":
        query += " AND COALESCE(is_special, 0) = 1"
    elif special_filter == "NON_SPECIAL":
        query += " AND COALESCE(is_special, 0) = 0"

    query += " GROUP BY crew ORDER BY count DESC"
    cursor.execute(query, params)
    distribution = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return distribution


def fetch_stagnant_aging_accounts(date_from, date_to, category_filter="All", crew_filter="", special_filter="ALL", client_filter="All"):
    from datetime import datetime
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Fetch job aggregates per client in a single grouped query
    j_query = "SELECT client_code, SUM(price_after_vat) as total_charges, MAX(date) as last_job FROM jobs WHERE date BETWEEN ? AND ?"
    j_params = [date_from, date_to]

    if client_filter and client_filter != "All":
        j_query += " AND client_code = ?"
        j_params.append(client_filter)

    if category_filter and category_filter != "All":
        j_query += " AND (category_1 = ? OR category_2 = ?)"
        j_params.extend([category_filter, category_filter])
    if crew_filter and crew_filter.strip() != "" and crew_filter != "All":
        normalized_filter = crew_filter.replace("+", ",")
        crew_names = [c.strip() for c in normalized_filter.split(",") if c.strip()]
        for crew_name in crew_names:
            j_query += " AND crew LIKE ?"
            j_params.append(f"%{crew_name}%")
    if special_filter == "SPECIAL":
        j_query += " AND COALESCE(is_special, 0) = 1"
    elif special_filter == "NON_SPECIAL":
        j_query += " AND COALESCE(is_special, 0) = 0"
    j_query += " GROUP BY client_code"

    cursor.execute(j_query, j_params)
    jobs_map = {str(r['client_code']).strip(): (float(r['total_charges'] or 0.0), r['last_job']) for r in cursor.fetchall()}

    # 2. Fetch payment aggregates per client in a single grouped query
    p_query = "SELECT client_code, SUM(amount) as total_payments, MAX(date) as last_pay FROM payments WHERE date BETWEEN ? AND ?"
    p_params = [date_from, date_to]

    if client_filter and client_filter != "All":
        p_query += " AND client_code = ?"
        p_params.append(client_filter)

    if category_filter and category_filter != "All":
        p_query += " AND (job_category = ? OR subcategory = ?)"
        p_params.extend([category_filter, category_filter])
    if special_filter == "SPECIAL":
        p_query += " AND COALESCE(is_special, 0) = 1"
    elif special_filter == "NON_SPECIAL":
        p_query += " AND COALESCE(is_special, 0) = 0"
    p_query += " GROUP BY client_code"

    cursor.execute(p_query, p_params)
    pays_map = {str(r['client_code']).strip(): (float(r['total_payments'] or 0.0), r['last_pay']) for r in cursor.fetchall()}

    all_codes = list(set(jobs_map.keys()) | set(pays_map.keys()))
    if not all_codes:
        conn.close()
        return []

    # 3. Batch lookup client names efficiently
    names_map = {}
    chunk_size = 500
    for i in range(0, len(all_codes), chunk_size):
        chunk = all_codes[i:i + chunk_size]
        placeholders = ",".join(["?"] * len(chunk))
        try:
            cursor.execute(f"SELECT code, name FROM clients WHERE code IN ({placeholders})", chunk)
            for r in cursor.fetchall():
                names_map[str(r['code']).strip()] = r['name']
        except Exception:
            pass

    stagnant_list = []
    today = datetime.now()

    for code in all_codes:
        if not code: continue
        client_name = names_map.get(code) or f"Client {code}"
        j_charges, j_last = jobs_map.get(code, (0.0, None))
        p_payments, p_last = pays_map.get(code, (0.0, None))

        debt = j_charges - p_payments
        if debt > 0.01:
            dates = []
            if j_last:
                try: dates.append(datetime.strptime(j_last, "%Y-%m-%d"))
                except: pass
            if p_last:
                try: dates.append(datetime.strptime(p_last, "%Y-%m-%d"))
                except: pass

            days_stagnant = max(0, (today - max(dates)).days) if dates else 999
            stagnant_list.append({
                "code": code,
                "name": client_name,
                "debt": round(debt, 2),
                "days_stagnant": days_stagnant
            })

    conn.close()
    stagnant_list.sort(key=lambda x: (x['days_stagnant'], x['debt']), reverse=True)
    return stagnant_list


def fetch_crew_jobs(crew_name):
    """Fetch all jobs for a specific technician or crew name, sorted by date descending."""
    import sqlite3
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.job_id, j.client_code, j.category_1, j.category_2, j.crew,
               j.date, j.time_slot, j.invoice_number, j.price_before_vat,
               j.vat_amount, j.price_after_vat, j.notes, j.extra_fields,
               COALESCE(j.is_special, 0) AS is_special,
               COALESCE(c.name, 'Άγνωστος Πελάτης') AS client_name
        FROM jobs j
        LEFT JOIN clients c ON j.client_code = c.code
        WHERE j.crew LIKE ?
        ORDER BY j.date DESC, j.time_slot ASC
    """, (f"%{crew_name}%",))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]



def fetch_client_history(client_code):
    """Fetch combined job and payment history for a client, sorted by date descending."""
    import sqlite3
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    unified = []
    
    cursor.execute("SELECT * FROM jobs WHERE client_code = ? ORDER BY date DESC", [client_code])
    for row in cursor.fetchall():
        d = dict(row)
        d['type'] = 'job'
        d['icon'] = '🔧'
        unified.append(d)
    
    cursor.execute("SELECT * FROM payments WHERE client_code = ? ORDER BY date DESC", [client_code])
    for row in cursor.fetchall():
        d = dict(row)
        d['type'] = 'payment'
        d['icon'] = '💰'
        unified.append(d)
    
    conn.close()
    # Sort by date descending (newest first), payments without dates last
    unified.sort(key=lambda x: x.get('date', '') or '', reverse=True)
    return unified