.PHONY: setup run-backend run-frontend e2e lint-backend lint-frontend test-backend

setup:
	cd backend && (command -v uv >/dev/null 2>&1 && uv venv && uv pip install -r requirements.txt || (python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt))
	cd frontend && npm install

run-backend:
	cd backend && (. .venv/bin/activate 2>/dev/null || true) && uvicorn app.main:app --reload --port 8000

run-frontend:
	cd frontend && npm run dev

lint-frontend:
	cd frontend && npm run lint

lint-backend:
	cd backend && (. .venv/bin/activate 2>/dev/null || true) && ruff check .

test-backend:
	cd backend && (. .venv/bin/activate 2>/dev/null || true) && pytest

e2e:
	$(MAKE) -j2 run-backend run-frontend
