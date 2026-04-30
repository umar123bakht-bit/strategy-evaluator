import sqlite3
import json

DB_PATH = "strategy_data.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            industry TEXT NOT NULL,
            description TEXT,
            target_market TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id INTEGER NOT NULL,
            deck_name TEXT NOT NULL,
            overall_score INTEGER,
            verdict TEXT,
            results_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (brand_id) REFERENCES brands(id)
        )
    """)
    conn.commit()
    conn.close()


def add_brand(name, industry, description, target_market):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO brands (name, industry, description, target_market) VALUES (?, ?, ?, ?)",
            (name, industry, description, target_market),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_brands():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM brands ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_brand(brand_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM brands WHERE id = ?", (brand_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_brand(brand_id, name, industry, description, target_market):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE brands SET name=?, industry=?, description=?, target_market=? WHERE id=?",
            (name, industry, description, target_market, brand_id),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def delete_brand(brand_id):
    conn = get_connection()
    conn.execute("DELETE FROM analyses WHERE brand_id = ?", (brand_id,))
    conn.execute("DELETE FROM brands WHERE id = ?", (brand_id,))
    conn.commit()
    conn.close()


def save_analysis(brand_id, deck_name, overall_score, verdict, results_json):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO analyses (brand_id, deck_name, overall_score, verdict, results_json) VALUES (?, ?, ?, ?, ?)",
        (brand_id, deck_name, overall_score, verdict, json.dumps(results_json)),
    )
    analysis_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return analysis_id


def get_analyses(brand_id=None):
    conn = get_connection()
    if brand_id:
        rows = conn.execute(
            """SELECT a.*, b.name as brand_name, b.industry
               FROM analyses a JOIN brands b ON a.brand_id = b.id
               WHERE a.brand_id = ? ORDER BY a.created_at DESC""",
            (brand_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT a.*, b.name as brand_name, b.industry
               FROM analyses a JOIN brands b ON a.brand_id = b.id
               ORDER BY a.created_at DESC"""
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_analysis(analysis_id):
    conn = get_connection()
    row = conn.execute(
        """SELECT a.*, b.name as brand_name, b.industry, b.description, b.target_market
           FROM analyses a JOIN brands b ON a.brand_id = b.id
           WHERE a.id = ?""",
        (analysis_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_analysis(analysis_id):
    conn = get_connection()
    conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    conn.commit()
    conn.close()
