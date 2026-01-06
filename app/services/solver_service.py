from pulp import *
import numpy as np
from typing import List, Dict
from app.schemas.travel import Flight, Hotel, CarRental, TravelRequest, SolverResult, ItineraryLeg
from app.services.geo_service import get_coords

def solve_itinerary(
    request: TravelRequest,
    flights: List[Flight],
    hotels: List[Hotel],
    cars: List[CarRental]
) -> SolverResult:

    all_cities = list(set(request.origin_cities + request.destination_cities + request.mandatory_cities))
    n = len(all_cities)
    city_map = {city: i for i, city in enumerate(all_cities)}

    M = 999999
    # Initialize matrices with M (infinity equivalent)
    # cost_matrix stores the Price Per Person of the best flight found
    cost_matrix = np.full((n, n), M)
    time_matrix = np.full((n, n), M)
    # track the "best" flight object for reconstruction
    flight_data = {}

    # We need total_pax to calculate the weighted score correctly
    total_pax = request.pax_adults + request.pax_children
    if total_pax < 1: total_pax = 1

    # Pre-processing: Select the best flight edge between any two cities
    # based on the User's weighted preferences (Cost vs Time).
    # Instead of just taking the cheapest, we take the one that minimizes the objective function score.

    # Init score matrix to track best score found so far
    score_matrix = np.full((n, n), float('inf'))

    for f in flights:
        if f.origin in city_map and f.destination in city_map:
            i, j = city_map[f.origin], city_map[f.destination]

            # Calculate score for this specific flight
            # Score = (Weight_Cost * Total_Price) + (Weight_Time * Duration)
            # Total_Price = Price_Per_Person * Pax
            current_score = (request.weight_cost * f.price * total_pax) + (request.weight_time * f.duration_minutes)

            if current_score < score_matrix[i, j]:
                score_matrix[i, j] = current_score
                cost_matrix[i, j] = f.price
                time_matrix[i, j] = f.duration_minutes
                flight_data[(i, j)] = f

    prob = LpProblem("Travel_Optimization", LpMinimize)

    x = LpVariable.dicts("x", [(i, j) for i in range(n) for j in range(n) if i != j], cat='Binary')
    u = LpVariable.dicts("u", range(n), lowBound=0, upBound=n, cat='Continuous')
    is_start = LpVariable.dicts("is_start", range(n), cat='Binary')
    is_end = LpVariable.dicts("is_end", range(n), cat='Binary')

    obj_terms = []

    for i in range(n):
        for j in range(n):
            if i == j: continue
            f_cost = cost_matrix[i, j]
            if f_cost == M: continue

            # Objective Function: Minimize weighted sum of Cost and Time
            term = x[i, j] * (request.weight_cost * f_cost * total_pax + request.weight_time * time_matrix[i, j])
            obj_terms.append(term)

    prob += lpSum(obj_terms)

    # Start/End constraints
    for i, city in enumerate(all_cities):
        if city not in request.origin_cities:
            prob += is_start[i] == 0
        if city not in request.destination_cities:
            prob += is_end[i] == 0

    prob += lpSum([is_start[i] for i in range(n)]) == 1
    prob += lpSum([is_end[i] for i in range(n)]) == 1

    # Flow Conservation
    for k in range(n):
        prob += lpSum([x[k, j] for j in range(n) if k != j]) - lpSum([x[i, k] for i in range(n) if i != k]) == is_start[k] - is_end[k]

    # Subtour Elimination (MTZ formulation)
    for i in range(n):
        for j in range(n):
            if i != j:
                prob += u[i] - u[j] + n * x[i, j] <= n - 1

    prob.solve(PULP_CBC_CMD(msg=0))

    status = LpStatus[prob.status]
    itinerary = []
    total_cost_val = 0.0
    total_duration_val = 0

    if status == 'Optimal':
        start_node = -1
        for i in range(n):
            if value(is_start[i]) == 1:
                start_node = i
                break

        if start_node != -1:
            current = start_node
            visited = {current}

            # Simple cycle detection to prevent infinite loops in reconstruction
            while True:
                next_hop = -1
                for j in range(n):
                    if current != j and value(x[current, j]) == 1:
                        next_hop = j
                        break

                if next_hop != -1:
                    f = flight_data.get((current, next_hop))
                    # f might be None if the solver picked an edge that we thought existed but didn't?
                    # Unlikely given the constraints, but safe to check.

                    price = cost_matrix[current, next_hop]
                    duration = time_matrix[current, next_hop]

                    # Fetch coords for frontend map
                    origin_name = all_cities[current]
                    dest_name = all_cities[next_hop]
                    origin_c = get_coords(origin_name)
                    dest_c = get_coords(dest_name)

                    origin_list = list(origin_c) if origin_c else None
                    dest_list = list(dest_c) if dest_c else None

                    itinerary.append(ItineraryLeg(
                        origin=origin_name,
                        destination=dest_name,
                        flight=f,
                        price=price,
                        duration=duration,
                        price_formatted=f"R$ {price:.2f}",
                        origin_coords=origin_list,
                        dest_coords=dest_list
                    ))

                    total_cost_val += price
                    total_duration_val += duration
                    current = next_hop

                    if current in visited:
                        break # loop detected
                    visited.add(current)

                    if value(is_end[current]) == 1:
                        break
                else:
                    break

    return SolverResult(
        status=status,
        itinerary=itinerary,
        total_cost=total_cost_val,
        total_duration=int(total_duration_val)
    )
