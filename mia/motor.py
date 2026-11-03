"""EL MOTOR (MIA). NO HACE FALTA TOCAR ESTE FICHERO.

QUÉ ES
------
Es la "recepcionista" que aplica el manual de la directora: coge los datos de un
caso, mira qué reglas se cumplen, aplica una y apunta el resultado. Y repite.

Es el mismo motor del ejercicio E2 del gimnasio (versión v4). No tenéis que
programarlo: lo usáis igual que usáis LogisticRegression de sklearn sin haberla
escrito. Le dais vuestras reglas y él hace su trabajo.

CÓMO TRABAJA (en cada vuelta)
-----------------------------
  1. Busca qué reglas se cumplen con los datos del caso tal y como están ahora
     (sin repetir las que ya ha usado).
  2. Si no se cumple ninguna, para.
  3. Si se cumplen varias, elige la de más prioridad.
  4. La aplica: apunta su resultado en los datos del caso (un riesgo o una decisión).
Y vuelve a empezar, mientras no haya una 'decision'.

Hacen falta varias vueltas porque lo que se apunta en una vuelta (por ejemplo,
'riesgo': 'alto') hace que en la siguiente se cumpla otra regla. Eso es encadenar.

DOS DIFERENCIAS CON EL E2
-------------------------
  - Cada regla tiene un quinto dato, 'porque', con la frase que explica la regla.
    Por eso la línea que separa los datos tiene cinco variables.
  - En vez de devolver solo la decisión, devuelve un diccionario con todo lo que
    necesita la app:

        resultado = motor(aitor, reglas)
        resultado['decision']   ->  'LLAMADA DE LA DIRECTORA'
        resultado['usadas']     ->  ['R2', 'R5']
        resultado['porque']     ->  ['R2: la probabilidad de baja es alta',
                                     'R5: riesgo alto y lleva 24 meses o más: es un socio fiel']
        resultado['vueltas']    ->  qué pasó en cada vuelta (para una tabla)
"""


def motor(caso, reglas, ver=False):
    """Aplica las reglas a un caso, vuelta a vuelta, hasta que hay una decisión.

    Argumentos:
        caso (dict): datos del caso, con la predicción del modelo ya puesta.
                     Ejemplo: {'nombre': 'Aitor', 'visitas_mes': 2, 'meses_socio': 36, 'p': 0.8}
        reglas (list): la lista de reglas de reglas.py.
        ver (bool): si es True, escribe qué pasa en cada vuelta.

    Devuelve:
        dict con:
            'decision': la decisión final. Ejemplo: 'LLAMADA DE LA DIRECTORA'
            'usadas':   reglas aplicadas, en orden. Ejemplo: ['R2', 'R5']
            'porque':   una línea por regla usada, con su texto. Sirve para explicar.
            'vueltas':  qué pasó en cada vuelta (para enseñarlo en una tabla).
    """
    datos = dict(caso)    # copia de los datos del caso (el original no se toca)
    usadas = []           # reglas que ya se han aplicado
    vueltas = []          # lo que pasa en cada vuelta
    explicacion = []      # el texto 'porque' de cada regla aplicada
    vuelta = 0

    while 'decision' not in datos:        # mientras no haya decisión...
        vuelta = vuelta + 1

        # 1. ¿Qué reglas se cumplen? (cumplen se vacía en cada vuelta)
        cumplen = []
        nombres_cumplen = []
        for regla in reglas:
            nombre, se_cumple, apunta, prioridad, porque = regla
            if nombre in usadas:
                continue
            try:
                se_cumple_ahora = se_cumple(datos)
            except KeyError:   # si al caso le falta un dato, la regla no se cumple
                se_cumple_ahora = False
            if se_cumple_ahora:
                cumplen.append(regla)
                nombres_cumplen.append(nombre)

        # 2. Si no se cumple ninguna, paramos
        if len(cumplen) == 0:
            break

        # 3. Si se cumplen varias, elegimos la de más prioridad (la prioridad es el dato 3)
        elegida = cumplen[0]
        for regla in cumplen:
            if regla[3] > elegida[3]:
                elegida = regla

        # 4. Aplicamos la elegida: apuntamos su resultado en los datos del caso
        nombre, se_cumple, apunta, prioridad, porque = elegida
        datos.update(apunta)
        usadas.append(nombre)
        explicacion.append(nombre + ': ' + porque)

        vueltas.append({'vuelta': vuelta,
                        'se cumplen': ', '.join(nombres_cumplen),
                        'se aplica': nombre,
                        'apunta': str(apunta)})
        if ver:
            print('Vuelta', vuelta, ': se cumplen', nombres_cumplen, '-> se aplica', nombre, '-> apunta', apunta)

    decision = datos.get('decision', 'SIN DECISIÓN (ninguna regla encaja: falta una regla)')
    if ver:
        print()
        print(datos.get('nombre', 'Caso'), ':', decision, '  (reglas usadas:', ' -> '.join(usadas), ')')

    return {'decision': decision, 'usadas': usadas, 'porque': explicacion, 'vueltas': vueltas}
