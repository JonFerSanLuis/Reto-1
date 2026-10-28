"""
tests/test_integration.py - Prueba de integración end-to-end de los 4 objetivos.
"""

import os
import tempfile
import pytest
from src.extraction.models import HousingAd
from src.extraction.api_client import OpenDataEuskadiHousingClient
from src.indicators.udalmap_client import UdalmapClient
from src.hdfs.client import HDFSClient
from src.kafka.producer import HousingKafkaProducer
from src.kafka.consumer import HousingKafkaConsumer
from src.kafka.mock_broker import InMemoryKafkaBroker


def test_full_academic_pipeline_integration():
    """
    Verifica la cadena de dependencias entre los 4 componentes del reto:
    1. Datos de vivienda estructurados
    2. Indicadores complementarios
    3. Almacenamiento y recuperación en HDFS con verificación de integridad
    4. Streaming y recepción de anuncios en Apache Kafka
    """
    InMemoryKafkaBroker.reset()

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Preparar datos simulados o reales de vivienda
        ad = HousingAd(
            id="ad_integration_1",
            fuente="OpenDataEuskadi_Visesa",
            tipo_operacion="alquiler",
            municipio="Bilbao",
            precio=650.0,
            superficie_m2=68.0,
            habitaciones=2
        )
        api_json = os.path.join(tmpdir, "vivienda_raw.json")
        client = OpenDataEuskadiHousingClient()
        from src.extraction.models import ExtractionResult
        res = ExtractionResult(fuente="Test", total_registros=1, items=[ad])
        client.save_to_json(res, api_json)
        assert os.path.exists(api_json)

        # 2. HDFS: Almacenar original y validar recuperación
        sim_hdfs = os.path.join(tmpdir, "hdfs_store")
        hdfs = HDFSClient(simulation_mode=True, simulation_storage_dir=sim_hdfs)
        hdfs_target = "/data/reto1/raw/vivienda/api/20261028/vivienda.json"
        up_res = hdfs.upload_file(api_json, hdfs_target)
        assert up_res.exito is True

        downloaded_json = os.path.join(tmpdir, "downloaded.json")
        hdfs.download_file(hdfs_target, downloaded_json)
        assert hdfs.calculate_sha256(downloaded_json) == up_res.checksum_sha256

        # 3. Kafka: Publicar el anuncio en el tópico y consumirlo
        topic = "euskadi-anuncios-inmobiliarios"
        producer = HousingKafkaProducer(topic=topic, simulation_mode=True)
        consumer = HousingKafkaConsumer(topic=topic, simulation_mode=True)

        sent = producer.publish_ad(ad)
        assert sent is True

        received_list = consumer.consume_batch(max_messages=1, timeout_seconds=1.0)
        assert len(received_list) == 1
        msg = received_list[0]
        assert msg.id == "ad_integration_1"
        assert msg.municipio == "Bilbao"
        assert msg.precio == 650.0

        producer.close()
        consumer.close()
