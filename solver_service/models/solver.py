"""
Travel Itinerary Solver - Core optimization logic
Uses NSGA-II multi-objective optimization for cost/time trade-off
"""

import numpy as np
import logging
from typing import List, Dict, Optional, Tuple, Callable
from deap import base, creator, tools, algorithms
import random
from solver_service.models.schemas import (
    FlightSchema,
    HotelSchema,
    CarRentalSchema,
    TravelRequestSchema,
    ItineraryLegSchema,
    SolveResponseSchema
)

logger = logging.getLogger(__name__)

# NSGA-II Configuration
POPULATION_SIZE = 100
GENERATIONS = 50
CXPB = 0.8  # Crossover probability
MUTPB = 0.2  # Mutation probability
ELITE_SIZE = 5  # Number of Pareto-optimal solutions to keep


# NSGA-II Global Context (thread-safe storage)
class SolverContext:
    """Stores solver state for fitness evaluation"""
    def __init__(self):
        self.all_cities = []
        self.city_map = {}
        self.cost_matrix = None
        self.time_matrix = None
        self.flight_data = {}
        self.hotel_costs = {}
        self.request = None
        self.n = 0
    
    def reset(self):
        self.all_cities = []
        self.city_map = {}
        self.cost_matrix = None
        self.time_matrix = None
        self.flight_data = {}
        self.hotel_costs = {}
        self.request = None
        self.n = 0


_context = SolverContext()


def _is_valid_tour(individual: List[int]) -> bool:
    """
    Validate if a tour respects constraints:
    - Starts from an origin city
    - Visits all mandatory and destination cities
    - Ends at a destination city
    """
    if len(individual) < 2 or len(individual) != _context.n:
        return False
    
    start_city = _context.all_cities[individual[0]]
    end_city = _context.all_cities[individual[-1]]
    visited = set(individual)
    
    # Check start is origin
    if start_city not in _context.request.origin_cities:
        return False
    
    # Check end is destination (or same for round trip)
    if _context.request.is_round_trip:
        if end_city not in _context.request.origin_cities:
            return False
    else:
        if end_city not in _context.request.destination_cities:
            return False
    
    # Check all mandatory and destination cities are visited
    required_cities = set(_context.request.mandatory_cities + _context.request.destination_cities)
    required_indices = {_context.city_map[city] for city in required_cities if city in _context.city_map}
    
    return required_indices.issubset(visited)


def _evaluate_tour(individual: List[int]) -> Tuple[float, float]:
    """
    Evaluate fitness (multi-objective):
    - Objective 1: Total cost (flight + hotel)
    - Objective 2: Total duration (time)
    
    Returns: (total_cost, total_duration)
    """
    if not _is_valid_tour(individual):
        # Penalty for invalid tours
        return (1e10, 1e10)
    
    total_cost = 0.0
    total_duration = 0
    total_pax = _context.request.pax_adults + _context.request.pax_children
    if total_pax < 1:
        total_pax = 1
    
    try:
        # Calculate flight costs and duration
        for idx in range(len(individual) - 1):
            i = individual[idx]
            j = individual[idx + 1]
            
            flight_cost = _context.cost_matrix[i, j]
            flight_duration = _context.time_matrix[i, j]
            
            # Check if route is possible
            if flight_cost >= 999999:
                return (1e10, 1e10)
            
            total_cost += flight_cost * total_pax
            total_duration += int(flight_duration)
        
        # Add hotel costs for all visited cities (except last)
        for idx in range(len(individual) - 1):
            city_idx = individual[idx]
            city = _context.all_cities[city_idx]
            hotel_cost = _context.hotel_costs.get(city, 0.0)
            total_cost += hotel_cost * _context.request.stay_days_per_city
        
        # Return positive costs; DEAP uses weights to minimize
        return (total_cost, total_duration)
    
    except Exception as e:
        logger.error(f"Error evaluating tour: {str(e)}")
        return (1e10, 1e10)


def _create_individual() -> List[int]:
    """Create a random valid individual (permutation)"""
    max_attempts = 100
    for _ in range(max_attempts):
        # Start with a random permutation
        individual = list(range(_context.n))
        random.shuffle(individual)
        
        if _is_valid_tour(individual):
            return individual
    
    # Fallback: create a greedy tour
    return _create_greedy_individual()


