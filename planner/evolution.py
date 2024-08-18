import random
import json
from datetime import datetime, timedelta

PATIENT_CONFIG_PATH = "./patient_types.json"

def load_patient_types(path):
    with open(path, 'r') as file:
        return json.load(file)['patient_types']

def is_within_time_interval(subject_time, start_time, time_interval):
    """
    Check if genome[1]["new_admission_time"] is within the specified time interval of patient["new_admission_time"].

    Parameters:
    subject_time (datetime object): The time to check if it is within the time interval.
    start_time (datetime object): The start time of the time interval.
    time_interval (timedelta): The time interval to check within.

    Returns:
    bool: True if genome[1]["new_admission_time"] is within the specified time interval of patient["new_admission_time"], False otherwise.
    """
    # Calculate the end of the time interval
    interval_end_time = start_time + time_interval
    # Check if genome_admission_time is within the interval
    return start_time <= subject_time <= interval_end_time

def is_working_time(time):
    """
    Check if the given time is within working hours (8:00 - 17:00).

    Parameters:
    time (datetime object): The time to check if it is within working hours.

    Returns:
    bool: True if the given time is within working hours, False otherwise.
    """
    return (time.isoweekday() <= 5) and (8 <= time.hour < 17)

def get_working_time_spans(start_time, end_time):
    result = []
    current_time = start_time
    if current_time.hour < 8 and current_time.isoweekday() <= 5:
        current_time = datetime(current_time.year, current_time.month, current_time.day, 8, 0, 0)
    while current_time < end_time:
        if is_working_time(current_time):
            # add current time until end of working day to result list
            eod = datetime(current_time.year, current_time.month, current_time.day, 17, 0, 0)
            result.append((current_time, eod, eod-current_time))
        current_time = datetime(current_time.year, current_time.month, current_time.day, 8, 0, 0) + timedelta(days=1)
    return result

def get_random_time_between(start_time, end_time):
    """
    Returns a random datetime between two datetime objects.
    
    :param start_time: datetime: The start time
    :param end_time: datetime: The end time
    :return: datetime: A random datetime between start_time and end_time
    """
    time_difference = end_time - start_time
    total_seconds = int(time_difference.total_seconds())
    random_seconds = random.randint(0, total_seconds)
    random_time = start_time + timedelta(seconds=random_seconds)
    return random_time

def generate_evenly_distributed_times(first_admission_time, now, current_time, num_times=10):
    """
    Generates evenly distributed timestamps within a given interval.

    :param now (datetime): start of the time interval
    :param last_possible_time (datetime): end of the time interval
    :param current_time (datetime): current time
    :param num_times (int): number of timestamps to generate

    :return: list of datetime: list of evenly distributed timestamps
    """
    last_possible_time = first_admission_time + timedelta(hours=24 * 7)
    timedeltas = get_working_time_spans(now, last_possible_time)
    if not(current_time + timedelta(hours=24) > last_possible_time) and len(timedeltas) > 0:
        timestamps = []
        stamps_per_day = num_times // len(timedeltas)
        for delta in timedeltas:
            for i in range(stamps_per_day):
                new_replanning_time = get_random_time_between(delta[0], delta[1])
                timestamps.append(new_replanning_time)
    else: # case where the new_replanning_time is less than 24 hours prior to the last possible replan time -> patient will leave hospital
        timestamps = [now for i in range(num_times)]
    return timestamps

