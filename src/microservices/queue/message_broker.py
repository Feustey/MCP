from abc import ABC, abstractmethod
import json
import logging
import asyncio
from typing import Dict, List, Any, Callable, Optional, Union
from enum import Enum
import uuid
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Types de messages et priorités
class MessagePriority(int, Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 9

class MessageType(str, Enum):
    ANALYSIS_REQUEST = "analysis_request"
    DATA_UPDATE = "data_update"
    ALERT = "alert"
    RECOMMENDATION = "recommendation"
    SYSTEM_EVENT = "system_event"

# Modèle de message standardisé
class Message:
    def __init__(self, 
                 message_type: MessageType,
                 payload: Dict[str, Any],
                 priority: MessagePriority = MessagePriority.NORMAL,
                 message_id: Optional[str] = None,
                 correlation_id: Optional[str] = None,
                 reply_to: Optional[str] = None,
                 ttl: Optional[int] = None):
        self.message_type = message_type
        self.payload = payload
        self.priority = priority
        self.message_id = message_id or str(uuid.uuid4())
        self.correlation_id = correlation_id
        self.reply_to = reply_to
        self.timestamp = datetime.utcnow().isoformat()
        self.ttl = ttl  # Time-to-live en secondes
    
    def to_json(self) -> str:
        return json.dumps({
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "ttl": self.ttl
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        data = json.loads(json_str)
        return cls(
            message_type=MessageType(data["message_type"]),
            payload=data["payload"],
            priority=MessagePriority(data["priority"]),
            message_id=data.get("message_id"),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
            ttl=data.get("ttl")
        )

# Interface abstraite pour les brokers de messages
class MessageBroker(ABC):
    @abstractmethod
    async def connect(self) -> bool:
        """Établit la connexion au broker."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Ferme la connexion au broker."""
        pass
    
    @abstractmethod
    async def create_queue(self, queue_name: str, durable: bool = True, 
                           auto_delete: bool = False, arguments: Dict = None) -> bool:
        """Crée une file d'attente."""
        pass
    
    @abstractmethod
    async def publish(self, queue_name: str, message: Message) -> bool:
        """Publie un message dans une file d'attente."""
        pass
    
    @abstractmethod
    async def subscribe(self, queue_name: str, callback: Callable[[Message], None]) -> bool:
        """S'abonne à une file d'attente pour recevoir des messages."""
        pass
    
    @abstractmethod
    async def unsubscribe(self, queue_name: str) -> bool:
        """Se désabonne d'une file d'attente."""
        pass

    @abstractmethod
    async def queue_exists(self, queue_name: str) -> bool:
        """Vérifie si une file d'attente existe."""
        pass

    @abstractmethod
    async def queue_length(self, queue_name: str) -> int:
        """Récupère le nombre de messages dans une file d'attente."""
        pass

# Implémentation pour RabbitMQ
class RabbitMQBroker(MessageBroker):
    def __init__(self, host: str = 'localhost', port: int = 5672, 
                 username: str = 'guest', password: str = 'guest',
                 vhost: str = '/'):
        self.connection_params = {
            'host': host,
            'port': port,
            'login': username,
            'password': password,
            'virtualhost': vhost
        }
        self.connection = None
        self.channel = None
        self.subscriptions = {}
    
    async def connect(self) -> bool:
        try:
            import aio_pika
            
            self.connection = await aio_pika.connect_robust(**self.connection_params)
            self.channel = await self.connection.channel()
            logger.info(f"Connexion établie avec RabbitMQ à {self.connection_params['host']}:{self.connection_params['port']}")
            return True
        except Exception as e:
            logger.error(f"Erreur de connexion à RabbitMQ: {str(e)}")
            return False
    
    async def disconnect(self) -> bool:
        try:
            if self.connection:
                await self.connection.close()
                self.connection = None
                self.channel = None
                logger.info("Déconnexion de RabbitMQ réussie")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la déconnexion de RabbitMQ: {str(e)}")
            return False
    
    async def create_queue(self, queue_name: str, durable: bool = True, 
                          auto_delete: bool = False, arguments: Dict = None) -> bool:
        try:
            import aio_pika
            
            if not self.channel:
                await self.connect()
            
            await self.channel.declare_queue(
                queue_name,
                durable=durable,
                auto_delete=auto_delete,
                arguments=arguments or {}
            )
            logger.info(f"File d'attente '{queue_name}' créée avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la création de la file d'attente '{queue_name}': {str(e)}")
            return False
    
    async def publish(self, queue_name: str, message: Message) -> bool:
        try:
            import aio_pika
            
            if not self.channel:
                await self.connect()
            
            # Vérifier si la file existe, sinon la créer
            if not await self.queue_exists(queue_name):
                await self.create_queue(queue_name)
            
            # Créer le message AMQP
            amqp_message = aio_pika.Message(
                body=message.to_json().encode(),
                message_id=message.message_id,
                correlation_id=message.correlation_id,
                reply_to=message.reply_to,
                priority=message.priority.value,
                expiration=str(message.ttl * 1000) if message.ttl else None  # Conversion en millisecondes
            )
            
            # Publier le message
            await self.channel.default_exchange.publish(
                amqp_message,
                routing_key=queue_name
            )
            
            logger.debug(f"Message publié dans la file '{queue_name}': {message.message_id}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la publication dans la file '{queue_name}': {str(e)}")
            return False
    
    async def subscribe(self, queue_name: str, callback: Callable[[Message], None]) -> bool:
        try:
            import aio_pika
            
            if not self.channel:
                await self.connect()
            
            # Vérifier si la file existe, sinon la créer
            if not await self.queue_exists(queue_name):
                await self.create_queue(queue_name)
            
            # Créer la fonction de traitement
            async def process_message(message: aio_pika.IncomingMessage):
                async with message.process():
                    try:
                        msg_body = message.body.decode()
                        parsed_message = Message.from_json(msg_body)
                        # Appeler le callback utilisateur de manière asynchrone
                        await asyncio.create_task(callback(parsed_message))
                    except Exception as e:
                        logger.error(f"Erreur lors du traitement du message: {str(e)}")
            
            # S'abonner à la file
            queue = await self.channel.declare_queue(queue_name, passive=True)
            consumer_tag = await queue.consume(process_message)
            
            # Stocker la souscription
            self.subscriptions[queue_name] = consumer_tag
            
            logger.info(f"Abonnement à la file '{queue_name}' réussi")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'abonnement à la file '{queue_name}': {str(e)}")
            return False
    
    async def unsubscribe(self, queue_name: str) -> bool:
        try:
            if not self.channel or queue_name not in self.subscriptions:
                return False
            
            await self.channel.basic_cancel(self.subscriptions[queue_name])
            del self.subscriptions[queue_name]
            
            logger.info(f"Désabonnement de la file '{queue_name}' réussi")
            return True
        except Exception as e:
            logger.error(f"Erreur lors du désabonnement de la file '{queue_name}': {str(e)}")
            return False
    
    async def queue_exists(self, queue_name: str) -> bool:
        try:
            import aio_pika
            
            if not self.channel:
                await self.connect()
            
            try:
                await self.channel.declare_queue(queue_name, passive=True)
                return True
            except aio_pika.exceptions.ChannelClosed:
                return False
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la file '{queue_name}': {str(e)}")
            return False
    
    async def queue_length(self, queue_name: str) -> int:
        try:
            import aio_pika
            
            if not self.channel:
                await self.connect()
            
            try:
                queue = await self.channel.declare_queue(queue_name, passive=True)
                return queue.declaration_result.message_count
            except Exception:
                return 0
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la longueur de la file '{queue_name}': {str(e)}")
            return 0

# Implémentation pour MQTT
class MQTTBroker(MessageBroker):
    def __init__(self, host: str = 'localhost', port: int = 1883, 
                 username: str = None, password: str = None,
                 client_id: str = None):
        self.connection_params = {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'client_id': client_id or f"mcp-mqtt-{uuid.uuid4().hex[:8]}"
        }
        self.client = None
        self.subscriptions = {}
        self.topics_info = {}  # Stocke des informations sur les topics/queues
    
    async def connect(self) -> bool:
        try:
            import paho.mqtt.client as mqtt
            import asyncio
            
            # Créer et configurer le client
            self.client = mqtt.Client(self.connection_params['client_id'])
            
            if self.connection_params['username'] and self.connection_params['password']:
                self.client.username_pw_set(
                    self.connection_params['username'],
                    self.connection_params['password']
                )
            
            # Configurer les callbacks
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            
            # Connecter le client
            self.client.connect(
                self.connection_params['host'],
                self.connection_params['port']
            )
            
            # Démarrer la boucle client dans un thread séparé
            self.client.loop_start()
            
            # Attendre la connexion établie
            await asyncio.sleep(1)
            
            logger.info(f"Connexion établie avec MQTT à {self.connection_params['host']}:{self.connection_params['port']}")
            return True
        except Exception as e:
            logger.error(f"Erreur de connexion à MQTT: {str(e)}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connexion MQTT établie")
            # Réabonner aux anciens topics après reconnexion
            for topic in self.subscriptions:
                client.subscribe(topic)
        else:
            logger.error(f"Erreur de connexion MQTT, code: {rc}")
    
    def _on_message(self, client, userdata, msg):
        try:
            # Extraire le topic et l'ajouter comme une file d'attente
            topic = msg.topic
            
            # Vérifier si nous avons un callback pour ce topic
            if topic in self.subscriptions:
                # Désérialiser le message
                message = Message.from_json(msg.payload.decode())
                
                # Appeler le callback
                callback = self.subscriptions[topic]
                asyncio.create_task(callback(message))
        except Exception as e:
            logger.error(f"Erreur lors du traitement du message MQTT: {str(e)}")
    
    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning(f"Déconnexion MQTT inattendue, code: {rc}")
    
    async def disconnect(self) -> bool:
        try:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
                self.client = None
                logger.info("Déconnexion de MQTT réussie")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la déconnexion de MQTT: {str(e)}")
            return False
    
    async def create_queue(self, queue_name: str, durable: bool = True, 
                          auto_delete: bool = False, arguments: Dict = None) -> bool:
        """
        Dans MQTT, les 'queues' sont des topics.
        Cette méthode est essentiellement un no-op puisque les topics
        sont créés automatiquement lorsque des messages y sont publiés.
        """
        # Stocker les informations du topic pour référence
        self.topics_info[queue_name] = {
            'created': datetime.utcnow(),
            'durable': durable,
            'auto_delete': auto_delete,
            'arguments': arguments or {}
        }
        
        logger.info(f"Topic MQTT '{queue_name}' enregistré")
        return True
    
    async def publish(self, queue_name: str, message: Message) -> bool:
        try:
            if not self.client:
                await self.connect()
            
            # Publier le message au topic
            result = self.client.publish(
                topic=queue_name,
                payload=message.to_json(),
                qos=1 if message.priority == MessagePriority.HIGH else 0,
                retain=False
            )
            
            # Vérifier le résultat
            if result.rc == 0:
                logger.debug(f"Message publié dans le topic '{queue_name}': {message.message_id}")
                return True
            else:
                logger.error(f"Erreur lors de la publication dans le topic '{queue_name}', code: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de la publication dans le topic '{queue_name}': {str(e)}")
            return False
    
    async def subscribe(self, queue_name: str, callback: Callable[[Message], None]) -> bool:
        try:
            if not self.client:
                await self.connect()
            
            # Enregistrer le callback
            self.subscriptions[queue_name] = callback
            
            # S'abonner au topic
            result = self.client.subscribe(queue_name, qos=1)
            
            # Vérifier le résultat
            if result[0] == 0:
                logger.info(f"Abonnement au topic '{queue_name}' réussi")
                return True
            else:
                logger.error(f"Erreur lors de l'abonnement au topic '{queue_name}', code: {result[0]}")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de l'abonnement au topic '{queue_name}': {str(e)}")
            return False
    
    async def unsubscribe(self, queue_name: str) -> bool:
        try:
            if not self.client or queue_name not in self.subscriptions:
                return False
            
            # Se désabonner du topic
            result = self.client.unsubscribe(queue_name)
            
            # Supprimer le callback
            del self.subscriptions[queue_name]
            
            # Vérifier le résultat
            if result[0] == 0:
                logger.info(f"Désabonnement du topic '{queue_name}' réussi")
                return True
            else:
                logger.error(f"Erreur lors du désabonnement du topic '{queue_name}', code: {result[0]}")
                return False
        except Exception as e:
            logger.error(f"Erreur lors du désabonnement du topic '{queue_name}': {str(e)}")
            return False
    
    async def queue_exists(self, queue_name: str) -> bool:
        """
        Dans MQTT, tous les topics existent virtuellement.
        Cette méthode vérifie si nous avons déjà enregistré ce topic.
        """
        return queue_name in self.topics_info
    
    async def queue_length(self, queue_name: str) -> int:
        """
        MQTT ne fournit pas de moyen standard de connaître le nombre
        de messages en attente. On renvoie toujours 0.
        """
        return 0

# Factory pour créer le bon broker selon la configuration
class MessageBrokerFactory:
    @staticmethod
    def create(broker_type: str, config: Dict[str, Any]) -> MessageBroker:
        if broker_type.lower() == 'rabbitmq':
            return RabbitMQBroker(
                host=config.get('host', 'localhost'),
                port=config.get('port', 5672),
                username=config.get('username', 'guest'),
                password=config.get('password', 'guest'),
                vhost=config.get('vhost', '/')
            )
        elif broker_type.lower() == 'mqtt':
            return MQTTBroker(
                host=config.get('host', 'localhost'),
                port=config.get('port', 1883),
                username=config.get('username'),
                password=config.get('password'),
                client_id=config.get('client_id')
            )
        else:
            raise ValueError(f"Type de broker non supporté: {broker_type}")

# Exemple d'utilisation simple du broker de messages
async def example_usage():
    # Créer un broker RabbitMQ
    broker = MessageBrokerFactory.create('rabbitmq', {
        'host': 'localhost',
        'port': 5672
    })
    
    # Se connecter
    await broker.connect()
    
    # Créer une file d'attente
    await broker.create_queue('analytics_requests')
    
    # Callback pour traiter les messages
    async def process_message(message: Message):
        print(f"Message reçu: {message.payload}")
    
    # S'abonner à la file
    await broker.subscribe('analytics_requests', process_message)
    
    # Publier un message
    message = Message(
        message_type=MessageType.ANALYSIS_REQUEST,
        payload={"node_id": "123456", "depth": "full"},
        priority=MessagePriority.HIGH
    )
    await broker.publish('analytics_requests', message)
    
    # Attendre un peu pour démonstration
    await asyncio.sleep(5)
    
    # Se désabonner et se déconnecter
    await broker.unsubscribe('analytics_requests')
    await broker.disconnect()

if __name__ == "__main__":
    # Exemple d'utilisation
    asyncio.run(example_usage()) 