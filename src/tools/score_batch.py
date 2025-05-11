#!/usr/bin/env python3
import asyncio
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import json
import sys
import httpx
import re
from bs4 import BeautifulSoup

# MongoDB pour récupérer les pubkeys
from motor.motor_asyncio import AsyncIOMotorClient
# Redis pour loguer les résultats
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.redis_operations import RedisOperations
from src.integrations.amboss_integration import AmbossAPIIntegration
from src.amboss_scraper import AmbossScraper

# Clients API (placeholders à adapter)
# from src.clients.amboss_api import get_amboss_reputation
# from src.clients.sparkseer_api import get_sparkseer_metrics
# from src.clients.lnrouter_api import simulate_route

# Pour l'instant, on utilise des mocks simples
SPARKSEER_API_KEY = os.getenv("SPARKSEER_API_KEY", "")
SPARKSEER_BASE_URL = os.getenv("SPARKSEER_BASE_URL", "https://api.sparkseer.space")

TOTAL_NODES_ESTIMATE = 20000

async def get_amboss_reputation(pubkey, amboss_scraper):
    try:
        node_data = await amboss_scraper.scrape_node_data(pubkey)
        rep = None
        if node_data and hasattr(node_data, 'reputation_score'):
            rep = node_data.reputation_score
        logger.info(f"[Amboss][{pubkey}] Réputation scrapée: {rep}")
        return rep
    except Exception as e:
        logger.error(f"Erreur Amboss (scraping) pour {pubkey}: {e}")
        return None

async def get_sparkseer_metrics(pubkey):
    if not SPARKSEER_API_KEY:
        logger.warning("Clé API Sparkseer non configurée")
        return None
    url = f"{SPARKSEER_BASE_URL}/v1/node/current-stats/{pubkey}"
    headers = {"api-key": SPARKSEER_API_KEY}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"[Sparkseer][{pubkey}] Réponse brute: {data}")
            # Correction : Sparkseer retourne une liste, on prend le premier élément
            if isinstance(data, list):
                data = data[0] if data else {}
            return {
                "centrality": data.get("betweenness_rank", 0),
                "history": data.get("htlc_response_time_mean", 0),
                "fees": data.get("mean_outbound_fee_rate", 0)
            }
        except Exception as e:
            logger.error(f"Erreur Sparkseer pour {pubkey}: {e}")
            return None

async def simulate_lnrouter(pubkey):
    # TODO: remplacer par appel réel
    return 1.0  # ou None si indisponible

async def get_amboss_ranks(pubkey, amboss_scraper):
    try:
        url = f"https://amboss.space/node/{pubkey}"
        html = await amboss_scraper._get_page(url)
        if not html:
            logger.warning(f"Amboss HTML vide pour {pubkey}")
            return None, None, None, None
        # Log du HTML une fois par jour (à améliorer si besoin)
        # with open(f"amboss_html_{pubkey}.html", "w") as f:
        #     f.write(html)
        channel_rank, capacity_rank = extract_ranks(html)
        norm_channel = 1 - (channel_rank / TOTAL_NODES_ESTIMATE) if channel_rank else None
        norm_capacity = 1 - (capacity_rank / TOTAL_NODES_ESTIMATE) if capacity_rank else None
        logger.info(f"[Amboss][{pubkey}] Channels Rank: {channel_rank}, Capacity Rank: {capacity_rank}, Normalisés: {norm_channel}, {norm_capacity}")
        return channel_rank, capacity_rank, norm_channel, norm_capacity
    except Exception as e:
        logger.error(f"Erreur Amboss (ranks) pour {pubkey}: {e}")
        return None, None, None, None

def extract_ranks(html):
    soup = BeautifulSoup(html, 'html.parser')
    channel_rank = None
    capacity_rank = None

    # Recherche du bloc Channels Rank
    channel_h2 = soup.find('h2', string=re.compile(r'Channels Rank'))
    if channel_h2:
        channel_div = channel_h2.find_next('div', class_=re.compile(r'kFAOBa'))
        if channel_div and channel_div.text.strip().isdigit():
            channel_rank = int(channel_div.text.strip())

    # Recherche du bloc Capacity Rank
    capacity_h2 = soup.find('h2', string=re.compile(r'Capacity Rank'))
    if capacity_h2:
        capacity_div = capacity_h2.find_next('div', class_=re.compile(r'kFAOBa'))
        if capacity_div and capacity_div.text.strip().isdigit():
            capacity_rank = int(capacity_div.text.strip())

    return channel_rank, capacity_rank

