from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from src.lightning_validator import LightningValidator
from src.lightning_optimizer import LightningOptimizer
from src.redis_operations import RedisOperations
import os
from src.hypothesis_manager import HypothesisManager
from src.lnbits_operations import LNbitsOperations
from src.mongo_operations import MongoOperations
from datetime import datetime

# Création du router
router = APIRouter(
    prefix="/lightning",
    tags=["Lightning"],
    responses={
        401: {"description": "Non authentifié"},
        403: {"description": "Accès refusé"},
        429: {"description": "Trop de requêtes"},
        500: {"description": "Erreur serveur"}
    }
)

# Configuration Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialisation des composants
redis_ops = RedisOperations(redis_url=REDIS_URL)
lightning_validator = LightningValidator(redis_ops)
lightning_optimizer = LightningOptimizer(redis_ops)

# Initialisation des composants
lnbits_ops = LNbitsOperations(
    api_url=os.getenv("LNBITS_API_URL", "https://testnet.lnbits.com"),
    admin_key=os.getenv("LNBITS_ADMIN_KEY", ""),
    invoice_key=os.getenv("LNBITS_INVOICE_KEY", "")
)
mongo_ops = MongoOperations()
hypothesis_manager = HypothesisManager(mongo_ops, lnbits_ops)

class ValidationResponse(BaseModel):
    """
    Modèle de réponse pour la validation
    """
    is_valid: bool = Field(..., description="Indique si la validation est réussie")
    message: str = Field(..., description="Message détaillant le résultat de la validation")
    details: Optional[Dict] = Field(None, description="Détails supplémentaires sur la validation")

class NodeStats(BaseModel):
    """
    Modèle pour les statistiques d'un nœud
    """
    node_id: str = Field(..., description="Identifiant du nœud")
    total_channels: int = Field(..., description="Nombre total de canaux")
    total_capacity: float = Field(..., description="Capacité totale en BTC")
    average_fee_rate: float = Field(..., description="Taux de frais moyen en ppm")
    uptime: float = Field(..., description="Temps de fonctionnement en heures")
    last_updated: str = Field(..., description="Date de dernière mise à jour")

class NetworkSummary(BaseModel):
    """
    Modèle pour le résumé du réseau
    """
    total_nodes: int = Field(..., description="Nombre total de nœuds")
    total_channels: int = Field(..., description="Nombre total de canaux")
    total_capacity: float = Field(..., description="Capacité totale du réseau en BTC")
    average_channels_per_node: float = Field(..., description="Nombre moyen de canaux par nœud")
    average_capacity_per_channel: float = Field(..., description="Capacité moyenne par canal en BTC")

# Nouveaux modèles pour les hypothèses
class FeeChangeRequest(BaseModel):
    """Modèle pour la création d'une hypothèse de changement de frais"""
    node_id: str = Field(..., description="Identifiant du nœud")
    channel_id: str = Field(..., description="Identifiant du canal")
    new_base_fee: int = Field(..., description="Nouveaux frais de base (msats)")
    new_fee_rate: int = Field(..., description="Nouveau taux de frais (ppm)")
    evaluation_period_days: int = Field(7, description="Période d'évaluation en jours")

class ChannelChangeRequest(BaseModel):
    """Modèle pour la création d'une hypothèse de configuration de canaux"""
    node_id: str = Field(..., description="Identifiant du nœud")
    proposed_changes: Dict[str, Any] = Field(..., description="Changements proposés")
    evaluation_period_days: int = Field(30, description="Période d'évaluation en jours")

class HypothesisResponse(BaseModel):
    """Modèle pour la réponse des hypothèses"""
    hypothesis_id: str = Field(..., description="Identifiant de l'hypothèse")
    message: str = Field(..., description="Message de succès ou d'erreur")
    details: Optional[Dict[str, Any]] = Field(None, description="Détails supplémentaires")

@router.post("/validate-key", response_model=ValidationResponse)
async def validate_lightning_key(pubkey: str = Query(..., description="Clé publique Lightning à valider")):
    """
    Valide une clé publique Lightning.
    
    Cette endpoint vérifie si une clé publique Lightning est valide
    et retourne des informations détaillées sur la validation.
    """
    try:
        result = await lightning_validator.validate_pubkey(pubkey)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate-node", response_model=ValidationResponse)
