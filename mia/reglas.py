"""EL FICHERO DE REGLAS (MIA · RA5). ESTE FICHERO LO ESCRIBÍS VOSOTROS.

QUÉ ES
------
Es el "manual de la directora": las instrucciones que dicen qué hacer con cada caso.
Es exactamente lo mismo que el Paso 3 del ejercicio E2 del gimnasio, pero en un
fichero aparte. Así la app de PIA también puede usar estas reglas.

Tiene tres partes, de arriba abajo:

  1. LÍMITES: los números que decide la empresa (por ejemplo, desde qué
     probabilidad el riesgo es "alto").
  2. CONDICIONES: una función por regla. Mira los datos del caso y responde
     True (se cumple) o False (no se cumple).
  3. LA LISTA 'reglas': junta cada condición con lo que hace la regla.

CÓMO SE LEE UNA REGLA
---------------------
    ('R5', si_R5, {'decision': 'LLAMADA DE LA DIRECTORA'}, 1, 'riesgo alto y socio fiel')
      |      |                  |                          |            |
    nombre  condición     lo que apunta en los datos   prioridad   el porqué (para la app)

Es la misma tupla del E2 con un quinto dato al final: una frase que explica la
regla. Es lo que la app enseña cuando alguien pregunta "¿por qué?".

TRES IDEAS QUE TENÉIS QUE RECORDAR
----------------------------------
  - 'd' son los datos del caso: un diccionario, como la ficha de Aitor en el E2.
  - Unas reglas APUNTAN algo intermedio (por ejemplo 'riesgo': 'alto') y otras lo
    LEEN después con d.get('riesgo'). Eso es encadenar reglas.
    Usad siempre d.get('...') para leer algo que apunta otra regla: si todavía no
    está apuntado, devuelve None y la regla no se cumple, sin dar error.
  - Si se cumplen varias reglas a la vez, gana la de prioridad más alta.
    Las reglas de seguridad llevan siempre la más alta (10).

CÓMO ADAPTARLO A VUESTRO PROYECTO (en este orden)
-------------------------------------------------
  1. Escribid primero vuestras reglas EN PAPEL, con una tabla:
         Regla | SI... | ENTONCES... | Prioridad
  2. Cambiad los LÍMITES por los vuestros.
  3. Escribid una función si_Rx por cada regla. Copiad una de las de abajo y
     cambiadla: casi todas son una sola línea.
  4. Poned cada regla en la lista 'reglas', con su prioridad y su porqué.
  5. Probadlas con vuestros casos en casos.py.

ANTES DE ENTREGAR, COMPROBAD
----------------------------
  [ ] 6 reglas o más
  [ ] al menos una regla de seguridad con prioridad 10 (un dato imposible: no se decide)
  [ ] al menos una regla que usa un dato que el modelo NO usa (aquí, meses_socio)
  [ ] cada regla tiene su texto 'porque'
  [ ] ningún caso se queda sin decisión
"""

# ---------------------------------------------------------------------------
# 1. LÍMITES QUE DECIDE LA EMPRESA
#    Van arriba y en mayúsculas porque pueden cambiar. Si la directora decide
#    que el riesgo alto empieza en 0,6, se cambia aquí y todas las reglas que
#    usan el límite se enteran. No hay que tocar el modelo.
# ---------------------------------------------------------------------------
LIMITE_ALTO = 0.7
LIMITE_MEDIO = 0.4

# Después (visitas previstas)
POCAS_VISITAS = 3
VISITAS_NORMALES = 6


# ---------------------------------------------------------------------------
# 2. CONDICIONES: ¿se cumple cada regla?
#    d = los datos del caso. Cada función responde True o False.
#    Leedlas como frases: la explicación de cada una dice lo que pregunta.
# ---------------------------------------------------------------------------
def si_R1(d):
    """R1 (SEGURIDAD). ¿Las visitas son negativas? Es un dato imposible."""
    return d['visitas_mes'] < 0


def si_R2(d):
    """R2. ¿La probabilidad de baja es igual o mayor que LIMITE_ALTO?"""
    return d['p'] >= LIMITE_ALTO


