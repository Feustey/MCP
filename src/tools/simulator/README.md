# Simulateur Stochastique de Nœuds Lightning

> Dernière mise à jour: 7 mai 2025

## Vue d'ensemble

Ce simulateur stochastique permet de tester les moteurs de décision pour l'optimisation des nœuds Lightning Network dans des environnements contrôlés et variés. Il utilise des modèles stochastiques pour simuler l'évolution des canaux Lightning en réponse à des changements de politique de frais et autres facteurs environnementaux.

Le simulateur est conçu pour répondre à la question clé : **Le moteur de décision améliore-t-il objectivement les métriques mesurables du nœud au fil du temps ?**

## Fonctionnalités clés

1. **Simulation stochastique** : Évolution réaliste des canaux avec des variations aléatoires contrôlées
2. **Matrice de scénarios** : Génération combinatoire de scénarios pour tester la robustesse du moteur
3. **Mesures d'impact** : Évaluation objective de l'efficacité des décisions
4. **Comparaison vs baseline** : Mesure les améliorations par rapport à un scénario sans intervention
5. **Métriques normalisées** : Score composite pour évaluer la qualité globale des décisions

## Architecture

Le simulateur est composé de plusieurs modules :

- `stochastic_simulator.py` : Classes principales d'environnement et d'évaluation
- `performance_metrics.py` : Système de métriques et calcul d'impact
- `channel_evolution.py` : Modèle d'évolution stochastique des canaux
- `scenario_matrix.py` : Générateur de scénarios combinatoires
- `simulation_fixtures.py` : Générateur de données historiques et de bruit contrôlé
- `example_usage.py` : Exemple d'utilisation du simulateur

## Métriques

Le simulateur évalue les décisions selon plusieurs métriques clés :

- **Revenue** : Revenu total généré par les frais de routage
- **Capital efficiency** : Efficacité d'utilisation du capital investi
- **HTLC success rate** : Taux de succès des paiements routés
- **Peer retention** : Conservation des pairs
- **Opportunity cost** : Coût d'opportunité des décisions
- **Rebalancing cost** : Coût estimé des rebalancements nécessaires
- **Fee competitiveness** : Compétitivité des frais par rapport au réseau

## Usage

### Exemple simple

```python
from src.tools.simulator import LightningSimEnvironment, DecisionEvaluator
from src.tools.simulator import ScenarioMatrix

# Créer une matrice de scénarios
scenario_matrix = ScenarioMatrix()
scenarios = scenario_matrix.generate_scenario_combinations(sample_size=5)

# Configurer l'environnement
config = {
    "network_size": 20,
    "scenarios": scenarios,
    "simulation_days": 30,
    "noise_level": 0.2,
    "save_results": True
}

# Initialiser la simulation
simulator = LightningSimEnvironment(config)
evaluator = DecisionEvaluator(simulator)

# Évaluer le moteur de décision
results = evaluator.evaluate_decision_engine(your_decision_engine, steps=30)

# Analyser les résultats
print(f"Score qualité: {results['comparison']['decision_quality']:.2f}/10")
print(f"Amélioration des revenus: {results['comparison']['revenue_ratio']:.2f}x")
```

### Création d'un moteur de décision

Pour créer un moteur de décision compatible, implémentez la méthode `evaluate_network()` :

```python
class YourDecisionEngine:
    def evaluate_network(self, network_state):
        """
        Évalue l'état du réseau et prend des décisions
        
        Args:
            network_state: État actuel du réseau et des métriques
            
        Returns:
            Liste de décisions au format:
            [
                {
                    "channel_id": "...",
                    "action": "INCREASE_FEES" | "DECREASE_FEES" | "CLOSE_CHANNEL" | "NO_ACTION",
                    "fee_base_change": 100,  # Facultatif
                    "fee_rate_change": 50,   # Facultatif
                    "reason": "Explication"   # Facultatif
                },
                ...
            ]
        """
        # Votre logique de décision ici
        return decisions
```

## Tests

Les tests unitaires sont disponibles dans `tests/unit/test_stochastic_simulator.py`. Pour les exécuter :

```bash
python -m unittest tests/unit/test_stochastic_simulator.py
```

## Exemples

Consultez `example_usage.py` pour un exemple complet d'utilisation du simulateur, notamment :

- Configuration de plusieurs scénarios
- Exécution d'une simulation de référence
- Évaluation d'un moteur de décision personnalisé
- Analyse des résultats et recommandations

## Intégration dans le flux MCP

Ce simulateur s'intègre dans le flux MCP (Mission Control Platform) comme suit :

1. **Développement** : Utilisez le simulateur pour développer et tester des heuristiques de décision
2. **Test A/B** : Comparez différentes stratégies de frais dans des conditions contrôlées
3. **Shadow mode** : Validez les décisions avant de les appliquer en production
4. **Amélioration continue** : Ajustez les stratégies en fonction des métriques d'efficacité

## Personnalisation

- `config.py` : Modifiez les paramètres de configuration par défaut
- `volatility_factors` : Ajustez les facteurs de volatilité pour différents types de canaux
- `weights` dans `_calculate_effectiveness()` : Modifiez les pondérations des métriques selon vos priorités

## Limitations

- Simulation en temps discret (pas journalier)
- L'effet réseau entre nœuds est simplifié
- Pas de modélisation des attaques ou comportements malveillants
- Approximation des coûts de rebalancement

## Roadmap

- [ ] Ajout de graphes de réseau plus réalistes
- [ ] Intégration de données historiques réelles
- [ ] Modélisation des attaques et comportements malveillants
- [ ] Visualisation graphique des résultats de simulation
- [ ] API pour intégration dans des dashboards 