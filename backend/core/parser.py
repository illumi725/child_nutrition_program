import os
import re
import datetime
import pandas as pd
from fuzzywuzzy import fuzz
from typing import List, Dict, Any

from core.database import get_db_connection

try:
    from anthro_utils import calculate_anthro_stats
except ImportError:
    from backend.anthro_utils import calculate_anthro_stats

def clean_name(name_str):
    if not name_str: return ""
    s = re.sub(r'[^\w\s\.]', ' ', str(name_str).upper())
    return ' '.join(s.split())

def split_beneficiary_name(raw_name, surname_dict=None):
    raw_name = str(raw_name).strip()
    if not raw_name: return "", "", ""
    
    # Extract suffix to prevent it from being parsed as a middle name
    suffixes = ['JR', 'JR.', 'SR', 'SR.', 'II', 'III', 'IV', 'V', 'VI']
    found_suffix = ""
    
    parts = raw_name.split()
    if len(parts) > 1 and parts[-1].upper().replace('.','') in [s.replace('.','') for s in suffixes]:
        found_suffix = parts.pop().upper().replace('.','')
        raw_name = ' '.join(parts)
        
    lastname = ""
    firstname = ""
    middlename = ""
    
    if ',' in raw_name:
        parts = raw_name.split(',', 1)
        lastname = parts[0].strip().upper()
        first_and_middle = parts[1].strip() if len(parts) > 1 else ""
        fn_parts = first_and_middle.split()
        if len(fn_parts) > 1:
            middlename = fn_parts[-1].upper()
            firstname = ' '.join(fn_parts[:-1]).upper()
        else:
            firstname = first_and_middle.upper()
            middlename = ""
    else:
        parts = raw_name.split()
        if len(parts) >= 3:
            lastname = parts[-1].upper()
            middlename = parts[-2].upper()
            firstname = ' '.join(parts[:-2]).upper()
        elif len(parts) == 2:
            lastname = parts[1].upper()
            firstname = parts[0].upper()
            middlename = ""
        elif len(parts) == 1:
            lastname = parts[0].upper()
            firstname = ""
            middlename = ""

    # Intelligent Middle Name check
    if surname_dict and middlename and middlename not in surname_dict:
        # The parsed middle name is not a known surname. 
        # In Philippine naming conventions, this means it's likely a compound first name.
        firstname = f"{firstname} {middlename}".strip()
        middlename = ""

    if found_suffix:
        firstname = f"{firstname} {found_suffix}".strip()
        
    return lastname, firstname, middlename

def calculate_match_score(excel_rec, db_rec):
    ex_ln, ex_fn = clean_name(excel_rec['lastname']), clean_name(excel_rec['firstname'])
    ex_mn = clean_name(excel_rec.get('middlename', ''))
    db_ln, db_fn, db_mn = clean_name(db_rec.get('lastname')), clean_name(db_rec.get('firstname')), clean_name(db_rec.get('middlename'))
    ex_bd = str(excel_rec['birthday'])
    db_bd = str(db_rec['birthday'])

    db_full_fn = clean_name(f"{db_fn} {db_mn}")
    ex_full_fn = clean_name(f"{ex_fn} {ex_mn}")
    
    names_match = (ex_ln == db_ln) and (
        (ex_fn == db_fn and ex_mn == db_mn) or 
        (ex_full_fn == db_full_fn) or
        (ex_full_fn.replace(" ","") == db_full_fn.replace(" ",""))
    )

    if names_match and ex_bd == db_bd:
        return 100, "exact"
        
    ex_full = clean_name(f"{ex_ln} {ex_fn} {ex_mn}")
    db_full = clean_name(f"{db_ln} {db_fn} {db_mn}")
    score = fuzz.token_set_ratio(ex_full, db_full)
    
    has_db_mn = len(db_mn) > 0
    has_ex_mn = len(ex_fn.split()) > 1 or (len(ex_fn.split()) == 1 and len(ex_fn) == 1)
    if has_db_mn and not has_ex_mn: score -= 15
    
    match_type = "fuzzy"
    if ex_bd != db_bd:
        is_swap = False
        if ex_bd and db_bd and len(ex_bd) == 10 and len(db_bd) == 10:
            try:
                y1, m1, d1 = ex_bd.split('-')
                y2, m2, d2 = db_bd.split('-')
                if y1 == y2 and m1 == d2 and d1 == m2:
                    is_swap = True
            except: pass
            
        if is_swap:
            score -= 5
            match_type = "fuzzy_dob_swapped"
        else:
            score -= 20
            match_type = "fuzzy_dob_mismatch"
            
    return max(0, score), match_type

