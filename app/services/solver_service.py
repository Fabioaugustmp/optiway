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

    print("Starting Solver...")
    try:
        all_cities = list(set(request.origin_cities + request.destination_cities + request.mandatory_cities))
        n = len(all_cities)
        city_map = {city: i for i, city in enumerate(all_cities)}

        M = 999999
        cost_matrix = np.full((n, n), M)
        time_matrix = np.full((n, n), M)
        flight_data = {}
        
        # Map Hotel Costs (Min price per city for optimization)
        hotel_cost_map = {}
        for h in hotels:
            if h.city not in hotel_cost_map:
                hotel_cost_map[h.city] = h.price_per_night
            else:
                if h.price_per_night < hotel_cost_map[h.city]:
                    hotel_cost_map[h.city] = h.price_per_night

        total_pax = request.pax_adults + request.pax_children
        if total_pax < 1: total_pax = 1

        score_matrix = np.full((n, n), float('inf'))

        for f in flights:
            if f.origin in city_map and f.destination in city_map:
                i, j = city_map[f.origin], city_map[f.destination]
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
                if f_cost == M:
                    prob += x[i, j] == 0
                    continue

                h_cost = hotel_cost_map.get(all_cities[j], 0)
                d_cost = request.daily_cost_per_person
                days = request.stay_days_per_city
                
                stay_cost_total = (h_cost * days) + (d_cost * days * total_pax)
                
                total_money = (f_cost * total_pax) + stay_cost_total
                total_time = time_matrix[i, j]
                
                term = x[i, j] * (request.weight_cost * total_money + request.weight_time * total_time)
                obj_terms.append(term)

        prob += lpSum(obj_terms)

        for i, city in enumerate(all_cities):
            if city not in request.origin_cities:
                prob += is_start[i] == 0

        if request.is_round_trip:
            for i, city in enumerate(all_cities):
                 if city not in request.origin_cities:
                     prob += is_end[i] == 0
            for i in range(n):
                prob += is_start[i] == is_end[i]
        else:
            for i, city in enumerate(all_cities):
                 if city not in request.destination_cities:
                     prob += is_end[i] == 0

        prob += lpSum([is_start[i] for i in range(n)]) == 1
        prob += lpSum([is_end[i] for i in range(n)]) == 1
        
        for k in range(n):
            incoming = lpSum([x[i, k] for i in range(n) if i != k])
            if request.is_round_trip:
                 prob += incoming == 1
            else:
                 prob += incoming == 1 - is_start[k]

        for k in range(n):
            prob += lpSum([x[k, j] for j in range(n) if k != j]) - lpSum([x[i, k] for i in range(n) if i != k]) == is_start[k] - is_end[k]

        for i in range(n):
            for j in range(n):
                if i != j:
                    prob += u[i] - u[j] + n * x[i, j] <= n - 1 + (n + 2) * is_start[j]

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

                while True:
                    next_hop = -1
                    for j in range(n):
                        if current != j and value(x[current, j]) == 1:
                            next_hop = j
                            break

                    if next_hop != -1:
                        f = flight_data.get((current, next_hop))
                        price = float(cost_matrix[current, next_hop])
                        duration = int(time_matrix[current, next_hop])

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
                            break 
                        visited.add(current)

                        if value(is_end[current]) == 1:
                            break
                    else:
                        break

    except Exception as e:
        import traceback
        traceback.print_exc()
        return SolverResult(
            status=f"Error: {str(e)}",
            itinerary=[],
            total_cost=0.0,
            total_duration=0,
            warning_message=f"Solver Crashed: {str(e)}",
            hotels_found=hotels
        )
    
    return SolverResult(
        status=status,
        itinerary=itinerary,
        total_cost=float(total_cost_val),
        total_duration=int(total_duration_val),
        alternatives={}, 
        hotels_found=hotels 
    )
