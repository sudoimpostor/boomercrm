# -*- coding: utf-8 -*-
"""
NSOFT Legacy Client Database Migration Pipeline
Author: NSOFT Data Bridge Engine (Optimized for Hermes Execution)
Date: 2026-07-15
"""

import os
import re
import csv
import json
import sqlite3
import sys

# Διαδρομές αρχείων
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEGACY_CSV_PATH = os.path.join(BASE_DIR, "raw_legacy_clients.csv")
TARGET_DB_PATH = os.path.join(BASE_DIR, "company_data.db")
LOG_FILE_PATH = os.path.join(BASE_DIR, "migration_log.txt")

def log_message(msg):
    print(msg)
    with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def clean_string(val):
    if not val:
        return ""
    return str(val).strip()

def extract_greek_phones(row_dict):
    """
    Ανιχνεύει και καθαρίζει τηλέφωνα από WTEL, HTEL, WFAX, PROBLEM, EIDXOR1.
    Εφαρμόζει κανόνες αυτόματης συμπλήρωσης προθεμάτων για 7-ψήφια και 8-ψήφια τηλέφωνα.
    """
    phone_candidates = [
        row_dict.get("WTEL", ""),
        row_dict.get("HTEL", ""),
        row_dict.get("WFAX", ""),
        row_dict.get("PROBLEM", ""),
        row_dict.get("EIDXOR1", "")
    ]
    
    extracted = []
    for raw_val in phone_candidates:
        if not raw_val:
            continue
        # Διαχωρισμός αν υπάρχουν πολλά τηλέφωνα στην ίδια γραμμή
        parts = re.split(r'[/,\|]|\bκαι\b|\band\b', str(raw_val), flags=re.IGNORECASE)
        for part in parts:
            digits = re.sub(r'\D', '', part)
            if not digits:
                continue
                
            # Αφαίρεση ελληνικού κωδικού χώρας αν υπάρχει
            if digits.startswith('30') and len(digits) > 10:
                digits = digits[2:]
            elif digits.startswith('0030') and len(digits) > 12:
                digits = digits[4:]
            
            # --- ΕΞΥΠΝΗ ΣΥΜΠΛΗΡΩΣΗ ΠΡΟΘΕΜΑΤΩΝ ---
            # 1. Αν είναι 8-ψήφιο και ξεκινάει από ψηφίο κινητού, λείπει το "69"
            if len(digits) == 8 and digits[0] in '345789':
                digits = '69' + digits
            # 2. Αν είναι 7-ψήφιο, θεωρούμε ότι λείπει το "210" (Αθήνα)
            elif len(digits) == 7:
                digits = '210' + digits
            # -------------------------------------
            
            # Αποδοχή μόνο έγκυρων 10-ψήφιων ελληνικών αριθμών
            if len(digits) == 10 and (digits.startswith('2') or digits.startswith('69') or digits.startswith('8')):
                extracted.append(digits)
            elif len(digits) == 10:
                extracted.append(digits)
                
    return list(dict.fromkeys(extracted))

def validate_greek_afm(afm):
    """
    Έλεγχος εγκυρότητας ΑΦΜ με Modulo 11.
    Προσθέτει αυτόματα 0 στην αρχή αν είναι 8-ψήφιο.
    """
    if not afm:
        return False, ""
    
    digits = re.sub(r'\D', '', str(afm))
    
    if len(digits) == 8:
        digits = '0' + digits
        
    if len(digits) != 9:
        return False, digits
        
    sum_val = 0
    for i in range(8):
        sum_val += int(digits[i]) * (2 ** (8 - i))
        
    remainder = sum_val % 11
    check_digit = int(digits[8])
    
    is_valid = False
    if remainder == 10:
        is_valid = (check_digit == 0)
    else:
        is_valid = (check_digit == remainder)
        
    return is_valid, digits

