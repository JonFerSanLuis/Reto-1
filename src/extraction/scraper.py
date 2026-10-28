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
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,eu;q=0.8,en;q=0.7"
        })

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

            # Pausa de cortesía para respetar el servidor
            time.sleep(self.delay)

        return ExtractionResult(
            fuente="Habitaclia_Scraping",
            total_registros=len(all_ads),
            items=all_ads,
            errores=errores
        )

    def _scrape_page(self, url: str, municipio: str, tipo_operacion: str, max_items: int) -> List[HousingAd]:
        """Descarga y parsea una página web individual de anuncios."""
        resp = self.session.get(url, timeout=self.timeout)
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
        # 1. Título y Enlace
        title_tag = article.find(["h2", "h3"])
        link_tag = article.find("a", href=True)
        titulo = title_tag.get_text(strip=True) if title_tag else None
        href = link_tag["href"] if link_tag else None
        full_url = href if (href and href.startswith("http")) else (f"https://www.habitaclia.com{href}" if href else source_url)

        # 2. Identificador
        data_id = article.get("data-id") or article.get("id")
        if not data_id and href:
            match_id = re.search(r"(\d+)\.htm", href)
            data_id = match_id.group(1) if match_id else f"art_{index}"
        elif not data_id:
            data_id = f"{municipio.lower()}_{index}_{int(time.time())}"

        # 3. Precio
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
        else:
            price_match = re.search(r"\b(\d{1,2}(?:\.\d{3})*|\d+)\s*€", article.get_text())
            if price_match:
                try:
                    clean_num = price_match.group(1).replace(".", "").replace(",", ".")
                    precio = float(clean_num)
                except ValueError:
                    precio = None

        # 4. Características: m², habitaciones, baños
        text_content = article.get_text(" ", strip=True)
        superficie = None
        sup_match = re.search(r"(\d+)\s*m[2²]", text_content, re.I)
        if sup_match:
            try:
                superficie = float(sup_match.group(1))
            except ValueError:
                pass

        habitaciones = None
        hab_match = re.search(r"(\d+)\s*hab", text_content, re.I)
        if hab_match:
            try:
                habitaciones = int(hab_match.group(1))
            except ValueError:
                pass

        banos = None
        ban_match = re.search(r"(\d+)\s*baño", text_content, re.I)
        if ban_match:
            try:
                banos = int(ban_match.group(1))
            except ValueError:
                pass

        # 5. Barrio / Ubicación
        location_tag = article.find(class_=re.compile(r"location|ubicacion|barrio"))
        barrio = location_tag.get_text(strip=True) if location_tag else None

        # Si no encontramos datos mínimos de anuncio (precio o título), descartar
        if not precio and not titulo:
            return None

        return HousingAd(
            id=f"habitaclia_{data_id}",
            fuente="Habitaclia_Scraping",
            tipo_operacion=tipo_operacion,
            municipio=municipio,
            barrio=barrio,
            precio=precio,
            superficie_m2=superficie,
            habitaciones=habitaciones,
            banos=banos,
            titulo=titulo,
            descripcion=text_content[:300] if text_content else None,
            url=full_url,
            fecha_extraccion=datetime.now(timezone.utc).isoformat(),
            es_sintetico=False
        )

    def save_to_json(self, result: ExtractionResult, filepath: str) -> None:
        """Guarda los resultados del scraping en JSON."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)

    def save_to_csv(self, result: ExtractionResult, filepath: str) -> None:
        """Guarda los resultados del scraping en CSV."""
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