def _create_greedy_individual() -> List[int]:
    """Create a greedy tour starting from first origin city"""
    # Find first origin city
    start_idx = None
    for i, city in enumerate(_context.all_cities):
        if city in _context.request.origin_cities:
            start_idx = i
            break
    
    if start_idx is None:
        start_idx = 0
    
    # Start with origin
    tour = [start_idx]
    unvisited = set(range(_context.n)) - {start_idx}
    
    # Greedily add nearest unvisited cities
    while unvisited:
        current = tour[-1]
        nearest = min(
            unvisited,
            key=lambda x: _context.cost_matrix[current, x] if _context.cost_matrix[current, x] < 999999 else float('inf')
        )
        
        if _context.cost_matrix[current, nearest] >= 999999:
            # If no valid connection, just add remaining cities in order
            tour.extend(sorted(unvisited))
            break
        
        tour.append(nearest)
        unvisited.remove(nearest)
    
    return tour


def _mutate_swap(individual: List[int], indpb: float = 0.2) -> Tuple[List[int]]:
    """Swap mutation - randomly swap two cities in the tour"""
    for i in range(len(individual)):
        if random.random() < indpb:
            j = random.randint(0, len(individual) - 1)
            individual[i], individual[j] = individual[j], individual[i]
    
    return (individual,)


def _mutate_insert(individual: List[int], indpb: float = 0.2) -> Tuple[List[int]]:
    """Insert mutation - remove a city and reinsert it elsewhere"""
    if random.random() < indpb and len(individual) > 2:
        i = random.randint(0, len(individual) - 1)
        j = random.randint(0, len(individual) - 1)
        individual.insert(j, individual.pop(i))
    
    return (individual,)


def _crossover_ox(parent1: List[int], parent2: List[int]) -> Tuple[List[int], List[int]]:
    """Order Crossover (OX) - TSP-specific crossover operator"""
    size = len(parent1)
    a, b = sorted([random.randint(0, size - 1), random.randint(0, size - 1)])
    
    # Extract segment from parent1
    child1 = [None] * size
    child1[a:b] = parent1[a:b]
    
    # Fill remaining from parent2
    ptr = b
    for city in parent2[b:] + parent2[:b]:
        if city not in child1:
            if ptr >= size:
                ptr = 0
            child1[ptr] = city
            ptr += 1
    
    # Repeat for child2
    child2 = [None] * size
    child2[a:b] = parent2[a:b]
    ptr = b
    for city in parent1[b:] + parent1[:b]:
        if city not in child2:
            if ptr >= size:
                ptr = 0
            child2[ptr] = city
            ptr += 1
    # Wrap back into Individual to preserve fitness attribute expected by DEAP
    return (creator.Individual(child1), creator.Individual(child2))


