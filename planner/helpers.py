import random
import json
from datetime import datetime
BASE_TIME = datetime(2018, 1, 1, 0, 0, 0)

RESOURCE_MAPPING = {
    "surgery": "OR",
    "nursing_a": "A_BED",
    "nursing_b": "B_BED",
    "intake": "INTAKE",
    "er_treatment": "ER_PRACTITIONER"
}

def convert_to_hours_since_2018(time):
    """
    Convert ISO 8601 datetime string to hours since 01.01.2018 0:00.
    
    :param time (str): ISO 8601 datetime string
    :return: float: Hours since 01.01.2018 0:00
    """
    target_time = datetime.fromisoformat(time)
    delta = target_time - BASE_TIME
    return delta.total_seconds() / 3600
 
def load_patient_types(path):
    with open(path, 'r') as file:
        return json.load(file)['patient_types']
    
def load_max_capacities(path):
    with open(path, 'r') as file:
        resources = json.load(file)['resources']
        max_capacities = {}
        for resource in resources:
            max_capacities[resource['resource_type']] = resource['capacity']
        max_capacities_remapped = {}
        for name, capacity in max_capacities.items():
            max_capacities_remapped[RESOURCE_MAPPING[name]] = capacity
        return max_capacities_remapped
    
def convert_from_my_resources(resource):
    return RESOURCE_MAPPING[resource]
    

def float_range(start, stop, step):
    while start < stop:
        yield start
        start += step

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
