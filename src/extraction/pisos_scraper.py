"""
src/extraction/pisos_scraper.py - Web Scraper para anuncios de Pisos.com en Euskadi.

Obtiene anuncios inmobiliarios de alquiler y compraventa en los tres territorios
históricos de Euskadi (Bizkaia, Gipuzkoa y Araba), normalizando los datos en
el modelo estándar HousingAd con control ético de ritmo y pausas de cortesía.
"""

import time
import re
import json
import csv
import os
import requests
import urllib3
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from .models import HousingAd, ExtractionResult


class PisosComScraper:
    """Scraper especializado en el portal Pisos.com para el mercado vasco."""

    DEFAULT_TARGETS = [
        {
            "municipio": "Bilbao",
            "provincia": "Bizkaia",
            "tipo": "alquiler",
            "url": "https://www.pisos.com/alquiler/viviendas-bilbao/"
        },
        {
            "municipio": "Donostia-San Sebastián",
            "provincia": "Gipuzkoa",
            "tipo": "alquiler",
            "url": "https://www.pisos.com/alquiler/viviendas-donostia_san_sebastian/"
        },
        {
            "municipio": "Vitoria-Gasteiz",
            "provincia": "Araba",
            "tipo": "alquiler",
            "url": "https://www.pisos.com/alquiler/viviendas-vitoria_gasteiz/"
        },
        {
            "municipio": "Bilbao",
            "provincia": "Bizkaia",
            "tipo": "compraventa",
            "url": "https://www.pisos.com/venta/pisos-bilbao/"
        }
    ]

    def __init__(self, request_delay_seconds: float = 1.5, timeout_seconds: int = 12):
        self.delay = request_delay_seconds
        self.timeout = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,eu;q=0.8,en;q=0.7",
            "Referer": "https://www.pisos.com/"
        })

    def _safe_get(self, url: str, **kwargs) -> requests.Response:
        """Petición GET con soporte y fallback ante certificados SSL locales de la CA de Euskadi."""
        kwargs.setdefault("timeout", self.timeout)
        try:
            return self.session.get(url, **kwargs)
        except requests.exceptions.SSLError:
            urllib3.disable_warnings()
            return self.session.get(url, verify=False, **kwargs)

    def scrape_targets(
        self,
        targets: Optional[List[Dict[str, str]]] = None,
        max_items_per_target: int = 20
    ) -> ExtractionResult:
        """
        Ejecuta el raspado web de los objetivos configurados.
        Retorna un ExtractionResult unificado con anuncios parseados y validados.
        """
        targets_to_run = targets or self.DEFAULT_TARGETS
        all_ads: List[HousingAd] = []
        errores: List[str] = []

        for target in targets_to_run:
            muni = target.get("municipio", "Euskadi")
            prov = target.get("provincia")
            tipo_op = target.get("tipo", "alquiler")
            url = target["url"]

            try:
                ads = self._scrape_page(url, muni, prov, tipo_op, max_items=max_items_per_target)
                all_ads.extend(ads)
            except Exception as e:
                errores.append(f"Fallo al raspar {url} ({muni}): {e}")

            time.sleep(self.delay)

        return ExtractionResult(
            fuente="PisosCom_Scraping",
            total_registros=len(all_ads),
            items=all_ads,
            errores=errores
        )

    def _scrape_page(
        self,
        url: str,
        municipio: str,
        provincia: Optional[str],
        tipo_operacion: str,
        max_items: int
    ) -> List[HousingAd]:
        """Descarga y procesa una página HTML de Pisos.com."""
        resp = self._safe_get(url)
        if resp.status_code == 429:
            raise RuntimeError(f"HTTP 429 Too Many Requests recibido de {url}")
        resp.raise_for_status()

        soup = BeautifulSoup(resp.content, "html.parser")

        cards = soup.find_all(class_=re.compile(r"ad-preview|row\s+clearfix|grid__item"))
        if not cards:
            cards = soup.find_all("article")

        results: List[HousingAd] = []
        for idx, card in enumerate(cards):
            if len(results) >= max_items:
                break

            ad = self._extract_card_data(card, municipio, provincia, tipo_operacion, idx, url)
            if ad:
                results.append(ad)

        return results

    def _extract_card_data(
        self,
        card,
        municipio: str,
        provincia: Optional[str],
        tipo_operacion: str,
        index: int,
        source_url: str
    ) -> Optional[HousingAd]:
        """Extrae los atributos estructurados desde un elemento HTML de anuncio."""
        title_tag = card.find(class_=re.compile(r"ad-preview__title|title")) or card.find(["h2", "h3"])
        link_tag = card.find("a", href=True)
        titulo = title_tag.get_text(strip=True) if title_tag else None
        href = link_tag["href"] if link_tag else None

        if href and not href.startswith("http"):
            full_url = f"https://www.pisos.com{href}"
        else:
            full_url = href or source_url

        data_id = (
            card.get("data-ad-id") or
            card.get("data-id") or
            card.get("id")
        )
        if not data_id and href:
            match_id = re.search(r"(\d+)(?:_[a-z0-9]+)?\.html?", href)
            data_id = f"pisos_{match_id.group(1)}" if match_id else None

        if not data_id:
            data_id = f"pisos_{municipio.lower()}_{index}_{int(time.time())}"
        elif not str(data_id).startswith("pisos_"):
            data_id = f"pisos_{data_id}"

        precio = None
        price_tag = card.find(class_=re.compile(r"ad-preview__price|price|p-price"))
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            match_price = re.search(r"([\d\.]+)\s*€", price_text)
            if match_price:
                try:
                    num_clean = match_price.group(1).replace(".", "").replace(",", ".")
                    precio = float(num_clean)
                except ValueError:
                    precio = None

        card_text = card.get_text(" ", strip=True)

        superficie_m2 = None
        sup_match = re.search(r"(\d+(?:[\.,]\d+)?)\s*m²?", card_text, re.IGNORECASE)
        if sup_match:
            try:
                superficie_m2 = float(sup_match.group(1).replace(",", "."))
            except ValueError:
                superficie_m2 = None

        habitaciones = None
        hab_match = re.search(r"(\d+)\s*(?:habs?|hab\b|dorm\b|habitaciones)", card_text, re.IGNORECASE)
        if hab_match:
            try:
                habitaciones = int(hab_match.group(1))
            except ValueError:
                habitaciones = None

        banos = None
        banos_match = re.search(r"(\d+)\s*(?:baños?|bñ)", card_text, re.IGNORECASE)
        if banos_match:
            try:
                banos = int(banos_match.group(1))
            except ValueError:
                banos = None

        barrio_tag = card.find(class_=re.compile(r"location|zone|ad-preview__location"))
        barrio = barrio_tag.get_text(strip=True) if barrio_tag else None

        desc_tag = card.find(class_=re.compile(r"description|desc"))
        descripcion = desc_tag.get_text(strip=True) if desc_tag else None

        if not titulo and not precio:
            return None

        return HousingAd(
            id=str(data_id),
            fuente="PisosCom_Scraping",
            tipo_operacion=tipo_operacion,
            municipio=municipio,
            provincia=provincia,
            barrio=barrio,
            precio=precio,
            superficie_m2=superficie_m2,
            habitaciones=habitaciones,
            banos=banos,
            titulo=titulo,
            descripcion=descripcion,
            url=full_url,
            fecha_extraccion=datetime.now(timezone.utc).isoformat(),
            es_sintetico=False
        )

    def save_to_json(self, result: ExtractionResult, filepath: str) -> None:
        """Exporta el resultado consolidado a un archivo JSON con formato legible."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)

    def save_to_csv(self, result: ExtractionResult, filepath: str) -> None:
        """Exporta los anuncios planos a un fichero tabular CSV normalizado."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        fieldnames = [
            "id", "fuente", "tipo_operacion", "municipio", "provincia", "barrio",
            "precio", "superficie_m2", "habitaciones", "banos", "titulo",
            "url", "fecha_extraccion"
        ]
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for ad in result.items:
                writer.writerow(ad.to_dict())