def solve_itinerary(
    request: TravelRequestSchema,
    flights: List[FlightSchema],
    hotels: List[HotelSchema],
    cars: List[CarRentalSchema]
) -> SolveResponseSchema:
    """
    Solve multi-city travel itinerary optimization problem using NSGA-II.
    Multi-objective optimization: minimizes cost AND duration simultaneously.
    Returns a single best solution based on Pareto frontier.
    
    Args:
        request: Travel requirements and preferences
        flights: Available flight options
        hotels: Available hotel options
        cars: Available car rental options
    
    Returns:
        Optimized itinerary with status and cost breakdown
    """
    
    logger.info("Starting NSGA-II solver...")
    
    try:
        # 1. Consolidate Cities
        req_cities = set(
            request.origin_cities + 
            request.destination_cities + 
            request.mandatory_cities
        )
        
        # Add cities from flight data
        for f in flights:
            req_cities.add(f.origin)
            req_cities.add(f.destination)
        
        all_cities = sorted(list(req_cities))
        n = len(all_cities)
        
        if n < 2:
            return SolveResponseSchema(
                status="Infeasible",
                itinerary=[],
                total_cost=0,
                total_duration=0,
                warning_message="Insufficient cities for itinerary"
            )
        
        city_map = {city: i for i, city in enumerate(all_cities)}
        
        # 2. Build Cost and Time Matrices
        M = 999999  # Large number for impossible routes
        cost_matrix = np.full((n, n), M, dtype=float)
        time_matrix = np.full((n, n), M, dtype=float)
        flight_data = {}  # (i, j) -> FlightSchema
        
        # Fill flight data
        for f in flights:
            if f.origin in city_map and f.destination in city_map:
                i, j = city_map[f.origin], city_map[f.destination]
                if f.price < cost_matrix[i, j]:
                    cost_matrix[i, j] = f.price
                    time_matrix[i, j] = f.duration_minutes
                    flight_data[(i, j)] = f
        
        # Build hotel costs map
        hotel_costs = {city: 0.0 for city in all_cities}
        for h in hotels:
            if h.city in hotel_costs:
                hotel_costs[h.city] = h.price_per_night
        
        # 3. Setup NSGA-II Global Context
        _context.reset()
        _context.all_cities = all_cities
        _context.city_map = city_map
        _context.cost_matrix = cost_matrix
        _context.time_matrix = time_matrix
        _context.flight_data = flight_data
        _context.hotel_costs = hotel_costs
        _context.request = request
        _context.n = n
        
        # 4. Setup DEAP Framework for Multi-Objective Optimization
        # Clear any existing definitions
        if hasattr(creator, "FitnessMin"):
            del creator.FitnessMin
        if hasattr(creator, "Individual"):
            del creator.Individual
        
        # Create fitness and individual classes
        creator.create("FitnessMin", base.Fitness, weights=(-1.0, -1.0))  # Minimize both objectives
        creator.create("Individual", list, fitness=creator.FitnessMin)
        
        toolbox = base.Toolbox()
        
        # Register genetic operators
        toolbox.register("individual", tools.initIterate, creator.Individual, _create_individual)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)
        toolbox.register("evaluate", _evaluate_tour)
        toolbox.register("mate", _crossover_ox)
        toolbox.register("mutate", _mutate_swap, indpb=0.3)
        # Selection operator required by eaSimple; NSGA-II non-dominated selection
        toolbox.register("select", tools.selNSGA2)
    
        # Note: Constraint validation is handled in _evaluate_tour through fitness penalties
        
        # 5. Create initial population
        pop = toolbox.population(n=POPULATION_SIZE)
        
        # Evaluate initial population
        fitnesses = list(map(toolbox.evaluate, pop))
        for ind, fit in zip(pop, fitnesses):
            ind.fitness.values = fit
        
        logger.info(f"Initial population: {len(pop)} individuals")
        
        # 6. Run NSGA-II Algorithm
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean, axis=0)
        stats.register("std", np.std, axis=0)
        stats.register("min", np.min, axis=0)
        stats.register("max", np.max, axis=0)
        
        logbook = tools.Logbook()
        logbook.header = ['gen', 'nevals'] + stats.fields
        
        pop, logbook = algorithms.eaSimple(
            pop, toolbox,
            cxpb=CXPB,
            mutpb=MUTPB,
            ngen=GENERATIONS,
            stats=stats,
            verbose=False
        )
        
        # 7. Extract Pareto Front
        from deap import tools as deap_tools
        pareto_front = deap_tools.sortNondominated(pop, len(pop), first_front_only=True)[0]
        
        logger.info(f"Pareto front size: {len(pareto_front)}")
        
        if not pareto_front:
            return SolveResponseSchema(
                status="Infeasible",
                itinerary=[],
                total_cost=0,
                total_duration=0,
                warning_message="No feasible solution found"
            )
        
        # 8. Select best solution from Pareto front
        # Strategy: choose solution with best cost if weight_cost > weight_time
        # Otherwise, choose solution with best time
        if request.weight_cost > request.weight_time:
            best_individual = min(pareto_front, key=lambda x: abs(x.fitness.values[0]))
        else:
            best_individual = min(pareto_front, key=lambda x: abs(x.fitness.values[1]))
        
        # 9. Reconstruct Itinerary from Best Individual
        itinerary = []
        total_cost_val = 0.0
        total_duration_val = 0
        cost_breakdown = {"flight": 0.0, "hotel": 0.0, "car": 0.0}
        
        total_pax = request.pax_adults + request.pax_children
        if total_pax < 1:
            total_pax = 1
        
        # Build itinerary from tour
        for idx in range(len(best_individual) - 1):
            i = best_individual[idx]
            j = best_individual[idx + 1]
            
            flight = flight_data.get((i, j))
            price = cost_matrix[i, j]
            duration = int(time_matrix[i, j])
            
            if price < M:
                leg = ItineraryLegSchema(
                    origin=all_cities[i],
                    destination=all_cities[j],
                    flight=flight,
                    price=price,
                    duration=duration,
                    price_formatted=f"R$ {price:.2f}"
                )
                itinerary.append(leg)
                
                total_cost_val += price * total_pax
                total_duration_val += duration
                cost_breakdown["flight"] += price * total_pax
        
        # Add hotel costs
        for idx in range(len(best_individual) - 1):
            city_idx = best_individual[idx]
            city = all_cities[city_idx]
            hotel_cost = hotel_costs.get(city, 0.0)
            cost_breakdown["hotel"] += hotel_cost * request.stay_days_per_city
            total_cost_val += hotel_cost * request.stay_days_per_city
        
        logger.info(f"Best solution - Cost: R$ {total_cost_val:.2f}, Duration: {total_duration_val} min")
        
        return SolveResponseSchema(
            status="Optimal",
            itinerary=itinerary,
            total_cost=total_cost_val,
            total_duration=total_duration_val,
            cost_breakdown=cost_breakdown
        )
        
    except Exception as e:
        logger.error(f"Solver error: {str(e)}", exc_info=True)
        return SolveResponseSchema(
            status="Error",
            itinerary=[],
            total_cost=0,
            total_duration=0,
            warning_message=f"Solver error: {str(e)}"
        )
