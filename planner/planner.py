
import bottle
import requests
import json
from datetime import datetime, timedelta
from evolution import evolve
from helpers import convert_to_hours_since_2018, load_max_capacities, convert_from_my_resources

RESOURCE_CONFIG_PATH = "../db/resources/resource_config.json"

@bottle.route('/replan_patient', method='POST') 
def replan_patient():
    req = bottle.request
    cid = req.forms.cid # Case ID
    current_time = datetime.fromisoformat(req.forms.time) # Current Time (ISO 8601, XML Schema DataTime format)
    info = json.loads(req.forms.get('info')) # json hash - can contain arbitrary keys e.g. "diagnosis"
    resources = json.loads(req.forms.resources) # list of json hashes - fixed structure [("cid", "task", "start", "info", "wait")]
    # callback_url = req.headers['CPEE-CALLBACK']
    # planner.plan_patient(cid, current_time, info, resources, callback_url)
    # return bottle.HTTPResponse(
    #     json.dumps({'Ack.:': 'Response later'}),
    #     status=202,
    #     headers={'content-type': 'application/json', 'CPEE-CALLBACK': 'true'}
    #     )
    return planner.plan_patient(cid, current_time, info, resources)


class Planner:
    def __init__(self):
        self.super = super()
        self.replanned_patients = {}
        self.patients_to_replan = {}
        self.max_capacities = load_max_capacities(RESOURCE_CONFIG_PATH) 
    
    def plan_patient(self, cid, current_time, info, resources, callback_url=None):
        """
        Function to plan the patient
        
        :param: cid (Integer): Case ID
        :param: time (String): current time in ISO 8601, XML Schema DataTime format
        :param: info (dictionary): json hash - can contain arbitrary keys e.g. "diagnosis"
        :param: resources (list): list of json hashes - fixed structure {"cid", "task", "start", "info", "wait"}
        
        :return: String: replan_time_iso: ISO 8601, XML Schema DataTime format
        """
        # convert current_time to datetime object
        current_time_dt = datetime.fromisoformat(current_time)
        
        # convert resource names from the simulator to the names used in the planner
        for resource in resources:
            resource['task'] = convert_from_my_resources['task']
        
        # clean up replanned_patients dictionary
        for cid_replanned in list(self.replanned_patients.keys()):
            replan_time = convert_to_hours_since_2018(self.replanned_patients[cid_replanned]["new_admission_time"])
            current_time_rel = convert_to_hours_since_2018(current_time)
            if (replan_time <= current_time_rel) and (cid_replanned != cid):
                del self.replanned_patients[cid_replanned]
        
        # update the replanned_patients dictionary
        if cid in self.replanned_patients.keys(): 
            info['sent_home_counter'] = self.replanned_patients[cid]["sent_home_counter"] + 1
            info['first_admission_time'] = self.replanned_patients[cid]["first_admission_time"]
            info['last_replan_time'] = self.replanned_patients[cid]["new_admission_time"]
            # patient gets replanned and will not be considered during replanning as potential collusion complication as other patients are in the replanned_patients dict
            del self.replanned_patients[cid] 
        else:
            info['sent_home_counter'] = 1
            info['first_admission_time'] = current_time
            info['last_replan_time'] = current_time
        
        # add patient to patients_to_replan dictionary
        self.patients_to_replan[cid] = {
            "diagnosis": info["diagnosis"],
            "sent_home_counter": info["sent_home_counter"],
            "first_admission_time": datetime.fromisoformat(info["first_admission_time"]),
            "last_replan_time": datetime.fromisoformat(info["last_replan_time"]),
            "min_replan_time": (current_time_dt + timedelta(hours=24, seconds=1)),
            "new_admission_time": (current_time_dt + timedelta(hours=24, seconds=1))
        }
        
        # Evolutionary Algorithm
        replanned_patients = evolve(self.patients_to_replan, self.replanned_patients, resources, self.max_capacities, current_time)
        replan_time_iso = replanned_patients[cid]["new_admission_time"]
        replan_time_rel = convert_to_hours_since_2018(replan_time_iso)
        
        self.replanned_patients[cid] = replanned_patients[cid]
        
        # convert datetime objects back to isoformat strings
        result = {cid: self.replanned_patients[cid]["new_admission_time"].isoformat()}
        
        if callback_url:
            headers = {'content-type': 'application/json', 'CPEE-CALLBACK': 'true'}
            response = requests.put(url=callback_url, json=result, headers=headers)
            if response.status_code == 200:
                print("Patient replanned successfully")
            else:
                print("Patient replan failed")
        else:
            return json.dumps(result)
        
    
if __name__ == '__main__':
    planner = Planner()
    bottle.run(host='::0', port=12791)
