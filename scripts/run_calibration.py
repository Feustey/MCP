#!/usr/bin/env python3
"""
Script principal pour exécuter le protocole de calibration.
Ce script permet d'exécuter le protocole de calibration depuis la ligne de commande.

Dernière mise à jour: 8 mai 2025
"""

import sys
import os
from pathlib import Path
import logging

# Configurer les chemins d'importation
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
sys.path.append(str(root_dir))

# Importer les modules de calibration
from src.tools.simulator.calibration_cli import run_calibration

if __name__ == "__main__":
    # Configurer le logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/calibration.log")
        ]
    )
    
    # Exécuter la CLI
    run_calibration() 