# HaulTrackr Backend

HaulTrackr is a full-stack application designed to help truck drivers plan routes and manage Electronic Logging Device (ELD) logs. The system takes into account Hours of Service (HOS) regulations, fuel stops, and rest requirements to generate optimal routes and compliant log sheets.

![Python Version](https://img.shields.io/badge/python-3.13-blue)
![Django Version](https://img.shields.io/badge/django-5.1.7-green)

## Table of Contents

- [System Architecture](#system-architecture)
- [Features](#features)
- [Technical Stack](#technical-stack)
- [Core Components](#core-components)
- [Data Models](#data-models)
- [API Endpoints](#api-endpoints)
- [API Documentation (Swagger)](#api-documentation-swagger)
- [Authentication](#authentication)
- [Setup Instructions](#setup-instructions)
- [Configuration](#configuration)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## System Architecture

```mermaid
graph TB
    subgraph Frontend["React Frontend"]
        UI["User Interface"]
        MapView["Map View Component"]
        LogView["Log View Component"]
        TripForm["Trip Form Component"]
    end

    subgraph Backend["Django Backend"]
        subgraph APIs["External APIs"]
            ORS["OpenRouteService API"]
            POI["Points of Interest API"]
        end

        subgraph Services["Core Services"]
            RS["Routing Service"]
            SP["Stop Planner"]
            LG["Log Generator"]
            VG["Visual Grid Generator"]
        end

        subgraph Models["Data Models"]
            Trip["Trip Model"]
            Log["LogSheet Model"]
            Stop["RestStop Model"]
            Status["DutyStatus Model"]
        end

        subgraph API["Django REST API"]
            TP["Trip Planning Endpoints"]
            LP["Log Processing Endpoints"]
            VP["Visual Processing Endpoints"]
        end
    end

    subgraph Storage["Data Storage"]
        DB[(Database)]
        Cache[(Cache)]
    end

    UI --> TripForm
    UI --> MapView
    UI --> LogView
    TripForm --> TP
    TP --> RS
    RS --> ORS
    RS --> SP
    SP --> POI
    SP --> Stop
    TP --> LG
    LG --> Log
    LG --> Status
    LP --> VG
    VG --> Cache
    Trip --> DB
    Log --> DB
    Stop --> DB
    Status --> DB
```

## Features

- Route planning with OpenRouteService API integration
- Automatic rest stop planning based on HOS regulations
- Fuel stop calculation at 1000-mile intervals
- ELD log generation and visualization
- Multi-day trip support
- Real-time status updates

## Technical Stack

### Backend (Django)

- Django REST Framework for API endpoints
- SQLite database (can be scaled to PostgreSQL)
- Redis for caching (optional)
- OpenRouteService API for route calculations
- Custom services for:
  - Route planning
  - Stop scheduling
  - Log generation
  - Visual grid creation
- **drf-yasg** for Swagger/OpenAPI documentation
- **SimpleJWT** for JWT authentication
- **django-cors-headers** for CORS

### Frontend (React)

- React for UI components
- Map visualization
- Log sheet display
- Trip planning interface

## Core Components

### 1. Route Planner

- Handles trip creation and management
- Calculates optimal routes
- Integrates with external mapping services
- Manages location data

### 2. Stop Planner

- Calculates required rest stops
- Plans fuel stops
- Optimizes stop locations
- Handles time management

### 3. ELD Logger

- Generates electronic logging device sheets
- Tracks duty status changes
- Ensures HOS compliance
- Creates visual representations

## Data Models

### Trip Model

```python
class Trip:
    - current_location
    - pickup_location
    - dropoff_location
    - current_cycle_hours
    - created_at
```

### RestStop Model

```python
class RestStop:
    - name
    - location
    - coordinates
    - type (REST/FUEL/BOTH)
    - amenities
    - trip (ForeignKey)
    - planned_arrival
    - planned_departure
```

### LogSheet Model

```python
class LogSheet:
    - trip (ForeignKey)
    - date
    - log_data (JSON)
```

## API Endpoints

The API is structured around REST principles. All endpoints are available under the `/api/` prefix.

### Authentication Endpoints

- `POST /users/register/`: Create a new user account.
- `POST /token/`: Obtain a JWT access and refresh token pair.
- `POST /token/refresh/`: Refresh an expired access token using a refresh token.

### Trip Planning

- `GET /trips/`: List all trips for the authenticated user.
- `POST /trips/`: Create a new trip.
- `GET /trips/{id}/`: Retrieve details for a specific trip.
- `POST /trips/{id}/plan/`: Generate a full route plan for a trip, including stops and logs.

### Log Management

- `GET /logs/`: List all log sheets for the authenticated user's trips.
- `GET /logs/{id}/`: Get a specific log sheet.
- `POST /logs/generate_logs/`: Generate log sheets for a given trip.
- `GET /logs/{id}/grid/`: Get a visual grid image for a specific log sheet.

### Duty Status Management

- `GET /duty-status/`: List all duty status changes for the authenticated user.
- `POST /duty-status/`: Create a new duty status change for one of the user's log sheets.
- `GET /duty-status/{id}/`: Get a specific duty status change.

## API Documentation (Swagger)

Interactive API documentation is available:

- **Swagger UI:** [http://localhost:8000/swagger/](http://localhost:8000/swagger/)
- **ReDoc:** [http://localhost:8000/redoc/](http://localhost:8000/redoc/)

You can use these interfaces to explore and test all API endpoints.

## Authentication

This project uses JSON Web Token (JWT) for authentication, powered by [SimpleJWT](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/).

### Registration

Create a new user by sending a `POST` request to the `/api/users/register/` endpoint.

**Request:**

```json
{
  "username": "your_username",
  "password": "your_password",
  "email": "user@example.com"
}
```

### Logging In (Obtaining a Token)

Once registered, you can obtain an access and refresh token pair by sending a `POST` request to the `/api/token/` endpoint.

**Request:**

```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Making Authenticated Requests

Include the `access` token in the `Authorization` header of your requests to protected endpoints, prefixed with "Bearer".

**Example Header:**

```
Authorization: Bearer <your_access_token>
```

## Setup Instructions

1. **Clone the repository:**

   ```bash
   git clone <repo-url>
   cd haultrackrbackend
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables:**

   - Create a `.env` file or set the following variables in your shell:
     - `SECRET_KEY` (if overriding default)
     - `ORS_API_KEY` (for OpenRouteService, if used)
     - Any other API keys or secrets

5. **Apply migrations:**

   ```bash
   python manage.py migrate
   ```

6. **Run the development server:**

   ```bash
   python manage.py runserver
   ```

7. **Access the API and documentation:**
   - API root: [http://localhost:8000/api/](http://localhost:8000/api/)
   - Swagger: [http://localhost:8000/swagger/](http://localhost:8000/swagger/)
   - ReDoc: [http://localhost:8000/redoc/](http://localhost:8000/redoc/)

## Configuration

- **CORS:**  
  The backend is configured to allow requests from the React frontend (localhost:5173 and production domain).  
  Update `CORS_ALLOWED_ORIGINS` in `settings.py` as needed.
- **Database:**  
  Uses SQLite by default. To use PostgreSQL, update the `DATABASES` setting in `settings.py`:
  ```python
  DATABASES = {
      "default": {
          "ENGINE": "django.db.backends.postgresql",
          "NAME": "<your-db-name>",
          "USER": "<your-db-user>",
          "PASSWORD": "<your-db-password>",
          "HOST": "localhost",
          "PORT": "5432",
      }
  }
  ```

## Testing

To run the test suite:

```bash
python manage.py test
```

Add and maintain tests in the `tests.py` files within each app.

## Contributing

Contributions are welcome! Please open issues or submit pull requests.

- Fork the repo and create your branch from `main`.
- Ensure code passes all tests.
- Follow PEP8 and Django best practices.

## License

This project is licensed under the MIT License. See the [LICENSE](https://opensource.org/license/mit) for details.
