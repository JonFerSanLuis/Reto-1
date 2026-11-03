"""
Módulo de extracción de datos de vivienda (APIs públicas y web scraping).
"""
from .api_client import OpenDataEuskadiHousingClient
from .scraper import HabitacliaScraper
from .pisos_scraper import PisosComScraper
from .models import HousingAd, ExtractionResult

__all__ = [
    "OpenDataEuskadiHousingClient",
    "HabitacliaScraper",
    "PisosComScraper",
    "HousingAd",
    "ExtractionResult"
]