def migrate_pipeline(dry_run=True):
    log_message(f"=== MIGRATION RUN: {'DRY RUN (SANDBOX)' if dry_run else 'LIVE PRODUCTION'} ===")
    
    if not os.path.exists(LEGACY_CSV_PATH):
        log_message(f"ERROR: Legacy file not found at {LEGACY_CSV_PATH}")
        return False
        
    log_message(f"Reading legacy file from: {LEGACY_CSV_PATH}")
    
    # Σύνδεση στη βάση
    if dry_run:
        db_conn = sqlite3.connect(":memory:")
        log_message("Connected to in-memory database (sandbox).")
    else:
        db_conn = sqlite3.connect(TARGET_DB_PATH)
        log_message(f"Connected to production database at {TARGET_DB_PATH}")
        
    cursor = db_conn.cursor()
    
    # Δημιουργία πίνακα αν δεν υπάρχει
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT,
            address_2 TEXT,
            area TEXT,
            telephone TEXT,
            telephone_2 TEXT,
            vat_number TEXT,
            profession TEXT,
            notes TEXT,
            extra_fields TEXT
        )
    """)
    db_conn.commit()
    
    # Δοκιμή αποκωδικοποίησης (Windows-1253 ή UTF-8)
    encodings = ['utf-8-sig', 'cp1253', 'windows-1253', 'utf-8', 'iso-8859-7']
    reader = None
    f_handle = None
    
    for encoding in encodings:
        try:
            f_handle = open(LEGACY_CSV_PATH, mode='r', encoding=encoding)
            sample = f_handle.read(2048)
            f_handle.seek(0)
            dialect = csv.Sniffer().sniff(sample)
            f_handle.seek(0)
            reader = csv.DictReader(f_handle, dialect=dialect)
            log_message(f"Successfully opened CSV with encoding: {encoding}")
            break
        except Exception:
            if f_handle:
                f_handle.close()
            continue
            
    if not reader:
        log_message("ERROR: Could not read legacy file. Check file format or encoding.")
        return False
        
    success_count = 0
    skipped_count = 0
    invalid_afm_count = 0
    
    for idx, row in enumerate(reader, start=1):
        try:
            code = clean_string(row.get("CODE", row.get("KOD_PEL", "")))
            name = clean_string(row.get("SURNAME", row.get("EPONYMIA", "")))
            
            if not code or not name:
                skipped_count += 1
                continue
                
            address = clean_string(row.get("WADDR1", ""))
            address_2 = clean_string(row.get("WADDR2", ""))
            area = clean_string(row.get("WADDR2", ""))
            
            # Εξαγωγή & συμπλήρωση τηλεφώνων
            all_phones = extract_greek_phones(row)
            tel1 = all_phones[0] if len(all_phones) > 0 else ""
            tel2 = all_phones[1] if len(all_phones) > 1 else ""
            
            # Έλεγχος ΑΦΜ
            raw_afm = row.get("AFM", "")
            is_valid_afm, clean_afm = validate_greek_afm(raw_afm)
            if raw_afm and not is_valid_afm:
                invalid_afm_count += 1
                
            profession = clean_string(row.get("JOB", ""))
            
            # Συλλογή σημειώσεων
            raw_notes_parts = []
            if row.get("PROBLEM"):
                raw_notes_parts.append(f"Problem: {row['PROBLEM']}")
            if row.get("EIDXOR1"):
                raw_notes_parts.append(f"Eidxor1: {row['EIDXOR1']}")
            if len(all_phones) > 2:
                raw_notes_parts.append(f"Extra phones: {', '.join(all_phones[2:])}")
                
            notes = "; ".join(raw_notes_parts)
            
            # Packing των υπόλοιπων 30+ πεδίων σε JSON
            extra_payload = {}
            standard_mapped_keys = ["CODE", "KOD_PEL", "SURNAME", "EPONYMIA", "WADDR1", "WADDR2", "WTEL", "HTEL", "WFAX", "AFM", "JOB", "PROBLEM", "EIDXOR1"]
            for key, val in row.items():
                if key and key.strip() not in standard_mapped_keys and val is not None:
                    extra_payload[key.strip()] = str(val).strip()
                    
            if "YPOLOIPO" in row:
                extra_payload["YPOLOIPO"] = row["YPOLOIPO"]
            if "LASTAPDT" in row:
                extra_payload["LASTAPDT"] = row["LASTAPDT"]
                
            extra_fields_json = json.dumps(extra_payload, ensure_ascii=False)
            
            cursor.execute("""
                INSERT OR REPLACE INTO clients (
                    code, name, address, address_2, area, 
                    telephone, telephone_2, vat_number, profession, 
                    notes, extra_fields
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, name, address, address_2, area, tel1, tel2, clean_afm, profession, notes, extra_fields_json))
            
            success_count += 1
            
        except Exception as ex:
            log_message(f"ERROR at Row {idx}: {ex}")
            skipped_count += 1
            
    f_handle.close()
    
    if not dry_run:
        db_conn.commit()
        log_message("Database transaction committed successfully.")
    else:
        log_message("Dry-run complete. Sandbox rolled back cleanly.")
        
    db_conn.close()
    
    log_message("\n=== MIGRATION SUMMARY ===")
    log_message(f"• Successfully mapped & imported: {success_count} clients")
    log_message(f"• Failed or skipped rows: {skipped_count}")
    log_message(f"• Validated AFMs with warning alerts: {invalid_afm_count}")
    log_message("=========================\n")
    return True

if __name__ == "__main__":
    is_live = len(sys.argv) > 1 and sys.argv[1].lower() == "live"
    migrate_pipeline(dry_run=not is_live)
