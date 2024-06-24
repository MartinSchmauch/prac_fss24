from state import EventType, Event
from db.db_util import DATABASE_PATIENTS, DATABASE_RESOURCES, get_db
from helpers import get_task_duration, get_db, generate_response_text, get_queue_length
import bottle
from logging_util import log_event
import json


def admit_patient(state):
    req = bottle.request
    patient_type = req.forms.patient_type
    patient_id = req.forms.patient_id
    admission_time = float(req.forms.intake_time)
    html_status = 201
    conn_p = get_db(DATABASE_PATIENTS)
    cursor = conn_p.cursor()
    
    if (patient_id == None) or (patient_id == ""): # patient_id is not given
        cursor.execute(
            "INSERT INTO Patient (patient_type, diagnosis, admission_time) VALUES (?, ?, ?)",
            (patient_type, patient_type , admission_time)
        )
    else: # patient_id is given
        patient_id = int(patient_id)
        cursor.execute("SELECT * FROM Patient WHERE id = ?", (patient_id,))
        row = cursor.fetchone()
        if row != None: # valid patient_id that already exists in patient db
            assert patient_id == row['id']
            html_status = 200
        else: # invalid patient_id
            cursor.execute(
                "INSERT INTO Patient (patient_type, diagnosis, admission_time) VALUES (?, ?, ?)",
                (patient_type, patient_type , admission_time)
            )
    patient_id = cursor.lastrowid
    conn_p.commit()
    conn_p.close()
    
    available = "True"
    if patient_type.startswith("A") or patient_type.startswith("B"): # check treatment feasability
        conn_r = get_db(DATABASE_RESOURCES)
        cursor = conn_r.cursor()
        # check that intake resource is available
        cursor.execute("SELECT resource_name FROM resources WHERE resource_type='intake' AND available_at <= ? LIMIT 1", (admission_time,))
        row = cursor.fetchone()
        if row is None: # intake resource not available -> replan
            available = "False"
        # check that surgery or nursing resource queue are no longer than 2
        nursing_type = "nursing_a" if patient_type.startswith("A") else "nursing_b"
        surgery_queue_length = get_queue_length("surgery")
        nursing_queue_length = get_queue_length(nursing_type)
        if surgery_queue_length > 2 or nursing_queue_length > 2: # queue longer than 2 -> replan
            available = "False"
        conn_r.close()
    state.events.put((admission_time, Event(event_type=EventType.ADMISSION, 
                                            event_start=admission_time, 
                                            event_end=admission_time,
                                            patient_id=patient_id,
                                            patient_type=patient_type)))
    return bottle.HTTPResponse(
            json.dumps({"patient_id": patient_id,
                        "available": available,
                        } ),
            status=html_status,
            headers = { 'content-type': 'application/json'}
            )
    
    
