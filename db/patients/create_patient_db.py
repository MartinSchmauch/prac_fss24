import sqlite3

def create_database():
    conn = sqlite3.connect('patient.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Patient (
            id INTEGER PRIMARY KEY,
            patient_type TEXT NOT NULL,
            diagnosis TEXT,
            admission_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_database()
    print("Database and table created successfully.")