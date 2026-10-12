# Fuel Route Optimizer

A Django REST API that calculates driving routes across the United States and recommends cost-effective fuel stops using a dataset of fuel station prices.

Built as a backend engineering assignment for **Spotter**.

## Features

- Calculate driving routes between US locations.
- Return route distance, estimated duration, and GeoJSON geometry.
- Find verified fuel stations near the driving route.
- Recommend fuel stops using a price-aware refueling algorithm.
- Calculate gallons purchased and total additional fuel expenditure.
- Import fuel-price records from a CSV dataset.
- Document the API using Swagger/OpenAPI.
- Run the application with Docker and PostgreSQL.
- Validate functionality using automated tests.

## Tech Stack

- Python 3.13
- Django and Django REST Framework
- PostgreSQL 17
- OpenRouteService for routing and geocoding
- Docker and Docker Compose
- uv for dependency management
- pytest for automated testing
- Ruff for linting and formatting
- drf-spectacular for OpenAPI documentation

## How It Works

The API receives a starting location and a destination.

1. **Geocoding:** Resolve the starting and destination locations to geographic coordinates.
2. **Routing:** Request a driving route from the routing provider.
3. **Station matching:** Find verified fuel stations within a geographic corridor around the route.
4. **Fuel optimization:** Calculate recommended refueling stops using station prices, vehicle range, and fuel consumption.
5. **Response:** Return the driving route and fuel purchase recommendations.

Station matching and fuel optimization are performed locally after retrieving the driving route, reducing the need for additional routing API calls.

## Vehicle Assumptions

| Parameter | Value |
|---|---|
| Maximum range | 500 miles |
| Fuel efficiency | 10 miles per gallon |
| Tank capacity | 50 gallons |
| Initial fuel | Full tank |
| Fuel prices | Provided CSV dataset |

The total fuel cost represents **additional fuel purchased during the journey**, excluding the fuel already present in the vehicle at departure.

## API Endpoint

### `POST /api/v1/routes/optimize/`

**Request**

```json
{
  "start": "New York, NY",
  "finish": "Chicago, IL"
}
```

**Example response (abridged)**

```json
{
  "start": "New York, NY",
  "finish": "Chicago, IL",
  "distance_miles": 800.43,
  "duration_minutes": 839.11,
  "geometry": {
    "type": "LineString",
    "coordinates": []
  },
  "fuel": {
    "total_cost": 101.78,
    "total_gallons_purchased": 30.043,
    "fuel_remaining_gallons": 0.0,
    "stops": [
      {
        "station_id": 15842,
        "name": "SHEETZ #769",
        "latitude": 41.007944,
        "longitude": -76.489601,
        "distance_along_route": 157.3,
        "price_per_gallon": 3.329,
        "gallons_purchased": 15.73,
        "fuel_cost": 52.36517
      },
      {
        "station_id": 10756,
        "name": "PILOT TRAVEL CENTERS #3",
        "latitude": 41.1287428,
        "longitude": -80.7693587,
        "distance_along_route": 402.8,
        "price_per_gallon": 3.45233333,
        "gallons_purchased": 14.313,
        "fuel_cost": 49.41324695229
      }
    ]
  }
}
```

The actual `geometry.coordinates` array contains the route's geographic points. It is omitted from this example for readability.

### HTTP Responses

| Status | Description |
|---|---|
| 200 | Route successfully optimized |
| 400 | Invalid request or unresolved location |
| 422 | Insufficient verified fuel-station coverage |
| 502 | Routing provider unavailable |

## Fuel Optimization Algorithm

The optimizer uses a greedy price-aware refueling strategy for a fixed route.

At each potential stop, the algorithm evaluates reachable fuel stations:

- If a cheaper station is reachable, purchase enough fuel to reach it.
- Otherwise, fill the tank as needed, without purchasing more fuel than the remaining journey requires.
- Continue until the destination is reached.

The algorithm respects the vehicle's maximum 500-mile range and 10 MPG consumption rate.

Its results depend on which verified stations are available along the route. It does not currently calculate actual road detours to individual fuel stations.

## Getting Started

### Requirements

- Docker
- Docker Compose
- An OpenRouteService API key

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd fuel-route-optimizer
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Configure the PostgreSQL connection, Django settings, and routing provider API key using the variable names provided in `.env.example`.

Keep the real `.env` file out of version control.

### 3. Start Docker

```bash
docker compose up --build -d
```

### 4. Apply migrations

```bash
docker compose exec web uv run python manage.py migrate
```

### 5. Import fuel station data

The provided CSV dataset contains 8,151 fuel-station records, including fuel prices and location descriptions.

Import it using the project's CSV import management command.

**Before submission:** Add the exact command used by this repository, including the CSV path and any required options.

### 6. Prepare verified station coordinates

The source dataset does not provide reliable geographic coordinates for every station.

Stations must have verified coordinates before they are eligible for route matching.

**Before submission:** Document how to load the verified stations used in the demonstration. A fresh database containing only the fuel-price CSV will not necessarily reproduce the New York → Chicago example.

### 7. Start using the API

```bash
curl -X POST http://localhost:8000/api/v1/routes/optimize/ \
  -H "Content-Type: application/json" \
  -d '{
    "start": "New York, NY",
    "finish": "Chicago, IL"
  }'
```

Swagger/OpenAPI documentation is available through the URLs configured in the Django project.

## Testing

All commands run inside Docker.

**Django checks**

```bash
docker compose exec web uv run python manage.py check
```

**Automated tests**

```bash
docker compose exec web uv run pytest
```

**Ruff linting**

```bash
docker compose exec web uv run ruff check .
```

**Ruff formatting validation**

```bash
docker compose exec web uv run ruff format --check .
```

**OpenAPI validation**

```bash
docker compose exec web uv run python manage.py spectacular --validate
```

## Architecture

The application separates responsibilities into dedicated services:

| Component | Responsibility |
|---|---|
| RoutePlanner | Orchestrates the optimization process |
| GeocodingService | Resolves location descriptions into coordinates |
| RoutingService | Retrieves driving route information |
| StationMatcher | Matches verified stations to route geometry |
| FuelOptimizer | Calculates refueling stops and costs |

This separation allows routing, station matching, and fuel optimization to be tested independently.

## Limitations

- Fuel optimization assumes a full starting tank.
- Fuel prices are based on the supplied dataset and are not real-time prices.
- Geographic distance from a station to the route does not necessarily equal the actual driving detour.
- Station coverage depends on available verified coordinates.
- Some US routes may return HTTP 422 until additional station locations are verified.
- The optimizer minimizes fuel purchase cost among available matched stations under its fixed-route assumptions, not necessarily across every possible driving route.

## Future Improvements

- Expand verified fuel-station coverage nationwide.
- Automate reliable coordinate verification.
- Account for real driving detours and station access.
- Support configurable vehicle range, MPG, and initial fuel.
- Optimize multiple alternative driving routes.
- Add persistent route caching to reduce repeated provider requests.

## Demonstration

A short Loom walkthrough demonstrates the API request, route optimization result, code architecture, and automated tests.

**Demo link:** Add Loom URL here.

## License

Add the applicable license information if the project is being distributed under a license.
