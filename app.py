import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
from data.models import Flight, Hotel, CarRental, TravelRequest
from data.crawler import MockCrawler, GoogleFlightsCrawler, AmadeusCrawler
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
data_fim = st.sidebar.date_input("Data de Retorno", datetime.today() + timedelta(days=40))

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
st.sidebar.markdown("---")

# Provider Selection
st.sidebar.subheader("Provedor de Voos")
provider = st.sidebar.selectbox("Escolha o Provedor", ["Google Flights (Scraper)", "Amadeus API", "Mock Data"])

# Load env vars
import os
from dotenv import load_dotenv
load_dotenv()

amadeus_key = os.getenv("AMADEUS_API_KEY", "")
amadeus_secret = os.getenv("AMADEUS_API_SECRET", "")

if provider == "Amadeus API":
    amadeus_key = st.sidebar.text_input("Amadeus API Key", value=amadeus_key)
    amadeus_secret = st.sidebar.text_input("Amadeus API Secret", value=amadeus_secret, type="password")
    use_prod = st.sidebar.checkbox("Usar Ambiente de Produção", value=False)
    
    
    # Inputs moved to global scope below

# Limpeza de input
origens = [c.strip() for c in origens if c.strip()]
destinos = [c.strip() for c in destinos if c.strip()]
todas_cidades = list(set(origens + destinos + obrigatorias))

