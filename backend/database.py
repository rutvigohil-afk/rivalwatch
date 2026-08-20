import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "rivalwatch.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def create_tables():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price REAL,
            currency TEXT,
            rating REAL,
            reviews INTEGER,
            url TEXT,
            scraped_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            change_type TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            percentage REAL,
            detected_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scraper_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            products_found INTEGER,
            error TEXT,
            timestamp TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_tables()
    print("Database created successfully!")