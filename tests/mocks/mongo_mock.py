from typing import Dict, List, Optional
from datetime import datetime

class MockMongoDB:
    def __init__(self):
        self.metrics = {}
        self.history = {}
    
    def save_metrics(self, run_id: str, model_version: str, metrics: Dict, hyperparameters: Dict) -> bool:
        self.metrics[run_id] = {
            'run_id': run_id,
            'model_version': model_version,
            'metrics': metrics,
            'hyperparameters': hyperparameters,
            'timestamp': datetime.now()
        }
        if model_version not in self.history:
            self.history[model_version] = []
        self.history[model_version].append(self.metrics[run_id])
        return True
    
    def get_metrics_history(self, model_version: str) -> List[Dict]:
        return self.history.get(model_version, [])
    
    def get_latest_metrics(self, model_version: str) -> Optional[Dict]:
        history = self.history.get(model_version, [])
        return history[-1] if history else None
    
    def delete_metrics(self, run_id: str) -> bool:
        if run_id in self.metrics:
            model_version = self.metrics[run_id]['model_version']
            self.history[model_version] = [m for m in self.history[model_version] if m['run_id'] != run_id]
            del self.metrics[run_id]
            return True
        return False 