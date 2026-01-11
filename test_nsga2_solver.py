#!/usr/bin/env python3
"""
Script de teste para validar a implementação NSGA-II do solver.
Simula uma requisição de viagem e verifica o funcionamento.
"""

import sys
from datetime import datetime, timedelta
from typing import List

# Importar schemas
from solver_service.models.schemas import (
    FlightSchema,
    HotelSchema,
    CarRentalSchema,
    TravelRequestSchema,
    ItineraryLegSchema,
    SolveResponseSchema
)

# Importar solver
from solver_service.models.solver import solve_itinerary

def create_test_flights() -> List[FlightSchema]:
    """Criar voos de teste"""
    base_date = datetime(2026, 2, 1)
    return [
        # São Paulo → Rio de Janeiro
        FlightSchema(
            airline="LATAM",
            origin="São Paulo",
            destination="Rio de Janeiro",
            departure_time=base_date + timedelta(hours=8),
            arrival_time=base_date + timedelta(hours=10),
            price=350.0,
            duration_minutes=120,
            stops=0,
            flight_number="LA101"
        ),
        FlightSchema(
            airline="Gol",
            origin="São Paulo",
            destination="Rio de Janeiro",
            departure_time=base_date + timedelta(hours=14),
            arrival_time=base_date + timedelta(hours=16),
            price=280.0,
            duration_minutes=120,
            stops=0,
            flight_number="G201"
        ),
        
        # Rio de Janeiro → Belo Horizonte
        FlightSchema(
            airline="LATAM",
            origin="Rio de Janeiro",
            destination="Belo Horizonte",
            departure_time=base_date + timedelta(hours=10, minutes=30),
            arrival_time=base_date + timedelta(hours=12),
            price=220.0,
            duration_minutes=90,
            stops=0,
            flight_number="LA201"
        ),
        
        # Belo Horizonte → São Paulo
        FlightSchema(
            airline="Azul",
            origin="Belo Horizonte",
            destination="São Paulo",
            departure_time=base_date + timedelta(hours=16),
            arrival_time=base_date + timedelta(hours=18),
            price=210.0,
            duration_minutes=120,
            stops=0,
            flight_number="AZ301"
        ),
    ]

def create_test_hotels() -> List[HotelSchema]:
    """Criar hotéis de teste"""
    return [
        HotelSchema(
            city="São Paulo",
            name="Hotel Paulista",
            price_per_night=150.0,
            rating=4.5
        ),
        HotelSchema(
            city="Rio de Janeiro",
            name="Hotel Copacabana",
            price_per_night=200.0,
            rating=4.8
        ),
        HotelSchema(
            city="Belo Horizonte",
            name="Hotel Centro",
            price_per_night=120.0,
            rating=4.2
        ),
    ]

def create_test_request() -> TravelRequestSchema:
    """Criar requisição de teste"""
    return TravelRequestSchema(
        origin_cities=["São Paulo"],
        destination_cities=["Rio de Janeiro"],
        mandatory_cities=["Belo Horizonte"],
        pax_adults=2,
        pax_children=1,
        start_date=datetime(2026, 2, 1),
        return_date=datetime(2026, 2, 10),
        is_round_trip=True,
        weight_cost=0.7,      # Preferência por custo
        weight_time=0.3,
        allow_open_jaw=True,
        stay_days_per_city=2,
        daily_cost_per_person=100.0
    )

def test_solver():
    """Executar teste do solver"""
    print("=" * 60)
    print("TESTE DE VALIDAÇÃO - NSGA-II SOLVER")
    print("=" * 60)
    
    print("\n1. Preparando dados de teste...")
    flights = create_test_flights()
    hotels = create_test_hotels()
    request = create_test_request()
    
    print(f"   ✓ {len(flights)} voos carregados")
    print(f"   ✓ {len(hotels)} hotéis carregados")
    print(f"   ✓ Requisição criada: {request.origin_cities[0]} → {request.destination_cities[0]}")
    
    print("\n2. Executando NSGA-II Solver...")
    try:
        response = solve_itinerary(request, flights, hotels, [])
        print(f"   ✓ Solver executado com sucesso")
    except Exception as e:
        print(f"   ✗ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n3. Validando resultado...")
    
    # Validar status
    if response.status not in ["Optimal", "Feasible"]:
        print(f"   ✗ Status inválido: {response.status}")
        return False
    print(f"   ✓ Status: {response.status}")
    
    # Validar itinerário
    if not response.itinerary:
        print(f"   ⚠ Nenhum itinerário gerado")
        return False
    print(f"   ✓ Itinerário gerado: {len(response.itinerary)} legs")
    
    # Validar custos
    if response.total_cost <= 0:
        print(f"   ✗ Custo inválido: {response.total_cost}")
        return False
    print(f"   ✓ Custo total: R$ {response.total_cost:.2f}")
    
    # Validar duração
    if response.total_duration <= 0:
        print(f"   ✗ Duração inválida: {response.total_duration}")
        return False
    print(f"   ✓ Duração total: {response.total_duration} minutos")
    
    # Validar breakdown
    if response.cost_breakdown:
        print(f"   ✓ Breakdown:")
        print(f"     - Voos: R$ {response.cost_breakdown.get('flight', 0):.2f}")
        print(f"     - Hotéis: R$ {response.cost_breakdown.get('hotel', 0):.2f}")
        print(f"     - Carros: R$ {response.cost_breakdown.get('car', 0):.2f}")
    
    print("\n4. Detalhamento do itinerário:")
    for i, leg in enumerate(response.itinerary, 1):
        print(f"   {i}. {leg.origin} → {leg.destination}")
        print(f"      Preço: R$ {leg.price:.2f}")
        print(f"      Duração: {leg.duration} minutos")
    
    print("\n" + "=" * 60)
    print("✓ TESTE PASSOU COM SUCESSO!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_solver()
    sys.exit(0 if success else 1)
