import random
import json
from planners import Planner
from plannerhelper import PlannerHelper
from helpers import load_patient_types

RESOURCE_CONFIG_PATH = "resource_config.json"
PATIENT_CONFIG_PATH = "patient_types.json"

class Resources:
    def __init__(self):
        self.capacities = {} # {resource_type: max capacity}
        self.occupations = {} # {resource_type: current occupation}
        self.queues = {} # {resource_type: number of patients waiting in queue}
        with open(RESOURCE_CONFIG_PATH, "r") as file:
            resource_config = json.load(file)
        for resource in resource_config["resources"]:
            resource_name = resource["resource_type"]
            self.capacities[resource_name] = resource["capacity"]
            self.occupations[resource_name] = 0
            if resource_name != "intake":
                self.queues[resource_name] = 0
    
    def populate_resources(self, resources):
        for resource in resources: # iterate over all resources and get current capacities
            if resource['wait']:
                self.queues[resource['task']] += 1
            else:
                self.occupations[resource['task']] += 1
        return self
    

class Evolution():
    def __init__(self, replanned_patients, resources, time):
        self.unfinished_cases = 0 # number of items in resources
        self.finished_cases = 0 # number of finished cases overall
        self.cases_started = 0 # only possible with a given trace in the json
        self.er_surgery_nursing_started = {}
        self.er_treatment_finished = {}
        self.replanned_patients = replanned_patients # key: cid, value: {diagnosis, sent_home_counter, first_admission_time, last_possible_admission_time, new_admission_time}
        self.resources = Resources() # initialize resources
        self.resources.populate_resources(resources) # add current resource utilization to resources
        self.patient_types = load_patient_types(PATIENT_CONFIG_PATH)
        # evaluate arrival_rate func: arrival_rate_func = eval(f"lambda: {arrival_rate_func_str}") # see patient_generator.py
        self.time = time
        self.population = [] # (case_id, {diagnosis, sent_home_counter, first_admission_time, last_possible_admission_time, new_admission_time})
        self.result = None
        
    def get_results(self):
        return self.result
    
    def fitness_function(self, genome):
        """
        Function to calculate the fitness function score for a given genome.
        
        Parameters:
            genome (tuple list): (case_id, {diagnosis, sent_home_counter, first_admission_time, last_possible_admission_time, new_admission_time})
        
        Returns:
            Double: fitness_value
        """
                
        er_treatment_duration_factor = 20
        sent_home_factor = 500
        processed_factor = 5000
        
        # patient types: type, diagnosis, arrival_rate, treatment_durations
        
        # Penality for patients that wait longer than 4 hours after ER treatment until they get processed with Nursing/Surgery
        er_treatment_2_processing = [
            (self.er_surgery_nursing_started[case_id] if case_id in self.er_surgery_nursing_started else self.time)
               - er_treatment_finished
               for case_id, er_treatment_finished in self.er_treatment_finished.items()]
        er_treatment_2_processing_excessive = [0 if t < 4 else (t-4)**2 for t in er_treatment_2_processing]

        pen_er_treatment = sum(er_treatment_2_processing_excessive) / self.cases_started * er_treatment_duration_factor

        # patients sent home
        time_for_intake = dict(filter(lambda k : k[0].label == HealthcareElements.TIME_FOR_INTAKE,
                                self.simulator.event_times.items()))
        time_for_intake_cases = [t[0].case_id for t in time_for_intake.items()]
        intake_count = collections.Counter(time_for_intake_cases)
        sent_home_count = sum(filter(lambda k : k > 1, intake_count.values()))
        pen_sent_home = sent_home_count / self.cases_started * sent_home_factor

        # patients processed
        released = len(list(filter(lambda k : k[0].label == HealthcareElements.RELEASING,
                                self.simulator.event_times.items())))
        pen_processed = (self.cases_started - released) * processed_factor / self.cases_started

        
        # Weighted sum of scores, with accuracy being twice as important
        fitness = (pen_er_treatment + pen_sent_home + pen_processed) / 3
        return fitness
    
    
    def format_resource(self, resources):
        formatted_resources = [f"Resource: {str(resource)}" for resource in resources]
        return formatted_resources
    
    
    def generate_random_time(self, simulation_time, min_time=24, max_time=168):
        return simulation_time + random.randint(min_time, max_time)
    
    
    def mutate_genome(self, genome, simulation_time, mutation_probability=0.01, time_variation=12):
        """
        Mutates the genome with a given probability.
        
        :param genome: The genome to mutate (case_id, element_label, replanning_time).
        :param simulation_time: Current simulation time to ensure mutation makes sense in context.
        :param mutation_probability: Probability of mutating any part of the genome.
        :param time_variation: The maximum variation in replanning_time during mutation.
        :return: A possibly mutated genome.
        """
        case_id, element_label, replanning_time = genome
        if random.random() < mutation_probability:
            # Mutate the replanning_time by adding or subtracting a random amount within time_variation
            time_adjustment = random.randint(-time_variation, time_variation)
            mutated_replanning_time = max(simulation_time, replanning_time + time_adjustment)
            return (case_id, element_label, mutated_replanning_time)
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
        new_population = selected_population
        for i in range(0, len(selected_population), 2):
            parent1 = selected_population[i]
            # Ensure there's a second parent for crossover; if not, just add the single parent to the new population
            if i + 1 < len(selected_population):
                parent2 = selected_population[i + 1]
                time_child = (parent1[2] + parent2[2]) / 2
                new_replanning_times.append(time_child)
            else:
                new_replanning_times.append(parent1[2])
        for genome in unselected_population:
            if new_replanning_times:
                new_time = new_replanning_times.pop(0)
                updated_genome = (genome[0], genome[1], new_time)
                new_population.append(updated_genome)
            else: # if number of genomes in unselected_population is greater than selected_population (odd number of genomes in population)
                new_population.append(genome)
        return new_population
        
        
    def perform_evolution_cycle(self):
        # planned_activities = [] # [(case_id, element_label, replanning_time), ...]
        for case_id, content in self.replanned_patients.items(): # 19, ['time_for_intake']
            self.population.append((case_id, content))
            # for key, value in content.items(): # 'time_for_intake'
                # available_resources = self.format_resource(self.planner_helper.available_resources()) # AVAILABLE RESOURCES:  ['OR1', 'A_BED1', ..., B_BED1']                
                # print("\n-----AVAILABLE RES. -----\n", len(available_resources))
                # patient_type = self.planner_helper.get_case_type(case_id) # A/B/ER
                # patient_diagnosis = self.planner_helper.get_case_data(case_id)["diagnosis"] # {'diagnosis': 'A2'}
                # randomly add replanning times between 24 hours and 168 hours in the future of the simulation time
                # population.append((case_id, element_label, self.generate_random_time(simulation_time)))
                
        # Evaluation: Calculate the fitness of each genome
        genome_fitness = {} # key: cid, value: fitness score
        avg_score = 0
        for genome in self.population:
            genom_score = self.fitness_function(genome)
            genome_fitness[genome[0]] = genom_score
            avg_score += genom_score
        avg_score /= len(self.population)
        
        # Selection for Reproduction: Sort the population based on fitness and select the top 50%
        self.population = sorted(self.population, key=lambda x: genome_fitness[x[0]], reverse=True) # sort by fitness
        if len(self.population) > 1:
            selected_population = self.population[:len(self.population) // 2]
            selected_population = sorted(selected_population, key=lambda x: x[2]) # sort by replanning time
            unselected_population = self.population[len(self.population) // 2:]
            
            # Reproduction: Create new genomes by applying mutation and crossover to the selected genomes
            #    Crossover: Combine the genomes to create new genomes
            new_population = self.crossover_population(selected_population, unselected_population)
        #     Mutation: Mutate the genomes with a probability of 0.01
        else:
            new_population = self.population
        new_population = [self.mutate_genome(genome, self.time) for genome in new_population]
        
        # Replacement to form new population
        self.population = new_population        
        return avg_score
    

# class to test using the given simulator
class MyPlanner(Planner):
    def __init__(self, problem, simulator):
        super().__init__()
        self.unfinished_cases = 0
        self.cases_started = 0
        self.er_surgery_nursing_started = {}
        self.er_treatment_finished = {}
        self.replanned_patients = {}
        # self.planner_helper = PlannerHelper(problem, simulator)
    
    def plan(self, plannable_elements, simulation_time):
        evolution = Evolution(self.replanned_patients, self.planner_helper.available_resources(), simulation_time)
        evolve(plannable_elements, self.planner_helper.available_resources(), simulation_time)

planner = MyPlanner(problem, simulator)
planner.set_planner_helper(PlannerHelper(problem, simulator))
planner.plan(plannable_elements, simulation_time)


def evolve(replanned_patients, resources, time, iterations = 10):
    evolution = Evolution(replanned_patients, resources, time)
    for i in range(iterations): # potentially add stopping criteria based on score
        score = evolution.perform_evolution_cycle()
        print(f"Running iteration {i}")
        print("Score: ", score)
    return evolution.get_results()
        