def generate_new_admission_time(now, last_possible_time):
    """
    Creates a new random admission time for a patient within a given time interval.

    :param now (Datetime): start of the time interval
    :param last_possible_time (datetime): end of the time interval

    :return: datetime: new random admission time
    """
    # delta = timedelta(random.randint(min_time, max_time))
    time_difference = last_possible_time - now
    total_minutes = int(time_difference.total_seconds() // 60)
    random_minutes = random.randint(0, total_minutes)
    random_datetime = now + timedelta(minutes=random_minutes)
    return random_datetime


class Resources:
    def __init__(self, max_capacities):
        self.capacities = max_capacities # {resource_name: number of max capacities}
        # OR, A_BED, B_BED, INTAKE, ER_PRACTITIONER
        self.occupations = {} # {resource_name: number of current occupations}
        self.queues = {} # {resource_name: number of patients waiting in queue}
        self.average_nursing_start_time = {"A_BED": None, "B_BED": None}
        for resource_name in max_capacities.keys():
            self.occupations[resource_name] = 0
            self.queues[resource_name] = 0
        # intake, ER_treatment, surgery, nursing_a, nursing_b
    
    def populate_resources(self, resources):
        """
        :param: resources (list) e.g. [{'cid': 1, 'task': 'intake', 'start': 0, 'info': {'diagnosis': 'A1'}, 'wait': False}]
        """
        resource_mapping = {
            "intake": "INTAKE",
            "ER_treatment": "ER_PRACTITIONER",
            "surgery": "OR",
            "nursing": "BED",
        }
        timestamps_a = []
        timestamps_b = []
        for resource in resources:
            resource_name = resource_mapping[resource['task']]
            # handle nursing types
            if resource_name == "BED":
                if resource['info']['diagnosis'][0] == "A":
                    resource_name = "A_BED"
                    timestamps_a.append(datetime.fromisoformat(resource['start']).timestamp)
                elif resource['info']['diagnosis'][0] == "B":
                    resource_name = "B_BED"
                    timestamps_b.append(datetime.fromisoformat(resource['start']).timestamp)
                else:
                    print("UNKOWN DIAGNOSIS")
                
            # handle wait boolean
            if isinstance(resource['wait'], str):
                resource_in_queue = resource['wait'].lower() == "true"
            else:
                resource_in_queue = resource['wait']
            # fill up queues and occupations
            if resource_in_queue:
                self.queues[resource_name] += 1
            else:
                self.occupations[resource_name] += 1
        
        for key in self.average_nursing_start_time.keys():
            if self.average_nursing_start_time[key] is not None:
                self.average_nursing_start_time[key] = sum(self.average_nursing_start_time[key]) / len(self.average_nursing_start_time[key])
                self.average_nursing_start_time[key] = datetime.fromtimestamp(self.average_nursing_start_time[key])

class Evolution():
    def __init__(self, patients_to_replan, replanned_patients, resources, max_capacities, current_time):
        # patients_to_replan and replanned patients are dictionaries with disjoint keys
        self.patients_to_replan = patients_to_replan # key: cid, value: {diagnosis, sent_home_counter, first_admission_time, new_admission_time}
        self.replanned_patients = replanned_patients # key: cid, value: {diagnosis, sent_home_counter, first_admission_time, new_admission_time}
        self.resources = Resources(max_capacities) # initialize resources
        self.resources.populate_resources(resources) # add current resource utilization to resources
        self.patient_types = load_patient_types(PATIENT_CONFIG_PATH)
        # evaluate arrival_rate func: arrival_rate_func = eval(f"lambda: {arrival_rate_func_str}") # see patient_generator.py
        self.current_time = current_time
        self.population = [] # (case_id, fitness_score, {diagnosis, sent_home_counter, first_admission_time, new_admission_time})
        
    def get_best_genome_with_cid(self, cid):
        for _, genome in enumerate(self.population):
            if genome[0] == cid:
                return genome
        
    def get_results(self):
        """Returns the final population as a dictionary with case_id as key and content as value.
        This format is compatible with the replanned_patients dictionary in the planner.py script.

        :return: dictionary: replanned patients in format {case_id: content}, whereat the content is in format {diagnosis, sent_home_counter, first_admission_time, new_admission_time}
        """
        result = {}
        for cid, _ in self.patients_to_replan.items():
            result[cid] = self.get_best_genome_with_cid(cid)[2]["new_admission_time"]
        return result
    
    def fitness_function(self, genome):
        """
        Function to calculate the fitness function score for a given genome.
        
        :param: genome (tuple list): (case_id, {diagnosis, sent_home_counter, first_admission_time, new_admission_time})
        
        :return: Double: fitness_value
        """
        pen_sent_home = 0
        average_intake_time = 1.125
        pen_er_treatment = 0
        pen_processed = 0
        
        er_treatment_duration_factor = 10
        sent_home_factor = 10
        processed_factor = 10
        
        # ----- er treatment waiting time -----        
        # Penality for patients that wait longer than 4 hours after ER treatment until they get processed with Nursing/Surgery
        # only patients A2, A3, A4, B3, B4 need surgery
        # er_diagnosis takes 2,5 hours on average
        # waiting time determined by:
        # queue length for surgery and nursing + average time left for nursing and surgery
        replan_delta = genome[2]["new_admission_time"] - genome[2]["last_replan_time"]
        if (replan_delta < timedelta(hours=36)):
            if self.resources.queues["ER_PRACTITIONER"] > 0:
                if genome[2]["diagnosis"] in ["A2", "A3"]:
                    pen_er_treatment += 2
                if genome[2]["diagnosis"] in ["A4", "B3", "B4"]:
                    pen_er_treatment += 2
                else:
                    pen_er_treatment += 1
            if self.resources.queues["OR"] > 0:
                if genome[2]["diagnosis"] in ["A2", "A3"]:
                    pen_er_treatment += 1
                if genome[2]["diagnosis"] in ["A4", "B3", "B4"]:
                    pen_er_treatment += 2
            if self.resources.queues[genome[2]["diagnosis"][0] + "_BED"] > 0: # A_BED or B_BED
                if genome[2]["diagnosis"] == "A1":
                    pen_er_treatment += 1
                if genome[2]["diagnosis"] in ["A2", "B1"]:
                    pen_er_treatment += 2
                if genome[2]["diagnosis"] in ["A3", "A4", "B2", "B3", "B4"]:
                    pen_er_treatment += 3
                # avg_nursing_start_time = self.resources.average_nursing_start_time[genome[2]["diagnosis"][0] + "_BED"]
                # if avg_nursing_start_time is not None:
                #     # if the average nursing start time is less than 5 hours from the current time, add a penalty
                #     # -> avg nursing time left is > 5 hours
                #     if (genome[2]["new_admission_time"] - avg_nursing_start_time) > timedelta(hours=5):
                #         pen_er_treatment += 1
        pen_er_treatment *= er_treatment_duration_factor
        
        # ----- patients sent home -----
        # intake takes norm(1, 0.125) hours
        # check if at new_admission_time there are already other patients rescheduled or up to 1 hour before
        for patient in self.replanned_patients.values():
            if is_within_time_interval(genome[2]["new_admission_time"], datetime.fromisoformat(patient["new_admission_time"]), timedelta(hours=average_intake_time)):
                # if self.resources.queues["INTAKE"] > 0 or self.resources.queues["OR"] > 0 or self.resources.queues["A_BED"] > 0 or self.resources.queues["B_BED"] > 0:
                #     pen_sent_home += 2
                # else:
                pen_sent_home += 1
        # check if the new_admission_time is within working hours
        if not is_working_time(genome[2]["new_admission_time"]):
            pen_sent_home += 2
        pen_sent_home *= sent_home_factor

        # ----- patients processed -----        
        # Penality for patients if their replan_time is not within the time interval 7 days after first_admission_time
        if not is_within_time_interval(genome[2]["new_admission_time"], genome[2]["first_admission_time"], timedelta(days=7)):
            pen_processed += 4
        # Penalty for each hour that the replan_time gets closer to the last_possible_time
        hours_until_deadline = ((genome[2]["first_admission_time"] + timedelta(days=7)) - genome[2]["new_admission_time"]).total_seconds() / 3600
        days_until_deadline = hours_until_deadline / 24 # TODO: add abs()?
        pen_processed += (1 / days_until_deadline) # the smaller the days_until_deadline, the higher the penalty
        # if hours_until_deadline < 36:
        #     pen_processed += 1
        
        pen_processed *= processed_factor
        
        fitness = (pen_er_treatment + pen_sent_home + pen_processed) / 3
        return fitness
    
    def mutate_genome(self, genome, mutation_probability=0.01, time_variation=4):
        """
        Mutates the genome with a given probability.
        
        :param genome: The genome to mutate (cid, fitness_score, content dictionary).
        :param mutation_probability: Probability of mutating any part of the genome.
        :param time_variation: The maximum variation in replanning_time during mutation.
        
        :return: A possibly mutated genome.
        """
        # case_id, element_label, replanning_time = genome
        cid, fitness, content = genome
        if random.random() < mutation_probability:
            # Mutate the replanning_time by adding or subtracting a random amount within time_variation
            time_adjustment_hours = random.randint(-time_variation, time_variation)
            time_adjustment = timedelta(hours=time_adjustment_hours)
            mutated_time = content["new_admission_time"] + time_adjustment
            if mutated_time < content["min_replan_time"]:
                mutated_time = content["min_replan_time"]
            content["new_admission_time"] = mutated_time
            return (cid, fitness, content)
        else:
            return genome
            
    
    def crossover_population(self, selected_population, unselected_population, crossover_probability=0.7):
        """
        Performs crossover on the selected population.
        
        :param selected_population: The population selected for reproduction.
        :param unselected_population: The remaining population.
        :param crossover_probability: The probability of performing crossover between two genomes.
        
        :return: A new population generated through crossover.
        """
        new_replanning_times = []
        new_population = selected_population # elitism
        for i in range(0, len(selected_population), 2):
            parent1 = selected_population[i]
            # Ensure there's a second parent for crossover; if not, just add the single parent to the new population
            if i + 1 < len(selected_population):
                parent2 = selected_population[i + 1]
                # Convert datetime to timestamp
                timestamp1 = parent1[2]["new_admission_time"].timestamp()
                timestamp2 = parent2[2]["new_admission_time"].timestamp()
                # Calculate the average timestamp
                average_timestamp = (timestamp1 + timestamp2) / 2
                # Convert the average timestamp back to datetime, including timezone information
                time_child = datetime.fromtimestamp(average_timestamp, tz=parent1[2]["new_admission_time"].tzinfo)
                new_replanning_times.append(time_child)
            else:
                new_replanning_times.append(parent1[2]["new_admission_time"])
        for genome in unselected_population:
            if new_replanning_times:
                new_time = new_replanning_times.pop(0)
                genome[2]["new_admission_time"] = max(genome[2]["min_replan_time"], new_time)
                updated_genome = (genome[0], genome[1], genome[2])
                new_population.append(updated_genome)
            else: # if number of genomes in unselected_population is greater than selected_population (odd number of genomes in population)
                new_population.append(genome)
        return new_population
        
        
    def perform_evolution_cycle(self):
        """
        Starts one evolution cycle

        :return: float: average fitness score of the population
        """
        # Evaluation: Calculate the fitness of each genome
        avg_score = 0
        for idx, genome in enumerate(self.population):
            genom_score = self.fitness_function(genome)
            self.population[idx] = (genome[0], genom_score, genome[2])
            avg_score += genom_score
        avg_score /= len(self.population)
        # Selection for Reproduction: Sort the population based on fitness and select the top 50%
        self.population = sorted(self.population, key=lambda x: x[1], reverse=False) # sort by fitness in ascending order
        if len(self.population) > 1:
            selected_population = self.population[:len(self.population) // 2]
            selected_population = sorted(selected_population, key=lambda x: x[2]["new_admission_time"]) # sort by replanning time
            unselected_population = self.population[len(self.population) // 2:]
            
            # Reproduction: Create new genomes by applying mutation and crossover to the selected genomes
            #    Crossover: Combine the genomes to create new genomes
            new_population = self.crossover_population(selected_population, unselected_population)
        #     Mutation: Mutate the genomes with a probability of 0.01
        else:
            new_population = self.population
        new_population = [self.mutate_genome(genome) for genome in new_population]
        # Replacement to form new population
        self.population = new_population
        return avg_score, 
    
    def initialize_population(self, pop_size=10):
        """
        creates the initial population of genomes with random replanning times

        :return: list: population of genomes in format (case_id, score, content dictionary)
        """
        for cid, content in self.patients_to_replan.items():
            new_admission_times = generate_evenly_distributed_times(first_admission_time=content["first_admission_time"], 
                                                                    now=content["new_admission_time"], 
                                                                    current_time=self.current_time,
                                                                    num_times=pop_size)
            for new_admission_time in new_admission_times:
                content_with_new_time = content.copy()
                content_with_new_time["new_admission_time"] = new_admission_time
                self.population.append((cid, 9999, content_with_new_time)) # worst score is 9999

def evolve(patients_to_replan, replanned_patients, resources, max_capacities, current_time):
    """
    Function to evolve the replanning times of patients. Also takes into account the patients
    that are already replanned as well as the current resource sitution.

    :param: patients_to_replan (dict): patients to be replanned in format {case_id: {diagnoisis, sent_home_counter, first_admission_time, new_admission_time}}
    :param: replanned_patients (dict): patients that are already replanned in format {case_id: {diagnosis, sent_home_counter, first_admission_time, new_admission_time}}
    :param: resources (list): list of resources in format [{"cid", "task", "start", "info", "wait"}]
    :param: current_time (datetime): point in time at which replanning is performed
    :param: iterations (int, optional): _description_. Defaults to 10.

    :return: dictionary: dictionray with case_id as key and content as value - compatible with replanned_patients in planner.py
    """
    population_size=10
    iterations = 10
    
    cids = list(patients_to_replan.keys())
    evolution = Evolution(patients_to_replan, replanned_patients, resources, max_capacities, current_time)
    evolution.initialize_population(pop_size=population_size)
    for i in range(iterations): # potentially add stopping criteria based on score
        score = evolution.perform_evolution_cycle()
        scores = [round(pop[1], 2) for pop in evolution.population]
        current_best_score = evolution.population[0][1]
        print(f"           Running iteration {i+1}, AVG Score: {score}, Best Score: {current_best_score} top 5 scores: {scores[0:5]}")

        
    replan_times = evolution.get_results()
    for cid in cids:
        patients_to_replan[cid]["new_admission_time"] = replan_times[cid].isoformat()
        patients_to_replan[cid]["last_replan_time"] = replan_times[cid].isoformat()
        patients_to_replan[cid]["first_admission_time"] = patients_to_replan[cid]["first_admission_time"].isoformat()
        replanned_patients[cid] = patients_to_replan[cid]
    return replanned_patients
    