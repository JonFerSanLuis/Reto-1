# Repositorio Académico Multidisciplinar · IA y Big Data

Repositorio centralizado para los proyectos, retos y entregas del curso de especialización en **Inteligencia Artificial y Big Data**, organizado modularmente por asignaturas.

---

## Estructura del Repositorio por Asignaturas

```text
.
├── ainhoa/                         # 🎓 Sistemas de Big Data · Reto 1 Vivienda Juvenil (Ainhoa)
│   ├── src/                        # Extracción (API + Scraping), HDFS, Kafka y Análisis
│   ├── data/                       # Almacenes brutos, procesados y muestras
│   ├── tests/                      # Suite de 18 pruebas unitarias e integración
│   ├── scripts/                    # Scripts de pipeline
│   ├── main.py                     # Orquestador específico de Ainhoa
│   ├── dashboard.html              # Interfaz visual interactiva Augen Pro
│   └── README.md                   # Documentación técnica completa del Reto 1
│
├── mia/                            # 🧠 Modelos de Inteligencia Artificial (MIA)
│   ├── motor.py                    # Motor de inferencia y encadenamiento
│   ├── reglas.py                   # Sistema experto y reglas de decisión
│   ├── casos.py                    # Batería de casos de prueba y evaluación
│   └── README.md                   # Documentación de reglas y justificación (RA1 y RA5)
│
├── pia/                            # 💻 Programación de Inteligencia Artificial (PIA)
│   ├── api/                        # API REST con FastAPI
│   ├── app/                        # Aplicación web interactiva (Streamlit)
│   └── README.md                   # Documentación de arquitectura y endpoints
│
├── saa/                            # 🤖 Sistemas de Aprendizaje Automático (SAA)
│   ├── notebooks/                  # EDA y experimentación con modelos predictivos
│   ├── modelos/                    # Pipelines y modelos serializados (.joblib)
│   └── README.md                   # Comparativa de modelos, métricas y evaluación
│
├── main.py                         # 🚀 Orquestador y lanzador global desde VS Code / terminal
├── conftest.py                     # Configuración de resolución de paths multiasignatura
├── pyproject.toml                  # Configuración de pytest y dependencias globales
├── AGENTS.md                       # Protocolo de ramas Git (dev-companero, dev-jon, test, main)
└── README.md                       # Índice general del repositorio
```

---

## 1. Asignatura: Ainhoa (Sistemas de Big Data · Reto 1)

* **Tema:** *¿Dónde pueden vivir los jóvenes en Euskadi? ¿Puede una persona joven independizarse con su salario?*
* **Alcance de la Fase 1:**
  1. **Extracción de Vivienda:** API oficial de Open Data Euskadi / Visesa WS (217 promociones) y Web Scraping ético en Habitaclia y Pisos.com.
  2. **Indicadores Complementarios:** Estadísticas socioeconómicas municipales de Eustat / Udalmap e indicadores salariales de juventud del Observatorio Vasco de la Juventud (OVJ).
  3. **Almacenamiento en HDFS:** Particionado jerárquico de datos brutos con verificación de integridad SHA-256.
  4. **Streaming en Apache Kafka:** Productor y consumidor en tiempo real sobre el tópico `euskadi-anuncios-inmobiliarios`.
  5. **Dashboard Visual Augen Pro:** Cartografía interactiva Leaflet, visor fotográfico de promociones, simulador del bono Gaztelagun (-300 €/mes) y comparador municipal en `http://localhost:8080/dashboard.html`.
* **Documentación en detalle:** Ver [`ainhoa/README.md`](ainhoa/README.md).

---

## 2. Asignatura: MIA (Modelos de Inteligencia Artificial)

* **Enfoque:** Construcción de sistemas basados en reglas de decisión explicables (RA1 y RA5).
* **Componentes:**
  - `reglas.py`: Definición de reglas `SI... ENTONCES...`, prioridades y reglas de seguridad (prioridad 10).
  - `motor.py`: Encadenamiento directo de reglas.
  - `casos.py`: Casos de prueba reales para evaluar la toma de decisiones.
* **Documentación en detalle:** Ver [`mia/README.md`](mia/README.md).

---

## 3. Asignatura: PIA (Programación de Inteligencia Artificial)

* **Enfoque:** Creación de APIs y aplicaciones cliente para exponer modelos y motores.
* **Componentes:**
  - `api/`: Servicio REST con FastAPI para consultas remotas.
  - `app/`: Aplicación frontend en Streamlit para interacción visual de usuario.
* **Documentación en detalle:** Ver [`pia/README.md`](pia/README.md).

---

## 4. Asignatura: SAA (Sistemas de Aprendizaje Automático)

* **Enfoque:** Entrenamiento, evaluación y comparación de modelos predictivos de Machine Learning (Regresión Logística, Random Forest, XGBoost).
* **Documentación en detalle:** Ver [`saa/README.md`](saa/README.md).

---

## Cómo Ejecutar el Repositorio

### Desde Visual Studio Code (F5)
Al pulsar **F5** o abrir el menú **Run & Debug** (`Ctrl+Shift+D`):
- `▶️ Reto 1 (Ainhoa): Pipeline Completo + Dashboard Visual`: Ejecuta el pipeline completo de Big Data de Ainhoa y abre automáticamente el dashboard visual interactivo.
- `🌐 Abrir Solo Dashboard Visual (Ainhoa)`: Inicia el servidor web local en el puerto 8080.
- `⚡ Ejecutar Solo Pipeline de Datos y Análisis`: Ejecuta la ingesta y análisis en la consola integrada.
- `🧪 Ejecutar Suite de Pruebas (pytest)`: Pasa los 18 tests automatizados.

### Desde la Terminal
```bash
# Ejecutar el proyecto de Ainhoa por defecto (Pipeline + Dashboard):
python main.py

# Ejecutar el pipeline de datos en consola (sin navegador):
python main.py --pipeline

# Abrir directamente el dashboard visual en el navegador:
python main.py --visual

# Ver información de otra asignatura:
python main.py --subject mia
python main.py --subject pia
python main.py --subject saa

# Ejecutar todas las pruebas del repositorio:
python main.py --test
# o bien:
pytest -v
```
