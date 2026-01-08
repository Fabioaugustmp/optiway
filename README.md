# 🌍 OptiWay: Travel Itinerary Optimization System
### *Advanced Multi-Objective Travel Planning & Optimization Framework*

**OptiWay** é uma solução de arquitetura distribuída voltada ao planejamento de viagens multi-destino. O projeto integra técnicas de **Pesquisa Operacional (OR)**, **Web Crawling Distribuído** e **Microserviços** para resolver o problema de otimização de rotas com base em trade-offs de custo financeiro e eficiência temporal.

Este projeto foi desenvolvido com foco em robustez, escalabilidade e aplicação de modelos matemáticos complexos para situações do mundo real.

---

## 🎓 Fundamentação Científica e Objetivos

O núcleo do sistema aborda uma variante do **Problema do Caixeiro Viajante (Traveling Salesperson Problem - TSP)** com restrições adicionais de janelas de tempo, cidades obrigatórias e custos dinâmicos de estadia.

### Modelo Matemático
Utilizamos a formulação **MTZ (Miller-Tucker-Zemlin)** para eliminação de sub-rotas em um grafo direcionado.
- **Variáveis de Decisão**: $x_{ij} \in \{0, 1\}$, indicando se o trajeto entre as cidades $i$ e $j$ é selecionado.
- **Função Objetivo**: 
  $$\min Z = \alpha \cdot \text{CustoTotal} + \beta \cdot \text{TempoTotal}$$
  Onde $\alpha$ e $\beta$ são pesos atribuídos pelo usuário para equilibrar despesas financeiras e duração total da logística.

---

## 🏗️ Arquitetura do Sistema

O sistema é composto por três camadas principais operando de forma assíncrona:

1.  **Core Gateway (FastAPI - Porto 8000)**: Gerencia autenticação (JWT), persistência de dados (SQLAlchemy/SQLite) e orquestração de buscas.
2.  **Solver Service (FastAPI/PuLP - Porto 8002)**: Microserviço dedicado exclusivamente ao processamento matemático. Isolar o solver permite que a carga computacional pesada não afete a responsividade da API principal.
3.  **Data Acquisition Layer**: Conjunto de crawlers (Selenium/Amadeus) que realizam o scraping e consumo de APIs externas de aviação.

---

## 🛠️ Requisitos e Instalação

### Pré-requisitos
- Python 3.10+
- Navegador Google Chrome (para o Google Flights Scraper)
- PuLP Solver (CBC está incluído por padrão)

### Configuração do Ambiente

1.  **Clonar o repositório**:
    ```bash
    git clone <repository-url>
    cd traveler-cost
    ```

2.  **Criar e Ativar Ambiente Virtual**:
    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    ```

3.  **Instalar Dependências**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Variáveis de Ambiente**:
    Crie um arquivo `.env` na raiz com as seguintes chaves (exemplo no `.env.example`):
    ```env
    AMADEUS_API_KEY="SUA_CHAVE"
    AMADEUS_API_SECRET="SEU_SEGREDO"
    SECRET_KEY="SUA_SECRET_KEY_PARA_JWT"
    ```

---

## 🚀 Guia de Execução (Orquestração de Serviços)

Para que o sistema opere plenamente, os seguintes serviços devem ser iniciados em terminais separados:

### 1. Solver Microservice (Obrigatório para Otimização)
O solver deve estar rodando para processar os cálculos de rota.
```powershell
# No terminal 1
python -m solver_service.main
```
*Disponível em: `http://localhost:8002`*

### 2. Core API Gateway
Responsável pela interface web e endpoints de negócio.
```powershell
# No terminal 2
python main.py
```
*Disponível em: `http://localhost:8000`*

### 3. Flight Crawler Bridge (Opcional - Backend de busca)
Caso utilize as funcionalidades de crawling intensivo:
```powershell
# No terminal 3
python -m flight_crawler.main
```

---

## 📑 Referência da API e Exemplos de Consulta

### 🔐 Autenticação

#### Registro de Usuário
`POST /auth/register`
```bash
curl -X POST http://localhost:8000/auth/register \
-H "Content-Type: application/json" \
-d '{"email": "user@exemplo.com", "password": "123", "full_name": "Fabio Rodrigues"}'
```

#### Obter Token (Login)
`POST /auth/login`
```bash
curl -X POST http://localhost:8000/auth/login \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "username=user@exemplo.com&password=123"
```

### 🧠 Otimização de Roteiro

#### Resolver Viagem Completa
`POST /api/solve`
Requer o header `Authorization: Bearer <seu_token>`.

**Payload Exemplo:**
```json
{
  "origin_cities": ["São Paulo"],
  "destination_cities": ["Miami", "Orlando"],
  "mandatory_cities": ["New York"],
  "pax_adults": 2,
  "pax_children": 1,
  "start_date": "2026-02-01T00:00:00",
  "weight_cost": 0.7,
  "weight_time": 0.3,
  "is_round_trip": true,
  "stay_days_per_city": 3,
  "daily_cost_per_person": 150.0,
  "use_mock_data": true
}
```

**Exemplo de Comando cURL:**
```bash
curl -X POST http://localhost:8000/api/solve \
-H "Authorization: Bearer <SEU_TOKEN>" \
-H "Content-Type: application/json" \
-d '{...payload_acima...}'
```

---

## 🔍 Monitoramento e Debug

- **Swagger UI (Core)**: `http://localhost:8000/docs`
- **Swagger UI (Solver)**: `http://localhost:8002/docs`
- **Dashboards**: Acesse `http://localhost:8000` via navegador para uma experiência visual completa.

---

## 🚧 Solução de Problemas (Troubleshooting)

- **ImportError / No Module Named**: Certifique-se de estar rodando os comandos com `python -m <module>` a partir da raiz do projeto para que o PYTHONPATH seja resolvido corretamente.
- **Porta 8000/8002 em uso**: Caso ocorra erro de endereço em uso, identifique o processo no Windows com `netstat -ano | findstr :8000` e finalize-o no Gerenciador de Tarefas ou use `taskkill /F /PID <PID>`.
- **Static Files NotFound**: O sistema exige a pasta `app/static`. Esta pasta é criada automaticamente na inicialização, mas deve existir para o servidor servir os assets.

---

*Documentação gerada como parte do currículo de Pós-Graduação em Engenharia de Software e Otimização Combinatória.*

