#!/usr/bin/env python3
import os
import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from rag import RAGWorkflow
from cache_manager import CacheManager
from models import Document as PydanticDocument, QueryHistory as PydanticQueryHistory, SystemStats as PydanticSystemStats

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()

class LNbitsRAGIntegration:
    """
    Classe pour intégrer LNbits avec le système RAG.
    Permet d'utiliser les données de LNbits comme source pour le RAG
    et d'utiliser le RAG pour analyser les données de LNbits.
    """
    
    def __init__(self):
        # Initialisation des composants
        self.rag_workflow = RAGWorkflow()
        self.cache_manager = CacheManager()
        
        # Configuration LNbits
        self.lnbits_url = os.getenv("LNBITS_URL", "http://192.168.0.45:5000")
        self.lnbits_admin_key = os.getenv("LNBITS_ADMIN_KEY", "")
        self.lnbits_invoice_key = os.getenv("LNBITS_INVOICE_KEY", "")
        self.lnbits_user_id = os.getenv("LNBITS_USER_ID", "")
        
        # Configuration SSL pour LNbits
        self.ssl_context = None
        if self.lnbits_url.startswith("https"):
            import ssl
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        
        logger.info(f"Initialisation de LNbitsRAGIntegration avec URL: {self.lnbits_url}")
    
    async def initialize(self):
        """Initialise les connexions et vérifie l'accès à LNbits."""
        try:
            # Initialiser la connexion Mongo
            await self.mongo_ops.connect()
            
            # Vérification de l'accès à LNbits
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.lnbits_url}/api/v1/health",
                    ssl=self.ssl_context
                ) as response:
                    if response.status == 200:
                        logger.info("Connexion à LNbits établie avec succès")
                    else:
                        logger.warning(f"Impossible de se connecter à LNbits: {response.status}")
                        # Essayer avec HTTP
                        http_url = self.lnbits_url.replace("https://", "http://")
                        async with session.get(
                            f"{http_url}/api/v1/health",
                            ssl=self.ssl_context
                        ) as http_response:
                            if http_response.status == 200:
                                logger.info("Connexion à LNbits établie avec succès via HTTP")
                                self.lnbits_url = http_url
                            else:
                                logger.error(f"Impossible de se connecter à LNbits via HTTP: {http_response.status}")
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation: {str(e)}")
            return False
    
    async def get_lnbits_data(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """
        Récupère des données depuis l'API LNbits.
        
        Args:
            endpoint: L'endpoint LNbits à appeler
            params: Paramètres de la requête
            
        Returns:
            Dict: Les données récupérées
        """
        headers = {
            "X-Api-Key": self.lnbits_admin_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.lnbits_url}/api/v1/{endpoint}"
                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    ssl=self.ssl_context
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Erreur lors de la récupération des données LNbits: {response.status}")
                        return {"error": f"Erreur HTTP {response.status}"}
        except Exception as e:
            logger.error(f"Exception lors de la récupération des données LNbits: {str(e)}")
            return {"error": str(e)}
    
    async def create_lnbits_document(self, data: Dict[str, Any], source: str) -> bool:
        """
        Crée un document RAG à partir des données LNbits.
        
        Args:
            data: Les données LNbits
            source: La source des données
            
        Returns:
            bool: True si le document a été créé avec succès
        """
        try:
            # Conversion des données en texte
            content = json.dumps(data, indent=2)
            
            # Sauvegarde du document en utilisant MongoOperations
            document_dict = {
                "content": content,
                "source": source,
                "embedding": [], # Sera généré plus tard
                "metadata": {
                    "lnbits_data": True,
                    "timestamp": datetime.now().isoformat()
                }
            }
            return await self.mongo_ops.save_document(document_dict)
        except Exception as e:
            logger.error(f"Erreur lors de la création du document LNbits: {str(e)}")
            return False
    
    async def ingest_lnbits_data(self) -> bool:
        """
        Ingère les données LNbits dans le système RAG.
        
        Returns:
            bool: True si l'ingestion a réussi
        """
        try:
            # Récupération des données LNbits
            wallets = await self.get_lnbits_data("wallet")
            payments = await self.get_lnbits_data("payments")
            invoices = await self.get_lnbits_data("invoices")
            
            # Création des documents
            success = True
            success &= await self.create_lnbits_document(wallets, "lnbits_wallets")
            success &= await self.create_lnbits_document(payments, "lnbits_payments")
            success &= await self.create_lnbits_document(invoices, "lnbits_invoices")
            
            # Mise à jour des embeddings
            if success:
                await self.rag_workflow.update_embeddings()
            
            return success
        except Exception as e:
            logger.error(f"Erreur lors de l'ingestion des données LNbits: {str(e)}")
            return False
    
    async def query_lnbits_data(self, query: str) -> Dict[str, Any]:
        """
        Interroge le système RAG avec une requête concernant les données LNbits.
        
        Args:
            query: La requête à poser
            
        Returns:
            Dict: La réponse du système RAG
        """
        try:
            # Ajout d'un contexte pour les données LNbits
            enhanced_query = f"Concernant les données LNbits: {query}"
            
            # Interrogation du système RAG
            response = await self.rag_workflow.query(enhanced_query)
            
            # Sauvegarde de l'historique (utilise déjà une fonction séparée ou à adapter)
            history_entry = {
                "query": query,
                "response": response.get("response", ""),
                "context_docs": [doc.get('source', '') for doc in response.get('context_docs', [])],
                "processing_time": response.get("processing_time", 0.0),
                "cache_hit": response.get('cache_hit', False),
                "metadata": {"lnbits_query": True}
            }
            # Utiliser mongo_ops (si save_query_history est dans MongoOperations)
            await self.mongo_ops.save_query_history(history_entry)

            return response
        except Exception as e:
            logger.error(f"Erreur lors de l'interrogation des données LNbits: {str(e)}")
            return {
                "query": query,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def analyze_lnbits_data(self) -> Dict[str, Any]:
        """
        Analyse les données LNbits et génère un rapport.
        
        Returns:
            Dict: Le rapport d'analyse
        """
        try:
            # Récupération des données LNbits
            wallets = await self.get_lnbits_data("wallet")
            payments = await self.get_lnbits_data("payments")
            invoices = await self.get_lnbits_data("invoices")
            
            # Analyse des données
            total_wallets = len(wallets) if isinstance(wallets, list) else 1
            total_payments = len(payments) if isinstance(payments, list) else 0
            total_invoices = len(invoices) if isinstance(invoices, list) else 0
            
            # Calcul des statistiques
            total_amount = 0
            if isinstance(payments, list):
                for payment in payments:
                    if isinstance(payment, dict) and "amount" in payment:
                        total_amount += payment.get("amount", 0)
            
            # Génération du rapport
            report = {
                "total_wallets": total_wallets,
                "total_payments": total_payments,
                "total_invoices": total_invoices,
                "total_amount": total_amount,
                "timestamp": datetime.now().isoformat()
            }
            
            # Création d'un document RAG avec le rapport
            await self.create_lnbits_document(report, "lnbits_analysis")
            
            # Sauvegarde de l'historique
            history_entry = {
                "query": "Analyse des données LNbits",
                "response": json.dumps(report),
                "context_docs": [],
                "processing_time": 0.0,
                "cache_hit": False,
                "metadata": {"lnbits_analysis": True}
            }
            # Utiliser mongo_ops
            await self.mongo_ops.save_query_history(history_entry)

            return report
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des données LNbits: {str(e)}")
            return {"error": str(e)}
    
    async def close(self):
        """Ferme les connexions."""
        # Fermer la connexion Mongo
        await self.mongo_ops.disconnect()
        logger.info("Connexions LNbitsRAGIntegration fermées.")

async def main():
    """Fonction principale pour tester l'intégration."""
    try:
        logger.info("Démarrage de l'intégration LNbits-RAG")
        
        # Initialisation de l'intégration
        integration = LNbitsRAGIntegration()
        success = await integration.initialize()
        
        if not success:
            logger.error("Impossible d'initialiser l'intégration LNbits-RAG")
            return
        
        # Ingestion des données LNbits
        logger.info("Ingestion des données LNbits")
        success = await integration.ingest_lnbits_data()
        
        if not success:
            logger.error("Impossible d'ingérer les données LNbits")
            return
        
        # Analyse des données LNbits
        logger.info("Analyse des données LNbits")
        analysis = await integration.analyze_lnbits_data()
        logger.info(f"Analyse terminée: {json.dumps(analysis, indent=2)}")
        
        # Interrogation du système RAG
        logger.info("Interrogation du système RAG")
        queries = [
            "Combien de portefeuilles sont gérés par LNbits?",
            "Quel est le montant total des paiements?",
            "Quelles sont les fonctionnalités principales de LNbits?"
        ]
        
        for query in queries:
            logger.info(f"Requête: {query}")
            response = await integration.query_lnbits_data(query)
            logger.info(f"Réponse: {json.dumps(response, indent=2)}")
        
        # Fermeture des connexions
        await integration.close()
        
        logger.info("Intégration LNbits-RAG terminée avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de l'intégration LNbits-RAG: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 