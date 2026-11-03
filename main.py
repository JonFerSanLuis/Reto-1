#!/usr/bin/env python3
"""
main.py - Orquestador y Portal Multiasignatura del Repositorio.

Permite ejecutar el proyecto de cualquiera de las asignaturas:
  python main.py                 -> Ejecuta por defecto el proyecto de Ainhoa (Pipeline + Dashboard Visual).
  python main.py --subject ainhoa -> Ejecuta el proyecto de Ainhoa (Big Data y Vivienda Juvenil).
  python main.py --subject mia   -> Muestra información y casos de MIA (Modelos de IA).
  python main.py --subject pia   -> Muestra información y estructura de PIA (Programación de IA).
  python main.py --subject saa   -> Muestra información y modelos de SAA (Aprendizaje Automático).
  python main.py --pipeline      -> Ejecuta el pipeline de datos de Ainhoa.
  python main.py --visual        -> Abre el dashboard visual de Ainhoa.
  python main.py --test          -> Ejecuta la suite de pruebas completa con pytest.
"""

import os
import sys
import argparse
import subprocess

# Configurar salida segura en UTF-8 en Windows
if sys.platform.startswith("win") and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
AINHOA_DIR = os.path.join(ROOT_DIR, "ainhoa")

if AINHOA_DIR not in sys.path:
    sys.path.insert(0, AINHOA_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def print_banner():
    print("=" * 80)
    print("  REPOSITORIO ACADÉMICO MULTIDISCIPLINAR - CURSO DE IA Y BIG DATA")
    print("=" * 80)
    print("  Asignaturas disponibles:")
    print("    1. [ainhoa] -> Sistemas de Big Data / Reto 1 Vivienda Euskadi (Ainhoa)")
    print("    2. [mia]    -> Modelos de Inteligencia Artificial (Sistemas de Reglas)")
    print("    3. [pia]    -> Programación de Inteligencia Artificial (API & App)")
    print("    4. [saa]    -> Sistemas de Aprendizaje Automático (Machine Learning)")
    print("=" * 80 + "\n")


def run_ainhoa_main(args_list):
    """Ejecuta el orquestador de Ainhoa pasando los argumentos pertinentes."""
    ainhoa_main_script = os.path.join(AINHOA_DIR, "main.py")
    cmd = [sys.executable, ainhoa_main_script] + args_list
    return subprocess.call(cmd, cwd=AINHOA_DIR)


def show_subject_info(subject: str):
    subj = subject.lower()
    readme_map = {
        "mia": os.path.join(ROOT_DIR, "mia", "README.md"),
        "pia": os.path.join(ROOT_DIR, "pia", "README.md"),
        "saa": os.path.join(ROOT_DIR, "saa", "README.md"),
    }
    readme_file = readme_map.get(subj)
    if readme_file and os.path.exists(readme_file):
        with open(readme_file, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
            try:
                print(text)
            except UnicodeEncodeError:
                safe_text = text.encode("ascii", errors="replace").decode("ascii")
                print(safe_text)
    else:
        print(f"[INFO] Asignatura '{subject}' inicializada en la carpeta ./{subject}/")


def main():
    parser = argparse.ArgumentParser(
        description="Portal de Ejecución Multiasignatura - IA y Big Data"
    )
    parser.add_argument(
        "--subject",
        choices=["ainhoa", "mia", "pia", "saa"],
        default="ainhoa",
        help="Asignatura a ejecutar (por defecto: ainhoa)"
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="Ejecuta únicamente el pipeline de datos (Ainhoa)."
    )
    parser.add_argument(
        "--visual",
        action="store_true",
        help="Inicia el servidor web y abre el dashboard visual (Ainhoa)."
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Ejecuta la suite de pruebas unitarias con pytest."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Puerto HTTP para el Dashboard Visual (por defecto: 8080)."
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="No abrir el navegador automáticamente."
    )

    args, unknown = parser.parse_known_args()

    if args.test:
        import pytest
        print("\nEjecutando pruebas de todas las asignaturas...\n")
        code = pytest.main(["-v"])
        sys.exit(code)

    if args.subject == "ainhoa":
        # Pasar los argumentos correspondientes a ainhoa/main.py
        passthrough = []
        if args.pipeline:
            passthrough.append("--pipeline")
        if args.visual:
            passthrough.append("--visual")
        if args.port != 8080:
            passthrough.extend(["--port", str(args.port)])
        if args.no_browser:
            passthrough.append("--no-browser")
        passthrough.extend(unknown)
        
        sys.exit(run_ainhoa_main(passthrough))
    else:
        print_banner()
        show_subject_info(args.subject)


if __name__ == "__main__":
    main()
