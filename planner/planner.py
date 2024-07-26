
import bottle
from datetime import datetime, timedelta
from evolution import Evolution

@bottle.route('/replan_patient', method='POST') 
def replan_patient():
    req = bottle.request
    cid = req.forms.cid # Case ID
    time = datetime.fromisoformat(req.forms.time) # Current Time (ISO 8601, XML Schema DataTime format)
    info = req.forms.info # json hash - can contain arbitrary keys e.g. "diagnosis"
    resources = req.forms.resources # json hash - fixed structure ("cid", "task", "start", "info", "wait")
    return planner.plan_patient(cid, time, info, resources)



class Planner:
    def __init__(self):
        self.super = super()
        self.replanned_patients = {}
        
    
    def plan_patient(self, cid, time, info, resources):
        """
        Function to plan the patient
        
        Parameters:
            cid (Integer): Case ID
            time (String): current time in ISO 8601, XML Schema DataTime format
            info (dictionary): json hash - can contain arbitrary keys e.g. "diagnosis"
            resources (dictionary): json hash - fixed structure ("cid", "task", "start", "info", "wait")
        
        Returns:
            String: replan_time_iso: ISO 8601, XML Schema DataTime format
        """
        
        
        if cid not in self.replanned_patients.keys(): # update the replanned_patients dictionary
            self.replanned_patients[cid] = {
                "diagnosis": info["diagnosis"],
                "sent_home_counter": 1,
                "first_admission_time": time,
                "new_admission_time": (time + timedelta(hours=24)).isoformat(),
                }
        else:
            self.replanned_patients[cid]["sent_home_counter"] += 1
            self.replanned_patients[cid]["new_admission_time"] = (time + timedelta(hours=24)).isoformat()
        
        # Evolutionary Algorithm
        self.replanned_patients = Evolution.evolve(self.replanned_patients, resources, time)
        
        return self.replanned_patients[cid]["new_admission_time"]
        
    
if __name__ == '__main__':
    planner = Planner()
    bottle.run(host='::0', port=12791)