import os
import sqlite3
import pymysql
import datetime
import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

SITES_QUERY = """
    SELECT s.site_id, s.site_name, s.batch, br.barangay_name, cm.citymun_name, p.province_name
    FROM sites s
    LEFT JOIN barangays br ON s.barangay_code = br.barangay_code
    LEFT JOIN cities_municipalities cm ON s.citymun_code = cm.citymun_code
    LEFT JOIN provinces p ON s.province_code = p.province_code
    ORDER BY s.site_name
"""  # noqa: E501

BENEFICIARIES_BASE_QUERY = """
    SELECT
        b.beneficiary_id, b.lastname, b.firstname, b.middlename, b.birthday, b.gender, b.site_id,
        s.site_name, s.batch, br.barangay_name, cm.citymun_name, p.province_name,
        bl.weight, bl.height, bl.age, bl.date_collected,
        bl.bmifa_status, bl.bmifa_figure, bl.wfa_status, bl.wfa_figure,
        bl.hfa_status, bl.hfa_figure, bl.wfh_status, bl.wfh_figure
    FROM beneficiaries b
    LEFT JOIN sites s ON b.site_id = s.site_id
    LEFT JOIN barangays br ON s.barangay_code = br.barangay_code
    LEFT JOIN cities_municipalities cm ON s.citymun_code = cm.citymun_code
    LEFT JOIN provinces p ON s.province_code = p.province_code
    LEFT JOIN (
        SELECT beneficiary_id, MAX(created_at) AS max_created
        FROM baseline_info
        GROUP BY beneficiary_id
    ) latest ON latest.beneficiary_id = b.beneficiary_id
    LEFT JOIN baseline_info bl ON bl.beneficiary_id = b.beneficiary_id
        AND bl.created_at = latest.max_created
"""  # noqa: E501

# Register adapter for decimal.Decimal to work seamlessly with SQLite
sqlite3.register_adapter(Decimal, str)

# ── Connection Routing ────────────────────────────────────────────────────────


def get_db_connection():
    """Return a database connection based on the current mode (cloud/local)."""
    from core.app_settings import get_mode

    if get_mode() == "local":
        return _get_local_connection()
    return _get_cloud_connection()


def _get_cloud_connection():
    from core._config import (
        CLOUD_DB_HOST,
        CLOUD_DB_USER,
        CLOUD_DB_PASSWORD,
        CLOUD_DB_DATABASE,
        CLOUD_DB_PORT,
    )

    return pymysql.connect(
        host=CLOUD_DB_HOST,
        user=CLOUD_DB_USER,
        password=CLOUD_DB_PASSWORD,
        database=CLOUD_DB_DATABASE,
        port=CLOUD_DB_PORT,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
    )


def _get_local_connection():
    from core.app_settings import get_local_db_path

    path = get_local_db_path()
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Local database not found at {path}.\n"
            "Please go to Settings and run a full replication first."
        )
    conn = sqlite3.connect(path)

    # Register NOW function for MySQL compatibility
    conn.create_function(
        "NOW", 0, lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    # SQLite dict factory
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys=ON")

    # Auto-create crucial SQLite indexes for local query optimization
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_beneficiaries_site_id ON beneficiaries(site_id)"  # noqa: E501
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_baseline_info_beneficiary_id ON baseline_info(beneficiary_id)"  # noqa: E501
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_baseline_info_created_at ON baseline_info(created_at)"  # noqa: E501
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_baseline_info_beneficiary_created ON baseline_info(beneficiary_id, created_at DESC)"  # noqa: E501
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sites_barangay_code ON sites(barangay_code)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_barangays_barangay_code ON barangays(barangay_code)"  # noqa: E501
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cities_municipalities_citymun_code ON cities_municipalities(citymun_code)"  # noqa: E501
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_provinces_province_code ON provinces(province_code)"  # noqa: E501
        )
        conn.commit()
    except Exception as e:
        logger.warning("SQLite index setup: %s", e)

    return SQLiteConnectionWrapper(conn)


