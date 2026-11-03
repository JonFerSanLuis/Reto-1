#!/usr/bin/env python3
"""
scripts/run_pipeline.py - Demostración integral de los 4 primeros objetivos del Reto 1:

1. Extracción de vivienda real vía API (Open Data Euskadi / Visesa) y Web Scraping (Habitaclia y Pisos.com).
2. Obtención de indicadores complementarios (Udalmap / Eustat y Observatorio Vasco de la Juventud).
3. Almacenamiento y verificación de recuperación de originales en HDFS.
4. Simulación de streaming de nuevos anuncios en Apache Kafka (productor y consumidor).
"""

import os
import sys
import json
import time
from datetime import datetime, timezone

# Asegurar que el directorio raíz está en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.extraction.api_client import OpenDataEuskadiHousingClient
from src.extraction.scraper import HabitacliaScraper
from src.extraction.pisos_scraper import PisosComScraper
from src.indicators.udalmap_client import UdalmapClient
from src.indicators.ovj_client import OVJYouthEmancipationClient
from src.hdfs.client import HDFSClient
from src.kafka.producer import HousingKafkaProducer
from src.kafka.consumer import HousingKafkaConsumer


def main():
    print("=" * 70)
    print("RETO 1: VIVIENDA JUVENIL EN EUSKADI - PIPELINE INTEGRADO (FASE 1)")
    print("=" * 70)
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    # -------------------------------------------------------------
    # OBJETIVO 1: Extracción de vivienda (API y Web Scraping)
    # -------------------------------------------------------------
    print("\n[OBJETIVO 1] Extracción de datos de vivienda...")
    api_client = OpenDataEuskadiHousingClient()
    print("  -> Consultando API pública de Open Data Euskadi / Visesa...")
    api_result = api_client.fetch_promotions()
    print(f"     [OK] {api_result.total_registros} promociones obtenidas vía API.")

    raw_api_json = os.path.join(BASE_DIR, "data", "raw", f"vivienda_api_{today_str}.json")
    raw_api_csv = os.path.join(BASE_DIR, "data", "raw", f"vivienda_api_{today_str}.csv")
    api_client.save_to_json(api_result, raw_api_json)
    api_client.save_to_csv(api_result, raw_api_csv)
    print(f"     Guardado en: {raw_api_json} y {raw_api_csv}")

    # Guardar muestra pequeña y no sensible en data/samples/
    sample_api_json = os.path.join(BASE_DIR, "data", "samples", "vivienda_api_sample.json")
    api_sample_result = api_result.model_copy(update={"items": api_result.items[:10], "total_registros": min(10, api_result.total_registros)})
    api_client.save_to_json(api_sample_result, sample_api_json)

    scraper = HabitacliaScraper(request_delay_seconds=1.0)
    print("  -> Ejecutando web scraping de anuncios en Habitaclia...")
    scrape_targets = [
        {"municipio": "Bilbao", "tipo": "alquiler", "url": "https://www.habitaclia.com/alquiler-bilbao.htm"}
    ]
    scrape_result = scraper.scrape_targets(targets=scrape_targets, max_items_per_target=15)
    print(f"     [OK] {scrape_result.total_registros} anuncios obtenidos vía Habitaclia.")

    raw_scrape_json = os.path.join(BASE_DIR, "data", "raw", f"vivienda_scraping_{today_str}.json")
    raw_scrape_csv = os.path.join(BASE_DIR, "data", "raw", f"vivienda_scraping_{today_str}.csv")
    scraper.save_to_json(scrape_result, raw_scrape_json)
    scraper.save_to_csv(scrape_result, raw_scrape_csv)

    sample_scrape_json = os.path.join(BASE_DIR, "data", "samples", "vivienda_scraping_sample.json")
    scrape_sample_result = scrape_result.model_copy(update={"items": scrape_result.items[:10], "total_registros": min(10, scrape_result.total_registros)})
    scraper.save_to_json(scrape_sample_result, sample_scrape_json)

    # Scraper adicional de Pisos.com
    pisos_scraper = PisosComScraper(request_delay_seconds=1.0)
    print("  -> Ejecutando web scraping de anuncios en Pisos.com (Euskadi)...")
    pisos_targets = [
        {"municipio": "Bilbao", "provincia": "Bizkaia", "tipo": "alquiler", "url": "https://www.pisos.com/alquiler/viviendas-bilbao/"}
    ]
    pisos_result = pisos_scraper.scrape_targets(targets=pisos_targets, max_items_per_target=10)
    print(f"     [OK] {pisos_result.total_registros} anuncios obtenidos vía Pisos.com.")

    raw_pisos_json = os.path.join(BASE_DIR, "data", "raw", f"vivienda_pisos_{today_str}.json")
    raw_pisos_csv = os.path.join(BASE_DIR, "data", "raw", f"vivienda_pisos_{today_str}.csv")
    pisos_scraper.save_to_json(pisos_result, raw_pisos_json)
    pisos_scraper.save_to_csv(pisos_result, raw_pisos_csv)

    # -------------------------------------------------------------
    # OBJETIVO 2: Indicadores complementarios (Udalmap y OVJ)
    # -------------------------------------------------------------
    print("\n[OBJETIVO 2] Obtención de indicadores complementarios (Eustat/Udalmap y OVJ)...")
    ind_client = UdalmapClient()
    print("  -> Descargando indicadores oficiales municipales Udalmap...")
    munis_demo = ["Bilbao", "Donostia / San Sebastián", "Vitoria-Gasteiz", "Barakaldo", "Getxo"]
    indicators_dataset = ind_client.fetch_all_target_indicators(filter_municipalities=munis_demo)
    print(f"     [OK] {len(indicators_dataset.registros)} series de indicadores municipales recuperadas.")

    raw_ind_json = os.path.join(BASE_DIR, "data", "raw", f"indicadores_udalmap_{today_str}.json")
    raw_ind_csv = os.path.join(BASE_DIR, "data", "raw", f"indicadores_udalmap_{today_str}.csv")
    ind_client.save_to_json(indicators_dataset, raw_ind_json)
    ind_client.save_to_csv(indicators_dataset, raw_ind_csv)

    sample_ind_json = os.path.join(BASE_DIR, "data", "samples", "indicadores_sample.json")
    ind_sample_result = indicators_dataset.model_copy(update={"registros": indicators_dataset.registros[:15]})
    ind_client.save_to_json(ind_sample_result, sample_ind_json)

    # Observatorio Vasco de la Juventud (OVJ)
    ovj_client = OVJYouthEmancipationClient()
    print("  -> Obteniendo estadísticas del Observatorio Vasco de la Juventud (OVJ)...")
    ovj_indicators = ovj_client.get_emancipation_indicators()
    print(f"     [OK] {len(ovj_indicators)} series de juventud cargadas (emancipación, coste y salarios).")

    raw_ovj_json = os.path.join(BASE_DIR, "data", "raw", f"indicadores_ovj_{today_str}.json")
    raw_ovj_csv = os.path.join(BASE_DIR, "data", "raw", f"indicadores_ovj_{today_str}.csv")
    ovj_client.save_indicators_to_json(ovj_indicators, raw_ovj_json)
    ovj_client.save_indicators_to_csv(ovj_indicators, raw_ovj_csv)

    # Ejemplo de cálculo de esfuerzo juvenil sobre el alquiler medio en Bilbao (aprox 950€)
    effort_bilbao = ovj_client.calculate_youth_effort(950.0, territorio="Bizkaia", incluir_gaztelagun=True)
    print(f"     [ANÁLISIS] Esfuerzo en Bilbao (950 €/mes): {effort_bilbao.tasa_esfuerzo_sin_ayuda_pct}% salario joven (sin ayuda) -> {effort_bilbao.tasa_esfuerzo_con_gaztelagun_pct}% (con Gaztelagun). Diagnóstico: {effort_bilbao.diagnostico_tension}")

    # -------------------------------------------------------------
    # OBJETIVO 3: Almacenamiento de originales en HDFS
    # -------------------------------------------------------------
    print("\n[OBJETIVO 3] Almacenamiento y verificación en Apache HDFS...")
    hdfs = HDFSClient()
    live_status = "Clúster Activo (WebHDFS)" if hdfs.is_live_cluster_available() else "Emulación Local HDFS (data/hdfs_storage/)"
    print(f"  -> Conexión HDFS: {live_status}")

    hdfs_api_path = f"/data/reto1/raw/vivienda/api/{today_str}/vivienda_api.json"
    hdfs_scrape_path = f"/data/reto1/raw/vivienda/scraping/{today_str}/vivienda_scraping.json"
    hdfs_ind_path = f"/data/reto1/raw/indicadores/{today_str}/indicadores.json"
    hdfs_ovj_path = f"/data/reto1/raw/indicadores/{today_str}/ovj_juventud.json"

    print("  -> Subiendo ficheros originales a HDFS...")
    res_api = hdfs.upload_file(raw_api_json, hdfs_api_path)
    print(f"     [OK] API: {res_api.hdfs_path} ({res_api.file_size_bytes} bytes, SHA256: {res_api.checksum_sha256[:12]}...)")

    res_scrape = hdfs.upload_file(raw_scrape_json, hdfs_scrape_path)
    print(f"     [OK] Scraping: {res_scrape.hdfs_path} ({res_scrape.file_size_bytes} bytes, SHA256: {res_scrape.checksum_sha256[:12]}...)")

    res_ind = hdfs.upload_file(raw_ind_json, hdfs_ind_path)
    print(f"     [OK] Udalmap: {res_ind.hdfs_path} ({res_ind.file_size_bytes} bytes, SHA256: {res_ind.checksum_sha256[:12]}...)")

    res_ovj = hdfs.upload_file(raw_ovj_json, hdfs_ovj_path)
    print(f"     [OK] OVJ Juventud: {res_ovj.hdfs_path} ({res_ovj.file_size_bytes} bytes, SHA256: {res_ovj.checksum_sha256[:12]}...)")

    # Demostración de recuperación desde HDFS
    print("  -> Comprobando recuperación y verificación de integridad desde HDFS...")
    recovered_local = os.path.join(BASE_DIR, "data", "raw", f"recuperado_hdfs_api_{today_str}.json")
    hdfs.download_file(hdfs_api_path, recovered_local)
    rec_sha = hdfs.calculate_sha256(recovered_local)
    assert rec_sha == res_api.checksum_sha256, "Error: Checksum recuperado no coincide con el original"
    print(f"     [VERIFICADO] Fichero recuperado idéntico al original (SHA-256 coincidente: {rec_sha[:12]}...)")

    # -------------------------------------------------------------
    # OBJETIVO 4: Simulación de anuncios con Kafka (Productor y Consumidor)
    # -------------------------------------------------------------
    print("\n[OBJETIVO 4] Simulación de streaming con Apache Kafka...")
    producer = HousingKafkaProducer()
    consumer = HousingKafkaConsumer()

    # Seleccionar datos para publicar (priorizando Pisos.com o Habitaclia o API)
    sample_ads = (pisos_result.items[:3] + scrape_result.items[:2]) if (pisos_result.items or scrape_result.items) else api_result.items[:5]
    print(f"  -> Publicando {len(sample_ads)} anuncios en el tópico '{producer.topic}'...")

    def on_sent(ad, count):
        print(f"     [Productor -> Kafka] (#{count}) {ad.id}: {ad.titulo[:40] if ad.titulo else 'Sin titulo'}... [{ad.precio} € - {ad.municipio}]")

    sent_count = producer.stream_ads(sample_ads, interval_seconds=0.2, on_sent_callback=on_sent)
    print(f"     Total publicados por el productor: {sent_count}")

    print(f"  -> Consumiendo anuncios desde el tópico '{consumer.topic}'...")
    def on_received(ad, count):
        print(f"     [Consumidor <- Kafka] (#{count}) Recibido: {ad.id} | {ad.municipio} | {ad.tipo_operacion} | {ad.precio} €")

    received_ads = consumer.consume_batch(max_messages=sent_count, timeout_seconds=2.0, on_message_callback=on_received)
    print(f"     Total recibidos por el consumidor: {len(received_ads)}")
    assert len(received_ads) == sent_count, "Error: No todos los mensajes publicados fueron consumidos"
    print("     [VERIFICADO] Todos los anuncios emitidos fueron recibidos y validados contra el esquema HousingAd.")

    producer.close()
    consumer.close()

    print("\n" + "=" * 70)
    print("PIPELINE FINALIZADO CON ÉXITO: LOS 4 OBJETIVOS ESTÁN INTEGRADOS Y OPERATIVOS.")
    print("=" * 70)


if __name__ == "__main__":
    main()
