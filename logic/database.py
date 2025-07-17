
from pathlib import Path
import sys
import sqlite3
import shutil
import bcrypt

def get_db_path():
    try:
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent / "data"
            base_path.mkdir(exist_ok=True, parents=True)
            db_path = base_path / "meds.db"

            if not db_path.exists():
                # pyrefly: ignore  # missing-attribute
                meipass = getattr(sys, '_MEIPASS', None)
                if meipass:
                    internal_db = Path(meipass) / "data" / "meds.db"
                else:
                    internal_db = None
                if internal_db is not None and internal_db.exists():
                    shutil.copy(internal_db, db_path)
                    print(f"📦 Copiado banco empacotado para: {db_path}")
                else:
                    print(f"⚠️ Banco empacotado não encontrado em: {internal_db}")
                print(f"Caminho do DB (modo frozen): {db_path}")
            return db_path
        else:
            base_path = Path(__file__).parent.parent / "data"
            base_path.mkdir(exist_ok=True, parents=True)
            db_path = base_path / "meds.db"
            print("DB path (dev):", db_path)
            return db_path
    except Exception as e:
        print(f"❌ Erro ao determinar o caminho do banco de dados: {e}")
        return Path("data/meds.db")  # fallback padrão


def connect_db(db_path=None):
    db_path = db_path or get_db_path()
    print("📌 Caminho recebido para o banco:", db_path)  # <-- Adicione isso
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    with connect_db() as conn:
        cursor = conn.cursor()
        # Cria tabela de usuários (e-mail único, senha hash)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        # Cria tabela de medicamentos com user_id
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                dosage_per_intake REAL NOT NULL,
                type TEXT,
                schedule TEXT,
                packaging TEXT,
                quantity_per_package INTEGER NOT NULL,
                stock_in_units INTEGER NOT NULL,
                status TEXT,
                is_reference INTEGER,
                prescription_expiry DATE,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        conn.commit()

# Funções de usuário
def create_user(email, password, db_path=None):
    db_path = db_path or get_db_path()
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with connect_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, password_hash))
        conn.commit()
        return cursor.lastrowid

def get_user_by_email(email, db_path=None):
    db_path = db_path or get_db_path()
    with connect_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        return cursor.fetchone()

def validate_user(email, password, db_path=None):
    db_path = db_path or get_db_path()
    user = get_user_by_email(email, db_path)
    if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return user
    return None


def insert_medication(
    user_id,
    name,
    dosage_per_intake,
    med_type,
    schedule,
    packaging,
    quantity_per_package,
    stock_in_units,
    status,
    is_reference,
    prescription_expiry,
    db_path=None
):
    db_path = db_path or get_db_path()
    with connect_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO medications (
                user_id,
                name,
                dosage_per_intake,
                type,
                schedule,
                packaging,
                quantity_per_package,
                stock_in_units,
                status,
                is_reference,
                prescription_expiry
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            name,
            dosage_per_intake,
            med_type,
            schedule,
            packaging,
            quantity_per_package,
            stock_in_units,
            status,
            is_reference,
            prescription_expiry
        ))
        conn.commit()
def fetch_all_medications(user_id=None, db_path=None):
    db_path = db_path or get_db_path()
    with connect_db(db_path) as conn:
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute("SELECT * FROM medications WHERE user_id = ?", (user_id,))
        else:
            cursor.execute("SELECT * FROM medications")
        return cursor.fetchall()
def get_medication_by_id(med_id, db_path=None):
    db_path = db_path or get_db_path()
    with connect_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medications WHERE id = ?", (med_id,))
        return cursor.fetchone()
def update_stock(med_id, new_stock, db_path=None):
    db_path = db_path or get_db_path()
    with connect_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE medications SET stock_in_units = ? WHERE id = ?", (new_stock, med_id))  # noqa: E501
        conn.commit()
def delete_medication(med_id, db_path=None):
    db_path = db_path or get_db_path()
    with connect_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM medications WHERE id = ?", (med_id,))
        conn.commit()

