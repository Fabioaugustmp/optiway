# Backend API (main)

Serviço FastAPI principal que expõe autenticação, busca de localizações, solução de itinerários e histórico.

## Como executar

- Local:
  - `pip install -r requirements.txt`
  - `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
- Docker:
  - `docker compose up --build`
  - A API estará em `http://localhost:8000`

## Autenticação

Fluxo recomendado:
1. Registrar usuário
2. Fazer login para obter `access_token`
3. Usar `Authorization: Bearer <token>` nas chamadas protegidas

### Registrar

```bash
curl -X POST 'http://localhost:8000/auth/register' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "user@example.com",
    "password": "strong-pass",
    "full_name": "User Test"
  }'
```

### Login (OAuth2 Password Flow)

```bash
curl -X POST 'http://localhost:8000/auth/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=user@example.com&password=strong-pass'
```

Resposta:
```json
{ "access_token": "<token>", "token_type": "bearer" }
```

## Localizações

### Autocomplete de locais

```bash
curl 'http://localhost:8000/api/locations/search?q=Sao%20Paulo'
```

### Validação de lista de locais

```bash
curl 'http://localhost:8000/api/locations/validate?q=GRU&q=SDU&q=AAA'
```

## Viagens (Solver)

### Resolver itinerário

Endpoint protegido (Bearer).

```bash
TOKEN="<seu_token>"
curl -X POST 'http://localhost:8000/api/solve' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "origin_cities": ["São Paulo"],
    "destination_cities": ["Rio de Janeiro", "Belo Horizonte"],
    "mandatory_cities": [],
    "pax_adults": 1,
    "pax_children": 0,
    "start_date": "2026-02-01T00:00:00",
    "is_round_trip": false,
    "provider": "Mock Data",
    "weight_cost": 0.7,
    "weight_time": 0.3,
    "allow_open_jaw": true,
    "stay_days_per_city": 2,
    "daily_cost_per_person": 200.0,
    "search_hotels": false
  }'
```

### Listar itinerários do usuário

```bash
TOKEN="<seu_token>"
curl 'http://localhost:8000/api/itineraries' -H "Authorization: Bearer $TOKEN"
```

### Detalhe do itinerário

```bash
TOKEN="<seu_token>"
ITINERARY_ID=1
curl "http://localhost:8000/api/itineraries/$ITINERARY_ID" -H "Authorization: Bearer $TOKEN"
```

## Usuários

### Histórico de buscas

```bash
TOKEN="<seu_token>"
curl 'http://localhost:8000/users/history' -H "Authorization: Bearer $TOKEN"
```

### Detalhe de uma busca

```bash
TOKEN="<seu_token>"
SEARCH_ID=1
curl "http://localhost:8000/users/history/$SEARCH_ID" -H "Authorization: Bearer $TOKEN"
```
