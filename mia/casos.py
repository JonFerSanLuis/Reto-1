"""CASOS DE PRUEBA (MIA · RA5). ESTE FICHERO LO ADAPTÁIS VOSOTROS.

PARA QUÉ SIRVE
--------------
Antes de entregar un programa hay que comprobar que hace lo que debe. Aquí se
apuntan unos cuantos casos con la decisión que ESPERÁIS que salga, y el
ordenador comprueba si sale eso. Es como el Paso 6 del E2, pero sin tener que
mirarlo uno a uno: escribe BIEN o MAL al lado de cada caso.

Responde a la pregunta 2 del RA5: "¿Han probado el sistema con varios casos?"

SI SALE MAL
-----------
Hay dos posibilidades, y las dos sirven para aprender:
  - la regla está mal escrita (por ejemplo, un >= donde debía ir un <), o
  - lo que esperabais estaba mal pensado (el sistema tiene razón y vosotros no).
Mirad las reglas usadas que salen al lado y seguid el caso vuelta a vuelta.

QUÉ CASOS PONER
---------------
  - un caso normal por cada decisión posible (aquí hay 5 decisiones: 5 casos),
  - un caso límite, justo en el límite (por ejemplo, una probabilidad de 0,70),
  - un caso con un dato erróneo, para ver que la regla de seguridad lo para.

CÓMO SE ESCRIBE UN CASO
-----------------------
    ('Aitor', {'visitas_mes': 2, 'meses_socio': 36}, 'LLAMADA DE LA DIRECTORA'),
      |              |                                     |
    nombre    datos del caso (sin la p:            decisión que esperáis
              la calcula el modelo)

CÓMO SE EJECUTA
---------------
Desde el notebook practica_reglas.ipynb (Paso 3), o en la terminal, desde la
carpeta de la plantilla:   python -m mia.casos
"""

CASOS = [
    # nombre,  datos del caso,                               decisión esperada
    ('Aitor', {'visitas_mes': 2,  'meses_socio': 36}, 'LLAMADA DE LA DIRECTORA'),
    ('Leire', {'visitas_mes': 4,  'meses_socio': 30}, 'EMAIL CON DESCUENTO'),
    ('Nerea', {'visitas_mes': 3,  'meses_socio': 10}, 'SESIÓN GRATIS'),
    ('Unai',  {'visitas_mes': 5,  'meses_socio': 40}, 'EMAIL CON DESCUENTO'),
    ('Irati', {'visitas_mes': 8,  'meses_socio': 20}, 'NO HACER NADA'),
    ('Gorka', {'visitas_mes': -3, 'meses_socio': 15}, 'REVISAR FICHA (dato erróneo)'),
    ('Maite', {'visitas_mes': 2, 'meses_socio': 10, 'tipo_cuota': 'premium'}, 'LLAMADA + MES GRATIS'),
    ('Ane',   {'visitas_mes': 5, 'meses_socio': 40, 'cuota_impagada': 'si'}, 'PASAR A ADMINISTRACIÓN'),
    ('Mikel', {'visitas_mes': 2, 'meses_socio': 12, 'edad': 16}, 'AVISAR A LA FAMILIA'),
    ('Jon',   {'visitas_mes': 6, 'meses_socio': 20, 'edad': -5}, 'REVISAR FICHA (dato erróneo)'),
]


def probar_casos(reglas, predecir, motor):
    """Pasa todos los CASOS por el motor y dice BIEN o MAL en cada uno.

    Hace con cada caso lo mismo que hacíais con Aitor en el E2:
      1. copia sus datos y le pone el nombre,
      2. le pide al modelo la probabilidad (p),
      3. lo pasa por el motor,
      4. compara la decisión con la esperada.

    Argumentos:
        reglas (list): la lista de reglas de reglas.py.
        predecir (function): la función del modelo (modelo.py).
        motor (function): el motor (motor.py).

    Devuelve:
        list: una fila por caso (para enseñarla como tabla).
    """
    filas = []
    for nombre, datos, esperada in CASOS:
        caso = dict(datos)
        caso['nombre'] = nombre
        caso['p'] = predecir(caso)
        resultado = motor(caso, reglas)
        filas.append({'caso': nombre,
                      'p': caso['p'],
                      'reglas usadas': ' -> '.join(resultado['usadas']),
                      'decisión': resultado['decision'],
                      'esperada': esperada,
                      '¿bien?': 'BIEN' if resultado['decision'] == esperada else 'MAL'})
    return filas


if __name__ == '__main__':
    # Esto solo se ejecuta si lanzáis el fichero desde la terminal: python -m mia.casos
    from modelo import predecir
    from mia.motor import motor
    from mia.reglas import reglas
    for fila in probar_casos(reglas, predecir, motor):
        print(f"{fila['¿bien?']:5s} {fila['caso']:8s} p={fila['p']:<5} {fila['reglas usadas']:10s} {fila['decisión']}")
