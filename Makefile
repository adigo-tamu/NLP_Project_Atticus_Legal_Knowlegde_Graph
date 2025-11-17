.PHONY: help install setup test clean lint format run-api docs

help:
	@echo "Project Atticus - Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make setup        - Set up development environment"
	@echo "  make setup-db     - Initialize Neo4j database schema"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make run-api      - Run API server"
	@echo "  make docs         - Build documentation"
	@echo "  make clean        - Clean generated files"

install:
	pip install -r requirements.txt
	pip install -e .

setup:
	@echo "Setting up Project Atticus development environment..."
	@cp .env.example .env
	@echo "Created .env file - please update with your API keys"
	@mkdir -p data/raw data/processed data/graphs logs models
	@echo "Created data directories"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env file with your API keys"
	@echo "2. Install Neo4j and start the database"
	@echo "3. Run 'make setup-db' to initialize the database schema"
	@echo "4. Download CUAD dataset: python scripts/download_cuad.py"

setup-db:
	python scripts/setup_database.py

test:
	pytest tests/ -v --cov=atticus --cov-report=html --cov-report=term

lint:
	ruff check src/
	mypy src/

format:
	black src/ tests/
	ruff check --fix src/

run-api:
	uvicorn atticus.api.main:app --reload --host 0.0.0.0 --port 8000

docs:
	mkdocs build

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ htmlcov/ .coverage .pytest_cache/ .mypy_cache/ .ruff_cache/

# Docker commands
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f
