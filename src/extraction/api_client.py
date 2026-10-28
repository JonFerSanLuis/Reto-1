"""
src/extraction/api_client.py - Cliente API para datos oficiales de vivienda en Euskadi.

Consulta las promociones y viviendas protegidas del Gobierno Vasco a través de
Open Data Euskadi y el servicio público de Visesa (Departamento de Vivienda).
"""

import json
import csv
import os
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from .models import HousingAd, ExtractionResult


class OpenDataEuskadiHousingClient:
    """Cliente para la obtención de datos de vivienda pública de Euskadi vía API REST."""

    DEFAULT_API_URL = "https://apps.visesa.eus/ws/promocion/filtro"
    DEFAULT_CSV_FALLBACK_URL = (
        "https://opendata.euskadi.eus/contenidos/ds_localizaciones/"
        "promociones_etxebide/opendata/promociones.csv"
    )

    def __init__(self, api_url: Optional[str] = None, timeout_seconds: int = 15):
        self.api_url = api_url or self.DEFAULT_API_URL
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AntigravityAcademicResearch/1.0 (Euskadi Youth Housing Project; Python requests)",
            "Accept": "application/json"
        })

    def fetch_promotions(self) -> ExtractionResult:
        """
        Consulta el endpoint REST de promociones de vivienda protegida de Euskadi.
        Retorna un ExtractionResult con objetos HousingAd validados.
        """
        errores: List[str] = []
        ads: List[HousingAd] = []

        try:
            response = self.session.get(self.api_url, timeout=self.timeout_seconds)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            msg = f"Error en la petición HTTP a {self.api_url}: {e}"
            errores.append(msg)
            # Intento de fallback al CSV de Open Data Euskadi si la API falla
            return self._fetch_csv_fallback(errores)
        except json.JSONDecodeError as e:
            msg = f"Error al decodificar la respuesta JSON de {self.api_url}: {e}"
            errores.append(msg)
            return ExtractionResult(fuente="OpenDataEuskadi_Visesa", total_registros=0, items=[], errores=errores)

        rows = data.get("rows", [])
        for row in rows:
            try:
                ad = self._parse_api_row(row)
                if ad:
                    ads.append(ad)
            except Exception as ex:
                errores.append(f"Error parseando registro {row.get('idContenido')}: {ex}")

        return ExtractionResult(
            fuente="OpenDataEuskadi_Visesa",
            total_registros=len(ads),
            items=ads,
            errores=errores
        )

    def _parse_api_row(self, row: Dict[str, Any]) -> Optional[HousingAd]:
        """Transforma una fila del WS de Visesa en un objeto HousingAd estandarizado."""
        id_contenido = str(row.get("idContenido") or row.get("codigoInterno") or "")
        if not id_contenido:
            return None

        poblacion = row.get("poblacion") or "Euskadi"
        # Determinar régimen
        tipo_venta = row.get("idTipoVenta")
        fecha_prevista = str(row.get("fechaPrevista") or "").lower()
        if tipo_venta == 7 or "alokairu" in fecha_prevista or "alquiler" in fecha_prevista:
            tipo_operacion = "alquiler"
        elif "compra" in fecha_prevista or "cv" in fecha_prevista:
            tipo_operacion = "compraventa"
        else:
            tipo_operacion = "vpo"

        # Precios
        precio = None
        if row.get("precioMinimo"):
            try:
                precio = float(row["precioMinimo"])
            except (ValueError, TypeError):
                pass
        elif row.get("rentaMinima"):
            try:
                precio = float(row["rentaMinima"])
            except (ValueError, TypeError):
                pass
        elif row.get("precioCompra"):
            try:
                precio = float(row["precioCompra"])
            except (ValueError, TypeError):
                pass
        elif row.get("precioAlquiler"):
            try:
                precio = float(row["precioAlquiler"])
            except (ValueError, TypeError):
                pass

        superficie = None
        if row.get("superficie"):
            try:
                superficie = float(row["superficie"])
            except (ValueError, TypeError):
                pass

        habitaciones = None
        if row.get("numeroDormitorios"):
            try:
                habitaciones = int(row["numeroDormitorios"])
            except (ValueError, TypeError):
                pass
        elif row.get("numeroDormitoriosMinimo"):
            try:
                habitaciones = int(row["numeroDormitoriosMinimo"])
            except (ValueError, TypeError):
                pass

        # Construir URL pública
        url_detalle = f"https://www.visesa.euskadi.eus/webvis01-promocionesdetalle/es/?id={id_contenido}"

        return HousingAd(
            id=f"visesa_{id_contenido}",
            fuente="OpenDataEuskadi_Visesa",
            tipo_operacion=tipo_operacion,
            municipio=poblacion.strip(),
            direccion=row.get("direccion") or row.get("direccionPromocion"),
            precio=precio,
            superficie_m2=superficie,
            habitaciones=habitaciones,
            banos=None,
            titulo=row.get("titulo"),
            descripcion=row.get("texto"),
            url=url_detalle,
            fecha_extraccion=datetime.now(timezone.utc).isoformat(),
            es_sintetico=False
        )

    def _fetch_csv_fallback(self, prev_errors: List[str]) -> ExtractionResult:
        """Descarga el catálogo de promociones de Etxebide en CSV como respaldo oficial."""
        errores = list(prev_errors)
        ads: List[HousingAd] = []
        try:
            resp = self.session.get(self.DEFAULT_CSV_FALLBACK_URL, timeout=self.timeout_seconds)
            resp.raise_for_status()
            text = resp.content.decode("latin1", errors="replace")
            reader = csv.DictReader(text.splitlines(), delimiter=";")
            for row in reader:
                id_prom = row.get("ID_PROM")
                if not id_prom:
                    continue
                reg = (row.get("Reg Acceso") or "").lower()
                op = "alquiler" if "alquiler" in reg else ("compraventa" if "compra" in reg else "vpo")
                muni = row.get("Municipio") or "Euskadi"
                prov = row.get("Territorio")
                ubic = row.get("Ubicacion")

                ads.append(HousingAd(
                    id=f"etxebide_{id_prom}",
                    fuente="OpenDataEuskadi_Etxebide_CSV",
                    tipo_operacion=op,
                    municipio=muni.strip(),
                    provincia=prov,
                    direccion=ubic,
                    precio=None,  # No disponible en este CSV, no se inventa
                    superficie_m2=None,
                    habitaciones=None,
                    titulo=f"Promoción Etxebide {id_prom} - {row.get('Expediente', '')}",
                    descripcion=f"Promotor: {row.get('Promotor', '')}. Tipología: {row.get('Tipologia', '')}",
                    url=self.DEFAULT_CSV_FALLBACK_URL,
                    fecha_extraccion=datetime.now(timezone.utc).isoformat(),
                    es_sintetico=False
                ))
        except Exception as e:
            errores.append(f"Error en descarga CSV fallback: {e}")

        return ExtractionResult(
            fuente="OpenDataEuskadi_CSV_Fallback",
            total_registros=len(ads),
            items=ads,
            errores=errores
        )

    def save_to_json(self, result: ExtractionResult, filepath: str) -> None:
        """Guarda los resultados originales de la extracción en formato JSON."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)

    def save_to_csv(self, result: ExtractionResult, filepath: str) -> None:
        """Guarda los resultados originales de la extracción en formato CSV."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        if not result.items:
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                f.write("id,fuente,tipo_operacion,municipio,precio,superficie_m2,habitaciones,fecha_extraccion\n")
            return

        fieldnames = list(result.items[0].model_dump().keys())
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in result.items:
                writer.writerow(item.model_dump())
