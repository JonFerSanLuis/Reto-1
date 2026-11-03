"""
src/indicators/ovj_client.py - Cliente de Indicadores del Observatorio Vasco de la Juventud (OVJ).

Recopila y modela los indicadores oficiales de emancipación residencial,
salario medio juvenil y porcentaje de esfuerzo salarial para alquiler y compra
en la Comunidad Autónoma de Euskadi (Gazteen Euskal Behatokia / Eustat).
"""

import os
import json
import csv
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class YouthEmancipationData(BaseModel):
    """Modelo estructurado de indicadores de juventud y vivienda en Euskadi."""
    indicador_id: str
    nombre: str
    unidad: str
    territorio: str = "Euskadi"
    tramo_edad: str = "18-29 años"
    series_anuales: Dict[str, float] = Field(default_factory=dict)
    ultimo_ano: str
    ultimo_valor: float
    descripcion: str


class YouthHousingEffortReport(BaseModel):
    """Informe de cálculo de esfuerzo económico juvenil para una vivienda o municipio."""
    precio_mensual_euros: float
    territorio: str
    salario_medio_joven_neto: float
    tasa_esfuerzo_sin_ayuda_pct: float
    aplica_gaztelagun: bool
    importe_ayuda_gaztelagun_euros: float
    precio_con_gaztelagun_euros: float
    tasa_esfuerzo_con_gaztelagun_pct: float
    diagnostico_tension: str
    fecha_calculo: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OVJYouthEmancipationClient:
    """
    Cliente para consultar y explotar estadísticas del Observatorio Vasco de la Juventud
    y calcular el Índice de Esfuerzo Juvenil (IEJ) en el acceso a la vivienda.
    """

    # Salarios netos mensuales medios de la juventud asalariada (18-29 años) en Euskadi (Fuente: OVJ / Eustat)
    SALARIOS_REFERENCIA_JUVENTUD = {
        "Euskadi": 1420.0,
        "Bizkaia": 1410.0,
        "Gipuzkoa": 1445.0,
        "Araba": 1405.0
    }

    # Ayuda máxima mensual del programa del Gobierno Vasco Gaztelagun para jóvenes menores de 36 años
    GAZTELAGUN_MAX_AYUDA_MENSUAL = 300.0

    # Series oficiales consolidadas del Observatorio Vasco de la Juventud
    OFFICIAL_OVJ_SERIES = [
        {
            "indicador_id": "OVJ_EMAN_18_29",
            "nombre": "Tasa de emancipación residencial de la juventud (18 a 29 años)",
            "unidad": "porcentaje (%)",
            "territorio": "Euskadi",
            "tramo_edad": "18-29 años",
            "series_anuales": {"2020": 32.8, "2021": 31.4, "2022": 32.5, "2023": 33.1, "2024": 33.4},
            "ultimo_ano": "2024",
            "ultimo_valor": 33.4,
            "descripcion": "Porcentaje de personas de 18 a 29 años que residen fuera del hogar de origen."
        },
        {
            "indicador_id": "OVJ_EMAN_30_34",
            "nombre": "Tasa de emancipación residencial de personas adultas jóvenes (30 a 34 años)",
            "unidad": "porcentaje (%)",
            "territorio": "Euskadi",
            "tramo_edad": "30-34 años",
            "series_anuales": {"2020": 71.0, "2021": 70.8, "2022": 72.1, "2023": 73.0, "2024": 73.2},
            "ultimo_ano": "2024",
            "ultimo_valor": 73.2,
            "descripcion": "Porcentaje de personas de 30 a 34 años emancipadas en Euskadi."
        },
        {
            "indicador_id": "OVJ_COSTE_ALQUILER_SOLO",
            "nombre": "Coste de acceso al alquiler libre en solitario (% de salario neto)",
            "unidad": "porcentaje de salario (%)",
            "territorio": "Euskadi",
            "tramo_edad": "18-29 años",
            "series_anuales": {"2020": 53.2, "2021": 54.8, "2022": 57.3, "2023": 58.9, "2024": 61.2},
            "ultimo_ano": "2024",
            "ultimo_valor": 61.2,
            "descripcion": "Porcentaje del salario neto medio que una persona joven debe destinar al pago del alquiler medio en solitario."
        },
        {
            "indicador_id": "OVJ_COSTE_HIPOTECA_SOLO",
            "nombre": "Coste de acceso a la compraventa libre en solitario (% de salario neto)",
            "unidad": "porcentaje de salario (%)",
            "territorio": "Euskadi",
            "tramo_edad": "18-29 años",
            "series_anuales": {"2020": 56.4, "2021": 57.9, "2022": 61.5, "2023": 66.8, "2024": 68.4},
            "ultimo_ano": "2024",
            "ultimo_valor": 68.4,
            "descripcion": "Porcentaje del salario neto necesario para la cuota hipotecaria mensual en solitario."
        }
    ]

    def get_emancipation_indicators(self) -> List[YouthEmancipationData]:
        """Obtiene las series oficiales de indicadores de juventud del Observatorio."""
        return [YouthEmancipationData(**item) for item in self.OFFICIAL_OVJ_SERIES]

    def calculate_youth_effort(
        self,
        precio_mensual_euros: float,
        territorio: str = "Euskadi",
        incluir_gaztelagun: bool = True
    ) -> YouthHousingEffortReport:
        """
        Calcula la tasa de esfuerzo de una persona joven para un precio de alquiler dado,
        evaluando el impacto mitigador de la ayuda Gaztelagun del Gobierno Vasco.
        """
        # Normalizar territorio
        terr_key = "Euskadi"
        for t in ["Bizkaia", "Gipuzkoa", "Araba"]:
            if t.lower() in territorio.lower():
                terr_key = t
                break

        salario_neto = self.SALARIOS_REFERENCIA_JUVENTUD.get(terr_key, 1420.0)

        # Esfuerzo sin ayuda
        esfuerzo_sin_ayuda = (precio_mensual_euros / salario_neto) * 100.0

        # Esfuerzo con ayuda Gaztelagun (hasta 300 €/mes o máx 50% de la renta)
        if incluir_gaztelagun and precio_mensual_euros > 0:
            importe_ayuda = min(self.GAZTELAGUN_MAX_AYUDA_MENSUAL, precio_mensual_euros * 0.5)
            precio_con_ayuda = max(0.0, precio_mensual_euros - importe_ayuda)
            esfuerzo_con_ayuda = (precio_con_ayuda / salario_neto) * 100.0
            aplica_g = True
        else:
            importe_ayuda = 0.0
            precio_con_ayuda = precio_mensual_euros
            esfuerzo_con_ayuda = esfuerzo_sin_ayuda
            aplica_g = False

        # Diagnóstico según recomendación oficial del Banco de España y directivas europeas (máx 30-35%)
        if esfuerzo_sin_ayuda <= 30.0:
            diagnostico = "Sostenible (Acceso residencial viable)"
        elif esfuerzo_sin_ayuda <= 40.0:
            diagnostico = "Tensión moderada (Requiere optimización de gastos o apoyo)"
        else:
            diagnostico = "Tensión severa / Exclusión residencial (Requiere vivienda protegida o Gaztelagun)"

        return YouthHousingEffortReport(
            precio_mensual_euros=round(precio_mensual_euros, 2),
            territorio=terr_key,
            salario_medio_joven_neto=salario_neto,
            tasa_esfuerzo_sin_ayuda_pct=round(esfuerzo_sin_ayuda, 2),
            aplica_gaztelagun=aplica_g,
            importe_ayuda_gaztelagun_euros=round(importe_ayuda, 2),
            precio_con_gaztelagun_euros=round(precio_con_ayuda, 2),
            tasa_esfuerzo_con_gaztelagun_pct=round(esfuerzo_con_ayuda, 2),
            diagnostico_tension=diagnostico
        )

    def save_indicators_to_json(self, indicators: List[YouthEmancipationData], filepath: str) -> None:
        """Exporta las series a formato JSON estructurado."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        data = [i.model_dump() for i in indicators]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_indicators_to_csv(self, indicators: List[YouthEmancipationData], filepath: str) -> None:
        """Exporta las series a formato tabular CSV."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        fieldnames = ["indicador_id", "nombre", "unidad", "territorio", "tramo_edad", "ultimo_ano", "ultimo_valor", "descripcion"]
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for ind in indicators:
                row = ind.model_dump()
                row.pop("series_anuales", None)
                writer.writerow(row)
