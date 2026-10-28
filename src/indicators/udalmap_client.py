"""
src/indicators/udalmap_client.py - Cliente para la API Udalmap de Open Data Euskadi.

Obtiene indicadores oficiales sobre salarios (renta personal y disponible),
población municipal, juventud y demanda de vivienda en los municipios vascos.
"""

import json
import csv
import os
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from .models import MunicipalIndicatorValue, IndicatorMetadata, IndicatorsDataset


class UdalmapClient:
    """Cliente para consumir el servicio de indicadores municipales Udalmap del Gobierno Vasco."""

    BASE_URL = "https://api.euskadi.eus/udalmap/indicators"

    # Indicadores seleccionados para contextualizar la vivienda juvenil
    TARGET_INDICATORS = {
        "162": {
            "nombre": "Población total (hab.)",
            "unidad": "habitantes",
            "periodo": "Series anuales (hasta 2024-2025)",
            "descripcion": "Censo municipal continuo de población por término municipal.",
            "limitaciones": "Los datos corresponden al padrón anual oficial registrado por Eustat/INE."
        },
        "60": {
            "nombre": "Renta personal total media (€)",
            "unidad": "euros anuales",
            "periodo": "Series anuales de estadística de renta",
            "descripcion": "Renta media total percibida por personas físicas residentes.",
            "limitaciones": "Publicación sujeta al calendario de liquidación del IRPF (desfase temporal habitual de 1-2 años)."
        },
        "61": {
            "nombre": "Renta personal disponible media (€)",
            "unidad": "euros anuales",
            "periodo": "Series anuales",
            "descripcion": "Renta personal neta una vez deducidos impuestos directos y cotizaciones.",
            "limitaciones": "Permite calcular con mayor exactitud la tasa de esfuerzo de pago de alquiler/compra."
        },
        "50": {
            "nombre": "Tasa de ocupación juvenil (16 a 24 años) (%)",
            "unidad": "porcentaje",
            "periodo": "Series anuales",
            "descripcion": "Porcentaje de personas ocupadas de 16 a 24 años sobre el total del tramo de edad.",
            "limitaciones": "En municipios pequeños con baja población juvenil, la tasa puede tener mayor varianza muestral."
        },
        "86": {
            "nombre": "Solicitudes de vivienda en Etxebide (‰ habitantes)",
            "unidad": "por mil habitantes",
            "periodo": "Series anuales",
            "descripcion": "Ratio de personas inscritas como demandantes de vivienda protegida en Etxebide por cada 1.000 hab.",
            "limitaciones": "Mide la demanda administrativa registrada, no toda la necesidad latente no inscrita."
        }
    }

    def __init__(self, timeout_seconds: int = 20):
        self.timeout = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AntigravityAcademicResearch/1.0 (Euskadi Indicators; Python requests)",
            "Accept": "application/json"
        })

    def fetch_all_target_indicators(self, filter_municipalities: Optional[List[str]] = None) -> IndicatorsDataset:
        """
        Descarga todos los indicadores clave seleccionados.
        Si se especifica filter_municipalities (nombres o IDs), filtra los resultados.
        """
        dataset = IndicatorsDataset()
        errores: List[str] = []

        # 1. Registrar metadatos
        for ind_id, info in self.TARGET_INDICATORS.items():
            dataset.metadatos[ind_id] = IndicatorMetadata(
                id=ind_id,
                nombre=info["nombre"],
                unidad=info["unidad"],
                periodo_referencia=info["periodo"],
                descripcion_metodologica=info["descripcion"],
                limitaciones=info["limitaciones"]
            )

        # 2. Descargar datos de cada indicador
        for ind_id, meta in dataset.metadatos.items():
            url = f"{self.BASE_URL}/{ind_id}?_format=json"
            try:
                resp = self.session.get(url, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                parsed_vals = self._parse_indicator_data(ind_id, meta.nombre, meta.unidad, data, filter_municipalities)
                dataset.registros.extend(parsed_vals)
            except Exception as e:
                msg = f"Error al descargar indicador {ind_id} ({meta.nombre}): {e}"
                errores.append(msg)

        dataset.errores = errores
        return dataset

    def _parse_indicator_data(
        self,
        ind_id: str,
        nombre: str,
        unidad: str,
        raw_data: Dict[str, Any],
        filter_munis: Optional[List[str]]
    ) -> List[MunicipalIndicatorValue]:
        """Parsea la respuesta JSON de Udalmap extrayendo la serie temporal de cada municipio."""
        results: List[MunicipalIndicatorValue] = []
        munis = raw_data.get("municipalities", [])

        filter_munis_lower = [m.lower() for m in filter_munis] if filter_munis else None

        for m in munis:
            muni_id = str(m.get("id") or "")
            muni_name = str(m.get("name") or "")

            if filter_munis_lower:
                if muni_name.lower() not in filter_munis_lower and muni_id not in filter_munis:
                    continue

            # Extraer años y valores
            years_list = m.get("years", [])
            merged_years: Dict[str, float] = {}
            for year_dict in years_list:
                for y, val in year_dict.items():
                    if val is not None:
                        try:
                            merged_years[str(y)] = float(val)
                        except (ValueError, TypeError):
                            pass

            ultimo_ano = None
            ultimo_valor = None
            if merged_years:
                sorted_years = sorted(merged_years.keys(), key=lambda x: int(x) if x.isdigit() else 0)
                ultimo_ano = sorted_years[-1]
                ultimo_valor = merged_years[ultimo_ano]

            results.append(MunicipalIndicatorValue(
                municipio_id=muni_id,
                municipio_nombre=muni_name,
                indicador_id=ind_id,
                indicador_nombre=nombre,
                unidad=unidad,
                valores_por_ano=merged_years,
                ultimo_ano=ultimo_ano,
                ultimo_valor=ultimo_valor
            ))

        return results

    def save_to_json(self, dataset: IndicatorsDataset, filepath: str) -> None:
        """Guarda los indicadores en JSON preservando metadatos y series temporales."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(dataset.model_dump(), f, ensure_ascii=False, indent=2)

    def save_to_csv(self, dataset: IndicatorsDataset, filepath: str) -> None:
        """Guarda una versión tabular en CSV con el último valor y el año de referencia."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        fieldnames = ["municipio_id", "municipio_nombre", "indicador_id", "indicador_nombre", "unidad", "ultimo_ano", "ultimo_valor"]
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in dataset.registros:
                writer.writerow({
                    "municipio_id": r.municipio_id,
                    "municipio_nombre": r.municipio_nombre,
                    "indicador_id": r.indicador_id,
                    "indicador_nombre": r.indicador_nombre,
                    "unidad": r.unidad,
                    "ultimo_ano": r.ultimo_ano,
                    "ultimo_valor": r.ultimo_valor
                })