# --- Cost Parameters (Global) ---
st.sidebar.markdown("---")
st.sidebar.subheader("💰 Estimativa de Custos Extras")
custo_hotel = st.sidebar.number_input("Média Hotel/Noite (R$)", min_value=0.0, value=300.0, step=50.0)
custo_carro = st.sidebar.number_input("Aluguel Carro/Dia (R$)", min_value=0.0, value=150.0, step=10.0)
custo_diario = st.sidebar.number_input("Gasto Diário/Pessoa (R$)", min_value=0.0, value=200.0, step=20.0)
dias_por_cidade = st.sidebar.number_input("Dias por Cidade (Est.)", min_value=1, value=3)
alugar_carro = st.sidebar.checkbox("Alugar Carro?", value=False)

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
        


        # Crawler Initialization
        if provider == "Google Flights (Scraper)":
            crawler = GoogleFlightsCrawler(headless=True)
        elif provider == "Amadeus API":
            if amadeus_key and amadeus_secret:
                # Sanitize inputs
                clean_key = amadeus_key.strip()
                clean_secret = amadeus_secret.strip()
                print(f"Initializing Amadeus with Key ID starting: {clean_key[:6]}...") 
                print(f"Secret starting: {clean_secret[:4]}...")
                print(f"Environment: {'PRODUCTION' if use_prod else 'TEST'}")
                crawler = AmadeusCrawler(clean_key, clean_secret, production=use_prod)
            else:
                st.warning("⚠️ Credenciais Amadeus não fornecidas. Usando Mock.")
                crawler = MockCrawler()
        else:
            crawler = MockCrawler()
        
        # Loop to fetch flights from EACH city to all others to ensure connectivity (Mesh)
        flights = []
        for orig_city in todas_cidades:
            try:
                # Assuming crawler.fetch_flights takes strict origin and list of dests
                # For safety, remove self from dests
                dests = [c for c in todas_cidades if c != orig_city]
                if dests:
                    new_flights = crawler.fetch_flights(orig_city, dests, datetime.combine(data_inicio, datetime.min.time()), adults=pax_adultos, children=pax_criancas)
                    flights.extend(new_flights)
            except Exception as e:
                print(f"Error fetching from {orig_city}: {e}")
        
        # Original fallback logic was too simplistic, assume above works for Mock
        if not flights and provider != "Mock Data":
             status.write("⚠️ Crawler bloqueado ou sem dados. Usando dados simulados.")
             crawler = MockCrawler()
             for orig_city in todas_cidades:
                dests = [c for c in todas_cidades if c != orig_city]
                if dests:
                    flights.extend(crawler.fetch_flights(orig_city, dests, datetime.combine(data_inicio, datetime.min.time()), adults=pax_adultos, children=pax_criancas))

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
            allow_open_jaw=allow_open_jaw,
            is_round_trip=not allow_open_jaw,
            stay_days_per_city=dias_por_cidade,
            daily_cost_per_person=custo_diario
        )
        
        result = solve_itinerary(req, flights, hotels, cars)
        
        status.update(label="Processamento Concluído!", state="complete", expanded=False)

    # --- RESULTADOS ---
    if result["status"] == "Optimal":
        # --- CÁLCULO DE CUSTO TOTAL ---
        n_cidades_destino = len(destinos) + len(obrigatorias)
        dias_totais = dias_por_cidade * n_cidades_destino
        
        # Flight cost from result (assuming 'total_price' key or derived from itinerary)
        # Verify if result has 'total_price', else sum it up
        custo_voos = 0.0
        for leg in result['itinerary']:
            if 'price' in leg: # Price might be in 'flight' object or top level
                 # Check structure: leg['flight'].price covers it?
                 # Leg structure in solver output usually copies flight details
                 # Let's rely on result['total_cost'] if it only tracks FLIGHT cost?
                 # No, result['total_cost'] is the OBJECTIVE FUNCTION value (mixed cost+time).
                 # We need pure money cost.
                 pass

        # Recalculate pure flight cost from itinerary
        custo_voos = sum([leg['flight'].price for leg in result['itinerary']])

        custo_hospedagem = custo_hotel * dias_totais
        custo_alimentacao = custo_diario * dias_totais * (pax_adultos + pax_criancas)
        custo_transporte = (custo_carro * dias_totais) if alugar_carro else 0
        
        custo_total_viagem = custo_voos + custo_hospedagem + custo_alimentacao + custo_transporte

        st.success(f"✅ Roteiro Otimizado Encontrado!")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Custo Total (Est.)", f"R$ {custo_total_viagem:,.2f}")
        col2.metric("Custo Voos", f"R$ {custo_voos:,.2f}")
        col3.metric("Tempo Voos", f"{result['total_duration']} min")
        col4.metric("Dias Totais", f"{dias_totais} dias")
        
        with st.expander("💸 Detalhamento dos Custos"):
            st.write(f"- **Voos**: R$ {custo_voos:,.2f}")
            st.write(f"- **Hospedagem ({dias_totais} noites)**: R$ {custo_hospedagem:,.2f}")
            st.write(f"- **Alimentação/Extras**: R$ {custo_alimentacao:,.2f}")
            if alugar_carro:
                st.write(f"- **Carro ({dias_totais} dias)**: R$ {custo_transporte:,.2f}")
            st.info("Obs: Custos de hotel/carro são estimativas baseadas nos seus inputs.")
        
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
                "Duração": f"{f_obj.duration_minutes} min" if f_obj else "-",
                "Paradas": f"{f_obj.stops}" if f_obj else "-",
                "Bagagem": f"{f_obj.baggage}" if f_obj else "-",
                "Detalhes": f"{f_obj.details}" if f_obj else "-"
            })
            
            # Map paths
            if leg['from'] in mock_coords and leg['to'] in mock_coords:
                path_coords.append([mock_coords[leg['from']], mock_coords[leg['to']]])

        st.dataframe(pd.DataFrame(itinerary_data), use_container_width=True)

        # --- OUTRAS OPÇÕES ---
        st.subheader("🔍 Outras Opções de Voos Encontradas")
        
        alternatives_coords = []
        
        for leg in result['itinerary']:
            orig = leg['from']
            dest = leg['to']
            
            # Filter all fetched flights for this leg
            alternatives = [f for f in flights if f.origin == orig and f.destination == dest]
            # Exclude the one chosen (optional, or just list all sorted)
            alternatives.sort(key=lambda x: x.price)
            
            with st.expander(f"Ver opções para: {orig} ➡️ {dest} ({len(alternatives)} opções)"):
                alt_data = []
                for alt_f in alternatives:
                    alt_data.append({
                        "Cia": alt_f.airline,
                        "Preço": alt_f.formatted_price,
                        "Duração": f"{alt_f.duration_minutes} min",
                        "Paradas": alt_f.stops,
                        "Bagagem": alt_f.baggage,
                        "Detalhes": alt_f.details
                    })
                    
                    # Collect coords for map (Alternatives)
                    if orig in mock_coords and dest in mock_coords:
                         alternatives_coords.append({
                            "source": mock_coords[orig],
                            "target": mock_coords[dest],
                            "tooltip": f"Alternative: {orig}->{dest} ({alt_f.airline})"
                        })

                st.table(pd.DataFrame(alt_data))

        # Map Visualization
        st.subheader("🗺️ Visualização das Rotas")
        
        # Expanded Coords for Asia/Oceania context
        mock_coords.update({
            "SYD": [-33.86, 151.20], "SGN": [10.82, 106.62],
            "BKK": [13.75, 100.50], "MNL": [14.59, 120.98],
            "XMN": [24.47, 118.08], "DPS": [-8.74, 115.16],
            "CAN": [23.39, 113.29], "SIN": [1.35, 103.98],
            "KUL": [2.74, 101.69], "HKG": [22.31, 113.91]
        })

        if path_coords or alternatives_coords:
            import pydeck as pdk
            
            # 1. Optimal Route (Red)
            optimal_layer_data = []
            for leg in result['itinerary']:
                if leg['from'] in mock_coords and leg['to'] in mock_coords:
                    optimal_layer_data.append({
                        "source": [mock_coords[leg['from']][1], mock_coords[leg['from']][0]], # [Lon, Lat]
                        "target": [mock_coords[leg['to']][1], mock_coords[leg['to']][0]],
                        "tooltip": f"Optimal: {leg['from']}->{leg['to']}"
                    })

            # 2. Alternatives Data (Yellow)
            alt_layer_data = []
            for item in alternatives_coords:
                 # item['source'] is [Lat, Lon] from mock_coords
                 alt_layer_data.append({
                    "source": [item['source'][1], item['source'][0]],
                    "target": [item['target'][1], item['target'][0]],
                    "tooltip": item['tooltip']
                 })

            # Determine View State Center
            mid_lat, mid_lon = 0, 0
            count = 0
            
            # Collect all points to find center
            all_lats = []
            all_lons = []
            
            for d in optimal_layer_data:
                all_lons.append(d["source"][0])
                all_lats.append(d["source"][1])
            
            for d in alt_layer_data:
                all_lons.append(d["source"][0])
                all_lats.append(d["source"][1])
                
            if all_lats and all_lons:
                mid_lat = sum(all_lats) / len(all_lats)
                mid_lon = sum(all_lons) / len(all_lons)
            elif mock_coords and "GRU" in mock_coords:
                 mid_lat, mid_lon = mock_coords["GRU"][0], mock_coords["GRU"][1]

            view_state = pdk.ViewState(
                latitude=mid_lat,
                longitude=mid_lon,
                zoom=3,
                pitch=40,
            )

            # Layers
            layers = []
            
            if alt_layer_data:
                layers.append(pdk.Layer(
                    "ArcLayer",
                    data=alt_layer_data,
                    get_source_position="source",
                    get_target_position="target",
                    get_source_color=[255, 215, 0, 150], # Gold, semi-transparent
                    get_target_color=[255, 215, 0, 150],
                    get_width=2,
                    pickable=True,
                ))
            
            if optimal_layer_data:
                layers.append(pdk.Layer(
                    "ArcLayer",
                    data=optimal_layer_data,
                    get_source_position="source",
                    get_target_position="target",
                    get_source_color=[255, 0, 0, 255], # Red, Solid
                    get_target_color=[255, 0, 0, 255],
                    get_width=5,
                    pickable=True,
                ))

            r = pdk.Deck(
                layers=layers,
                initial_view_state=view_state,
                tooltip={"text": "{tooltip}"},
                # Using a default safe style or None
                map_style=None
            )
            
            st.pydeck_chart(r, use_container_width=True)

            # Legend
            st.markdown("""
            <div style='display: flex; gap: 20px;'>
                <div><span style='color:red; font-weight:bold;'>—</span> Rota Principal (Otimizada)</div>
                <div><span style='color:#FFD700; font-weight:bold;'>—</span> Rotas Alternativas</div>
            </div>
            """, unsafe_allow_html=True)

    else:
        st.error("Não foi possível encontrar um roteiro válido com as restrições informadas.")