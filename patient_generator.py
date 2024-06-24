from helpers import float_range, load_patient_types, get_patient_diagnose
import random

class Patient_Generator():
    def __init__(self, runtime):
        self.runtime = runtime
        self.patient_types = load_patient_types('patient_types.json')
        
    
    def generate_patients(self):
        # patient_arrival_rate_dict = {pt["type"]: pt["arrival_rate"] for pt in self.patient_types}
        patient_arrival_rate_dict = {}
        for  pt in self.patient_types:
            if pt["type"] not in patient_arrival_rate_dict.keys():
                patient_arrival_rate_dict[pt["type"]] = pt["arrival_rate"]
        patients = []
        for i in float_range(0.0, self.runtime, 1.0):  # Iterate through each time unit
            for patient_type, arrival_rate_func_str in patient_arrival_rate_dict.items():
                # Convert the string representation of the function to a callable function
                arrival_rate_func = eval(f"lambda: {arrival_rate_func_str}")
                # Evaluate the function to get the specific time point within the time unit
                arrival_time_point = i + arrival_rate_func()
                patient_diagnose = get_patient_diagnose(patient_type)
                patients.append((arrival_time_point, patient_diagnose))  # Store the arrival time and patient type
        return patients