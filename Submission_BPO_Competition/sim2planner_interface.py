from datetime import datetime, timedelta
from evolution import evolve

BASE_TIME = datetime(2018, 1, 1, 0, 0, 0)

def convert_to_iso8601(simulation_time):
    """
    Convert simulation time (hours since 01.01.2018 0:00) to ISO 8601 datetime string.
    
    :param simulation_time (float): Hours since 01.01.2018 0:00
    :return: ISO 8601 datetime string
    """
    if type(simulation_time) == str:
        simulation_time = float(simulation_time)
    delta = timedelta(hours=simulation_time)
    target_time = BASE_TIME + delta
    return target_time.isoformat()

def convert_to_hours_since_2018(time):
    """
    Convert ISO 8601 datetime string to hours since 01.01.2018 0:00.
    
    :param time (str): ISO 8601 datetime string
    :return: float: Hours since 01.01.2018 0:00
    """
    target_time = datetime.fromisoformat(time)
    delta = target_time - BASE_TIME
    return delta.total_seconds() / 3600

def convert_to_my_resources(resource_info):
    """converts the resource names from the simulator to the names used in the planner

    :pram: resource_info (list): list of json hashes in format {"cid", "task", "start", "info", "wait"}
    
    :returns: list: list of json hashes in format {"cid", "task", "start", "info", "wait"} with converted task names
    """
    resource_mapping = {
        "OR": "surgery",
        "A_BED": "nursing_a",
        "B_BED": "nursing_b",
        "INTAKE": "intake",
        "ER_PRACTITIONER": "er_treatment"
    }
    resources_remapped = {}
    for name, occupation in resource_info.items():
        resources_remapped[resource_mapping[name]] = occupation
    return resources_remapped

def get_available_resources(resources):
    resource_counts = {'OR': 0, 'A_BED': 0, 'B_BED': 0, 'INTAKE': 0, 'ER_PRACTITIONER': 0}
    for resource in resources:
        resource_counts[resource.type] += 1
    return resource_counts

def simulate_endpoint(available_info, replanned_patients, max_capacities):
    """
    Function to simulate the endpoint
    
    :param: available_info (dictionary): dictionary with keys 'cid', 'time', 'info', 'resources'
    :return: float: Hours since 01.01.2018 0:00
    """
    current_time_iso = available_info['time']
    current_time_dt = datetime.fromisoformat(current_time_iso)

    info = available_info['info']
    patients_to_replan = dict()
    patients_to_replan[available_info['cid']] = {
        "diagnosis": info["diagnosis"],
        "sent_home_counter": info["sent_home_counter"],
        "first_admission_time": datetime.fromisoformat(info["first_admission_time"]),
        "last_replan_time": datetime.fromisoformat(info["last_replan_time"]),
        "min_replan_time": (current_time_dt + timedelta(hours=24, seconds=1)),
        "new_admission_time": (current_time_dt + timedelta(hours=24, seconds=1))
    }
    
    replanned_patients = evolve(patients_to_replan, replanned_patients, available_info['resources'], max_capacities, current_time_dt)
    
    replan_time_iso = replanned_patients[available_info['cid']]["new_admission_time"]
    replan_time_rel = convert_to_hours_since_2018(replan_time_iso)
    
    return replan_time_rel, replanned_patients