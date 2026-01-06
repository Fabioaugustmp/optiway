from pulp import *
import numpy as np
import pandas as pd
from typing import List, Tuple, Dict
from data.models import Flight, Hotel, CarRental, TravelRequest

def solve_itinerary(
    request: TravelRequest,
    flights: List[Flight],
    hotels: List[Hotel],
    cars: List[CarRental]
) -> Dict:
    
    # 1. Consolidate Cities
    # All cities involved: Origins, Destinations, Mandatory
    all_cities = list(set(request.origin_cities + request.destination_cities + request.mandatory_cities))
    n = len(all_cities)
    city_map = {city: i for i, city in enumerate(all_cities)}
    
    # 2. Pre-process Costs and Times Matrices
    # Initialize with high values
    M = 999999
    cost_matrix = np.full((n, n), M)
    time_matrix = np.full((n, n), M)
    flight_data = {} # (i, j) -> Flight Object

    # Fill Flight Data
    for f in flights:
        if f.origin in city_map and f.destination in city_map:
            i, j = city_map[f.origin], city_map[f.destination]
            # Use the cheapest/fastest aggregation logic or just the first one found for now
            # Here we take the one provided (assuming pre-filtered or min)
            if f.price < cost_matrix[i, j]:
                cost_matrix[i, j] = f.price
                time_matrix[i, j] = f.duration_minutes
                flight_data[(i, j)] = f

    # Fill Hotel and Car Costs (Optional addition to node cost, simplifies to edge for now or separate var)
    # For TSP, we usually associate costs with edges. 
    # Let's approximate: Stay cost = Avg Hotel Price * 2 nights (simple assumption for the model)
    hotel_costs = {city: 0 for city in all_cities}
    for h in hotels:
        if h.city in hotel_costs:
            hotel_costs[h.city] = h.price_per_night

    # 3. PuLP Model
    prob = LpProblem("Travel_Optimization", LpMinimize)

    # Variables
    # x[i, j] = 1 if flight from i to j
    x = LpVariable.dicts("x", [(i, j) for i in range(n) for j in range(n) if i != j], cat='Binary')
    # u[i] = sequence number for MTZ
    u = LpVariable.dicts("u", range(n), lowBound=0, upBound=n, cat='Continuous')

    # Objective Function
    # Cost Component: Flight Price * Pax + Hotel (approx)
    # Time Component: Flight Duration
    
    obj_terms = []
    
    total_pax = request.pax_adults + request.pax_children
    
    for i in range(n):
        for j in range(n):
            if i == j: continue
            
            # Weighted Cost
            # Flight Cost
            f_cost = cost_matrix[i, j]
            if f_cost == M: continue # Skip invalid edges
            
            # Hotel Cost at destination (Simplified: 1 night per city visit)
            h_cost = hotel_costs.get(all_cities[j], 0) * total_pax
            
            total_money = (f_cost * total_pax) + h_cost
            total_minutes = time_matrix[i, j]
            
            # Normalize for objective: 
            # We assume user cares about R$ 1 roughly as much as 1 minute? No, scaling needed.
            # Simple scaling: Cost + (Time * ValueOfTime). Let's use weights directly.
            # To avoid scale issues, let's just multiply weights.
            # User slider returns 0..1 per category.
            
            term = x[i, j] * (request.weight_cost * total_money + request.weight_time * total_minutes)
            obj_terms.append(term)
            
    prob += lpSum(obj_terms)

    # Constraints
    
    # 1. Flow Conservation for Mandatory Cities ("Intermediate")
    # For every city k in Mandatory, Enter = 1, Leave = 1
    # Actually, standard TSP says Enter=1, Leave=1 for ALL cities if it's a cycle.
    # But this is Open Path or Open-Jaw.
    
    # Origins and Destinations are sets.
    # We create a dummy Start Node S and End Node E if strictly solving path.
    # OR simpler: 
    # Sum(x_out) - Sum(x_in) = 1  (if Origin)
    # Sum(x_out) - Sum(x_in) = -1 (if Destination)
    # Sum(x_out) - Sum(x_in) = 0  (if Intermediate)
    
    # Given we allow CHOOSING an origin from a list, and a destination from a list.
    
    # Create binary variables for being Start and End
    is_start = LpVariable.dicts("is_start", range(n), cat='Binary')
    is_end = LpVariable.dicts("is_end", range(n), cat='Binary')
    
    # Only allowed cities can be start/end
    for i, city in enumerate(all_cities):
        if city not in request.origin_cities:
            prob += is_start[i] == 0
        if city not in request.destination_cities:
            prob += is_end[i] == 0
            
    # Exactly one start and one end
    prob += lpSum([is_start[i] for i in range(n)]) == 1
    prob += lpSum([is_end[i] for i in range(n)]) == 1
    
    if not request.allow_open_jaw:
        # Start city must be same as End city? 
        # Usually Open Jaw means Start != End allowed.
        # Closed Jaw means Start == End.
        # So if Allow Open Jaw = False, then is_start[i] == is_end[i]. 
        # But wait, physically you "arrive" at start at the end?
        # TSP Cycle means Return. Path means One Way.
        # Assuming "Travel" implies round trip or returning home?
        # Let's assume standard TSP Cycle for "Closed", and Path for "Open-Jaw".
        pass
        
    # Flow Constraints
    for k in range(n):
        # Outflow - Inflow
        prob += lpSum([x[k, j] for j in range(n) if k != j]) - lpSum([x[i, k] for i in range(n) if i != k]) == is_start[k] - is_end[k]

    # Connectivity / MTZ
    # u_i - u_j + N*x_ij <= N-1
    for i in range(n):
        for j in range(n):
            if i != j:
                prob += u[i] - u[j] + n * x[i, j] <= n - 1

    # Solve
    prob.solve(PULP_CBC_CMD(msg=0))
    
    # Reconstruct
    status = LpStatus[prob.status]
    itinerary = []
    total_cost_val = 0.0
    total_duration_val = 0
    
    if status == 'Optimal':
        # Find start node
        start_node = -1
        for i in range(n):
            if value(is_start[i]) == 1:
                start_node = i
                break
        
        current = start_node
        visited = {current}
        
        while True:
            # Find next hop
            next_hop = -1
            for j in range(n):
                if current != j and value(x[current, j]) == 1:
                    next_hop = j
                    break
            
            if next_hop != -1:
                f = flight_data.get((current, next_hop))
                # Fallback if specific flight obj missing (shouldn't happen if cost valid)
                price = cost_matrix[current, next_hop] if f is None else f.price
                duration = time_matrix[current, next_hop] if f is None else f.duration_minutes
                
                itinerary.append({
                    "from": all_cities[current],
                    "to": all_cities[next_hop],
                    "flight": f,
                    "price": price,
                    "duration": duration,
                    "price_formatted": f"R$ {price:.2f}"
                })
                total_cost_val += price
                total_duration_val += duration
                current = next_hop
                visited.add(current)
                
                # If we hit the end node designated by solver
                if value(is_end[current]) == 1:
                    break
            else:
                break
                
    return {
        "status": status,
        "itinerary": itinerary,
        "total_cost": total_cost_val,
        "total_price": total_cost_val, # Alias for compatibility
        "total_duration": total_duration_val
    }
