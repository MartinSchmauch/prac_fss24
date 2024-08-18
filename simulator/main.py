import bottle
import sys
import os
import threading
import datetime
from state import State
from route_handler import admit_patient, request_resource, release_patient, replan_patient, send_system_state
from logging_util import setup_logging



def get_unique_log_file_name():
    # Generate a unique log file name based on the current timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join("logs", f"process_log_{timestamp}.log")

@bottle.route('/admit-patient', method='POST')
def handle_admit_patient():
    return admit_patient(state)

@bottle.route('/request-resource', method='POST')
def handle_request_resource(): # for resources intake, er_treatment, surgery, nursing
    return request_resource(state)

@bottle.route('/release-patient', method='POST') 
def handle_release_patient():
    return release_patient(state)

@bottle.route('/replan-patient', method='POST')
def handle_replan_patient():
    return replan_patient(state)

@bottle.route('/get-system-state', method='GET')
def handle_get_system_state():
    return send_system_state(state)

if __name__ == '__main__':
    setup_logging(get_unique_log_file_name())
    if len(sys.argv) == 3:
        runtime = float(sys.argv[1])
        test_run = sys.argv[2]
    else: 
        runtime = 10.0
        test_run = False
    state = State(running_time=runtime, test=test_run) # start simulator with parameters from the discord photo
    simulation_thread = threading.Thread(target=state.run)
    simulation_thread.start()
    bottle.run(host='::0', port=12790)
