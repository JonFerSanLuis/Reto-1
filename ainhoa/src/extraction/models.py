"""
src/extraction/models.py - Modelos de datos para anuncios y promociones de vivienda.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class HousingAd(BaseModel):
    """
    Modelo unificado para un anuncio o promoción inmobiliaria en Euskadi.
    Conserva los campos reales obtenidos sin inventar valores ausentes.
    """
    id: str = Field(..., description="Identificador único del anuncio o promoción")
    fuente: str = Field(..., description="Nombre de la fuente (p. ej. 'OpenDataEuskadi_Visesa', 'Habitaclia_Scraping')")
    tipo_operacion: str = Field(..., description="Tipo de régimen: 'alquiler', 'compraventa', 'aroc' o 'vpo'")
    municipio: str = Field(..., description="Municipio de Euskadi")
    provincia: Optional[str] = Field(None, description="Territorio histórico (Bizkaia, Gipuzkoa, Araba)")
    barrio: Optional[str] = Field(None, description="Barrio o zona del municipio")
    direccion: Optional[str] = Field(None, description="Dirección o ubicación pública de la vivienda")
    precio: Optional[float] = Field(None, description="Precio en euros (€/mes en alquiler o € total en compra)")
    superficie_m2: Optional[float] = Field(None, description="Superficie útil o construida en m²")
    habitaciones: Optional[int] = Field(None, description="Número de dormitorios")
    banos: Optional[int] = Field(None, description="Número de baños")
    titulo: Optional[str] = Field(None, description="Título del anuncio o nombre de la promoción")
    descripcion: Optional[str] = Field(None, description="Descripción original del anuncio")
    url: Optional[str] = Field(None, description="Enlace público al anuncio o expediente")
    fecha_extraccion: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Fecha y hora de obtención en formato ISO 8601"
    )
    es_sintetico: bool = Field(False, description="Flag que identifica si el dato es real o de prueba")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ExtractionResult(BaseModel):
    """Contenedor de resultados de una operación de extracción."""
    fuente: str
    total_registros: int
    fecha_ejecucion: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    items: List[HousingAd]
    errores: List[str] = Field(default_factory=list)
