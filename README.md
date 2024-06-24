# prac_fss24

## Execution
The simulator has two modes it can be started in:
- the "Test Mode" where patients are generated within the simulator based on the arrival rates given in the specifications - based on these patients cpee instances are created upon arrival time
- the "Normal Mode" where the simulator expects that patients are generated externally and cpee instances are created externally as well

To start the simulator go to repository root and enter:
```
python3 main.py runtime TestMode
```
where the runtime is the duration in which patients should arrive in the hospital. This parameter is only important if the TestMode is set to True. If the simulator ought to be run in normal mode you can leave runtime and TestMode blank (python3 main.py).


## Simulation results
The results of the simulation are logged and saved in a .log file in the ~/logs directory. A log entry consists of multiple properties that form an event in the simulator.

Log entry: Time_of_event - patient_id - patient_type - event_type - status - message

If a patient is new in a hospital, there is not yet a patient_id, so the id is "None" for the ADMISSION event.
If a patient can not be treated, this is seen as "failure" and the patient has to be replanned, thus this event is having the status "Failure".

