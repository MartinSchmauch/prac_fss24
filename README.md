# prac_fss24

The simulator has two modes it can be started in:
- the "Test Mode" where patients are generated within the simulator based on the arrival rates given in the specifications - based on these patients cpee instances are created upon arrival time
- the "Normal Mode" where the simulator expects that patients are generated externally and cpee instances are created externally as well

To start the simulator go to repository root and enter:
```
python3 main.py runtime TestMode
```
where the runtime is the duration in which patients should arrive in the hospital. This parameter is only important if the TestMode is set to True. If the simulator ought to be run in normal mode you can leave runtime and TestMode blank (python3 main.py).
