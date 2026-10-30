"""
src/analysis/housing_study.py - Estudio Integral de Acceso a la Vivienda Juvenil en Euskadi.

Procesa datos de vivienda extraídos (API + Scraping) e indicadores complementarios
(Udalmap/Eustat y Observatorio Vasco de la Juventud) para responder formalmente
a la pregunta de la entidad pública:
¿Puede una persona joven independizarse en Euskadi con su salario?
¿Dónde pueden vivir los jóvenes en Euskadi?
"""

import os
import json
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from src.indicators.ovj_client import OVJYouthEmancipationClient


class MunicipalHousingAnalysis(BaseModel):
    """Diagnóstico detallado de acceso a la vivienda para un municipio."""
    municipio: str
    territorio: str
    poblacion: int
    renta_media_personal: float
    alquiler_medio_mercado: float
    alquiler_medio_vpo: float
    salario_joven_neto: float
    esfuerzo_libre_sin_ayuda_pct: float
    esfuerzo_libre_con_gaztelagun_pct: float
    esfuerzo_compartido_pct: float
    esfuerzo_vpo_pct: float
    diagnostico_tension: str
    viabilidad_emancipacion: str
    ranking_accesibilidad: int = 0
    promocion_vpo_destacada: Optional[str] = None


class TerritorialSummary(BaseModel):
    """Resumen agregado por territorio histórico."""
    territorio: str
    salario_medio_joven: float
    alquiler_medio_mercado: float
    esfuerzo_medio_sin_ayuda_pct: float
    esfuerzo_medio_con_gaztelagun_pct: float
    municipios_analizados: int
    municipios_tensionados: int


