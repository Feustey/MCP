import json
from typing import Dict, List, Optional, Any
import redis
from ..training.metrics import MetricCollection

class RedisMetricsStorage:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        prefix: str = "metrics:"
    ):
        """Initialise le stockage Redis pour les métriques"""
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True
        )
        self.prefix = prefix

    def save_metrics(
        self,
        run_id: str,
        metrics: Dict[str, List[float]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Sauvegarde les métriques dans Redis"""
        # Sauvegarder les métriques
        metrics_key = f"{self.prefix}{run_id}:values"
        self.redis_client.hset(
            metrics_key,
            mapping={k: json.dumps(v) for k, v in metrics.items()}
        )

        # Sauvegarder les métadonnées si fournies
        if metadata:
            metadata_key = f"{self.prefix}{run_id}:metadata"
            self.redis_client.hset(
                metadata_key,
                mapping={k: json.dumps(v) for k, v in metadata.items()}
            )

    def load_metrics(
        self,
        run_id: str
    ) -> Dict[str, List[float]]:
        """Charge les métriques depuis Redis"""
        metrics_key = f"{self.prefix}{run_id}:values"
        metrics_data = self.redis_client.hgetall(metrics_key)
        
        if not metrics_data:
            return {}
        
        return {
            k: json.loads(v) for k, v in metrics_data.items()
        }

    def load_metadata(
        self,
        run_id: str
    ) -> Dict[str, Any]:
        """Charge les métadonnées depuis Redis"""
        metadata_key = f"{self.prefix}{run_id}:metadata"
        metadata = self.redis_client.hgetall(metadata_key)
        
        if not metadata:
            return {}
        
        return {
            k: json.loads(v) for k, v in metadata.items()
        }

    def list_runs(self) -> List[str]:
        """Liste tous les runs disponibles"""
        pattern = f"{self.prefix}:*"
        keys = self.redis_client.keys(pattern)
        runs = set()
        for key in keys:
            parts = key.split(":")
            if len(parts) > 1:
                runs.add(parts[1])
        return list(runs)

    def delete_run(self, run_id: str) -> None:
        """Supprime un run et ses métriques associées"""
        metrics_key = f"{self.prefix}{run_id}:values"
        metadata_key = f"{self.prefix}{run_id}:metadata"
        self.redis_client.delete(metrics_key, metadata_key) 