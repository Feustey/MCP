from typing import List, Any, Iterator
import numpy as np

class DataBatcher:
    def __init__(self, batch_size: int = 32):
        self.batch_size = batch_size
        
    def create_batches(self, data: List[Any]) -> Iterator[List[Any]]:
        """Crée des batchs de données de taille fixe"""
        for i in range(0, len(data), self.batch_size):
            yield data[i:i + self.batch_size]
            
    def shuffle_and_batch(self, data: List[Any]) -> Iterator[List[Any]]:
        """Mélange les données et crée des batchs"""
        indices = np.random.permutation(len(data))
        shuffled_data = [data[i] for i in indices]
        return self.create_batches(shuffled_data) 