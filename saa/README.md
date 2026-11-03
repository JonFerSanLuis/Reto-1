# SAA · Sistemas de Aprendizaje Automático

> **Módulo:** Sistemas de Aprendizaje Automático (SAA)  
> **Enfoque:** Entrenamiento, evaluación, validación cruzada y comparación de modelos de Machine Learning supervisados y no supervisados.

---

## 1. Descripción de la Asignatura
En este módulo se abordan el preprocesamiento de datos (EDA, normalización, codificación), la selección de características y el entrenamiento de algoritmos de clasificación y regresión:
- Regresión Logística
- Árboles de Decisión y Random Forest
- Gradient Boosting y XGBoost
- Redes Neuronales Densas (MLP)

---

## 2. Estructura del Proyecto SAA
```text
saa/
├── README.md               # Métricas de entrenamiento y análisis comparativo
├── notebooks/              # Cuadernos Jupyter de experimentación y EDA
├── modelos/                # Modelos serializados (joblib / pickle)
│   └── modelo.joblib       # Pipeline entrenado (escalador + clasificador)
└── src/                    # Scripts de entrenamiento y evaluación
```

---

## 3. Serialización del Modelo
Para utilizar el modelo en la plantilla común del reto:
```python
import joblib
from sklearn.pipeline import Pipeline

# Guardar pipeline completo (preprocesado + clasificador)
joblib.dump(pipeline, 'saa/modelos/modelo.joblib')
```
