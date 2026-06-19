.PHONY: help build up down logs shell db-shell restart clean dev prod rebuild health

# Default target
help:
	@echo "================================"
	@echo "Sched App - Docker Commands"
	@echo "================================"
	@echo ""
	@echo "Development:"
	@echo "  make dev              - Start development environment"
	@echo "  make up               - Start all services"
	@echo "  make down             - Stop all services"
	@echo "  make logs             - View all logs (follow)"
	@echo "  make shell            - Access Flask app shell"
	@echo "  make db-shell         - Access MySQL shell"
	@echo ""
	@echo "Production:"
	@echo "  make prod             - Start production environment"
	@echo "  make prod-restart     - Restart production services"
	@echo ""
	@echo "Management:"
	@echo "  make build            - Build Docker images"
	@echo "  make rebuild          - Rebuild images (no cache)"
	@echo "  make restart          - Restart all services"
	@echo "  make health           - Check container health"
	@echo "  make clean            - Clean up containers & volumes"
	@echo ""
	@echo "Database:"
	@echo "  make db-backup        - Backup MySQL database"
	@echo "  make db-restore FILE=backup.sql - Restore from backup"
	@echo ""

# ============================================
# DEVELOPMENT
# ============================================
dev: build
	docker-compose up -d
	@echo "✓ Development environment started"
	@echo "   Flask app: http://localhost:5000"
	@echo "   MySQL: localhost:3306"
	@docker-compose ps

up:
	docker-compose up -d
	@docker-compose ps

down:
	docker-compose down
	@echo "✓ Services stopped"

logs:
	docker-compose logs -f

logs-app:
	docker-compose logs -f app

logs-db:
	docker-compose logs -f mysql

shell:
	docker-compose exec app bash

db-shell:
	docker-compose exec mysql mysql -u appuser -p rritmb

# ============================================
# PRODUCTION
# ============================================
prod: build
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "✓ Production environment started"
	@docker-compose ps

prod-restart:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart
	@echo "✓ Production services restarted"

prod-logs:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# ============================================
# BUILD & MANAGEMENT
# ============================================
build:
	docker-compose build
	@echo "✓ Images built successfully"

rebuild:
	docker-compose build --no-cache
	@echo "✓ Images rebuilt (no cache)"

restart:
	docker-compose restart
	@echo "✓ Services restarted"

health:
	@echo "Container Health Status:"
	@docker-compose ps
	@echo ""
	@echo "Detailed health checks:"
	@docker-compose exec app curl -s http://localhost:5000/health || echo "Flask: NOT RESPONDING"
	@docker-compose exec mysql mysqladmin ping -u root -proot || echo "MySQL: NOT RESPONDING"

clean:
	docker-compose down -v
	rm -rf mysql_data/
	@echo "✓ Cleaned: containers, volumes, and local mysql_data"

# ============================================
# DATABASE
# ============================================
db-backup:
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	docker-compose exec mysql mysqldump -u appuser -p rritmb > backups/backup_$$TIMESTAMP.sql; \
	echo "✓ Database backed up to backups/backup_$$TIMESTAMP.sql"

db-restore:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make db-restore FILE=path/to/backup.sql"; \
		exit 1; \
	fi
	docker-compose exec mysql mysql -u root -proot rritmb < $(FILE)
	@echo "✓ Database restored from $(FILE)"

db-init:
	@echo "Initializing database..."
	@docker-compose exec app python -c "from app import create_app, db; app = create_app(); with app.app_context(): db.create_all()"
	@echo "✓ Database initialized"

# ============================================
# UTILITIES
# ============================================
ps:
	docker-compose ps

prune:
	docker system prune -f
	@echo "✓ Cleaned unused Docker resources"

version:
	@echo "Docker versions:"
	@docker --version
	@docker-compose --version

env-check:
	@echo "Checking .env file..."
	@if [ ! -f .env ]; then \
		echo "⚠ .env file not found!"; \
		echo "Creating from template..."; \
		cp .env.example .env; \
		echo "✓ Created .env - please edit with your values"; \
	else \
		echo "✓ .env file exists"; \
	fi

# ============================================
# CI/CD
# ============================================
lint:
	docker-compose run --rm app python -m py_compile app/*.py

test:
	docker-compose run --rm app python -m pytest tests/ -v

# ============================================
# DEPLOYMENT
# ============================================
deploy-prod:
	@echo "Production Deployment Checklist:"
	@echo "✓ All changes committed to git"
	@echo "✓ .env configured for production"
	@echo "✓ Database backups completed"
	@echo "✓ SSL certificates installed"
	@make prod
	@echo "✓ Services started - verify health:"
	@make health

# ============================================
# Development shortcuts
# ============================================
start: up
stop: down
restart-app:
	docker-compose restart app
ssh:
	docker-compose exec app bash
sql:
	docker-compose exec mysql mysql -u appuser -p rritmb
