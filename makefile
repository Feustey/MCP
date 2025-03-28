PYTHON=python3
VENV=venv
PIP=$(VENV)/bin/pip

.PHONY: clean venv install upgrade-pip run

# Crée l'environnement virtuel
venv:
	$(PYTHON) -m venv $(VENV)

# Upgrade pip dans le venv
upgrade-pip:
	$(VENV)/bin/python -m pip install --upgrade pip

# Installe les dépendances
install: venv upgrade-pip
	$(PIP) install -r requirements.txt

# Nettoie l'environnement virtuel
clean:
	rm -rf $(VENV)

# Lance l'application
run:
	source $(VENV)/bin/activate && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