def get_best_site_suggestion(ex, sites_cache):
    if not sites_cache: return None
    ex_full = f"{ex.get('excel_site','') or ''} {ex.get('excel_brgy','') or ''} {ex.get('excel_city','') or ''} {ex.get('excel_prov','') or ''}".upper()
    best_sid, best_s_score = None, 0
    for s in sites_cache:
        db_full = f"{s.get('site_name','') or ''} {s.get('barangay_name','') or ''} {s.get('citymun_name','') or ''} {s.get('province_name','') or ''}".upper()
        s_score = fuzz.token_set_ratio(ex_full, db_full)
        if ex.get('excel_batch') is not None and s.get('batch') == ex['excel_batch']:
            s_score += 10
        if s_score > best_s_score:
            best_s_score, best_sid = s_score, s['site_id']
    return best_sid if best_s_score > 70 else None

def safe_float(val):
    try:
        if pd.isna(val): return None
        return round(float(val), 2)
    except: return None

def parse_date_collected(df_header):
    if len(df_header) > 9:
        row10 = df_header.iloc[9]
        for col_idx in [4, 5, 6]:
            if col_idx < len(row10):
                val_str = str(row10.iloc[col_idx]).upper()
                if 'DATE OF WEIGHING' in val_str:
                    parts = val_str.split('DATE OF WEIGHING:')
                    if len(parts) > 1:
                        raw = parts[1].split('MIDLINE')[0].split('ENDLINE')[0].strip()
                        clean = raw.replace('_', '').replace('\n', ' ').strip()
                        if clean:
                            try: return pd.to_datetime(clean).strftime('%Y-%m-%d')
                            except:
                                try:
                                    import dateparser
                                    dt = dateparser.parse(clean)
                                    if dt: return dt.strftime('%Y-%m-%d')
                                except: pass
    return None

def parse_form_5a(file_path: str, surname_dict=None) -> List[Dict[str, Any]]:
    records = []
    try:
        xl = pd.ExcelFile(file_path)
        form_5a_sheet = next((s for s in xl.sheet_names if '5A' in s.upper()), None)
        if not form_5a_sheet: return records
        df_temp = pd.read_excel(file_path, sheet_name=form_5a_sheet, nrows=30, header=None)
        
        excel_city, excel_brgy, excel_prov, excel_site = "", "", "", ""
        for _, row in df_temp.iterrows():
            row_str = ' '.join(str(v).upper() for v in row.values if pd.notna(v))
            if 'CITY/ MUNICIPALITY:' in row_str: excel_city = str(row.tolist()[9]).strip() if len(row) > 9 else ""
            if 'BARANGAY:' in row_str: excel_brgy = str(row.tolist()[9]).strip() if len(row) > 9 else ""
            if 'PROVINCE' in row_str and 'BULACAN' in row_str: excel_prov = 'BULACAN'
            elif 'PROVINCE' in row_str: excel_prov = str(row.tolist()[2]).strip() if len(row) > 2 else ""
            if 'FEEDING SITE' in row_str: excel_site = str(row.tolist()[2]).strip() if len(row) > 2 else ""

        excel_batch = None
        batch_match = re.search(r'Batch\s*(\d+)', os.path.basename(file_path), re.IGNORECASE)
        if batch_match: 
            excel_batch = int(batch_match.group(1))
        
        if excel_batch is None:
            for _, row in df_temp.iterrows():
                row_list = [str(x).upper() for x in row.tolist()]
                if any('BATCH' in val for val in row_list):
                    idx = next((i for i, val in enumerate(row_list) if 'BATCH' in val), -1)
                    if idx != -1 and idx + 1 < len(row):
                        try:
                            val = str(row.tolist()[idx+1]).strip()
                            excel_batch = int(re.search(r'(\d+)', val).group(1))
                            break
                        except: pass

        date_collected = parse_date_collected(df_temp)
        header_row_index = -1
        for idx, row in df_temp.iterrows():
            row_str = ' '.join(str(val).upper() for val in row.values if pd.notna(val))
            if 'LAST NAME' in row_str or 'FIRST NAME' in row_str:
                header_row_index = idx
                break
        if header_row_index == -1: return records
        df = pd.read_excel(file_path, sheet_name=form_5a_sheet, skiprows=header_row_index)
        
        name_col = next((col for col in df.columns if 'name' in str(col).lower()), None)
        birthday_col = next((col for col in df.columns if 'birthday' in str(col).lower() or 'birth' in str(col).lower()), None)
        gender_col = next((col for col in df.columns if any(k in str(col).lower() for k in ['sex', 'gender'])), None)
        
        weight_col, height_col = None, None
        for col in df.columns:
            for r_idx in range(min(3, len(df))):
                val_str = str(df.iloc[r_idx][col]).lower()
                col_str = str(col).lower()
                if not weight_col and ('weight' in val_str or ('weight' in col_str and 'baseline' in col_str)): weight_col = col
                if not height_col and ('height' in val_str or ('height' in col_str and 'baseline' in col_str)): height_col = col

        sites_cache = []
        try:
            from core.database import get_db_connection
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT site_id, site_name, batch, barangay_name, citymun_name, province_name FROM sites s LEFT JOIN barangays br ON s.barangay_code = br.barangay_code LEFT JOIN cities_municipalities cm ON s.citymun_code = cm.citymun_code LEFT JOIN provinces p ON s.province_code = p.province_code")
                sites_cache = cursor.fetchall()
            conn.close()
        except: pass

        start_idx = 2 if weight_col or height_col else 0
        for act_idx in range(start_idx, len(df)):
            row = df.iloc[act_idx]
            raw_name = str(row[name_col]) if pd.notna(row.get(name_col)) else ""
            if not raw_name or raw_name.lower() in ['nan', 'none', '']: continue
            
            lastname, firstname, middlename = split_beneficiary_name(raw_name, surname_dict)
            
            gender = "Boy"
            if gender_col:
                raw_g = str(row.get(gender_col)).upper()
                if 'G' in raw_g or 'F' in raw_g or 'GIRL' in raw_g: gender = "Girl"
            
            raw_bday = row.get(birthday_col)
            bday_str = None
            if pd.notna(raw_bday):
                try: bday_str = pd.to_datetime(raw_bday).strftime('%Y-%m-%d')
                except: bday_str = str(raw_bday)

            ex_rec = {
                "stable_id": f"{os.path.basename(file_path)}_{header_row_index + act_idx + 2}",
                "row_number": header_row_index + act_idx + 2,
                "file_path": file_path,
                "source_file": os.path.basename(file_path),
                "raw_name": raw_name,
                "lastname": lastname, "firstname": firstname, "middlename": middlename,
                "gender": gender,
                "birthday": bday_str,
                "excel_city": excel_city, "excel_brgy": excel_brgy, "excel_prov": excel_prov, "excel_site": excel_site,
                "excel_batch": excel_batch,
                "weight": safe_float(row.get(weight_col)) if weight_col else None,
                "height": safe_float(row.get(height_col)) if height_col else None,
                "date_collected": date_collected
            }
            anthro_preview = None
            if bday_str and ex_rec['weight'] and ex_rec['height']:
                try:
                    b_dt = datetime.datetime.strptime(bday_str, '%Y-%m-%d').date()
                    c_dt = datetime.datetime.strptime(date_collected, '%Y-%m-%d').date() if date_collected else datetime.date.today()
                    months = (c_dt.year - b_dt.year) * 12 + c_dt.month - b_dt.month
                    anthro_preview = calculate_anthro_stats(months, gender, ex_rec['weight'], ex_rec['height'])
                except: pass
            ex_rec['anthro_preview'] = anthro_preview
            ex_rec['suggested_site_id'] = get_best_site_suggestion(ex_rec, sites_cache)
            records.append(ex_rec)
    except Exception as e:
        print(f"[RE-ERROR] Parser: {str(e)}")
    return records

