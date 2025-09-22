import random
import json
from locust import HttpUser, task, between, events
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPLoadTestUser(HttpUser):
    wait_time = between(0.5, 2)
    
    def on_start(self):
        """Exécuté une fois au début de chaque utilisateur simulé"""
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.user_id = f"user_{random.randint(1000, 9999)}"
        logger.info(f"Starting user: {self.user_id}")
    
    @task(3)
    def test_health_check(self):
        """Test endpoint de santé - haute fréquence"""
        with self.client.get("/health", 
                             catch_response=True,
                             name="Health Check") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(5)
    def test_lightning_operations(self):
        """Test opérations Lightning Network"""
        operations = [
            ("GET", "/api/v1/lightning/status"),
            ("GET", "/api/v1/health"),
        ]
        
        method, endpoint = random.choice(operations)
        
        with self.client.request(method, endpoint,
                                 headers=self.headers,
                                 catch_response=True,
                                 name=f"Lightning: {endpoint}") as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Lightning operation failed: {response.status_code}")
    
    @task(4)
    def test_analytics_endpoints(self):
        """Test endpoints d'analytics"""
        analytics_endpoints = [
            "/health",
            "/api/v1/health",
            "/api/v1/lightning/status"
        ]
        
        endpoint = random.choice(analytics_endpoints)
        params = {
            "period": random.choice(["hour", "day", "week"]),
            "limit": random.randint(10, 100)
        }
        
        with self.client.get(endpoint,
                             params=params,
                             headers=self.headers,
                             catch_response=True,
                             name=f"Analytics: {endpoint}") as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Analytics failed: {response.status_code}")
    
    @task(2)
    def test_node_analysis(self):
        """Test analyse de nœuds Lightning"""
        # Utilise un node_id générique pour tester
        node_id = "03" + "0" * 64  # Node ID Lightning valide fictif
        
        endpoints = [
            f"/api/v1/lightning/nodes/{node_id}/analysis",
            f"/api/v1/lightning/nodes/{node_id}/enhanced-analysis",
            f"/api/v1/lightning/nodes/{node_id}/recommendations"
        ]
        
        endpoint = random.choice(endpoints)
        
        with self.client.get(endpoint,
                             headers=self.headers,
                             catch_response=True,
                             name="Node Analysis") as response:
            if response.status_code in [200, 404]:  # 404 attendu pour node fictif
                response.success()
            else:
                response.failure(f"Node analysis failed: {response.status_code}")
    
    @task(1)
    def test_various_endpoints(self):
        """Test divers endpoints disponibles"""
        endpoints = [
            "/",
            "/health", 
            "/api/v1/health",
            "/api/v1/lightning/status"
        ]
        
        endpoint = random.choice(endpoints)
        
        with self.client.get(endpoint,
                             headers=self.headers,
                             catch_response=True,
                             name="Various Endpoints") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Endpoint failed: {response.status_code}")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Exécuté au début du test"""
    logger.info("=" * 50)
    logger.info("Starting MCP Lightning Load Test")
    logger.info(f"Target host: {environment.host}")
    logger.info(f"Time: {datetime.now().isoformat()}")
    logger.info("=" * 50)

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Exécuté à la fin du test"""
    logger.info("=" * 50)
    logger.info("Load Test Completed")
    logger.info(f"Total requests: {environment.stats.total.num_requests}")
    logger.info(f"Total failures: {environment.stats.total.num_failures}")
    logger.info(f"Average response time: {environment.stats.total.avg_response_time:.2f}ms")
    logger.info(f"RPS: {environment.stats.total.current_rps:.2f}")
    logger.info("=" * 50)

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log des métriques pour chaque requête (échantillonné)"""
    # Log seulement 10% des requêtes pour éviter la surcharge
    if random.random() < 0.1:
        if exception:
            logger.warning(f"Request failed: {name} - {exception}")
        elif response_time > 1000:  # Plus d'1 seconde
            logger.warning(f"Slow request: {name} - {response_time:.2f}ms")