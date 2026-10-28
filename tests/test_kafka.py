"""
tests/test_kafka.py - Pruebas para el productor y consumidor de Apache Kafka.
"""

import pytest
from src.extraction.models import HousingAd
from src.kafka.producer import HousingKafkaProducer
from src.kafka.consumer import HousingKafkaConsumer
from src.kafka.mock_broker import InMemoryKafkaBroker


@pytest.fixture(autouse=True)
def clean_broker():
    """Limpia los tópicos en memoria antes de cada test."""
    InMemoryKafkaBroker.reset()
    yield
    InMemoryKafkaBroker.reset()


def test_kafka_producer_consumer_flow():
    """Verifica el envío de un anuncio por el productor y su correcta recepción por el consumidor."""
    topic = "test-topic-vivienda"
    producer = HousingKafkaProducer(topic=topic, simulation_mode=True)
    consumer = HousingKafkaConsumer(topic=topic, simulation_mode=True)

    test_ad = HousingAd(
        id="kafka_ad_101",
        fuente="Habitaclia_Scraping",
        tipo_operacion="alquiler",
        municipio="Bilbao",
        precio=875.0,
        superficie_m2=70.0,
        habitaciones=2
    )

    success = producer.publish_ad(test_ad)
    assert success is True

    messages = consumer.consume_batch(max_messages=1, timeout_seconds=1.0)
    assert len(messages) == 1
    received = messages[0]
    assert received.id == "kafka_ad_101"
    assert received.municipio == "Bilbao"
    assert received.precio == 875.0


def test_kafka_stream_progressive_arrival():
    """Comprueba la simulación de streaming progresivo de múltiples anuncios."""
    topic = "test-stream-topic"
    producer = HousingKafkaProducer(topic=topic, simulation_mode=True)
    consumer = HousingKafkaConsumer(topic=topic, simulation_mode=True)

    ads = [
        HousingAd(id=f"stream_{i}", fuente="Test", tipo_operacion="alquiler", municipio="Donostia", precio=900.0 + i)
        for i in range(5)
    ]

    sent = producer.stream_ads(ads, interval_seconds=0.01)
    assert sent == 5

    received = consumer.consume_batch(max_messages=5, timeout_seconds=1.0)
    assert len(received) == 5
    assert [a.id for a in received] == [f"stream_{i}" for i in range(5)]
