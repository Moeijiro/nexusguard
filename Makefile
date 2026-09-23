# Developer shortcuts. The README lists the raw commands too.

BACKEND := backend
VENV := $(BACKEND)/.venv/bin

.PHONY: help install api bot web seed test clean

help:
	@echo "make install  install backend + dashboard dependencies"
	@echo "make api      run the API (and the demo simulator) on :8000"
	@echo "make bot      run the Discord bot (needs DISCORD_BOT_TOKEN)"
	@echo "make web      run the dashboard on :3000"
	@echo "make seed     rebuild the simulated demo guilds"
	@echo "make test     run the backend test suite"

install:
	python3 -m venv $(BACKEND)/.venv
	$(VENV)/pip install -r $(BACKEND)/requirements-dev.txt
	cd frontend && npm install

api:
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --port 8000

bot:
	cd $(BACKEND) && .venv/bin/python -m app.bot

web:
	cd frontend && npm run dev

seed:
	cd $(BACKEND) && .venv/bin/python -m app.demo.seed --reset

test:
	cd $(BACKEND) && .venv/bin/python -m pytest

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -f $(BACKEND)/*.db $(BACKEND)/*.db-wal $(BACKEND)/*.db-shm
