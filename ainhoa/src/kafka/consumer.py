"""
src/kafka/consumer.py - Consumidor de Apache Kafka en Python para anuncios inmobiliarios.

Se suscribe al tópico de anuncios, valida su formato contra el modelo HousingAd,
gestiona errores de deserialización y registra los datos procesados en tiempo real.
"""

import os
import json
from typing import List, Dict, Any, Optional, Callable
from src.extraction.models import HousingAd
from .mock_broker import InMemoryKafkaBroker


class HousingKafkaConsumer:
    """Consumidor de Kafka para recibir e inspeccionar anuncios inmobiliarios."""

    DEFAULT_TOPIC = "euskadi-anuncios-inmobiliarios"
    DEFAULT_GROUP = "euskadi-vivienda-consumidores"

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: Optional[str] = None,
        group_id: Optional[str] = None,
        simulation_mode: Optional[bool] = None
    ):
        self.bootstrap_servers = bootstrap_servers or os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic = topic or os.environ.get("KAFKA_TOPIC", self.DEFAULT_TOPIC)
        self.group_id = group_id or os.environ.get("KAFKA_CONSUMER_GROUP", self.DEFAULT_GROUP)

        env_sim = os.environ.get("KAFKA_SIMULATION_MODE", "").lower() in ("true", "1", "yes")
        self.simulation_mode = simulation_mode if simulation_mode is not None else env_sim

        self._real_consumer = None
        self._mock_broker: Optional[InMemoryKafkaBroker] = None

        if not self.simulation_mode:
            self._init_real_consumer()

        if self._real_consumer is None:
            self.simulation_mode = True
            self._mock_broker = InMemoryKafkaBroker.get_broker(self.topic)

    def _init_real_consumer(self):
        """Intenta conectarse al broker real de Kafka."""
        try:
            from kafka import KafkaConsumer
            self._real_consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers.split(","),
                group_id=self.group_id,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                consumer_timeout_ms=3000,
                value_deserializer=lambda m: json.loads(m.decode("utf-8"))
            )
        except Exception:
            self._real_consumer = None

    def consume_batch(
        self,
        max_messages: int = 10,
        timeout_seconds: float = 2.0,
        on_message_callback: Optional[Callable[[HousingAd, int], None]] = None
    ) -> List[HousingAd]:
        """
        Consume hasta max_messages del tópico.
        Valida que cada mensaje cumpla con el modelo HousingAd y descarta mensajes corruptos sin bloquearse.
        """
        received: List[HousingAd] = []

        if not self.simulation_mode and self._real_consumer:
            try:
                count = 0
                for msg in self._real_consumer:
                    payload = msg.value
                    try:
                        ad = HousingAd(**payload)
                        received.append(ad)
                        count += 1
                        if on_message_callback:
                            on_message_callback(ad, count)
                    except Exception as err:
                        print(f"[AVISO CONSUMIDOR] Mensaje descartado por esquema inválido: {err}")

                    if count >= max_messages:
                        break
            except Exception as e:
                print(f"[ERROR KAFKA CONSUMER] Error durante el consumo: {e}")
        else:
            # Modo broker en memoria
            if self._mock_broker:
                for idx in range(max_messages):
                    payload = self._mock_broker.poll(timeout_seconds=timeout_seconds)
                    if payload is None:
                        break
                    try:
                        ad = HousingAd(**payload)
                        received.append(ad)
                        if on_message_callback:
                            on_message_callback(ad, len(received))
                    except Exception as err:
                        print(f"[AVISO CONSUMIDOR] Mensaje simulado descartado: {err}")

        return received

    def close(self):
        """Cierra el consumidor y libera recursos."""
        if self._real_consumer:
            self._real_consumer.close()
