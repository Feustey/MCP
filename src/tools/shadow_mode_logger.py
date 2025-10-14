"""
Shadow Mode Logger - Logging des décisions en mode observation
Dernière mise à jour: 12 octobre 2025
Version: 1.0.0

En mode Shadow:
- Aucune action réelle exécutée
- Toutes les recommandations loggées
- Comparaison possible avec actions manuelles
- Rapports quotidiens générés
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import json

import structlog

from src.optimizers.heuristics_engine import ChannelScore
from src.optimizers.decision_engine import Decision, DecisionType

logger = structlog.get_logger(__name__)


@dataclass
class ShadowDecisionLog:
    """Log d'une décision en shadow mode"""
    decision_id: str
    channel_id: str
    timestamp: datetime
    score: ChannelScore
    decision: Decision
    would_execute: bool  # Si cette décision aurait été exécutée
    manual_action: Optional[str] = None  # Action manuelle prise (si renseignée)
    expert_validation: Optional[bool] = None  # Validation par expert
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "decision_id": self.decision_id,
            "channel_id": self.channel_id,
            "timestamp": self.timestamp.isoformat(),
            "score": self.score.to_dict(),
            "decision": self.decision.to_dict(),
            "would_execute": self.would_execute,
            "manual_action": self.manual_action,
            "expert_validation": self.expert_validation,
            "notes": self.notes
        }


