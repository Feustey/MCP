"""
API Endpoints pour le système Token4Good (T4G)
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from token4good import (
    T4GService, T4GMarketplace, T4GRewardsEngine,
    T4GTokenAction, ServiceCategory, UserLevel
)
from token4good.models import (
    T4GTransaction, MentoringSession, MarketplaceService, 
    ServiceBooking, UserProfile
)

# Import pour les endpoints Bitcoin/LND
try:
    from app.services.lnbits import LNbitsService
    LNbitsServiceAvailable = True
except ImportError:
    LNbitsServiceAvailable = False
    logger.warning("LNbitsService non disponible - endpoints Bitcoin/LND désactivés")

# Initialisation des services T4G
t4g_service = T4GService()
t4g_marketplace = T4GMarketplace(t4g_service)
t4g_rewards = T4GRewardsEngine(t4g_service)

router = APIRouter(prefix="/api/v1/token4good", tags=["Token4Good"])


# ==================== MODÈLES DE REQUÊTE ====================

class CreateUserRequest(BaseModel):
    user_id: str
    username: str
    email: str
    skills: Optional[List[str]] = []


class AwardTokensRequest(BaseModel):
    user_id: str
    action_type: T4GTokenAction
    tokens: int
    description: str
    metadata: Optional[Dict] = {}
    impact_score: Optional[float] = 1.0


class CreateMentoringSessionRequest(BaseModel):
    mentor_id: str
    mentee_id: str
    topic: str
    category: str
    duration_minutes: int


class CompleteMentoringSessionRequest(BaseModel):
    session_id: str
    feedback: Optional[Dict] = {}


class CreateServiceRequest(BaseModel):
    provider_id: str
    name: str
    description: str
    category: ServiceCategory
    token_cost: int
    estimated_duration: str
    requirements: Optional[List[str]] = []
    tags: Optional[List[str]] = []


class BookServiceRequest(BaseModel):
    client_id: str
    service_id: str
    scheduled_at: Optional[datetime] = None
    notes: Optional[str] = None


class CompleteBookingRequest(BaseModel):
    booking_id: str
    feedback: Optional[Dict] = {}


class SearchServicesRequest(BaseModel):
    category: Optional[ServiceCategory] = None
    max_cost: Optional[int] = None
    tags: Optional[List[str]] = None
    provider_level: Optional[str] = None


# ==================== ENDPOINTS UTILISATEURS ====================

@router.post("/users", response_model=UserProfile)
async def create_user_profile(request: CreateUserRequest):
    """Crée un nouveau profil utilisateur T4G"""
    try:
        profile = await t4g_service.create_user_profile(
            user_id=request.user_id,
            username=request.username,
            email=request.email,
            skills=request.skills
        )
        return profile
    except Exception as e:
        logger.error(f"Erreur création profil: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/{user_id}", response_model=UserProfile)
async def get_user_profile(user_id: str):
    """Récupère le profil d'un utilisateur"""
    if user_id not in t4g_service.users:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    return t4g_service.users[user_id]


@router.get("/users/{user_id}/statistics")
async def get_user_statistics(user_id: str):
    """Récupère les statistiques complètes d'un utilisateur"""
    try:
        stats = await t4g_service.get_user_statistics(user_id)
        return stats
    except Exception as e:
        logger.error(f"Erreur récupération stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/opportunities")
async def get_earning_opportunities(user_id: str):
    """Suggère des opportunités de gains pour un utilisateur"""
    try:
        opportunities = await t4g_rewards.suggest_earning_opportunities(user_id)
        return {"opportunities": opportunities}
    except Exception as e:
        logger.error(f"Erreur opportunités: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaderboard")
