# Flight Crawler API

Serviço FastAPI para realizar crawling de voos e aluguel de carros usando scrapers (Playwright).

## Como executar

- Local:
  - `pip install -r flight_crawler/requirements.txt`
  - `python -m playwright install --with-deps`
  - `uvicorn flight_crawler.main:app --host 0.0.0.0 --port 8001 --reload`
- Docker:
  - `docker compose up --build`
  - A API estará em `http://localhost:8001`

## Endpoints

### Health

```bash
curl 'http://localhost:8001/health'
```

### Crawling de voos

`POST /api/v1/crawl` recebe uma lista de entradas `FlightSearchInput`.

Schema (simplificado):
- `origin` (string)
- `destination` (string)
- `departure_date` (YYYY-MM-DD)
- `return_date` (opcional)
- `passengers` (int)
- `scrapers` (lista opcional: ex. ["google_flights", "latam", "azul", "gol", "kayak"]) 

Exemplo:
```bash
curl -X POST 'http://localhost:8001/api/v1/crawl' \
  -H 'Content-Type: application/json' \
  -d '[
    {
      "origin": "GRU",
      "destination": "RIO",
      "departure_date": "2026-02-01",
      "passengers": 1,
      "scrapers": ["google_flights", "kayak"]
    },
    {
      "origin": "GRU",
      "destination": "BHZ",
      "departure_date": "2026-02-03",
      "passengers": 1
    }
  ]'
```

### Crawling de carros

`POST /api/v1/crawl-cars` recebe uma lista `CarSearchInput`.

Schema (simplificado):
- `city` (string)
- `pick_up_date` (YYYY-MM-DD)
- `drop_off_date` (YYYY-MM-DD)
- `scrapers` (lista opcional)

Exemplo:
```bash
curl -X POST 'http://localhost:8001/api/v1/crawl-cars' \
  -H 'Content-Type: application/json' \
  -d '[
    {
      "city": "São Paulo",
      "pick_up_date": "2026-02-01",
      "drop_off_date": "2026-02-05"
    }
  ]'
```
