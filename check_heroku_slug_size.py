#!/usr/bin/env python3
import os
import subprocess
import json
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constantes
HEROKU_SLUG_LIMIT_MB = 500
THRESHOLD_WARNING_PERCENT = 80  # Afficher un avertissement à 80% de la limite

def get_directory_size(path='.', exclude_dirs=None):
    """Récupère la taille d'un répertoire en Mo, en excluant certains dossiers"""
    if exclude_dirs is None:
        exclude_dirs = ['.git', 'venv', '__pycache__']
    
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        # Exclure les répertoires spécifiés
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp) and not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    
    # Convertir en Mo
    return total_size / (1024 * 1024)

def check_files_in_slugignore():
    """Vérifie quels dossiers sont exclus dans .slugignore"""
    excluded_dirs = []
    
    if os.path.exists('.slugignore'):
        with open('.slugignore', 'r') as f:
            for line in f:
                line = line.strip()
                # Ignorer les lignes vides et commentaires
                if line and not line.startswith('#'):
                    if line.endswith('/'):
                        excluded_dirs.append(line[:-1])
                    else:
                        excluded_dirs.append(line)
    
    return excluded_dirs

def get_directory_details(path='.', exclude_dirs=None, min_size_mb=1):
    """Récupère les détails des dossiers et fichiers les plus volumineux"""
    if exclude_dirs is None:
        exclude_dirs = ['.git', 'venv', '__pycache__']
    
    sizes = []
    
    # Taille des répertoires principaux
    for dirname in os.listdir(path):
        if dirname in exclude_dirs:
            continue
        
        dirpath = os.path.join(path, dirname)
        if os.path.isdir(dirpath):
            size_mb = get_directory_size(dirpath, exclude_dirs)
            if size_mb >= min_size_mb:
                sizes.append({
                    'path': dirname,
                    'size_mb': size_mb,
                    'type': 'directory'
                })
    
    # Taille des fichiers à la racine
    for filename in os.listdir(path):
        filepath = os.path.join(path, filename)
        if os.path.isfile(filepath):
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if size_mb >= min_size_mb:
                sizes.append({
                    'path': filename,
                    'size_mb': size_mb,
                    'type': 'file'
                })
    
    # Trier par taille, du plus grand au plus petit
    return sorted(sizes, key=lambda x: x['size_mb'], reverse=True)

def get_heroku_app_name():
    """Tente de récupérer le nom de l'application Heroku depuis Git"""
    try:
        git_remote = subprocess.check_output(
            ['git', 'remote', '-v'], 
            stderr=subprocess.STDOUT, 
            universal_newlines=True
        )
        
        for line in git_remote.split('\n'):
            if 'heroku' in line and 'fetch' in line:
                # Format typique: heroku  https://git.heroku.com/app-name.git (fetch)
                parts = line.split('/')
                if len(parts) >= 4:
                    app_name = parts[3].split('.')[0]
                    return app_name
    except (subprocess.CalledProcessError, IndexError):
        pass
    
    return None

def print_slug_size_warning(total_size_mb):
    """Affiche un avertissement sur la taille du slug"""
    percent_used = (total_size_mb / HEROKU_SLUG_LIMIT_MB) * 100
    
    print("\n=== TAILLE ESTIMÉE DU SLUG ===")
    print(f"Taille estimée:  {total_size_mb:.2f} MB")
    print(f"Limite Heroku:   {HEROKU_SLUG_LIMIT_MB} MB")
    print(f"Utilisation:     {percent_used:.1f}%")
    
    status = "✅ OK"
    if percent_used >= 100:
        status = "❌ CRITIQUE - Dépassement de la limite!"
    elif percent_used >= THRESHOLD_WARNING_PERCENT:
        status = "⚠️  ATTENTION - Approche de la limite!"
    
    print(f"\nStatut: {status}")
    
    if percent_used >= THRESHOLD_WARNING_PERCENT:
        print("\nRecommandations:")
        print("- Migrer les données volumineuses vers une base de données")
        print("- Exclure les répertoires non nécessaires dans .slugignore")
        print("- Nettoyer les fichiers temporaires et de build")
        print("- Compresser les ressources statiques (images, etc.)")
    
    return percent_used

def main():
    print("\n=== VÉRIFICATION DE LA TAILLE DU SLUG HEROKU ===\n")
    
    # Récupérer le nom de l'application Heroku
    app_name = get_heroku_app_name()
    if app_name:
        print(f"Application Heroku détectée: {app_name}")
    else:
        print("Aucune application Heroku détectée dans les remotes Git")
    
    # Vérifier les exclusions dans .slugignore
    excluded_dirs = check_files_in_slugignore()
    if excluded_dirs:
        print(f"\nRépertoires exclus dans .slugignore: {', '.join(excluded_dirs)}")
    else:
        print("\nAucun répertoire explicitement exclu dans .slugignore")
        print("⚠️  Recommandation: Créer ou mettre à jour .slugignore pour exclure les fichiers non nécessaires")
    
    # Calculer la taille actuelle du projet
    exclude_dirs = ['.git', 'venv', '__pycache__'] + excluded_dirs
    total_size_mb = get_directory_size('.', exclude_dirs)
    
    # Afficher les détails des répertoires et fichiers
    print("\n=== DÉTAILS DES ÉLÉMENTS LES PLUS VOLUMINEUX ===")
    details = get_directory_details('.', exclude_dirs)
    
    if details:
        print(f"{'TYPE':<10} {'CHEMIN':<30} {'TAILLE (MB)':<10}")
        print("-" * 55)
        
        for item in details[:10]:  # Afficher les 10 plus gros éléments
            print(f"{item['type']:<10} {item['path']:<30} {item['size_mb']:.2f}")
    else:
        print("Aucun élément volumineux trouvé")
    
    # Afficher l'avertissement sur la taille du slug
    percent_used = print_slug_size_warning(total_size_mb)
    
    # Conseils spécifiques basés sur les résultats
    if percent_used >= THRESHOLD_WARNING_PERCENT:
        print("\n=== ACTIONS RECOMMANDÉES ===\n")
        
        # Vérifier si collected_data est exclu
        if 'collected_data' not in excluded_dirs and os.path.exists('collected_data'):
            print("⚠️  Le répertoire 'collected_data' n'est pas exclu!")
            print("   Exécutez: python simple_migration.py pour migrer les données vers MongoDB")
        
        # Vérifier la présence de fichiers de build
        build_dirs = ['build', 'dist', 'node_modules']
        for d in build_dirs:
            if d not in excluded_dirs and os.path.exists(d):
                print(f"⚠️  Le répertoire '{d}' n'est pas exclu!")
                print(f"   Ajoutez '{d}/' à votre .slugignore")
    
    print("\nPour migrer les données JSON vers MongoDB, exécutez:")
    print("python simple_migration.py")
    
    print("\nPour plus d'informations, consultez HEROKU_OPTIMISATION.md")

if __name__ == "__main__":
    main() 