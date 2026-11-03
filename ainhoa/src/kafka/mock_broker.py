"""
src/kafka/mock_broker.py - Adaptador en memoria para simulación y pruebas de Apache Kafka.

Permite ejecutar pruebas automatizadas completas del productor y consumidor
sin necesidad de levantar un clúster Kafka/Zookeeper externo.
"""

import json
import queue
import time
from typing import Dict, Any, Optional, List


class InMemoryKafkaBroker:
    """Broker Kafka en memoria para pruebas desacopladas."""

    _instances: Dict[str, "InMemoryKafkaBroker"] = {}

    def __init__(self, topic_name: str = "euskadi-anuncios-inmobiliarios"):
        self.topic = topic_name
        self._queue: queue.Queue = queue.Queue()
        self._all_messages: List[Dict[str, Any]] = []

    @classmethod
    def get_broker(cls, topic_name: str = "euskadi-anuncios-inmobiliarios") -> "InMemoryKafkaBroker":
        if topic_name not in cls._instances:
            cls._instances[topic_name] = InMemoryKafkaBroker(topic_name)
        return cls._instances[topic_name]

    @classmethod
    def reset(cls, topic_name: Optional[str] = None):
        if topic_name:
            if topic_name in cls._instances:
                del cls._instances[topic_name]
        else:
            cls._instances.clear()

    def send(self, message: Dict[str, Any]):
        """Publica un mensaje JSON en el tópico en memoria."""
        self._all_messages.append(message)
        self._queue.put(message)

    def poll(self, timeout_seconds: float = 1.0) -> Optional[Dict[str, Any]]:
        """Extrae un mensaje del tópico en memoria con timeout."""
        try:
            return self._queue.get(timeout=timeout_seconds)
        except queue.Empty:
            return None

    def get_total_messages(self) -> int:
        return len(self._all_messages)
