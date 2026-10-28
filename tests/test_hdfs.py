"""
tests/test_hdfs.py - Pruebas para el cliente de Apache Hadoop HDFS.
"""

import os
import tempfile
import pytest
from src.hdfs.client import HDFSClient


def test_hdfs_upload_and_download_integrity():
    """Verifica que el almacenamiento y recuperación en HDFS conserva exactamente el checksum."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Usar un directorio de simulación temporal para aislar la prueba
        sim_dir = os.path.join(tmpdir, "hdfs_store")
        client = HDFSClient(simulation_mode=True, simulation_storage_dir=sim_dir)

        # Crear fichero de prueba original
        src_file = os.path.join(tmpdir, "original_data.json")
        sample_content = '{"fuente": "Test", "precio": 1200, "municipio": "Bilbao"}\n'
        with open(src_file, "w", encoding="utf-8") as f:
            f.write(sample_content)

        orig_sha = client.calculate_sha256(src_file)

        # Subir a HDFS
        hdfs_target = "/data/reto1/raw/vivienda/api/20261028/datos.json"
        res = client.upload_file(src_file, hdfs_target)

        assert res.exito is True
        assert res.checksum_sha256 == orig_sha
        assert client.exists(hdfs_target) is True

        # Listar directorio
        items = client.list_directory("/data/reto1/raw/vivienda/api/20261028")
        assert "datos.json" in items

        # Recuperar y verificar integridad
        downloaded_file = os.path.join(tmpdir, "recovered.json")
        client.download_file(hdfs_target, downloaded_file)

        assert os.path.exists(downloaded_file)
        recovered_sha = client.calculate_sha256(downloaded_file)
        assert recovered_sha == orig_sha


def test_hdfs_file_not_found():
    """Comprueba el manejo de errores al intentar recuperar un archivo inexistente."""
    with tempfile.TemporaryDirectory() as tmpdir:
        client = HDFSClient(simulation_mode=True, simulation_storage_dir=tmpdir)
        with pytest.raises(FileNotFoundError):
            client.download_file("/ruta/inexistente/archivo.json", os.path.join(tmpdir, "dest.json"))
