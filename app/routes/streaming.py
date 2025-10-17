"""
Streaming endpoints pour retourner les résultats progressivement
Améliore l'expérience utilisateur en montrant les résultats au fur et à mesure
"""

import logging
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.clients.sparkseer_client import SparkseerClient
from src.clients.anthropic_client import AnthropicClient
from src.clients.ollama_client import ollama_client
from src.utils.cache_manager import cache_manager
from app.services.rag_service import get_rag_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/streaming", tags=["Streaming"])

# Clients
sparkseer_client = SparkseerClient()
anthropic_client = AnthropicClient()


class StreamingStatus(BaseModel):
    """Status update pour le streaming"""
    type: str  # 'status', 'data', 'error', 'complete'
    message: str
    timestamp: str = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow().isoformat()
        super().__init__(**data)


async def stream_json_lines(data: Dict[str, Any]) -> str:
    """Format les données en JSON Lines (NDJSON)"""
    return json.dumps(data, ensure_ascii=False) + '\n'


async def stream_node_recommendations(
    pubkey: str,
    use_cache: bool = True
) -> AsyncGenerator[str, None]:
    """
    Stream les recommandations d'un nœud progressivement
    
    Args:
        pubkey: Public key du nœud
        use_cache: Utiliser le cache
        
    Yields:
        Lignes JSON (NDJSON) avec les données
    """
    try:
        # Étape 1: Envoyer un statut initial
        yield await stream_json_lines({
            'type': 'status',
            'message': 'Initialisation de l\'analyse...',
            'progress': 0
        })
        
        # Étape 2: Vérifier le cache
        if use_cache:
            yield await stream_json_lines({
                'type': 'status',
                'message': 'Vérification du cache...',
                'progress': 10
            })
            
            cached = await cache_manager.get(f"recommendations:{pubkey}:None:None")
            if cached:
                yield await stream_json_lines({
                    'type': 'cached_data',
                    'data': cached,
                    'progress': 100
                })
                
                yield await stream_json_lines({
                    'type': 'complete',
                    'message': 'Données en cache retournées',
                    'progress': 100
                })
                return
        
        # Étape 3: Récupérer les métriques de base
        yield await stream_json_lines({
            'type': 'status',
            'message': 'Récupération des métriques réseau...',
            'progress': 30
        })
        
        try:
            node_info = await sparkseer_client.get_node_info(pubkey)
            if node_info:
                yield await stream_json_lines({
                    'type': 'node_info',
                    'data': node_info,
                    'progress': 50
                })
        except Exception as e:
            logger.warning(f"Failed to get node info: {str(e)}")
            yield await stream_json_lines({
                'type': 'warning',
                'message': f'Métriques réseau indisponibles: {str(e)}',
                'progress': 50
            })
        
        # Étape 4: Récupérer les recommandations techniques
        yield await stream_json_lines({
            'type': 'status',
            'message': 'Génération des recommandations techniques...',
            'progress': 60
        })
        
        try:
            recommendations = await sparkseer_client.get_node_recommendations(pubkey)
            if recommendations:
                yield await stream_json_lines({
                    'type': 'technical_recommendations',
                    'data': recommendations,
                    'progress': 80
                })
        except Exception as e:
            logger.warning(f"Failed to get recommendations: {str(e)}")
            yield await stream_json_lines({
                'type': 'warning',
                'message': f'Recommandations techniques indisponibles: {str(e)}',
                'progress': 80
            })
        
        # Étape 5: Générer l'analyse IA (plus longue)
        yield await stream_json_lines({
            'type': 'status',
            'message': 'Génération de l\'analyse IA avancée...',
            'progress': 85
        })
        
        try:
            ai_analysis = await anthropic_client.generate_priority_actions(
                pubkey=pubkey,
                node_info=node_info if 'node_info' in locals() else {},
                recommendations=recommendations if 'recommendations' in locals() else {}
            )
            
            if ai_analysis and not ai_analysis.get('error'):
                yield await stream_json_lines({
                    'type': 'ai_recommendations',
                    'data': ai_analysis,
                    'progress': 95
                })
        except Exception as e:
            logger.error(f"Failed to generate AI analysis: {str(e)}")
            yield await stream_json_lines({
                'type': 'warning',
                'message': f'Analyse IA indisponible: {str(e)}',
                'progress': 95
            })
        
        # Étape finale: Complétion
        yield await stream_json_lines({
            'type': 'complete',
            'message': 'Analyse terminée',
            'progress': 100,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error streaming recommendations: {str(e)}")
        yield await stream_json_lines({
            'type': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })


async def stream_rag_query(
    query: str,
    max_results: int = 5
) -> AsyncGenerator[str, None]:
    """
    Stream une requête RAG progressivement
    
    Args:
        query: Requête textuelle
        max_results: Nombre de documents similaires
        
    Yields:
        Lignes JSON avec les résultats progressifs
    """
    try:
        # Initialisation
        yield await stream_json_lines({
            'type': 'status',
            'message': 'Initialisation du système RAG...',
            'progress': 0
        })
        
        # Obtenir le workflow RAG
        rag_workflow = await get_rag_workflow()
        
        # Génération de l'embedding
        yield await stream_json_lines({
            'type': 'status',
            'message': 'Génération de l\'embedding de requête...',
            'progress': 20
        })
        
        query_embedding = await ollama_client.embed(query)
        
        # Recherche de documents similaires
        yield await stream_json_lines({
            'type': 'status',
            'message': 'Recherche de documents similaires...',
            'progress': 40
        })
        
        import numpy as np
        similar_docs = rag_workflow.find_similar_documents(
            np.array(query_embedding),
            k=max_results
        )
        
        # Stream les documents trouvés un par un
        for i, (doc, score) in enumerate(similar_docs):
            progress = 40 + int((i + 1) / len(similar_docs) * 20)
            yield await stream_json_lines({
                'type': 'similar_document',
                'data': {
                    'content': doc[:200] + '...' if len(doc) > 200 else doc,
                    'similarity': float(score),
                    'rank': i + 1
                },
                'progress': progress
            })
            
            # Petit délai pour simuler le streaming progressif
            await asyncio.sleep(0.1)
        
        # Génération de la réponse
        yield await stream_json_lines({
            'type': 'status',
            'message': 'Génération de la réponse...',
            'progress': 70
        })
        
        result = await rag_workflow.process_query(query, n_results=max_results)
        
        # Stream la réponse
        yield await stream_json_lines({
            'type': 'answer',
            'data': {
                'answer': result.get('answer', ''),
                'confidence': result.get('confidence_score', 0.0),
                'sources_count': len(result.get('sources', []))
            },
            'progress': 95
        })
        
        # Complétion
        yield await stream_json_lines({
            'type': 'complete',
            'message': 'Requête RAG terminée',
            'progress': 100
        })
        
    except Exception as e:
        logger.error(f"Error streaming RAG query: {str(e)}")
        yield await stream_json_lines({
            'type': 'error',
            'message': str(e)
        })


# ============================================================================
# ENDPOINTS STREAMING
# ============================================================================

@router.get("/node/{pubkey}/recommendations")
async def stream_node_recommendations_endpoint(
    pubkey: str,
    use_cache: bool = Query(default=True),
    authorization: Optional[str] = Header(None)
):
    """
    Stream les recommandations d'un nœud progressivement
    
    Returns un stream NDJSON (Newline Delimited JSON)
    """
    # Validation
    if len(pubkey) != 66:
        raise HTTPException(status_code=400, detail="Invalid pubkey format")
    
    return StreamingResponse(
        stream_node_recommendations(pubkey, use_cache),
        media_type="application/x-ndjson"
    )


@router.post("/rag/query")
async def stream_rag_query_endpoint(
    query: str = Query(..., description="Requête RAG"),
    max_results: int = Query(default=5, ge=1, le=20),
    authorization: Optional[str] = Header(None)
):
    """
    Stream une requête RAG progressivement
    
    Returns un stream NDJSON
    """
    if not query or len(query) < 3:
        raise HTTPException(status_code=400, detail="Query too short")
    
    return StreamingResponse(
        stream_rag_query(query, max_results),
        media_type="application/x-ndjson"
    )


@router.get("/node/{pubkey}/analysis")
async def stream_node_analysis_endpoint(
    pubkey: str,
    include_ai: bool = Query(default=True),
    authorization: Optional[str] = Header(None)
):
    """
    Stream une analyse complète de nœud progressivement
    """
    if len(pubkey) != 66:
        raise HTTPException(status_code=400, detail="Invalid pubkey format")
    
    async def generate_analysis():
        try:
            # Étape 1: Info de base
            yield await stream_json_lines({
                'type': 'status',
                'message': 'Récupération des informations de base...',
                'progress': 0
            })
            
            node_info = await sparkseer_client.get_node_info(pubkey)
            if node_info:
                yield await stream_json_lines({
                    'type': 'basic_info',
                    'data': node_info,
                    'progress': 25
                })
            
            # Étape 2: Métriques réseau
            yield await stream_json_lines({
                'type': 'status',
                'message': 'Analyse de la position réseau...',
                'progress': 50
            })
            
            # Simuler récupération de métriques avancées
            await asyncio.sleep(0.5)
            
            # Étape 3: Recommandations
            yield await stream_json_lines({
                'type': 'status',
                'message': 'Génération des recommandations...',
                'progress': 75
            })
            
            recommendations = await sparkseer_client.get_node_recommendations(pubkey)
            if recommendations:
                yield await stream_json_lines({
                    'type': 'recommendations',
                    'data': recommendations,
                    'progress': 90
                })
            
            # Étape 4: Analyse IA (optionnelle)
            if include_ai:
                yield await stream_json_lines({
                    'type': 'status',
                    'message': 'Analyse IA en cours...',
                    'progress': 95
                })
                
                try:
                    ai_analysis = await anthropic_client.analyze_node_performance(
                        pubkey=pubkey,
                        metrics=node_info.get('metrics', {}) if node_info else {}
                    )
                    
                    yield await stream_json_lines({
                        'type': 'ai_analysis',
                        'data': ai_analysis,
                        'progress': 98
                    })
                except Exception as e:
                    logger.warning(f"AI analysis failed: {str(e)}")
            
            # Complétion
            yield await stream_json_lines({
                'type': 'complete',
                'message': 'Analyse complète terminée',
                'progress': 100
            })
            
        except Exception as e:
            logger.error(f"Error in analysis stream: {str(e)}")
            yield await stream_json_lines({
                'type': 'error',
                'message': str(e)
            })
    
    return StreamingResponse(
        generate_analysis(),
        media_type="application/x-ndjson"
    )


@router.get("/health")
async def streaming_health():
    """Health check pour les endpoints streaming"""
    return {
        "status": "healthy",
        "streaming_available": True,
        "supported_formats": ["ndjson"],
        "endpoints": [
            "/streaming/node/{pubkey}/recommendations",
            "/streaming/node/{pubkey}/analysis",
            "/streaming/rag/query"
        ]
    }


logger.info("Streaming endpoints module loaded")

