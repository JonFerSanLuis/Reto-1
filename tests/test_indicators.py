"""
tests/test_indicators.py - Pruebas para el módulo de indicadores complementarios Udalmap.
"""

import os
import tempfile
import pytest
from src.indicators.models import MunicipalIndicatorValue, IndicatorMetadata, IndicatorsDataset
from src.indicators.udalmap_client import UdalmapClient


def test_indicator_models():
    """Comprueba la integridad de los modelos de indicadores."""
    val = MunicipalIndicatorValue(
        municipio_id="48020",
        municipio_nombre="Bilbao",
        indicador_id="162",
        indicador_nombre="Población total",
        unidad="habitantes",
        valores_por_ano={"2023": 344127.0, "2024": 345000.0},
        ultimo_ano="2024",
        ultimo_valor=345000.0
    )
    assert val.municipio_id == "48020"
    assert val.ultimo_valor == 345000.0
    assert len(val.valores_por_ano) == 2


def test_parse_indicator_data():
    """Valida el procesamiento de la estructura nativa devuelta por la API de Udalmap."""
    client = UdalmapClient()
    mock_api_data = {
        "id": "60",
        "name": "Renta personal total",
        "municipalities": [
            {
                "id": "48020",
                "name": "Bilbao",
                "years": [
                    {"2021": 24500.50},
                    {"2022": 25800.00}
                ]
            },
            {
                "id": "20069",
                "name": "Donostia / San Sebastián",
                "years": [
                    {"2021": 28000.00},
                    {"2022": 29500.00}
                ]
            }
        ]
    }
    parsed = client._parse_indicator_data("60", "Renta personal", "€", mock_api_data, filter_munis=["Bilbao"])
    assert len(parsed) == 1
    assert parsed[0].municipio_nombre == "Bilbao"
    assert parsed[0].ultimo_ano == "2022"
    assert parsed[0].ultimo_valor == 25800.00


def test_indicators_save_json_and_csv():
    """Comprueba la persistencia a disco de los indicadores en JSON y CSV."""
    client = UdalmapClient()
    val = MunicipalIndicatorValue(
        municipio_id="01059",
        municipio_nombre="Vitoria-Gasteiz",
        indicador_id="61",
        indicador_nombre="Renta personal disponible",
        unidad="€",
        valores_por_ano={"2022": 21000.0},
        ultimo_ano="2022",
        ultimo_valor=21000.0
    )
    dataset = IndicatorsDataset(registros=[val])

    with tempfile.TemporaryDirectory() as tmpdir:
        json_file = os.path.join(tmpdir, "ind.json")
        csv_file = os.path.join(tmpdir, "ind.csv")

        client.save_to_json(dataset, json_file)
        client.save_to_csv(dataset, csv_file)

        assert os.path.exists(json_file)
        assert os.path.exists(csv_file)
