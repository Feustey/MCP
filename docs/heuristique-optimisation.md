# Documentation sur les heuristiques d'optimisation
> Dernière mise à jour: 7 mai 2025

# Heuristique d'Optimisation des Nœuds Lightning

## Vue d'ensemble

L'heuristique d'optimisation est un composant central de MCP qui analyse les métriques d'un nœud Lightning Network et calcule un score composite pour évaluer ses performances. Ce score est utilisé pour automatiser les ajustements de configuration et maximiser les performances du nœud.

## Principes de base

L'heuristique repose sur plusieurs principes fondamentaux :

1. **Équilibre multifactoriel** - Prendre en compte plusieurs métriques complémentaires
2. **Pondération adaptative** - Ajuster les poids des facteurs selon leur importance relative
3. **Boucle de feedback** - Affiner l'heuristique à partir des résultats des tests A/B
4. **Benchmarking continu** - Comparer les performances avec d'autres configurations

## Métriques clés

Les principales métriques prises en compte sont :

| Métrique | Description | Importance |
|----------|-------------|------------|
| `htlc_response_time` | Temps de réponse aux HTLC | Élevée |
| `channel_balance_quality` | Équilibre de la liquidité des canaux | Élevée |
| `routing_success_rate` | Taux de succès des tentatives de routage | Moyenne |
| `revenue_per_sat_locked` | Revenus par satoshi immobilisé | Moyenne |
| `bidirectional_channels_ratio` | Proportion de canaux avec liquidité bidirectionnelle | Moyenne |
| `liquidity_score` | Score du scanner de liquidité | Moyenne |

## Implémentation du calcul de score

La fonction `calculate_score` implémente l'heuristique de scoring :

```python
def calculate_score(metrics: Dict[str, float], weights: Dict[str, float] = None) -> float:
    """
    Calcule un score composite basé sur les métriques de performance du nœud.
    
    Args:
        metrics: Dictionnaire contenant les métriques du nœud
        weights: Dictionnaire de poids personnalisés (facultatif)
        
    Returns:
        float: Score entre 0 et 100
    """
    # Poids par défaut si non spécifiés
    if not weights:
        weights = {
            "htlc_response_time": 0.30,      # Temps de réponse HTLC
            "liquidity_balance": 0.30,       # Équilibre de la liquidité des canaux
            "routing_success_rate": 0.20,    # Taux de succès des routages
            "revenue_efficiency": 0.10,      # Efficacité des revenus
            "liquidity_score": 0.10          # Score de liquidité
        }
    
    # 1. Score du temps de réponse HTLC
    # Objectif : 0.3s ou moins = score maximal
    # Plus de 2s = score minimal
    htlc_time = metrics.get("htlc_response_time", 2.0)
    htlc_score = max(0, min(100, (2.0 - htlc_time) / 1.7 * 100))
    
    # 2. Score de l'équilibre de liquidité
    # Combine le channel_balance_quality et le % de canaux liquides
    liquidity_score = (
        metrics.get("channel_balance_quality", 0) * 60 +  # Qualité de l'équilibre (0-1) * 60
        min(1.0, metrics.get("liquid_channels_ratio", 0) / 0.66) * 40  # % canaux liquides, cible 66%
    )
    
    # 3. Score du taux de succès des routages
    routing_score = metrics.get("routing_success_rate", 0) * 100
    
    # 4. Score de l'efficacité des revenus
    # Combine revenue_per_sat_locked et average_fee_earned
    revenue_score = (
        min(1.0, metrics.get("revenue_per_sat_locked", 0) / 0.0001) * 50 +  # Normalisation des revenus/sat
        min(1.0, metrics.get("average_fee_earned", 0) / 100) * 50  # Normalisation des frais moyens
    )
    
    # 5. Score de liquidité (optionnel)
    # Utilise directement le score de liquidité calculé par LiquidityScanManager
    liquidity_scan_score = metrics.get("liquidity_score", 0)
    
    # Bonus pour les canaux bidirectionnels
    bidirectional_ratio = metrics.get("bidirectional_channels_ratio", 0)
    if bidirectional_ratio > 0.8:  # Plus de 80% de canaux bidirectionnels
        liquidity_scan_score *= 1.2
        liquidity_scan_score = min(100, liquidity_scan_score)  # Plafonner à 100
    
    # Calcul du score final pondéré
    final_score = (
        weights["htlc_response_time"] * htlc_score +
        weights["liquidity_balance"] * liquidity_score +
        weights["routing_success_rate"] * routing_score +
        weights["revenue_efficiency"] * revenue_score +
        weights["liquidity_score"] * liquidity_scan_score
    )
    
    # Bonus/Malus basés sur des facteurs critiques
    if htlc_time > 8.0:  # Pénalité pour temps de réponse très lent
        final_score *= 0.7
    if metrics.get("channel_balance_quality", 0) < 0.3:  # Pénalité pour déséquilibre sévère
        final_score *= 0.8
    if bidirectional_ratio < 0.5:  # Pénalité pour faible taux de canaux bidirectionnels
        final_score *= 0.9
        
    return round(final_score, 2)
```

## Version sans liquidité

Une version simplifiée du calcul de score sans les métriques de liquidité est également disponible :

```python
def calculate_score(metrics: Dict[str, float]) -> float:
    """
    Calcule un score composite basé sur les métriques de performance du nœud.
    Version simplifiée sans les métriques de liquidité.
    """
    weights = {
        "htlc_response_time": 0.40,      # Temps de réponse HTLC 
        "liquidity_balance": 0.30,       # Équilibre de la liquidité des canaux
        "routing_success_rate": 0.20,    # Taux de succès des routages
        "revenue_efficiency": 0.10       # Efficacité des revenus
    }
    
    # Calcul des scores individuels...
    
    # Calcul du score final pondéré
    final_score = (
        weights["htlc_response_time"] * htlc_score +
        weights["liquidity_balance"] * liquidity_score +
        weights["routing_success_rate"] * routing_score +
        weights["revenue_efficiency"] * revenue_score
    )
    
    return round(final_score, 2)
```

