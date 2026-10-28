"""
Módulo de obtención de indicadores complementarios socioeconómicos y demográficos.
"""
from .models import MunicipalIndicatorValue, IndicatorsDataset, IndicatorMetadata
from .udalmap_client import UdalmapClient
from .ovj_client import OVJYouthEmancipationClient, YouthEmancipationData, YouthHousingEffortReport

__all__ = [
    "MunicipalIndicatorValue",
    "IndicatorsDataset",
    "IndicatorMetadata",
    "UdalmapClient",
    "OVJYouthEmancipationClient",
    "YouthEmancipationData",
    "YouthHousingEffortReport"
]
