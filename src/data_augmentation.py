from typing import Dict, Any, List
import numpy as np
from datetime import datetime, timedelta

class DataAugmentor:
    def __init__(self):
        self.noise_factor = 0.1
        
    def add_gaussian_noise(self, data: float) -> float:
        """Ajoute un bruit gaussien aux données numériques"""
        return data + np.random.normal(0, self.noise_factor * abs(data))
    
    def time_shift(self, timestamp: datetime, max_shift_hours: int = 24) -> datetime:
        """Décale légèrement les timestamps"""
        shift = timedelta(hours=np.random.randint(-max_shift_hours, max_shift_hours))
        return timestamp + shift
    
    def augment_node_data(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Augmente les données d'un nœud"""
        augmented = node_data.copy()
        
        # Augmenter les métriques numériques
        if 'capacity' in augmented:
            augmented['capacity'] = self.add_gaussian_noise(float(augmented['capacity']))
        if 'num_channels' in augmented:
            augmented['num_channels'] = max(1, int(self.add_gaussian_noise(float(augmented['num_channels']))))
            
        # Décaler les timestamps
        if 'last_update' in augmented:
            augmented['last_update'] = self.time_shift(augmented['last_update'])
            
        return augmented 