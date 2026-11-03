# PIA · Programación de Inteligencia Artificial

> **Módulo:** Programación de Inteligencia Artificial (PIA)  
> **Enfoque:** Construcción de APIs REST y aplicaciones web interactivas para exponer modelos y motores de decisión.

---

## 1. Descripción de la Asignatura
En este módulo se desarrollan las interfaces de consumo y aplicaciones de usuario final para interactuar con los modelos predictivos de Machine Learning y los motores de reglas de decisión.

---

## 2. Estructura del Proyecto PIA
```text
pia/
├── README.md               # Guía de despliegue y endpoints
├── api/                    # API REST con FastAPI
│   └── main.py             # Endpoints /predict, /reglas, /diagnostico
├── app/                    # Aplicación web interactiva (Streamlit)
│   └── app.py              # Interfaz de usuario para recepción y clientes
└── requirements.txt        # Dependencias de FastAPI, Uvicorn y Streamlit
```

---

## 3. Ejecución Rápida
- **API REST (FastAPI)**:
  ```bash
  uvicorn pia.api.main:app --reload --port 8000
  ```
- **App Web (Streamlit)**:
  ```bash
  streamlit run pia/app/app.py
  ```
