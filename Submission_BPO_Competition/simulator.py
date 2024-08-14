from enum import Enum, auto
from plannerhelper import PlannerHelper


class EventType(Enum):
	CASE_ARRIVAL = auto()
	ACTIVATE_TASK = auto()
	ACTIVATE_EVENT = auto()
	START_TASK = auto()
	COMPLETE_TASK = auto()
	COMPLETE_EVENT = auto()
	PLAN_EVENTS = auto()
	COMPLETE_CASE = auto()
	SCHEDULE_RESOURCES = auto()
	ASSIGN_RESOURCES = auto()
	REGULAR_PLANNING_MOMENT = auto()


class SimulationEvent:
	def __init__(self, event_type, moment, element, resource=None):
		self.event_type = event_type
		self.moment = moment
		self.element = element
		self.resource = resource

	def __lt__(self, other):
		return self.moment < other.moment

	def __str__(self):
		return str(self.event_type) + "\t(" + str(round(self.moment, 2)) + ")\t" + str(self.element) + "," + str(self.resource)


class Simulator:
	def __init__(self, planner, problem):
		self.events = []  # list of tuples (planned moment, simulationevent)
		self.unassigned_tasks = dict()  # dictionary of unassigned tasks id -> task
		self.assigned_tasks = dict()  # dictionary of assigned tasks id -> (task, resource, moment of assignment)
		self.available_resources = set()  # set of available resources
		self.away_resources = []  # list of resources that are unavailable, because they are away
		self.busy_resources = dict()  # dictionary of busy resources resource -> (task they are busy on, moment they started on the task)
		self.busy_cases = dict()  # dictionary of busy cases case_id -> list of ids of elements that are planned in self.events for the case
		self.now = 0  # current moment in the simulation
		self.finalized_cases = 0  # number of cases that have been finalized
		self.total_cycle_time = 0  # sum of cycle times of finalized cases
		self.case_start_times = dict()  # dictionary of case_id -> moment the case started
		self.task_start_end_times = dict()
		self.event_times = dict()
		self.problem = problem  # the problem to be simulated
		self.planner = planner  # the planner to be used for planning events

		planner.set_planner_helper(PlannerHelper(problem, self))
		problem.set_simulator(self)
		self.init_simulation()

	def restart(self):
		self.events = []
		self.unassigned_tasks = dict()
		self.assigned_tasks = dict()
		self.available_resources = set()
		self.away_resources = []
		self.busy_resources = dict()
		self.busy_cases = dict()
		self.now = 0
		self.finalized_cases = 0
		self.total_cycle_time = 0
		self.case_start_times = dict()
		self.task_start_end_times = dict()
		self.event_times = dict()

		self.problem.restart()
		self.init_simulation()

	def sort_events(self):
		"""
		First start tasks (i.e. use resources) before another COMPLETE_EVENT comes into action
		"""
		self.events.sort(key = lambda k : (k[0], # time
									 1 if k[1].event_type == EventType.COMPLETE_EVENT else
									 0)
		)

	def init_simulation(self):
		"""
		Initializes the simulation by:
		- setting the available resources to all resources in the problem
		- adding the first case arrival event to the events list
		- setting the first regular planning moment
		- restarting the problem
		"""
		for r in self.problem.resources:
			self.available_resources.add(r)
		self.problem.restart()
		(t, task) = self.problem.next_case()
		self.events.append((t, SimulationEvent(EventType.CASE_ARRIVAL, t, task)))
		next_planning_moment = self.problem.next_regular_planning_moment(0)
		self.events.append((next_planning_moment, SimulationEvent(EventType.REGULAR_PLANNING_MOMENT, next_planning_moment, None)))
		self.events.append((0, SimulationEvent(EventType.SCHEDULE_RESOURCES, 0, None)))
		self.sort_events()

	def cancel(self, case_id, event_label):
		"""
		Cancels an event for a case with a certain label by removing it from the events list.
		"""
		found_index = None
		for i in range(len(self.events)):
			if self.events[i][1].element is not None and self.events[i][1].element.case_id == case_id and self.events[i][1].element.label == event_label:
				found_index = i
		if found_index is not None:
			event = self.events.pop(found_index)
			# also remove the element from the busy case
			self.busy_cases[case_id] = list(filter(
				lambda k : k.id != event[1].element.id,
				self.busy_cases[case_id]
			))

	def is_planning_slot(self, time):
		"""
		Returns whether the given time is the time of a planning slot.
		There are planning slots every half hour between 8:00 and 15:00 (inclusive) on weekdays.
		"""
		time_in_week = time % (24 * 7)
		hour_of_day_x_10 = round((time_in_week % 24)*10)  # we multiply by 10 to avoid floating point errors
		#day_of_week = round(time_in_week // 24)  # 0 is Monday, 1 is Tuesday, ..., 6 is Sunday
		day_of_week = True
		return hour_of_day_x_10 >= 80 and hour_of_day_x_10 <= 150 and day_of_week < 5 and hour_of_day_x_10 % 5 == 0

	def activate(self, element):
		"""
		Activates an element.
		For an event that means scheduling the completion of the event for the moment at which it happens.
		For a task that means scheduling the assignment of resources immediately.
		"""
		self.busy_cases[element.case_id].append(element)
		if element.is_event():
			self.planner.report(element.case_id, element, self.now, None, EventType.ACTIVATE_EVENT)
			self.events.append((element.occurrence_time, SimulationEvent(EventType.COMPLETE_EVENT, element.occurrence_time, element)))
		elif element.is_task():
			self.planner.report(element.case_id, element, self.now, None, EventType.ACTIVATE_TASK)
			self.unassigned_tasks[element.id] = element
			self.events.append((self.now, SimulationEvent(EventType.ASSIGN_RESOURCES, self.now, None)))
		self.events.append((self.now, SimulationEvent(EventType.PLAN_EVENTS, self.now, None)))

	def run(self, running_time=24*365):
		"""
		Runs the simulation for the specified amount of time.
		"""
		while self.now <= running_time:
			(self.now, event) = self.events.pop(0)

			if event.event_type == EventType.CASE_ARRIVAL:				
				self.planner.report(event.element.case_id, None, self.now, None, EventType.CASE_ARRIVAL)  # report CASE_ARRIVAL
				# create the case
				self.case_start_times[event.element.case_id] = self.now
				self.busy_cases[event.element.case_id] = []
				# activate the first element
				self.activate(event.element)
				# schedule the next case arrival
				(t, task) = self.problem.next_case()
				self.events.append((t, SimulationEvent(EventType.CASE_ARRIVAL, t, task)))

			elif event.event_type == EventType.START_TASK:
				self.task_start_end_times[event.element] = [self.now, 0]
				self.planner.report(event.element.case_id, event.element, self.now, event.resource, EventType.START_TASK) # report START_TASK
				self.problem.start_task(event.element)
				# start the task
				self.busy_resources[event.resource] = (event.element, self.now)
				# schedule the completion of the task
				t = self.now + self.problem.processing_time_sample(event.resource, event.element, self.now)
				self.events.append((t, SimulationEvent(EventType.COMPLETE_TASK, t, event.element, event.resource)))				

			elif event.event_type == EventType.COMPLETE_EVENT \
			  		or event.event_type == EventType.COMPLETE_TASK:
				self.planner.report(event.element.case_id, event.element, self.now, event.resource, event.event_type) # report COMPLETE_EVENT or COMPLETE_TASK
				# for tasks, process the resource that performed the task
				if event.event_type == EventType.COMPLETE_TASK:
					self.task_start_end_times[event.element][1] = self.now
					del self.busy_resources[event.resource]
					if self.problem.resources_available(event.resource, self.now):
						self.available_resources.add(event.resource)
						self.events.append((self.now, SimulationEvent(EventType.ASSIGN_RESOURCES, self.now, None)))  # if a resource becomes available, it can be assigned, so we schedule the assignment of resources
					else:
						self.away_resources.append(event.resource)
					del self.assigned_tasks[event.element.id]
				else:
					self.event_times[event.element] = self.now

				# complete the element
				self.busy_cases[event.element.case_id] = list(filter(
					lambda k : k.id != event.element.id,
					self.busy_cases[event.element.case_id]
				))
				next_elements = self.problem.complete_element(event.element)
				# activate the next elements
				for next_element in next_elements:  
					self.activate(next_element)
				# if the case is done, complete the case
				if len(self.busy_cases[event.element.case_id]) == 0:					
					self.events.append((self.now, SimulationEvent(EventType.COMPLETE_CASE, self.now, event.element)))

			elif event.event_type == EventType.SCHEDULE_RESOURCES:
				# check if resources become available again and make them available if that is the case
				resources_to_add = []
				for resource in self.away_resources:
					if self.problem.resources_available(resource, self.now):
						resources_to_add.append(resource)
				for resource in resources_to_add:
					self.away_resources.remove(resource)
					self.available_resources.add(resource)
				if len(resources_to_add) > 0:
					self.events.append((self.now, SimulationEvent(EventType.ASSIGN_RESOURCES, self.now, None)))  # if a resource becomes available, it can be assigned, so we schedule the assignment of resources
				# check if resources leave and send them away if that is the case
				resources_to_remove = []
				for resource in self.available_resources:
					if not self.problem.resources_available(resource, self.now):
						resources_to_remove.append(resource)
				for resource in resources_to_remove:
					self.available_resources.remove(resource)
					self.away_resources.append(resource)
				# schedule the next resource check
				self.events.append((self.now + 1, SimulationEvent(EventType.SCHEDULE_RESOURCES, self.now + 1, None)))

			elif event.event_type == EventType.ASSIGN_RESOURCES:
				# assign resources to tasks
				if len(self.unassigned_tasks) > 0 and len(self.available_resources) > 0:
					assignments = self.problem.assign_resources(self.unassigned_tasks, self.available_resources)
					for (task, resource) in assignments:
						self.events.append((self.now, SimulationEvent(EventType.START_TASK, self.now, task, resource)))
						del self.unassigned_tasks[task.id]
						self.assigned_tasks[task.id] = (task, resource, self.now)
						self.available_resources.remove(resource)

			elif event.event_type == EventType.REGULAR_PLANNING_MOMENT:
				# schedule event planning for now
				self.events.append((self.now, SimulationEvent(EventType.PLAN_EVENTS, self.now, None)))
				# schedule the next regular planning moment
				next_planning_moment = self.problem.next_regular_planning_moment(self.now)
				self.events.append((next_planning_moment, SimulationEvent(EventType.REGULAR_PLANNING_MOMENT, next_planning_moment, None)))

			elif event.event_type == EventType.PLAN_EVENTS:			
				# plan events
				# is done each time an element is activated and there are events to plan
				if len(self.problem.can_plan)>0:
					planned_events = self.planner.plan(self.problem.can_plan, self.now)
					for planned_element in planned_events:
						created_events = self.problem.plan(planned_element[0], planned_element[1], planned_element[2])
						for created_event in created_events:
							if not created_event.is_event():
								raise ValueError("At this stage, we only allow for planning of events.")
							self.activate(created_event)

			elif event.event_type == EventType.COMPLETE_CASE:
				self.planner.report(event.element.case_id, None, self.now, None, EventType.COMPLETE_CASE)  # report COMPLETE_CASE
				self.total_cycle_time += self.now - self.case_start_times[event.element.case_id]
				self.finalized_cases += 1
				del self.busy_cases[event.element.case_id]
			self.sort_events()

		score = self.problem.evaluate()
		return score