import sqlite3

def create_resource_db():
    conn = sqlite3.connect('resources.db')
    cursor = conn.cursor()
    
    # Create the resources table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Resources (
            resource_name TEXT PRIMARY KEY,
            resource_type TEXT NOT NULL,
            available_at REAL NOT NULL
        )
    ''')

    # Create the queue table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            priority INTEGER NOT NULL,
            request_time REAL NOT NULL,
            callback_url TEXT NOT NULL,
            patient_id INTEGER NOT NULL,
            patient_type TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            FOREIGN KEY (resource_type) REFERENCES Resources (resource_type)
        )
    ''')

    conn.commit()
    conn.close()

create_resource_db()
print("Database and tables created successfully.")
