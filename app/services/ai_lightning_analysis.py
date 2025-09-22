"""
AI-powered Lightning Network analysis using Anthropic API.
Provides enhanced insights and recommendations for Lightning nodes.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib
from dotenv import load_dotenv
from app.services.redis_cache import cache_service

load_dotenv()
logger = logging.getLogger(__name__)

class AILightningAnalysis:
    """
    Enhanced Lightning Network analysis using AI for deeper insights.
    """
    
    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.use_mock = not self.anthropic_key or os.getenv("AI_USE_MOCK", "false").lower() == "true"
        
        if self.use_mock:
            logger.warning("AI Lightning Analysis en mode mock")
        else:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.anthropic_key)
                logger.info("Client Anthropic initialisé avec succès")
            except ImportError:
                logger.error("Module anthropic non disponible, mode mock activé")
                self.use_mock = True
            except Exception as e:
                logger.error(f"Erreur initialisation Anthropic: {str(e)}, mode mock activé")
                self.use_mock = True
    
    async def analyze_node_with_ai(self, node_id: str, basic_analysis: Dict) -> Dict[str, Any]:
        """
        Enhance basic node analysis with AI-powered insights.
        """
        # Check cache first
        query_data = {
            'node_id': node_id,
            'analysis_type': 'enhanced_node_analysis',
            'basic_metrics': {
                'total_capacity': basic_analysis.get('metrics', {}).get('total_capacity', 0),
                'channel_count': basic_analysis.get('metrics', {}).get('channel_count', 0),
                'centrality_score': basic_analysis.get('scores', {}).get('centrality_score', 0),
                'reliability_score': basic_analysis.get('scores', {}).get('reliability_score', 0)
            }
        }
        
        query_hash = await cache_service.generate_query_hash(
            f"enhanced_analysis_{node_id}", 
            query_data
        )
        
        # Try to get from cache
        cached_result = await cache_service.get_ai_insight(query_hash)
        if cached_result:
            logger.info(f"Utilisation du cache pour l'analyse IA du nœud {node_id}")
            return cached_result
        
        # Generate new AI analysis
        if self.use_mock:
            ai_analysis = self._generate_mock_ai_analysis(node_id, basic_analysis)
        else:
            ai_analysis = await self._generate_real_ai_analysis(node_id, basic_analysis)
        
        # Cache the result
        await cache_service.cache_ai_insight(query_hash, ai_analysis, ttl_hours=12)
        
        return ai_analysis
    
    def _generate_mock_ai_analysis(self, node_id: str, basic_analysis: Dict) -> Dict[str, Any]:
        """Generate mock AI analysis for testing."""
        scores = basic_analysis.get('scores', {})
        metrics = basic_analysis.get('metrics', {})
        
        # Simulate AI-like analysis
        overall_score = scores.get('overall_score', 7.0)
        channel_count = metrics.get('channel_count', 10)
        capacity = metrics.get('total_capacity', 100000000)
        
        # Mock strategic insights based on metrics
        strategic_insights = []
        if overall_score < 6.0:
            strategic_insights.append({
                "priority": "high",
                "category": "performance",
                "title": "Amélioration critique de la performance",
                "insight": "Le nœud présente des scores inférieurs à la moyenne. Une optimisation globale est nécessaire.",
                "confidence": 0.85
            })
        
        if channel_count < 5:
            strategic_insights.append({
                "priority": "high", 
                "category": "connectivity",
                "title": "Expansion du réseau de connexions",
                "insight": "Le nombre de canaux est limité. Augmenter la connectivité améliorerait significativement la position réseau.",
                "confidence": 0.90
            })
        
        if capacity > 100000000:  # > 1 BTC
            strategic_insights.append({
                "priority": "medium",
                "category": "capital_efficiency", 
                "title": "Optimisation de l'efficacité du capital",
                "insight": "La capacité importante suggère un potentiel d'optimisation des stratégies de routage et de frais.",
                "confidence": 0.75
            })
        
        # Mock market analysis
        market_context = {
            "network_trends": {
                "routing_demand": "croissante",
                "fee_competition": "modérée", 
                "liquidity_premium": "stable"
            },
            "competitive_analysis": {
                "similar_nodes_performance": "comparative",
                "market_share_opportunity": "moyenne",
                "differentiation_potential": "élevé"
            },
            "timing_recommendations": {
                "optimal_expansion_period": "3-6 mois",
                "fee_adjustment_frequency": "hebdomadaire",
                "rebalancing_schedule": "bi-hebdomadaire"
            }
        }
        
        # Mock risk assessment
        risk_analysis = {
            "concentration_risk": {
                "level": "low" if channel_count > 8 else "medium",
                "assessment": "Distribution des canaux acceptable" if channel_count > 8 else "Diversification recommandée"
            },
            "liquidity_risk": {
                "level": "low",
                "assessment": "Niveaux de liquidité dans les normes"
            },
            "technical_risk": {
                "level": "low",
                "assessment": "Configuration technique stable"
            }
        }
        
        return {
            "ai_analysis_version": "mock_v1.0",
            "analysis_timestamp": datetime.now().isoformat(),
            "strategic_insights": strategic_insights,
            "market_context": market_context,
            "risk_analysis": risk_analysis,
            "confidence_score": 0.80,
            "next_review_date": (datetime.now().replace(hour=datetime.now().hour + 24)).isoformat(),
            "ai_model": "mock_claude",
            "processing_time_ms": 150
        }
    
    async def _generate_real_ai_analysis(self, node_id: str, basic_analysis: Dict) -> Dict[str, Any]:
        """Generate real AI analysis using Anthropic API."""
        try:
            # Prepare context for AI analysis
            context = self._prepare_analysis_context(node_id, basic_analysis)
            
            # Create the prompt for enhanced analysis
            prompt = f"""
