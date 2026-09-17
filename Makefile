.PHONY: help install format format-check lint typecheck test check run

help:
	@echo "Доступные команды:"
	@echo "  make install              Синхронизировать зависимости через uv"
	@echo "  make format               Отформатировать проект через Ruff"
	@echo "  make format-check         Проверить форматирование без изменений"
	@echo "  make lint                 Запустить Ruff lint"
	@echo "  make typecheck            Проверить production source через mypy"
	@echo "  make test                 Запустить pytest"
	@echo "  make check                Запустить полный local quality gate"
	@echo "  make run URL=https://...  Запустить измерение для переданного URL"

install:
	uv sync

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

typecheck:
	uv run mypy src

test:
	uv run pytest

check: format-check lint typecheck test

run:
	$(if $(strip $(URL)),,$(error Не задан URL. Использование: make run URL=https://example.com/large-file))
	uv run internet-speed-meter "$(URL)"