def request_resource(state): # for resources intake, er_treatment, surgery, nursing
    req = bottle.request
    patient_type = req.forms.patient_type
    patient_id = req.forms.patient_id
    resource_type = req.forms.resource_type
    request_time = float(req.forms.request_time)
    callback_url = req.headers['CPEE-CALLBACK']

    conn_r = get_db(DATABASE_RESOURCES)
    cursor = conn_r.cursor()
    if resource_type == "nursing":
        if patient_type.startswith("A"):
            resource_type += "_a" 
        elif patient_type.startswith("B") or patient_type.startswith("ER_B"): 
            resource_type += "_b"
        else:
            raise Exception("Invalid patient type")
        
    task_duration = get_task_duration(patient_types_config=state.get_patient_types_config(), patient_type=patient_type, resource_type=resource_type)
    end_time = request_time + task_duration
    
    cursor.execute(f"SELECT resource_name FROM Resources WHERE resource_type = ? and available_at <= ? LIMIT 1", (resource_type, request_time,))
    row = cursor.fetchone()
    if row is None: # go into queue TODO: handle queue
        print("Go into queue for resource type and patient: ", resource_type, patient_type)
        priority = 0 if patient_type.startswith("ER") else 1
        cursor.execute(
            "INSERT INTO Queue (priority, request_time, callback_url, patient_id, patient_type, resource_name) VALUES (?, ?, ?, ?, ?, ?)", # TODO: add cppe id for callback?
            (priority, request_time, callback_url, patient_id, patient_type, resource_type)
        )
        conn_r.commit()
        conn_r.close()
        # TODO: is this still needed?
        state.events.put((request_time, Event(event_type=EventType.ENTER_QUEUE, 
                                              event_start=request_time, 
                                              event_resource=resource_type, 
                                              event_callback_url=callback_url, 
                                              patient_id=patient_id, 
                                              patient_type=patient_type)))
    else: # take resource
        resource_name = row['resource_name']
        cursor.execute(f"UPDATE Resources SET available_at = ? WHERE resource_name = ?", (end_time, resource_name,))
        conn_r.commit()
        conn_r.close()
        response_json = generate_response_text(end_time, patient_type, resource_type)
        log_event(virtual_time=request_time, 
                      patient_id=patient_id, 
                      patient_type=patient_type, 
                      event_type=EventType.REQUEST_RESOURCE,
                      status="success", 
                      message=f"Resource type {resource_type} requested and resource {resource_name} assigned"
                      )
        state.events.put((end_time, Event(event_type=EventType.RELEASE_RESOURCE, 
                                          event_start=request_time,
                                          event_end=end_time, 
                                          event_resource=resource_type,
                                          patient_id=patient_id,
                                          patient_type=patient_type, 
                                          event_callback_url=callback_url, 
                                          event_callback_content=response_json,
            )))
    return bottle.HTTPResponse(
        json.dumps({'Ack.:': 'Response later'}),
        status=202,
        headers={'content-type': 'application/json', 'CPEE-CALLBACK': 'true'}
        ) # either way this is a async request -> response upon release of resource 
    
def release_patient(state):
    req = bottle.request
    patient_id = req.forms.patient_id
    patient_type = req.forms.patient_type
    now = float(req.forms.release_time) + 0.00001
    conn_r = get_db(DATABASE_RESOURCES)
    cursor = conn_r.cursor()
    cursor.execute("DELETE FROM Queue WHERE patient_id = ?", (patient_id,))
    conn_r.commit()
    conn_r.close()
    
    # TODO: write report to log:
    state.events.put((now, Event(event_type=EventType.RELEASE_PATIENT, 
                                   event_start=now, 
                                   event_end=now,
                                   patient_type= patient_type,
                                   patient_id=patient_id)))
    return bottle.HTTPResponse(
            json.dumps({"patient_id": patient_id}),
            status=200,
            headers = { 'content-type': 'application/json'}
            )
    

def replan_patient(state):
    req = bottle.request
    patient_id = req.forms.patient_id
    patient_type = req.forms.patient_type
    intake_time = float(req.forms.arrival_time)
    replanned_intake = intake_time + 24.0
    
    import queue
    temp_queue = queue.PriorityQueue()

    # List to store the elements
    elements = []
    # Transfer elements to the temporary queue and save them to the list
    while not state.events.empty():
        item = state.events.get()
        elements.append(item)
        temp_queue.put(item)
    # Transfer elements back to the original queue
    state.events = temp_queue
    # Now, `elements` list contains all the elements from the queue
    for item in elements:
        if type(item[0]) == tuple:
            print(item[0], " : ", item[1])
    replan_time = intake_time + 0.00001
    state.events.put((replan_time, Event(event_type=EventType.REPLAN_PATIENT,
                                        event_start=replan_time,
                                        event_end=replanned_intake,
                                        patient_id=patient_id,
                                        patient_type=patient_type)))
    return bottle.HTTPResponse(
            json.dumps({"patient_id": patient_id}),
            status=200,
            headers = { 'content-type': 'application/json'}
            )
    