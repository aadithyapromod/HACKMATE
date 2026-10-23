.PHONY: help dev check build clean backend frontend runner

help:
	@echo "HackMate Development Commands:"
	@echo "  make dev       - Start local development services"
	@echo "  make check     - Run code verification across frontend, backend, runner"
	@echo "  make build     - Build Docker containers"
	@echo "  make clean     - Remove caches and temporary build artifacts"

dev:
	docker compose up --build

check:
	@echo "Running verification checks..."
	@powershell -ExecutionPolicy Bypass -File ./scripts/check.ps1 || ./scripts/check.sh

build:
	docker compose build

clean:
	rm -rf frontend/.next frontend/node_modules backend/__pycache__ generated/*
