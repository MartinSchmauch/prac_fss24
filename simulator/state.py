import queue
import requests
import time
import sys
sys.path.append('../')
from db.db_util import get_db, initialize_resources, DATABASE_RESOURCES
from event import Event, EventType
from helpers import load_patient_types, create_cpee_instance, get_next_available_resource, generate_response_text, get_task_duration, get_queue_length, pop_queue
from logging_util import log_event
from patient_generator import Patient_Generator

class State:
    def __init__(self, running_time=10, test=False, patient_types_path='../patient_types.json', resources_config='../db/resources/resource_config.json'):
        self.RESOURCES_CONFIG = resources_config
        self.CALLBACK_HEADER = {
                'content-type': 'application/json',
                'CPEE-CALLBACK': 'true'
                }
        self.running_time = running_time
        self.time = 0.0
        self.callbacks_awaiting = 0 # number of callbacks that are still expected
        self.patients_in_system = 0
        self.patient_states = {}
        self.events = queue.PriorityQueue()
        self.init_resources()
        self.test = test
        if test:
            patient_generator = Patient_Generator(runtime=running_time)
            patient_list = patient_generator.generate_patients()
            self.patient_types_config = load_patient_types(patient_types_path)
            self.populate_initial_events(patient_list)
        
    def get_system_state(self):
        states_list = []
        for patient_id, patient_state in self.patient_states.items():
            states_list.append({"cid": patient_id, "task": patient_state["task"], "start": patient_state["start"], "info": patient_state["info"], "wait": patient_state["wait"]})
        return states_list
    
    def get_patient_types_config(self):
        return self.patient_types_config
    
    def init_resources(self):
        initialize_resources(config_file=self.RESOURCES_CONFIG, db_file=DATABASE_RESOURCES)
            
    def populate_initial_events(self, patient_list): # test method
        for p in patient_list: # create number of patients into queue
            arrival_time, patient_type = p
            log_event(virtual_time=arrival_time, 
                      patient_type=patient_type, 
                      event_type=EventType.CREATION,
                      status="success",
                      message="Initial Creation event representing 1 patient put into the queue")
            self.events.put((arrival_time, Event(event_type=EventType.CREATION, event_start=arrival_time, patient_id=None, patient_type=patient_type)))
    
    def run(self):
        # while self.time <= self.running_time:
        if self.test:
            while (self.events.qsize() > 0) or (self.patients_in_system > 0): # event in queue or cpee instances still running but currently no event in queue (e.g. between end of nursing and release patient)
                # wait until self.callbacks_awaiting == 0 and only then continue with next line:
                while self.callbacks_awaiting > 0:
                    time.sleep(0.0001)
                (self.time, event) = self.events.get() # wait for all patients that arrive at the exact same time, only continue when the next admission is greater than the next event
                # check that  all the patients that arrive are matching with the expected patients
                self.handle_event(event)
            print("\n-------------------\nSIMULATION FINISHED\n-------------------\n")
        else:
            while True:
                while self.callbacks_awaiting > 0:
                    time.sleep(0.001)
                (self.time, event) = self.events.get()
                self.handle_event(event)
        return
        
    def handle_event(self, event):
        print("\nsystem state: ", self.get_system_state())
        if event.event_type == EventType.CREATION: # triggered by replan endpoint or initial creation
            self.callbacks_awaiting += 1
            try:
                process_id = create_cpee_instance(patient_type=event.patient_type, arrival_time=event.event_start, patient_id=event.patient_id)
                log_event(virtual_time=event.event_start, 
                        patient_id=event.patient_id, 
                        patient_type=event.patient_type, 
                        event_type=event.event_type, 
                        status="success", 
                        message="Cpee instance created"
                        )
            finally: 
                self.callbacks_awaiting -= 1

        elif event.event_type == EventType.ADMISSION:
            self.patients_in_system += 1
            log_event(virtual_time=event.event_start,
                      patient_id=event.patient_id,
                      patient_type=event.patient_type,
                      event_type=event.event_type,
                      status="success",
                      message="patient admitted to hospital (resources feasable)"
                      )
            
        elif event.event_type == EventType.ENTER_QUEUE:
            self.patient_states[event.patient_id] = {"task": event.event_resource, "start": event.event_start, "info": {"diagnosis": event.patient_type}, "wait": True}
        
        elif event.event_type == EventType.REQUEST_RESOURCE: # coming from queue - resource now available -> take resource
            patient_type = event.patient_type
            resource_type = event.event_resource
            request_time = event.event_start
            available_at, resource_name = get_next_available_resource(resource_type, request_time)
            self.patient_states[event.patient_id] = {"task": resource_type, "start": event.event_start, "info": {"diagnosis": event.patient_type}, "wait": False}
            task_duration = get_task_duration(patient_types_config=self.get_patient_types_config(), patient_type=patient_type, resource_type=resource_type)
            end_time = request_time + task_duration
            response_json = generate_response_text(finish_time=end_time, patient_type=patient_type, resource_type=resource_type)
            conn_r = get_db(DATABASE_RESOURCES)
            cursor = conn_r.cursor() 
            cursor.execute(f"UPDATE Resources SET available_at = ? WHERE resource_name = ?", (end_time, resource_name,))
            conn_r.commit()
            conn_r.close()
            log_event(virtual_time=request_time, 
                      patient_id=event.patient_id, 
                      patient_type=event.patient_type, 
                      event_type=event.event_type, 
                      status="success", 
                      message=f"Resource type {resource_type} requested and resource {resource_name} assigneds"
                      )
            self.events.put((end_time, Event(event_type=EventType.RELEASE_RESOURCE, 
                                                    event_start=request_time, 
                                                    event_end=end_time,
                                                    event_resource=event.event_resource,
                                                    event_callback_url=event.event_callback_url, 
                                                    event_callback_content=response_json,
                                                    patient_id=event.patient_id,)))
            
        elif event.event_type == EventType.RELEASE_RESOURCE: # resource consumed -> send final callback to cpee
            del self.patient_states[event.patient_id]
            log_event(virtual_time=event.event_end, 
                      patient_id=event.patient_id, 
                      patient_type=event.patient_type, 
                      event_type=event.event_type, 
                      status="success", 
                      message=f"1 resource of type {event.event_resource} released"
                      )
            if get_queue_length(event.event_resource) > 0: # resource gets available -> take next patient from queue
                id, priority, request_time, callback_url, patient_id, patient_type, resource_type = pop_queue(event.event_resource) # returns (priority, request_time, callback_url, patient_id, patient_type, resource_type)
                new_request_time = event.event_end
                self.events.put((new_request_time, Event(event_type=EventType.REQUEST_RESOURCE, 
                                                  event_start=new_request_time, 
                                                  event_resource=resource_type, 
                                                  event_callback_url=callback_url,
                                                  patient_id=patient_id, 
                                                  patient_type=patient_type)))
            reponse = requests.put(event.event_callback_url, headers=self.CALLBACK_HEADER, json=event.event_callback_content)
            
        elif event.event_type == EventType.RELEASE_PATIENT:
            log_event(virtual_time=event.event_start, 
                      patient_id=event.patient_id,
                      patient_type=event.patient_type,
                      event_type=event.event_type, 
                      status="success", 
                      message="Patient realeased from hospital"
                      )
            self.patients_in_system -= 1
        
        elif event.event_type == EventType.REPLAN_PATIENT:
            log_event(virtual_time=event.event_start,
                      patient_id=event.patient_id,
                      patient_type=event.patient_type,
                      event_type=event.event_type,
                      status="failure",
                      message=f"patient got replanned to time: {event.event_end}"
                      )
            self.patients_in_system -= 1
            self.events.put((event.event_end, Event(event_type=EventType.CREATION, 
                                                            event_start=event.event_end,
                                                            event_end = event.event_end,
                                                            patient_id=event.patient_id, 
                                                            patient_type=event.patient_type)))
    