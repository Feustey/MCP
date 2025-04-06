import os
import aiohttp
import asyncio
import logging
import ssl
from datetime import datetime
from typing import List, Dict, Any
from models import (
    Document, NodeData, ChannelData, NetworkMetrics,
    NodePerformance, SecurityMetrics, ChannelRecommendation
)
from src.mongo_operations import MongoOperations
from cache_manager import CacheManager
from dotenv import load_dotenv
from src.rag import RAGWorkflow
import json
from tiktoken import encoding_for_model
import traceback

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class DataAggregator:
    def __init__(self):
        self.mongo_ops = None
        self.cache_manager = CacheManager()
        self.sparkseer_api_key = os.getenv("SPARKSEER_API_KEY")
        self.lnbits_url = os.getenv("LNBITS_URL")
        self.lnbits_admin_key = os.getenv("LNBITS_ADMIN_KEY")
        self.lnbits_invoice_key = os.getenv("LNBITS_INVOICE_KEY")
        self.sparkseer_base_url = "https://api.sparkseer.space"  # URL corrigée sans /api/v1
        
        # Configuration SSL pour LNBits
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def initialize(self):
        """Initialise les connexions aux bases de données"""
        if self.mongo_ops is None:
            self.mongo_ops = MongoOperations()
            await self.mongo_ops.initialize()
        return self

    async def make_request(self, url: str, headers: Dict[str, str], params: Dict[str, Any] = None, verify_ssl: bool = True) -> Any:
        """Fait une requête HTTP avec gestion d'erreur"""
        try:
            connector = None if verify_ssl else aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Erreur HTTP {response.status} pour {url}")
                        return None
        except aiohttp.ClientError as e:
            logger.error(f"Erreur de connexion pour {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue pour {url}: {str(e)}")
            return None

    async def fetch_sparkseer_network_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques globales du réseau"""
        headers = {"api-key": self.sparkseer_api_key}
        return await self.make_request(
            f"{self.sparkseer_base_url}/v1/stats/ln-summary-ts",
            headers=headers
        ) or {}

    async def fetch_sparkseer_top_nodes(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Récupère les nœuds les plus importants"""
        headers = {"api-key": self.sparkseer_api_key}
        params = {"limit": limit}
        response = await self.make_request(
            f"{self.sparkseer_base_url}/v1/stats/centralities",
            headers=headers,
            params=params
        )
        
        logger.info(f"Réponse brute de l'API pour les nœuds top: {json.dumps(response, indent=2)}")
        
        if response is None:
            logger.error("Pas de réponse de l'API pour les nœuds top")
            return []
            
        if isinstance(response, str):
            logger.warning("La réponse est une chaîne de caractères, tentative de conversion en JSON")
            try:
                response = json.loads(response)
            except json.JSONDecodeError as e:
                logger.error(f"Impossible de parser la réponse en JSON: {e}")
                return []
                
        if isinstance(response, dict):
            # Si la réponse est un dictionnaire, cherchons la liste des nœuds
            logger.info(f"Clés disponibles dans la réponse: {list(response.keys())}")
            for key in response:
                if isinstance(response[key], list):
                    logger.info(f"Liste trouvée dans la clé '{key}' avec {len(response[key])} éléments")
                    # Vérifier la structure des nœuds
                    for i, node in enumerate(response[key]):
                        logger.info(f"Structure du nœud {i}: {json.dumps(node, indent=2)}")
                    return response[key]
            logger.error("Aucune liste trouvée dans la réponse")
            return []
            
        if isinstance(response, list):
            logger.info(f"Réponse est une liste avec {len(response)} éléments")
            # Vérifier la structure des nœuds
            for i, node in enumerate(response):
                logger.info(f"Structure du nœud {i}: {json.dumps(node, indent=2)}")
            return response
            
        logger.error(f"Format de réponse inattendu: {type(response)}")
        return []

    async def fetch_sparkseer_node_details(self, node_id: str) -> Dict[str, Any]:
        """Récupère les détails d'un nœud spécifique"""
        if not node_id:
            logger.warning("ID de nœud vide fourni, retour d'un dictionnaire vide")
            return {
                "error": "ID de nœud manquant",
                "timestamp": datetime.now().isoformat()
            }
            
        headers = {"api-key": self.sparkseer_api_key}
        response = await self.make_request(
            f"{self.sparkseer_base_url}/v1/stats/node/{node_id}",
            headers=headers
        )
        
        logger.info(f"Réponse brute de l'API pour les détails du nœud {node_id}: {json.dumps(response, indent=2)}")
        
        if response is None:
            logger.error(f"Pas de réponse de l'API pour le nœud {node_id}")
            return {
                "error": "Pas de réponse de l'API",
                "node_id": node_id,
                "timestamp": datetime.now().isoformat()
            }
            
        if isinstance(response, str):
            logger.warning("La réponse est une chaîne de caractères, tentative de conversion en JSON")
            try:
                response = json.loads(response)
            except json.JSONDecodeError as e:
                logger.error(f"Impossible de parser la réponse en JSON: {e}")
                return {
                    "error": "Réponse invalide de l'API",
                    "node_id": node_id,
                    "timestamp": datetime.now().isoformat()
                }
                
        if isinstance(response, dict):
            # Ajouter des métadonnées
            response["_metadata"] = {
                "node_id": node_id,
                "timestamp": datetime.now().isoformat(),
                "source": "sparkseer"
            }
            return response
            
        logger.error(f"Format de réponse inattendu pour les détails du nœud: {type(response)}")
        return {
            "error": "Format de réponse inattendu",
            "node_id": node_id,
            "timestamp": datetime.now().isoformat()
        }

    async def fetch_sparkseer_channel_metrics(self) -> List[Dict[str, Any]]:
        """Récupère les métriques des canaux"""
        headers = {"api-key": self.sparkseer_api_key}
        return await self.make_request(
            f"{self.sparkseer_base_url}/v1/stats/ln-summary-ts",  # Même endpoint que network_metrics pour l'instant
            headers=headers
        ) or []

    async def fetch_sparkseer_fee_analysis(self) -> Dict[str, Any]:
        """Récupère l'analyse des frais"""
        headers = {"api-key": self.sparkseer_api_key}
        return await self.make_request(
            f"{self.sparkseer_base_url}/v1/stats/centralities",  # Même endpoint que top_nodes pour l'instant
            headers=headers
        ) or {}

    async def fetch_sparkseer_network_health(self) -> Dict[str, Any]:
        """Récupère la santé du réseau"""
        headers = {"api-key": self.sparkseer_api_key}
        return await self.make_request(
            f"{self.sparkseer_base_url}/v1/stats/ln-summary-ts",  # Même endpoint que network_metrics pour l'instant
            headers=headers
        ) or {}

    async def fetch_lnbits_wallets(self) -> List[Dict[str, Any]]:
        """Récupère la liste des wallets LNBits"""
        headers = {"X-Api-Key": self.lnbits_admin_key}
        return await self.make_request(
            f"{self.lnbits_url}/api/v1/wallet",
            headers=headers,
            verify_ssl=False
        ) or []

    async def fetch_lnbits_payments(self, wallet_id: str) -> List[Dict[str, Any]]:
        """Récupère l'historique des paiements d'un wallet"""
        headers = {"X-Api-Key": self.lnbits_admin_key}
        params = {"wallet_id": wallet_id}
        return await self.make_request(
            f"{self.lnbits_url}/api/v1/payments",
            headers=headers,
            params=params,
            verify_ssl=False
        ) or []

    async def fetch_lnbits_invoices(self, wallet_id: str) -> List[Dict[str, Any]]:
        """Récupère les factures d'un wallet"""
        headers = {"X-Api-Key": self.lnbits_invoice_key}
        params = {"wallet_id": wallet_id}
        return await self.make_request(
            f"{self.lnbits_url}/api/v1/invoices",
            headers=headers,
            params=params,
            verify_ssl=False
        ) or []

    async def process_node_data(self, raw_data: Dict[str, Any]) -> NodeData:
        """Traite les données brutes d'un nœud"""
        return NodeData(
            node_id=raw_data.get("node_id", ""),
            alias=raw_data.get("alias", ""),
            capacity=float(raw_data.get("capacity", 0)),
            channel_count=int(raw_data.get("channel_count", 0)),
            last_update=datetime.now(),
            reputation_score=float(raw_data.get("reputation_score", 0)),
            metadata=raw_data.get("metadata", {})
        )

    async def process_channel_data(self, raw_data: Dict[str, Any]) -> ChannelData:
        """Traite les données brutes d'un canal"""
        return ChannelData(
            channel_id=raw_data.get("channel_id", ""),
            capacity=float(raw_data.get("capacity", 0)),
            fee_rate=raw_data.get("fee_rate", {"base": 0, "rate": 0}),
            balance=raw_data.get("balance", {"local": 0, "remote": 0}),
            age=int(raw_data.get("age", 0)),
            last_update=datetime.now(),
            metadata=raw_data.get("metadata", {})
        )

    async def create_document(self, data: Any, source: str) -> Document:
        """Crée un document RAG à partir des données"""
        try:
            logger.info(f"Création d'un document pour la source: {source}")
            
            # Convertir les données en chaîne de caractères de manière sûre
            if isinstance(data, (dict, list)):
                content = json.dumps(data, indent=2)
            else:
                content = str(data)
                
            logger.debug(f"Contenu du document: {content[:200]}...")  # Log des 200 premiers caractères
            
            # Déterminer le type de données
            data_type = data.__class__.__name__ if hasattr(data, "__class__") else type(data).__name__
            logger.info(f"Type de données détecté: {data_type}")
            
            # TODO: Implémenter la génération d'embeddings
            # Pour l'instant, on utilise une liste vide
            embeddings = []
            
            # Créer le document
            doc = Document(
                content=content,
                source=source,
                embedding=embeddings,
                metadata={
                    "type": data_type,
                    "created_at": datetime.now().isoformat(),
                    "content_length": len(content)
                }
            )
            
            logger.info(f"Document créé avec succès pour {source}")
            return doc
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du document: {str(e)}")
            logger.error(f"Détails de l'erreur: {traceback.format_exc()}")
            # En cas d'erreur, on crée un document minimal
            return Document(
                content="Erreur lors de la création du document",
                source=source,
                embedding=[],
                metadata={"error": str(e)}
            )

    async def _chunk_data(self, data: Dict[str, Any], max_tokens: int = 4000) -> List[Dict[str, Any]]:
        """Découpe les données en morceaux plus petits pour respecter la limite de tokens."""
        try:
            # Convertir les données en chaîne JSON
            data_str = json.dumps(data, indent=2)
            
            # Initialiser le tokenizer
            tokenizer = encoding_for_model("gpt-3.5-turbo")
            
            # Découper en morceaux
            tokens = tokenizer.encode(data_str)
            chunks = []
            current_chunk = []
            current_token_count = 0
            
            for token in tokens:
                if current_token_count + 1 > max_tokens:
                    # Convertir les tokens en texte et parser en JSON
                    chunk_text = tokenizer.decode(current_chunk)
                    try:
                        chunk_data = json.loads(chunk_text)
                        chunks.append(chunk_data)
                    except json.JSONDecodeError:
                        # Si le chunk n'est pas un JSON valide, l'ajouter comme texte
                        chunks.append({"text": chunk_text})
                    
                    # Réinitialiser pour le prochain chunk
                    current_chunk = [token]
                    current_token_count = 1
                else:
                    current_chunk.append(token)
                    current_token_count += 1
            
            # Ajouter le dernier chunk s'il existe
            if current_chunk:
                chunk_text = tokenizer.decode(current_chunk)
                try:
                    chunk_data = json.loads(chunk_text)
                    chunks.append(chunk_data)
                except json.JSONDecodeError:
                    chunks.append({"text": chunk_text})
            
            return chunks
            
        except Exception as e:
            logger.error(f"Erreur lors du découpage des données : {str(e)}")
            # En cas d'erreur, retourner les données originales dans une liste
            return [data]

    async def submit_to_rag(self, data: Dict[str, Any], source: str) -> str:
        """Soumet les données au système RAG et retourne les recommandations."""
        try:
            logger.info(f"Début de la soumission au RAG pour la source: {source}")
            logger.debug(f"Données à traiter: {json.dumps(data, indent=2)}")
            
            # Création du document RAG
            logger.info("Création du document RAG...")
            doc = await self.create_document(data, source)
            
            # Sauvegarde dans MongoDB
            logger.info("Sauvegarde du document dans MongoDB...")
            await self.mongo_ops.save_document(doc)
            
            # Découper les données en morceaux plus petits
            logger.info("Découpage des données en chunks...")
            chunks = await self._chunk_data(data)
            logger.info(f"Nombre de chunks créés: {len(chunks)}")
            
            # Initialiser le workflow RAG
            logger.info("Initialisation du workflow RAG...")
            rag_workflow = RAGWorkflow()
            all_recommendations = []
            
            # Traiter chaque chunk
            for i, chunk in enumerate(chunks, 1):
                logger.info(f"Traitement du chunk {i}/{len(chunks)}...")
                try:
                    # Générer des recommandations pour ce chunk
                    chunk_recommendations = await rag_workflow.query(
                        f"Analysez les données suivantes et fournissez des recommandations détaillées : {json.dumps(chunk, indent=2)}"
                    )
                    if chunk_recommendations:
                        all_recommendations.append(chunk_recommendations)
                    else:
                        logger.warning(f"Pas de recommandations générées pour le chunk {i}")
                except Exception as chunk_error:
                    logger.error(f"Erreur lors du traitement du chunk {i}: {str(chunk_error)}")
                    continue
            
            if not all_recommendations:
                logger.warning("Aucune recommandation n'a été générée")
                return "Aucune recommandation n'a pu être générée pour ces données."
            
            # Combiner toutes les recommandations
            logger.info("Combinaison des recommandations...")
            combined_recommendations = "\n\n".join(all_recommendations)
            
            # Sauvegarder les recommandations combinées
            logger.info("Sauvegarde des recommandations...")
            recommendation_doc = await self.create_document(
                {"recommendations": combined_recommendations, "source_data": data},
                f"{source}_recommendations"
            )
            await self.mongo_ops.save_document(recommendation_doc)
            
            logger.info("Soumission au RAG terminée avec succès")
            return combined_recommendations
            
        except Exception as e:
            logger.error(f"Erreur lors de la soumission au RAG: {str(e)}")
            logger.error(f"Détails de l'erreur: {traceback.format_exc()}")
            return f"Erreur lors de la génération des recommandations: {str(e)}"

    async def aggregate_data(self):
        """Fonction principale pour agréger les données"""
        try:
            # S'assurer que les connexions sont initialisées
            await self.initialize()
            
            # Récupération des données Sparkseer
            logger.info("Récupération des métriques réseau Sparkseer...")
            network_metrics = await self.fetch_sparkseer_network_metrics()
            if network_metrics:
                # Soumission au RAG et stockage des recommandations
                recommendations = await self.submit_to_rag(network_metrics, "sparkseer_network_metrics")
                logger.info("Métriques réseau et recommandations sauvegardées")
            else:
                logger.warning("Aucune métrique réseau n'a été récupérée")

            logger.info("Récupération des nœuds top Sparkseer...")
            top_nodes = await self.fetch_sparkseer_top_nodes(limit=100)
            logger.info(f"Nombre de nœuds top récupérés : {len(top_nodes)}")
            
            for i, node_data in enumerate(top_nodes, 1):
                try:
                    # Vérifier si le nœud a un ID
                    node_id = node_data.get("node_id", "")
                    if not node_id:
                        logger.warning(f"Nœud {i} sans ID trouvé, données : {json.dumps(node_data, indent=2)}")
                        continue
                        
                    logger.info(f"Traitement du nœud {i}/{len(top_nodes)} (ID: {node_id})")
                    
                    # Récupération des détails du nœud
                    node_details = await self.fetch_sparkseer_node_details(node_id)
                    if "error" in node_details:
                        logger.warning(f"Erreur lors de la récupération des détails du nœud {node_id}: {node_details['error']}")
                        continue
                        
                    # Mise à jour des données du nœud
                    node_data.update(node_details)
                    
                    # Soumission au RAG et stockage des recommandations
                    recommendations = await self.submit_to_rag(node_data, f"sparkseer_node_{node_id}")
                    logger.info(f"Données et recommandations sauvegardées pour le nœud {node_id}")
                    
                except Exception as e:
                    logger.error(f"Erreur lors du traitement du nœud {i}: {str(e)}")
                    continue

            logger.info("Récupération des métriques de canaux Sparkseer...")
            channel_metrics = await self.fetch_sparkseer_channel_metrics()
            logger.info(f"Nombre de métriques de canaux récupérées : {len(channel_metrics)}")
            
            for i, channel_data in enumerate(channel_metrics, 1):
                try:
                    channel_id = channel_data.get("channel_id", "")
                    if not channel_id:
                        logger.warning(f"Canal {i} sans ID trouvé, données : {json.dumps(channel_data, indent=2)}")
                        continue
                        
                    logger.info(f"Traitement du canal {i}/{len(channel_metrics)} (ID: {channel_id})")
                    recommendations = await self.submit_to_rag(channel_data, f"sparkseer_channel_{channel_id}")
                    logger.info(f"Données et recommandations sauvegardées pour le canal {channel_id}")
                    
                except Exception as e:
                    logger.error(f"Erreur lors du traitement du canal {i}: {str(e)}")
                    continue

            logger.info("Récupération de l'analyse des frais Sparkseer...")
            fee_analysis = await self.fetch_sparkseer_fee_analysis()
            if fee_analysis:
                doc = await self.create_document(fee_analysis, "sparkseer_fee_analysis")
                await self.mongo_ops.save_document(doc)
                logger.info("Analyse des frais sauvegardée")
            else:
                logger.warning("Aucune analyse des frais n'a été récupérée")

            logger.info("Récupération de la santé du réseau Sparkseer...")
            network_health = await self.fetch_sparkseer_network_health()
            if network_health:
                doc = await self.create_document(network_health, "sparkseer_network_health")
                await self.mongo_ops.save_document(doc)
                logger.info("Santé du réseau sauvegardée")
            else:
                logger.warning("Aucune donnée de santé du réseau n'a été récupérée")

            # Récupération des données LNBits
            logger.info("Récupération des wallets LNBits...")
            lnbits_wallets = await self.fetch_lnbits_wallets()
            logger.info(f"Nombre de wallets récupérés : {len(lnbits_wallets)}")
            
            for i, wallet in enumerate(lnbits_wallets, 1):
                try:
                    wallet_id = wallet.get("id")
                    if not wallet_id:
                        logger.warning(f"Wallet {i} sans ID trouvé, données : {json.dumps(wallet, indent=2)}")
                        continue
                        
                    logger.info(f"Traitement du wallet {i}/{len(lnbits_wallets)} (ID: {wallet_id})")
                    
                    # Récupération des paiements
                    payments = await self.fetch_lnbits_payments(wallet_id)
                    wallet["payments"] = payments
                    logger.info(f"Nombre de paiements récupérés pour le wallet {wallet_id}: {len(payments)}")

                    # Récupération des factures
                    invoices = await self.fetch_lnbits_invoices(wallet_id)
                    wallet["invoices"] = invoices
                    logger.info(f"Nombre de factures récupérées pour le wallet {wallet_id}: {len(invoices)}")

                    # Création du document
                    doc = await self.create_document(wallet, "lnbits")
                    await self.mongo_ops.save_document(doc)
                    logger.info(f"Wallet {wallet_id} sauvegardé avec succès")
                    
                except Exception as e:
                    logger.error(f"Erreur lors du traitement du wallet {i}: {str(e)}")
                    continue

            # Mise à jour des statistiques
            stats = {
                "total_documents": len(top_nodes) + len(channel_metrics) + len(lnbits_wallets) + 3,  # +3 pour les métriques globales
                "total_queries": 0,
                "average_processing_time": 0.0,
                "cache_hit_rate": 0.0,
                "last_update": datetime.now().isoformat()
            }
            await self.mongo_ops.update_system_stats(stats)
            logger.info("Statistiques mises à jour")

        except Exception as e:
            logger.error(f"Erreur lors de l'agrégation des données: {str(e)}")
            logger.error(f"Détails de l'erreur: {traceback.format_exc()}")
            raise

async def main():
    aggregator = DataAggregator()
    await aggregator.aggregate_data()

if __name__ == "__main__":
    asyncio.run(main()) 