import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "portal.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sesiones (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente     TEXT NOT NULL,
            tipo        TEXT NOT NULL,
            fecha       TEXT NOT NULL,
            token       TEXT NOT NULL UNIQUE,
            mensaje     TEXT,
            portada_url TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fotos (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            sesion_id      INTEGER NOT NULL,
            filename       TEXT NOT NULL,
            cloudinary_url TEXT,
            public_id      TEXT,
            FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
        )
    """)
    # Migraciones
    for col in [
        "ALTER TABLE fotos ADD COLUMN cloudinary_url TEXT",
        "ALTER TABLE fotos ADD COLUMN public_id TEXT",
        "ALTER TABLE sesiones ADD COLUMN mensaje TEXT",
        "ALTER TABLE sesiones ADD COLUMN portada_url TEXT",
    ]:
        try:
            conn.execute(col)
        except Exception:
            pass
    conn.commit()
    conn.close()