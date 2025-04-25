PYTHON=python3
VENV=venv
PIP=$(VENV)/bin/pip

.PHONY: clean venv install upgrade-pip run test test-verbose test-coverage test-all

# Crée l'environnement virtuel
venv:
	$(PYTHON) -m venv $(VENV)

# Upgrade pip dans le venv
upgrade-pip:
	$(VENV)/bin/python -m pip install --upgrade pip

# Installe les dépendances
install: venv upgrade-pip
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

# Nettoie l'environnement virtuel
clean:
	rm -rf $(VENV)

# Lance l'application
run:
	source $(VENV)/bin/activate && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Lance les tests unitaires
test:
	source $(VENV)/bin/activate && python -m pytest --asyncio-mode=strict

# Lance les tests unitaires en mode verbeux
test-verbose:
	source $(VENV)/bin/activate && python -m pytest -v --asyncio-mode=strict

# Lance les tests unitaires avec couverture
test-coverage:
	source $(VENV)/bin/activate && python -m pytest --cov=src --cov-report=term --cov-report=html --asyncio-mode=strict

# Lance tous les tests (y compris les tests personnalisés)
test-all:
	source $(VENV)/bin/activate && python run_all_tests.py
