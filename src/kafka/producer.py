"""
src/kafka/producer.py - Productor de Apache Kafka en Python para anuncios inmobiliarios.

Publica eventos JSON con la estructura de anuncios obtenida de fuentes reales de Euskadi.
Permite simular la llegada progresiva de anuncios mediante un intervalo configurable.
"""

import os
import json
import time
from typing import List, Dict, Any, Optional, Callable
from src.extraction.models import HousingAd
from .mock_broker import InMemoryKafkaBroker


class HousingKafkaProducer:
    """Productor Kafka con soporte dual: clúster real o broker en memoria para pruebas."""

    DEFAULT_TOPIC = "euskadi-anuncios-inmobiliarios"

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: Optional[str] = None,
        simulation_mode: Optional[bool] = None
    ):
        self.bootstrap_servers = bootstrap_servers or os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic = topic or os.environ.get("KAFKA_TOPIC", self.DEFAULT_TOPIC)

        env_sim = os.environ.get("KAFKA_SIMULATION_MODE", "").lower() in ("true", "1", "yes")
        self.simulation_mode = simulation_mode if simulation_mode is not None else env_sim

        self._real_producer = None
        self._mock_broker: Optional[InMemoryKafkaBroker] = None

        if not self.simulation_mode:
            self._init_real_producer()

        if self._real_producer is None:
            self.simulation_mode = True
            self._mock_broker = InMemoryKafkaBroker.get_broker(self.topic)

    def _init_real_producer(self):
        """Intenta conectarse al broker real de Kafka."""
        try:
            from kafka import KafkaProducer
            self._real_producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers.split(","),
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retries=3,
                request_timeout_ms=3000
            )
        except Exception:
            # Si el broker no está disponible, se activará el modo simulación
            self._real_producer = None

    def publish_ad(self, ad: HousingAd) -> bool:
        """
        Publica un anuncio inmobiliario en el tópico de Kafka.
        El mensaje se serializa en JSON con la clave del municipio para particionado natural.
        """
        ad_payload = ad.model_dump()
        key = ad.municipio or "EUSKADI"

        if not self.simulation_mode and self._real_producer:
            try:
                future = self._real_producer.send(self.topic, key=key, value=ad_payload)
                self._real_producer.flush()
                return True
            except Exception as e:
                print(f"[ERROR KAFKA PRODUCER] Fallo al publicar anuncio {ad.id}: {e}")
                return False
        else:
            if self._mock_broker:
                self._mock_broker.send(ad_payload)
                return True
            return False

    def stream_ads(
        self,
        ads: List[HousingAd],
        interval_seconds: float = 0.5,
        on_sent_callback: Optional[Callable[[HousingAd, int], None]] = None
    ) -> int:
        """
        Simula la llegada progresiva de nuevos anuncios inmobiliarios con un retardo configurable.
        Retorna el número de anuncios publicados satisfactoriamente.
        """
        sent_count = 0
        for idx, ad in enumerate(ads, start=1):
            success = self.publish_ad(ad)
            if success:
                sent_count += 1
                if on_sent_callback:
                    on_sent_callback(ad, sent_count)
            if interval_seconds > 0 and idx < len(ads):
                time.sleep(interval_seconds)
        return sent_count

    def close(self):
        """Cierra la conexión con el broker."""
        if self._real_producer:
            self._real_producer.close()