## Tests A/B et ajustement des poids

MCP utilise des tests A/B pour comparer différentes configurations et affiner les poids de l'heuristique :

```python
async def run_a_b_test(base_scenario: Dict[str, Any]) -> Dict[str, Any]:
    """Exécute un test A/B pour comparer différentes configurations."""
    # Génération de scénarios
    scenarios = await test_manager.generate_a_b_test(base_scenario)
    
    # Exécution des tests pour chaque scénario
    for scenario in scenarios:
        await test_manager.configure_node(scenario)
        await test_manager.start_test_session(
            scenario_id=scenario['id'],
            duration_minutes=1440  # 24 heures
        )
    
    # Identification du scénario gagnant
    winner = await test_manager.action_tracker.identify_winners(scenario_ids)
    
    # Ajustement de l'heuristique si nécessaire
    if winner and winner['action_type'] != "heuristic":
        new_weights = await test_manager.action_tracker.calculate_weight_adjustment()
        return {"winner": winner, "new_weights": new_weights}
    
    return {"winner": winner}
```

## Ajustement dynamique des poids

Le système calcule de nouveaux poids basés sur les performances comparatives des scénarios :

```python
async def calculate_weight_adjustment(self) -> Dict[str, float]:
    """Calcule des ajustements de poids basés sur les performances des tests."""
    # Récupération des données de performance
    metrics = await self.get_all_test_metrics()
    
    # Analyse des corrélations entre métriques et performances
    correlations = {}
    for metric in ["htlc_response_time", "liquidity_balance", "routing_success_rate", 
                   "revenue_efficiency", "liquidity_score"]:
        correlations[metric] = self._calculate_correlation(
            [m.get(metric, 0) for m in metrics.values()],
            [m.get("sats_forwarded_24h", 0) for m in metrics.values()]
        )
    
    # Normalisation des corrélations en poids
    total_correlation = sum(abs(c) for c in correlations.values())
    if total_correlation == 0:
        return DEFAULT_WEIGHTS
        
    new_weights = {
        metric: min(0.5, max(0.1, abs(corr) / total_correlation))
        for metric, corr in correlations.items()
    }
    
    # Ajustement pour que la somme soit 1.0
    weight_sum = sum(new_weights.values())
    new_weights = {m: w/weight_sum for m, w in new_weights.items()}
    
    return new_weights
```

## Intégration avec RAG

L'heuristique est enrichie par l'intégration avec le système RAG qui fournit des connaissances contextuelles :

```python
async def validate_lightning_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
    """Valide une configuration Lightning en utilisant le RAG pour l'enrichir."""
    # Construction du contexte
    context = f"""
    Configuration à évaluer:
    - Base Fee: {config.get('fee_structure', {}).get('base_fee_msat', 'Non spécifié')} msat
    - Fee Rate: {config.get('fee_structure', {}).get('fee_rate', 'Non spécifié')} ppm
    - Target Local Ratio: {config.get('channel_policy', {}).get('target_local_ratio', 'Non spécifié')}
    """
    
    # Requête RAG pour évaluation
    result = await self.rag.query(
        "Évalue cette configuration de nœud Lightning en termes d'équilibre " 
        "entre revenus et probabilité de routage. Donne un score de 1 à 10 et des suggestions.",
        additional_context=context,
        search_type="hybrid"
    )
    
    # Extraction du score et des suggestions
    score_match = re.search(r"score\s*:\s*(\d+(?:\.\d+)?)", result, re.IGNORECASE)
    score = float(score_match.group(1)) if score_match else 5.0
    
    # Extraction des suggestions
    suggestions = re.findall(r"suggestion\s*:\s*([^\n]+)", result, re.IGNORECASE)
    
    return {
        "score": score,
        "feedback": result,
        "improvements": suggestions
    }
```

## Génération de scénarios

Le système peut générer automatiquement des scénarios de test en utilisant le RAG :

```python
async def generate_test_scenarios():
    """Génère des scénarios de test en utilisant le RAG."""
    prompt = """
    Génère 5 configurations différentes pour un nœud Lightning Network au format JSON.
    Chaque configuration doit avoir un ID unique et inclure:
    - fee_structure (base_fee_msat et fee_rate)
    - channel_policy (target_local_ratio et rebalance_threshold)
    
    Les configurations doivent couvrir une gamme de stratégies:
    1. Une configuration optimisée pour le volume (frais bas)
    2. Une configuration optimisée pour le revenu (frais élevés)
    3. Une configuration équilibrée
    4. Une configuration conservative
    5. Une configuration agressive
    
    Réponds uniquement avec le JSON brut.
    """
    
    # Génération via RAG
    scenarios_raw = await rag_system.query(prompt, use_query_expansion=False)
    
    # Traitement et validation des scénarios
    # ...
    
    return validated_scenarios, output_path
```

## Conclusion

L'heuristique d'optimisation MCP combine des métriques clés de performance des nœuds Lightning Network avec un système de pondération adaptative pour optimiser automatiquement les configurations. La boucle de feedback via tests A/B permet d'affiner continuellement les poids de l'heuristique en fonction des performances réelles.

Cette approche basée sur les données permet d'atteindre un équilibre optimal entre les revenus de routage, le taux de succès des paiements et l'efficacité de la liquidité, adaptée aux spécificités de chaque nœud et à l'évolution du réseau Lightning.
