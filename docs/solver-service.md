# Documentação Técnica: Serviço de Otimização (Solver Service)

## 1. Introdução

O **Solver Service** representa o núcleo algorítmico do ecossistema OptiWay, projetado para resolver o Problema de Roteamento de Viagens Multi-Cidades (*Multi-City Travel Routing Problem*). Diferente de mecanismos de busca convencionais que agregam passagens ponto-a-ponto, este serviço aborda a construção de itinerários complexos como um problema de otimização combinatória, visando minimizar uma função de custo composta por variáveis financeiras e temporais.

Este documento detalha a formulação matemática, a modelagem algorítmica e a implementação computacional do solucionador, estruturado para atender requisitos de nível acadêmico avançado.

---

## 2. Formulação Matemática

O problema é modelado como uma variação do **Problema do Caixeiro Viajante Assimétrico (ATSP - Asymmetric Traveling Salesman Problem)** em um grafo direcionado $G = (V, A)$, onde:

- $V = \{0, 1, ..., n-1\}$ é o conjunto de vértices, representando as cidades envolvidas (origem, destinos intermediários e mandatórios).
- $A = \{(i, j) \in V \times V : i \neq j\}$ é o conjunto de arcos, representando a existência de voos ou conexões diretas entre as cidades.

### 2.1 Variáveis de Decisão

Para a formulação de Programação Linear Inteira Mista (MILP), definimos as seguintes variáveis:

1.  **Variáveis de Fluxo (Binárias)**:
    $$x_{i,j} \in \{0, 1\}, \quad \forall (i, j) \in A$$
    Indica se o arco do nó $i$ para o nó $j$ faz parte da solução ótima.

2.  **Variáveis de Eliminação de Subciclos (Contínuas)**:
    $$u_i \in \mathbb{R}_{\geq 0}, \quad \forall i \in V$$
    Variáveis auxiliares utilizadas na formulação Miller-Tucker-Zemlin (MTZ) para ordenar a viscositação dos nós e prevenir subciclos desconexos.

3.  **Variáveis de Início e Fim (Binárias)**:
    $$s_i, e_i \in \{0, 1\}, \quad \forall i \in V$$
    Definem, respectivamente, se o nó $i$ é o ponto de partida ou o ponto de término do itinerário.

### 2.2 Função Objetivo

O objetivo é minimizar o custo generalizado ($Z$) do itinerário, que pondera o impacto financeiro e o tempo total de viagem. Seja $C_{i,j}$ o custo monetário da transição $i \to j$ (incluindo preço do voo e custos de estadia no nó de destino) e $T_{i,j}$ o tempo associado à transição.

$$ \min Z = \sum_{i \in V} \sum_{j \in V, j \neq i} x_{i,j} \cdot (\alpha \cdot C_{i,j} + \beta \cdot T_{i,j}) $$

Onde:
- $\alpha$: Peso atribuído ao fator custo (normalizado entre 0 e 1).
- $\beta$: Peso atribuído ao fator tempo (normalizado entre 0 e 1).
- $C_{i,j}$: Custo do voo + (Custo diário de hotel em $j \times$ dias de estadia).

### 2.3 Restrições (Constraints)

#### 2.3.1 Conservação de Fluxo e Topologia
O sistema deve garantir um caminho contínuo de um nó inicial único para um nó final único, visitando os nós intermediários necessários.

1.  **Definição de Início e Fim Únicos**:
    $$ \sum_{i \in V} s_i = 1 \quad \text{e} \quad \sum_{i \in V} e_i = 1 $$

2.  **Equilíbrio de Fluxo nos Nós**:
    Para todo nó $k \in V$, a diferença entre o fluxo de saída e o fluxo de entrada deve corresponder à sua designação como início ou fim:
    $$ \sum_{j \in V, j \neq k} x_{k,j} - \sum_{i \in V, i \neq k} x_{i,k} = s_k - e_k $$

#### 2.3.2 Restrições de Visitação Obrigatória
Seja $V_{dest} \subseteq V$ o conjunto de cidades de destino que devem obrigatoriamente ser visitadas. Para cada $k \in V_{dest}$, deve haver pelo menos um arco de entrada ou o nó deve ser o ponto de partida:

$$ \sum_{i \in V, i \neq k} x_{i,k} + s_k \geq 1, \quad \forall k \in V_{dest} $$

Analogamente para o fluxo de saída:

$$ \sum_{j \in V, j \neq k} x_{k,j} + e_k \geq 1, \quad \forall k \in V_{dest} $$

