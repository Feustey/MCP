"""
Token4Good Service - Gestionnaire principal du système T4G
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import uuid
import logging

from .models import (
    T4GTransaction, MentoringSession, UserProfile, 
    T4GTokenAction, UserLevel, T4G_REWARD_SYSTEM
)

logger = logging.getLogger(__name__)


class T4GService:
    """Service principal pour la gestion des tokens T4G"""
    
    def __init__(self, database_client=None):
        self.db = database_client
        self.transactions: Dict[str, T4GTransaction] = {}
        self.users: Dict[str, UserProfile] = {}
        self.mentoring_sessions: Dict[str, MentoringSession] = {}
        
    async def create_user_profile(self, user_id: str, username: str, email: str, 
                                  skills: List[str] = None) -> UserProfile:
        """Crée un profil utilisateur T4G"""
        profile = UserProfile(
            user_id=user_id,
            username=username,
            email=email,
            skills=skills or []
        )
        
        self.users[user_id] = profile
        
        # Bonus de bienvenue
        await self.award_tokens(
            user_id=user_id,
            action_type=T4GTokenAction.CONTRIBUTION_COMMUNAUTAIRE,
            tokens=50,
            description="Bonus de bienvenue dans la communauté T4G"
        )
        
        logger.info(f"Nouveau profil T4G créé pour {username} ({user_id})")
        return profile
    
    async def award_tokens(self, user_id: str, action_type: T4GTokenAction, 
                          tokens: int, description: str, 
                          metadata: Dict = None, impact_score: float = 1.0) -> T4GTransaction:
        """Attribue des tokens T4G à un utilisateur"""
        transaction_id = str(uuid.uuid4())
        
        # Calcul des tokens avec multiplieurs
        base_reward = T4G_REWARD_SYSTEM.get(action_type, {}).get("base_reward", tokens)
        final_tokens = int(base_reward * impact_score)
        
        transaction = T4GTransaction(
            id=transaction_id,
            user_id=user_id,
            action_type=action_type,
            tokens_earned=final_tokens,
            description=description,
            metadata=metadata or {},
            impact_score=impact_score
        )
        
        # Mise à jour du profil utilisateur
        if user_id in self.users:
            profile = self.users[user_id]
            profile.total_tokens_earned += final_tokens
            profile.last_activity = datetime.utcnow()
            profile.update_level()
            
        # Stockage de la transaction
        self.transactions[transaction_id] = transaction
        
        logger.info(f"Tokens T4G attribués: {final_tokens} à {user_id} pour {action_type.value}")
        return transaction
    
    async def spend_tokens(self, user_id: str, tokens: int, description: str,
                          service_id: Optional[str] = None) -> bool:
        """Dépense des tokens T4G"""
        if user_id not in self.users:
            return False
            
        profile = self.users[user_id]
        if profile.available_balance < tokens:
            return False
        
        transaction_id = str(uuid.uuid4())
        transaction = T4GTransaction(
            id=transaction_id,
            user_id=user_id,
            action_type=T4GTokenAction.CONTRIBUTION_COMMUNAUTAIRE,  # Generic for spending
            tokens_spent=tokens,
            description=description,
            metadata={"service_id": service_id} if service_id else {}
        )
        
        profile.total_tokens_spent += tokens
        profile.last_activity = datetime.utcnow()
        self.transactions[transaction_id] = transaction
        
        logger.info(f"Tokens T4G dépensés: {tokens} par {user_id} pour {description}")
        return True
    
    async def create_mentoring_session(self, mentor_id: str, mentee_id: str,
                                     topic: str, category: str, 
                                     duration_minutes: int) -> MentoringSession:
        """Crée une session de mentoring"""
        session_id = str(uuid.uuid4())
        
        # Calcul des tokens de récompense basé sur la durée et catégorie
        base_tokens = {
            "lightning_network": 50,
            "dazbox_setup": 75, 
            "business_dev": 100,
            "dazpay_integration": 60
        }.get(category, 50)
        
        # Bonus pour les longues sessions
        duration_multiplier = 1.0
        if duration_minutes >= 120:  # 2h+
            duration_multiplier = 1.3
        elif duration_minutes >= 90:  # 1.5h+
            duration_multiplier = 1.2
            
        tokens_reward = int(base_tokens * duration_multiplier)
        
        session = MentoringSession(
            id=session_id,
            mentor_id=mentor_id,
            mentee_id=mentee_id,
            topic=topic,
            category=category,
            duration_minutes=duration_minutes,
            tokens_reward=tokens_reward,
            status="scheduled",
            scheduled_at=datetime.utcnow()
        )
        
        self.mentoring_sessions[session_id] = session
        logger.info(f"Session de mentoring créée: {session_id} ({topic})")
        return session
    
    async def complete_mentoring_session(self, session_id: str, 
                                       feedback: Dict = None) -> bool:
        """Finalise une session de mentoring et attribue les tokens"""
        if session_id not in self.mentoring_sessions:
            return False
            
        session = self.mentoring_sessions[session_id]
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        session.feedback = feedback or {}
        
        # Calcul des multiplieurs basés sur le feedback
        rating_multiplier = 1.0
        if feedback and "rating" in feedback:
            rating = feedback["rating"]
            if rating >= 5:
                rating_multiplier = 1.5
            elif rating >= 4:
                rating_multiplier = 1.2
        
        final_tokens = int(session.tokens_reward * rating_multiplier)
        
        # Attribution des tokens au mentor
        await self.award_tokens(
            user_id=session.mentor_id,
            action_type=T4GTokenAction.MENTORING,
            tokens=final_tokens,
            description=f"Session de mentoring complétée: {session.topic}",
            metadata={
                "session_id": session_id,
                "mentee_id": session.mentee_id,
                "duration": session.duration_minutes,
                "category": session.category,
                "rating": feedback.get("rating") if feedback else None
            },
            impact_score=rating_multiplier
        )
        
        logger.info(f"Session de mentoring complétée: {session_id}, {final_tokens} tokens attribués")
        return True
    
    async def get_user_statistics(self, user_id: str) -> Dict:
        """Récupère les statistiques d'un utilisateur"""
        if user_id not in self.users:
            return {}
            
        profile = self.users[user_id]
        user_transactions = [t for t in self.transactions.values() if t.user_id == user_id]
        
        # Calcul des statistiques
        mentoring_sessions_given = len([s for s in self.mentoring_sessions.values() 
                                       if s.mentor_id == user_id and s.status == "completed"])
        mentoring_sessions_received = len([s for s in self.mentoring_sessions.values()
                                          if s.mentee_id == user_id and s.status == "completed"])
        
        tokens_by_action = {}
        for transaction in user_transactions:
            action = transaction.action_type.value
            tokens_by_action[action] = tokens_by_action.get(action, 0) + transaction.tokens_earned
        
        return {
            "profile": profile,
            "total_transactions": len(user_transactions),
            "mentoring_given": mentoring_sessions_given,
            "mentoring_received": mentoring_sessions_received,
            "tokens_by_action": tokens_by_action,
            "avg_session_rating": self._calculate_avg_rating(user_id),
            "community_rank": self._get_community_rank(user_id),
            "next_level": self._get_next_level_requirements(profile)
        }
    
    async def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Récupère le classement de la communauté"""
        sorted_users = sorted(
            self.users.values(),
            key=lambda u: (u.total_tokens_earned, u.reputation_score),
            reverse=True
        )
        
        leaderboard = []
        for i, user in enumerate(sorted_users[:limit]):
            mentoring_count = len([s for s in self.mentoring_sessions.values()
                                 if s.mentor_id == user.user_id and s.status == "completed"])
            
            leaderboard.append({
                "rank": i + 1,
                "username": user.username,
                "user_level": user.user_level.value,
                "total_tokens": user.total_tokens_earned,
                "reputation_score": user.reputation_score,
                "mentoring_sessions": mentoring_count,
                "skills": user.skills[:3]  # Top 3 skills
            })
        
        return leaderboard
    
    def _calculate_avg_rating(self, user_id: str) -> float:
        """Calcule la note moyenne pour un mentor"""
        sessions = [s for s in self.mentoring_sessions.values()
                   if s.mentor_id == user_id and s.status == "completed" and s.feedback]
        
        if not sessions:
            return 0.0
            
        ratings = [s.feedback.get("rating", 0) for s in sessions if s.feedback.get("rating")]
        return sum(ratings) / len(ratings) if ratings else 0.0
    
    def _get_community_rank(self, user_id: str) -> int:
        """Obtient le rang dans la communauté"""
        sorted_users = sorted(
            self.users.values(),
            key=lambda u: u.total_tokens_earned,
            reverse=True
        )
        
        for i, user in enumerate(sorted_users):
            if user.user_id == user_id:
                return i + 1
        return len(sorted_users)
    
    def _get_next_level_requirements(self, profile: UserProfile) -> Dict:
        """Calcule les requis pour le niveau suivant"""
        current_tokens = profile.total_tokens_earned
        
        if profile.user_level == UserLevel.CONTRIBUTEUR:
            return {
                "next_level": "MENTOR",
                "tokens_needed": max(0, 500 - current_tokens),
                "progress_percentage": min(100, (current_tokens / 500) * 100)
            }
        elif profile.user_level == UserLevel.MENTOR:
            return {
                "next_level": "EXPERT", 
                "tokens_needed": max(0, 1500 - current_tokens),
                "progress_percentage": min(100, ((current_tokens - 500) / 1000) * 100)
            }
        else:
            return {
                "next_level": "MAX_LEVEL",
                "tokens_needed": 0,
                "progress_percentage": 100
            }