async def validate_lightning_node(node_id: str = Query(..., description="ID du nœud Lightning à valider")):
    """
    Valide un nœud Lightning.
    
    Cette endpoint vérifie si un nœud Lightning est valide et actif
    sur le réseau, et retourne des informations détaillées sur la validation.
    """
    try:
        result = await lightning_validator.validate_node(node_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/node/{node_id}/stats", response_model=NodeStats)
async def get_node_stats(node_id: str):
    """
    Récupère les statistiques d'un nœud Lightning.
    
    Cette endpoint fournit des statistiques détaillées sur un nœud Lightning,
    incluant le nombre de canaux, la capacité totale, et les taux de frais.
    """
    try:
        stats = await lightning_optimizer.get_node_stats(node_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/node/{node_id}/history")
async def get_node_history(
    node_id: str,
    limit: int = Query(10, description="Nombre maximum d'entrées à retourner", ge=1, le=100)
):
    """
    Récupère l'historique d'un nœud Lightning.
    
    Cette endpoint fournit l'historique des modifications et événements
    importants pour un nœud Lightning spécifique.
    """
    try:
        history = await lightning_optimizer.get_node_history(node_id, limit)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/network-summary", response_model=NetworkSummary)
async def get_network_summary():
    """
    Récupère un résumé de l'état du réseau Lightning.
    
    Cette endpoint fournit des statistiques globales sur l'état actuel
    du réseau Lightning, incluant le nombre de nœuds, de canaux et la capacité totale.
    """
    try:
        summary = await lightning_optimizer.get_network_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/centralities")
async def get_network_centralities(
    metric: str = Query("betweenness", description="Métrique de centralité à calculer", enum=["betweenness", "closeness", "degree"])
):
    """
    Calcule les centralités des nœuds du réseau.
    
    Cette endpoint calcule différentes métriques de centralité pour les nœuds
    du réseau Lightning, permettant d'identifier les nœuds les plus importants.
    """
    try:
        centralities = await lightning_optimizer.calculate_centralities(metric)
        return centralities
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/node/{node_id}/optimize")
async def optimize_node(
    node_id: str,
    max_channels: Optional[int] = Query(100, description="Nombre maximum de canaux", ge=1, le=1000),
    min_capacity: Optional[float] = Query(0.1, description="Capacité minimale par canal en BTC", ge=0.01, le=1.0)
):
    """
    Optimise la configuration d'un nœud Lightning.
    
    Cette endpoint analyse et suggère des optimisations pour un nœud Lightning,
    en se basant sur son état actuel et les tendances du réseau.
    """
    try:
        optimization = await lightning_optimizer.optimize_node(
            node_id,
            max_channels=max_channels,
            min_capacity=min_capacity
        )
        return {
            "status": "success",
            "optimization": optimization
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hypotheses/fees", response_model=HypothesisResponse, 
             summary="Crée une hypothèse de changement de frais",
             description="""
             Crée une nouvelle hypothèse de changement de frais pour un canal spécifique.
             
             Cette endpoint permet de proposer un changement dans la structure des frais d'un canal
             et suivre son impact sur les performances du canal. L'hypothèse compare les statistiques
             avant et après le changement pour déterminer si le changement est bénéfique.
             
             **Exemples d'utilisation:**
             
             ```
             # Créer une hypothèse pour doubler le taux de frais
             POST /lightning/hypotheses/fees
             {
                 "node_id": "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
                 "channel_id": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                 "new_base_fee": 1000,
                 "new_fee_rate": 200,
                 "evaluation_period_days": 7
             }
             ```
             """)
async def create_fee_hypothesis(request: FeeChangeRequest):
    """
    Crée une hypothèse de changement de frais pour un canal spécifique.
    """
    try:
        hypothesis = await hypothesis_manager.create_fee_hypothesis(
            node_id=request.node_id,
            channel_id=request.channel_id,
            new_base_fee=request.new_base_fee,
            new_fee_rate=request.new_fee_rate,
            evaluation_period_days=request.evaluation_period_days
        )
        
        return HypothesisResponse(
            hypothesis_id=hypothesis.hypothesis_id,
            message="Hypothèse de changement de frais créée avec succès",
            details={
                "node_id": hypothesis.node_id,
                "channel_id": hypothesis.channel_id,
                "before_fee_rate": hypothesis.before_fee_rate,
                "new_fee_rate": hypothesis.new_fee_rate
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hypotheses/fees/{hypothesis_id}/apply", response_model=HypothesisResponse,
             summary="Applique une hypothèse de changement de frais",
             description="""
             Applique les changements proposés dans une hypothèse de frais.
             
             Cette endpoint met à jour la structure des frais du canal concerné
             selon les paramètres définis dans l'hypothèse. Une fois appliquée,
             l'hypothèse commence sa période d'évaluation.
             
             **Exemples d'utilisation:**
             
             ```
             # Appliquer une hypothèse existante
             POST /lightning/hypotheses/fees/550e8400-e29b-41d4-a716-446655440000/apply
             ```
             """)
async def apply_fee_hypothesis(hypothesis_id: str):
    """
    Applique une hypothèse de changement de frais.
    """
    try:
        success = await hypothesis_manager.apply_fee_hypothesis(hypothesis_id)
        
        if success:
            return HypothesisResponse(
                hypothesis_id=hypothesis_id,
                message="Hypothèse de changement de frais appliquée avec succès",
                details={"applied_at": datetime.now().isoformat()}
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Erreur lors de l'application de l'hypothèse"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hypotheses/fees/{hypothesis_id}/evaluate", 
             summary="Évalue une hypothèse de changement de frais",
             description="""
             Évalue les résultats d'une hypothèse de changement de frais.
             
             Cette endpoint analyse les performances du canal après la période d'évaluation
             définie dans l'hypothèse. Elle compare les statistiques avant et après le changement
             pour déterminer si l'hypothèse est validée et fournit une conclusion détaillée.
             
             **Exemples d'utilisation:**
             
             ```
             # Évaluer une hypothèse existante
             GET /lightning/hypotheses/fees/550e8400-e29b-41d4-a716-446655440000/evaluate
             ```
             """)
async def evaluate_fee_hypothesis(hypothesis_id: str):
    """
    Évalue une hypothèse de changement de frais.
    """
    try:
        result = await hypothesis_manager.evaluate_fee_hypothesis(hypothesis_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hypotheses/channels", response_model=HypothesisResponse,
             summary="Crée une hypothèse de configuration de canaux",
             description="""
             Crée une nouvelle hypothèse de configuration de canaux pour un nœud spécifique.
             
             Cette endpoint permet de proposer des changements dans la configuration des canaux
             d'un nœud, comme l'ouverture de nouveaux canaux, la fermeture de canaux existants
             ou le rééquilibrage. L'hypothèse compare les performances avant et après les changements.
             
             **Exemples d'utilisation:**
             
             ```
             # Créer une hypothèse pour ajouter deux canaux et en fermer un
             POST /lightning/hypotheses/channels
             {
                 "node_id": "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
                 "proposed_changes": {
                     "add_channels": [
                         {"target_node": "02fc8e97419338c9475c6c06bd8f3ee5c917352809a4024db350a48497036eec86", "capacity": 5000000},
                         {"target_node": "0260fab633066d6f9a0ce7c942cb8edf72c254e491232c48867518f8b8a5a559ec", "capacity": 3000000}
                     ],
                     "close_channels": [
                         {"channel_id": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"}
                     ],
                     "rebalance": true
                 },
                 "evaluation_period_days": 30
             }
             ```
             """)
async def create_channel_hypothesis(request: ChannelChangeRequest):
    """
    Crée une hypothèse de configuration de canaux pour un nœud spécifique.
    """
    try:
        hypothesis = await hypothesis_manager.create_channel_hypothesis(
            node_id=request.node_id,
            proposed_changes=request.proposed_changes,
            evaluation_period_days=request.evaluation_period_days
        )
        
        return HypothesisResponse(
            hypothesis_id=hypothesis.hypothesis_id,
            message="Hypothèse de configuration de canaux créée avec succès",
            details={
                "node_id": hypothesis.node_id,
                "proposed_changes": hypothesis.proposed_changes
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hypotheses/channels/{hypothesis_id}/apply", response_model=HypothesisResponse,
             summary="Applique une hypothèse de configuration de canaux",
             description="""
             Applique les changements proposés dans une hypothèse de configuration de canaux.
             
             Cette endpoint exécute les changements définis dans l'hypothèse, comme l'ouverture
             ou la fermeture de canaux, ou le rééquilibrage. Une fois appliquée, l'hypothèse
             commence sa période d'évaluation.
             
             **Exemples d'utilisation:**
             
             ```
             # Appliquer une hypothèse existante
             POST /lightning/hypotheses/channels/550e8400-e29b-41d4-a716-446655440000/apply
             ```
             """)
async def apply_channel_hypothesis(hypothesis_id: str):
    """
    Applique une hypothèse de configuration de canaux.
    """
    try:
        success = await hypothesis_manager.apply_channel_hypothesis(hypothesis_id)
        
        if success:
            return HypothesisResponse(
                hypothesis_id=hypothesis_id,
                message="Hypothèse de configuration de canaux appliquée avec succès",
                details={"applied_at": datetime.now().isoformat()}
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Erreur lors de l'application de l'hypothèse"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hypotheses/channels/{hypothesis_id}/evaluate",
             summary="Évalue une hypothèse de configuration de canaux",
             description="""
             Évalue les résultats d'une hypothèse de configuration de canaux.
             
             Cette endpoint analyse les performances du nœud après la période d'évaluation
             définie dans l'hypothèse. Elle compare la configuration et les performances
             avant et après les changements pour déterminer si l'hypothèse est validée
             et fournit une conclusion détaillée.
             
             **Exemples d'utilisation:**
             
             ```
             # Évaluer une hypothèse existante
             GET /lightning/hypotheses/channels/550e8400-e29b-41d4-a716-446655440000/evaluate
             ```
             """)
async def evaluate_channel_hypothesis(hypothesis_id: str):
    """
    Évalue une hypothèse de configuration de canaux.
    """
    try:
        result = await hypothesis_manager.evaluate_channel_hypothesis(hypothesis_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hypotheses/fees/node/{node_id}",
             summary="Liste les hypothèses de frais pour un nœud",
             description="""
             Récupère la liste des hypothèses de changement de frais pour un nœud spécifique.
             
             Cette endpoint retourne toutes les hypothèses de frais associées à un nœud donné,
             avec leur statut actuel et leurs résultats s'ils sont disponibles.
             
             **Exemples d'utilisation:**
             
             ```
             # Lister les hypothèses pour un nœud
             GET /lightning/hypotheses/fees/node/03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f
             
             # Lister uniquement les hypothèses validées
             GET /lightning/hypotheses/fees/node/03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f?only_validated=true
             ```
             """)
async def list_fee_hypotheses(
    node_id: str, 
    limit: int = Query(10, description="Nombre maximum d'hypothèses à retourner", ge=1, le=100),
    only_validated: bool = Query(False, description="Ne retourner que les hypothèses validées")
):
    """
    Liste les hypothèses de changement de frais pour un nœud spécifique.
    """
    try:
        hypotheses = await mongo_ops.get_fee_hypotheses_for_node(
            node_id=node_id,
            limit=limit,
            only_validated=only_validated
        )
        
        # Conversion en dictionnaires pour la réponse JSON
        result = []
        for h in hypotheses:
            h_dict = h.model_dump()
            
            # Statut de l'hypothèse
            if h.is_validated is not None:
                h_dict["status"] = "validée" if h.is_validated else "non validée"
            elif h.change_applied_at:
                h_dict["status"] = "en évaluation"
            else:
                h_dict["status"] = "créée"
                
            result.append(h_dict)
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hypotheses/channels/node/{node_id}",
             summary="Liste les hypothèses de canaux pour un nœud",
             description="""
             Récupère la liste des hypothèses de configuration de canaux pour un nœud spécifique.
             
             Cette endpoint retourne toutes les hypothèses de configuration de canaux associées
             à un nœud donné, avec leur statut actuel et leurs résultats s'ils sont disponibles.
             
             **Exemples d'utilisation:**
             
             ```
             # Lister les hypothèses pour un nœud
             GET /lightning/hypotheses/channels/node/03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f
             
             # Lister uniquement les hypothèses validées
             GET /lightning/hypotheses/channels/node/03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f?only_validated=true
             ```
             """)
async def list_channel_hypotheses(
    node_id: str, 
    limit: int = Query(10, description="Nombre maximum d'hypothèses à retourner", ge=1, le=100),
    only_validated: bool = Query(False, description="Ne retourner que les hypothèses validées")
):
    """
    Liste les hypothèses de configuration de canaux pour un nœud spécifique.
    """
    try:
        hypotheses = await mongo_ops.get_channel_hypotheses_for_node(
            node_id=node_id,
            limit=limit,
            only_validated=only_validated
        )
        
        # Conversion en dictionnaires pour la réponse JSON
        result = []
        for h in hypotheses:
            h_dict = h.model_dump()
            
            # Statut de l'hypothèse
            if h.is_validated is not None:
                h_dict["status"] = "validée" if h.is_validated else "non validée"
            elif h.changes_applied_at:
                h_dict["status"] = "en évaluation"
            else:
                h_dict["status"] = "créée"
                
            result.append(h_dict)
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 