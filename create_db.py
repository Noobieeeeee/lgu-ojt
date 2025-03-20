import sqlite3
from werkzeug.security import generate_password_hash

def init_db():
    conn = sqlite3.connect('crud_system.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            enduser TEXT NOT NULL
        )
    ''')
    
    # Create entry table
    c.execute('''
        CREATE TABLE IF NOT EXISTS entry (
            JEV TEXT PRIMARY KEY,
            Payee TEXT NOT NULL,
            ObligationRequest TEXT NOT NULL,
            AccountsPayable TEXT,
            Particulars TEXT,
            Amount REAL,
            "Date Entry" TEXT,
            "Date Received" TEXT
        )
    ''')
    
    # Insert default admin user
    try:
        c.execute('''
            INSERT INTO users (username, password, enduser)
            VALUES (?, ?, ?)
        ''', ('admin', generate_password_hash('admin123'), 'Xy'))
        conn.commit()
    except sqlite3.IntegrityError:
        print("Admin user already exists")
    
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!") 