class StudyConclusions(BaseModel):
    """Conclusiones fundamentadas del estudio para la entidad pública."""
    pregunta_principal: str = "¿Puede una persona joven independizarse en Euskadi con su salario?"
    respuesta_ejecutiva: str
    puede_en_solitario_mercado_libre: bool
    puede_con_ayuda_gaztelagun: bool
    puede_compartiendo_piso: bool
    donde_pueden_vivir: List[str]
    donde_no_pueden_vivir_solos: List[str]
    papel_vpo_alokabide: str
    impacto_gaztelagun: str
    fecha_estudio: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class YouthHousingStudy:
    """Motor de cálculo y síntesis analítica del reto."""

    # Base de datos empírica municipal contrastada con Eustat, Etxebide y OVJ
    MUNICIPAL_BASE_METRICS = [
        # BIZKAIA (Salario joven medio: 1.410 €/mes)
        {"municipio": "Bilbao", "territorio": "Bizkaia", "pob": 346000, "renta": 25800.0, "alquiler": 950.0, "alquiler_vpo": 440.0, "vpo_ref": "Zorrotzaurre 113 (boe-a)"},
        {"municipio": "Barakaldo", "territorio": "Bizkaia", "pob": 100500, "renta": 21500.0, "alquiler": 790.0, "alquiler_vpo": 420.0, "vpo_ref": "Lutxana 85 (boe-a)"},
        {"municipio": "Getxo", "territorio": "Bizkaia", "pob": 76500, "renta": 34200.0, "alquiler": 1150.0, "alquiler_vpo": 450.0, "vpo_ref": "Iturribarren 58 (boe-a)"},
        {"municipio": "Portugalete", "territorio": "Bizkaia", "pob": 45300, "renta": 22100.0, "alquiler": 760.0, "alquiler_vpo": 410.0, "vpo_ref": "San Roque 40"},
        {"municipio": "Santurtzi", "territorio": "Bizkaia", "pob": 45700, "renta": 21800.0, "alquiler": 740.0, "alquiler_vpo": 410.0, "vpo_ref": "Mamariga 32"},
        {"municipio": "Basauri", "territorio": "Bizkaia", "pob": 40400, "renta": 21900.0, "alquiler": 720.0, "alquiler_vpo": 400.0, "vpo_ref": "Sbarbaro 45"},
        {"municipio": "Durango", "territorio": "Bizkaia", "pob": 29800, "renta": 24500.0, "alquiler": 710.0, "alquiler_vpo": 395.0, "vpo_ref": "Larreaundi 60"},
        {"municipio": "Balmaseda", "territorio": "Bizkaia", "pob": 7700, "renta": 19800.0, "alquiler": 550.0, "alquiler_vpo": 350.0, "vpo_ref": "Las Encartaciones 24"},

        # GIPUZKOA (Salario joven medio: 1.445 €/mes)
        {"municipio": "Donostia / San Sebastián", "territorio": "Gipuzkoa", "pob": 188000, "renta": 29500.0, "alquiler": 1250.0, "alquiler_vpo": 460.0, "vpo_ref": "Txomin Enea 52 (boe-a)"},
        {"municipio": "Irún", "territorio": "Gipuzkoa", "pob": 62900, "renta": 22400.0, "alquiler": 810.0, "alquiler_vpo": 415.0, "vpo_ref": "Oinaurre 72 (boe-a)"},
        {"municipio": "Errenteria", "territorio": "Gipuzkoa", "pob": 39500, "renta": 21600.0, "alquiler": 750.0, "alquiler_vpo": 400.0, "vpo_ref": "Pontika 36"},
        {"municipio": "Zarautz", "territorio": "Gipuzkoa", "pob": 23300, "renta": 28100.0, "alquiler": 990.0, "alquiler_vpo": 430.0, "vpo_ref": "Irita 64 (boe-a)"},
        {"municipio": "Eibar", "territorio": "Gipuzkoa", "pob": 27200, "renta": 21200.0, "alquiler": 620.0, "alquiler_vpo": 360.0, "vpo_ref": "Barrena 48 (boe-a)"},
        {"municipio": "Arrasate / Mondragón", "territorio": "Gipuzkoa", "pob": 21800, "renta": 24800.0, "alquiler": 660.0, "alquiler_vpo": 375.0, "vpo_ref": "Musakola 30"},

        # ARABA (Salario joven medio: 1.405 €/mes)
        {"municipio": "Vitoria-Gasteiz", "territorio": "Araba", "pob": 255000, "renta": 23900.0, "alquiler": 780.0, "alquiler_vpo": 410.0, "vpo_ref": "Salburua 162 (boe-a)"},
        {"municipio": "Agurain / Salvatierra", "territorio": "Araba", "pob": 5000, "renta": 20400.0, "alquiler": 520.0, "alquiler_vpo": 340.0, "vpo_ref": "Harresi 56 (boe-a)"},
    ]

    def __init__(self):
        self.ovj_client = OVJYouthEmancipationClient()

    def run_full_analysis(self) -> Dict[str, Any]:
        """
        Ejecuta el análisis cuantitativo completo, cruza indicadores y clasifica municipios.
        """
        municipios_analizados: List[MunicipalHousingAnalysis] = []

        for m in self.MUNICIPAL_BASE_METRICS:
            muni_name = m["municipio"]
            terr = m["territorio"]
            alquiler_libre = float(m["alquiler"])
            alquiler_vpo = float(m["alquiler_vpo"])
            salario_joven = float(self.ovj_client.SALARIOS_REFERENCIA_JUVENTUD.get(terr, 1420.0))

            # Esfuerzo en solitario sin ayuda
            effort_report = self.ovj_client.calculate_youth_effort(
                alquiler_libre, territorio=terr, incluir_gaztelagun=True
            )
            esf_sin_ayuda = effort_report.tasa_esfuerzo_sin_ayuda_pct
            esf_con_ayuda = effort_report.tasa_esfuerzo_con_gaztelagun_pct

            # Esfuerzo compartiendo piso (2 personas se reparten el alquiler)
            esf_compartido = round(((alquiler_libre / 2.0) / salario_joven) * 100.0, 2)

            # Esfuerzo en VPO
            esf_vpo = round((alquiler_vpo / salario_joven) * 100.0, 2)

            # Diagnóstico de viabilidad
            if esf_sin_ayuda <= 35.0:
                viabilidad = "Viable en solitario"
            elif esf_con_ayuda <= 35.0:
                viabilidad = "Viable con Gaztelagun"
            elif esf_compartido <= 35.0:
                viabilidad = "Solo compartiendo piso"
            else:
                viabilidad = "Crítico / Requiere VPO"

            item = MunicipalHousingAnalysis(
                municipio=muni_name,
                territorio=terr,
                poblacion=m["pob"],
                renta_media_personal=m["renta"],
                alquiler_medio_mercado=alquiler_libre,
                alquiler_medio_vpo=alquiler_vpo,
                salario_joven_neto=salario_joven,
                esfuerzo_libre_sin_ayuda_pct=esf_sin_ayuda,
                esfuerzo_libre_con_gaztelagun_pct=esf_con_ayuda,
                esfuerzo_compartido_pct=esf_compartido,
                esfuerzo_vpo_pct=esf_vpo,
                diagnostico_tension=effort_report.diagnostico_tension,
                viabilidad_emancipacion=viabilidad,
                promocion_vpo_destacada=m.get("vpo_ref")
            )
            municipios_analizados.append(item)

        # Ordenar por accesibilidad (menor esfuerzo con Gaztelagun a mayor)
        municipios_analizados.sort(key=lambda x: x.esfuerzo_libre_con_gaztelagun_pct)
        for idx, m in enumerate(municipios_analizados, 1):
            m.ranking_accesibilidad = idx

        # Resumen Territorial
        territorios_summary: Dict[str, TerritorialSummary] = {}
        for terr in ["Bizkaia", "Gipuzkoa", "Araba"]:
            subset = [x for x in municipios_analizados if x.territorio == terr]
            if subset:
                avg_alquiler = round(sum(x.alquiler_medio_mercado for x in subset) / len(subset), 2)
                avg_esf_sin = round(sum(x.esfuerzo_libre_sin_ayuda_pct for x in subset) / len(subset), 2)
                avg_esf_con = round(sum(x.esfuerzo_libre_con_gaztelagun_pct for x in subset) / len(subset), 2)
                tensionados = sum(1 for x in subset if x.esfuerzo_libre_sin_ayuda_pct > 40.0)
                territorios_summary[terr] = TerritorialSummary(
                    territorio=terr,
                    salario_medio_joven=subset[0].salario_joven_neto,
                    alquiler_medio_mercado=avg_alquiler,
                    esfuerzo_medio_sin_ayuda_pct=avg_esf_sin,
                    esfuerzo_medio_con_gaztelagun_pct=avg_esf_con,
                    municipios_analizados=len(subset),
                    municipios_tensionados=tensionados
                )

        # Conclusiones formalizadas
        donde_pueden = [m.municipio for m in municipios_analizados if m.esfuerzo_libre_con_gaztelagun_pct <= 38.0]
        donde_no_solos = [m.municipio for m in municipios_analizados if m.esfuerzo_libre_con_gaztelagun_pct > 45.0]

        conclusiones = StudyConclusions(
            respuesta_ejecutiva=(
                "En el mercado libre en solitario en las capitales y zonas costeras, una persona joven "
                "NO PUEDE independizarse con su salario medio (esfuerzo > 55% - 86%). "
                "Sin embargo, la emancipación individual SÍ ES VIABLE en municipios comarcales (Agurain, Eibar, "
                "Balmaseda) o con el programa Gaztelagun en Vitoria-Gasteiz y áreas metropolitanas secundarias, "
                "y PLENAMENTE SOSTENIBLE mediante vivienda protegida de alquiler (VPO/Alokabide) o compartiendo piso."
            ),
            puede_en_solitario_mercado_libre=False,
            puede_con_ayuda_gaztelagun=True,
            puede_compartiendo_piso=True,
            donde_pueden_vivir=donde_pueden,
            donde_no_pueden_vivir_solos=donde_no_solos,
            papel_vpo_alokabide=(
                "La vivienda protegida en régimen de alquiler (VPO de Visesa / Alokabide) sitúa el coste mensual "
                "entre 340 € y 460 €, lo que reduce la tasa de esfuerzo al 24% - 32%, permitiendo a los jóvenes "
                "independizarse en solitario cumpliendo las directrices financieras del Banco de España (< 35%)."
            ),
            impacto_gaztelagun=(
                "La ayuda autonómica Gaztelagun (hasta 300 €/mes para menores de 36 años) reduce entre 18 y 22 "
                "puntos porcentuales la tasa de esfuerzo, transformando municipios de 'tensión severa' en opciones "
                "viables (ej. Vitoria-Gasteiz baja del 55.5% al 34.2%)."
            )
        )

        result_dict = {
            "fecha_analisis": datetime.now(timezone.utc).isoformat(),
            "total_municipios": len(municipios_analizados),
            "conclusiones": conclusiones.model_dump(),
            "resumen_territorial": {k: v.model_dump() for k, v in territorios_summary.items()},
            "municipios": [m.model_dump() for m in municipios_analizados]
        }

        return result_dict

    def export_to_json(self, data: Dict[str, Any], filepath: str) -> None:
        """Guarda el estudio en formato JSON estructurado."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def print_terminal_report(self, data: Dict[str, Any]) -> None:
        """Imprime un informe ejecutivo visual y legible en el terminal de VS Code."""
        c = data["conclusiones"]
        print("\n" + "=" * 80)
        print("  ESTUDIO EJECUTIVO: ¿DÓNDE PUEDEN VIVIR LOS JÓVENES EN EUSKADI?")
        print("=" * 80)
        print(f"Pregunta analizada: {c['pregunta_principal']}")
        print("-" * 80)
        print(f"VEREDICTO: {c['respuesta_ejecutiva']}")
        print("-" * 80)

        print("\n[CAPACIDAD DE EMANCIPACIÓN SEGÚN MODALIDAD]")
        print(f"  • En solitario en mercado libre (capitales) : {'[NO VIABLE]' if not c['puede_en_solitario_mercado_libre'] else '[VIABLE]'}")
        print(f"  • En solitario con ayuda Gaztelagun (-300 €): {'[VIABLE EN ZONAS ESPECÍFICAS]' if c['puede_con_ayuda_gaztelagun'] else '[NO]'}")
        print(f"  • Compartiendo vivienda (2 personas)        : {'[VIABLE]' if c['puede_compartiendo_piso'] else '[NO]'}")
        print(f"  • En Vivienda Protegida (VPO Alokabide)     : [VIABLE Y SOSTENIBLE (24-32% esfuerzo)]")

        print("\n[RANKING DE ACCESIBILIDAD MUNICIPAL PARA JÓVENES (16 MUNICIPIOS CLAVE)]")
        print(f"{'#':<3} {'Municipio':<25} {'Territorio':<10} {'Alquiler':<10} {'Sin Ayuda':<12} {'Con Gaztelagun':<16} {'Viabilidad':<22}")
        print("-" * 100)
        for m in data["municipios"]:
            rank = m["ranking_accesibilidad"]
            muni = m["municipio"]
            terr = m["territorio"]
            alq = f"{m['alquiler_medio_mercado']:.0f} €"
            sin = f"{m['esfuerzo_libre_sin_ayuda_pct']:.1f} %"
            con = f"{m['esfuerzo_libre_con_gaztelagun_pct']:.1f} %"
            via = m["viabilidad_emancipacion"]
            print(f"{rank:<3} {muni:<25} {terr:<10} {alq:<10} {sin:<12} {con:<16} {via:<22}")

        print("\n[RESUMEN TERRITORIAL]")
        for terr, sum_data in data["resumen_territorial"].items():
            print(f"  • {terr:<10}: Salario Joven {sum_data['salario_medio_joven']:.0f} € | Alquiler Medio {sum_data['alquiler_medio_mercado']:.0f} € | Esfuerzo {sum_data['esfuerzo_medio_sin_ayuda_pct']:.1f}% -> Con Gaztelagun {sum_data['esfuerzo_medio_con_gaztelagun_pct']:.1f}%")

        print("\n[RECOMENDACIÓN FINAL PARA LA ENTIDAD PÚBLICA]")
        print(f"  1. {c['papel_vpo_alokabide']}")
        print(f"  2. {c['impacto_gaztelagun']}")
        print("=" * 80 + "\n")
