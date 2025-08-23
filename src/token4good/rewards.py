"""
Token4Good Rewards Engine - Moteur de calcul et attribution des récompenses
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from collections import defaultdict

from .models import T4GTokenAction, UserProfile, T4G_REWARD_SYSTEM
from .service import T4GService

logger = logging.getLogger(__name__)


class T4GRewardsEngine:
    """Moteur intelligent pour le calcul et l'attribution des récompenses T4G"""
    
    def __init__(self, t4g_service: T4GService):
        self.t4g_service = t4g_service
        self.achievement_cache = {}
        self.community_multipliers = {
            "high_demand_skill": 1.2,  # Compétences très demandées
            "quick_responder": 1.1,    # Réponse rapide aux demandes
            "consistent_helper": 1.15,  # Aide régulière
            "quality_contributor": 1.3, # Contributions de haute qualité
            "community_leader": 1.5     # Leadership communautaire
        }
    
    async def calculate_dynamic_reward(self, user_id: str, action_type: T4GTokenAction,
                                     context: Dict = None) -> Dict:
        """Calcule une récompense dynamique basée sur le contexte et l'historique"""
        base_config = T4G_REWARD_SYSTEM.get(action_type, {})
        base_reward = base_config.get("base_reward", 50)
        multipliers = base_config.get("multipliers", {})
        
        # Facteur de base
        final_multiplier = 1.0
        applied_bonuses = []
        
        # Multiplieurs basés sur le contexte fourni
        for bonus_key, bonus_value in multipliers.items():
            if context and context.get(bonus_key, False):
                final_multiplier *= bonus_value
                applied_bonuses.append(f"{bonus_key}: +{int((bonus_value - 1) * 100)}%")
        
        # Multiplieurs communautaires dynamiques
        community_bonuses = await self._calculate_community_multipliers(user_id, action_type, context)
        for bonus_name, bonus_value in community_bonuses.items():
            final_multiplier *= bonus_value
            applied_bonuses.append(f"{bonus_name}: +{int((bonus_value - 1) * 100)}%")
        
        # Facteur de rareté de l'action
        rarity_bonus = await self._calculate_rarity_bonus(action_type)
        final_multiplier *= rarity_bonus
        if rarity_bonus > 1.0:
            applied_bonuses.append(f"rarity_bonus: +{int((rarity_bonus - 1) * 100)}%")
        
        # Facteur de qualité historique
        quality_bonus = await self._calculate_quality_bonus(user_id)
        final_multiplier *= quality_bonus
        if quality_bonus > 1.0:
            applied_bonuses.append(f"quality_history: +{int((quality_bonus - 1) * 100)}%")
        
        final_tokens = int(base_reward * final_multiplier)
        
        return {
            "base_reward": base_reward,
            "final_tokens": final_tokens,
            "total_multiplier": final_multiplier,
            "applied_bonuses": applied_bonuses,
            "breakdown": {
                "base": base_reward,
                "context_multipliers": multipliers,
                "community_bonuses": community_bonuses,
                "rarity_bonus": rarity_bonus,
                "quality_bonus": quality_bonus
            }
        }
    
    async def _calculate_community_multipliers(self, user_id: str, action_type: T4GTokenAction,
                                             context: Dict = None) -> Dict[str, float]:
        """Calcule les bonus communautaires"""
        bonuses = {}
        user = self.t4g_service.users.get(user_id)
        
        if not user:
            return bonuses
        
        # Bonus pour compétences très demandées
        if await self._has_high_demand_skills(user_id):
            bonuses["high_demand_skill"] = self.community_multipliers["high_demand_skill"]
        
        # Bonus réponse rapide
        if context and context.get("response_time_hours", 24) < 2:
            bonuses["quick_responder"] = self.community_multipliers["quick_responder"]
        
        # Bonus aide régulière
        if await self._is_consistent_helper(user_id):
            bonuses["consistent_helper"] = self.community_multipliers["consistent_helper"]
        
        # Bonus qualité
        if await self._is_quality_contributor(user_id):
            bonuses["quality_contributor"] = self.community_multipliers["quality_contributor"]
        
        # Bonus leadership
        if await self._is_community_leader(user_id):
            bonuses["community_leader"] = self.community_multipliers["community_leader"]
        
        return bonuses
    
    async def _calculate_rarity_bonus(self, action_type: T4GTokenAction) -> float:
        """Calcule un bonus basé sur la rareté de l'action"""
        # Compter les actions de ce type dans les dernières 24h
        recent_actions = 0
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        for transaction in self.t4g_service.transactions.values():
            if (transaction.action_type == action_type and 
                transaction.timestamp > cutoff_time):
                recent_actions += 1
        
        # Plus l'action est rare, plus le bonus est élevé
        if recent_actions <= 2:
            return 1.3  # Très rare
        elif recent_actions <= 5:
            return 1.2  # Rare
        elif recent_actions <= 10:
            return 1.1  # Peu commune
        else:
            return 1.0  # Commune
    
    async def _calculate_quality_bonus(self, user_id: str) -> float:
        """Calcule un bonus basé sur l'historique de qualité"""
        user_transactions = [t for t in self.t4g_service.transactions.values() 
                           if t.user_id == user_id]
        
        if len(user_transactions) < 5:
            return 1.0  # Pas assez d'historique
        
        # Calculer la moyenne des scores d'impact
        avg_impact = sum(t.impact_score for t in user_transactions) / len(user_transactions)
        
        # Convertir en bonus (impact moyen élevé = bonus)
        if avg_impact >= 1.4:
            return 1.2
        elif avg_impact >= 1.2:
            return 1.1
        else:
            return 1.0
    
    async def _has_high_demand_skills(self, user_id: str) -> bool:
        """Vérifie si l'utilisateur a des compétences très demandées"""
        high_demand_skills = [
            "lightning-network", "bitcoin", "dazbox", "dazpay", 
            "node-management", "api-integration", "business-development"
        ]
        
        user = self.t4g_service.users.get(user_id)
        if not user:
            return False
        
        return any(skill.lower() in high_demand_skills for skill in user.skills)
    
    async def _is_consistent_helper(self, user_id: str) -> bool:
        """Vérifie si l'utilisateur aide régulièrement"""
        # Actions dans les 7 derniers jours
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_actions = [
            t for t in self.t4g_service.transactions.values()
            if t.user_id == user_id and t.timestamp > week_ago and t.tokens_earned > 0
        ]
        
        # Au moins 3 actions dans la semaine
        return len(recent_actions) >= 3
    
    async def _is_quality_contributor(self, user_id: str) -> bool:
        """Vérifie si l'utilisateur fait des contributions de qualité"""
        # Vérifier les sessions de mentoring avec de bonnes notes
        quality_sessions = [
            s for s in self.t4g_service.mentoring_sessions.values()
            if (s.mentor_id == user_id and s.status == "completed" and 
                s.feedback and s.feedback.get("rating", 0) >= 4.5)
        ]
        
        return len(quality_sessions) >= 2
    
    async def _is_community_leader(self, user_id: str) -> bool:
        """Vérifie si l'utilisateur est un leader communautaire"""
        user = self.t4g_service.users.get(user_id)
        if not user:
            return False
        
        # Expert avec beaucoup d'activité
        return (user.user_level.value == "expert" and 
                user.total_tokens_earned >= 2000 and
                user.reputation_score >= 0.8)
    
    async def process_achievement_unlocks(self, user_id: str) -> List[Dict]:
        """Vérifie et traite les achievements débloqués"""
        user = self.t4g_service.users.get(user_id)
        if not user:
            return []
        
        unlocked_achievements = []
        
        # Achievement : Premier pas
        if (user.total_tokens_earned >= 10 and 
            "first_steps" not in self.achievement_cache.get(user_id, [])):
            unlocked_achievements.append({
                "id": "first_steps",
                "name": "Premier pas dans T4G",
                "description": "Premiers tokens gagnés !",
                "bonus_tokens": 25,
                "badge": "🎯"
            })
        
        # Achievement : Mentor débutant
        mentoring_count = len([s for s in self.t4g_service.mentoring_sessions.values()
                              if s.mentor_id == user_id and s.status == "completed"])
        if (mentoring_count >= 3 and 
            "beginner_mentor" not in self.achievement_cache.get(user_id, [])):
            unlocked_achievements.append({
                "id": "beginner_mentor",
                "name": "Mentor débutant",
                "description": "3 sessions de mentoring complétées",
                "bonus_tokens": 50,
                "badge": "🎓"
            })
        
        # Achievement : Expert communautaire
        if (user.total_tokens_earned >= 1000 and user.reputation_score >= 0.7 and
            "community_expert" not in self.achievement_cache.get(user_id, [])):
            unlocked_achievements.append({
                "id": "community_expert",
                "name": "Expert communautaire",
                "description": "1000+ tokens et excellente réputation",
                "bonus_tokens": 100,
                "badge": "⭐"
            })
        
        # Achievement : Contributeur régulier
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_days_active = len(set(
            t.timestamp.date() for t in self.t4g_service.transactions.values()
            if t.user_id == user_id and t.timestamp > week_ago
        ))
        if (recent_days_active >= 5 and 
            "regular_contributor" not in self.achievement_cache.get(user_id, [])):
            unlocked_achievements.append({
                "id": "regular_contributor", 
                "name": "Contributeur régulier",
                "description": "Actif 5 jours dans la semaine",
                "bonus_tokens": 75,
                "badge": "🔥"
            })
        
        # Attribuer les bonus et marquer comme débloqués
        for achievement in unlocked_achievements:
            await self.t4g_service.award_tokens(
                user_id=user_id,
                action_type=T4GTokenAction.CONTRIBUTION_COMMUNAUTAIRE,
                tokens=achievement["bonus_tokens"],
                description=f"Achievement débloqué: {achievement['name']}",
                metadata={"achievement_id": achievement["id"]}
            )
            
            # Marquer comme débloqué
            if user_id not in self.achievement_cache:
                self.achievement_cache[user_id] = []
            self.achievement_cache[user_id].append(achievement["id"])
        
        return unlocked_achievements
    
    async def calculate_weekly_bonuses(self) -> Dict:
        """Calcule et attribue les bonus hebdomadaires"""
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # Top contributeurs de la semaine
        weekly_contributions = defaultdict(int)
        for transaction in self.t4g_service.transactions.values():
            if (transaction.timestamp > week_ago and 
                transaction.tokens_earned > 0):
                weekly_contributions[transaction.user_id] += transaction.tokens_earned
        
        # Top 3 contributeurs
        top_contributors = sorted(
            weekly_contributions.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        
        bonuses_awarded = []
        
        for i, (user_id, tokens_earned) in enumerate(top_contributors):
            bonus_tokens = [100, 75, 50][i]  # 1er, 2ème, 3ème
            
            await self.t4g_service.award_tokens(
                user_id=user_id,
                action_type=T4GTokenAction.CONTRIBUTION_COMMUNAUTAIRE,
                tokens=bonus_tokens,
                description=f"Bonus hebdomadaire - Top {i+1} contributeur",
                metadata={"weekly_rank": i+1, "weekly_tokens": tokens_earned}
            )
            
            bonuses_awarded.append({
                "rank": i+1,
                "user_id": user_id,
                "weekly_tokens": tokens_earned,
                "bonus": bonus_tokens
            })
        
        logger.info(f"Bonus hebdomadaires attribués à {len(bonuses_awarded)} utilisateurs")
        return {"bonuses_awarded": bonuses_awarded}
    
    async def suggest_earning_opportunities(self, user_id: str) -> List[Dict]:
        """Suggère des opportunités de gains pour un utilisateur"""
        user = self.t4g_service.users.get(user_id)
        if not user:
            return []
        
        opportunities = []
        
        # Analyser l'historique pour identifier les patterns
        user_actions = defaultdict(int)
        for transaction in self.t4g_service.transactions.values():
            if transaction.user_id == user_id:
                user_actions[transaction.action_type] += 1
        
        # Suggérer selon le profil
        if user_actions[T4GTokenAction.MENTORING] == 0:
            opportunities.append({
                "type": "mentoring",
                "title": "Commencer le mentoring",
                "description": "Partagez votre expertise et gagnez jusqu'à 100 T4G par session",
                "potential_tokens": "50-100 T4G",
                "difficulty": "Facile",
                "time_investment": "1-2h"
            })
        
        if user_actions[T4GTokenAction.CODE_REVIEW] < 3:
            opportunities.append({
                "type": "code_review",
                "title": "Code reviews",
                "description": "Aidez à améliorer le code de la communauté",
                "potential_tokens": "80-120 T4G",
                "difficulty": "Moyen", 
                "time_investment": "30min-1h"
            })
        
        if user_actions[T4GTokenAction.DOCUMENTATION] == 0:
            opportunities.append({
                "type": "documentation",
                "title": "Création de documentation",
                "description": "Créez des guides utiles pour la communauté",
                "potential_tokens": "100-140 T4G",
                "difficulty": "Moyen",
                "time_investment": "2-3h"
            })
        
        # Opportunités basées sur les compétences
        if "lightning-network" in [s.lower() for s in user.skills]:
            opportunities.append({
                "type": "specialized_mentoring",
                "title": "Mentoring Lightning Network",
                "description": "Votre expertise Lightning est très demandée (+20% bonus)",
                "potential_tokens": "60-120 T4G",
                "difficulty": "Facile",
                "time_investment": "1h"
            })
        
        return opportunities[:5]  # Top 5 opportunités