# MRP Cutting Optimization Engine — API Documentation

**Version:** 1.0.0  
**Base URL:** `http://localhost:8000`  
**Engine:** Google OR-Tools CP-SAT Solver

---

## Overview

The MRP Cutting Optimization Engine is a REST API that solves fabric cutting plan problems for garment manufacturing. Given production demand across colorways and sizes, it outputs an optimized set of **markers** — spreading plans that minimize fabric waste, layer count, and financial cost while satisfying all demand constraints.

The API exposes two endpoints:

| Endpoint | Description |
|---|---|
| `POST /api/v1/optimize` | Dynamically generate cut patterns from scratch |
| `POST /api/v1/infer-layers` | Infer layer counts for pre-existing CAD marker layouts |
| `GET /health` | Service liveness check |

---

## Authentication

Every request to `/api/v1/*` endpoints must include an API key header.

| Header | Type | Required | Description |
|---|---|---|---|
| `X-API-KEY` | string | Yes | Secret key configured via the `API_KEY` environment variable |

**Missing key → 403 Forbidden**  
**Wrong key → 401 Unauthorized**

```http
X-API-KEY: your_api_key_here
```

---

## Supported Sizes

The solver works with Brazilian garment sizing. All size fields in request and response bodies use these codes:

| Code | Size |
|---|---|
| `P` | Pequeno (Small) |
| `M` | Médio (Medium) |
| `G` | Grande (Large) |
| `GG` | Extra Grande (XL) |
| `G1` | G1 (2XL) |
| `G2` | G2 (3XL) |
| `G3` | G3 (4XL) |

The solver may apply **downgrades** — cutting a larger-size pattern to fulfill a smaller size demand — in a strict one-step cascade: `G3 → G2 → G1 → GG → G → M → P`.

---

## Endpoints

---

### `POST /api/v1/optimize`

Runs the full CP-SAT optimization. The solver chooses how many distinct marker layouts to create (up to `MAX_PATTERNS`), how many fabric layers to spread per marker, and whether any downgrades are needed, minimizing a combined objective of fabric waste, layer time, and pattern count.

**Tag:** Dynamic

#### Request Body

```json
{
  "demand_data": {
    "<colorway_key>": {
      "<size_code>": <quantity>
    }
  },
  "table_length_cm": 800,
  "fabric_width_cm": 180,
  "nesting_efficiency": 0.85,
  "cost_per_size": { "<size_code>": <cost_per_unit> },
  "area_per_size_cm2": { "<size_code>": <area_in_cm2> }
}
```

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| `demand_data` | object | Yes | — | Maps a colorway identifier to a dictionary of size → quantity pairs. The colorway key is a free-form string (e.g. `"2020/186"`). |
| `table_length_cm` | integer | Yes | `> 0` | Physical length of the cutting table in centimetres. |
| `fabric_width_cm` | integer | Yes | `> 0` | Width of the fabric roll in centimetres. |
| `nesting_efficiency` | float | No | `(0, 1]`, default `0.85` | Fraction of table area effectively usable after nesting (dead zones, seams). |
| `cost_per_size` | object | No | — | Override the default cost-per-unit per size, used in the waste objective. Defaults: `P=10, M=12, G=14, GG=16, G1=18, G2=20, G3=25`. |
| `area_per_size_cm2` | object | No | — | Override the default garment area per size in cm². Defaults: `P=12000, M=13500, G=15000, GG=16500, G1=18000, G2=19500, G3=21000`. |

#### Example Request

```http
POST /api/v1/optimize
Content-Type: application/json
X-API-KEY: your_api_key_here

{
  "demand_data": {
    "2020/186": { "P": 5, "M": 5, "G": 26, "GG": 18 },
    "2020/187": { "M": 10, "G": 10, "GG": 10 }
  },
  "table_length_cm": 800,
  "fabric_width_cm": 180,
  "nesting_efficiency": 0.85
}
```

#### Example Response

```json
{
  "status": "OPTIMAL",
  "solve_time_ms": 843.12,
  "total_financial_waste": 56.0,
  "markers": [
    {
      "marker_id": "MKR-001",
      "layout": { "P": 1.0, "M": 1.0, "G": 2.0, "GG": 1.0 },
      "spreading_layers": 18,
      "table_length_used_cm": 312.5,
      "utilization_pct": 91.3
    },
    {
      "marker_id": "MKR-002",
      "layout": { "G": 1.0, "GG": 1.0 },
      "spreading_layers": 10,
      "table_length_used_cm": 164.7,
      "utilization_pct": 88.0
    }
  ]
}
```

---

### `POST /api/v1/infer-layers`

Given a fixed set of pre-existing CAD marker layouts, the solver finds the minimum number of layers to spread each marker to satisfy all demand. Unlike `/optimize`, the layouts themselves are not changed — only the spreading quantities are decided.

**Tag:** Inference

#### Request Body

```json
{
  "demand_data": {
    "<colorway_key>": {
      "<size_code>": <quantity>
    }
  },
  "input_markers": [
    { "<size_code>": <pieces_per_layer> }
  ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `demand_data` | object | Yes | Same structure as `/optimize`. Maps colorway → size → quantity. |
| `input_markers` | array of objects | Yes | Each object represents one existing CAD marker. Keys are size codes; values are the number of pieces of that size that appear in one layer of the marker. Fractional values (e.g. `0.5`) are supported for half-markers (the solver will automatically enforce even layer counts for those). |

#### Example Request

```http
POST /api/v1/infer-layers
Content-Type: application/json
X-API-KEY: your_api_key_here

