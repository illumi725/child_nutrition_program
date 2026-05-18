import os
import sys
from PySide6.QtCore import QThread, Signal
from core.database import fetch_beneficiaries
from core.parser import parse_form_5a, evaluate_match, get_best_site_suggestion, clean_name
from core.database import get_db_connection


def _get_app_base_dir():
    """
    Returns the stable base directory for cache files.
    - In a PyInstaller bundle (frozen): directory containing the .exe / executable.
    - In development: project root (two levels up from this file's package).
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class ScanWorker(QThread):
    progress = Signal(int, str)
    log      = Signal(str)       # real-time console messages
    finished = Signal(dict)
    error    = Signal(str)

    def __init__(self, file_paths, root_dir=None):
        super().__init__()
        self.file_paths = file_paths
        self.root_dir = root_dir  # The root directory to scan for inter-file duplicates

    def run(self):
        try:
            self.progress.emit(10, "Fetching beneficiaries from database...")
            db_records = fetch_beneficiaries()
            
            from core.database import get_surname_dictionary
            surname_dict = get_surname_dictionary()
            
            excel_records = []
            total_files = len(self.file_paths)
            for i, fp in enumerate(self.file_paths):
                if os.path.exists(fp) and fp.endswith('.xlsx'):
                    self.progress.emit(10 + int(40 * (i / total_files)), f"Parsing {os.path.basename(fp)}...")
                    excel_records.extend(parse_form_5a(fp, surname_dict=surname_dict))

            self.progress.emit(50, "Loading sites cache...")
            sites_cache = []
            try:
                conn = get_db_connection()
                with conn.cursor() as cursor:
                    cursor.execute("SELECT site_id, site_name, batch, barangay_name, citymun_name, province_name FROM sites s LEFT JOIN barangays br ON s.barangay_code = br.barangay_code LEFT JOIN cities_municipalities cm ON s.citymun_code = cm.citymun_code LEFT JOIN provinces p ON s.province_code = p.province_code")
                    sites_cache = cursor.fetchall()
                conn.close()
            except:
                pass

            self.progress.emit(60, "Grouping database records...")
            db_by_bday = {}
            db_by_lname = {}
            for r in db_records:
                bd = str(r['birthday'])
                if bd not in db_by_bday: db_by_bday[bd] = []
                db_by_bday[bd].append(r)
                
                ln = clean_name(r.get('lastname')).split(' ')[0] if clean_name(r.get('lastname')) else ''
                if ln and ln not in db_by_lname: db_by_lname[ln] = []
                if ln: db_by_lname[ln].append(r)

            self.progress.emit(54, "Building inter-file duplicate index...")
            # ── Cached inter-file name index ──────────────────────────────────
            # Index = { "LASTNAME|FIRSTNAME": ["file1.xlsx", "file2.xlsx"] }
            # Covers ALL xlsx files in the directory (including selected ones).
            # Fingerprint is stable regardless of which files are selected.
            import json, hashlib

            INTERFILE_CACHE = os.path.join(_get_app_base_dir(), "interfile_index_cache.json")

            def dir_fingerprint(root_dir):
                parts = []
                for dirpath, dirs, files in os.walk(root_dir):
                    dirs.sort()  # stable traversal order
                    for f in files:
                        if f.endswith('.xlsx') and not f.startswith('~'):
                            fp = os.path.join(dirpath, f)
                            try:
                                st = os.stat(fp)
                                parts.append(f"{fp}:{st.st_size}:{int(st.st_mtime)}")
                            except:
                                pass
                parts.sort()  # sort globally for stable hash
                return hashlib.md5("\n".join(parts).encode()).hexdigest()

            dir_name_index = {}  # { (ln, fn): [all file_basenames] }
            selected_basenames = set(os.path.basename(fp) for fp in self.file_paths)

            if self.root_dir and os.path.isdir(self.root_dir):
                fingerprint = dir_fingerprint(self.root_dir)
                cache_ok = False
                self.log.emit(f"[Inter-file] Cache path: {INTERFILE_CACHE}")
                self.log.emit(f"[Inter-file] Fingerprint: {fingerprint}  |  Cache exists: {os.path.exists(INTERFILE_CACHE)}")

                if os.path.exists(INTERFILE_CACHE):
                    try:
                        with open(INTERFILE_CACHE, 'r', encoding='utf-8') as cf:
                            cached = json.load(cf)
                        cached_fp = cached.get("fingerprint", "")
                        if cached_fp == fingerprint:
                            dir_name_index = {
                                tuple(k.split("|", 1)): v
                                for k, v in cached.get("index", {}).items()
                            }
                            cache_ok = True
                            self.log.emit(f"[Inter-file] ✅ Loaded cached index ({len(dir_name_index)} unique names).")
                        else:
                            self.log.emit(f"[Inter-file] ⚠ Fingerprint mismatch — rebuilding.")
                            self.log.emit(f"[Inter-file]   Saved:   {cached_fp}")
                            self.log.emit(f"[Inter-file]   Current: {fingerprint}")
                    except Exception as ce:
                        self.log.emit(f"[Inter-file] Cache read failed: {ce}. Rebuilding...")

                if not cache_ok:
                    # Index ALL xlsx files — store full row data, not just filenames
                    all_files_to_index = []
                    for dirpath, dirs, files in os.walk(self.root_dir):
                        dirs.sort()
                        for f in files:
                            fp = os.path.join(dirpath, f)
                            if f.endswith('.xlsx') and not f.startswith('~'):
                                all_files_to_index.append(fp)

                    self.log.emit(f"[Inter-file] Building fresh index from {len(all_files_to_index)} file(s)...")
                    total_dir = len(all_files_to_index)
                    for idx, fp in enumerate(all_files_to_index):
                        pct = 54 + int(15 * (idx / max(1, total_dir)))
                        fname = os.path.basename(fp)
                        self.progress.emit(pct, f"Indexing {fname} ({idx+1}/{total_dir})...")
                        self.log.emit(f"[Inter-file] Indexing: {fname}")
                        try:
                            recs = parse_form_5a(fp, surname_dict=surname_dict)
                            for r in recs:
                                ln = clean_name(r.get('lastname', ''))
                                fn = clean_name(r.get('firstname', ''))
                                key = (ln, fn)
                                dir_name_index.setdefault(key, [])
                                # Store full row data for each occurrence
                                dir_name_index[key].append({
                                    "file":       fname,
                                    "file_path":  fp,
                                    "row_number": r.get('row_number'),
                                    "birthday":   str(r.get('birthday', '')),
                                    "weight":     str(r.get('weight', '')),
                                    "height":     str(r.get('height', '')),
                                    "raw_name":   r.get('raw_name', f"{r.get('lastname','')}, {r.get('firstname','')}"),
                                })
                        except Exception as ex:
                            self.log.emit(f"[Inter-file] ⚠ Skipped {fname}: {ex}")

                    try:
                        cache_data = {
                            "fingerprint": fingerprint,
                            "index": {f"{k[0]}|{k[1]}": v for k, v in dir_name_index.items()}
                        }
                        with open(INTERFILE_CACHE, 'w', encoding='utf-8') as cf:
                            json.dump(cache_data, cf, ensure_ascii=False)
                        self.log.emit(f"[Inter-file] 💾 Index saved ({len(dir_name_index)} unique names).")
                    except Exception as se:
                        self.log.emit(f"[Inter-file] ⚠ Cache save failed: {se}")


            # Build selected-file name index for comparison
            selected_name_index = {}  # { (ln, fn): [selected file_basenames] }
            for ex in excel_records:
                ln = clean_name(ex.get('lastname', ''))
                fn = clean_name(ex.get('firstname', ''))
                key = (ln, fn)
                fname = os.path.basename(ex.get('file_path', ''))
                selected_name_index.setdefault(key, [])
                if fname not in selected_name_index[key]:
                    selected_name_index[key].append(fname)


            self.progress.emit(70, "Checking for Excel duplicates...")


            # Group just the selected files for intra-file detection
            excel_groups = {}
            for ex in excel_records:
                key = (clean_name(ex['lastname']), clean_name(ex['firstname']))
                excel_groups.setdefault(key, []).append(ex)
            
            excel_duplicates = []
            conflict_stable_ids = set()
            seen_dup_keys = set()

            # Intra-file: duplicates within selected files
            for key, group in excel_groups.items():
                if len(group) > 1:
                    unique_files = list(set(r.get('file_path', '') for r in group))
                    dup_type = "Intra-file (Same File)" if len(unique_files) == 1 else "Inter-file (Across Selected)"
                    file_names = [os.path.basename(f) for f in unique_files]
                    excel_duplicates.append({
                        "name": f"{key[0]}, {key[1]}",
                        "birthday": "Multiple/Conflicting" if len(set(str(r['birthday']) for r in group)) > 1 else str(group[0]['birthday']),
                        "type": dup_type,
                        "files": ", ".join(file_names),
                        "rows": group
                    })
                    seen_dup_keys.add(key)
                    for r in group:
                        conflict_stable_ids.add(r['stable_id'])


            # Inter-file: use cached index — O(n) lookup, no re-parsing
            # dir_name_index covers ALL files; filter out selected ones to find OTHER files
            for key, sel_files in selected_name_index.items():
                if key in seen_dup_keys:
                    continue
                all_index_rows = dir_name_index.get(key, [])
                # index rows are dicts; filter to only those from OTHER (non-selected) files
                other_rows = [
                    r for r in all_index_rows
                    if isinstance(r, dict) and r.get('file') not in selected_basenames
                ]
                if other_rows:
                    sel_rows = excel_groups.get(key, [])
                    # Merge: selected full records + other-file simplified records
                    all_rows = list(sel_rows) + other_rows
                    other_file_names = list({r.get('file', '') for r in other_rows})
                    sel_file_names   = list({os.path.basename(r.get('file_path', '')) for r in sel_rows})
                    all_files_str = ", ".join(set(sel_file_names + other_file_names))
                    excel_duplicates.append({
                        "name": f"{key[0]}, {key[1]}",
                        "birthday": "—",
                        "type": "Inter-file (Found in Directory)",
                        "files": all_files_str,
                        "rows": all_rows
                    })
                    seen_dup_keys.add(key)
                    for r in sel_rows:
                        conflict_stable_ids.add(r['stable_id'])


            processable_records = [ex for ex in excel_records if ex['stable_id'] not in conflict_stable_ids]



            self.progress.emit(80, "Evaluating matches...")
            matches, fuzzy_matches, potential_dupes, missing_in_db = [], [], [], []
            
            total_records = len(processable_records)
            for i, ex in enumerate(processable_records):
                if i % 10 == 0:
                    self.progress.emit(80 + int(20 * (i / max(1, total_records))), f"Evaluating match {i}/{total_records}...")
                    
                best_score, best_db_match = 0, None
                ex_bd = str(ex['birthday'])
                ex_ln = clean_name(ex['lastname']).split(' ')[0] if clean_name(ex['lastname']) else ''
                
                ex_bd_swapped = ""
                if len(ex_bd) == 10:
                    try:
                        y, m, d = ex_bd.split('-')
                        ex_bd_swapped = f"{y}-{d}-{m}"
                    except: pass
                    
                candidates_list = db_by_bday.get(ex_bd, []) + db_by_lname.get(ex_ln, [])
                if ex_bd_swapped:
                    candidates_list += db_by_bday.get(ex_bd_swapped, [])
                    
                candidates = {c['beneficiary_id']: c for c in candidates_list}.values()
                
                for db_r in candidates:
                    if db_r.get('_matched'): 
                        continue

                    # Local evaluation logic since core was slightly modified
                    from core.parser import calculate_match_score
                    score, _ = calculate_match_score(ex, db_r)
                    if score > best_score:
                        best_score, best_db_match = score, db_r
                        
                if best_db_match:
                    best_db_match['suggested_site'] = get_best_site_suggestion(ex, sites_cache)
                    match_info = evaluate_match(ex, best_db_match)
                    res_obj = { "excel": ex, "db": best_db_match, **match_info }
                    
                    if match_info['score'] == 100:
                        matches.append(res_obj)
                        best_db_match['_matched'] = True
                    elif match_info['score'] >= 85:
                        fuzzy_matches.append(res_obj)
                        best_db_match['_matched'] = True
                    elif match_info['score'] >= 70:
                        potential_dupes.append(res_obj)
                        best_db_match['_matched'] = True
                    else:
                        missing_in_db.append(ex)
                else:
                    missing_in_db.append(ex)

            # Determine which sites are being scanned by looking at the DB records we successfully matched
            scanned_site_ids = set()
            
            # 1. Fallback: If we extracted a site from the Excel header, use it
            for ex in excel_records:
                if ex.get('suggested_site_id'):
                    scanned_site_ids.add(ex['suggested_site_id'])
                    
            # 2. Most accurate: Look at the actual DB records we matched. 
            # If 20 people matched beneficiaries in "Site A", we are definitely scanning "Site A".
            for match_list in [matches, fuzzy_matches, potential_dupes]:
                for res in match_list:
                    if res['db'].get('site_id'):
                        scanned_site_ids.add(res['db']['site_id'])
                
            missing_in_excel = []
            for r in db_records:
                if not r.get('_matched'):
                    # Only flag as missing if the database record belongs to one of the sites we just scanned
                    if not scanned_site_ids or r.get('site_id') in scanned_site_ids:
                        missing_in_excel.append(r)

            self.progress.emit(100, "Done!")
            self.finished.emit({
                "exact_matches": matches, 
                "fuzzy_matches": fuzzy_matches, 
                "potential_matches": potential_dupes,
                "excel_duplicates": excel_duplicates,
                "missing_in_db": missing_in_db, 
                "missing_in_excel": missing_in_excel[:500]  # Cap at 500 to prevent UI lag if massive
            })
        except Exception as e:
            self.error.emit(str(e))

class GlobalStatsWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    # Cache file next to the executable (or project root in dev mode)
    CACHE_PATH = os.path.join(_get_app_base_dir(), "global_stats_cache.json")

    @staticmethod
    def _serialize(obj):
        """Recursively convert non-JSON-serializable types (date, Decimal, etc.)."""
        import datetime
        from decimal import Decimal
        if isinstance(obj, dict):
            return {k: GlobalStatsWorker._serialize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [GlobalStatsWorker._serialize(i) for i in obj]
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        return obj

    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir
        
    def run(self):
        try:
            self.progress.emit(5, "Scanning for Excel files...")
            
            import os
            import json
            import datetime
            from core.parser import parse_form_5a, clean_name
            from core.database import fetch_beneficiaries, get_surname_dictionary
            
            # Find all xlsx files
            excel_files = []
            for root, dirs, files in os.walk(self.base_dir):
                for f in files:
                    if f.endswith('.xlsx') and not f.startswith('~'):
                        excel_files.append(os.path.join(root, f))
                        
            if not excel_files:
                raise Exception("No Excel files found in the selected directory.")
                
            self.progress.emit(10, f"Found {len(excel_files)} Excel files. Fetching database...")
            
            # Fetch entire DB
            db_records = fetch_beneficiaries()
            total_db = len(db_records)
            surname_dict = get_surname_dictionary()
            
            # Find DB Duplicates (by name)
            db_name_groups = {}
            for r in db_records:
                key = (clean_name(r['lastname']), clean_name(r['firstname']))
                db_name_groups.setdefault(key, []).append(r)
                
            db_duplicates = sum(1 for group in db_name_groups.values() if len(group) > 1)
            
            self.progress.emit(25, "Parsing all Excel files. This may take a while...")
            
            all_excel_records = []
            for i, fp in enumerate(excel_files):
                self.progress.emit(25 + int(50 * (i / len(excel_files))), f"Parsing {os.path.basename(fp)}...")
                all_excel_records.extend(parse_form_5a(fp, surname_dict=surname_dict))
                
            total_excel = len(all_excel_records)
            
            self.progress.emit(80, "Calculating Excel duplicates...")
            
            # Find Excel Duplicates
            ex_name_groups = {}
            for ex in all_excel_records:
                ln = clean_name(ex['lastname'])
                fn = clean_name(ex['firstname'])
                key = (ln, fn)
                ex_name_groups.setdefault(key, []).append(ex)

            excel_duplicates_list = [r for group in ex_name_groups.values() if len(group) > 1 for r in group]
            excel_duplicates = len(set((r['lastname'], r['firstname']) for r in excel_duplicates_list))
            
            self.progress.emit(85, "Cross-referencing DB vs Excel...")
            
            # Cross reference using dictionaries for speed
            db_lookup = { (clean_name(r['lastname']).split(' ')[0], clean_name(r['firstname'])) : True for r in db_records if r.get('lastname') and r.get('firstname')}
            ex_lookup = { (clean_name(ex['lastname']).split(' ')[0], clean_name(ex['firstname'])) : True for ex in all_excel_records if ex.get('lastname') and ex.get('firstname')}
            
            missing_in_db_list = []
            for ex in all_excel_records:
                ln = clean_name(ex['lastname']).split(' ')[0] if ex.get('lastname') else ''
                fn = clean_name(ex['firstname'])
                if (ln, fn) not in db_lookup:
                    missing_in_db_list.append(ex)
                    
            missing_in_excel_list = []
            for r in db_records:
                ln = clean_name(r['lastname']).split(' ')[0] if r.get('lastname') else ''
                fn = clean_name(r['firstname'])
                if (ln, fn) not in ex_lookup:
                    missing_in_excel_list.append(r)

            db_duplicates_list = [r for group in db_name_groups.values() if len(group) > 1 for r in group]
            
            scanned_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            result = {
                "total_db": total_db,
                "total_excel": total_excel,
                "missing_in_db": len(missing_in_db_list),
                "missing_in_excel": len(missing_in_excel_list),
                "db_duplicates": db_duplicates,
                "excel_duplicates": excel_duplicates,
                "files_scanned": len(excel_files),
                "scanned_at": scanned_at,
                "base_dir": self.base_dir,
                # Full record lists for clickable cards:
                "db_records": db_records,
                "excel_records": all_excel_records,
                "missing_in_db_list": missing_in_db_list,
                "missing_in_excel_list": missing_in_excel_list,
                "db_duplicates_list": db_duplicates_list,
                "excel_duplicates_list": excel_duplicates_list,
            }

            self.progress.emit(98, "Saving cache...")
            # Save to cache (serialize dates/Decimals first)
            try:
                with open(GlobalStatsWorker.CACHE_PATH, 'w', encoding='utf-8') as f:
                    json.dump(GlobalStatsWorker._serialize(result), f, ensure_ascii=False)
            except Exception as cache_err:
                print(f"[CACHE-WARN] Could not save cache: {cache_err}")

            self.progress.emit(100, "Done!")
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))



