"""
src/indicators/models.py - Modelos de datos para indicadores socioeconómicos municipales.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class MunicipalIndicatorValue(BaseModel):
    """Serie temporal y valor más reciente de un indicador para un municipio."""
    municipio_id: str = Field(..., description="Código municipal INE/Eustat")
    municipio_nombre: str = Field(..., description="Nombre oficial del municipio")
    indicador_id: str = Field(..., description="Identificador numérico en Udalmap")
    indicador_nombre: str = Field(..., description="Nombre del indicador")
    unidad: str = Field(..., description="Unidad de medida (ej. '€', 'Habitantes', '%')")
    valores_por_ano: Dict[str, float] = Field(default_factory=dict, description="Evolución temporal {año: valor}")
    ultimo_ano: Optional[str] = Field(None, description="Último año registrado en la serie")
    ultimo_valor: Optional[float] = Field(None, description="Valor más reciente registrado")


class IndicatorMetadata(BaseModel):
    """Metadatos de procedencia, periodo y comparabilidad del indicador."""
    id: str
    nombre: str
    unidad: str
    fuente: str = "Eustat / Open Data Euskadi (Udalmap)"
    periodo_referencia: str
    ambito_geografico: str = "Comunidad Autónoma de Euskadi (Municipal)"
    descripcion_metodologica: str
    limitaciones: str


class IndicatorsDataset(BaseModel):
    """Conjunto consolidado de indicadores complementarios para el estudio de vivienda juvenil."""
    fuente: str = "OpenDataEuskadi_Udalmap_Eustat"
    fecha_obtencion: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ambito_geografico: str = "Comunidad Autónoma del País Vasco (251 municipios)"
    metadatos: Dict[str, IndicatorMetadata] = Field(default_factory=dict)
    registros: List[MunicipalIndicatorValue] = Field(default_factory=list)
    errores: List[str] = Field(default_factory=list)
