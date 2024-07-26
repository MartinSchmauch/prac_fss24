import random
import json
 
def load_patient_types(path):
    with open(path, 'r') as file:
        return json.load(file)['patient_types']

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