def si_R3(d):
    """R3. ¿La probabilidad está entre LIMITE_MEDIO (incluido) y LIMITE_ALTO (sin incluir)?"""
    return d['p'] >= LIMITE_MEDIO and d['p'] < LIMITE_ALTO


def si_R4(d):
    """R4. ¿La probabilidad es menor que LIMITE_MEDIO?"""
    return d['p'] < LIMITE_MEDIO


def si_R5(d):
    """R5. ¿Hay apuntado riesgo alto (lo apunta R2) Y lleva 24 meses o más?"""
    return d.get('riesgo') == 'alto' and d['meses_socio'] >= 24


def si_R6(d):
    """R6. ¿Hay apuntado riesgo alto (lo apunta R2) Y lleva menos de 24 meses?"""
    return d.get('riesgo') == 'alto' and d['meses_socio'] < 24


def si_R7(d):
    """R7. ¿Hay apuntado riesgo medio (lo apunta R3)?"""
    return d.get('riesgo') == 'medio'


def si_R8(d):
    """R8. ¿Hay apuntado riesgo bajo (lo apunta R4)?"""
    return d.get('riesgo') == 'bajo'


def si_R9(d):
    """R9. ¿Hay riesgo alto y el socio es premium?"""
    return d.get('riesgo') == 'alto' and d.get('tipo_cuota') == 'premium'


def si_R10(d):
    """R10. ¿El socio debe alguna cuota?"""
    return d.get('cuota_impagada') == 'si'


def si_R11(d):
    """R11. ¿Es menor de edad y tiene riesgo alto?"""
    return d.get('edad', 30) < 18 and d.get('riesgo') == 'alto'


def si_R12(d):
    """R12 (SEGURIDAD). ¿La edad es imposible?"""
    return d.get('edad', 30) < 0 or d.get('edad', 30) > 100


# ---------------------------------------------------------------------------
# 3. LA LISTA DE REGLAS (igual que en el ejercicio E2, con un quinto dato)
#    Cada regla tiene 5 datos, siempre en este orden:
#      nombre, condición, qué apunta, prioridad, porqué
#
#    - R2, R3 y R4 apuntan un RIESGO: no deciden nada, dejan una nota.
#    - R1 y R5 a R8 apuntan una DECISIÓN: cuando se aplica una, el motor termina.
# ---------------------------------------------------------------------------
reglas = [
    ('R1', si_R1, {'decision': 'REVISAR FICHA (dato erróneo)'}, 10, 'las visitas son negativas: el dato está mal y no se decide nada'),
    ('R2', si_R2, {'riesgo': 'alto'},                            1, 'la probabilidad de baja es alta'),
    ('R3', si_R3, {'riesgo': 'medio'},                           1, 'la probabilidad de baja es media'),
    ('R4', si_R4, {'riesgo': 'bajo'},                            1, 'la probabilidad de baja es baja'),
    ('R5', si_R5, {'decision': 'LLAMADA DE LA DIRECTORA'},       1, 'riesgo alto y lleva 24 meses o más: es un socio fiel'),
    ('R6', si_R6, {'decision': 'SESIÓN GRATIS'},                 1, 'riesgo alto y lleva menos de 24 meses'),
    ('R7', si_R7, {'decision': 'EMAIL CON DESCUENTO'},           1, 'riesgo medio'),
    ('R8', si_R8, {'decision': 'NO HACER NADA'},                 1, 'riesgo bajo'),
    ('R9', si_R9, {'decision': 'LLAMADA + MES GRATIS'},          2, 'riesgo alto y es socio premium'),
    ('R10', si_R10, {'decision': 'PASAR A ADMINISTRACIÓN'},      8, 'debe una cuota'),
    ('R11', si_R11, {'decision': 'AVISAR A LA FAMILIA'},          5, 'es menor de edad y tiene riesgo alto'),
    ('R12', si_R12, {'decision': 'REVISAR FICHA (dato erróneo)'}, 10, 'la edad es imposible'),
]
