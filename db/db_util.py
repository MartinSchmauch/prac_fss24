import sqlite3
import json

DATABASE_RESOURCES = './db/resources/resources.db'
DATABASE_PATIENTS = './db/patients/patient.db'

def get_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_resources(config_file='./db/resources/resource_config.json', db_file='./db/resources/resources.db'):
    with open(config_file, 'r') as file:
        config = json.load(file)
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM Resources
    ''')
    # show all column names
    for resource_type in config['resources']: # default resource initialization
        for resource_index in range(resource_type['capacity']):
            resource_name = f"{resource_type['resource_type']}_{resource_index}"
            cursor.execute('''
                INSERT OR REPLACE INTO Resources (resource_name, resource_type, available_at)
                VALUES (?, ?, ?)
            ''', (resource_name, resource_type['resource_type'], resource_type['available_at']))
    # for resource_item in config['resource_planning']: # override specific resources
    #     cursor.execute('''
    #             INSERT OR REPLACE INTO Resources (resource_name, resource_type, available_at)
    #             VALUES (?, ?, ?)
    #         ''', (resource_item['resource_name'], resource_item['resource_type'], resource_item['available_at']))
    # reset queue table
    cursor.execute('''
        DELETE FROM Queue
    ''')
    conn.commit()
    conn.close()