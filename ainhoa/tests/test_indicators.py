"""
tests/test_indicators.py - Pruebas para el módulo de indicadores complementarios Udalmap y OVJ.
"""

import os
import tempfile
import pytest
from src.indicators.models import MunicipalIndicatorValue, IndicatorMetadata, IndicatorsDataset
from src.indicators.udalmap_client import UdalmapClient
from src.indicators.ovj_client import OVJYouthEmancipationClient, YouthEmancipationData, YouthHousingEffortReport


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


def test_ovj_emancipation_indicators():
    """Verifica la carga de series de juventud del Observatorio Vasco de la Juventud."""
    ovj_client = OVJYouthEmancipationClient()
    indicators = ovj_client.get_emancipation_indicators()

    assert len(indicators) >= 4
    ids = [ind.indicador_id for ind in indicators]
    assert "OVJ_EMAN_18_29" in ids
    assert "OVJ_COSTE_ALQUILER_SOLO" in ids

    eman_18_29 = next(i for i in indicators if i.indicador_id == "OVJ_EMAN_18_29")
    assert eman_18_29.ultimo_valor == 33.4
    assert eman_18_29.ultimo_ano == "2024"


def test_ovj_youth_effort_calculation():
    """Comprueba el cálculo de esfuerzo económico juvenil y la mitigación de Gaztelagun."""
    ovj_client = OVJYouthEmancipationClient()

    # Alquiler de 850€ en Bizkaia (salario joven ref: 1410€)
    report = ovj_client.calculate_youth_effort(850.0, territorio="Bizkaia", incluir_gaztelagun=True)

    assert report.precio_mensual_euros == 850.0
    assert report.territorio == "Bizkaia"
    assert report.salario_medio_joven_neto == 1410.0
    # Esfuerzo bruto: 850 / 1410 * 100 = 60.28%
    assert report.tasa_esfuerzo_sin_ayuda_pct == pytest.approx(60.28, rel=1e-2)
    # Gaztelagun aplica máximo 300€: 850 - 300 = 550€
    assert report.importe_ayuda_gaztelagun_euros == 300.0
    assert report.precio_con_gaztelagun_euros == 550.0
    # Esfuerzo con ayuda: 550 / 1410 * 100 = 39.01%
    assert report.tasa_esfuerzo_con_gaztelagun_pct == pytest.approx(39.01, rel=1e-2)
    assert "Tensión severa" in report.diagnostico_tension


def test_ovj_save_json_and_csv():
    """Valida la exportación de indicadores de juventud a JSON y CSV."""
    ovj_client = OVJYouthEmancipationClient()
    indicators = ovj_client.get_emancipation_indicators()

    with tempfile.TemporaryDirectory() as tmpdir:
        json_file = os.path.join(tmpdir, "ovj.json")
        csv_file = os.path.join(tmpdir, "ovj.csv")

        ovj_client.save_indicators_to_json(indicators, json_file)
        ovj_client.save_indicators_to_csv(indicators, csv_file)

        assert os.path.exists(json_file)
        assert os.path.exists(csv_file)
        assert os.path.getsize(json_file) > 0
        assert os.path.getsize(csv_file) > 0
