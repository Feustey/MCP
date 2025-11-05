"""
Tests unitaires et d'intégration pour les rapports quotidiens

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 5 novembre 2025
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from motor.motor_asyncio import AsyncIOMotorDatabase

from config.models.daily_reports import (
    DailyReport,
    UserProfile,
    ReportSummary,
    ReportMetrics,
    ReportRecommendation,
    ReportAlert,
    ReportTrends
)
from app.services.daily_report_generator import DailyReportGenerator


@pytest.fixture
def mock_db():
    """Mock de la base de données MongoDB"""
    db = Mock(spec=AsyncIOMotorDatabase)
    
    # Mock collections
    db.user_profiles = Mock()
    db.daily_reports = Mock()
    db.nodes = Mock()
    db.node_metrics_history = Mock()
    
    return db


@pytest.fixture
def mock_rag_workflow():
    """Mock du système RAG"""
    rag = AsyncMock()
    rag.query = AsyncMock(return_value={
        "answer": "Test analysis",
        "recommendations": []
    })
    rag.index_document = AsyncMock(return_value=True)
    return rag


@pytest.fixture
def sample_user():
    """Utilisateur de test avec pubkey"""
    return {
        "id": "user_123",
        "tenant_id": "tenant_123",
        "lightning_pubkey": "02" + "a" * 64,
        "node_alias": "TestNode",
        "daily_report_enabled": True,
        "daily_report_schedule": "0 6 * * *",
        "last_report_generated": None,
        "total_reports_generated": 0
    }


@pytest.fixture
def sample_node_data():
    """Données de nœud de test"""
    return {
        "pubkey": "02" + "a" * 64,
        "local": {
            "alias": "TestNode",
            "capacity": 1000000,
            "channels": 10,
            "score": 85.5,
            "metrics": {
                "forwarding_rate_24h": 0.0025,
                "revenue_sats_24h": 15000
            }
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@pytest.fixture
async def report_generator(mock_db, mock_rag_workflow):
    """Instance du générateur de rapports avec mocks"""
    return DailyReportGenerator(
        db=mock_db,
        rag_workflow=mock_rag_workflow,
        redis_ops=None
    )


# ============================================================================
# TESTS DES MODÈLES
# ============================================================================

class TestDailyReportModels:
    """Tests des modèles Pydantic"""
    
    def test_user_profile_creation(self):
        """Test création d'un profil utilisateur"""
        profile = UserProfile(
            email="test@example.com",
            username="testuser",
            lightning_pubkey="02" + "a" * 64,
            node_alias="TestNode",
            daily_report_enabled=True
        )
        
        assert profile.email == "test@example.com"
        assert profile.lightning_pubkey == "02" + "a" * 64
        assert profile.daily_report_enabled is True
        assert profile.total_reports_generated == 0
    
    def test_user_profile_pubkey_validation(self):
        """Test validation de la pubkey Lightning"""
        # Pubkey valide
        profile = UserProfile(
            email="test@example.com",
            username="testuser",
            lightning_pubkey="02" + "a" * 64
        )
        assert len(profile.lightning_pubkey) == 66
        
        # Pubkey invalide (trop courte)
        with pytest.raises(ValueError):
            UserProfile(
                email="test@example.com",
                username="testuser",
                lightning_pubkey="02abc"
            )
    
    def test_daily_report_creation(self):
        """Test création d'un rapport quotidien"""
        report = DailyReport(
            user_id="user_123",
            node_pubkey="02" + "a" * 64,
            node_alias="TestNode"
        )
        
        assert report.user_id == "user_123"
        assert report.generation_status == "pending"
        assert report.retry_count == 0
        assert report.rag_indexed is False
    
    def test_report_summary_validation(self):
        """Test validation du résumé de rapport"""
        summary = ReportSummary(
            overall_score=85.5,
            score_delta_24h=2.3,
            status="healthy",
            capacity_btc=0.01,
            channels_count=10,
            forwarding_rate_24h=0.0025,
            revenue_sats_24h=15000
        )
        
        assert summary.overall_score == 85.5
        assert summary.status == "healthy"
        
        # Score hors limites
        with pytest.raises(ValueError):
            ReportSummary(
                overall_score=150,  # > 100
                score_delta_24h=0,
                status="healthy",
                capacity_btc=0,
                channels_count=0,
                forwarding_rate_24h=0,
                revenue_sats_24h=0
            )
    
    def test_report_recommendation_creation(self):
        """Test création d'une recommandation"""
        rec = ReportRecommendation(
            priority="high",
            category="liquidity",
            title="Test recommendation",
            description="Test description",
            impact_score=8.5,
            suggested_action="Do something",
            estimated_gain_sats_month=50000
        )
        
        assert rec.priority == "high"
        assert rec.impact_score == 8.5
        assert rec.estimated_gain_sats_month == 50000


