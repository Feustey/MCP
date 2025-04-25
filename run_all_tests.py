#!/usr/bin/env python3
"""
Script pour exécuter tous les tests dans le cadre du projet MCP
"""
import os
import sys
import logging
import subprocess
import time

# Configuration de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_test_file(test_file, verbose=True):
    """
    Exécute un fichier de test spécifique et retourne le résultat
    
    Args:
        test_file (str): Chemin du fichier de test à exécuter
        verbose (bool): Afficher les détails de l'exécution
        
    Returns:
        tuple: (success: bool, output: str)
    """
    cmd = ['python', test_file]
    
    if verbose:
        logger.info(f"Exécution des tests dans {test_file}")
    
    try:
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        elapsed_time = time.time() - start_time
        
        if result.returncode == 0:
            if verbose:
                logger.info(f"✅ {test_file} a réussi en {elapsed_time:.2f}s")
            return True, result.stdout
        else:
            if verbose:
                logger.error(f"❌ {test_file} a échoué en {elapsed_time:.2f}s")
                logger.error(f"Sortie d'erreur: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        if verbose:
            logger.error(f"❌ Erreur lors de l'exécution de {test_file}: {str(e)}")
        return False, str(e)

def run_all_test_files():
    """
    Exécute tous les fichiers de test disponibles et affiche un rapport
    
    Returns:
        int: Nombre de tests qui ont échoué
    """
    # Liste des fichiers de test à exécuter
    test_files = [
        "run_tests.py",
        "run_enhanced_tests.py",
        "test_rag_responses.py"
    ]
    
    # Statistiques globales
    total_tests = len(test_files)
    successful_tests = 0
    failed_tests = []
    start_time = time.time()
    
    # Exécuter chaque fichier de test
    for test_file in test_files:
        success, output = run_test_file(test_file)
        if success:
            successful_tests += 1
        else:
            failed_tests.append(test_file)
    
    # Afficher le rapport final
    elapsed_time = time.time() - start_time
    logger.info("\n" + "="*50)
    logger.info(f"RAPPORT D'EXÉCUTION DES TESTS:")
    logger.info(f"Tests exécutés: {total_tests}")
    logger.info(f"Tests réussis: {successful_tests}")
    logger.info(f"Tests échoués: {len(failed_tests)}")
    logger.info(f"Temps total d'exécution: {elapsed_time:.2f}s")
    
    # Afficher la liste des tests qui ont échoué
    if failed_tests:
        logger.info("\nTests échoués:")
        for test_file in failed_tests:
            logger.info(f"  - {test_file}")
    
    logger.info("="*50)
    
    return len(failed_tests)

if __name__ == "__main__":
    # Exécuter tous les tests
    sys.exit(run_all_test_files()) 