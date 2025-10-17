"""
Optimizer RAG Ollama pour générer des recommandations Lightning de haute qualité
Utilise des stratégies optimisées et des prompts spécialisés
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
import os

from src.clients.ollama_client import ollama_client
from src.ollama_strategy_optimizer import (
    detect_query_type,
    get_strategy,
    QueryType,
    OllamaStrategy
)
from app.services.rag_metrics import (
    rag_model_requests,
    rag_generation_duration,
    record_model_tokens
)

logger = logging.getLogger(__name__)


class OllamaRAGOptimizer:
    """
    Optimizer pour générer des recommandations Lightning de haute qualité via Ollama
    """
    
    def __init__(self, prompt_file: str = "prompts/lightning_recommendations_v2.md"):
        self.prompt_file = prompt_file
        self.system_prompt_v2 = self._load_prompt()
        
        self.stats = {
            'total_generations': 0,
            'avg_quality_score': 0.0,
            'by_query_type': {},
            'by_model': {},
            'total_tokens_generated': 0
        }
        
        logger.info(f"OllamaRAGOptimizer initialized with prompt: {prompt_file}")
    
    def _load_prompt(self) -> str:
        """Charge le prompt système optimisé"""
        try:
            if os.path.exists(self.prompt_file):
                with open(self.prompt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logger.info(f"Loaded optimized prompt ({len(content)} chars)")
                    return content
            else:
                logger.warning(f"Prompt file not found: {self.prompt_file}, using default")
                return self._get_default_prompt()
        except Exception as e:
            logger.error(f"Failed to load prompt: {str(e)}")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Prompt de fallback"""
        return """Tu es un expert Lightning Network. 
Analyse les métriques et fournis des recommandations actionnables, priorisées et avec commandes CLI."""
    
    async def generate_lightning_recommendations(
        self,
        node_metrics: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        query_type: Optional[QueryType] = None,
        force_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Génère des recommandations Lightning optimisées
        
        Args:
            node_metrics: Métriques complètes du nœud
            context: Contexte additionnel
            query_type: Type de requête (auto-détecté si None)
            force_model: Forcer un modèle spécifique
            
        Returns:
            Recommandations structurées avec métadonnées
        """
        start_time = datetime.now()
        context = context or {}
        
        # Auto-détecter le type de requête
        if not query_type:
            query = context.get('query', 'Analyse et recommandations pour ce nœud')
            query_type = detect_query_type(query, context)
        
        # Obtenir la stratégie optimale
        strategy = get_strategy(query_type)
        
        # Override model si demandé
        if force_model:
            strategy.model = force_model
        
        logger.info(
            f"Generating recommendations: "
            f"type={query_type.value}, model={strategy.model}, "
            f"temp={strategy.temperature}"
        )
        
        # Construire le prompt optimisé
        prompt = self._build_optimized_prompt(
            node_metrics=node_metrics,
            context=context,
            strategy=strategy
        )
        
        # Générer avec les paramètres optimaux
        try:
            response = await ollama_client.generate(
                prompt=prompt,
                model=strategy.model,
                temperature=strategy.temperature,
                max_tokens=strategy.num_predict,
                num_ctx=strategy.num_ctx,
                top_p=strategy.top_p
            )
            
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Métriques
            rag_generation_duration.labels(
                model=strategy.model,
                token_count_bucket=self._get_token_bucket(len(response))
            ).observe(duration_ms / 1000)
            
            rag_model_requests.labels(
                model_name=strategy.model,
                model_type='generation',
                status='success'
            ).inc()
            
            # Post-processing
            processed_response = self._post_process_response(
                response=response,
                query_type=query_type,
                node_metrics=node_metrics
            )
            
            # Stats
            self._update_stats(
                query_type,
                strategy.model,
                processed_response.get('quality_score', 0.8),
                len(response)
            )
            
            return {
                'recommendations': processed_response['recommendations'],
                'analysis': processed_response.get('analysis', ''),
                'summary': processed_response.get('summary', ''),
                'metadata': {
                    'model': strategy.model,
                    'query_type': query_type.value,
                    'generation_time_ms': duration_ms,
                    'quality_score': processed_response.get('quality_score', 0.0),
                    'response_length': len(response),
                    'recommendations_count': len(processed_response['recommendations']),
                    'parameters': {
                        'temperature': strategy.temperature,
                        'top_p': strategy.top_p,
                        'num_ctx': strategy.num_ctx,
                        'num_predict': strategy.num_predict
                    }
                },
                'raw_response': response if context.get('include_raw', False) else None
            }
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {str(e)}")
            
            rag_model_requests.labels(
                model_name=strategy.model,
                model_type='generation',
                status='error'
            ).inc()
            
            # Fallback gracieux
            return self._create_fallback_response(node_metrics, str(e))
    
    def _build_optimized_prompt(
        self,
        node_metrics: Dict[str, Any],
        context: Dict[str, Any],
        strategy: OllamaStrategy
    ) -> str:
        """Construit un prompt optimisé pour Lightning"""
        
        # System prompt de la stratégie OU prompt v2 complet
        if context.get('use_v2_prompt', True):
            system = self.system_prompt_v2
        else:
            system = strategy.system_prompt_template
        
        # Contexte Lightning structuré
        lightning_context = self._format_lightning_context(node_metrics, context)
        
        # Question/instruction finale
        instruction = context.get('instruction', """
Analyse ce nœud Lightning et génère des recommandations actionnables.
Respecte le format structuré avec priorités, impacts quantifiés et commandes CLI.
""")
        
        # Assemblage final
        prompt = f"""{system}

{lightning_context}

{instruction}

Génère maintenant ton analyse et tes recommandations au format strict défini ci-dessus:"""
        
        return prompt
    
    def _format_lightning_context(
        self,
        node_metrics: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Formate le contexte Lightning de manière structurée"""
        
        sections = []
        
        # Section identification
        sections.append(f"""## NŒUD LIGHTNING NETWORK

**Identification**
- Pubkey: {node_metrics.get('pubkey', 'N/A')[:16]}...
- Alias: {node_metrics.get('alias', 'Unknown')}
- Capacité totale: {node_metrics.get('total_capacity', 0):,} sats""")
        
        # Section performance
        sections.append(f"""
**Performance (30 derniers jours)**
- Revenue routing: {node_metrics.get('routing_revenue', 0):,} sats/mois
- Tentatives forward: {node_metrics.get('forward_attempts', 0)}
- Success rate: {node_metrics.get('success_rate', 0):.1f}%
- Uptime: {node_metrics.get('uptime_percentage', 0):.1f}%""")
        
        # Section liquidité
        sections.append(f"""
**Liquidité**
- Balance local: {node_metrics.get('local_balance', 0):,} sats ({node_metrics.get('local_pct', 0):.1f}%)
- Balance remote: {node_metrics.get('remote_balance', 0):,} sats ({node_metrics.get('remote_pct', 0):.1f}%)
- Ratio balance: {node_metrics.get('balance_ratio', 0.5):.2f}""")
        
        # Section canaux
        sections.append(f"""
**Canaux**
- Nombre total: {node_metrics.get('channel_count', 0)}
- Actifs: {node_metrics.get('active_channels', 0)}
- Inactifs: {node_metrics.get('inactive_channels', 0)}
- Taille moyenne: {node_metrics.get('avg_channel_size', 0):,} sats""")
        
        # Section frais
        sections.append(f"""
**Frais Actuels**
- Base fee: {node_metrics.get('base_fee_msat', 0)} msat
- Fee rate: {node_metrics.get('fee_rate_ppm', 0)} ppm
- Benchmark réseau: {node_metrics.get('network_median_fee', 100)} ppm (médian)
- Compétitivité: {self._calculate_fee_competitiveness(node_metrics)}""")
        
        # Section position réseau
        sections.append(f"""
**Position Réseau**
- Betweenness centrality: {node_metrics.get('betweenness', 0):.6f}
- Degree: {node_metrics.get('degree', 0)}
- Rank: #{node_metrics.get('rank', 0):,} / {node_metrics.get('total_nodes', 15000):,}
- Percentile: {self._calculate_percentile(node_metrics)}%""")
        
        # Échecs récents (si disponible)
        if 'recent_failures' in node_metrics and node_metrics['recent_failures']:
            failures = node_metrics['recent_failures']
            sections.append(f"""
**Échecs de Routage Récents**
- No route: {failures.get('no_route', 0)} ({failures.get('no_route_pct', 0):.1f}%)
- Insufficient capacity: {failures.get('insufficient_capacity', 0)} ({failures.get('insufficient_capacity_pct', 0):.1f}%)
- Temporary failure: {failures.get('temporary_failure', 0)} ({failures.get('temporary_failure_pct', 0):.1f}%)""")
        
        # État du réseau (si disponible)
        if context.get('network_state'):
            network = context['network_state']
            sections.append(f"""
**État du Réseau Lightning Global**
- Congestion: {network.get('congestion_level', 'normale')}
- Fee rate médian: {network.get('median_fee_rate', 100)} ppm
- Nœuds actifs: {network.get('active_nodes', 15000):,}
- Canaux publics: {network.get('public_channels', 60000):,}
- Capacité réseau: {network.get('network_capacity', 5000):,} BTC""")
        
        return '\n'.join(sections)
    
    def _calculate_fee_competitiveness(self, metrics: Dict[str, Any]) -> str:
        """Calcule la compétitivité des frais"""
        node_fee = metrics.get('fee_rate_ppm', 100)
        network_median = metrics.get('network_median_fee', 100)
        
        if network_median == 0:
            return "Non calculable"
        
        ratio = node_fee / network_median
        
        if ratio < 0.7:
            return f"Très compétitif ({ratio:.1f}x médian)"
        elif ratio < 1.0:
            return f"Compétitif ({ratio:.1f}x médian)"
        elif ratio < 1.5:
            return f"Au-dessus médian ({ratio:.1f}x)"
        else:
            return f"Non compétitif ({ratio:.1f}x médian)"
    
    def _calculate_percentile(self, metrics: Dict[str, Any]) -> float:
        """Calcule le percentile du nœud"""
        rank = metrics.get('rank', 0)
        total = metrics.get('total_nodes', 15000)
        
        if total == 0:
            return 0.0
        
        percentile = ((total - rank) / total) * 100
        return round(percentile, 1)
    
    def _post_process_response(
        self,
        response: str,
        query_type: QueryType,
        node_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Post-traite la réponse pour extraire recommandations structurées"""
        
        # Parser les sections
        recommendations = []
        analysis = ""
        summary = ""
        
        # Extraction du résumé exécutif
        summary_match = re.search(r'🎯 Résumé Exécutif.*?\n(.*?)\n###', response, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
        
        # Extraction de l'analyse
        analysis_match = re.search(r'📊 Analyse des Métriques(.*?)🚀 Recommandations', response, re.DOTALL)
        if analysis_match:
            analysis = analysis_match.group(1).strip()
        
        # Extraction des recommandations par priorité
        priority_patterns = [
            (r'PRIORITÉ CRITIQUE 🔴(.*?)(?=PRIORITÉ|###|$)', 'critical'),
            (r'PRIORITÉ HAUTE 🟠(.*?)(?=PRIORITÉ|###|$)', 'high'),
            (r'PRIORITÉ MOYENNE 🟡(.*?)(?=PRIORITÉ|###|$)', 'medium'),
            (r'PRIORITÉ BASSE 🟢(.*?)(?=PRIORITÉ|###|$)', 'low')
        ]
        
        for pattern, priority in priority_patterns:
            matches = re.finditer(pattern, response, re.DOTALL)
            for match in matches:
                rec = self._parse_recommendation(match.group(1), priority)
                if rec:
                    recommendations.append(rec)
        
        # Score de qualité (heuristique)
        quality_score = self._estimate_quality(response, recommendations, node_metrics)
        
        return {
            'recommendations': recommendations,
            'analysis': analysis,
            'summary': summary,
            'quality_score': quality_score,
            'raw_response': response
        }
    
    def _parse_recommendation(self, section: str, priority: str) -> Optional[Dict[str, Any]]:
        """Parse une recommandation depuis le texte"""
        try:
            rec = {
                'priority': priority,
                'action': '',
                'impact': '',
                'effort': '',
                'risk': 'medium',
                'justification': '',
                'command': '',
                'validation': ''
            }
            
            lines = section.split('\n')
            current_field = None
            
            for line in lines:
                line = line.strip()
                
                # Extraire l'action (première ligne non-vide en gras)
                if line.startswith('**') and not rec['action']:
                    rec['action'] = line.strip('*').strip()
                    continue
                
                # Extraire les champs
                if '**Impact estimé**' in line:
                    rec['impact'] = line.split(':', 1)[-1].strip()
                elif '**Effort**' in line:
                    rec['effort'] = line.split(':', 1)[-1].strip()
                elif '**Risque**' in line:
                    risk_text = line.split(':', 1)[-1].strip().lower()
                    if 'faible' in risk_text or 'low' in risk_text:
                        rec['risk'] = 'low'
                    elif 'élevé' in risk_text or 'high' in risk_text:
                        rec['risk'] = 'high'
                elif '**Justification**' in line:
                    rec['justification'] = line.split(':', 1)[-1].strip()
                elif '**Commande**' in line or line.startswith('```bash'):
                    current_field = 'command'
                elif '**Validation**' in line:
                    current_field = 'validation'
                elif current_field == 'command' and line.startswith('lncli'):
                    rec['command'] = line
                    current_field = None
                elif current_field == 'validation':
                    rec['validation'] += line + ' '
            
            return rec if rec['action'] else None
            
        except Exception as e:
            logger.warning(f"Failed to parse recommendation: {str(e)}")
            return None
    
    def _estimate_quality(
        self,
        response: str,
        recommendations: List[Dict],
        node_metrics: Dict
    ) -> float:
        """Estime la qualité de la réponse (0-1)"""
        score = 0.5  # Base
        
        # Longueur raisonnable
        if 500 < len(response) < 4000:
            score += 0.1
        
        # Contient des recommandations
        if len(recommendations) >= 2:
            score += 0.15
        elif len(recommendations) >= 4:
            score += 0.20
        
        # Contient des commandes CLI
        cli_count = response.count('lncli') + response.count('bitcoin-cli')
        score += min(cli_count * 0.05, 0.15)
        
        # Contient des chiffres/estimations
        digit_density = sum(c.isdigit() for c in response) / len(response)
        score += min(digit_density * 2, 0.1)
        
        # Contient des priorités structurées
        if '🔴' in response or '🟠' in response:
            score += 0.1
        
        # Contient des émojis de structure
        structure_emojis = ['🎯', '📊', '🚀', '⚠️']
        structure_score = sum(emoji in response for emoji in structure_emojis) * 0.02
        score += min(structure_score, 0.1)
        
        # Pénalité si trop court ou trop long
        if len(response) < 300:
            score -= 0.2
        elif len(response) > 5000:
            score -= 0.1
        
        return max(0.0, min(score, 1.0))
    
    def _create_fallback_response(
        self,
        node_metrics: Dict[str, Any],
        error: str
    ) -> Dict[str, Any]:
        """Crée une réponse de fallback en cas d'erreur"""
        return {
            'recommendations': [
                {
                    'priority': 'medium',
                    'action': 'Vérifier la connectivité du service Ollama',
                    'impact': 'Permet de générer des recommandations',
                    'effort': '5 minutes',
                    'risk': 'low',
                    'justification': f'Erreur de génération: {error}',
                    'command': 'ollama list',
                    'validation': 'Vérifier que le service Ollama répond'
                }
            ],
            'analysis': f"Impossible de générer une analyse complète. Erreur: {error}",
            'summary': "Service de génération temporairement indisponible",
            'metadata': {
                'model': 'fallback',
                'query_type': 'error',
                'quality_score': 0.0,
                'error': error
            }
        }
    
    def _get_token_bucket(self, length: int) -> str:
        """Bucket de longueur pour métriques"""
        if length < 500:
            return "< 500"
        elif length < 1500:
            return "500-1500"
        elif length < 3000:
            return "1500-3000"
        else:
            return "> 3000"
    
    def _update_stats(
        self,
        query_type: QueryType,
        model: str,
        quality_score: float,
        tokens_generated: int
    ):
        """Met à jour les statistiques"""
        self.stats['total_generations'] += 1
        self.stats['total_tokens_generated'] += tokens_generated
        
        # Moyenne mobile qualité
        n = self.stats['total_generations']
        self.stats['avg_quality_score'] = (
            (self.stats['avg_quality_score'] * (n - 1) + quality_score) / n
        )
        
        # Par type
        if query_type.value not in self.stats['by_query_type']:
            self.stats['by_query_type'][query_type.value] = {'count': 0, 'avg_quality': 0.0}
        
        type_stats = self.stats['by_query_type'][query_type.value]
        type_stats['count'] += 1
        type_stats['avg_quality'] = (
            (type_stats['avg_quality'] * (type_stats['count'] - 1) + quality_score) 
            / type_stats['count']
        )
        
        # Par modèle
        if model not in self.stats['by_model']:
            self.stats['by_model'][model] = {'count': 0, 'avg_quality': 0.0}
        
        model_stats = self.stats['by_model'][model]
        model_stats['count'] += 1
        model_stats['avg_quality'] = (
            (model_stats['avg_quality'] * (model_stats['count'] - 1) + quality_score) 
            / model_stats['count']
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques"""
        return {
            **self.stats,
            'avg_tokens_per_generation': (
                self.stats['total_tokens_generated'] / self.stats['total_generations']
                if self.stats['total_generations'] > 0 else 0
            )
        }


# Instance globale
ollama_rag_optimizer = OllamaRAGOptimizer()

logger.info("Ollama RAG Optimizer loaded successfully")