Tu es un expert en Lightning Network. Analyse ce nœud et fournis des insights stratégiques avancés.

Données du nœud:
{json.dumps(basic_analysis, indent=2)}

Fournis une analyse JSON avec:
1. strategic_insights: Liste d'insights stratégiques avec priorité, catégorie, titre, insight, et confidence (0-1)
2. market_context: Analyse du contexte de marché actuel
3. risk_analysis: Évaluation des risques par catégorie
4. confidence_score: Ton niveau de confiance global (0-1)

Réponds uniquement en JSON valide, sans explication additionnelle.
"""
            
            # Make API call to Anthropic
            message = await self._call_anthropic_api(prompt)
            
            # Parse and validate response
            try:
                ai_response = json.loads(message)
                
                # Add metadata
                ai_response.update({
                    "ai_analysis_version": "anthropic_v1.0",
                    "analysis_timestamp": datetime.now().isoformat(),
                    "ai_model": "claude-3-sonnet",
                    "node_id": node_id
                })
                
                return ai_response
                
            except json.JSONDecodeError:
                logger.error("Réponse Anthropic non-JSON valide, basculement mode mock")
                return self._generate_mock_ai_analysis(node_id, basic_analysis)
                
        except Exception as e:
            logger.error(f"Erreur analyse AI réelle: {str(e)}, basculement mode mock")
            return self._generate_mock_ai_analysis(node_id, basic_analysis)
    
    async def _call_anthropic_api(self, prompt: str) -> str:
        """Make API call to Anthropic."""
        try:
            message = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            return message.content[0].text if message.content else ""
            
        except Exception as e:
            logger.error(f"Erreur appel API Anthropic: {str(e)}")
            raise
    
    def _prepare_analysis_context(self, node_id: str, basic_analysis: Dict) -> Dict:
        """Prepare analysis context for AI processing."""
        return {
            "node_id": node_id,
            "timestamp": datetime.now().isoformat(),
            "basic_metrics": basic_analysis.get('metrics', {}),
            "scores": basic_analysis.get('scores', {}),
            "network_position": basic_analysis.get('network_position', {}),
            "current_recommendations": basic_analysis.get('recommendations', {})
        }
    
    async def generate_network_insights(self, network_data: Dict) -> Dict[str, Any]:
        """Generate AI insights for overall network conditions."""
        query_hash = await cache_service.generate_query_hash(
            "network_insights",
            {"timestamp": datetime.now().strftime("%Y%m%d%H")}  # Hourly cache
        )
        
        cached_result = await cache_service.get_ai_insight(query_hash)
        if cached_result:
            return cached_result
        
        if self.use_mock:
            insights = {
                "network_health": "stable",
                "routing_opportunities": "modérées",
                "fee_market_status": "équilibré",
                "growth_sectors": ["commerce", "épargne", "gaming"],
                "risk_factors": ["volatilité", "régulation"],
                "strategic_recommendations": [
                    "Concentrer sur les nœuds de commerce électronique",
                    "Optimiser les frais pour la compétitivité",
                    "Diversifier les connexions géographiques"
                ]
            }
        else:
            # Would implement real AI network analysis here
            insights = {"status": "not_implemented"}
        
        await cache_service.cache_ai_insight(query_hash, insights, ttl_hours=1)
        return insights
    
    async def get_analysis_stats(self) -> Dict[str, Any]:
        """Get AI analysis service statistics."""
        cache_stats = await cache_service.get_cache_stats()
        
        return {
            "ai_service_status": "mock" if self.use_mock else "active",
            "anthropic_configured": bool(self.anthropic_key),
            "cache_service": cache_stats,
            "available_features": [
                "enhanced_node_analysis",
                "strategic_insights", 
                "risk_assessment",
                "market_context"
            ]
        }

# Instance globale du service d'analyse AI
ai_analysis_service = AILightningAnalysis()