# ============================================================================
# TESTS DU GÉNÉRATEUR DE RAPPORTS
# ============================================================================

class TestDailyReportGenerator:
    """Tests du service de génération de rapports"""
    
    @pytest.mark.asyncio
    async def test_generate_report_for_user(
        self, 
        report_generator, 
        mock_db,
        sample_user,
        sample_node_data
    ):
        """Test génération d'un rapport pour un utilisateur"""
        
        # Mock des appels DB
        mock_db.daily_reports.insert_one = AsyncMock()
        mock_db.daily_reports.update_one = AsyncMock()
        mock_db.user_profiles.update_one = AsyncMock()
        mock_db.nodes.find_one = AsyncMock(return_value=sample_node_data["local"])
        mock_db.node_metrics_history.find = Mock()
        mock_db.node_metrics_history.find.return_value.to_list = AsyncMock(return_value=[])
        mock_db.daily_reports.find = Mock()
        mock_db.daily_reports.find.return_value.to_list = AsyncMock(return_value=[])
        
        # Mock collecte de données
        with patch.object(
            report_generator,
            '_collect_node_data',
            return_value=sample_node_data
        ):
            await report_generator.generate_report_for_user(sample_user)
        
        # Vérifier que le rapport a été créé
        assert mock_db.daily_reports.insert_one.called
        
        # Vérifier que le profil utilisateur a été mis à jour
        assert mock_db.user_profiles.update_one.called
    
    @pytest.mark.asyncio
    async def test_collect_node_data(
        self,
        report_generator,
        mock_db,
        sample_node_data
    ):
        """Test collecte de données d'un nœud"""
        
        mock_db.nodes.find_one = AsyncMock(return_value=sample_node_data["local"])
        mock_db.node_metrics_history.find = Mock()
        mock_db.node_metrics_history.find.return_value.to_list = AsyncMock(return_value=[])
        
        node_data = await report_generator._collect_node_data("02" + "a" * 64)
        
        assert node_data["pubkey"] == "02" + "a" * 64
        assert "local" in node_data
        assert node_data["local"]["alias"] == "TestNode"
    
    def test_generate_summary(
        self,
        report_generator,
        sample_node_data
    ):
        """Test génération du résumé"""
        
        analysis = {"recommendations": []}
        summary = report_generator._generate_summary(sample_node_data, analysis)
        
        assert summary is not None
        assert summary.overall_score == 85.5
        assert summary.channels_count == 10
        assert summary.revenue_sats_24h == 15000
    
    def test_generate_metrics(
        self,
        report_generator,
        sample_node_data
    ):
        """Test génération des métriques"""
        
        metrics = report_generator._generate_metrics(sample_node_data)
        
        assert metrics is not None
        assert metrics.capacity["total_sats"] == 1000000
        assert metrics.channels["active"] == 10
    
    def test_detect_alerts_no_channels(
        self,
        report_generator
    ):
        """Test détection d'alertes - pas de canaux"""
        
        node_data = {
            "local": {
                "channels": 0
            }
        }
        analysis = {}
        
        alerts = report_generator._detect_alerts(node_data, analysis)
        
        assert len(alerts) > 0
        assert alerts[0].type == "no_channels"
        assert alerts[0].severity == "warning"
    
    @pytest.mark.asyncio
    async def test_run_with_multiple_users(
        self,
        report_generator,
        mock_db,
        sample_user
    ):
        """Test génération pour plusieurs utilisateurs"""
        
        # Mock 3 utilisateurs
        users = [
            {**sample_user, "id": f"user_{i}", "lightning_pubkey": f"02{'a' * 64}"}
            for i in range(3)
        ]
        
        mock_db.user_profiles.find = Mock()
        mock_db.user_profiles.find.return_value.to_list = AsyncMock(return_value=users)
        
        # Mock la génération pour chaque user
        with patch.object(
            report_generator,
            'generate_report_for_user',
            new=AsyncMock()
        ) as mock_generate:
            await report_generator.run()
            
            # Vérifier que generate_report_for_user a été appelé 3 fois
            assert mock_generate.call_count == 3
    
    @pytest.mark.asyncio
    async def test_report_generation_with_timeout(
        self,
        report_generator,
        mock_db,
        sample_user
    ):
        """Test gestion du timeout"""
        
        # Configurer un timeout très court
        report_generator.timeout_seconds = 0.1
        
        mock_db.daily_reports.insert_one = AsyncMock()
        mock_db.daily_reports.update_one = AsyncMock()
        
        # Mock une collecte très lente
        async def slow_collect(*args):
            await asyncio.sleep(1)  # Plus long que le timeout
            return {}
        
        with patch.object(
            report_generator,
            '_collect_node_data',
            side_effect=slow_collect
        ):
            await report_generator.generate_report_for_user(sample_user)
        
        # Vérifier que le rapport a été marqué en échec
        update_calls = mock_db.daily_reports.update_one.call_args_list
        # Au moins un appel pour marquer le rapport en échec
        assert any("failed" in str(call) for call in update_calls)


