"""
Token4Good Marketplace - Système d'échange de services contre tokens T4G
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

from .models import (
    MarketplaceService, ServiceBooking, ServiceCategory, 
    T4G_SERVICE_CATALOG, UserProfile
)
from .service import T4GService

logger = logging.getLogger(__name__)


class T4GMarketplace:
    """Marketplace pour échanger des services contre des tokens T4G"""
    
    def __init__(self, t4g_service: T4GService):
        self.t4g_service = t4g_service
        self.services: Dict[str, MarketplaceService] = {}
        self.bookings: Dict[str, ServiceBooking] = {}
        self._initialize_default_services()
    
    def _initialize_default_services(self):
        """Initialise les services par défaut de la marketplace"""
        for service_key, config in T4G_SERVICE_CATALOG.items():
            service_id = str(uuid.uuid4())
            service = MarketplaceService(
                id=service_id,
                name=config["name"],
                description=config["description"],
                category=config["category"],
                provider_id="system",  # Services système
                token_cost=config["base_cost"],
                estimated_duration=config["duration"],
                tags=self._extract_tags(config["description"])
            )
            self.services[service_id] = service
    
    def _extract_tags(self, description: str) -> List[str]:
        """Extrait des tags à partir de la description"""
        tags = []
        if "Lightning" in description or "lightning" in description:
            tags.append("lightning-network")
        if "DazBox" in description or "dazbox" in description:
            tags.append("dazbox")
        if "DazPay" in description or "dazpay" in description:
            tags.append("dazpay")
        if "Business" in description or "business" in description:
            tags.append("business")
        if "API" in description or "api" in description:
            tags.append("api")
        if "IA" in description or "AI" in description:
            tags.append("intelligence-artificielle")
        return tags
    
    async def create_service(self, provider_id: str, name: str, description: str,
                            category: ServiceCategory, token_cost: int,
                            estimated_duration: str, requirements: List[str] = None,
                            tags: List[str] = None) -> MarketplaceService:
        """Crée un nouveau service dans la marketplace"""
        # Vérifier que le provider a le niveau requis
        provider = self.t4g_service.users.get(provider_id)
        if not provider or provider.user_level.value == "contributeur":
            raise ValueError("Niveau MENTOR minimum requis pour créer des services")
        
        service_id = str(uuid.uuid4())
        service = MarketplaceService(
            id=service_id,
            name=name,
            description=description,
            category=category,
            provider_id=provider_id,
            token_cost=token_cost,
            estimated_duration=estimated_duration,
            requirements=requirements or [],
            tags=tags or []
        )
        
        self.services[service_id] = service
        logger.info(f"Nouveau service créé: {name} par {provider_id}")
        return service
    
    async def search_services(self, category: Optional[ServiceCategory] = None,
                             max_cost: Optional[int] = None,
                             tags: Optional[List[str]] = None,
                             provider_level: Optional[str] = None) -> List[MarketplaceService]:
        """Recherche des services selon différents critères"""
        results = []
        
        for service in self.services.values():
            if not service.is_active:
                continue
                
            # Filtre par catégorie
            if category and service.category != category:
                continue
                
            # Filtre par coût maximum
            if max_cost and service.token_cost > max_cost:
                continue
                
            # Filtre par tags
            if tags and not any(tag in service.tags for tag in tags):
                continue
                
            # Filtre par niveau du provider
            if provider_level:
                provider = self.t4g_service.users.get(service.provider_id)
                if provider and provider.user_level.value != provider_level:
                    continue
            
            results.append(service)
        
        # Tri par popularité (nombre de réservations) et note
        results.sort(key=lambda s: (s.total_bookings, s.rating or 0), reverse=True)
        return results
    
    async def book_service(self, client_id: str, service_id: str,
                          scheduled_at: Optional[datetime] = None,
                          notes: Optional[str] = None) -> ServiceBooking:
        """Réserve un service avec les tokens T4G"""
        if service_id not in self.services:
            raise ValueError("Service non trouvé")
            
        service = self.services[service_id]
        client = self.t4g_service.users.get(client_id)
        
        if not client:
            raise ValueError("Utilisateur non trouvé")
            
        # Vérifier le solde de tokens
        if client.available_balance < service.token_cost:
            raise ValueError(f"Solde insuffisant. Requis: {service.token_cost}, Disponible: {client.available_balance}")
        
        # Créer la réservation
        booking_id = str(uuid.uuid4())
        booking = ServiceBooking(
            id=booking_id,
            service_id=service_id,
            client_id=client_id,
            provider_id=service.provider_id,
            tokens_cost=service.token_cost,
            status="pending",
            scheduled_at=scheduled_at
        )
        
        # Débiter les tokens (en attente)
        await self.t4g_service.spend_tokens(
            user_id=client_id,
            tokens=service.token_cost,
            description=f"Réservation service: {service.name}",
            service_id=service_id
        )
        
        self.bookings[booking_id] = booking
        service.total_bookings += 1
        
        logger.info(f"Service réservé: {service.name} par {client_id}")
        return booking
    
    async def confirm_booking(self, booking_id: str) -> bool:
        """Confirme une réservation (par le provider)"""
        if booking_id not in self.bookings:
            return False
            
        booking = self.bookings[booking_id]
        booking.status = "confirmed"
        
        logger.info(f"Réservation confirmée: {booking_id}")
        return True
    
    async def complete_booking(self, booking_id: str, feedback: Dict = None) -> bool:
        """Finalise une réservation et transfère les tokens au provider"""
        if booking_id not in self.bookings:
            return False
            
        booking = self.bookings[booking_id]
        booking.status = "completed"
        booking.completed_at = datetime.utcnow()
        booking.feedback = feedback or {}
        
        # Attribuer les tokens au provider (transfert depuis le client)
        service = self.services[booking.service_id]
        
        # Calculer les tokens avec bonus qualité
        provider_tokens = booking.tokens_cost
        if feedback and feedback.get("rating", 0) >= 5:
            provider_tokens = int(provider_tokens * 1.1)  # Bonus 10% pour excellente prestation
        
        await self.t4g_service.award_tokens(
            user_id=booking.provider_id,
            action_type="support_technique",  # ou autre selon le service
            tokens=provider_tokens,
            description=f"Prestation service complétée: {service.name}",
            metadata={
                "booking_id": booking_id,
                "client_id": booking.client_id,
                "service_id": booking.service_id,
                "rating": feedback.get("rating") if feedback else None
            }
        )
        
        # Mettre à jour la note du service
        if feedback and "rating" in feedback:
            await self._update_service_rating(booking.service_id, feedback["rating"])
        
        logger.info(f"Réservation complétée: {booking_id}")
        return True
    
    async def cancel_booking(self, booking_id: str, reason: str = None) -> bool:
        """Annule une réservation et rembourse les tokens"""
        if booking_id not in self.bookings:
            return False
            
        booking = self.bookings[booking_id]
        
        if booking.status in ["completed", "cancelled"]:
            return False
        
        booking.status = "cancelled"
        
        # Remboursement des tokens au client
        await self.t4g_service.award_tokens(
            user_id=booking.client_id,
            action_type="contribution_communautaire",
            tokens=booking.tokens_cost,
            description=f"Remboursement annulation: {self.services[booking.service_id].name}",
            metadata={"booking_id": booking_id, "reason": reason}
        )
        
        logger.info(f"Réservation annulée: {booking_id}, raison: {reason}")
        return True
    
    async def get_user_bookings(self, user_id: str, as_client: bool = True) -> List[ServiceBooking]:
        """Récupère les réservations d'un utilisateur"""
        if as_client:
            return [b for b in self.bookings.values() if b.client_id == user_id]
        else:
            return [b for b in self.bookings.values() if b.provider_id == user_id]
    
    async def get_marketplace_stats(self) -> Dict:
        """Récupère les statistiques de la marketplace"""
        total_bookings = len(self.bookings)
        completed_bookings = len([b for b in self.bookings.values() if b.status == "completed"])
        
        # Calcul du volume de tokens échangés
        total_volume = sum(b.tokens_cost for b in self.bookings.values() if b.status == "completed")
        
        # Top services
        service_bookings = {}
        for booking in self.bookings.values():
            if booking.status == "completed":
                service_id = booking.service_id
                service_bookings[service_id] = service_bookings.get(service_id, 0) + 1
        
        top_services = sorted(service_bookings.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Taux de satisfaction
        ratings = []
        for booking in self.bookings.values():
            if booking.feedback and "rating" in booking.feedback:
                ratings.append(booking.feedback["rating"])
        
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        return {
            "total_services": len([s for s in self.services.values() if s.is_active]),
            "total_bookings": total_bookings,
            "completed_bookings": completed_bookings,
            "completion_rate": completed_bookings / total_bookings if total_bookings > 0 else 0,
            "total_volume_tokens": total_volume,
            "average_rating": avg_rating,
            "top_services": [
                {
                    "service": self.services[service_id].name,
                    "bookings": count
                }
                for service_id, count in top_services
            ],
            "active_providers": len(set(s.provider_id for s in self.services.values() if s.is_active))
        }
    
    async def _update_service_rating(self, service_id: str, new_rating: float):
        """Met à jour la note d'un service"""
        service = self.services[service_id]
        
        # Calcul de la moyenne pondérée
        if service.rating is None:
            service.rating = new_rating
        else:
            # Moyenne pondérée avec les réservations précédentes
            total_ratings = service.total_bookings
            service.rating = ((service.rating * (total_ratings - 1)) + new_rating) / total_ratings
    
    async def get_recommended_services(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Recommande des services basés sur le profil utilisateur"""
        user = self.t4g_service.users.get(user_id)
        if not user:
            return []
        
        # Services compatibles avec le budget
        affordable_services = [s for s in self.services.values() 
                             if s.is_active and s.token_cost <= user.available_balance]
        
        # Scoring basé sur les compétences et intérêts
        scored_services = []
        for service in affordable_services:
            score = 0
            
            # Bonus si correspond aux intérêts
            for interest in user.interests:
                if interest.lower() in service.description.lower() or interest.lower() in service.tags:
                    score += 2
            
            # Bonus pour les services populaires
            score += min(service.total_bookings * 0.1, 2)
            
            # Bonus pour les bonnes notes
            if service.rating:
                score += service.rating * 0.5
            
            scored_services.append({
                "service": service,
                "score": score,
                "reason": self._get_recommendation_reason(service, user)
            })
        
        # Tri par score et limitation
        scored_services.sort(key=lambda x: x["score"], reverse=True)
        return scored_services[:limit]
    
    def _get_recommendation_reason(self, service: MarketplaceService, user: UserProfile) -> str:
        """Génère une raison pour la recommandation"""
        reasons = []
        
        # Basé sur les intérêts
        matching_interests = [i for i in user.interests 
                            if i.lower() in service.description.lower()]
        if matching_interests:
            reasons.append(f"Correspond à vos intérêts: {', '.join(matching_interests[:2])}")
        
        # Basé sur la popularité
        if service.total_bookings > 10:
            reasons.append("Service populaire dans la communauté")
        
        # Basé sur la note
        if service.rating and service.rating >= 4.5:
            reasons.append("Excellente note communautaire")
        
        # Basé sur le niveau
        if user.user_level.value == "expert":
            reasons.append("Recommandé pour votre niveau d'expertise")
        
        return " • ".join(reasons) if reasons else "Nouveau service à découvrir"