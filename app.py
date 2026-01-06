import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
from data.models import Flight, Hotel, CarRental, TravelRequest
from data.crawler import MockCrawler, GoogleFlightsCrawler
from optimization.solver import solve_itinerary

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Viagem Otimizada - AI Powered", layout="wide", page_icon="✈️")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    h1 { color: #2E86C1; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR - ENTRADA DO USUÁRIO ---
st.sidebar.title("🛠️ Configuração da Viagem")

# Data e Pax
col_pax1, col_pax2 = st.sidebar.columns(2)
pax_adultos = col_pax1.number_input("Adultos", 1, 10, 1)
pax_criancas = col_pax2.number_input("Crianças", 0, 10, 0)
data_inicio = st.sidebar.date_input("Data de Início", datetime.today() + timedelta(days=30))

# Cidades
st.sidebar.subheader("Roteiro")
origens = st.sidebar.text_input("Origens Possíveis (sep. vírgula)", "São Paulo, Rio de Janeiro").split(",")
destinos = st.sidebar.text_input("Destinos Finais (sep. vírgula)", "Miami, Orlando").split(",")
obrigatorias = st.sidebar.multiselect("Paradas Obrigatórias", 
                                      ["New York", "Chicago", "Las Vegas", "Los Angeles", "San Francisco"],
                                      default=["New York"])

# Preferências
st.sidebar.subheader("Preferências de Otimização")
peso_custo = st.sidebar.slider("Peso: Custo Financeiro", 0.0, 1.0, 0.7)
peso_tempo = st.sidebar.slider("Peso: Tempo Total", 0.0, 1.0, 0.3)
allow_open_jaw = st.sidebar.checkbox("Permitir Open-Jaw (Retorno diferente)", value=True)

use_live_data = st.sidebar.toggle("Tentar Dados Reais (Beta)", value=False)

# Limpeza de input
origens = [c.strip() for c in origens if c.strip()]
destinos = [c.strip() for c in destinos if c.strip()]
todas_cidades = list(set(origens + destinos + obrigatorias))

# --- MAIN ---
st.title("🌍 Otimizador de Viagens Multi-Destino")
st.markdown(" Utilize Inteligência Artificial e Pesquisa Operacional para encontrar o melhor roteiro considerando **Custo** vs **Tempo**.")

if not origens or not destinos:
    st.warning("Por favor, preencha as cidades de origem e destino.")
    st.stop()

# Botão de Processamento
if st.button("🚀 Calcular Melhor Roteiro", type="primary"):
    
    with st.status("Processando sua viagem...", expanded=True) as status:
        
        # 1. Coleta de Dados
        status.write("🔍 Coletando dados de voos e hotéis...")
        
        crawler = GoogleFlightsCrawler(headless=True) if use_live_data else MockCrawler()
        
        # Loop to fetch flights from EACH city to all others to ensure connectivity (Mesh)
        flights = []
        for orig_city in todas_cidades:
            try:
                # Assuming crawler.fetch_flights takes strict origin and list of dests
                # For safety, remove self from dests
                dests = [c for c in todas_cidades if c != orig_city]
                if dests:
                    new_flights = crawler.fetch_flights(orig_city, dests, datetime.combine(data_inicio, datetime.min.time()))
                    flights.extend(new_flights)
            except Exception as e:
                print(f"Error fetching from {orig_city}: {e}")
        
        # Original fallback logic was too simplistic, assume above works for Mock
        if not flights and use_live_data:
             status.write("⚠️ Crawler bloqueado. Usando dados simulados.")
             crawler = MockCrawler()
             for orig_city in todas_cidades:
                dests = [c for c in todas_cidades if c != orig_city]
                if dests:
                    flights.extend(crawler.fetch_flights(orig_city, dests, datetime.combine(data_inicio, datetime.min.time())))

        hotels = crawler.fetch_hotels(todas_cidades)
        cars = crawler.fetch_car_rentals(todas_cidades)
        
        status.write(f"✅ Encontrados {len(flights)} voos e {len(hotels)} hotéis.")
        
        # DEBUG: Save to CSV
        if flights:
            df_debug = pd.DataFrame([f.__dict__ for f in flights])
            df_debug.to_csv("flights_captured.csv", index=False)
            st.success("Dados salvos em 'flights_captured.csv'")
            print(f"Saved {len(flights)} flights to flights_captured.csv")

        # 2. Otimização
        status.write("🧠 Executando Solver (TSP + MTZ)...")
        
        req = TravelRequest(
            origin_cities=origens,
            destination_cities=destinos,
            mandatory_cities=obrigatorias,
            pax_adults=pax_adultos,
            pax_children=pax_criancas,
            start_date=datetime.combine(data_inicio, datetime.min.time()),
            weight_cost=peso_custo,
            weight_time=peso_tempo,
            allow_open_jaw=allow_open_jaw
        )
        
        result = solve_itinerary(req, flights, hotels, cars)
        
        status.update(label="Processamento Concluído!", state="complete", expanded=False)

    # --- RESULTADOS ---
    if result["status"] == "Optimal":
        st.success("Roteiro Otimizado Encontrado!")
        
        # KPIS
        col1, col2, col3 = st.columns(3)
        total = result['total_cost']
        col1.metric("Custo Total Estimado", f"R$ {total:,.2f}")
        col2.metric("Número de Trechos", len(result['itinerary']))
        col3.metric("Status Otimização", "Ótimo Global")
        
        # Tabela Detalhada
        st.subheader("🗓️ Detalhes do Itinerário")
        
        itinerary_data = []
        path_coords = []
        
        # Mock Coords for map visualization since Crawler doesn't return lat/lon yet
        # In real app, Flight object would have coords or we'd geocode cities.
        mock_coords = {
            "São Paulo": [-23.55, -46.63], "Rio de Janeiro": [-22.90, -43.17],
            "Miami": [25.76, -80.19], "Orlando": [28.53, -81.37],
            "New York": [40.71, -74.00], "Chicago": [41.87, -87.62],
            "Las Vegas": [36.16, -115.13], "Los Angeles": [34.05, -118.24],
            "San Francisco": [37.77, -122.41], "Belo Horizonte": [-19.91, -43.93],
            "Brasília": [-15.78, -47.92]
        }

        for leg in result['itinerary']:
            f_obj = leg['flight']
            itinerary_data.append({
                "Origem": leg['from'],
                "Destino": leg['to'],
                "Cia Aérea": f_obj.airline if f_obj else "N/A",
                "Preço": f"R$ {leg['price']:.2f}",
                "Duração": f"{f_obj.duration_minutes} min" if f_obj else "-"
            })
            
            # Map paths
            if leg['from'] in mock_coords and leg['to'] in mock_coords:
                path_coords.append([mock_coords[leg['from']], mock_coords[leg['to']]])

        st.dataframe(pd.DataFrame(itinerary_data), width='stretch')

        # Map Visualization
        if path_coords:
            st.subheader("🗺️ Visualização no Mapa")
            
            # Create simple map df
            map_points = []
            for leg in result['itinerary']:
                orig = leg['from']
                dest = leg['to']
                if orig in mock_coords: map_points.append({"city": orig, "lat": mock_coords[orig][0], "lon": mock_coords[orig][1], "type": "Origem"})
                if dest in mock_coords: map_points.append({"city": dest, "lat": mock_coords[dest][0], "lon": mock_coords[dest][1], "type": "Destino"})
            
            df_map = pd.DataFrame(map_points).drop_duplicates(subset=['city'])
            st.map(df_map)

    else:
        st.error("Não foi possível encontrar um roteiro válido com as restrições informadas.")