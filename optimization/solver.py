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
    # Start with requested cities
    req_cities = set(request.origin_cities + request.destination_cities + request.mandatory_cities)
    
    # Add any city appearing in the provided flights/segments
    # This allows for intermediate hops (like expanding to nearest airport)
    for f in flights:
        req_cities.add(f.origin)
        req_cities.add(f.destination)
        
    all_cities = list(req_cities)
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
            
            # Hotel Cost at destination + Daily Cost
            # logic: If we fly i -> j, we stay in j for 'stay_days_per_city'
            # (Exception: if j is the final destination and we return immediately? 
            #  Assumption: User spends time in every destination visited)
            
            unit_hotel_cost = hotel_costs.get(all_cities[j], 0)
            unit_daily_cost = request.daily_cost_per_person
            days = request.stay_days_per_city
            
            # Total Stay Cost for this leg (Hotel for group + Daily for group)
            # Hotel is usually per room, but let's assume price_per_night is effectively covered
            # or simplified: HotelPrice * Days. 
            # Note: HotelPrice might be per person or per room. Model says "price_per_night". 
            # Let's assume one room fits all or costs are scaled. The prompt says "Optimize cost".
            # Safest is to treat Hotel Cost as total for the group or per person?
            # Let's add them up.
            
            stay_cost_total = (unit_hotel_cost * days) + (unit_daily_cost * days * total_pax)
            
            total_money = (f_cost * total_pax) + stay_cost_total
            total_minutes = time_matrix[i, j]
            
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
    # Constraints
    
    # 1. Start/End Constraints
    is_start = LpVariable.dicts("is_start", range(n), cat='Binary')
    is_end = LpVariable.dicts("is_end", range(n), cat='Binary')
    
    # Force start to be one of the origin_cities
    for i, city in enumerate(all_cities):
        if city not in request.origin_cities:
            prob += is_start[i] == 0

    # End Constraint logic
    if request.is_round_trip:
        # If Round Trip, End City MUST be the same as Start City?
        # Or at least one of the Origin Cities?
        # Let's enforce that End City must be in origin_cities.
        # AND we must ensure a cycle? Standard TSP uses sum(x_ij)=1 for all if cycle.
        # But we surely have intermediate nodes that are visited once.
        # Let's rely on Flow Conservation with Start/End being same set.
        
        for i, city in enumerate(all_cities):
             if city not in request.origin_cities:
                 prob += is_end[i] == 0
                 
        # Additional constraint: The specific City picked as Start must be the same as End?
        # Usually yes: SP -> Rio -> SP.
        # prob += is_start[i] == is_end[i] for all i
        for i in range(n):
            prob += is_start[i] == is_end[i]
            
    else:
        # One Way: End must be in destination_cities
        for i, city in enumerate(all_cities):
             if city not in request.destination_cities:
                 prob += is_end[i] == 0

    # Exactly one start and one end
    prob += lpSum([is_start[i] for i in range(n)]) == 1
    prob += lpSum([is_end[i] for i in range(n)]) == 1
        
    # Flow Constraints
    for k in range(n):
        # Round Trip: Start Node has Out=1, In=1 (if cycle) but our formulation treats Start/End separate?
        # If we use is_start/is_end logic:
        # Start Node: Out - In = 1
        # End Node: Out - In = -1
        # Interm: Out - In = 0
        # If Start == End (Round Trip), then Out - In = 0 for ALL nodes?
        # Implies a cycle. 
        # But we need to Break the Cycle logic for "Start" to "End".
        # Actually for Round Trip, we want path Start -> ... -> End, where Start and End refer to the same city physically compount,
        # but in graph theory to avoiding a simple 0-cost loop, we usually duplicate the node or just standard Flow conservation?
        
        # Let's keep logic: Out - In = Start - End
        # If Start==End, then Out=In for all. Which allows disjoint cycles.
        # We need MTZ to prevent disjoint sub-tours.
        
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
    
    # Cost Breakdown
    breakdown = {
        "flight": 0.0,
        "car": 0.0,
        "hotel": 0.0
    }
    
    if status == 'Optimal':
        # Find start node
        start_node = -1
        for i in range(n):
            if value(is_start[i]) == 1:
                start_node = i
                break
        
        current = start_node
        visited = {current}
        
        # Guard against infinite loops if solver allows cycles (Round Trip)
        # For Round Trip, we expect to visit Start again at the very end.
        
        steps = 0
        while steps < n + 5: # Safety limit
            # Find next hop
            next_hop = -1
            found_next = False
            for j in range(n):
                if current != j and value(x[current, j]) == 1:
                    next_hop = j
                    found_next = True
                    break
            
            if found_next:
                f = flight_data.get((current, next_hop))
                price = cost_matrix[current, next_hop] if f is None else f.price
                duration = time_matrix[current, next_hop] if f is None else f.duration_minutes
                
                leg_cost = price
                
                # Check Carrier Type for breakdown
                airline_lower = f.airline.lower() if f else ""
                if "carro" in airline_lower or "rent" in airline_lower:
                    breakdown["car"] += leg_cost
                else:
                    breakdown["flight"] += leg_cost
                
                # Add implicit hotel/stay cost to total (for reporting correct optimizer cost)
                # Note: The optimizer used these costs to decide, so we should reflect them?
                # Or just return movement costs? 
                # The user expects "Total Cost". Let's add stay costs to the leg-associated breakdown if possible
                # or just keep it separate. 
                # The 'itinerary' list usually shows movement. 
                # Let's NOT add it to 'price' of the flight leg to avoid confusion in UI.
                # But we must track it for the optimization score verification.
                
                # Re-calculate stay cost for this node to add to total_cost_val
                # We are going TO next_hop.
                unit_h = hotel_costs.get(all_cities[next_hop], 0)
                unit_d = request.daily_cost_per_person
                d_days = request.stay_days_per_city
                stay_total = (unit_h * d_days) + (unit_d * d_days * total_pax)
                
                breakdown["hotel"] += (unit_h * d_days) # Tracking pure hotel
                # daily cost is not in breakdown keys yet, but total_cost_val should include it
                
                # total_cost_val in this loop is accumulating the "Money" part of the objective?
                # Original code: total_cost_val += price. 
                # If we want the validation to match the "Custo Total" displayed, we should probably
                # let the UI calculate the static costs (Hotel * Days) as it does now, 
                # OR return the Solver's view of cost.
                # The UI adds them separately. 
                # IMPORTANT: If we add them here to total_cost_val, the UI might double count if it ALSO adds them.
                # Let's check app.py: 
                # app.py calculates: custo_total_viagem = custo_voos + custo_hospedagem...
                # So we should KEEP 'total_cost_val' here as just the flight prices for consistency with existing UI structure,
                # UNLESS we change UI to use solver's total.
                # Given instructions, I shouldn't break UI. 
                # I will leave total_cost_val as movement cost, but the DECISION (x[i,j]) was made using the full cost.
                # This is correct: The Logic considers it, but the Reporting can stay modular.
                
                # However, for 'breakdown' I will leave as is for compatibility.
                
                # Add implicit hotel cost if spending time? 
                # Currently we only track movement costs.
                
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
                
                steps += 1
                
                # Stopping Condition
                # If we reached the designated End node
                if value(is_end[current]) == 1:
                    # If Round Trip, we must ensure we haven't just started (steps > 0)
                    if request.is_round_trip:
                         break
                    else:
                         break
            else:
                break
                
    return {
        "status": status,
        "itinerary": itinerary,
        "total_cost": total_cost_val,
        "total_price": total_cost_val,
        "total_duration": total_duration_val,
        "cost_breakdown": breakdown
    }
