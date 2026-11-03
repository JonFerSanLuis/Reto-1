"""
conftest.py - Configuración global de pytest y resolución de paths multiasignatura.
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Asegurar que la carpeta de Ainhoa está en sys.path para imports de src
ainhoa_dir = os.path.join(ROOT_DIR, "ainhoa")
if ainhoa_dir not in sys.path:
    sys.path.insert(0, ainhoa_dir)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
