# Industrial Cutting Optimization API v2.0

This microservice provides a high-precision, financial-industrial solver for textile cutting optimization. It uses a Total Cost of Operation (TCO) model to balance material waste, labor, CAD setup, and strategic underproduction.

## Endpoints

### `POST /api/v1/optimize`

Solves a multi-colorway cutting job to minimize total manufacturing expense.

#### Request Payload (`CutRequest`)

| Field | Type | Description | Default |
| :--- | :--- | :--- | :--- |
| `demand_data` | `dict` | Maps `(Colorway) -> {Size: Quantity}` | Required |
| `table_length_cm` | `int` | Usable length of the cutting table. | Required |
| `fabric_width_cm` | `int` | Usable width of the fabric (minus selvedge). | Required |
| `nesting_efficiency` | `float` | Estimated CAD nesting utilization (0.0 - 1.0). | `0.85` |
| **TCO Overrides** | | | |
| `max_shortage_pct` | `float` | Global backstop for underproduction (e.g. 0.05 for 5%). | `0.05` |
| `shortage_penalty_multiplier` | `float` | Penalty for short-shipping (e.g. 1.5x fabric cost). | `1.5` |
| **Anomaly Gates** | | | |
| `anomaly_scaling_pct` | `float` | % of the anchor size to identify "awkward" outliers. | `0.02` (2%) |
| `hard_anomaly_ceiling` | `int` | Hard count cap for anomaly identification. | `3` |

#### Response Schema (`OptimizationResponse`)

- `status`: Solver status (`OPTIMAL`, `FEASIBLE`, `INFEASIBLE`).
- `solve_time_ms`: Computation time.
- `total_financial_waste`: Cost of fabric surplus (overproduction).
- `markers`: List of physical layout results.
- `ledger`: Detailed production vs. shortage decisions per size/colorway.

---

## Core Features

### 1. Financial-Industrial TCO Engine
The solver does not use abstract weights. Every decision is pegged to currency:
- **Marker Setup**: Fixed CAD cost + variable paper/plotting length cost.
- **Labor**: Cost per layer spread.
- **Waste**: Cost of fabric surplus vs. cost of short-shipping penalty.

### 2. Strategic Underproduction (Short-Shipping)
The engine utilizes **Slack Variables** to allow for underproduction if the cost of fulfillment exceeds the business penalty. This prevents the solver from creating expensive, low-ply markers for a single remainder piece.

### 3. Hybrid Dynamic Anomaly Gate
Protects assortment integrity while allowing flexibility for outliers:
- **Anomalies**: Sizes with demand below the dynamic threshold can be shorted up to 100%.
- **Core Sizes**: Protected by a strict 12% operational backstop.

---

## Example Usage (Python)

```python
import requests

payload = {
    "demand_data": {
        "PRETO": {"P": 10, "M": 50, "G": 45},
        "BRANCO": {"M": 40, "G": 30, "G3": 1}
    },
    "table_length_cm": 800,
    "fabric_width_cm": 180,
    "anomaly_scaling_pct": 0.02
}

response = requests.post("http://localhost:8000/api/v1/optimize", json=payload)
print(response.json())
```
