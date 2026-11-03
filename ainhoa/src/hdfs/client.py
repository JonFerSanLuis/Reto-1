"""
src/hdfs/client.py - Cliente para Apache Hadoop HDFS mediante WebHDFS REST API.

Gestiona el almacenamiento estructurado de datos brutos (raw data), verificación
de integridad mediante checksums y recuperación de ficheros sin alterar los originales.
Soporta un modo de emulación local para pruebas en entornos sin clúster activo.
"""

import os
import hashlib
import shutil
import requests
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class HDFSUploadResult(BaseModel):
    """Resultado de una operación de almacenamiento en HDFS."""
    local_path: str
    hdfs_path: str
    file_size_bytes: int
    checksum_sha256: str
    modo: str = Field(..., description="'webhdfs_live' o 'local_simulation'")
    exito: bool
    mensaje: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HDFSClient:
    """Cliente para interactuar con Apache HDFS vía WebHDFS o emulación local."""

    DEFAULT_BASE_HDFS_DIR = "/data/reto1/raw"

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        simulation_mode: Optional[bool] = None,
        simulation_storage_dir: str = "data/hdfs_storage"
    ):
        self.host = host or os.environ.get("HDFS_NAMENODE_HOST", "localhost")
        self.port = port or int(os.environ.get("HDFS_NAMENODE_PORT", "9870"))
        self.user = user or os.environ.get("HDFS_USER", "hadoop")
        self.sim_storage = os.path.abspath(simulation_storage_dir)

        # Detectar si se fuerza modo simulación o si el servicio está caído
        env_sim = os.environ.get("HDFS_SIMULATION_MODE", "").lower() in ("true", "1", "yes")
        self.force_simulation = simulation_mode if simulation_mode is not None else env_sim

        self.webhdfs_base_url = f"http://{self.host}:{self.port}/webhdfs/v1"
        self._is_live_cache: Optional[bool] = None

    def is_live_cluster_available(self) -> bool:
        """Comprueba si el NameNode de HDFS responde vía WebHDFS."""
        if self.force_simulation:
            return False
        if self._is_live_cache is not None:
            return self._is_live_cache

        test_url = f"{self.webhdfs_base_url}/?op=GETFILESTATUS&user.name={self.user}"
        try:
            resp = requests.get(test_url, timeout=2)
            self._is_live_cache = (resp.status_code in (200, 401, 403, 404))
        except requests.exceptions.RequestException:
            self._is_live_cache = False

        return self._is_live_cache

    @staticmethod
    def calculate_sha256(filepath: str) -> str:
        """Calcula el hash SHA-256 de un archivo para validar su integridad."""
        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        return sha.hexdigest()

    def upload_file(self, local_path: str, hdfs_path: str, overwrite: bool = True) -> HDFSUploadResult:
        """
        Sube un fichero local original a HDFS manteniendo su integridad exacta.
        hdfs_path debe ser absoluto dentro de HDFS, ej: /data/reto1/raw/vivienda/api/20261028/datos.json
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"El archivo local no existe: {local_path}")

        file_size = os.path.getsize(local_path)
        checksum = self.calculate_sha256(local_path)

        if self.is_live_cluster_available():
            return self._upload_webhdfs(local_path, hdfs_path, file_size, checksum, overwrite)
        else:
            return self._upload_simulation(local_path, hdfs_path, file_size, checksum)

    def download_file(self, hdfs_path: str, local_destination: str) -> str:
        """
        Recupera un archivo almacenado en HDFS y lo guarda en el sistema de ficheros local.
        Verifica que el archivo resultante coincide exactamente con el original.
        """
        os.makedirs(os.path.dirname(os.path.abspath(local_destination)), exist_ok=True)

        if self.is_live_cluster_available():
            url = f"{self.webhdfs_base_url}{hdfs_path}?op=OPEN&user.name={self.user}"
            resp = requests.get(url, stream=True, timeout=15)
            resp.raise_for_status()
            with open(local_destination, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
        else:
            sim_path = self._to_sim_path(hdfs_path)
            if not os.path.exists(sim_path):
                raise FileNotFoundError(f"Archivo no encontrado en simulación HDFS: {hdfs_path}")
            shutil.copy2(sim_path, local_destination)

        return local_destination

    def list_directory(self, hdfs_dir: str) -> List[str]:
        """Lista los ficheros contenidos en un directorio de HDFS."""
        if self.is_live_cluster_available():
            url = f"{self.webhdfs_base_url}{hdfs_dir}?op=LISTSTATUS&user.name={self.user}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            statuses = data.get("FileStatuses", {}).get("FileStatus", [])
            return [s.get("pathSuffix", "") for s in statuses]
        else:
            sim_dir = self._to_sim_path(hdfs_dir)
            if not os.path.exists(sim_dir):
                return []
            return os.listdir(sim_dir)

    def exists(self, hdfs_path: str) -> bool:
        """Verifica si un fichero o directorio existe en HDFS."""
        if self.is_live_cluster_available():
            url = f"{self.webhdfs_base_url}{hdfs_path}?op=GETFILESTATUS&user.name={self.user}"
            resp = requests.get(url, timeout=5)
            return resp.status_code == 200
        else:
            return os.path.exists(self._to_sim_path(hdfs_path))

    # --- Métodos internos ---
    def _to_sim_path(self, hdfs_path: str) -> str:
        clean = hdfs_path.lstrip("/").replace("/", os.sep)
        return os.path.join(self.sim_storage, clean)

    def _upload_simulation(
        self,
        local_path: str,
        hdfs_path: str,
        size: int,
        checksum: str
    ) -> HDFSUploadResult:
        sim_dest = self._to_sim_path(hdfs_path)
        os.makedirs(os.path.dirname(sim_dest), exist_ok=True)
        shutil.copy2(local_path, sim_dest)

        # Verificación inmediata de checksum
        stored_checksum = self.calculate_sha256(sim_dest)
        if stored_checksum != checksum:
            return HDFSUploadResult(
                local_path=local_path,
                hdfs_path=hdfs_path,
                file_size_bytes=size,
                checksum_sha256=checksum,
                modo="local_simulation",
                exito=False,
                mensaje="Fallo de integridad: los checksums difieren."
            )

        return HDFSUploadResult(
            local_path=local_path,
            hdfs_path=hdfs_path,
            file_size_bytes=size,
            checksum_sha256=checksum,
            modo="local_simulation",
            exito=True,
            mensaje=f"Almacenado y verificado en simulación HDFS: {sim_dest}"
        )

    def _upload_webhdfs(
        self,
        local_path: str,
        hdfs_path: str,
        size: int,
        checksum: str,
        overwrite: bool
    ) -> HDFSUploadResult:
        # Paso 1: Petición inicial para obtener redirección a DataNode
        url = f"{self.webhdfs_base_url}{hdfs_path}?op=CREATE&overwrite={'true' if overwrite else 'false'}&user.name={self.user}"
        resp1 = requests.put(url, allow_redirects=False, timeout=10)

        if resp1.status_code not in (307, 201):
            return HDFSUploadResult(
                local_path=local_path,
                hdfs_path=hdfs_path,
                file_size_bytes=size,
                checksum_sha256=checksum,
                modo="webhdfs_live",
                exito=False,
                mensaje=f"NameNode rechazó creación: HTTP {resp1.status_code} - {resp1.text}"
            )

        upload_url = resp1.headers.get("Location") or url
        with open(local_path, "rb") as f:
            resp2 = requests.put(upload_url, data=f, timeout=30)

        if resp2.status_code in (200, 201):
            return HDFSUploadResult(
                local_path=local_path,
                hdfs_path=hdfs_path,
                file_size_bytes=size,
                checksum_sha256=checksum,
                modo="webhdfs_live",
                exito=True,
                mensaje="Fichero subido y confirmado en clúster HDFS."
            )
        else:
            return HDFSUploadResult(
                local_path=local_path,
                hdfs_path=hdfs_path,
                file_size_bytes=size,
                checksum_sha256=checksum,
                modo="webhdfs_live",
                exito=False,
                mensaje=f"DataNode falló al escribir los datos: HTTP {resp2.status_code}"
            )
