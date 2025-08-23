"""
Token4Good (T4G) - Modèles de données pour le système de tokens et marketplace
"""
from datetime import datetime
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


class T4GTokenAction(str, Enum):
    """Types d'actions pour gagner des tokens T4G"""
    MENTORING = "mentoring"
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"
    SUPPORT_TECHNIQUE = "support_technique"
    FORMATION = "formation"
    CONTRIBUTION_COMMUNAUTAIRE = "contribution_communautaire"
    PARRAINAGE = "parrainage"
    WEBINAIRE = "webinaire"


class ServiceCategory(str, Enum):
    """Catégories de services dans la marketplace"""
    TECHNICAL_EXCELLENCE = "technical_excellence"
    BUSINESS_GROWTH = "business_growth"
    KNOWLEDGE_TRANSFER = "knowledge_transfer"
    COMMUNITY_SERVICES = "community_services"


class UserLevel(str, Enum):
    """Niveaux d'engagement des utilisateurs"""
    CONTRIBUTEUR = "contributeur"      # 0-500 T4G
    MENTOR = "mentor"                  # 500-1500 T4G
    EXPERT = "expert"                  # 1500+ T4G


class T4GTransaction(BaseModel):
    """Modèle pour les transactions de tokens T4G"""
    id: str
    user_id: str
    action_type: T4GTokenAction
    tokens_earned: int
    tokens_spent: int = 0
    description: str
    metadata: Dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    impact_score: float = Field(default=1.0, description="Score d'impact de 0 à 1")


class MentoringSession(BaseModel):
    """Session de mentoring"""
    id: str
    mentor_id: str
    mentee_id: str
    topic: str
    category: Literal["lightning_network", "dazbox_setup", "business_dev", "dazpay_integration"]
    duration_minutes: int
    tokens_reward: int
    status: Literal["scheduled", "in_progress", "completed", "cancelled"]
    scheduled_at: datetime
    completed_at: Optional[datetime] = None
    feedback: Optional[Dict] = None
    impact_metrics: Optional[Dict] = None


class MarketplaceService(BaseModel):
    """Service disponible dans la marketplace T4G"""
    id: str
    name: str
    description: str
    category: ServiceCategory
    provider_id: str
    token_cost: int
    estimated_duration: str
    requirements: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    rating: Optional[float] = None
    total_bookings: int = 0


class ServiceBooking(BaseModel):
    """Réservation d'un service marketplace"""
    id: str
    service_id: str
    client_id: str
    provider_id: str
    tokens_cost: int
    status: Literal["pending", "confirmed", "in_progress", "completed", "cancelled"]
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    feedback: Optional[Dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserProfile(BaseModel):
    """Profil utilisateur T4G"""
    user_id: str
    username: str
    email: str
    total_tokens_earned: int = 0
    total_tokens_spent: int = 0
    current_balance: int = 0
    user_level: UserLevel = UserLevel.CONTRIBUTEUR
    skills: List[str] = Field(default_factory=list)
    interests: List[str] = Field(default_factory=list)
    reputation_score: float = Field(default=0.5, description="Score de réputation de 0 à 1")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: Optional[datetime] = None
    
    @property
    def available_balance(self) -> int:
        """Solde disponible de tokens"""
        return self.total_tokens_earned - self.total_tokens_spent
    
    def update_level(self):
        """Met à jour le niveau en fonction du total de tokens gagnés"""
        if self.total_tokens_earned >= 1500:
            self.user_level = UserLevel.EXPERT
        elif self.total_tokens_earned >= 500:
            self.user_level = UserLevel.MENTOR
        else:
            self.user_level = UserLevel.CONTRIBUTEUR


class T4GMarketplaceStats(BaseModel):
    """Statistiques de la marketplace T4G"""
    total_users: int
    total_transactions: int
    total_tokens_circulation: int
    active_services: int
    avg_session_rating: float
    top_skills: List[Dict[str, int]]
    monthly_growth: float


# Configuration des services et récompenses
T4G_SERVICE_CATALOG = {
    # Mentoring Modules (50-100 T4G/session)
    "lightning_mastery": {
        "name": "Lightning Network Mastery",
        "category": ServiceCategory.TECHNICAL_EXCELLENCE,
        "base_cost": 50,
        "duration": "1h",
        "description": "Accompagnement personnalisé sur la gestion de nœuds Lightning"
    },
    "dazbox_setup": {
        "name": "DazBox Setup Pro",
        "category": ServiceCategory.TECHNICAL_EXCELLENCE,
        "base_cost": 75,
        "duration": "1.5h",
        "description": "Installation et optimisation guidée DazBox"
    },
    "business_development": {
        "name": "Bitcoin Business Development",
        "category": ServiceCategory.BUSINESS_GROWTH,
        "base_cost": 100,
        "duration": "2h",
        "description": "Stratégies d'intégration Lightning pour entreprises"
    },
    "dazpay_integration": {
        "name": "DazPay Integration",
        "category": ServiceCategory.TECHNICAL_EXCELLENCE,
        "base_cost": 60,
        "duration": "1h",
        "description": "Support technique API et e-commerce DazPay"
    },
    
    # Premium Services (120-400 T4G)
    "dazia_premium": {
        "name": "Support DazIA Premium",
        "category": ServiceCategory.TECHNICAL_EXCELLENCE,
        "base_cost": 200,
        "duration": "2h",
        "description": "Optimisation IA avancée personnalisée"
    },
    "node_audit": {
        "name": "Audit de Nœud Lightning",
        "category": ServiceCategory.TECHNICAL_EXCELLENCE,
        "base_cost": 150,
        "duration": "3h",
        "description": "Analyse complète et recommandations"
    },
    "strategic_consultation": {
        "name": "Consultation Stratégique",
        "category": ServiceCategory.BUSINESS_GROWTH,
        "base_cost": 250,
        "duration": "2h",
        "description": "ROI et scaling Lightning Network"
    },
    "lightning_certification": {
        "name": "Certification Lightning Expert",
        "category": ServiceCategory.KNOWLEDGE_TRANSFER,
        "base_cost": 400,
        "duration": "1 semaine",
        "description": "Programme complet de certification"
    }
}

# Configuration des récompenses par action
T4G_REWARD_SYSTEM = {
    T4GTokenAction.MENTORING: {
        "base_reward": 50,
        "multipliers": {
            "session_rating_5": 1.5,
            "session_rating_4": 1.2,
            "long_session": 1.3,  # > 2h
            "repeat_mentee": 1.1
        }
    },
    T4GTokenAction.CODE_REVIEW: {
        "base_reward": 80,
        "multipliers": {
            "critical_fix": 1.5,
            "detailed_feedback": 1.2,
            "quick_turnaround": 1.1
        }
    },
    T4GTokenAction.DOCUMENTATION: {
        "base_reward": 100,
        "multipliers": {
            "comprehensive": 1.4,
            "with_examples": 1.2,
            "translated": 1.3
        }
    },
    T4GTokenAction.SUPPORT_TECHNIQUE: {
        "base_reward": 40,
        "multipliers": {
            "urgent_issue": 1.3,
            "complex_problem": 1.2,
            "follow_up": 1.1
        }
    },
    T4GTokenAction.PARRAINAGE: {
        "base_reward": 30,
        "multipliers": {
            "active_new_member": 2.0,
            "successful_onboarding": 1.5
        }
    }
}