#### 2.3.3 Restrições de Subciclo (Miller-Tucker-Zemlin)
Para evitar a formação de ciclos isolados que não conectam a origem ao destino (subtours), aplicam-se as restrições MTZ:

$$ u_i - u_j + n \cdot x_{i,j} \leq n - 1, \quad \forall i, j \in V, i \neq j $$

Essas restrições impõem uma ordem topológica sequencial à visitação, garantindo que o itinerário forme um caminho hamiltoniano (ou semi-hamiltoniano) válido.

#### 2.3.4 Restrições de Domínio (Open Jaw vs. Round Trip)
- **Round Trip (Ida e Volta)**: Impõe-se que o nó de início seja igual ao nó de fim ($s_i = e_i$).
- **Open Jaw**: Permite que o nó de início e fim sejam distintos, desde que pertençam aos conjuntos de origem e destino permitidos.

---

## 3. Implementação Computacional

### 3.1 Arquitetura do Software

O serviço é implementado em **Python 3.12**, utilizando o framework **FastAPI** para exposição dos endpoints RESTful. A arquitetura segue o padrão de design de microsserviços, isolando a lógica de otimização da camada de persistência e da interface de usuário.

### 3.2 Otimizador (Solver Engine)

A biblioteca **PuLP** é utilizada para a modelagem algébrica do problema MILP. O PuLP atua como uma interface de alto nível que traduz as variáveis e restrições Python para o formato padrão *MPS* ou *LP*, que é então resolvido pelo **CBC (Coin-OR Branch and Cut)** solver.

**Características do CBC Utilizado:**
- **Algoritmo**: Branch-and-Cut.
- **Heurísticas**: Simplex Primal/Dual com cortes de Gomory e cortes de Clique.
- **Complexidade**: Sendo o TSP um problema NP-Hard, a solução exata para $n$ grande é computacionalmente intratável. No entanto, para instâncias típicas de turismo ($n \leq 10$), o solver converge para a otimalidade global em tempo sub-segundo.

### 3.3 Construção do Grafo

Antes da otimização, o serviço executa a etapa de **Consolidação de Dados**:
1.  **Vértices**: União dos conjuntos de cidades de origem, destino e mandatórias.
2.  **Matriz de Adjacência**:
    - Inicializada com custos infinitos ($M = \infty$).
    - Preenchida com os dados reais de voos obtidos pelo *Crawler Service*.
    - Em casos de múltiplos voos entre dois nós, seleciona-se o de menor custo ajustado (preço vs duração) para a construção da aresta (pré-processamento guloso).

### 3.4 Tratamento de Inviabilidade

O modelo incorpora robustez para cenários de inviabilidade:
- **Grafos Desconexos**: Caso não existam voos conectando subconjuntos de cidades, as variáveis $x_{i,j}$ para arcos inexistentes são fixadas em 0.
- **Alternativas Parciais**: Se o status do solver não for "Optimal", o sistema é capaz de identificar componentes conexos parciais ou sugerir modais alternativos (ex: transporte terrestre gerado sinteticamente para distâncias curtas, calculadas via Distância de Haversine).

---

## 4. API Specification

### POST `/api/v1/solve`

Endpoint principal que orquestra a execução do modelo.

**Input (`SolveRequestSchema`)**:
- Vetores de preferências do usuário (cidades, datas, orçamentos, pesos $\alpha, \beta$).
- Listas de objetos: `Flight`, `Hotel` (opcional), `CarRental` (opcional).

**Output (`SolveResponseSchema`)**:
- Relatório de estado: `Optimal`, `Infeasible` ou `Unbounded`.
- `itinerary`: Lista ordenada de arestas (legs) compondo a solução.
- `cost_breakdown`: Decomposição vetorial dos custos (Voo, Hotel, Carro).
- Metadados de performance (tempo de execução, gap de otimalidade).

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
```json
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

---

## 5. Referências Bibliográficas e Teóricas

1.  **Miller, C. E., Tucker, A. W., & Zemlin, R. A. (1960).** Integer programming formulation of traveling salesman problems. *Journal of the ACM (JACM)*, 7(4), 326-329.
2.  **Dantzig, G. B., Fulkerson, D. R., & Johnson, S. M. (1954).** Solution of a large-scale traveling-salesman problem. *Operations Research*, 2(4), 393-410.
3.  **Applegate, D. L., Bixby, R. E., Chvátal, V., & Cook, W. J. (2006).** *The Traveling Salesman Problem: A Computational Study*. Princeton University Press.
4.  **Mitchell, J. E. (2002).** Branch-and-Cut Algorithms for Combinatorial Optimization Problems. *Handbook of Applied Optimization*, 65-77.
