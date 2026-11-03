"""
tests/test_analysis.py - Pruebas unitarias para el módulo de análisis de vivienda juvenil en Euskadi.
"""

import os
import tempfile
import pytest
from src.analysis.housing_study import YouthHousingStudy, MunicipalHousingAnalysis


def test_youth_housing_study_full_analysis():
    study = YouthHousingStudy()
    result = study.run_full_analysis()

    assert "conclusiones" in result
    assert "resumen_territorial" in result
    assert "municipios" in result
    assert result["total_municipios"] == 16

    # Verificar que el ranking está correctamente ordenado de 1 a 16
    rankings = [m["ranking_accesibilidad"] for m in result["municipios"]]
    assert rankings == list(range(1, 17))

    # Agurain o municipios económicos deben estar en los primeros puestos
    primer_muni = result["municipios"][0]
    assert primer_muni["municipio"] in ("Agurain / Salvatierra", "Balmaseda", "Eibar")
    assert primer_muni["esfuerzo_libre_con_gaztelagun_pct"] <= 35.0

    # Donostia / Getxo deben estar en las posiciones más tensionadas
    ultimo_muni = result["municipios"][-1]
    assert ultimo_muni["municipio"] in ("Donostia / San Sebastián", "Getxo")
    assert ultimo_muni["esfuerzo_libre_sin_ayuda_pct"] > 65.0

    # Resumen territorial
    terr = result["resumen_territorial"]
    assert "Bizkaia" in terr
    assert "Gipuzkoa" in terr
    assert "Araba" in terr


def test_study_export_to_json():
    study = YouthHousingStudy()
    result = study.run_full_analysis()

    with tempfile.TemporaryDirectory() as tmpdir:
        out_json = os.path.join(tmpdir, "estudio_test.json")
        study.export_to_json(result, out_json)
        assert os.path.exists(out_json)
        assert os.path.getsize(out_json) > 1000
