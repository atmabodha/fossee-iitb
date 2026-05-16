# Adaptive Sequencing Prototype

This repository contains the backend and database architecture for the Adaptive Sequencing system. It utilizes FastAPI, SQLAlchemy, and a PostgreSQL database.

## 🚀 Quick Start for Developers

Follow these steps to set up the system on your local machine.

### Prerequisites
- [Docker & Docker Compose](https://docs.docker.com/get-docker/) installed.
- [Python 3.10+](https://www.python.org/downloads/) installed.

### 1. Start the Database
The project includes a `docker-compose.yml` to instantly spin up a local PostgreSQL container.
```bash
docker-compose up -d
```
*Note: The database runs on `localhost:5432` with the `postgres:postgres` credentials.*

### 2. Set Up the Python Environment
Create a virtual environment, activate it, and install the required dependencies.
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r api_architecture/requirements.txt
```

### 3. Initialize the Database Schema
Once your Docker container is running, execute the initialization script. This uses SQLAlchemy to construct the 1NF strictly normalized schema (tables, foreign keys) mapped in `api_architecture/database/models.py`:
```bash
python init_db.py
```
*Note: Running `init_db.py` will drop and recreate all tables.*

### 4. Running the Development Server (FastAPI)
The central entry point is currently mocked or can be launched via standard Uvicorn commands:
```bash
uvicorn api_architecture.main:app --reload
```

---

## 📂 Architecture Overview

The system is separated cleanly into independent modules for testability and scaling:
- **`api_architecture/database/models.py`**: PostgreSQL Schema mapped strictly to 1NF tables. 
- **`api_architecture/services/storage.py`**: SQLAlchemy interactions via `AsyncSession`, abstracting all joins and database logic from the core engine.
- **`api_architecture/engine/sequencing_engine.py`**: The adaptive routing algorithm. Completely agnostic to the database, receiving pure Python datasets to determine a student's next question.
- **`api_architecture/models/`**: Pydantic validation boundaries describing `Question` properties and `StudentState`.

## 🤝 Contributing
When working on new features:
1. All changes to database schemas must be verified in `models.py` and reflected in `init_db.py`.
2. Do not mix database session queries directly inside logic layers (e.g. `engine/`). Always use repository wrappers like `AsyncQuestionFetcher` in `storage.py`.
