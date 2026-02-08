"""
Multi-Source Radar Downloaders

Unified interface for downloading radar data from:
- US NEXRAD (AWS S3)
- Canadian Environment Canada
- Mexican CONAGUA
"""

from .nexrad import NEXRADDownloader
from .canada import CanadaRadarDownloader
from .mexico import MexicoRadarDownloader
from .unified import UnifiedRadarDownloader

__all__ = [
    'NEXRADDownloader',
    'CanadaRadarDownloader',
    'MexicoRadarDownloader',
    'UnifiedRadarDownloader',
]