{
  "demand_data": {
    "2020/186": { "P": 10, "M": 10 }
  },
  "input_markers": [
    { "P": 1.0, "M": 1.0 },
    { "P": 2.0 }
  ]
}
```

#### Example Response

```json
{
  "status": "OPTIMAL",
  "solve_time_ms": 112.44,
  "total_financial_waste": 0.0,
  "markers": [
    {
      "marker_id": "CAD-MKR-001",
      "layout": { "P": 1.0, "M": 1.0 },
      "spreading_layers": 10,
      "table_length_used_cm": 0.0,
      "utilization_pct": 0.0
    }
  ]
}
```

> **Note:** `table_length_used_cm` and `utilization_pct` are always `0.0` for infer-layers responses because table dimensions are not part of the inference input.

---

### `GET /health`

Liveness check. Returns immediately without authentication.

**Tag:** System

#### Example Response

```json
{
  "status": "healthy",
  "engine": "OR-Tools CP-SAT"
}
```

---

## Response Schema

All `/api/v1/*` endpoints return an `OptimizationResponse` on success.

### `OptimizationResponse`

| Field | Type | Description |
|---|---|---|
| `status` | string | Solver exit status. `"OPTIMAL"` means a proven best solution; `"FEASIBLE"` means a valid (but possibly not globally optimal) solution was found within the time limit. |
| `solve_time_ms` | float | Total wall-clock time for the request in milliseconds (includes Python overhead, not just solver time). |
| `total_financial_waste` | float | Estimated cost of surplus garments produced beyond demand, in the same units as `cost_per_size`. |
| `markers` | array of `MarkerResult` | The ordered list of markers to cut. Markers are sorted from highest to lowest total piece count by the solver. |

### `MarkerResult`

| Field | Type | Description |
|---|---|---|
| `marker_id` | string | Auto-generated identifier. Format: `MKR-NNN` for `/optimize`, `CAD-MKR-NNN` for `/infer-layers`. |
| `layout` | object | Maps size code → pieces per layer for this marker. Only sizes with at least one piece are included. |
| `spreading_layers` | integer | Total number of fabric layers to spread for this marker across all colorways. |
| `table_length_used_cm` | float | Estimated table length consumed by this marker in centimetres (`/optimize` only). |
| `utilization_pct` | float | Percentage of the usable table area consumed by this marker (`/optimize` only). |

---

## Error Responses

| HTTP Status | Condition |
|---|---|
| `401 Unauthorized` | `X-API-KEY` header present but incorrect |
| `403 Forbidden` | `X-API-KEY` header missing |
| `422 Unprocessable Entity` | Request body fails validation **or** the solver could not find a feasible solution for the given demand |
| `500 Internal Server Error` | Unexpected server-side error |

All error responses follow FastAPI's default error envelope:

```json
{
  "detail": "human-readable error description"
}
```

---

## Environment Variables

The service is fully configured through environment variables (or a `.env` file at the project root).

| Variable | Default | Description |
|---|---|---|
| `API_KEY` | `super_secret_dev_key_change_in_production` | Secret used to authenticate incoming requests. **Change before deploying.** |
| `ALLOWED_CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated list of origins allowed by the CORS middleware. |
| `MAX_PATTERNS` | `3` | Maximum number of distinct marker layouts the solver may create per request. |
| `MAX_PLY_LIMIT` | `100` | Maximum layers that can be spread on the cutting table per colorway per marker. |
| `SOLVER_TIME_LIMIT_SECONDS` | `30.0` | Hard wall-clock limit for the CP-SAT solver. Requests that hit this limit return `"FEASIBLE"` instead of `"OPTIMAL"` if a valid solution was found, or a 422 if not. |

---

## Running with Docker

### Build and start

```bash
# Copy the environment template and fill in your values
cp .env.example .env

# Build the image and start the container
docker compose up --build
```

The service will be available at `http://localhost:8000`.

### Stop

```bash
docker compose down
```

### Rebuild after code changes

```bash
docker compose up --build --force-recreate
```

### Scale workers

Set `WORKERS` in your `.env` or override at runtime:

```bash
WORKERS=4 docker compose up
```

---

## Running Locally (without Docker)

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

---

## Interactive API Explorer

When the service is running, FastAPI automatically serves a Swagger UI at:

```
http://localhost:8000/docs
```

And a ReDoc interface at:

```
http://localhost:8000/redoc
```

---

## Solver Notes

- The CP-SAT solver works with integer arithmetic internally. Piece counts in `layout` may be fractional (`0.5`) when a marker contains a half-piece — i.e., two adjacent layers together yield one complete garment of that size.
- The solver minimizes a weighted sum of: **financial waste** (surplus × cost) + **total layers spread** × 5 + **number of patterns used** × 200 + **downgrade count** × 15. This means the solver strongly prefers fewer patterns over fewer layers when trade-offs arise.
- If the solver returns `"FEASIBLE"` instead of `"OPTIMAL"`, the solution is valid and safe to use in production, but a better solution may exist. Consider increasing `SOLVER_TIME_LIMIT_SECONDS` if optimality is required.
- The `/infer-layers` endpoint has a fixed 10-second solver time limit regardless of configuration, since the search space is much smaller (layouts are fixed).
