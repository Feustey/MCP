"""
Configuration pour le système Token4Good (T4G)
"""
import os
from typing import Dict, List
from pydantic import BaseSettings


class T4GConfig(BaseSettings):
    """Configuration pour le système T4G"""
    
    # Base de données
    database_url: str = os.getenv("T4G_DATABASE_URL", "sqlite:///token4good.db")
    redis_url: str = os.getenv("T4G_REDIS_URL", "redis://localhost:6379")
    
    # Configuration des tokens
    welcome_bonus_tokens: int = 50
    min_balance_for_expert: int = 1500
    min_balance_for_mentor: int = 500
    
    # Multiplieurs de récompenses
    quality_bonus_threshold: float = 4.5  # Note minimum pour bonus qualité
    quality_bonus_multiplier: float = 1.1  # 10% de bonus
    
    # Limite de temps pour les actions
    quick_response_hours: int = 2
    consistent_helper_days: int = 7
    consistent_helper_min_actions: int = 3
    
    # Configuration de la marketplace
    marketplace_enabled: bool = True
    service_creation_min_level: str = "mentor"
    max_services_per_user: int = 10
    
    # Configuration des achievements
    achievements_enabled: bool = True
    weekly_bonuses_enabled: bool = True
    
    # Limites système
    max_tokens_per_transaction: int = 1000
    max_daily_tokens_per_user: int = 2000
    
    class Config:
        env_prefix = "T4G_"
        case_sensitive = False


# Configuration des services par défaut
DEFAULT_SERVICE_TEMPLATES = {
    "lightning_network_support": {
        "name": "Support Lightning Network",
        "description": "Aide personnalisée pour configuration et optimisation Lightning",
        "base_cost": 50,
        "duration": "1h",
        "category": "technical_excellence",
        "tags": ["lightning", "bitcoin", "node-management"]
    },
    "dazbox_installation": {
        "name": "Installation DazBox",
        "description": "Installation complète et configuration DazBox",
        "base_cost": 75,
        "duration": "1.5h",
        "category": "technical_excellence", 
        "tags": ["dazbox", "installation", "configuration"]
    },
    "business_consultation": {
        "name": "Consultation Business Bitcoin",
        "description": "Stratégie d'adoption Bitcoin pour entreprises",
        "base_cost": 120,
        "duration": "2h",
        "category": "business_growth",
        "tags": ["business", "strategy", "bitcoin-adoption"]
    },
    "code_review": {
        "name": "Code Review Lightning",
        "description": "Révision de code pour projets Lightning Network",
        "base_cost": 80,
        "duration": "1-2h",
        "category": "technical_excellence",
        "tags": ["code-review", "lightning", "development"]
    },
    "documentation_creation": {
        "name": "Création de Documentation",
        "description": "Rédaction de guides techniques personnalisés",
        "base_cost": 100,
        "duration": "2-3h",
        "category": "knowledge_transfer",
        "tags": ["documentation", "guides", "technical-writing"]
    }
}

# Configuration des événements communautaires
COMMUNITY_EVENTS = {
    "weekly_mentoring_challenge": {
        "name": "Défi Mentoring Hebdomadaire",
        "description": "Participer à 3+ sessions de mentoring dans la semaine",
        "reward_tokens": 100,
        "bonus_multiplier": 1.2,
        "requirements": {"mentoring_sessions": 3, "timeframe_days": 7}
    },
    "documentation_month": {
        "name": "Mois de la Documentation", 
        "description": "Créer des guides communautaires pendant le mois",
        "reward_tokens": 200,
        "bonus_multiplier": 1.5,
        "requirements": {"documentation_created": 2, "timeframe_days": 30}
    },
    "newcomer_helper": {
        "name": "Assistant des Nouveaux",
        "description": "Aider 5+ nouveaux membres dans leurs premiers pas",
        "reward_tokens": 150,
        "bonus_multiplier": 1.3,
        "requirements": {"newcomers_helped": 5, "timeframe_days": 14}
    }
}

# Gamification et badges
ACHIEVEMENT_BADGES = {
    "first_steps": "🎯",
    "beginner_mentor": "🎓", 
    "community_expert": "⭐",
    "regular_contributor": "🔥",
    "quality_helper": "💎",
    "lightning_master": "⚡",
    "business_advisor": "💼",
    "code_ninja": "🥷",
    "documentation_hero": "📚",
    "social_butterfly": "🦋"
}

# Messages d'encouragement
ENCOURAGEMENT_MESSAGES = [
    "Excellent travail ! Votre aide fait vraiment la différence dans la communauté.",
    "Merci de partager vos connaissances ! C'est ce qui rend T4G si spécial.",
    "Votre expertise aide d'autres à grandir. Continuez comme ça !",
    "Chaque contribution compte. Vous construisez un écosystème plus fort.",
    "Bravo ! Votre engagement inspire les autres membres de la communauté."
]

# Configuration des notifications
NOTIFICATION_TEMPLATES = {
    "tokens_earned": {
        "title": "Tokens T4G gagnés !",
        "message": "Vous avez gagné {tokens} T4G pour {action}. Nouveau solde: {balance} T4G"
    },
    "level_up": {
        "title": "Félicitations ! Niveau supérieur atteint !",
        "message": "Vous êtes maintenant niveau {new_level}. Nouveaux avantages débloqués !"
    },
    "achievement_unlocked": {
        "title": "Achievement débloqué ! {badge}",
        "message": "{achievement_name}: {description}. Bonus: +{bonus_tokens} T4G"
    },
    "service_booked": {
        "title": "Nouveau service réservé",
        "message": "{client_name} a réservé votre service '{service_name}' pour {tokens} T4G"
    },
    "mentoring_completed": {
        "title": "Session de mentoring terminée",
        "message": "Session avec {mentee_name} terminée. Tokens gagnés: {tokens} T4G"
    }
}

# Instantiation de la configuration
config = T4GConfig()