def evaluate_match(ex, db_r, sites_cache=None):
    score, m_type = calculate_match_score(ex, db_r)
    
    db_w, db_h = safe_float(db_r.get('weight')), safe_float(db_r.get('height'))
    db_date = db_r.get('date_collected')
    ex_date = ex.get('date_collected')
    
    db_bday_str = str(db_r.get('birthday', ''))
    ex_bday_str = str(ex.get('birthday', ''))
    
    weight_mismatch = (ex['weight'] is not None and (db_w is None or abs(ex['weight'] - db_w) > 0.1))
    height_mismatch = (ex['height'] is not None and (db_h is None or abs(ex['height'] - db_h) > 0.1))
    date_mismatch = (ex_date is not None and (ex_date != db_date))
    birthday_mismatch = (ex_bday_str and db_bday_str and ex_bday_str != db_bday_str)
    
    # Calculate name mismatch using the same logic as calculate_match_score
    ex_ln = clean_name(ex.get('lastname'))
    ex_fn = clean_name(ex.get('firstname'))
    ex_mn = clean_name(ex.get('middlename'))
    
    db_ln = clean_name(db_r.get('lastname'))
    db_fn = clean_name(db_r.get('firstname'))
    db_mn = clean_name(db_r.get('middlename'))
    
    db_full_fn = clean_name(f"{db_fn} {db_mn}")
    ex_full_fn = clean_name(f"{ex_fn} {ex_mn}")
    
    names_match = (ex_ln == db_ln) and (
        (ex_fn == db_fn and ex_mn == db_mn) or 
        (ex_full_fn == db_full_fn) or
        (ex_full_fn.replace(" ","") == db_full_fn.replace(" ",""))
    )
    name_mismatch = not names_match
    
    ex_site = (ex.get('excel_site') or '').strip().upper()
    db_site = (db_r.get('site_name') or '').strip().upper()
    site_mismatch = (ex_site != "" and db_site != "" and ex_site != db_site)
    
    baseline_mismatch = weight_mismatch or height_mismatch or date_mismatch or birthday_mismatch
    
    return {
        "score": score,
        "type": "exact" if score == 100 else m_type,
        "baseline_mismatch": baseline_mismatch,
        "weight_mismatch": weight_mismatch,
        "height_mismatch": height_mismatch,
        "date_mismatch": date_mismatch,
        "birthday_mismatch": birthday_mismatch,
        "name_mismatch": name_mismatch,
        "site_mismatch": site_mismatch
    }
