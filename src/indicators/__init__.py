"""
Módulo de obtención de indicadores complementarios socioeconómicos y demográficos.
"""
from .models import MunicipalIndicatorValue, IndicatorsDataset
from .udalmap_client import UdalmapClient

__all__ = ["MunicipalIndicatorValue", "IndicatorsDataset", "UdalmapClient"]
