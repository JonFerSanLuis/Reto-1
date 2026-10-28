# AGENTS.md - Reglas Compartidas de Desarrollo y Automatización de Git con Antigravity

Este documento establece las normas obligatorias de desarrollo, arquitectura de código y automatización de Git para los agentes de Antigravity que colaboren en el proyecto académico **Reto 1: Acceso a la Vivienda para Jóvenes en Euskadi**.

---

## 1. Configuración de Identidad y Ramas Personales

El repositorio es compartido por dos desarrolladores que trabajan desde ordenadores y configuraciones locales independientes de Antigravity.

### Regla Fundamental
**Ninguna instrucción compartida debe fijar o asumir la identidad o rama de un desarrollador específico en el código base.**

Cada instalación local debe declarar su rama personal de desarrollo ejecutando:
```bash
git config dev.branch dev-<nombre>
# Ejemplo para Jon:
git config dev.branch dev-jon
# Ejemplo para el compañero:
git config dev.branch dev-companero
```
Alternativamente, puede definirse mediante la variable de entorno `DEV_BRANCH`.

### Estructura de Ramas
1. `dev-jon`: Rama de desarrollo personal de Jon.
2. `dev-companero`: Rama de desarrollo personal del segundo desarrollador.
3. `test`: Rama de integración donde se combinan los cambios de ambos desarrolladores y se valida su estabilidad.
4. `main`: Rama principal de producción, protegida y con código 100% probado y coherente.

---

## 2. Automatización del Flujo de Git al Finalizar una Tarea

Cada vez que Antigravity complete una tarea de código o documentación solicitada por el usuario:

1. **Inspección de Estado**:
   - Verificar la rama actual con `git rev-parse --abbrev-ref HEAD`.
   - Si no está en la rama personal configurada (`dev.branch`), cambiar a ella inmediatamente antes de comitear.
   - Identificar los archivos modificados que correspondan estrictamente a la tarea realizada.
2. **Control de Secretos**:
   - Comprobar que ningún archivo contenga claves privadas, contraseñas, tokens, archivos `.env` ni credenciales.
3. **Validación Pre-Commit**:
   - Ejecutar la suite de pruebas unitarias y de integración (`pytest tests/`).
   - Si las pruebas fallan, **no se permite crear commits ni fusionar ramas** hasta subsanar el error.
4. **Commit Descriptivo**:
   - Generar un commit con mensaje claro que describa los cambios funcionales.
   - No crear commits vacíos ni incluir artefactos temporales o del entorno virtual.
5. **Publicación en la Rama Personal**:
   - Sincronizar y subir los cambios a GitHub mediante `git push origin <dev-branch>`.
6. **Integración en 'test'**:
   - Cambiar a la rama `test`.
   - Descargar los últimos cambios remotos de `test` (`git pull origin test`).
   - Fusionar la rama personal en `test` (`git merge <dev-branch>`).
   - En caso de conflictos, aplicar el protocolo de resolución de conflictos.
   - Ejecutar la suite de pruebas sobre el código integrado en `test`.
   - Subir `test` validada al repositorio remoto (`git push origin test`).
7. **Promoción a 'main'**:
   - Si y solo si todas las pruebas pasan en `test`, cambiar a `main`.
   - Descargar el estado de `main` y fusionar `test` (`git merge test`).
   - Subir `main` validada al repositorio remoto (`git push origin main`).
8. **Sincronización Final**:
   - Regresar a la rama personal de desarrollo y sincronizarla con `main` para disponer siempre de la última versión estable.
9. **Uso del Script Automatizado**:
   - Puede ejecutarse directamente el script que automatiza todos los pasos anteriores:
     ```bash
     python scripts/git_workflow.py "Mensaje descriptivo del commit"
     ```

---

## 3. Protocolo de Resolución de Conflictos

Cuando surja un conflicto de Git durante la integración en `test`:

1. **Análisis de Ambas Versiones**:
   - Inspeccionar los marcadores `<<<<<<< HEAD`, `=======` y `>>>>>>>`.
   - Comprender la finalidad de la modificación realizada por el compañero y la propia.
2. **Conservación de Funcionalidades**:
   - No descartar ciegamente ninguna de las dos versiones.
   - En archivos de configuración, listas o dependencias (`requirements.txt`, `.gitignore`), unificar las aportaciones de ambos sin duplicados.
   - En archivos de lógica Python, coordinar las funciones y clases para que ambas coexistan de forma armónica.
3. **Validación del Resultado**:
   - Asegurarse de que no queda ningún marcador residual de conflicto.
   - Reejecutar las pruebas unitarias y comprobar que la sintaxis y la lógica son correctas.
4. **Límite de Seguridad**:
   - Si la solución no puede determinarse con total certeza sin riesgo de romper código del compañero, **detener la integración**, avisar de los archivos afectados y conservar intacto el trabajo local.
   - **Prohibición estricta**: Queda terminantemente prohibido utilizar `git reset --hard`, `git push --force` o `git clean -fd` para forzar integraciones.

---

## 4. Arquitectura y Alcance Académico (Fase 1)

El proyecto aborda exclusivamente los cuatro primeros objetivos del reto:

1. **Extracción de Vivienda (`src/extraction/`)**:
   - **API**: Cliente REST hacia APIs oficiales de vivienda en Euskadi (Open Data Euskadi / Visesa WS).
   - **Scraping**: Scraper automatizado para portales inmobiliarios con anuncios reales en Euskadi (Habitaclia), respetando `robots.txt`, cabeceras y límites de tasa.
   - Almacenamiento local en formatos estándar JSON y CSV.
2. **Indicadores Complementarios (`src/indicators/`)**:
   - Cliente REST hacia la API de **Udalmap** (Eustat / Open Data Euskadi) para obtener datos municipales de población, renta personal y disponible, tasa de ocupación juvenil y demanda de vivienda.
3. **Almacenamiento en HDFS (`src/hdfs/`)**:
   - Cliente WebHDFS con separación estricta de originales (`/data/reto1/raw/vivienda/api/`, `/data/reto1/raw/vivienda/scraping/`, `/data/reto1/raw/indicadores/`).
   - Verificación de checksum, metadatos y función de recuperación y lectura.
   - Modo de emulación local para pruebas en entornos donde el cluster Hadoop aún no esté levantado.
4. **Simulación con Apache Kafka (`src/kafka/`)**:
   - Tópico oficial: `euskadi-anuncios-inmobiliarios`.
   - Productor Python: publica eventos JSON con la estructura unificada de anuncios reales a intervalos configurables.
   - Consumidor Python: se suscribe al tópico, valida el esquema JSON y procesa la llegada progresiva de anuncios.
   - Adaptador en memoria para ejecución de pruebas unitarias continuas sin depender de un broker en ejecución.

**Exclusiones para esta fase**: No implementar MongoDB, PyMongo, pipelines de agregación ni paneles finales de BI/visualización.