async def get_community_leaderboard(limit: int = 10):
    """Récupère le classement de la communauté"""
    try:
        leaderboard = await t4g_service.get_leaderboard(limit)
        return {"leaderboard": leaderboard}
    except Exception as e:
        logger.error(f"Erreur leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS TOKENS ====================

@router.post("/tokens/award", response_model=T4GTransaction)
async def award_tokens(request: AwardTokensRequest, background_tasks: BackgroundTasks):
    """Attribue des tokens T4G à un utilisateur"""
    try:
        # Calcul de récompense dynamique
        reward_info = await t4g_rewards.calculate_dynamic_reward(
            user_id=request.user_id,
            action_type=request.action_type,
            context=request.metadata
        )
        
        # Attribution des tokens
        transaction = await t4g_service.award_tokens(
            user_id=request.user_id,
            action_type=request.action_type,
            tokens=reward_info["final_tokens"],
            description=request.description,
            metadata=request.metadata,
            impact_score=request.impact_score
        )
        
        # Vérification des achievements en arrière-plan
        background_tasks.add_task(
            t4g_rewards.process_achievement_unlocks, 
            request.user_id
        )
        
        return transaction
    except Exception as e:
        logger.error(f"Erreur attribution tokens: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tokens/{user_id}/balance")
async def get_user_balance(user_id: str):
    """Récupère le solde de tokens d'un utilisateur"""
    if user_id not in t4g_service.users:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    user = t4g_service.users[user_id]
    return {
        "user_id": user_id,
        "total_earned": user.total_tokens_earned,
        "total_spent": user.total_tokens_spent,
        "available_balance": user.available_balance,
        "user_level": user.user_level.value
    }


@router.get("/tokens/{user_id}/transactions")
async def get_user_transactions(user_id: str, limit: int = 50):
    """Récupère les transactions d'un utilisateur"""
    user_transactions = [
        t for t in t4g_service.transactions.values() 
        if t.user_id == user_id
    ]
    
    # Tri par date décroissante
    user_transactions.sort(key=lambda x: x.timestamp, reverse=True)
    
    return {
        "transactions": user_transactions[:limit],
        "total_count": len(user_transactions)
    }


# ==================== ENDPOINTS MENTORING ====================

@router.post("/mentoring/sessions", response_model=MentoringSession)
async def create_mentoring_session(request: CreateMentoringSessionRequest):
    """Crée une nouvelle session de mentoring"""
    try:
        session = await t4g_service.create_mentoring_session(
            mentor_id=request.mentor_id,
            mentee_id=request.mentee_id,
            topic=request.topic,
            category=request.category,
            duration_minutes=request.duration_minutes
        )
        return session
    except Exception as e:
        logger.error(f"Erreur création session mentoring: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mentoring/sessions/complete")
async def complete_mentoring_session(request: CompleteMentoringSessionRequest, 
                                   background_tasks: BackgroundTasks):
    """Finalise une session de mentoring"""
    try:
        success = await t4g_service.complete_mentoring_session(
            session_id=request.session_id,
            feedback=request.feedback
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Session non trouvée")
        
        # Vérification des achievements pour le mentor
        session = t4g_service.mentoring_sessions[request.session_id]
        background_tasks.add_task(
            t4g_rewards.process_achievement_unlocks,
            session.mentor_id
        )
        
        return {"success": True, "message": "Session complétée avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur completion session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mentoring/sessions/{user_id}")
async def get_user_mentoring_sessions(user_id: str, as_mentor: bool = True):
    """Récupère les sessions de mentoring d'un utilisateur"""
    if as_mentor:
        sessions = [s for s in t4g_service.mentoring_sessions.values() 
                   if s.mentor_id == user_id]
    else:
        sessions = [s for s in t4g_service.mentoring_sessions.values()
                   if s.mentee_id == user_id]
    
    # Tri par date de création décroissante
    sessions.sort(key=lambda x: x.scheduled_at, reverse=True)
    
    return {"sessions": sessions}


# ==================== ENDPOINTS MARKETPLACE ====================

@router.post("/marketplace/services", response_model=MarketplaceService)
async def create_marketplace_service(request: CreateServiceRequest):
    """Crée un nouveau service dans la marketplace"""
    try:
        service = await t4g_marketplace.create_service(
            provider_id=request.provider_id,
            name=request.name,
            description=request.description,
            category=request.category,
            token_cost=request.token_cost,
            estimated_duration=request.estimated_duration,
            requirements=request.requirements,
            tags=request.tags
        )
        return service
    except Exception as e:
        logger.error(f"Erreur création service: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/marketplace/search")
async def search_marketplace_services(request: SearchServicesRequest):
    """Recherche des services dans la marketplace"""
    try:
        services = await t4g_marketplace.search_services(
            category=request.category,
            max_cost=request.max_cost,
            tags=request.tags,
            provider_level=request.provider_level
        )
        return {"services": services, "count": len(services)}
    except Exception as e:
        logger.error(f"Erreur recherche services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/marketplace/book", response_model=ServiceBooking)
async def book_marketplace_service(request: BookServiceRequest):
    """Réserve un service de la marketplace"""
    try:
        booking = await t4g_marketplace.book_service(
            client_id=request.client_id,
            service_id=request.service_id,
            scheduled_at=request.scheduled_at,
            notes=request.notes
        )
        return booking
    except Exception as e:
        logger.error(f"Erreur réservation service: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/marketplace/bookings/complete")
async def complete_service_booking(request: CompleteBookingRequest,
                                 background_tasks: BackgroundTasks):
    """Finalise une réservation de service"""
    try:
        success = await t4g_marketplace.complete_booking(
            booking_id=request.booking_id,
            feedback=request.feedback
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Réservation non trouvée")
        
        # Vérification des achievements pour le provider
        booking = t4g_marketplace.bookings[request.booking_id]
        background_tasks.add_task(
            t4g_rewards.process_achievement_unlocks,
            booking.provider_id
        )
        
        return {"success": True, "message": "Service complété avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur completion booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/marketplace/bookings/{user_id}")
async def get_user_bookings(user_id: str, as_client: bool = True):
    """Récupère les réservations d'un utilisateur"""
    try:
        bookings = await t4g_marketplace.get_user_bookings(user_id, as_client)
        return {"bookings": bookings}
    except Exception as e:
        logger.error(f"Erreur récupération bookings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/marketplace/recommendations/{user_id}")
async def get_service_recommendations(user_id: str, limit: int = 5):
    """Récupère des recommandations de services pour un utilisateur"""
    try:
        recommendations = await t4g_marketplace.get_recommended_services(user_id, limit)
        return {"recommendations": recommendations}
    except Exception as e:
        logger.error(f"Erreur recommandations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/marketplace/stats")
async def get_marketplace_statistics():
    """Récupère les statistiques de la marketplace"""
    try:
        stats = await t4g_marketplace.get_marketplace_stats()
        return stats
    except Exception as e:
        logger.error(f"Erreur stats marketplace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS ADMINISTRATIFS ====================

@router.post("/admin/rewards/weekly-bonuses")
async def trigger_weekly_bonuses():
    """Déclenche le calcul et l'attribution des bonus hebdomadaires"""
    try:
        result = await t4g_rewards.calculate_weekly_bonuses()
        return result
    except Exception as e:
        logger.error(f"Erreur bonus hebdomadaires: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/system/status")
async def get_system_status():
    """Récupère le statut général du système T4G"""
    try:
        total_users = len(t4g_service.users)
        total_transactions = len(t4g_service.transactions)
        total_services = len([s for s in t4g_marketplace.services.values() if s.is_active])
        total_bookings = len(t4g_marketplace.bookings)
        
        # Distribution des niveaux d'utilisateurs
        level_distribution = {}
        for user in t4g_service.users.values():
            level = user.user_level.value
            level_distribution[level] = level_distribution.get(level, 0) + 1
        
        # Tokens en circulation
        total_tokens_earned = sum(u.total_tokens_earned for u in t4g_service.users.values())
        total_tokens_spent = sum(u.total_tokens_spent for u in t4g_service.users.values())
        
        return {
            "system_health": "active",
            "total_users": total_users,
            "total_transactions": total_transactions,
            "total_services": total_services,
            "total_bookings": total_bookings,
            "level_distribution": level_distribution,
            "token_economy": {
                "total_earned": total_tokens_earned,
                "total_spent": total_tokens_spent,
                "in_circulation": total_tokens_earned - total_tokens_spent
            }
        }
    except Exception as e:
        logger.error(f"Erreur statut système: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS BITCOIN/LND POUR TOKEN4GOOD ====================

class CreateLightningInvoiceRequest(BaseModel):
    """Requête pour créer une facture Lightning"""
    amount: int = Field(..., description="Montant en satoshis", gt=0)
    memo: Optional[str] = Field("", description="Description de la facture")
    expiry: Optional[int] = Field(3600, description="Expiration en secondes", ge=60)


class PayLightningInvoiceRequest(BaseModel):
    """Requête pour payer une facture Lightning"""
    bolt11: str = Field(..., description="Facture BOLT11 à payer")
    max_fee_msat: Optional[int] = Field(None, description="Frais maximum en millisatoshis")


if LNbitsServiceAvailable:
    lnbits_service = LNbitsService()

    @router.post("/lightning/invoice/create")
    async def create_lightning_invoice(request: CreateLightningInvoiceRequest):
        """
        Crée une facture Lightning Network pour Token4Good
        
        Permet à l'application Token4Good de créer des factures Lightning
        pour recevoir des paiements Bitcoin via le réseau Lightning.
        """
        try:
            invoice = await lnbits_service.create_invoice(
                amount=request.amount,
                memo=request.memo or "Token4Good payment"
            )
            return {
                "status": "success",
                "payment_request": invoice.get("payment_request"),
                "payment_hash": invoice.get("payment_hash"),
                "checking_id": invoice.get("checking_id"),
                "amount": request.amount,
                "memo": request.memo,
                "expiry": request.expiry
            }
        except Exception as e:
            logger.error(f"Erreur création facture Lightning: {e}")
            raise HTTPException(status_code=500, detail=f"Échec création facture: {str(e)}")

    @router.get("/lightning/balance")
    async def get_lightning_balance():
        """
        Récupère le solde Lightning Network du wallet Token4Good
        
        Retourne le solde disponible en satoshis du wallet Lightning
        configuré pour Token4Good.
        """
        try:
            # Utiliser get_wallet_details pour récupérer les informations du wallet
            wallet_data = await lnbits_service.get_wallet_details()
            
            balance_sats = wallet_data.get("balance", 0) if isinstance(wallet_data, dict) else 0
            
            return {
                "status": "success",
                "balance_sats": balance_sats,
                "balance_msats": balance_sats * 1000,
                "wallet_id": wallet_data.get("id", "unknown") if isinstance(wallet_data, dict) else "unknown",
                "wallet_name": wallet_data.get("name", "Token4Good Wallet") if isinstance(wallet_data, dict) else "Token4Good Wallet"
            }
        except Exception as e:
            logger.error(f"Erreur récupération solde Lightning: {e}")
            raise HTTPException(status_code=500, detail=f"Échec récupération solde: {str(e)}")

    @router.post("/lightning/invoice/pay")
    async def pay_lightning_invoice(request: PayLightningInvoiceRequest):
        """
        Paye une facture Lightning Network depuis Token4Good
        
        Permet de payer une facture BOLT11 en utilisant le wallet Lightning
        configuré pour Token4Good.
        Note: max_fee_msat n'est pas supporté par LNbitsService actuellement
        """
        try:
            payment = await lnbits_service.pay_invoice(bolt11=request.bolt11)
            return {
                "status": "success",
                "payment_hash": payment.get("payment_hash"),
                "fee_msat": payment.get("fee_msat", 0),
                "checking_id": payment.get("checking_id"),
                "details": payment
            }
        except Exception as e:
            logger.error(f"Erreur paiement facture Lightning: {e}")
            raise HTTPException(status_code=500, detail=f"Échec paiement: {str(e)}")

    @router.get("/lightning/invoice/check/{payment_hash}")
    async def check_lightning_invoice_status(payment_hash: str):
        """
        Vérifie le statut d'une facture Lightning
        
        Permet de vérifier si une facture a été payée en utilisant
        son payment_hash via les transactions du wallet.
        """
        try:
            # Récupérer les transactions pour trouver celle correspondant au payment_hash
            transactions = await lnbits_service.get_transactions()
            payment_info = None
            
            if isinstance(transactions, dict) and "payments" in transactions:
                payments = transactions["payments"]
            elif isinstance(transactions, list):
                payments = transactions
            else:
                payments = []
            
            for payment in payments:
                if payment.get("payment_hash") == payment_hash or payment.get("checking_id") == payment_hash:
                    payment_info = payment
                    break
            
            if payment_info:
                paid = payment_info.get("status") == "paid" or payment_info.get("paid", False)
            else:
                paid = False
            
            return {
                "status": "success",
                "payment_hash": payment_hash,
                "paid": paid,
                "details": payment_info if payment_info else {"message": "Facture non trouvée"}
            }
        except Exception as e:
            logger.error(f"Erreur vérification facture: {e}")
            raise HTTPException(status_code=500, detail=f"Échec vérification: {str(e)}")

    @router.get("/lightning/node/info")
    async def get_lightning_node_info():
        """
        Récupère les informations du nœud Lightning Network
        
        Retourne les informations du réseau Lightning accessible via Token4Good.
        """
        try:
            network_nodes = await lnbits_service.get_network_nodes()
            network_stats = await lnbits_service.get_network_stats()
            
            return {
                "status": "success",
                "node_info": {
                    "network_stats": network_stats,
                    "available_nodes": len(network_nodes.get("nodes", [])) if isinstance(network_nodes, dict) else 0,
                    "network_data": network_nodes
                }
            }
        except Exception as e:
            logger.error(f"Erreur récupération info nœud: {e}")
            raise HTTPException(status_code=500, detail=f"Échec récupération info nœud: {str(e)}")

    @router.get("/lightning/channels")
    async def get_lightning_channels():
        """
        Récupère la liste des canaux Lightning Network
        
        Retourne les informations sur les canaux disponibles via le réseau Lightning.
        Note: Cette information peut nécessiter un accès direct à LND ou un endpoint spécifique.
        """
        try:
            # Utiliser les recommandations de canaux comme alternative
            channel_recommendations = await lnbits_service.get_unified_channel_recommendations()
            
            channels = channel_recommendations.get("channels", []) if isinstance(channel_recommendations, dict) else []
            
            return {
                "status": "success",
                "channels": channels,
                "total_channels": len(channels),
                "note": "Données basées sur les recommandations de canaux disponibles"
            }
        except Exception as e:
            logger.error(f"Erreur récupération canaux: {e}")
            raise HTTPException(status_code=500, detail=f"Échec récupération canaux: {str(e)}")

else:
    # Endpoints désactivés si LNbitsService n'est pas disponible
    @router.get("/lightning/status")
    async def lightning_service_status():
        """Vérifie si le service Lightning est disponible"""
        return {
            "status": "unavailable",
            "message": "Service Lightning Network non configuré pour Token4Good"
        }