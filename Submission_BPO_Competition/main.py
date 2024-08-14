from simulator import Simulator, EventType
from planners import Planner
from problems import HealthcareProblem
from reporter import EventLogReporter
from sim2planner_interface import simulate_endpoint, convert_to_iso8601, get_available_resources, convert_to_hours_since_2018

class GAPlanner(Planner):
    def __init__(self, eventlog_file, data_columns):
        super().__init__()
        self.eventlog_reporter = EventLogReporter(eventlog_file, data_columns)
        self.replanned_patients = dict() # cid: sent_home_counter, first_admission_time, last_replan_time, new_admission_time
        self.current_state = dict() 
        
    def plan(self, plannable_elements, simulation_time):
        print("TIME: ", simulation_time)
        planned_elements = []
        simulation_time_iso = convert_to_iso8601(simulation_time)
        
        max_capacities = get_available_resources(self.planner_helper.available_resources())
        
        for case_id, element_labels in sorted(plannable_elements.items()):
            available_info = dict()
            available_info['cid'] = case_id
            available_info['time'] = simulation_time_iso
            available_info['info'] = simulator.planner.planner_helper.get_case_data(case_id)
            available_info['resources'] = list(map(lambda el: dict({'cid': el[0]}, **el[1]), self.current_state.items()))

            for resource in available_info['resources']:
                resource['start'] = convert_to_iso8601(resource['start'])
            
            # clean up replanned_patients dictionary
            for cid in list(self.replanned_patients.keys()):
                replan_time = convert_to_hours_since_2018(self.replanned_patients[cid]["new_admission_time"])
                if (replan_time <= simulation_time) and (cid not in plannable_elements.keys()):
                    del self.replanned_patients[cid]
            
            for cid in plannable_elements.keys():
                if cid in self.replanned_patients.keys(): # update the replanned_patients dictionary
                    available_info['info']['sent_home_counter'] = self.replanned_patients[cid]["sent_home_counter"] + 1
                    available_info['info']['first_admission_time'] = self.replanned_patients[cid]["first_admission_time"]
                    available_info['info']['last_replan_time'] = self.replanned_patients[cid]["new_admission_time"]
                    # patient gets replanned and will not be considered during replanning as potential collusion complication as other patients are in the replanned_patients dict
                    del self.replanned_patients[cid]
                else:
                    available_info['info']['sent_home_counter'] = 1
                    available_info['info']['first_admission_time'] = simulation_time_iso
                    available_info['info']['last_replan_time'] = simulation_time_iso
            
            # using an actual server endpoint would take too long, so we simulate the endpoint
            next_plannable_time, replanned_patients = simulate_endpoint(available_info, self.replanned_patients, max_capacities)
            
            # update self.replanned_patients
            self.replanned_patients[case_id] = replanned_patients[case_id]
            for element_label in element_labels:
                planned_elements.append((case_id, element_label, next_plannable_time))
        return planned_elements

        
    def report(self, case_id, element, timestamp, resource, lifecycle_state):
        if((lifecycle_state != EventType.CASE_ARRIVAL) and (lifecycle_state != EventType.COMPLETE_CASE)):
            if(lifecycle_state == EventType.ACTIVATE_TASK):
                self.current_state[case_id] = {'cid': case_id, 'task': element.label.value, 'start': timestamp, 'info': simulator.planner.planner_helper.get_case_data(case_id), 'wait': True}
            elif(lifecycle_state == EventType.START_TASK):
                self.current_state[case_id]['wait'] = False
                self.current_state[case_id]['info'] = simulator.planner.planner_helper.get_case_data(case_id)
            elif(lifecycle_state == EventType.COMPLETE_TASK):
                if(self.current_state[case_id]['task'] == element.label.value):
                    self.current_state.pop(case_id)
                else:
                    pass
            else:
                pass

        self.eventlog_reporter.callback(case_id, element, timestamp, resource, lifecycle_state)
        

planner = GAPlanner("./temp/event_log.csv", ["diagnosis", "sent_home_counter", "first_admission_time", "last_admission_time"])
problem = HealthcareProblem()
simulator = Simulator(planner, problem)
result = simulator.run(365*24)
print(result)