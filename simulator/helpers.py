import random
import json
import requests
import sys
sys.path.append('../')
from db.db_util import get_db, DATABASE_RESOURCES
 
def load_patient_types(path):
    with open(path, 'r') as file:
        return json.load(file)['patient_types']

def float_range(start, stop, step):
    while start < stop:
        yield start
        start += step

def create_cpee_instance(patient_type, arrival_time, patient_id=None, xml_url="https://cpee.org/hub/server/Teaching.dir/Prak.dir/Challengers.dir/Martin_Schmauch.dir/MainMPS.xml"):
    url = "https://cpee.org/flow/start/url/"
    if patient_id is not None: # patient coming from replan
        # init_data = "{\"patient_type\": \"" + patient_type + "\", \"arrival_time\": \"" + str(arrival_time) + "\", \"patient_id\": \"" + str(patient_id) + "\"}"
        init_data = json.dums({"patient_type": patient_type, "arrival_time": arrival_time, "patient_id": patient_id})
    else: # patient coming from initial creation
        # init_data = "{\"patient_type\": \"" + patient_type + "\", \"arrival_time\": \"" + str(arrival_time) + "\"}"
        init_data = json.dumps({"patient_type": patient_type, "arrival_time": arrival_time})
    data = {"behavior": "fork_running",
            "url": xml_url,
            "init": init_data,
            }
    response = requests.post(url, data=data)
    response_json = response.json()
    process_id = response_json["CPEE-INSTANCE"]
    return process_id


    
def get_next_available_resource(resource_type, current_time): # TODO
    conn = get_db(DATABASE_RESOURCES)
    cursor = conn.cursor()
    cursor.execute("SELECT resource_name, available_at FROM Resources WHERE resource_type = ? and available_at <= ? ORDER BY available_at LIMIT 1", (resource_type, current_time))
    row = cursor.fetchone()
    if row is None:
        raise Exception("Error while trying to get next available resource")
    result = (row['available_at'] , row['resource_name'])
    conn.close()
    return result

def get_queue_length(resource_type):
    conn = get_db(DATABASE_RESOURCES)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM queue WHERE resource_type = ?", (resource_type,))
    row = cursor.fetchone()
    if row is None:
        raise Exception("Error while trying to get queue length")
    result = row[0]
    conn.close()
    return result

def pop_queue(resource_type):
    conn = get_db(DATABASE_RESOURCES)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM queue WHERE resource_type = ? ORDER BY priority, request_time LIMIT 1", (resource_type,))
    row = cursor.fetchone()
    if row is None:
        raise Exception("Error while trying to pop queue")
    cursor.execute("DELETE FROM queue WHERE patient_id = ?", (row["patient_id"],))
    conn.commit()
    conn.close()
    return row

def get_patient_diagnose(patient_type):
    random_value = random.uniform(0, 1)
    if patient_type == "A":
        if random_value < 0.5:
            return "A1"
        elif random_value < 0.75:
            return "A2"
        elif random_value < 0.875:
            return "A3"
        else:
            return "A4"
    elif patient_type == "B":
        if random_value < 0.5:
            return "B1"
        elif random_value < 0.75:
            return "B2"
        elif random_value < 0.875:
            return "B3"
        else:
            return "B4"
    elif patient_type == "EM":
        return "ER"
    else:
        raise Exception("Invalid patient type")
        
def get_random_patient():
    patient = random.choice(['ER', 'A', 'B'])
    if patient in ['A', 'B']:
        return get_patient_diagnose(patient)
    else:
        return 'ER'
        
def get_ER_diagnose():
    phantom_pain = random.choice([True, False])
    if phantom_pain:
        return "ER_phantom_pain"
    else:
        res = "ER_" + get_patient_diagnose("B")
        return res

def get_complications(patient_type):
    random_value = random.uniform(0, 1)
    complications = "False"
    if patient_type.startswith("ER"):
        patient_type = patient_type[-2:]
    if patient_type in ["A1", "A2", "B2"]:
        if random_value < 0.01:
            complications = "True"
    elif patient_type in ["A3", "A4", "B3", "B4"]:
        if random_value < 0.02:
            complications = "True"
    elif patient_type == "B1":
        if random_value < 0.001:
            complications = "True"
    else: 
        raise Exception("Invalid patient type")
    return complications

def get_task_duration(patient_types_config, patient_type, resource_type):
    if resource_type == "er_treatment":
        return max(0.0, random.normalvariate(2, 0.5))
    elif resource_type == "intake":
        return max(0.0, random.normalvariate(1, 0.125))
    else:
        if patient_type.startswith("ER"):
            patient_type = patient_type[-2:]
        for pt in patient_types_config:
            if pt['diagnosis'] == patient_type:
                if resource_type == "surgery":
                    return max(0.0, random.normalvariate(pt['operation_time_mean'], pt['operation_time_std']))
                elif resource_type.startswith("nursing"):
                    return max(0.0, random.normalvariate(pt['nursing_time_mean'], pt['nursing_time_std']))
                else:
                    raise Exception("Invalid resource type")

def generate_response_text(finish_time, patient_type, resource_type):
    if resource_type == "er_treatment":
        er_patient_type = get_ER_diagnose()
        return {"patient_type": er_patient_type, "finish_time": finish_time}  
    elif resource_type == "intake":
        return {"finish_time": finish_time}
    elif resource_type == "surgery":
        return {"finish_time": finish_time}
    elif resource_type.startswith("nursing"):
        complication = get_complications(patient_type)
        return {"complication": complication, "finish_time": finish_time}
    else: 
        raise Exception("Invalid resource type")