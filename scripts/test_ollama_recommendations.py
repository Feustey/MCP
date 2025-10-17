"""
Script de test pour les recommandations Ollama optimisées
Permet de valider que le système génère des recommandations de qualité
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ollama_rag_optimizer import ollama_rag_optimizer, QueryType


# Données de test simulées
SAMPLE_NODE_METRICS = {
    'pubkey': '03abc123def456789abc123def456789abc123def456789abc123def456789abc123',
    'alias': 'TestNode-MCP',
    'total_capacity': 50_000_000,  # 50M sats
    'routing_revenue': 8_500,  # 8.5k sats/mois
    'forward_attempts': 240,
    'success_rate': 78.5,
    'uptime_percentage': 96.2,
    'local_balance': 35_000_000,
    'local_pct': 70.0,
    'remote_balance': 15_000_000,
    'remote_pct': 30.0,
    'balance_ratio': 0.70,
    'channel_count': 12,
    'active_channels': 11,
    'inactive_channels': 1,
    'avg_channel_size': 4_166_667,
    'base_fee_msat': 5000,
    'fee_rate_ppm': 500,
    'network_median_fee': 100,
    'betweenness': 0.000125,
    'degree': 12,
    'rank': 850,
    'total_nodes': 15000,
    'recent_failures': {
        'no_route': 42,
        'no_route_pct': 70.0,
        'insufficient_capacity': 12,
        'insufficient_capacity_pct': 20.0,
        'temporary_failure': 6,
        'temporary_failure_pct': 10.0
    }
}

SAMPLE_NETWORK_STATE = {
    'congestion_level': 'normale',
    'median_fee_rate': 100,
    'active_nodes': 15234,
    'public_channels': 68542,
    'network_capacity': 5230
}


async def test_recommendation(
    query_type: QueryType,
    node_metrics: dict = None,
    context: dict = None
):
    """
    Teste la génération de recommandations pour un type de requête
    """
    print(f"\n{'='*80}")
    print(f"TEST: {query_type.value.upper()}")
    print(f"{'='*80}\n")
    
    node_metrics = node_metrics or SAMPLE_NODE_METRICS
    context = context or {
        'network_state': SAMPLE_NETWORK_STATE,
        'query': f'Test de requête type {query_type.value}'
    }
    
    start_time = datetime.now()
    
    try:
        result = await ollama_rag_optimizer.generate_lightning_recommendations(
            node_metrics=node_metrics,
            context=context,
            query_type=query_type
        )
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Afficher résultats
        print(f"✓ Génération réussie en {duration_ms:.0f}ms")
        print(f"\nModèle: {result['metadata']['model']}")
        print(f"Qualité: {result['metadata']['quality_score']:.2%}")
        print(f"Recommandations: {result['metadata']['recommendations_count']}")
        print(f"Longueur: {result['metadata']['response_length']} caractères")
        
        # Résumé
        if result.get('summary'):
            print(f"\n📋 Résumé:")
            print(f"   {result['summary'][:200]}...")
        
        # Recommandations
        print(f"\n🚀 Recommandations générées:")
        for i, rec in enumerate(result['recommendations'][:3], 1):
            priority_emoji = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }.get(rec['priority'], '⚪')
            
            print(f"\n   {i}. {priority_emoji} [{rec['priority'].upper()}] {rec['action'][:60]}...")
            if rec.get('impact'):
                print(f"      Impact: {rec['impact'][:50]}")
            if rec.get('command'):
                print(f"      CLI: {rec['command'][:60]}")
        
        if len(result['recommendations']) > 3:
            print(f"\n   ... et {len(result['recommendations']) - 3} autres recommandations")
        
        # Paramètres utilisés
        params = result['metadata']['parameters']
        print(f"\n⚙️  Paramètres:")
        print(f"   Temperature: {params['temperature']}")
        print(f"   Context window: {params['num_ctx']}")
        print(f"   Max tokens: {params['num_predict']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_all_query_types():
    """Teste tous les types de requêtes"""
    print("\n" + "="*80)
    print("TEST COMPLET - TOUS LES TYPES DE REQUÊTES")
    print("="*80)
    
    results = {}
    
    for query_type in QueryType:
        success = await test_recommendation(query_type)
        results[query_type.value] = success
        
        # Pause entre tests
        await asyncio.sleep(2)
    
    # Résumé final
    print("\n" + "="*80)
    print("RÉSUMÉ DES TESTS")
    print("="*80 + "\n")
    
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    for query_type, success in results.items():
        status = "✓ OK" if success else "✗ FAIL"
        print(f"   {status}  {query_type}")
    
    print(f"\nRésultat: {success_count}/{total_count} tests réussis")
    
    # Stats globales
    stats = ollama_rag_optimizer.get_stats()
    print(f"\nStatistiques globales:")
    print(f"   Générations: {stats['total_generations']}")
    print(f"   Qualité moyenne: {stats['avg_quality_score']:.2%}")
    print(f"   Tokens moyens: {stats.get('avg_tokens_per_generation', 0):.0f}")
    
    return success_count == total_count


async def test_specific_scenario(scenario_name: str):
    """Teste un scénario spécifique"""
    
    scenarios = {
        'desequilibre': {
            'name': 'Nœud avec déséquilibre liquidité',
            'metrics': {
                **SAMPLE_NODE_METRICS,
                'local_pct': 90.0,
                'remote_pct': 10.0,
                'success_rate': 45.0,
                'recent_failures': {
                    'no_route': 84,
                    'no_route_pct': 70.0
                }
            }
        },
        'frais_eleves': {
            'name': 'Nœud avec frais trop élevés',
            'metrics': {
                **SAMPLE_NODE_METRICS,
                'base_fee_msat': 10000,
                'fee_rate_ppm': 1000,
                'forward_attempts': 15,
                'routing_revenue': 800
            }
        },
        'uptime_faible': {
            'name': 'Nœud avec uptime faible',
            'metrics': {
                **SAMPLE_NODE_METRICS,
                'uptime_percentage': 87.3,
                'rank': 1240
            }
        }
    }
    
    if scenario_name not in scenarios:
        print(f"✗ Scénario inconnu: {scenario_name}")
        print(f"Scénarios disponibles: {', '.join(scenarios.keys())}")
        return False
    
    scenario = scenarios[scenario_name]
    
    print(f"\n{'='*80}")
    print(f"TEST SCÉNARIO: {scenario['name'].upper()}")
    print(f"{'='*80}\n")
    
    return await test_recommendation(
        QueryType.DETAILED_RECOMMENDATIONS,
        node_metrics=scenario['metrics']
    )


async def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test des recommandations Ollama optimisées")
    parser.add_argument(
        '--mode',
        choices=['all', 'single', 'scenario'],
        default='all',
        help='Mode de test'
    )
    parser.add_argument(
        '--type',
        choices=[qt.value for qt in QueryType],
        help='Type de requête pour mode single'
    )
    parser.add_argument(
        '--scenario',
        choices=['desequilibre', 'frais_eleves', 'uptime_faible'],
        help='Scénario spécifique pour mode scenario'
    )
    parser.add_argument(
        '--output',
        help='Fichier de sortie JSON pour sauvegarder les résultats'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("MCP OLLAMA RECOMMENDATIONS - TESTS")
    print("="*80)
    
    success = False
    
    if args.mode == 'all':
        success = await test_all_query_types()
    
    elif args.mode == 'single':
        if not args.type:
            print("✗ --type requis pour mode single")
            return 1
        
        query_type = QueryType(args.type)
        success = await test_recommendation(query_type)
    
    elif args.mode == 'scenario':
        if not args.scenario:
            print("✗ --scenario requis pour mode scenario")
            return 1
        
        success = await test_specific_scenario(args.scenario)
    
    # Sauvegarder résultats si demandé
    if args.output:
        stats = ollama_rag_optimizer.get_stats()
        with open(args.output, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"\n✓ Résultats sauvegardés dans {args.output}")
    
    print("\n" + "="*80)
    print(f"{'✓ TOUS LES TESTS RÉUSSIS' if success else '✗ CERTAINS TESTS ONT ÉCHOUÉ'}")
    print("="*80 + "\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