class ShadowModeLogger:
    """
    Logger pour mode Shadow
    
    Responsabilités:
    - Logger toutes les décisions simulées
    - Générer rapports quotidiens
    - Comparer avec actions manuelles
    - Calculer métriques de performance
    """
    
    def __init__(
        self,
        log_path: str = "data/reports/shadow_mode",
        storage_backend: Optional[Any] = None,
        enable_daily_reports: bool = True
    ):
        """
        Initialise le logger shadow mode
        
        Args:
            log_path: Répertoire pour les logs
            storage_backend: MongoDB collection pour persistance
            enable_daily_reports: Générer rapports quotidiens
        """
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)
        
        self.storage = storage_backend
        self.enable_daily_reports = enable_daily_reports
        
        # Cache en mémoire (pour la journée)
        self._today_logs: List[ShadowDecisionLog] = []
        self._last_report_date: Optional[datetime] = None
        
        logger.info(
            "shadow_mode_logger_initialized",
            log_path=str(self.log_path),
            daily_reports=enable_daily_reports
        )
    
    async def log_decision(
        self,
        channel_id: str,
        score: ChannelScore,
        decision: Decision,
        would_execute: bool = True
    ) -> str:
        """
        Logge une décision shadow
        
        Args:
            channel_id: ID du canal
            score: Score calculé
            decision: Décision générée
            would_execute: Si la décision aurait été exécutée (hors shadow)
            
        Returns:
            ID de la décision loggée
        """
        import hashlib
        
        # Générer ID unique
        data = f"{channel_id}{datetime.now().isoformat()}"
        decision_id = hashlib.sha256(data.encode()).hexdigest()[:16]
        
        # Créer le log
        shadow_log = ShadowDecisionLog(
            decision_id=decision_id,
            channel_id=channel_id,
            timestamp=datetime.now(),
            score=score,
            decision=decision,
            would_execute=would_execute
        )
        
        # Ajouter au cache du jour
        self._today_logs.append(shadow_log)
        
        # Sauvegarder dans fichier JSON
        await self._save_to_file(shadow_log)
        
        # Sauvegarder dans MongoDB
        if self.storage:
            await self._save_to_storage(shadow_log)
        
        logger.info(
            "shadow_decision_logged",
            decision_id=decision_id,
            channel_id=channel_id,
            decision_type=decision.decision_type.value,
            score=score.overall_score,
            would_execute=would_execute
        )
        
        # Vérifier si on doit générer un rapport quotidien
        if self.enable_daily_reports:
            await self._check_daily_report()
        
        return decision_id
    
    async def _save_to_file(self, shadow_log: ShadowDecisionLog):
        """Sauvegarde dans un fichier JSON"""
        date_str = shadow_log.timestamp.strftime("%Y%m%d")
        file_path = self.log_path / f"shadow_decisions_{date_str}.jsonl"
        
        # Append mode (JSONL = JSON Lines)
        with open(file_path, 'a') as f:
            f.write(json.dumps(shadow_log.to_dict()) + "\n")
    
    async def _save_to_storage(self, shadow_log: ShadowDecisionLog):
        """Sauvegarde dans MongoDB"""
        if not self.storage:
            return
        
        await self.storage.insert_one({
            "type": "shadow_decision",
            **shadow_log.to_dict()
        })
    
    async def _check_daily_report(self):
        """Vérifie si un rapport quotidien doit être généré"""
        today = datetime.now().date()
        
        if self._last_report_date is None or self._last_report_date != today:
            # Nouveau jour, générer le rapport d'hier
            if self._last_report_date is not None:
                await self.generate_daily_report(self._last_report_date)
            
            self._last_report_date = today
            self._today_logs = []  # Reset pour aujourd'hui
    
    async def generate_daily_report(
        self,
        date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Génère un rapport quotidien
        
        Args:
            date: Date du rapport (None = hier)
            
        Returns:
            Rapport formaté
        """
        if date is None:
            date = (datetime.now() - timedelta(days=1)).date()
        
        logger.info("generating_daily_report", date=date)
        
        # Charger les logs du jour
        logs = await self._load_logs_for_date(date)
        
        if not logs:
            logger.warning("no_logs_for_date", date=date)
            return {}
        
        # Calculer les statistiques
        stats = self._calculate_stats(logs)
        
        # Créer le rapport
        report = {
            "date": date.isoformat(),
            "total_decisions": len(logs),
            "statistics": stats,
            "decisions_by_type": self._group_by_type(logs),
            "score_distribution": self._analyze_scores(logs),
            "would_execute_count": len([l for l in logs if l.would_execute]),
            "top_recommendations": self._get_top_recommendations(logs, limit=10),
            "generated_at": datetime.now().isoformat()
        }
        
        # Sauvegarder le rapport
        report_path = self.log_path / f"daily_report_{date.isoformat()}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(
            "daily_report_generated",
            date=date,
            path=str(report_path),
            decisions=len(logs)
        )
        
        return report
    
    async def _load_logs_for_date(self, date: datetime.date) -> List[ShadowDecisionLog]:
        """Charge les logs d'une date spécifique"""
        date_str = date.strftime("%Y%m%d")
        file_path = self.log_path / f"shadow_decisions_{date_str}.jsonl"
        
        if not file_path.exists():
            return []
        
        logs = []
        with open(file_path, 'r') as f:
            for line in f:
                data = json.loads(line)
                # Reconstruction simplifiée (pour stats only)
                logs.append(data)
        
        return logs
    
    def _calculate_stats(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcule les statistiques des logs"""
        if not logs:
            return {}
        
        decision_types = {}
        confidence_levels = {}
        total_score = 0
        
        for log in logs:
            # Count par type de décision
            decision_type = log["decision"]["decision_type"]
            decision_types[decision_type] = decision_types.get(decision_type, 0) + 1
            
            # Count par niveau de confiance
            confidence = log["decision"]["confidence"]
            confidence_levels[confidence] = confidence_levels.get(confidence, 0) + 1
            
            # Score moyen
            total_score += log["score"]["overall_score"]
        
        return {
            "decision_types": decision_types,
            "confidence_levels": confidence_levels,
            "average_score": total_score / len(logs),
            "total_channels_analyzed": len(set(log["channel_id"] for log in logs))
        }
    
    def _group_by_type(self, logs: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Groupe les décisions par type"""
        grouped = {}
        
        for log in logs:
            decision_type = log["decision"]["decision_type"]
            if decision_type not in grouped:
                grouped[decision_type] = []
            grouped[decision_type].append(log)
        
        return grouped
    
    def _analyze_scores(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyse la distribution des scores"""
        scores = [log["score"]["overall_score"] for log in logs]
        
        if not scores:
            return {}
        
        return {
            "min": min(scores),
            "max": max(scores),
            "average": sum(scores) / len(scores),
            "median": sorted(scores)[len(scores) // 2],
            "distribution": {
                "excellent (>0.8)": len([s for s in scores if s > 0.8]),
                "good (0.6-0.8)": len([s for s in scores if 0.6 <= s <= 0.8]),
                "average (0.4-0.6)": len([s for s in scores if 0.4 <= s < 0.6]),
                "poor (0.2-0.4)": len([s for s in scores if 0.2 <= s < 0.4]),
                "critical (<0.2)": len([s for s in scores if s < 0.2])
            }
        }
    
    def _get_top_recommendations(
        self,
        logs: List[Dict[str, Any]],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retourne les top recommandations triées par impact potentiel"""
        # Filtrer les décisions actionnables
        actionable = [
            log for log in logs
            if log["decision"]["decision_type"] != "no_action"
        ]
        
        # Trier par confidence et score
        sorted_logs = sorted(
            actionable,
            key=lambda l: (l["decision"]["confidence_score"], l["score"]["overall_score"]),
            reverse=False  # Pires scores en premier
        )
        
        return [
            {
                "channel_id": log["channel_id"],
                "score": log["score"]["overall_score"],
                "decision": log["decision"]["decision_type"],
                "confidence": log["decision"]["confidence"],
                "reasoning": log["decision"]["reasoning"]
            }
            for log in sorted_logs[:limit]
        ]
    
    async def get_summary_stats(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Génère un résumé des derniers jours
        
        Args:
            days: Nombre de jours à analyser
            
        Returns:
            Statistiques agrégées
        """
        all_logs = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i+1)).date()
            logs = await self._load_logs_for_date(date)
            all_logs.extend(logs)
        
        if not all_logs:
            return {"error": "No shadow mode data available"}
        
        return {
            "period_days": days,
            "total_decisions": len(all_logs),
            "statistics": self._calculate_stats(all_logs),
            "score_distribution": self._analyze_scores(all_logs),
            "decision_breakdown": self._group_by_type(all_logs)
        }

