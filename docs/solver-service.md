# Solver Service API

Serviço FastAPI dedicado à otimização de itinerários (TSP + PuLP). Recebe entradas já coletadas (voos/hotéis/carros) e retorna o melhor roteiro.

## Como executar

- Local:
  - `pip install -r requirements.txt`
  - `uvicorn solver_service.main:app --host 0.0.0.0 --port 8002 --reload`
- Docker:
  - `docker compose up --build`
  - A API estará em `http://localhost:8002`

## Endpoints

### Health / Info

```bash
curl 'http://localhost:8002/api/v1/health'
curl 'http://localhost:8002/api/v1/info'
```

### Resolver itinerário

`POST /api/v1/solve` recebe `SolveRequestSchema` com:
- `travel_request` (preferências, datas, cidades)
- `flights` (lista de voos possíveis)
- `hotels` (opcional)
- `cars` (opcional)

Exemplo mínimo:
```bash
curl -X POST 'http://localhost:8002/api/v1/solve' \
  -H 'Content-Type: application/json' \
  -d '{
    "travel_request": {
      "origin_cities": ["São Paulo"],
      "destination_cities": ["Rio de Janeiro", "Belo Horizonte"],
      "mandatory_cities": [],
      "pax_adults": 1,
      "pax_children": 0,
      "start_date": "2026-02-01T00:00:00",
      "is_round_trip": false,
      "weight_cost": 0.7,
      "weight_time": 0.3,
      "allow_open_jaw": true,
      "stay_days_per_city": 2,
      "daily_cost_per_person": 200.0
    },
    "flights": [
      {
        "airline": "AZUL",
        "origin": "São Paulo",
        "destination": "Rio de Janeiro",
        "departure_time": "2026-02-01T08:00:00",
        "arrival_time": "2026-02-01T09:00:00",
        "price": 350.0,
        "duration_minutes": 60,
        "stops": 0,
        "flight_number": "AD1234",
        "details": "GRU->SDU"
      }
    ],
    "hotels": [],
    "cars": []
  }'
```
