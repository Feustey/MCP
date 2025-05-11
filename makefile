.PHONY: setup run-docker stop-docker test lint shell clean simulation grafana help optimize-all-profiles optimize-and-report

PYTHON = python3.9
PIP = $(PYTHON) -m pip

help:
	@echo "Commandes disponibles:"
	@echo "  setup         - Installe les dépendances et prépare l'environnement"
	@echo "  run-docker    - Démarre les services via Docker Compose"
	@echo "  stop-docker   - Arrête les services Docker"
	@echo "  test          - Lance les tests unitaires"
	@echo "  test-int      - Lance les tests d'intégration"
	@echo "  lint          - Vérifie le style du code"
	@echo "  shell         - Démarre un shell dans le conteneur API"
	@echo "  clean         - Nettoie les fichiers temporaires"
	@echo "  simulation    - Lance le simulateur de nœud"
	@echo "  grafana       - Ouvre Grafana dans le navigateur"
	@echo "  optimize-all-profiles - Exécute l'optimisation sur tous les profils simulés"
	@echo "  optimize-and-report - Générer le rapport d'optimisation"

setup:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	mkdir -p data/raw data/metrics data/reports data/actions data/rollback_snapshots
	mkdir -p rag/RAG_assets/nodes/simulations
	mkdir -p logs
	mkdir -p grafana/dashboards

run-docker:
	docker-compose up -d

stop-docker:
	docker-compose down

test:
	$(PYTHON) -m pytest tests/unit

test-int:
	$(PYTHON) -m pytest tests/integration

lint:
	flake8 src rag app
	black --check src rag app

shell:
	docker-compose exec mcp-api /bin/bash

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete

simulation:
	$(PYTHON) src/tools/node_simulator.py

grafana:
	@echo "Ouverture de Grafana dans le navigateur..."
	@open http://localhost:3000

optimize-all-profiles:
	@echo "Exécution de l'optimisation sur tous les profils simulés..."
	$(PYTHON) src/tools/node_simulator.py
	@for profile in normal saturated inactive abused star unstable aggressive_fees routing_hub; do \
		echo "=== Optimisation du profil: $$profile ==="; \
		FORCE_PROFILE=$$profile $(PYTHON) src/tools/optimize_and_execute.py --node-id=test_node_$$profile --dry-run --simulate --force; \
		echo ""; \
	done
	@echo "Optimisation terminée pour tous les profils."

optimize-and-report: optimize-all-profiles
	@echo "Génération du rapport d'optimisation..."
	$(PYTHON) src/tools/generate_optimization_report.py --format md
	@echo "Rapport généré avec succès!"
