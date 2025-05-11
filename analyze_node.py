#!/usr/bin/env python3
import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire courant au path pour les imports
sys.path.append(os.path.abspath("."))

# Définir l'URL d'Ollama explicitement avant les imports
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

try:
    from rag.rag import RAGWorkflow
    from src.llm_selector import OllamaLLM, get_llm
    # Définir la variable d'environnement pour forcer Ollama
    os.environ["RAG_LLM_CHOICE"] = "ollama"
except ImportError as e:
    print(f"Erreur d'importation: {e}")
    print("Impossible d'importer les modules nécessaires.")
    sys.exit(1)

class NodeAnalyzer:
    """Classe pour analyser un nœud Lightning et générer des recommandations"""
    
    def __init__(self, node_id):
        # Créer le LLM directement avec URL explicite
        llm = OllamaLLM(model="llama3", temperature=0.7)
        llm.base_url = os.environ["OLLAMA_BASE_URL"]
        
        self.node_id = node_id
        self.rag_workflow = RAGWorkflow(llm=llm)
        self.base_output_dir = Path("rag/RAG_assets/reports")
        self.node_dir = self.base_output_dir / node_id[:8]
        self.full_node_dir = self.base_output_dir / node_id
        
        # Créer les répertoires si nécessaires
        self.node_dir.mkdir(exist_ok=True, parents=True)
        self.full_node_dir.mkdir(exist_ok=True, parents=True)
        
        print(f"Utilisation d'Ollama à l'URL: {llm.base_url}")
    
    async def generate_node_report(self):
        """Génère un rapport complet sur le nœud"""
        print(f"Génération du rapport pour le nœud {self.node_id}")
        
        # Créer un timestamp pour le fichier
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        report_file = self.full_node_dir / f"{timestamp}_{self.node_id}_node_analysis.md"
        
        try:
            # Utiliser la fonction query du workflow RAG
            query = f"""
            Génère un rapport d'analyse complet et détaillé du nœud Lightning Network ayant l'ID {self.node_id}.
            Ce rapport doit inclure:
            1. Une analyse des métriques de centralité du nœud
            2. Une évaluation détaillée de ses canaux actuels
            3. Une analyse de sa politique de frais actuelle
            4. Des recommandations d'optimisation
            5. Des projections et perspectives d'évolution
            
            Le format doit être un document Markdown structuré avec des titres, sous-titres, tableaux et listes.
            """
            
            result = await self.rag_workflow.query(query)
            report_content = result.get("answer", "Aucune analyse disponible")
            
            # Sauvegarder le rapport
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(f"# Rapport d'analyse du nœud Lightning\n\n")
                f.write(f"Généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"Clé publique: `{self.node_id}`\n\n\n")
                f.write(report_content)
            
            print(f"Rapport généré avec succès: {report_file}")
            return report_file
        
        except Exception as e:
            print(f"Erreur lors de la génération du rapport: {e}")
            return None
    
    async def generate_channel_recommendation(self, capacity=2000000):
        """Génère des recommandations pour ouvrir un nouveau canal"""
        print(f"Génération de recommandations pour un nouveau canal de {capacity} sats")
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        recommendation_file = self.full_node_dir / f"{timestamp}_{self.node_id}_channel_recommendation.md"
        
        try:
            query = f"""
            Pour le nœud Lightning Network ayant l'ID {self.node_id}, recommande le meilleur nœud cible 
            pour ouvrir un nouveau canal avec une capacité de {capacity} sats.
            
            Fournir:
            1. L'ID complet du nœud cible recommandé
            2. L'alias du nœud s'il est connu
            3. Une justification détaillée du choix (centralité, services, géolocalisation)
            4. Des paramètres recommandés pour le canal (frais, politique)
            5. Des stratégies pour optimiser l'utilisation de ce canal
            
            Présente la recommandation dans un format Markdown structuré.
            """
            
            result = await self.rag_workflow.query(query)
            rec_content = result.get("answer", "Aucune recommandation disponible")
            
            # Sauvegarder la recommandation
            with open(recommendation_file, "w", encoding="utf-8") as f:
                f.write(f"# Recommandation de nouveau canal pour le nœud {self.node_id[:8]}\n\n")
                f.write(f"Généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"Capacité cible: {capacity} sats\n\n")
                f.write(rec_content)
            
            print(f"Recommandation de canal générée: {recommendation_file}")
            return recommendation_file
        
        except Exception as e:
            print(f"Erreur lors de la génération des recommandations de canal: {e}")
            return None
    
    async def generate_fee_policy(self):
        """Génère des recommandations de politique de frais pour les canaux existants"""
        print(f"Génération de recommandations de politique de frais")
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        policy_file = self.full_node_dir / f"{timestamp}_{self.node_id}_fee_policy.md"
        
        try:
            query = f"""
            Pour le nœud Lightning Network ayant l'ID {self.node_id}, propose une politique de frais 
            optimisée pour chacun des canaux actuellement ouverts.
            
            La politique doit inclure:
            1. Une stratégie globale de frais (philosophie)
            2. Des recommandations spécifiques par type de canal (hubs, services, régionaux)
            3. Des valeurs précises pour:
               - Frais entrants (ppm)
               - Frais sortants (ppm)
               - Frais de base (msats)
            4. Un calendrier d'ajustement (fréquence, conditions)
            5. Des métriques de suivi pour évaluer l'efficacité
            
            Présente ces recommandations dans un format Markdown structuré.
            """
            
            result = await self.rag_workflow.query(query)
            policy_content = result.get("answer", "Aucune politique de frais disponible")
            
            # Sauvegarder la politique
            with open(policy_file, "w", encoding="utf-8") as f:
                f.write(f"# Politique de frais recommandée pour le nœud {self.node_id[:8]}\n\n")
                f.write(f"Généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(policy_content)
            
            print(f"Politique de frais générée: {policy_file}")
            return policy_file
        
        except Exception as e:
            print(f"Erreur lors de la génération de la politique de frais: {e}")
            return None
    
    async def run_full_analysis(self):
        """Exécute l'analyse complète du nœud"""
        try:
            print(f"=== Début de l'analyse complète du nœud {self.node_id} ===")
            
            # 1. Générer le rapport principal
            report_file = await self.generate_node_report()
            
            # 2. Générer les recommandations de canal
            channel_rec_file = await self.generate_channel_recommendation(capacity=2000000)
            
            # 3. Générer la politique de frais
            fee_policy_file = await self.generate_fee_policy()
            
            # 4. Créer un fichier de synthèse
            summary = {
                "node_id": self.node_id,
                "analysis_date": datetime.now().isoformat(),
                "report_file": str(report_file) if report_file else None,
                "channel_recommendation_file": str(channel_rec_file) if channel_rec_file else None,
                "fee_policy_file": str(fee_policy_file) if fee_policy_file else None
            }
            
            summary_file = self.full_node_dir / f"latest_analysis_summary.json"
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            
            print(f"=== Analyse complète terminée avec succès ===")
            print(f"Synthèse disponible dans: {summary_file}")
            
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'analyse complète: {e}")
            return False

async def main():
    # ID du nœud à analyser
    node_id = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
    
    # Créer l'analyseur et exécuter l'analyse
    analyzer = NodeAnalyzer(node_id)
    success = await analyzer.run_full_analysis()
    
    if success:
        print(f"Analyse complète du nœud {node_id} terminée avec succès")
    else:
        print(f"L'analyse du nœud {node_id} a échoué")

if __name__ == "__main__":
    asyncio.run(main()) 