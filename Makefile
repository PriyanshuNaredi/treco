.PHONY: dev test lint

dev:
	docker compose up --build

backend-dev:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend-dev:
	cd frontend && npm run dev

test:
	cd backend && pytest tests/ -v

lint:
	cd backend && ruff check . && mypy app/

migrate:
	cd backend && alembic upgrade head
