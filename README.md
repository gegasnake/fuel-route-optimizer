# Django Backend Template

A reusable Django backend project template with a preconfigured development, testing, code-quality, documentation, and Continuous Integration environment.

The goal of this template is to provide a clean foundation for starting new Django backend projects without repeatedly configuring the same development infrastructure.

## Tech Stack

- Python 3.13
- Django
- Django REST Framework
- PostgreSQL
- Docker & Docker Compose
- uv
- Ruff
- mypy
- pytest
- pytest-django
- pre-commit
- tox
- MkDocs
- GitHub Actions

## Included Features

### Development

- Dockerized Django development environment
- PostgreSQL database
- Environment-variable-based configuration
- Modular Django settings
- Dependency management with uv
- Reproducible dependencies through `uv.lock`

### Code Quality

- Ruff linting
- Ruff formatting
- mypy static type checking
- pre-commit hooks

### Testing

- pytest
- pytest-django
- Django test database support
- tox automation

### Documentation

- MkDocs documentation
- Architecture documentation
- Development workflow
- Testing documentation
- CI/CD documentation
- API documentation structure

### Continuous Integration

GitHub Actions automatically validates:

- pytest tests
- Ruff linting
- Ruff formatting
- mypy
- Django system checks
- MkDocs documentation

The validation suite is executed through tox.

---

# Getting Started

## 1. Create a Project From the Template

On GitHub, click:

**Use this template → Create a new repository**

Then clone your newly created repository:

```bash
git clone <your-repository-url>
cd <your-project>
```

## 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Update the values in `.env` if necessary.

Example:

```env
SECRET_KEY=change-me
DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

POSTGRES_DB=app_db
POSTGRES_USER=app_user
POSTGRES_PASSWORD=change-me
POSTGRES_HOST=db
POSTGRES_PORT=5432

WEB_PORT=8000
```

Never commit the real `.env` file.

## 3. Build and Start the Project

```bash
docker compose up --build -d
```

Check that the containers are running:

```bash
docker compose ps
```

## 4. Run Database Migrations

```bash
docker compose exec web uv run python manage.py migrate
```

## 5. Run Django System Checks

```bash
docker compose exec web uv run python manage.py check
```

The application should now be available at:

```text
http://localhost:8000
```

or the port configured through `WEB_PORT`.

---

# Development Workflow

All development commands are intended to run inside Docker.

## Create a Django Application

```bash
docker compose exec web uv run python manage.py startapp <app_name>
```

Remember to register the new application in the Django settings when required.

## Create Migrations

```bash
docker compose exec web uv run python manage.py makemigrations
```

## Apply Migrations

```bash
docker compose exec web uv run python manage.py migrate
```

## Create a Superuser

```bash
docker compose exec web uv run python manage.py createsuperuser
```

## Django Shell

```bash
docker compose exec web uv run python manage.py shell
```

---

# Testing

Run pytest:

```bash
docker compose exec web uv run pytest
```

Run the complete validation suite:

```bash
docker compose exec web uv run tox
```

Individual tox environments can also be executed separately.

Tests:

```bash
docker compose exec web uv run tox run -e tests
```

Linting:

```bash
docker compose exec web uv run tox run -e lint
```

Formatting validation:

```bash
docker compose exec web uv run tox run -e format
```

Static type checking:

```bash
docker compose exec web uv run tox run -e type
```

Django system checks:

```bash
docker compose exec web uv run tox run -e django
```

Documentation validation:

```bash
docker compose exec web uv run tox run -e docs
```

---

# Code Quality

## Ruff

Check the project:

```bash
docker compose exec web uv run ruff check .
```

Automatically fix supported lint violations:

```bash
docker compose exec web uv run ruff check . --fix
```

Format the project:

```bash
docker compose exec web uv run ruff format .
```

Check formatting without modifying files:

```bash
docker compose exec web uv run ruff format --check .
```

## mypy

Run static type checking:

```bash
docker compose exec web uv run mypy
```

---

# Pre-commit

Pre-commit automatically runs repository hygiene and code-quality checks before commits.

Run all hooks manually:

```bash
docker compose exec web uv run pre-commit run --all-files
```

The configured hooks include:

- Ruff lint
- Ruff formatting
- Trailing whitespace validation
- End-of-file fixing
- YAML validation
- TOML validation
- Large file detection

---

# Documentation

Documentation is built using MkDocs.

Build documentation:

```bash
docker compose exec web uv run mkdocs build --strict
```

Serve documentation:

```bash
docker compose exec web uv run mkdocs serve -a 0.0.0.0:8001
```

Documentation source files are located in:

```text
docs/
```

Generated MkDocs output is written to:

```text
site/
```

The `site/` directory is generated and should not be committed.

---

# Continuous Integration

The project contains a GitHub Actions CI workflow under:

```text
.github/workflows/ci.yml
```

CI runs automatically on configured pushes and pull requests.

The pipeline:

```text
Push / Pull Request
        │
        ▼
   GitHub Actions
        │
        ▼
  Python 3.13 + uv
        │
        ▼
       tox
        │
   ┌────┼────┬─────┬──────┬──────┐
   ▼    ▼    ▼     ▼      ▼      ▼
pytest Ruff Format mypy Django  MkDocs
   │    │    │     │      │      │
   └────┴────┴─────┴──────┴──────┘
        │
        ▼
     CI Passed
```

Any failed validation causes the CI workflow to fail.

---

# Project Structure

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── config/
│   ├── settings/
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── docs/
│   ├── index.md
│   ├── getting-started.md
│   ├── architecture.md
│   ├── development.md
│   ├── testing.md
│   ├── ci-cd.md
│   └── api.md
│
├── tests/
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── mkdocs.yml
├── pyproject.toml
├── tox.toml
├── uv.lock
└── README.md
```

---

# After Creating a Project From This Template

After generating a new repository from this template:

1. Update the project name and metadata in `pyproject.toml`.
2. Update the project title and description in `README.md`.
3. Update the project information in `mkdocs.yml`.
4. Update the documentation under `docs/`.
5. Copy `.env.example` to `.env`.
6. Configure project-specific environment variables.
7. Build the Docker environment.
8. Run database migrations.
9. Run the complete tox validation suite.
10. Start creating project-specific Django applications.

Verify the project before beginning development:

```bash
docker compose exec web uv run tox
```

All validation environments should pass.

---

# Dependency Management

Dependencies are managed using uv.

Synchronize dependencies:

```bash
docker compose exec web uv sync
```

Add a runtime dependency:

```bash
docker compose exec web uv add <package>
```

Add a development dependency:

```bash
docker compose exec web uv add --dev <package>
```

The `uv.lock` file should be committed to Git to provide reproducible dependency installation.

---

# Philosophy

This template provides an opinionated development infrastructure while keeping application business logic minimal.

The template defines **how the project is developed, tested, validated, documented, and integrated**, while individual projects define their own applications, models, APIs, and business rules.