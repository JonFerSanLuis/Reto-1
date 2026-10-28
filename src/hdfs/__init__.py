"""
Módulo de almacenamiento y recuperación de ficheros originales en HDFS (Apache Hadoop).
"""
from .client import HDFSClient, HDFSUploadResult

__all__ = ["HDFSClient", "HDFSUploadResult"]
