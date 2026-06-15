import sqlite3

def init_db():
    conn = sqlite3.connect("portal.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sesiones (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente   TEXT NOT NULL,
            tipo      TEXT NOT NULL,
            fecha     TEXT NOT NULL,
            token     TEXT UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fotos (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            sesion_id  INTEGER NOT NULL,
            filename   TEXT NOT NULL,
            FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
        )
    """)

    conn.commit()
    conn.close()


def get_conn():
    return sqlite3.connect("portal.db")


if __name__ == "__main__":
    init_db()
    print("Base de datos creada.")