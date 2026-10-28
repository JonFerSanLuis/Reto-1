#!/usr/bin/env python3
"""
scripts/git_workflow.py

Automatización del flujo de trabajo de Git y GitHub para el Reto 1:
- Detección dinámica de la rama personal del desarrollador (via 'git config dev.branch' o DEV_BRANCH).
- Validación de estado local y prevención de inclusión de secretos.
- Ejecución de la suite de pruebas automatizadas (pytest) previa al commit.
- Commit descriptivo y push seguro a la rama personal.
- Integración en 'test', detección y ayuda en resolución automática de conflictos.
- Ejecución de pruebas sobre el código integrado en 'test'.
- Promoción validada a 'main' si todas las pruebas pasan.
- Sincronización final de la rama personal de desarrollo.
- Sin comandos destructivos (no force push, no hard reset).
"""

import os
import sys
import subprocess
import re
from typing import List, Tuple, Optional

# Extensiones y patrones sospechosos de contener secretos
SECRET_PATTERNS = [
    r"\.env$",
    r"\.pem$",
    r"\.key$",
    r"id_rsa",
    r"id_ed25519",
    r"password",
    r"token",
    r"secret",
    r"credential"
]


def run_cmd(cmd: List[str], check: bool = True, capture: bool = True, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    """Ejecuta un comando de forma segura y devuelve el resultado."""
    is_windows = os.name == "nt"
    env = os.environ.copy()
    # Evitar bloqueos interactivos en push/pull
    if cmd and cmd[0] == "git" and len(cmd) > 1 and cmd[1] in ("push", "pull", "fetch"):
        env["GCM_INTERACTIVE"] = "never"
        env["GIT_TERMINAL_PROMPT"] = "0"

    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            text=True,
            check=check,
            shell=is_windows,
            timeout=timeout,
            env=env
        )
        return res
    except subprocess.TimeoutExpired as e:
        print(f"[TIMEOUT] El comando excedió el tiempo límite ({timeout}s): {' '.join(cmd)}", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as e:
        if capture and e.stderr:
            print(f"[ERROR COMANDO] {' '.join(cmd)}\n{e.stderr.strip()}", file=sys.stderr)
        raise


def get_current_branch() -> str:
    """Devuelve la rama local actual."""
    res = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return res.stdout.strip()


def get_developer_branch() -> str:
    """
    Obtiene la rama personal configurada para esta instalación local.
    Prioridad:
    1. git config dev.branch
    2. Variable de entorno DEV_BRANCH
    3. Si la rama actual empieza por 'dev-', usa la rama actual.
    """
    try:
        res = run_cmd(["git", "config", "dev.branch"])
        branch = res.stdout.strip()
        if branch:
            return branch
    except subprocess.CalledProcessError:
        pass

    env_branch = os.environ.get("DEV_BRANCH")
    if env_branch:
        return env_branch

    curr = get_current_branch()
    if curr.startswith("dev-"):
        return curr

    raise ValueError(
        "No se ha configurado la rama personal del desarrollador. "
        "Ejecuta: git config dev.branch dev-<tu-nombre> (por ejemplo: git config dev.branch dev-jon)"
    )


def check_for_secrets(files: List[str]) -> List[str]:
    """Verifica que ningún archivo a incluir coincida con patrones de secretos."""
    forbidden = []
    for f in files:
        f_lower = f.lower()
        if any(re.search(pat, f_lower) for pat in SECRET_PATTERNS):
            if not f.endswith(".example") and not f.endswith(".py"):
                forbidden.append(f)
    return forbidden


def run_tests() -> bool:
    """Ejecuta la suite de pruebas pytest."""
    print(">>> Ejecutando pruebas automatizadas (pytest)...")
    python_exec = sys.executable
    try:
        res = subprocess.run([python_exec, "-m", "pytest", "tests", "-v"], check=False)
        return res.returncode == 0
    except Exception as e:
        print(f"[ERROR] No se pudo ejecutar pytest: {e}", file=sys.stderr)
        return False


def get_status() -> Tuple[List[str], List[str]]:
    """Devuelve (archivos_modificados_staged, archivos_modificados_unstaged)."""
    res = run_cmd(["git", "status", "--porcelain"])
    lines = res.stdout.splitlines()
    staged = []
    unstaged = []
    for line in lines:
        if len(line) < 4:
            continue
        idx_status = line[0]
        work_status = line[1]
        path = line[3:].strip()
        if idx_status not in (" ", "?"):
            staged.append(path)
        if work_status not in (" ",):
            unstaged.append(path)
        if idx_status == "?" and work_status == "?":
            unstaged.append(path)
    return staged, unstaged


def attempt_resolve_conflicts() -> bool:
    """
    Inspecciona si hay conflictos tras un merge.
    Si existen marcadores de conflicto, comprueba si pueden resolverse de forma segura.
    Retorna True si no quedan conflictos, False si se requiere intervención manual.
    """
    res = run_cmd(["git", "status", "--porcelain"])
    conflicted_files = []
    for line in res.stdout.splitlines():
        if line.startswith("UU ") or line.startswith("AA ") or line.startswith("DD "):
            conflicted_files.append(line[3:].strip())

    if not conflicted_files:
        return True

    print(f"[ALERTA] Conflictos detectados en los siguientes archivos: {conflicted_files}")
    for file_path in conflicted_files:
        if not os.path.exists(file_path):
            continue
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Si ambos añadieron entradas en archivos como requirements.txt o .gitignore sin solape crítico:
        if os.path.basename(file_path) in ("requirements.txt", ".gitignore"):
            # Resolver uniendo ambas listas de forma no redundante
            pattern = re.compile(r"<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> [^\n]+", re.S)
            def merge_unique(m):
                part_a = m.group(1).splitlines()
                part_b = m.group(2).splitlines()
                combined = []
                for item in part_a + part_b:
                    clean = item.strip()
                    if clean and clean not in combined:
                        combined.append(clean)
                return "\n".join(combined)

            new_content = pattern.sub(merge_unique, content)
            if "<<<<<<< HEAD" not in new_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                run_cmd(["git", "add", file_path])
                print(f"[RESOLUCIÓN AUTO] Conflicto resuelto automáticamente en {file_path}")
            else:
                return False
        else:
            # En código Python, no forzamos combinaciones ciegas para preservar exactitud
            print(f"[DECISIÓN PENDIENTE] Conflicto en archivo de lógica {file_path}. Requiere revisión.")
            return False

    # Verificar de nuevo si quedan conflictos
    res_after = run_cmd(["git", "status", "--porcelain"])
    remaining = [line for line in res_after.stdout.splitlines() if line[:2] in ("UU", "AA", "DD")]
    return len(remaining) == 0


def complete_task(commit_message: str, specific_files: Optional[List[str]] = None) -> bool:
    """
    Ejecuta el flujo completo de automatización tras finalizar una tarea:
    1. Verificación de rama y estado
    2. Comprobación de secretos
    3. Pruebas antes del commit
    4. Commit y push a la rama de desarrollo
    5. Integración en 'test'
    6. Pruebas en 'test'
    7. Promoción a 'main'
    8. Sincronización
    """
    dev_branch = get_developer_branch()
    current_branch = get_current_branch()

    print(f"=== INICIANDO FLUJO DE GIT ===")
    print(f"Rama configurada del desarrollador: {dev_branch}")
    print(f"Rama actual: {current_branch}")

    if current_branch != dev_branch:
        print(f"[PASO 1] Cambiando a la rama personal: {dev_branch}...")
        run_cmd(["git", "checkout", dev_branch])

    staged, unstaged = get_status()
    all_changed = list(set(staged + unstaged))

    if not all_changed:
        print("[INFO] No hay modificaciones pendientes en el repositorio. Nada que comitear.")
        return True

    files_to_commit = specific_files if specific_files else all_changed

    # Verificar secretos
    forbidden_secrets = check_for_secrets(files_to_commit)
    if forbidden_secrets:
        print(f"[ERROR CRÍTICO DE SEGURIDAD] Se detectaron archivos prohibidos: {forbidden_secrets}", file=sys.stderr)
        print("Elimínalos o añádelos a .gitignore antes de continuar.", file=sys.stderr)
        return False

    # Ejecutar pruebas antes del commit
    tests_passed = run_tests()
    if not tests_passed:
        print("[BLOQUEADO] Las pruebas automatizadas han fallado. No se generará commit hasta resolverlas.", file=sys.stderr)
        return False

    # Añadir archivos
    for f in files_to_commit:
        run_cmd(["git", "add", f])

    # Verificar si tras add hay algo staged
    staged_now, _ = get_status()
    if not staged_now:
        print("[INFO] No hay cambios reales staged para comitear.")
        return True

    # Commit descriptivo
    print(f"[PASO 2] Creando commit: '{commit_message}'...")
    run_cmd(["git", "commit", "-m", commit_message])

    # Push a la rama de desarrollo
    print(f"[PASO 3] Sincronizando y subiendo cambios a origin/{dev_branch}...")
    try:
        run_cmd(["git", "push", "origin", dev_branch])
        print(f"[ÉXITO] Rama {dev_branch} subida correctamente al remoto.")
    except Exception as e:
        print(f"[AVISO REMOTO] Falló el push a origin/{dev_branch}: {e}")
        print("Continuando con integración local...")

    # Integración en 'test'
    print("[PASO 4] Iniciando integración en rama 'test'...")
    try:
        run_cmd(["git", "checkout", "test"])
    except Exception:
        run_cmd(["git", "checkout", "-b", "test"])

    # Intentar traer cambios remotos de test si existen
    try:
        run_cmd(["git", "pull", "origin", "test", "--no-rebase"])
    except Exception:
        pass

    # Merge de dev_branch en test
    print(f"Mezclando '{dev_branch}' en 'test'...")
    merge_res = run_cmd(["git", "merge", dev_branch, "--no-edit"], check=False)
    if merge_res.returncode != 0:
        print("[AVISO] Aparecieron conflictos al integrar en 'test'. Intentando resolución automática...")
        resolved = attempt_resolve_conflicts()
        if not resolved:
            print("[ALTO] Conflictos sin resolver en 'test'. Se detiene la promoción a main.", file=sys.stderr)
            run_cmd(["git", "checkout", dev_branch])
            return False
        else:
            run_cmd(["git", "commit", "-m", f"Merge automático y resolución de conflictos de {dev_branch} en test"])

    # Ejecutar pruebas sobre el código integrado en 'test'
    print("[PASO 5] Verificando pruebas sobre la rama de integración 'test'...")
    test_branch_passed = run_tests()
    if not test_branch_passed:
        print("[BLOQUEO] El código integrado en 'test' falló las pruebas. NO se promocionará a 'main'.", file=sys.stderr)
        run_cmd(["git", "checkout", dev_branch])
        return False

    # Push a origin/test
    try:
        run_cmd(["git", "push", "origin", "test"])
        print("[ÉXITO] Rama 'test' subida al remoto.")
    except Exception as e:
        print(f"[AVISO] No se pudo hacer push de 'test' al remoto: {e}")

    # Promoción a 'main'
    print("[PASO 6] Promocionando versión validada a 'main'...")
    run_cmd(["git", "checkout", "main"])
    try:
        run_cmd(["git", "pull", "origin", "main", "--no-rebase"])
    except Exception:
        pass

    run_cmd(["git", "merge", "test", "--ff-only"], check=False)
    # Si fast-forward no es posible, merge con mensaje
    status_main = run_cmd(["git", "status", "--porcelain"])
    if "working tree clean" not in run_cmd(["git", "status"]).stdout:
        run_cmd(["git", "merge", "test", "--no-edit"])

    # Push a origin/main
    try:
        run_cmd(["git", "push", "origin", "main"])
        print("[ÉXITO] Rama 'main' actualizada en el remoto.")
    except Exception as e:
        print(f"[AVISO] No se pudo hacer push de 'main' al remoto: {e}")

    # Regresar a la rama personal y sincronizar con main
    print(f"[PASO 7] Regresando a la rama personal '{dev_branch}' y sincronizando...")
    run_cmd(["git", "checkout", dev_branch])
    run_cmd(["git", "merge", "main", "--no-edit"], check=False)

    print("=== FLUJO COMPLETADO CON ÉXITO ===")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/git_workflow.py '<mensaje_de_commit>' [archivos_especificos...]")
        sys.exit(1)

    msg = sys.argv[1]
    specific = sys.argv[2:] if len(sys.argv) > 2 else None
    success = complete_task(msg, specific)
    sys.exit(0 if success else 1)