# Calcul du score global (pondération brute)
def compute_score(norm_chan, norm_cap, cent, hist, fees, route):
    # Pondération brute : 0.2 chaque critère (à ajuster selon feedback)
    return round(0.2 * norm_chan + 0.2 * norm_cap + 0.2 * cent + 0.2 * hist + 0.1 * (1-fees) + 0.1 * route, 3)

# Config
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "daznode")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PUBKEYS = [
    "034ea80f8b148c750463546bd999bf7321a0e6dfc60aaf84bd0400a2e8d376c0d5",
    "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
    "032eafb65801a6cfb8da47c25138aa686640aec7eff486c04e8db777cf14725864",
    "02aced13b08adcbe1e0897ad3b26e4525e1a9cdb76c86ed4aa42a518045bcb7e9f",
    "03423790614f023e3c0cdaa654a3578e919947e4c3a14bf5044e7c787ebd11af1a",
    "034d3a52b36614092f2708f7ad5ceac0cc624e696f463c8b9cba8de4827de2c8dd",
    "032870511bfa0309bab3ca1832ead69eed848a4abddbc4d50e55bb2157f9525e51",
    "02f6fa3a67cb1ae7aa5ac5c86e765e6e2324570b3d6a367dc8c72bac45a5c1743f"
]

async def get_pubkeys_from_mongo(limit=20):
    # On ignore MongoDB, on retourne la liste fournie
    return PUBKEYS

async def main():
    pubkeys = await get_pubkeys_from_mongo(20)
    redis_ops = RedisOperations(REDIS_URL)
    # Instanciation du scraper Amboss (Redis mocké si besoin)
    amboss_scraper = AmbossScraper(redis_ops)
    valid_scores = 0
    errors = 0
    for pubkey in pubkeys:
        logger.info(f"Scoring {pubkey} ...")
        result = {
            "pubkey": pubkey,
            "timestamp": datetime.utcnow().isoformat(),
            "amboss_channel_rank": None,
            "amboss_capacity_rank": None,
            "amboss_channel_norm": None,
            "amboss_capacity_norm": None,
            "sparkseer_cent": None,
            "sparkseer_hist": None,
            "sparkseer_fees": None,
            "lnrouter_route": None,
            "score": None,
            "errors": {}
        }
        try:
            chan_rank, cap_rank, norm_chan, norm_cap = await get_amboss_ranks(pubkey, amboss_scraper)
            spark = await get_sparkseer_metrics(pubkey)
            route = await simulate_lnrouter(pubkey)
            result["amboss_channel_rank"] = chan_rank
            result["amboss_capacity_rank"] = cap_rank
            result["amboss_channel_norm"] = norm_chan
            result["amboss_capacity_norm"] = norm_cap
            result["sparkseer_cent"] = spark["centrality"] if spark else None
            result["sparkseer_hist"] = spark["history"] if spark else None
            result["sparkseer_fees"] = spark["fees"] if spark else None
            result["lnrouter_route"] = route
            # Score uniquement si tout est présent
            if None not in [norm_chan, norm_cap, spark["centrality"], spark["history"], spark["fees"], route]:
                # Nouveau score : pondération brute (à ajuster)
                result["score"] = compute_score(norm_chan, norm_cap, spark["centrality"], spark["history"], spark["fees"], route)
                valid_scores += 1
            else:
                result["errors"] = {k: v for k, v in zip(
                    ["amboss_channel_norm", "amboss_capacity_norm", "sparkseer_cent", "sparkseer_hist", "sparkseer_fees", "lnrouter"],
                    [norm_chan, norm_cap, spark["centrality"] if spark else None, spark["history"] if spark else None, spark["fees"] if spark else None, route]
                ) if v is None}
                errors += 1
        except Exception as e:
            logger.error(f"Erreur pour {pubkey}: {e}")
            result["errors"] = {"exception": str(e)}
            errors += 1
        # Log Redis (clé score:{pubkey}, TTL 24h)
        await redis_ops._init_redis()
        await redis_ops.redis.setex(f"score:{pubkey}", 86400, json.dumps(result))
    logger.info(f"Batch terminé. Scores valides: {valid_scores}, erreurs: {errors}")

if __name__ == "__main__":
    asyncio.run(main()) 