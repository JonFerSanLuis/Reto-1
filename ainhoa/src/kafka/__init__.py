"""
Módulo de simulación de streaming de anuncios inmobiliarios con Apache Kafka en Python.
"""
from .producer import HousingKafkaProducer
from .consumer import HousingKafkaConsumer
from .mock_broker import InMemoryKafkaBroker

__all__ = ["HousingKafkaProducer", "HousingKafkaConsumer", "InMemoryKafkaBroker"]
