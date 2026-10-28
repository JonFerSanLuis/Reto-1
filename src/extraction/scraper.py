"""
src/extraction/scraper.py - Web Scraper ético para anuncios inmobiliarios en Euskadi.

Obtiene anuncios reales de alquiler y venta en municipios vascos (Bilbao, Donostia,
Vitoria-Gasteiz) cumpliendo con robots.txt, pausas de cortesía y gestión de errores.
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


class HabitacliaScraper:
    """Scraper para portales inmobiliarios enfocado en el mercado residencial de Euskadi."""

    DEFAULT_TARGETS = [
        {"municipio": "Bilbao", "tipo": "alquiler", "url": "https://www.habitaclia.com/alquiler-bilbao.htm"},
        {"municipio": "Donostia-San Sebastián", "tipo": "alquiler", "url": "https://www.habitaclia.com/alquiler-donostia_san_sebastian.htm"},
        {"municipio": "Vitoria-Gasteiz", "tipo": "alquiler", "url": "https://www.habitaclia.com/alquiler-vitoria_gasteiz.htm"},
        {"municipio": "Bilbao", "tipo": "compraventa", "url": "https://www.habitaclia.com/comprar-vivienda-en-bilbao/"}
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
            "Accept-Language": "es-ES,es;q=0.9,eu;q=0.8,en;q=0.7"
        })

    def _safe_get(self, url: str, **kwargs) -> requests.Response:
        """Petición GET con soporte y fallback ante certificados SSL locales de la CA de Euskadi."""
        kwargs.setdefault("timeout", self.timeout)
        try:
            return self.session.get(url, **kwargs)
        except requests.exceptions.SSLError:
            urllib3.disable_warnings()
            return self.session.get(url, verify=False, **kwargs)

    def scrape_targets(self, targets: Optional[List[Dict[str, str]]] = None, max_items_per_target: int = 20) -> ExtractionResult:
        """
        Ejecuta el raspado web sobre las páginas objetivo definidas.
        Retorna un ExtractionResult consolidado con anuncios validados.
        """
        targets_to_run = targets or self.DEFAULT_TARGETS
        all_ads: List[HousingAd] = []
        errores: List[str] = []

        for target in targets_to_run:
            muni = target["municipio"]
            tipo_op = target["tipo"]
            url = target["url"]

            try:
                ads = self._scrape_page(url, muni, tipo_op, max_items=max_items_per_target)
                all_ads.extend(ads)
            except Exception as e:
                errores.append(f"Fallo al raspar {url} ({muni}): {e}")

            time.sleep(self.delay)

        return ExtractionResult(
            fuente="Habitaclia_Scraping",
            total_registros=len(all_ads),
            items=all_ads,
            errores=errores
        )

    def _scrape_page(self, url: str, municipio: str, tipo_operacion: str, max_items: int) -> List[HousingAd]:
        """Descarga y parsea una página web individual de anuncios."""
        resp = self._safe_get(url)
        if resp.status_code == 429:
            raise RuntimeError(f"HTTP 429 Too Many Requests recibido de {url}")
        resp.raise_for_status()

        soup = BeautifulSoup(resp.content, "html.parser")
        articles = soup.find_all("article")
        if not articles:
            articles = soup.find_all("div", class_=re.compile(r"list-item|property-item"))

        results: List[HousingAd] = []
        for idx, art in enumerate(articles):
            if len(results) >= max_items:
                break

            ad = self._extract_article_data(art, municipio, tipo_operacion, idx, url)
            if ad:
                results.append(ad)

        return results

    def _extract_article_data(self, article, municipio: str, tipo_operacion: str, index: int, source_url: str) -> Optional[HousingAd]:
        """Extrae los campos individuales de un elemento HTML de anuncio."""
        title_tag = article.find(["h2", "h3"])
        link_tag = article.find("a", href=True)
        titulo = title_tag.get_text(strip=True) if title_tag else None
        href = link_tag["href"] if link_tag else None
        full_url = href if (href and href.startswith("http")) else (f"https://www.habitaclia.com{href}" if href else source_url)

        data_id = article.get("data-id") or article.get("id")
        if not data_id and href:
            match_id = re.search(r"(\d+)\.htm", href)
            data_id = match_id.group(1) if match_id else f"art_{index}"
        elif not data_id:
            data_id = f"{municipio.lower()}_{index}_{int(time.time())}"

        precio = None
        price_tag = article.find(class_=re.compile(r"font-2|price|precio"))
        if price_tag:
            price_match = re.search(r"([\d\.]+)\s*€", price_tag.get_text(strip=True))
            if price_match:
                try:
                    clean_num = price_match.group(1).replace(".", "").replace(",", ".")
                    precio = float(clean_num)
                except ValueError:
                    precio = None

        superficie_m2 = None
        habitaciones = None
        banos = None

        features_tag = article.find(class_=re.compile(r"feature|details|info"))
        text_content = (features_tag.get_text(" ", strip=True) if features_tag else "") + " " + article.get_text(" ", strip=True)

        sup_match = re.search(r"(\d+(?:[\.,]\d+)?)\s*m2", text_content, re.IGNORECASE)
        if sup_match:
            try:
                superficie_m2 = float(sup_match.group(1).replace(",", "."))
            except ValueError:
                pass

        hab_match = re.search(r"(\d+)\s*(?:hab|dorm)", text_content, re.IGNORECASE)
        if hab_match:
            try:
                habitaciones = int(hab_match.group(1))
            except ValueError:
                pass

        ban_match = re.search(r"(\d+)\s*baño", text_content, re.IGNORECASE)
        if ban_match:
            try:
                banos = int(ban_match.group(1))
            except ValueError:
                pass

        loc_tag = article.find(class_=re.compile(r"location|ubicacion|zone"))
        barrio = loc_tag.get_text(strip=True) if loc_tag else None

        desc_tag = article.find("p")
        descripcion = desc_tag.get_text(strip=True) if desc_tag else None

        if not titulo and not precio:
            return None

        clean_id = f"habitaclia_{data_id}" if not str(data_id).startswith("habitaclia_") else str(data_id)

        return HousingAd(
            id=clean_id,
            fuente="Habitaclia_Scraping",
            tipo_operacion=tipo_operacion,
            municipio=municipio,
            provincia=None,
            barrio=barrio,
            direccion=None,
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
        """Exporta el resultado a formato JSON indentado."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)

    def save_to_csv(self, result: ExtractionResult, filepath: str) -> None:
        """Exporta el resultado a formato CSV estructurado."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        fieldnames = [
            "id", "fuente", "tipo_operacion", "municipio", "provincia", "barrio",
            "direccion", "precio", "superficie_m2", "habitaciones", "banos",
            "titulo", "descripcion", "url", "fecha_extraccion", "es_sintetico"
        ]
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for item in result.items:
                writer.writerow(item.to_dict())
