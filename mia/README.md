# MIA · Modelos de Inteligencia Artificial

> **Módulo:** Modelos de Inteligencia Artificial (MIA)  
> **Resultado de Aprendizaje Evaluado:** RA1 (Caracterización de problemas de IA) y RA5 (Sistemas basados en reglas de decisión).

---

## 1. Descripción de la Asignatura
En esta asignatura se desarrollan sistemas expertos basados en conocimiento y reglas de decisión para resolver problemas empresariales y sociales, complementando las predicciones de modelos estadísticos y de Machine Learning con reglas de negocio y salvaguardas de seguridad.

---

## 2. Estructura del Proyecto MIA
```text
mia/
├── README.md               # Documentación y justificación de casos y reglas
├── __init__.py
├── motor.py                # Motor de inferencia y encadenamiento de reglas
├── reglas.py               # Definición de reglas (SI... ENTONCES...) y prioridades
└── casos.py                # Batería de casos de prueba representativos
```

---

## 3. Requisitos de Entrega (RA5)
1. **Fichero de Reglas (`reglas.py`)**: Mínimo 6 reglas estructuradas con condición, acción y prioridad.
2. **Reglas de Seguridad**: Al menos una regla de prioridad 10 para datos imposibles o situaciones anómalas (*NO DECIDIR / ALERTA*).
3. **Casos de Prueba (`casos.py`)**: Ejecución con casos reales y casos límite demostrando la explicabilidad de cada decisión.
