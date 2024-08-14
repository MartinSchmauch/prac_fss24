from abc import ABC, abstractmethod


class Planner(ABC):
    """
    The class that must be implemented to create a planner.
    The class must implement the plan method.
    The class must not use the simulator or the problem directly. Information from those classes is not available to it.
    The class can use the planner_helper to get information about the simulation, but only information through the planner_helper is available to it,
    other information can be constructed via the report method.
    Note that once an event is planned, it can still show up as possible event to (re)plan.
    To avoid infinite loops of planning the same event multiple times, the planner_helper.is_planned can be used to check if an event is already planned.
    """

    def __init__(self):
        self.planner_helper = None
    
    def set_planner_helper(self, planner_helper):
        self.planner_helper = planner_helper
    
    @abstractmethod
    def plan(self, plannable_elements, simulation_time):
        '''
        The method that must be implemented for planning.
        :param plannable_elements: A dictionary with case_id as key and a list of element_labels that can be planned or re-planned.
        :param simulation_time: The current simulation time.
        :return: A list of tuples of how the elements are planned. Each tuple must have the following format: (case_id, element_label, timestamp).
        '''
        
        pass


    def report(self, case_id, element, timestamp, resource, lifecycle_state):
        '''
        The method that can be implemented for reporting.
        It is called by the simulator upon each simulation event.
        '''
        pass