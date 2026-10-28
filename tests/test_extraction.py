"""
tests/test_extraction.py - Pruebas para los módulos de extracción (API y Scraping).
"""

import os
import tempfile
import pytest
from src.extraction.models import HousingAd, ExtractionResult
from src.extraction.api_client import OpenDataEuskadiHousingClient
from src.extraction.scraper import HabitacliaScraper
from src.extraction.pisos_scraper import PisosComScraper


def test_housing_ad_validation():
    """Valida la creación y tipos de un HousingAd."""
    ad = HousingAd(
        id="test_001",
        fuente="Test_Source",
        tipo_operacion="alquiler",
        municipio="Bilbao",
        precio=850.0,
        superficie_m2=65.0,
        habitaciones=2
    )
    assert ad.id == "test_001"
    assert ad.precio == 850.0
    assert ad.tipo_operacion == "alquiler"
    d = ad.to_dict()
    assert d["municipio"] == "Bilbao"


def test_api_client_parsing():
    """Verifica el parseo de filas crudas devueltas por la API de Visesa."""
    client = OpenDataEuskadiHousingClient()
    mock_row = {
        "idContenido": 12345,
        "codigoInterno": "BI-001",
        "poblacion": "Bilbao",
        "idTipoVenta": 7,
        "fechaPrevista": "Viviendas en alquiler protegido",
        "precioMinimo": "450.50",
        "superficie": "72.0",
        "numeroDormitorios": "2",
        "titulo": "Promoción Bilbao Centro",
        "texto": "24 viviendas de alquiler",
        "direccion": "Gran Vía 1"
    }
    parsed = client._parse_api_row(mock_row)
    assert parsed is not None
    assert parsed.id == "visesa_12345"
    assert parsed.tipo_operacion == "alquiler"
    assert parsed.precio == 450.50
    assert parsed.superficie_m2 == 72.0
    assert parsed.habitaciones == 2
    assert parsed.municipio == "Bilbao"


def test_scraper_parsing_html():
    """Comprueba la capacidad de parsear un artículo HTML sintético con la estructura del portal."""
    scraper = HabitacliaScraper()
    mock_html = """
    <article id="anuncio_999">
        <h2><a href="/inmueble-999.htm">Piso en alquiler en Indautxu</a></h2>
        <span class="font-2">950 €</span>
        <p>Precioso piso de 80 m2 con 3 hab y 1 baño en el centro.</p>
        <span class="location">Indautxu, Bilbao</span>
    </article>
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(mock_html, "html.parser")
    article = soup.find("article")
    ad = scraper._extract_article_data(article, "Bilbao", "alquiler", 0, "http://example.com")

    assert ad is not None
    assert ad.id == "habitaclia_anuncio_999"
    assert ad.precio == 950.0
    assert ad.superficie_m2 == 80.0
    assert ad.habitaciones == 3
    assert ad.banos == 1


def test_pisos_scraper_parsing_html():
    """Verifica el parseo de un anuncio HTML proveniente de Pisos.com."""
    scraper = PisosComScraper()
    mock_html = """
    <div class="ad-preview" data-ad-id="88123">
        <h2 class="ad-preview__title">
            <a href="/alquiler/piso-bilbao-88123.html">Piso luminoso en Abando</a>
        </h2>
        <div class="ad-preview__price">890 €/mes</div>
        <div class="ad-preview__location">Abando, Bilbao</div>
        <p class="description">Estupenda vivienda de 75 m² con 2 habitaciones y 1 baño exterior.</p>
    </div>
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(mock_html, "html.parser")
    card = soup.find("div", class_="ad-preview")
    ad = scraper._extract_card_data(
        card=card,
        municipio="Bilbao",
        provincia="Bizkaia",
        tipo_operacion="alquiler",
        index=0,
        source_url="https://www.pisos.com/alquiler/viviendas-bilbao/"
    )

    assert ad is not None
    assert ad.id == "pisos_88123"
    assert ad.fuente == "PisosCom_Scraping"
    assert ad.precio == 890.0
    assert ad.superficie_m2 == 75.0
    assert ad.habitaciones == 2
    assert ad.banos == 1
    assert ad.municipio == "Bilbao"
    assert ad.provincia == "Bizkaia"
    assert "https://www.pisos.com/alquiler/piso-bilbao-88123.html" in ad.url


def test_save_json_and_csv():
    """Verifica que la exportación a JSON y CSV genera archivos válidos sin pérdida de campos."""
    client = OpenDataEuskadiHousingClient()
    sample_ad = HousingAd(
        id="sample_1",
        fuente="Unit_Test",
        tipo_operacion="compraventa",
        municipio="Donostia",
        precio=280000.0,
        superficie_m2=90.0,
        habitaciones=3
    )
    res = ExtractionResult(fuente="Test", total_registros=1, items=[sample_ad])

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "out.json")
        csv_path = os.path.join(tmpdir, "out.csv")

        client.save_to_json(res, json_path)
        client.save_to_csv(res, csv_path)

        assert os.path.exists(json_path)
        assert os.path.exists(csv_path)

        with open(json_path, "r", encoding="utf-8") as f:
            import json
            data = json.load(f)
            assert data["total_registros"] == 1
            assert data["items"][0]["id"] == "sample_1"
