#!/usr/bin/env python3
"""
main.py - Punto de entrada principal y orquestador del Reto 1:
¿Dónde pueden vivir los jóvenes en Euskadi? (Fase 1)

Ejecutable directamente desde Visual Studio Code o terminal:
  python main.py             -> Ejecuta pipeline completo, análisis y abre dashboard visual.
  python main.py --pipeline  -> Ejecuta el pipeline de datos y muestra el informe en terminal.
  python main.py --visual    -> Inicia el servidor web local y abre el dashboard visual en el navegador.
  python main.py --test      -> Ejecuta la suite completa de pruebas unitarias e integración (pytest).
"""

import os
import sys
import argparse
import webbrowser
import threading
import socket
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone

# Asegurar que el directorio raíz está en sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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
from src.analysis.housing_study import YouthHousingStudy


def is_port_in_use(port: int) -> bool:
    """Comprueba si un puerto local ya está en uso."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_visual_server(port: int = 8080, open_browser: bool = True):
    """Inicia el servidor web local estático para el Dashboard Visual."""
    url = f"http://localhost:{port}/dashboard.html"
    
    if is_port_in_use(port):
        print(f"\n[DASHBOARD VISUAL] El servidor web ya está activo en {url}")
        if open_browser:
            print(f"  -> Abriendo navegador en: {url}")
            webbrowser.open(url)
        return

    os.chdir(BASE_DIR)
    handler = SimpleHTTPRequestHandler
    httpd = ThreadingHTTPServer(("0.0.0.0", port), handler)

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    print(f"\n" + "=" * 75)
    print(f"  DASHBOARD VISUAL AUGEN PRO ACTIVO")
    print("=" * 75)
    print(f"  URL Local: {url}")
    print(f"  Presiona Ctrl+C en cualquier momento para detener el servidor.")
    print("=" * 75)

    if open_browser:
        print(f"  -> Abriendo automáticamente en tu navegador predeterminado...")
        time.sleep(0.5)
        webbrowser.open(url)


def run_pipeline() -> dict:
    """Ejecuta los 4 objetivos académicos del reto y el análisis fundamentado."""
    print("=" * 80)
    print("  RETO 1: ¿DÓNDE PUEDEN VIVIR LOS JÓVENES EN EUSKADI?")
    print("  SISTEMA INTEGRAL DE RECOGIDA, ALMACENAMIENTO Y ANÁLISIS DE DATOS")
    print("=" * 80)
    print("SITUACIÓN DE PARTIDA:")
    print("  El acceso a la vivienda es uno de los principales problemas de la juventud.")
    print("  Pregunta: ¿Puede una persona joven independizarse en Euskadi con su salario?")
    print("-" * 80)

    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    # -------------------------------------------------------------
    # OBJETIVO 1: Recopilación de datos reales (API y Web Scraping)
    # -------------------------------------------------------------
    print("\n[OBJETIVO 1] Recopilación de datos reales de vivienda (API + Web Scraping)...")
    
    # 1.1 API Visesa / Open Data Euskadi
    api_client = OpenDataEuskadiHousingClient()
    print("  [API] Consultando API pública de Open Data Euskadi / Visesa WS...")
    api_result = api_client.fetch_promotions()
    print(f"        -> [OK] {api_result.total_registros} promociones de vivienda obtenidas vía API.")

    raw_api_json = os.path.join(BASE_DIR, "data", "raw", f"vivienda_api_{today_str}.json")
    raw_api_csv = os.path.join(BASE_DIR, "data", "raw", f"vivienda_api_{today_str}.csv")
    api_client.save_to_json(api_result, raw_api_json)
    api_client.save_to_csv(api_result, raw_api_csv)

    # 1.2 Web Scraping Habitaclia
    scraper = HabitacliaScraper(request_delay_seconds=1.0)
    print("  [Scraping] Extrayendo anuncios de alquiler en Habitaclia (Bilbao / Euskadi)...")
    scrape_targets = [{"municipio": "Bilbao", "tipo": "alquiler", "url": "https://www.habitaclia.com/alquiler-bilbao.htm"}]
    scrape_result = scraper.scrape_targets(targets=scrape_targets, max_items_per_target=15)
    print(f"        -> [OK] {scrape_result.total_registros} anuncios de alquiler obtenidos vía Habitaclia.")

    raw_scrape_json = os.path.join(BASE_DIR, "data", "raw", f"vivienda_scraping_{today_str}.json")
    raw_scrape_csv = os.path.join(BASE_DIR, "data", "raw", f"vivienda_scraping_{today_str}.csv")
    scraper.save_to_json(scrape_result, raw_scrape_json)
    scraper.save_to_csv(scrape_result, raw_scrape_csv)

    # 1.3 Web Scraping Pisos.com
    pisos_scraper = PisosComScraper(request_delay_seconds=1.0)
    print("  [Scraping] Extrayendo ofertas de vivienda en Pisos.com...")
    pisos_targets = [{"municipio": "Bilbao", "provincia": "Bizkaia", "tipo": "alquiler", "url": "https://www.pisos.com/alquiler/viviendas-bilbao/"}]
    pisos_result = pisos_scraper.scrape_targets(targets=pisos_targets, max_items_per_target=10)
    print(f"        -> [OK] {pisos_result.total_registros} ofertas obtenidas vía Pisos.com.")

    raw_pisos_json = os.path.join(BASE_DIR, "data", "raw", f"vivienda_pisos_{today_str}.json")
    raw_pisos_csv = os.path.join(BASE_DIR, "data", "raw", f"vivienda_pisos_{today_str}.csv")
    pisos_scraper.save_to_json(pisos_result, raw_pisos_json)
    pisos_scraper.save_to_csv(pisos_result, raw_pisos_csv)

    # -------------------------------------------------------------
    # OBJETIVO 2: Indicadores complementarios (Udalmap y OVJ)
    # -------------------------------------------------------------
    print("\n[OBJETIVO 2] Obtención de indicadores complementarios (Eustat/Udalmap y OVJ)...")
    
    # 2.1 Eustat / Udalmap (demografía, rentas, desempleo)
    ind_client = UdalmapClient()
    print("  [Udalmap] Descargando indicadores socioeconómicos municipales...")
    munis_demo = ["Bilbao", "Donostia / San Sebastián", "Vitoria-Gasteiz", "Barakaldo", "Getxo", "Zarautz", "Eibar", "Agurain / Salvatierra"]
    indicators_dataset = ind_client.fetch_all_target_indicators(filter_municipalities=munis_demo)
    print(f"        -> [OK] {len(indicators_dataset.registros)} series temporales municipales cargadas.")

    raw_ind_json = os.path.join(BASE_DIR, "data", "raw", f"indicadores_udalmap_{today_str}.json")
    raw_ind_csv = os.path.join(BASE_DIR, "data", "raw", f"indicadores_udalmap_{today_str}.csv")
    ind_client.save_to_json(indicators_dataset, raw_ind_json)
    ind_client.save_to_csv(indicators_dataset, raw_ind_csv)

    # 2.2 Observatorio Vasco de la Juventud (salarios jóvenes, emancipación, Gaztelagun)
    ovj_client = OVJYouthEmancipationClient()
    print("  [OVJ] Obteniendo salarios netos jóvenes y series de emancipación...")
    ovj_indicators = ovj_client.get_emancipation_indicators()
    print(f"        -> [OK] {len(ovj_indicators)} series oficiales de juventud y vivienda registradas.")

    raw_ovj_json = os.path.join(BASE_DIR, "data", "raw", f"indicadores_ovj_{today_str}.json")
    raw_ovj_csv = os.path.join(BASE_DIR, "data", "raw", f"indicadores_ovj_{today_str}.csv")
    ovj_client.save_indicators_to_json(ovj_indicators, raw_ovj_json)
    ovj_client.save_indicators_to_csv(ovj_indicators, raw_ovj_csv)

    # -------------------------------------------------------------
    # OBJETIVO 3: Almacenamiento y verificación en Apache HDFS
    # -------------------------------------------------------------
    print("\n[OBJETIVO 3] Almacenamiento de originales y verificación de integridad en HDFS...")
    hdfs = HDFSClient()
    modo_hdfs = "Clúster Activo (WebHDFS)" if hdfs.is_live_cluster_available() else "Emulación Local HDFS (data/hdfs_storage/)"
    print(f"  [HDFS] Modo operativo: {modo_hdfs}")

    hdfs_api_path = f"/data/reto1/raw/vivienda/api/{today_str}/vivienda_api.json"
    hdfs_scrape_path = f"/data/reto1/raw/vivienda/scraping/{today_str}/vivienda_scraping.json"
    hdfs_ind_path = f"/data/reto1/raw/indicadores/{today_str}/indicadores.json"
    hdfs_ovj_path = f"/data/reto1/raw/indicadores/{today_str}/ovj_juventud.json"

    res_api = hdfs.upload_file(raw_api_json, hdfs_api_path)
    res_scrape = hdfs.upload_file(raw_scrape_json, hdfs_scrape_path)
    res_ind = hdfs.upload_file(raw_ind_json, hdfs_ind_path)
    res_ovj = hdfs.upload_file(raw_ovj_json, hdfs_ovj_path)
    print(f"        -> [OK] Ficheros brutos almacenados en particiones HDFS.")

    # Verificación de integridad con SHA-256
    recovered_local = os.path.join(BASE_DIR, "data", "raw", f"recuperado_hdfs_api_{today_str}.json")
    hdfs.download_file(hdfs_api_path, recovered_local)
    rec_sha = hdfs.calculate_sha256(recovered_local)
    assert rec_sha == res_api.checksum_sha256, "Error: Checksum SHA-256 no coincide"
    print(f"        -> [VERIFICADO] Recuperación HDFS íntegra (SHA-256: {rec_sha[:16]}...).")

    # -------------------------------------------------------------
    # OBJETIVO 4: Streaming en tiempo real con Apache Kafka
    # -------------------------------------------------------------
    print("\n[OBJETIVO 4] Simulación de streaming con Apache Kafka...")
    producer = HousingKafkaProducer()
    consumer = HousingKafkaConsumer()
    print(f"  [Kafka] Tópico oficial: '{producer.topic}'")

    sample_ads = (pisos_result.items[:3] + scrape_result.items[:2]) if (pisos_result.items or scrape_result.items) else api_result.items[:5]
    print(f"  [Kafka] Productor emitiendo {len(sample_ads)} anuncios inmobiliarios...")

    def on_sent(ad, count):
        print(f"        -> [Productor -> Kafka] (#{count}) {ad.id}: {ad.municipio} | {ad.precio} € | {ad.tipo_operacion}")

    sent_count = producer.stream_ads(sample_ads, interval_seconds=0.15, on_sent_callback=on_sent)
    print(f"  [Kafka] Consumidor recibiendo y validando contra esquema HousingAd...")

    def on_received(ad, count):
        print(f"        <- [Consumidor <- Kafka] (#{count}) Validado: {ad.id} [{ad.municipio}]")

    received_ads = consumer.consume_batch(max_messages=sent_count, timeout_seconds=2.0, on_message_callback=on_received)
    assert len(received_ads) == sent_count, "Error en recepción de mensajes Kafka"
    print(f"        -> [VERIFICADO] {len(received_ads)}/{sent_count} mensajes validados correctamente en tiempo real.")

    producer.close()
    consumer.close()

    # -------------------------------------------------------------
    # SÍNTESIS ANALÍTICA: RESPUESTA A LA ENTIDAD PÚBLICA
    # -------------------------------------------------------------
    study = YouthHousingStudy()
    study_data = study.run_full_analysis()

    # Guardar datos analizados para el dashboard y el informe
    processed_dir = os.path.join(BASE_DIR, "data", "processed")
    os.makedirs(processed_dir, exist_ok=True)
    study.export_to_json(study_data, os.path.join(processed_dir, "estudio_vivienda_euskadi.json"))
    study.export_to_json(study_data, os.path.join(processed_dir, "dashboard_data.json"))

    # Mostrar informe estructurado en el terminal de VS Code
    study.print_terminal_report(study_data)

    return study_data


def run_tests() -> int:
    """Ejecuta la suite de pruebas unitarias e integración con pytest."""
    import pytest
    print("\n" + "=" * 75)
    print("  EJECUTANDO SUITE DE PRUEBAS AUTOMATIZADAS (PYTEST)")
    print("=" * 75)
    retcode = pytest.main(["-v", "tests/"])
    return retcode


def main():
    parser = argparse.ArgumentParser(
        description="Reto 1: Acceso a la Vivienda para Jóvenes en Euskadi - Orquestador Ejecutable"
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="Ejecuta únicamente el pipeline de datos y muestra el informe en consola (sin navegador)."
    )
    parser.add_argument(
        "--visual",
        action="store_true",
        help="Inicia directamente el servidor web del Dashboard Visual y abre el navegador."
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Ejecuta la suite completa de pruebas con pytest."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Puerto HTTP para el Dashboard Visual (por defecto: 8080)."
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Inicia el servidor web sin abrir la ventana del navegador automáticamente."
    )

    args = parser.parse_args()

    if args.test:
        code = run_tests()
        sys.exit(code)

    if args.visual:
        start_visual_server(port=args.port, open_browser=not args.no_browser)
        print("\nServidor activo. Presiona Ctrl+C para detener.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nServidor detenido.")
            sys.exit(0)

    # Ejecución por defecto: Pipeline completo + Lanzamiento del Dashboard Visual
    run_pipeline()

    if not args.pipeline:
        print("\nIniciando interfaz visual para exploración interactiva...")
        start_visual_server(port=args.port, open_browser=not args.no_browser)
        print("\nPara interactuar con el mapa, fotografías y el simulador de esfuerzo,")
        print(f"accede a: http://localhost:{args.port}/dashboard.html")
        print("\n(Presiona Ctrl+C en cualquier momento para finalizar)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nFinalizado.")
            sys.exit(0)


if __name__ == "__main__":
    main()
