"""
Modèles de données pour les rapports quotidiens
Définition des modèles Pydantic pour le système de rapports automatisés

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 5 novembre 2025
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid

from config.models.base import BaseSchema, UserBase


class UserProfile(UserBase):
    """Profil utilisateur étendu pour DazNode avec configuration rapports quotidiens"""
    
    # Informations Lightning
    lightning_pubkey: Optional[str] = Field(
        None, 
        description="Pubkey du nœud Lightning (66 caractères hex)"
    )
    node_alias: Optional[str] = Field(None, description="Alias du nœud")
    
    # Configuration workflow
    daily_report_enabled: bool = Field(
        default=False, 
        description="Workflow quotidien activé"
    )
    daily_report_schedule: str = Field(
        default="0 6 * * *",  # 06:00 UTC par défaut
        description="Schedule cron pour le rapport quotidien"
    )
    notification_preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="Préférences de notification (email, webhook, etc.)"
    )
    
    # Métadonnées
    last_report_generated: Optional[datetime] = None
    total_reports_generated: int = Field(default=0)
    
    @validator("lightning_pubkey")
    def validate_lightning_pubkey(cls, v):
        """Valide le format de la pubkey Lightning"""
        if v is None:
            return v
        if not isinstance(v, str) or len(v) != 66:
            raise ValueError("Lightning pubkey must be 66 hex characters")
        try:
            int(v, 16)  # Vérifie que c'est bien de l'hexadécimal
        except ValueError:
            raise ValueError("Lightning pubkey must be hexadecimal")
        return v.lower()
    
    @validator("daily_report_schedule")
    def validate_cron_schedule(cls, v):
        """Valide le format cron"""
        parts = v.split()
        if len(parts) != 5:
            raise ValueError("Invalid cron schedule format (must be 5 parts)")
        return v
    
    class Config:
        collection = "user_profiles"
        indexes = [
            {"fields": ["lightning_pubkey"], "unique": True, "sparse": True},
            {"fields": ["daily_report_enabled"]},
            {"fields": ["tenant_id", "lightning_pubkey"]},
        ]


class ReportSummary(BaseModel):
    """Résumé exécutif du rapport"""
    overall_score: float = Field(..., ge=0, le=100, description="Score global (0-100)")
    score_delta_24h: float = Field(..., description="Évolution du score sur 24h")
    status: str = Field(..., description="Statut: healthy, warning, critical")
    critical_alerts: int = Field(default=0, ge=0)
    warnings: int = Field(default=0, ge=0)
    capacity_btc: float = Field(..., ge=0, description="Capacité totale en BTC")
    channels_count: int = Field(..., ge=0)
    forwarding_rate_24h: float = Field(..., ge=0)
    revenue_sats_24h: int = Field(..., ge=0)


class ReportMetrics(BaseModel):
    """Métriques détaillées du nœud"""
    capacity: Dict[str, Any] = Field(default_factory=dict)
    channels: Dict[str, Any] = Field(default_factory=dict)
    forwarding: Dict[str, Any] = Field(default_factory=dict)
    fees: Dict[str, Any] = Field(default_factory=dict)
    network: Dict[str, Any] = Field(default_factory=dict)


class ReportRecommendation(BaseModel):
    """Recommandation d'optimisation"""
    priority: str = Field(..., description="Priority: high, medium, low")
    category: str = Field(..., description="Category: liquidity, fees, channels, etc.")
    title: str = Field(..., description="Titre de la recommandation")
    description: str = Field(..., description="Description détaillée")
    impact_score: float = Field(..., ge=0, le=10, description="Impact estimé (0-10)")
    channels_affected: List[str] = Field(default_factory=list)
    suggested_action: str = Field(..., description="Action suggérée")
    estimated_gain_sats_month: Optional[int] = Field(None, ge=0)


class ReportAlert(BaseModel):
    """Alerte détectée sur le nœud"""
    severity: str = Field(..., description="Severity: critical, warning, info")
    type: str = Field(..., description="Type: channel_inactive, low_liquidity, etc.")
    title: str = Field(..., description="Titre de l'alerte")
    description: str = Field(..., description="Description détaillée")
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    requires_action: bool = Field(default=False)


class ReportTrends(BaseModel):
    """Tendances sur plusieurs jours"""
    score_evolution_7d: List[float] = Field(default_factory=list)
    revenue_evolution_7d: List[int] = Field(default_factory=list)
    forward_rate_evolution_7d: List[float] = Field(default_factory=list)
    capacity_evolution_7d: List[int] = Field(default_factory=list)


class DailyReport(BaseSchema):
    """Modèle pour les rapports quotidiens"""
    
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="ID de l'utilisateur")
    node_pubkey: str = Field(..., description="Pubkey du nœud analysé")
    node_alias: Optional[str] = None
    
    # Métadonnées
    report_date: datetime = Field(
        default_factory=lambda: datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
        description="Date du rapport"
    )
    generation_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp de génération"
    )
    report_version: str = Field(default="1.0.0")
    
    # Contenu du rapport
    summary: Optional[ReportSummary] = None
    metrics: Optional[ReportMetrics] = None
    recommendations: List[ReportRecommendation] = Field(default_factory=list)
    alerts: List[ReportAlert] = Field(default_factory=list)
    trends: Optional[ReportTrends] = None
    
    # RAG metadata
    rag_asset_id: Optional[str] = Field(
        None,
        description="ID de l'asset RAG associé"
    )
    rag_indexed: bool = Field(default=False)
    
    # Status
    generation_status: str = Field(
        default="pending",
        description="Status: pending, processing, completed, failed"
    )
    error_message: Optional[str] = None
    retry_count: int = Field(default=0, ge=0)
    
    @validator("generation_status")
    def validate_status(cls, v):
        """Valide le statut"""
        valid_statuses = ["pending", "processing", "completed", "failed"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v
    
    @validator("node_pubkey")
    def validate_pubkey(cls, v):
        """Valide le format de la pubkey"""
        if len(v) != 66:
            raise ValueError("Invalid pubkey format (must be 66 hex characters)")
        return v
    
    class Config:
        collection = "daily_reports"
        indexes = [
            {"fields": ["report_id"], "unique": True},
            {"fields": ["user_id", "report_date"]},
            {"fields": ["node_pubkey", "report_date"]},
            {"fields": ["tenant_id", "report_date"]},
            {"fields": ["generation_status"]},
            {"fields": ["report_date"], "expireAfterSeconds": 7776000}  # 90 jours
        ]


class DailyReportCreate(BaseModel):
    """Modèle pour créer un rapport (usage interne)"""
    user_id: str
    node_pubkey: str
    node_alias: Optional[str] = None


class DailyReportUpdate(BaseModel):
    """Modèle pour mettre à jour un rapport"""
    summary: Optional[ReportSummary] = None
    metrics: Optional[ReportMetrics] = None
    recommendations: Optional[List[ReportRecommendation]] = None
    alerts: Optional[List[ReportAlert]] = None
    trends: Optional[ReportTrends] = None
    generation_status: Optional[str] = None
    error_message: Optional[str] = None


class DailyReportResponse(BaseModel):
    """Réponse API pour un rapport"""
    status: str
    report: DailyReport


class DailyReportListResponse(BaseModel):
    """Réponse API pour une liste de rapports"""
    status: str
    reports: List[DailyReport]
    pagination: Dict[str, Any]


class WorkflowStatusResponse(BaseModel):
    """Réponse pour le statut du workflow"""
    enabled: bool
    schedule: str
    last_report: Optional[datetime] = None
    total_reports: int
    next_report: Optional[str] = None