# ============================================================================
# TESTS D'INTÉGRATION DES ENDPOINTS
# ============================================================================

class TestDailyReportsEndpoints:
    """Tests des endpoints API"""
    
    @pytest.mark.asyncio
    async def test_enable_daily_report_endpoint(self):
        """Test activation du workflow via API"""
        # TODO: Implémenter avec TestClient FastAPI
        pass
    
    @pytest.mark.asyncio
    async def test_get_latest_report_endpoint(self):
        """Test récupération du dernier rapport via API"""
        # TODO: Implémenter avec TestClient FastAPI
        pass
    
    @pytest.mark.asyncio
    async def test_get_report_history_endpoint(self):
        """Test récupération de l'historique via API"""
        # TODO: Implémenter avec TestClient FastAPI
        pass


# ============================================================================
# TESTS DU SCHEDULER
# ============================================================================

class TestDailyReportScheduler:
    """Tests du scheduler"""
    
    def test_scheduler_initialization(self):
        """Test initialisation du scheduler"""
        from app.scheduler.daily_report_scheduler import DailyReportScheduler
        
        mock_generator = Mock()
        scheduler = DailyReportScheduler(mock_generator)
        
        assert scheduler.report_generator == mock_generator
        assert scheduler.schedule_hour == 6
        assert scheduler.schedule_minute == 0
    
    def test_scheduler_start_stop(self):
        """Test démarrage et arrêt du scheduler"""
        from app.scheduler.daily_report_scheduler import DailyReportScheduler
        
        mock_generator = Mock()
        scheduler = DailyReportScheduler(mock_generator)
        
        scheduler.start()
        assert scheduler.scheduler.running
        
        scheduler.stop()
        assert not scheduler.scheduler.running
    
    def test_scheduler_get_status(self):
        """Test récupération du statut"""
        from app.scheduler.daily_report_scheduler import DailyReportScheduler
        
        mock_generator = Mock()
        scheduler = DailyReportScheduler(mock_generator)
        
        status = scheduler.get_status()
        
        assert "enabled" in status
        assert "running" in status
        assert "schedule" in status
        assert status["schedule"] == "06:00 UTC"


# ============================================================================
# FIXTURES POUR TESTS D'INTÉGRATION
# ============================================================================

@pytest.fixture
def test_database():
    """Base de données de test (à configurer selon l'environnement)"""
    # TODO: Configurer une base de données de test
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

