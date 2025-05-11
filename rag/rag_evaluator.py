import logging
import asyncio
import numpy as np
from typing import List, Dict, Any, Tuple, Optional, Union
from datetime import datetime

# Import RAGAS pour l'évaluation automatique
try:
    from ragas.metrics import faithfulness, answer_relevancy, context_relevancy
    from ragas.metrics.critique import harmfulness
    RAGAS_AVAILABLE = True
except ImportError:
    logging.warning("RAGAS non disponible. Installation requise pour l'évaluation automatique.")
    RAGAS_AVAILABLE = False

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGEvaluator:
    """
    Système d'évaluation automatique pour les réponses du RAG en utilisant RAGAS.
    Mesure la fidélité, la pertinence de la réponse, la pertinence du contexte
    et l'absence de contenu nuisible.
    """
    
    def __init__(self):
        if not RAGAS_AVAILABLE:
            logger.warning("RAGAS n'est pas disponible. L'évaluation ne fonctionnera pas correctement.")
            
        self.metrics = {}
        
        if RAGAS_AVAILABLE:
            self.metrics = {
                "faithfulness": faithfulness,
                "answer_relevancy": answer_relevancy,
                "context_relevancy": context_relevancy,
                "harmfulness": harmfulness
            }
        
        # Seuils pour l'interprétation des scores
        self.thresholds = {
            "excellent": 0.85,
            "good": 0.7,
            "acceptable": 0.5,
            "poor": 0.3
        }
        
        # Historique des évaluations
        self.evaluation_history = []
    
    async def evaluate(self, query: str, response: str, contexts: List[str]) -> Dict[str, float]:
        """
        Évalue la réponse du RAG en utilisant plusieurs métriques RAGAS.
        
        Args:
            query: La requête utilisateur
            response: La réponse générée
            contexts: Les contextes utilisés pour générer la réponse
            
        Returns:
            Dictionnaire contenant les scores pour chaque métrique
        """
        if not RAGAS_AVAILABLE:
            logger.error("Impossible d'évaluer: RAGAS n'est pas disponible")
            return self._get_fallback_scores()
            
        try:
            logger.info(f"Évaluation de la requête: {query[:50]}...")
            results = {}
            
            # Préparer les données au format requis par RAGAS
            combined_contexts = "\n\n".join(contexts)
            
            # Évaluer la pertinence du contexte
            context_score = await self.metrics["context_relevancy"].ascore(
                contexts=[[combined_contexts]], questions=[query]
            )
            
            # Évaluer la pertinence de la réponse
            answer_score = await self.metrics["answer_relevancy"].ascore(
                answers=[response], questions=[query]
            )
            
            # Évaluer la fidélité (groundedness)
            faithfulness_score = await self.metrics["faithfulness"].ascore(
                answers=[response], contexts=[[combined_contexts]]
            )
            
            # Vérifier l'absence de contenu nuisible
            harmfulness_score = await self.metrics["harmfulness"].ascore(
                answers=[response]
            )
            
            # Extraire les valeurs numériques des scores
            results = {
                "context_relevancy": float(context_score.iloc[0]["context_relevancy"]),
                "answer_relevancy": float(answer_score.iloc[0]["answer_relevancy"]),
                "faithfulness": float(faithfulness_score.iloc[0]["faithfulness"]),
                "harmfulness": 1.0 - float(harmfulness_score.iloc[0]["harmfulness"]), # Inverser le score pour l'uniformité
                "timestamp": datetime.now().isoformat()
            }
            
            # Calculer le score composite
            results["composite_score"] = (
                results["context_relevancy"] + 
                results["answer_relevancy"] + 
                results["faithfulness"] +
                results["harmfulness"]
            ) / 4.0
            
            # Ajouter l'évaluation à l'historique
            eval_record = {
                "query": query,
                "response_snippet": response[:100] + "..." if len(response) > 100 else response,
                "scores": results.copy(),
                "timestamp": datetime.now().isoformat()
            }
            self.evaluation_history.append(eval_record)
            
            logger.info(f"Évaluation terminée. Score composite: {results['composite_score']:.2f}")
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors de l'évaluation: {str(e)}")
            return self._get_fallback_scores()
    
    def _get_fallback_scores(self) -> Dict[str, float]:
        """Retourne des scores par défaut en cas d'erreur."""
        return {
            "context_relevancy": 0.0,
            "answer_relevancy": 0.0,
            "faithfulness": 0.0,
            "harmfulness": 0.0,
            "composite_score": 0.0,
            "error": True,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_quality_assessment(self, score: float) -> str:
        """
        Convertit un score numérique en évaluation qualitative.
        
        Args:
            score: Score numérique entre 0 et 1
            
        Returns:
            Évaluation qualitative (excellent, bon, acceptable, médiocre)
        """
        if score >= self.thresholds["excellent"]:
            return "excellent"
        elif score >= self.thresholds["good"]:
            return "bon"
        elif score >= self.thresholds["acceptable"]:
            return "acceptable"
        elif score >= self.thresholds["poor"]:
            return "médiocre"
        else:
            return "mauvais"
    
    def get_weakest_aspect(self, scores: Dict[str, float]) -> Tuple[str, float]:
        """
        Identifie l'aspect le plus faible de la réponse.
        
        Args:
            scores: Dictionnaire de scores
            
        Returns:
            Tuple contenant (métrique_la_plus_faible, score)
        """
        # Exclure les métriques qui ne sont pas des aspects de qualité
        relevant_scores = {k: v for k, v in scores.items() 
                         if k in ["context_relevancy", "answer_relevancy", "faithfulness", "harmfulness"]}
        
        if not relevant_scores:
            return ("inconnu", 0.0)
            
        weakest = min(relevant_scores.items(), key=lambda x: x[1])
        return weakest
    
    def get_evaluation_summary(self, n_last: int = 10) -> Dict[str, Any]:
        """
        Génère un résumé des dernières évaluations.
        
        Args:
            n_last: Nombre d'évaluations récentes à considérer
            
        Returns:
            Résumé statistique des évaluations récentes
        """
        if not self.evaluation_history:
            return {"message": "Aucune évaluation disponible"}
        
        # Prendre les n dernières évaluations
        recent_evals = self.evaluation_history[-n_last:] if len(self.evaluation_history) >= n_last else self.evaluation_history
        
        # Calculer les moyennes pour chaque métrique
        avg_scores = {}
        for metric in ["context_relevancy", "answer_relevancy", "faithfulness", "harmfulness", "composite_score"]:
            values = [eval_record["scores"].get(metric, 0) for eval_record in recent_evals]
            avg_scores[metric] = sum(values) / len(values) if values else 0
        
        # Identifier les tendances (amélioration ou dégradation)
        trends = {}
        if len(recent_evals) >= 3:
            # Diviser en première et seconde moitié
            mid_point = len(recent_evals) // 2
            first_half = recent_evals[:mid_point]
            second_half = recent_evals[-mid_point:]
            
            for metric in ["composite_score"]:
                first_avg = sum(e["scores"].get(metric, 0) for e in first_half) / len(first_half) if first_half else 0
                second_avg = sum(e["scores"].get(metric, 0) for e in second_half) / len(second_half) if second_half else 0
                
                if second_avg > first_avg * 1.05:  # 5% d'amélioration
                    trends[metric] = "amélioration"
                elif second_avg < first_avg * 0.95:  # 5% de dégradation
                    trends[metric] = "dégradation"
                else:
                    trends[metric] = "stable"
        
        # Préparer le résumé
        summary = {
            "period": {
                "start": recent_evals[0]["timestamp"] if recent_evals else None,
                "end": recent_evals[-1]["timestamp"] if recent_evals else None,
                "count": len(recent_evals)
            },
            "average_scores": avg_scores,
            "quality_assessment": self.get_quality_assessment(avg_scores["composite_score"]),
            "trends": trends,
            "weakest_aspect": self.get_weakest_aspect(avg_scores)
        }
        
        return summary

# Fonction utilitaire pour faciliter l'utilisation dans d'autres modules
async def evaluate_rag_response(query: str, response: str, contexts: List[str]) -> Dict[str, float]:
    """
    Évalue une réponse RAG avec RAGAS.
    
    Args:
        query: Requête utilisateur
        response: Réponse générée
        contexts: Contextes utilisés
        
    Returns:
        Scores d'évaluation
    """
    evaluator = RAGEvaluator()
    return await evaluator.evaluate(query, response, contexts) 