# ── SQLite Compatibility Wrapper ──────────────────────────────────────────────


class SQLiteCursorWrapper:
    """Makes sqlite3 cursor act like PyMySQL (context manager + %s params)"""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, args=None):
        sql = sql.replace("%s", "?")
        if args is not None:
            return self._cursor.execute(sql, args)
        return self._cursor.execute(sql)

    def executemany(self, sql, args):
        sql = sql.replace("%s", "?")
        return self._cursor.executemany(sql, args)

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchone(self):
        return self._cursor.fetchone()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cursor.close()

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount


class SQLiteConnectionWrapper:
    """Makes sqlite3 connection act like PyMySQL connection"""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return SQLiteCursorWrapper(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def fetch_beneficiaries(site_id: Optional[str] = None) -> List[Dict[str, Any]]:
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = BENEFICIARIES_BASE_QUERY
            args = None
            if site_id:
                sql += " WHERE b.site_id = %s"
                args = (site_id,)
            if args:
                cursor.execute(sql, args)
            else:
                cursor.execute(sql)
            rows = cursor.fetchall()
            for r in rows:
                if isinstance(r.get("weight"), Decimal):
                    r["weight"] = float(r["weight"])
                if isinstance(r.get("height"), Decimal):
                    r["height"] = float(r["height"])
                if isinstance(r.get("birthday"), (datetime.date, datetime.datetime)):
                    r["birthday"] = r["birthday"].strftime("%Y-%m-%d")
                if isinstance(
                    r.get("date_collected"), (datetime.date, datetime.datetime)
                ):
                    r["date_collected"] = r["date_collected"].strftime("%Y-%m-%d")
            return rows
    finally:
        connection.close()


def get_sites():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(SITES_QUERY)
            return cursor.fetchall()
    finally:
        conn.close()


def fetch_sites_cache():
    """Sites list for Excel parsing (shared with workers)."""
    return get_sites()


def sync_baseline(beneficiary_id, weight, height, date_collected, birthday):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Update the birthday in beneficiaries (only if birthday is provided)
            if birthday:
                cursor.execute(
                    "UPDATE beneficiaries SET birthday = %s WHERE beneficiary_id = %s",
                    (birthday, beneficiary_id),
                )

            # 2. Get gender to calculate anthro stats
            cursor.execute(
                "SELECT gender, birthday FROM beneficiaries WHERE beneficiary_id = %s",
                (beneficiary_id,),
            )
            ben = cursor.fetchone()
            if not ben:
                return False

            ref_date = datetime.date.today()
            if date_collected:
                try:
                    ref_date = datetime.datetime.strptime(
                        date_collected, "%Y-%m-%d"
                    ).date()
                except (ValueError, TypeError):
                    pass

            # Use the resolved birthday from DB (in case birthday param was None)
            resolved_birthday = birthday or (
                str(ben.get("birthday", "")) if ben.get("birthday") else None
            )
            if not resolved_birthday:
                logger.error(
                    "sync_baseline: no birthday for beneficiary_id=%s", beneficiary_id
                )
                return False

            bday_dt = datetime.datetime.strptime(resolved_birthday, "%Y-%m-%d").date()
            age_in_months = (
                (ref_date.year - bday_dt.year) * 12 + ref_date.month - bday_dt.month
            )

            try:
                from backend.anthro_utils import calculate_anthro_stats
            except ImportError:
                from anthro_utils import calculate_anthro_stats

            stats = calculate_anthro_stats(age_in_months, ben["gender"], weight, height)

            # 3. Find the latest baseline_info row (SQLite-compatible: no ORDER BY on UPDATE)  # noqa: E501
            cursor.execute(
                "SELECT info_id FROM baseline_info WHERE beneficiary_id = %s ORDER BY created_at DESC LIMIT 1",  # noqa: E501
                (beneficiary_id,),
            )
            info_row = cursor.fetchone()

            if info_row:
                # Update existing row by specific info_id (SQLite-compatible)
                sql = """
                UPDATE baseline_info SET 
                    weight = %s, height = %s, age = %s, date_collected = %s,
                    wfa_figure = %s, wfa_status = %s, 
                    hfa_figure = %s, hfa_status = %s, 
                    wfh_figure = %s, wfh_status = %s, 
                    bmifa_figure = %s, bmifa_status = %s, 
                    updated_at = NOW()
                WHERE info_id = %s
                """
                info_id = (
                    info_row["info_id"] if isinstance(info_row, dict) else info_row[0]
                )
                cursor.execute(
                    sql,
                    (
                        weight,
                        height,
                        age_in_months,
                        date_collected,
                        stats.get("wfa_figure"),
                        stats.get("wfa_status"),
                        stats.get("hfa_figure"),
                        stats.get("hfa_status"),
                        stats.get("wfh_figure"),
                        stats.get("wfh_status"),
                        stats.get("bmifa_figure"),
                        stats.get("bmifa_status"),
                        info_id,
                    ),
                )
            else:
                # No baseline_info row exists yet — insert one
                new_info_id = generate_beneficiary_id()
                sql_ins = """
                INSERT INTO baseline_info (
                    info_id, beneficiary_id, gender, weight, height, age, date_collected,
                    wfa_figure, wfa_status, hfa_figure, hfa_status,
                    wfh_figure, wfh_status, bmifa_figure, bmifa_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """  # noqa: E501
                cursor.execute(
                    sql_ins,
                    (
                        new_info_id,
                        beneficiary_id,
                        ben["gender"],
                        weight,
                        height,
                        age_in_months,
                        date_collected,
                        stats.get("wfa_figure"),
                        stats.get("wfa_status"),
                        stats.get("hfa_figure"),
                        stats.get("hfa_status"),
                        stats.get("wfh_figure"),
                        stats.get("wfh_status"),
                        stats.get("bmifa_figure"),
                        stats.get("bmifa_status"),
                    ),
                )

            conn.commit()
            return True
    except Exception as e:
        logger.error("sync_baseline failed: %s", e, exc_info=True)
        return False
    finally:
        conn.close()


def update_birthday_db(beneficiary_id, new_birthday):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Update the birthday in beneficiaries
            cursor.execute(
                "UPDATE beneficiaries SET birthday = %s WHERE beneficiary_id = %s",
                (new_birthday, beneficiary_id),
            )

            # 2. Get latest baseline info to recalculate anthro
            cursor.execute(
                """
                SELECT bl.info_id, bl.weight, bl.height, bl.date_collected, b.gender 
                FROM baseline_info bl
                JOIN beneficiaries b ON bl.beneficiary_id = b.beneficiary_id
                WHERE bl.beneficiary_id = %s
                ORDER BY bl.created_at DESC LIMIT 1
            """,
                (beneficiary_id,),
            )

            item = cursor.fetchone()
            if item and item.get("weight") and item.get("height"):
                ref_date = datetime.date.today()
                if item.get("date_collected"):
                    try:
                        ref_date = datetime.datetime.strptime(
                            item["date_collected"], "%Y-%m-%d"
                        ).date()
                    except (ValueError, TypeError):
                        pass

                bday_dt = datetime.datetime.strptime(new_birthday, "%Y-%m-%d").date()
                age_in_months = (
                    (ref_date.year - bday_dt.year) * 12 + ref_date.month - bday_dt.month
                )

                try:
                    from backend.anthro_utils import calculate_anthro_stats
                except ImportError:
                    from anthro_utils import calculate_anthro_stats

                stats = calculate_anthro_stats(
                    age_in_months, item["gender"], item["weight"], item["height"]
                )

                # 3. Update baseline_info
                sql = """
                UPDATE baseline_info SET 
                    age = %s,
                    wfa_figure = %s, wfa_status = %s, 
                    hfa_figure = %s, hfa_status = %s, 
                    wfh_figure = %s, wfh_status = %s, 
                    bmifa_figure = %s, bmifa_status = %s, 
                    updated_at = NOW()
                WHERE info_id = %s
                """
                cursor.execute(
                    sql,
                    (
                        age_in_months,
                        stats.get("wfa_figure"),
                        stats.get("wfa_status"),
                        stats.get("hfa_figure"),
                        stats.get("hfa_status"),
                        stats.get("wfh_figure"),
                        stats.get("wfh_status"),
                        stats.get("bmifa_figure"),
                        stats.get("bmifa_status"),
                        item["info_id"],
                    ),
                )

            conn.commit()
            return True
    except Exception as e:
        logger.error("update_birthday_db failed: %s", e, exc_info=True)
        return False
    finally:
        conn.close()


def update_name_db(beneficiary_id, lastname, firstname, middlename):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE beneficiaries 
                SET lastname = %s, firstname = %s, middlename = %s 
                WHERE beneficiary_id = %s
            """,
                (lastname, firstname, middlename, beneficiary_id),
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error("update_name_db failed: %s", e, exc_info=True)
        return False
    finally:
        conn.close()


def get_surname_dictionary():
    """
    Fetches all unique lastnames and middlenames from the database to create a dictionary of valid surnames.
    This is used to intelligently parse compound first names vs middle names.
    """  # noqa: E501
    conn = get_db_connection()
    surnames = set()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT lastname FROM beneficiaries WHERE lastname IS NOT NULL AND lastname != ''"  # noqa: E501
            )
            for row in cursor.fetchall():
                surnames.add(row["lastname"].strip().upper())

            cursor.execute(
                "SELECT DISTINCT middlename FROM beneficiaries WHERE middlename IS NOT NULL AND middlename != ''"  # noqa: E501
            )
            for row in cursor.fetchall():
                surnames.add(row["middlename"].strip().upper())
    except Exception as e:
        logger.error("get_surname_dictionary failed: %s", e, exc_info=True)
    finally:
        conn.close()
    return surnames


def _random_beneficiary_id():
    import random
    import string

    return "".join(random.choices(string.ascii_lowercase + string.digits, k=10))


def generate_beneficiary_id(cursor=None, max_attempts: int = 10) -> str:
    if cursor is None:
        for _ in range(max_attempts):
            bid = _random_beneficiary_id()
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM beneficiaries WHERE beneficiary_id = %s LIMIT 1",
                        (bid,),
                    )
                    if not cur.fetchone():
                        return bid
            finally:
                conn.close()
        raise RuntimeError("Could not generate unique beneficiary_id")

    for _ in range(max_attempts):
        bid = _random_beneficiary_id()
        cursor.execute(
            "SELECT 1 FROM beneficiaries WHERE beneficiary_id = %s LIMIT 1",
            (bid,),
        )
        if not cursor.fetchone():
            return bid
    raise RuntimeError("Could not generate unique beneficiary_id")


def authenticate_user(access_code, email=None):
    try:
        conn = get_db_connection()
    except FileNotFoundError:
        conn = _get_cloud_connection()

    try:
        with conn.cursor() as cursor:
            if email:
                cursor.execute(
                    "SELECT user_id, firstname, lastname, role, email FROM users "
                    "WHERE access_code = %s AND email = %s AND deleted_at IS NULL",
                    (access_code, email),
                )
            else:
                cursor.execute(
                    "SELECT user_id, firstname, lastname, role, email FROM users "
                    "WHERE access_code = %s AND deleted_at IS NULL",
                    (access_code,),
                )
            return cursor.fetchone()
    except Exception as e:
        logger.error("authenticate_user failed: %s", e, exc_info=True)
        return None
    finally:
        conn.close()


def check_email_exists(email):
    try:
        conn = get_db_connection()
    except FileNotFoundError:
        conn = _get_cloud_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT user_id FROM users WHERE email = %s AND deleted_at IS NULL",
                (email,),
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error("check_email_exists failed: %s", e, exc_info=True)
        return False
    finally:
        conn.close()


def add_beneficiary_to_db(
    site_id,
    lastname,
    firstname,
    middlename,
    birthday,
    gender,
    weight,
    height,
    date_collected,
    created_by,
):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            beneficiary_id = generate_beneficiary_id(cursor)
            reg_date = datetime.date.today().strftime("%Y-%m-%d")

            # Insert into beneficiaries
            sql_ben = """
            INSERT INTO beneficiaries (beneficiary_id, lastname, firstname, middlename, birthday, gender, registration_date, site_id, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """  # noqa: E501
            cursor.execute(
                sql_ben,
                (
                    beneficiary_id,
                    lastname,
                    firstname,
                    middlename,
                    birthday,
                    gender.upper(),
                    reg_date,
                    site_id,
                    created_by,
                ),
            )

            # Insert into baseline_info
            if weight and height:
                ref_date = datetime.date.today()
                if date_collected:
                    try:
                        ref_date = datetime.datetime.strptime(
                            date_collected, "%Y-%m-%d"
                        ).date()
                    except (ValueError, TypeError):
                        pass

                bday_dt = datetime.datetime.strptime(birthday, "%Y-%m-%d").date()
                age_in_months = (
                    (ref_date.year - bday_dt.year) * 12 + ref_date.month - bday_dt.month
                )

                try:
                    from backend.anthro_utils import calculate_anthro_stats
                except ImportError:
                    from anthro_utils import calculate_anthro_stats

                stats = calculate_anthro_stats(
                    age_in_months, gender.upper(), weight, height
                )

                info_id = generate_beneficiary_id(cursor)
                sql_bl = """
                INSERT INTO baseline_info (
                    info_id, beneficiary_id, gender, weight, height, age, date_collected,
                    wfa_figure, wfa_status, hfa_figure, hfa_status,
                    wfh_figure, wfh_status, bmifa_figure, bmifa_status,
                    created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """  # noqa: E501
                cursor.execute(
                    sql_bl,
                    (
                        info_id,
                        beneficiary_id,
                        gender.upper(),
                        weight,
                        height,
                        age_in_months,
                        date_collected,
                        stats.get("wfa_figure"),
                        stats.get("wfa_status"),
                        stats.get("hfa_figure"),
                        stats.get("hfa_status"),
                        stats.get("wfh_figure"),
                        stats.get("wfh_status"),
                        stats.get("bmifa_figure"),
                        stats.get("bmifa_status"),
                        created_by,
                    ),
                )

            conn.commit()
            return True, beneficiary_id
    except Exception as e:
        logger.error("add_beneficiary_to_db failed: %s", e, exc_info=True)
        return False, str(e)
    finally:
        conn.close()


def get_beneficiary_related_counts(beneficiary_id):
    """Returns record counts for all related tables for a given beneficiary_id."""
    conn = get_db_connection()
    try:
        counts = {}
        with conn.cursor() as cursor:
            tables = [
                ("feeding_records", "feeding_records"),
                ("baseline_info", "baseline_info"),
                ("beneficiaries_height_weight", "height_weight_records"),
                ("parents_beneficiaries", "parent_links"),
                ("consecutive_absences", "absence_records"),
            ]
            for table, label in tables:
                try:
                    cursor.execute(
                        f"SELECT COUNT(*) AS cnt FROM `{table}` WHERE beneficiary_id = %s",  # noqa: E501
                        (beneficiary_id,),
                    )
                    counts[label] = cursor.fetchone()["cnt"]
                except Exception:
                    counts[label] = "N/A"
        return counts
    finally:
        conn.close()


def delete_beneficiary_cascade(beneficiary_id):
    """Hard-deletes a beneficiary and all related records in the correct dependency order."""  # noqa: E501
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Delete child tables first, then the parent
            for table in [
                "feeding_records",
                "baseline_info",
                "beneficiaries_height_weight",
                "parents_beneficiaries",
                "consecutive_absences",
            ]:
                try:
                    cursor.execute(
                        f"DELETE FROM `{table}` WHERE beneficiary_id = %s",
                        (beneficiary_id,),
                    )
                except Exception as e:
                    logger.warning("cascade delete on %s: %s", table, e)
            cursor.execute(
                "DELETE FROM beneficiaries WHERE beneficiary_id = %s", (beneficiary_id,)
            )
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def find_beneficiaries_by_name(lastname: str, firstname: str):
    """
    Returns all beneficiary records whose lastname AND firstname match (case-insensitive).
    Includes related record counts for each match.
    """  # noqa: E501
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    b.beneficiary_id, b.lastname, b.firstname, b.middlename,
                    b.birthday, b.gender, s.site_name,
                    (SELECT COUNT(*) FROM feeding_records       fr WHERE fr.beneficiary_id = b.beneficiary_id) AS feeding_records,
                    (SELECT COUNT(*) FROM baseline_info         bi WHERE bi.beneficiary_id = b.beneficiary_id) AS baseline_info,
                    (SELECT COUNT(*) FROM beneficiaries_height_weight hw WHERE hw.beneficiary_id = b.beneficiary_id) AS height_weight_records,
                    (SELECT COUNT(*) FROM parents_beneficiaries pb WHERE pb.beneficiary_id = b.beneficiary_id) AS parent_links,
                    (SELECT COUNT(*) FROM consecutive_absences  ca WHERE ca.beneficiary_id = b.beneficiary_id) AS absence_records
                FROM beneficiaries b
                LEFT JOIN sites s ON b.site_id = s.site_id
                WHERE UPPER(TRIM(b.lastname))  = UPPER(TRIM(%s))
                  AND UPPER(TRIM(b.firstname)) = UPPER(TRIM(%s))
            """,  # noqa: E501
                (lastname, firstname),
            )
            rows = cursor.fetchall()
            for r in rows:
                if isinstance(r.get("birthday"), (datetime.date, datetime.datetime)):
                    r["birthday"] = r["birthday"].strftime("%Y-%m-%d")
            return rows
    finally:
        conn.close()


def bulk_transfer_beneficiaries(
    beneficiary_ids: list, target_site_id: str
) -> tuple[bool, str | None]:
    """
    Bulk transfers a list of beneficiaries to a target site.
    Returns (success, error_message).
    """
    if not beneficiary_ids:
        return False, "No beneficiaries selected for transfer."

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            placeholders = ", ".join(["%s"] * len(beneficiary_ids))
            sql = f"UPDATE beneficiaries SET site_id = %s WHERE beneficiary_id IN ({placeholders})"  # noqa: E501
            cursor.execute(sql, [target_site_id] + list(beneficiary_ids))
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        logger.error("bulk_transfer_beneficiaries failed: %s", e, exc_info=True)
        return False, str(e)
    finally:
        conn.close()


def get_beneficiaries_by_site(site_id: str) -> list:
    """
    Fetches all active (non-deleted) beneficiaries registered to a specific site_id.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT 
                    b.beneficiary_id,
                    b.lastname,
                    b.firstname,
                    b.middlename,
                    b.birthday,
                    b.gender,
                    b.registration_date,
                    s.site_name,
                    br.barangay_name
                FROM beneficiaries b
                LEFT JOIN sites s ON b.site_id = s.site_id
                LEFT JOIN barangays br ON s.barangay_code = br.barangay_code
                WHERE b.site_id = %s AND b.deleted_at IS NULL
                ORDER BY b.lastname, b.firstname
            """
            cursor.execute(sql, (site_id,))
            rows = cursor.fetchall()
            for r in rows:
                if isinstance(r.get("birthday"), (datetime.date, datetime.datetime)):
                    r["birthday"] = r["birthday"].strftime("%Y-%m-%d")
                if isinstance(
                    r.get("registration_date"), (datetime.date, datetime.datetime)
                ):
                    r["registration_date"] = r["registration_date"].strftime("%Y-%m-%d")
            return rows
    finally:
        conn.close()
