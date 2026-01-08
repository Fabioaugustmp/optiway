"""
Travel Itinerary Solver - Core optimization logic
Uses PuLP for TSP formulation with cost/time trade-off
"""

from pulp import *
import numpy as np
import logging
from typing import List, Dict, Optional, Tuple
from solver_service.models.schemas import (
    FlightSchema,
    HotelSchema,
    CarRentalSchema,
    TravelRequestSchema,
    ItineraryLegSchema,
    SolveResponseSchema
)

logger = logging.getLogger(__name__)


def solve_itinerary(
    request: TravelRequestSchema,
    flights: List[FlightSchema],
    hotels: List[HotelSchema],
    cars: List[CarRentalSchema]
) -> SolveResponseSchema:
    """
    Solve multi-city travel itinerary optimization problem.
    Uses TSP with MTZ constraints and weight-based cost/time trade-off.
    
    Args:
        request: Travel requirements and preferences
        flights: Available flight options
        hotels: Available hotel options
        cars: Available car rental options
    
    Returns:
        Optimized itinerary with status and cost breakdown
    """
    
    logger.info("Starting solver...")
    
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
        
        all_cities = list(req_cities)
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
        
        # 3. Create PuLP Model
        prob = LpProblem("Travel_Optimization", LpMinimize)
        
        # Decision variables
        x = LpVariable.dicts(
            "x",
            [(i, j) for i in range(n) for j in range(n) if i != j],
            cat='Binary'
        )
        u = LpVariable.dicts("u", range(n), lowBound=0, upBound=n, cat='Continuous')
        
        # Start and end nodes
        is_start = LpVariable.dicts("is_start", range(n), cat='Binary')
        is_end = LpVariable.dicts("is_end", range(n), cat='Binary')
        
        # 4. Objective Function
        total_pax = request.pax_adults + request.pax_children
        if total_pax < 1:
            total_pax = 1
        
        obj_terms = []
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                
                f_cost = cost_matrix[i, j]
                if f_cost >= M:
                    continue  # Skip invalid routes
                
                # Calculate total cost for this edge
                unit_hotel_cost = hotel_costs.get(all_cities[j], 0)
                unit_daily_cost = request.daily_cost_per_person
                days = request.stay_days_per_city
                
                stay_cost = (unit_hotel_cost * days) + (unit_daily_cost * days * total_pax)
                total_money = (f_cost * total_pax) + stay_cost
                total_minutes = time_matrix[i, j]
                
                term = x[i, j] * (
                    request.weight_cost * total_money +
                    request.weight_time * total_minutes
                )
                obj_terms.append(term)
        
        prob += lpSum(obj_terms), "Total_Cost"
        
        # 5. Constraints
        
        # Origin constraints
        for i, city in enumerate(all_cities):
            if city not in request.origin_cities:
                prob += is_start[i] == 0
        
        # Destination constraints
        if request.is_round_trip:
            for i, city in enumerate(all_cities):
                if city not in request.origin_cities:
                    prob += is_end[i] == 0
            
            # Start and end must be the same city for round trip
            for i in range(n):
                prob += is_start[i] == is_end[i]
        else:
            for i, city in enumerate(all_cities):
                if city not in request.destination_cities:
                    prob += is_end[i] == 0
        
        # Exactly one start and one end
        prob += lpSum([is_start[i] for i in range(n)]) == 1
        prob += lpSum([is_end[i] for i in range(n)]) == 1
        
        # Flow conservation
        for k in range(n):
            outflow = lpSum([x[k, j] for j in range(n) if k != j])
            inflow = lpSum([x[i, k] for i in range(n) if i != k])
            prob += outflow - inflow == is_start[k] - is_end[k]
        
        # Miller-Tucker-Zemlin subtour elimination
        for i in range(n):
            for j in range(n):
                if i != j:
                    prob += u[i] - u[j] + n * x[i, j] <= n - 1
        
        # 6. Solve
        prob.solve(PULP_CBC_CMD(msg=0))
        
        status = LpStatus[prob.status]
        
        # 7. Reconstruct Itinerary
        itinerary = []
        total_cost_val = 0.0
        total_duration_val = 0
        cost_breakdown = {"flight": 0.0, "hotel": 0.0, "car": 0.0}
        
        if status == 'Optimal':
            # Find start node
            start_node = -1
            for i in range(n):
                if value(is_start[i]) == 1:
                    start_node = i
                    break
            
            if start_node == -1:
                logger.warning("Could not find start node in optimal solution")
                return SolveResponseSchema(
                    status="Infeasible",
                    itinerary=[],
                    total_cost=0,
                    total_duration=0
                )
            
            current = start_node
            steps = 0
            max_steps = n + 5
            
            while steps < max_steps:
                # Find next hop
                next_hop = -1
                for j in range(n):
                    if current != j and value(x[current, j]) == 1:
                        next_hop = j
                        break
                
                if next_hop == -1:
                    break
                
                f = flight_data.get((current, next_hop))
                price = cost_matrix[current, next_hop] if f is None else f.price
                duration = time_matrix[current, next_hop] if f is None else f.duration_minutes
                
                # Create itinerary leg
                leg = ItineraryLegSchema(
                    origin=all_cities[current],
                    destination=all_cities[next_hop],
                    flight=f,
                    price=price,
                    duration=int(duration),
                    price_formatted=f"R$ {price:.2f}"
                )
                itinerary.append(leg)
                
                total_cost_val += price
                total_duration_val += int(duration)
                cost_breakdown["flight"] += price
                
                current = next_hop
                steps += 1
                
                # Stop if reached end node
                if value(is_end[current]) == 1:
                    break
        
        # Add hotel costs to breakdown
        for city in all_cities:
            cost_breakdown["hotel"] += hotel_costs.get(city, 0) * request.stay_days_per_city
        
        return SolveResponseSchema(
            status=status,
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
