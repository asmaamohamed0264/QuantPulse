# QuantPulse Automation Commands

# Default recipe lists all available commands
default:
    @just --list

# Install development dependencies
install:
    pip install -r requirements.txt
    pip install -e .

# Format code with black
format:
    black app/ tests/
    
# Lint code with flake8
lint:
    flake8 app/ tests/

# Run type checking
typecheck:
    mypy app/

# Run tests
test:
    pytest tests/ -v --cov=app

# Run tests with coverage report
test-cov:
    pytest tests/ -v --cov=app --cov-report=html --cov-report=term

# Build Docker image
build:
    docker build -t quantpulse:latest .

# Run locally with Docker
run:
    docker run -p 8000:8000 --env-file .env quantpulse:latest

# Run locally without Docker (development)
dev:
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Start services with docker-compose (development)
up:
    docker-compose up -d

# Stop docker-compose services
down:
    docker-compose down

# View logs
logs:
    docker-compose logs -f app

# Initialize database
init-db:
    python -m alembic upgrade head

# Create new migration
migrate message:
    python -m alembic revision --autogenerate -m "{{message}}"

# Apply migrations
upgrade:
    python -m alembic upgrade head

# Clean up Docker images and containers
clean:
    docker system prune -f
    docker image prune -f

# Deploy to production (customize for your VPS)
deploy:
    @echo "Building production image..."
    just build
    @echo "Pushing to registry..."
    # Add your deployment commands here
    
# Run security checks
security:
    safety check
    bandit -r app/

# Generate API documentation
docs:
    @echo "API docs available at: http://localhost:8000/docs"
    @echo "ReDoc available at: http://localhost:8000/redoc"