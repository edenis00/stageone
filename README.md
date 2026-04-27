# HNG Stage One - Demographic Profile API

## Overview
The **Demographic Profile API** is a FastAPI-based service designed to enrich names with demographic insights. By integrating with external APIs (**Genderize.io**, **Agify.io**, and **Nationalize.io**), it provides estimated gender, age, and nationality probability for a given name. The results are persisted in a PostgreSQL database for historical tracking and efficient retrieval.

This project was developed as part of the HNG Stage One backend task.

## Features
- **Name analysis**: Fetches demographic data (gender, age, country) based on a name.
- **Data Persistence**: Automatically stores profile data in a database.
- **Profile Management**: Full CRUD operations (Create, Read, List, Delete) for name profiles.
- **Advanced Filtering**: Search through analyzed profiles by gender, age group, or country.
- **Error Handling**: Robust validation and error reporting for upstream API failures.

## Tech Stack
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: [PostgreSQL](https://www.postgresql.org/)
- **ORM**: [SQLAlchemy](https://www.sqlalchemy.org/)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **External API Interaction**: [HTTPX](https://www.python-httpx.org/)
- **Validation**: [Pydantic](https://docs.pydantic.dev/)

---

## Installation & Setup

### 1. Clone the repository
```bash
git clone <repository-url>
cd stageone
```

### 2. Set up a Virtual Environment
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install fastapi uvicorn sqlalchemy pydantic-settings httpx uuid6 psycopg2-binary alembic
```

### 4. Environment Configuration
Create a `.env` file in the root directory and populate it with your configuration (refer to `.env.sample`).
```env
DATABASE_URL="postgresql://username:password@localhost:5432/hng_stageone"
GENDERIZE_URL=https://api.genderize.io
AGIFY_URL=https://api.agify.io
NATIONALIZE_URL=https://api.nationalize.io
```

### 5. Database Migrations
Run the migrations to set up the database schema:
```bash
alembic upgrade head
```

---

## Running the Application

Start the development server using Uvicorn:
```bash
uvicorn app.main:app --reload
```
The API will be accessible at `http://localhost:8000`.

---

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/profiles/` | Create a profile for a name (or retrieve if it already exists). |
| `GET` | `/api/profiles/` | List all profiles with optional filters (`gender`, `country_id`, `age_group`). |
| `GET` | `/api/profiles/{id}` | Get a specific profile by its ID. |
| `DELETE` | `/api/profiles/{id}` | Delete a profile by its ID. |

### Request Body (POST `/api/profiles/`)
```json
{
  "name": "Alex"
}
```

### Success Response (POST `/api/profiles/`)
```json
{
  "status": "success",
  "data": {
    "id": "018f203a-...",
    "name": "alex",
    "gender": "male",
    "gender_probability": 0.92,
    "age": 35,
    "age_group": "adult",
    "country_id": "US",
    "country_probability": 0.07,
    "created_at": "2024-05-15T10:00:00Z"
  }
}
```

---

## External Integrations
This API relies on the following third-party services:
- **[Genderize.io](https://genderize.io/)**: Predicts gender based on a name.
- **[Agify.io](https://agify.io/)**: Estimates age based on a name.
- **[Nationalize.io](https://nationalize.io/)**: Predicts nationality based on a name.

---

## License
MIT
