# -*- coding: utf-8 -*-
"""
generar_dataset.py
==================
Genera el dataset SINTÉTICO y ACADÉMICO de reportes de obra para el proyecto
VOREKO IA (Actividad 4, Módulo 2 – Gestión de Proyectos de IA, Tecmilenio).

IMPORTANTE
----------
* Los textos NO provienen de usuarios reales de VOREKO. Fueron redactados con
  apoyo de IA generativa y revisados por el autor, imitando la forma en que un
  residente, maestro de obra o cliente describiría situaciones habituales de
  obras residenciales pequeñas y medianas en México.
* La etiqueta `categoria_real` representa el SIGNIFICADO del texto según la
  regla de etiquetado descrita abajo; nunca la predicción de un modelo.

Regla de etiquetado (una categoría principal por registro)
----------------------------------------------------------
1. Se asigna la incidencia que el texto expresa como problema principal.
2. Si el texto menciona dos incidencias con peso similar, se aplica la
   prioridad: Riesgos de seguridad > Problemas de calidad > Retraso de
   ejecución > Sobrecosto, y se marca `multiples_incidencias = True`.
3. "Sin incidencia identificada" sólo se usa cuando el texto describe avance
   normal o resultados satisfactorios, aunque mencione palabras de otras
   categorías (p. ej. "el gasto se mantuvo dentro del presupuesto").

Uso
---
    python src/generar_dataset.py            # escribe data/reportes_obra_sinteticos.csv
    python src/generar_dataset.py --salida otra_ruta.csv

Sólo usa la biblioteca estándar de Python para que pueda ejecutarse en
cualquier entorno (local o Colab) sin dependencias adicionales.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Parámetros de reproducibilidad
# ---------------------------------------------------------------------------
SEMILLA = 2026                 # semilla única para fechas, tipos de obra y partición
N_EXPLORACION_POR_CLASE = 6    # 6 x 5 = 30 registros para pruebas exploratorias
FECHA_INICIO = dt.date(2026, 1, 5)
FECHA_FIN = dt.date(2026, 9, 30)

CATEGORIAS = [
    "Sobrecosto",
    "Retraso de ejecución",
    "Problemas de calidad",
    "Riesgos de seguridad",
    "Sin incidencia identificada",
]

TIPOS_OBRA = [
    "casa habitación de un nivel",
    "casa habitación de dos niveles",
    "ampliación de vivienda",
    "remodelación de departamento",
    "dúplex en condominio horizontal",
    "local comercial en planta baja de vivienda",
]

# Tipos de redacción utilizados para controlar la diversidad del dataset:
#   directo    -> describe la situación de forma explícita
#   coloquial  -> lenguaje informal de obra
#   negacion   -> la idea clave se expresa con una negación
#   ambiguo    -> contiene señales de más de una categoría
#   contraste  -> usa vocabulario de otra categoría pero su sentido es distinto
# Cada tupla: (texto, etapa_de_obra, tipo_redaccion, multiples_incidencias)

REPORTES = {
    "Sobrecosto": [
        ("El proveedor nos avisó que la varilla de 3/8 subió casi 18 % desde la cotización de la semana pasada.", "estructura", "directo", False),
        ("Se compraron 40 bultos de cemento a $265 cuando en el presupuesto venían a $228.", "obra negra", "directo", False),
        ("Ojo con la partida de impermeabilización, ya vamos arriba de lo autorizado y falta la mitad de la azotea.", "azotea", "coloquial", False),
        ("El electricista pidió que se le pagara extra por cambiar la ruta de la tubería que no venía en planos.", "instalaciones", "directo", False),
        ("Al final la renta de la revolvedora salió por más días de los considerados y se tuvo que pagar la diferencia.", "cimentación", "directo", False),
        ("Hubo que pedir otro viaje de grava porque el primero no alcanzó; no estaba contemplado.", "cimentación", "directo", False),
        ("La tablaroca que eligió el cliente es de una marca más cara y la diferencia la absorbió la obra.", "acabados", "directo", False),
        ("Nos salió carísimo el flete del block, el de siempre no tenía unidad y se contrató otro.", "obra negra", "coloquial", False),
        ("El maestro de obra pide aumento al destajo de aplanados porque dice que el muro viene muy desplomado.", "aplanados", "ambiguo", True),
        ("Se rompieron azulejos en la descarga y hubo que reponer dos cajas, cargo que no estaba previsto.", "acabados", "directo", False),
        ("No alcanzó lo presupuestado para la cancelería; la cotización final llegó 12 mil pesos más alta.", "cancelería", "negacion", False),
        ("Ya se gastó todo lo de la partida de instalaciones hidráulicas y faltan los baños de arriba.", "instalaciones", "directo", False),
        ("El concreto premezclado aumentó por el cargo de bombeo que no venía en la cotización original.", "losa de entrepiso", "directo", False),
        ("Pagamos horas extra a la cuadrilla para sacar el colado el sábado y eso no estaba en el presupuesto.", "losa de azotea", "ambiguo", True),
        ("La pintura vinílica cotizada se descontinuó y la sustituta cuesta bastante más.", "pintura", "directo", False),
        ("Se rentó el andamio otras dos semanas; el gasto acumulado ya rebasa lo que teníamos para equipo.", "fachada", "directo", False),
        ("Me cobraron el retiro de escombro aparte, yo entendía que iba incluido en el precio de la demolición.", "demolición", "coloquial", False),
        ("El tinaco y los accesorios se compraron en la ferretería de la esquina porque urgían y salieron más caros que con el distribuidor.", "instalaciones", "directo", False),
        ("La cuenta de materiales de esta semana va 30 % por encima de lo planeado para la etapa de muros.", "obra negra", "directo", False),
        ("Por indicación del calculista se metió más acero en las trabes y eso subió el costo de la estructura.", "estructura", "ambiguo", False),
        ("No se respetó el precio pactado con el yesero, ahora pide 15 pesos más por metro cuadrado.", "acabados", "negacion", False),
        ("El cliente pidió cambiar a porcelanato cuando el piso cerámico ya estaba comprado y no aceptan devolución.", "pisos", "directo", False),
        ("Estamos pagando renta de bodega porque el material llegó antes de tiempo y no cabe en el terreno.", "obra negra", "contraste", False),
        ("Se acabó el fondo de imprevistos y todavía falta la conexión del drenaje a la red municipal.", "instalaciones", "directo", False),
        ("Reparar la fuga de la cisterna obligó a comprar un impermeabilizante cristalizado que no estaba considerado.", "cisterna", "ambiguo", True),
        ("Que alguien revise la nota del herrero: cobró el portón como lámina calibre 14 y es calibre 18.", "herrería", "coloquial", False),
        ("Este mes las compras de material eléctrico duplicaron lo programado.", "instalaciones", "directo", False),
        ("El ajuste de precio del cemento ya se reflejó en la factura, casi dos mil pesos más por tonelada.", "obra negra", "directo", False),
        ("Se contrató una retroexcavadora para la cisterna porque a mano no se avanzaba, y ese gasto no venía en el presupuesto.", "cisterna", "ambiguo", True),
        ("El presupuesto de acabados ya no da; hay que pedirle autorización al cliente para cubrir la diferencia.", "acabados", "coloquial", False),
    ],
    "Retraso de ejecución": [
        ("La concretera canceló el pedido de las 8 de la mañana y el colado de la losa se reprogramó para el jueves.", "losa de entrepiso", "directo", False),
        ("Hoy sólo llegaron dos de los cinco albañiles y la barda no avanzó lo previsto.", "barda perimetral", "directo", False),
        ("Seguimos esperando la licencia de construcción, no podemos empezar la excavación.", "preliminares", "directo", False),
        ("Llovió toda la tarde y se suspendieron los trabajos de cimentación.", "cimentación", "directo", False),
        ("El herrero no ha entregado las ventanas y ya va dos semanas tarde.", "herrería", "negacion", False),
        ("CFE todavía no conecta el medidor definitivo y no se pueden probar las instalaciones.", "instalaciones", "directo", False),
        ("Vamos atrasados con el aplanado de fachada, a este ritmo no terminamos en la fecha pactada.", "fachada", "directo", False),
        ("El plomero se fue a otra obra y nos dejó a medias la instalación del baño.", "instalaciones", "coloquial", False),
        ("No llegó la bomba para el colado y la cuadrilla estuvo parada medio día.", "losa de azotea", "negacion", False),
        ("Ni ayer ni hoy se presentó el electricista; el cableado sigue igual.", "instalaciones", "negacion", False),
        ("Se detuvo la obra por una inspección del municipio que pidió documentos que el cliente no tenía.", "obra negra", "directo", False),
        ("El cliente no ha definido el modelo de cocina y el carpintero no puede arrancar.", "carpintería", "negacion", False),
        ("Faltan los planos estructurales firmados, así que no se puede cimbrar la losa.", "losa de entrepiso", "directo", False),
        ("La entrega del block se pospuso hasta la otra semana por falta de producción en la bloquera.", "obra negra", "directo", False),
        ("El programa marcaba terminar muros esta semana y apenas vamos a la mitad.", "obra negra", "directo", False),
        ("Por el puente del lunes casi nadie vino a trabajar y se perdió un día completo.", "obra negra", "coloquial", False),
        ("La impermeabilización se pasó para después porque el firme todavía no seca.", "azotea", "directo", False),
        ("Se fue la luz en toda la colonia y no pudimos usar la cortadora ni el rotomartillo.", "acabados", "directo", False),
        ("El proveedor de cancelería dice que el aluminio negro tarda tres semanas más en llegar.", "cancelería", "directo", False),
        ("Llevamos tres días sin agua en la obra; no se puede mezclar ni curar.", "obra negra", "negacion", False),
        ("La revisión del DRO quedó para el próximo martes y mientras tanto no se cuela.", "losa de azotea", "directo", False),
        ("Andamos lentos con los acabados porque la cuadrilla de pintura está incompleta.", "pintura", "coloquial", False),
        ("El terreno salió con mucha roca y la excavación va a tardar más de lo calculado.", "cimentación", "ambiguo", True),
        ("Todavía no llega el tinaco, así que la prueba de la red hidráulica sigue pendiente.", "instalaciones", "directo", False),
        ("Tuvimos que esperar a que el vecino moviera su camioneta para meter la olla y se perdió toda la mañana.", "losa de entrepiso", "coloquial", False),
        ("La fecha de entrega al cliente se recorre al menos dos semanas por el atraso en la estructura.", "estructura", "directo", False),
        ("La cuadrilla se fue a cobrar a otra obra y regresó hasta el miércoles.", "obra negra", "coloquial", False),
        ("La placa de mármol de la barra la están volviendo a cortar porque llegó con otra medida, y eso nos frena la cocina.", "acabados", "ambiguo", True),
        ("El colado no se hizo porque la cimbra no estaba lista.", "losa de entrepiso", "negacion", False),
        ("Seguimos sin poder subir a la azotea porque la administración del condominio no ha autorizado las maniobras.", "azotea", "negacion", False),
    ],
    "Problemas de calidad": [
        ("El aplanado de la recámara principal quedó ondulado, se nota mucho con la luz de la tarde.", "aplanados", "directo", False),
        ("Apareció humedad en el muro del baño; parece que la tubería de agua caliente gotea por dentro.", "instalaciones", "directo", False),
        ("Las losetas del pasillo suenan huecas al pisarlas, no quedaron bien adheridas.", "pisos", "directo", False),
        ("Al descimbrar la columna C-3 aparecieron oquedades en el concreto.", "estructura", "directo", False),
        ("La puerta del baño no cierra porque el marco quedó fuera de escuadra.", "carpintería", "negacion", False),
        ("En la prueba de la red hidráulica bajó la presión; hay una fuga en alguna conexión.", "instalaciones", "directo", False),
        ("Las juntas del azulejo de la cocina quedaron disparejas y con la boquilla manchada.", "acabados", "directo", False),
        ("La pintura de la fachada ya se está descarapelando a tres semanas de aplicada.", "pintura", "directo", False),
        ("El firme de la cochera tiene grietas por todos lados; no se curó como debía.", "pisos", "negacion", False),
        ("Los contactos de la sala no tienen tierra física, el electricista los conectó sólo con dos hilos.", "instalaciones", "ambiguo", True),
        ("El piso terminado quedó dos centímetros más alto que el umbral de la puerta.", "pisos", "directo", False),
        ("La pendiente de la azotea no lleva el agua a la bajada pluvial y se encharca en la esquina.", "azotea", "negacion", False),
        ("El WC quedó mal sellado y sale agua por la base cada vez que le jalas.", "instalaciones", "coloquial", False),
        ("En los castillos se ven las varillas por fuera, quedaron sin recubrimiento suficiente.", "estructura", "directo", False),
        ("El cliente no está conforme con el cemento pulido: tiene manchas y marcas de llana.", "pisos", "negacion", False),
        ("La ventana de la recámara deja pasar agua cuando llueve de lado.", "cancelería", "directo", False),
        ("Los muros de block no están a plomo; en la esquina norte se desvían casi 3 centímetros.", "obra negra", "negacion", False),
        ("No quedó bien la impermeabilización, ya hay goteras en la recámara de arriba.", "azotea", "negacion", False),
        ("En el plafón de tablaroca se marcan todas las juntas, le faltó acabado de pasta.", "acabados", "directo", False),
        ("La regadera tira muy poca agua; al parecer metieron tubería de menor diámetro que el especificado.", "instalaciones", "directo", False),
        ("Colocaron el piso sin respetar el despiece aprobado y quedaron cortes muy chicos junto a la puerta.", "pisos", "negacion", False),
        ("El concreto llegó muy aguado y los cilindros de prueba salieron por debajo de la resistencia de proyecto.", "estructura", "directo", False),
        ("Los cajones de la cocina se atoran y una de las puertas quedó chueca.", "carpintería", "coloquial", False),
        ("Las bisagras de la puerta principal ya están oxidadas y la obra ni siquiera se ha entregado.", "herrería", "directo", False),
        ("Hay fisuras en diagonal en el aplanado de la barda, saliendo de las esquinas de las ventanas.", "aplanados", "directo", False),
        ("El registro sanitario quedó a contrapendiente y el agua se estanca.", "instalaciones", "directo", False),
        ("Mal terminado el zoclo, hay piezas despegadas y sin boquilla.", "acabados", "coloquial", False),
        ("El barandal llegó con soldaduras sin pulir y la pintura escurrida.", "herrería", "directo", False),
        ("Hay que volver a levantar el muro del baño porque no respetaron el espacio de la regadera; eso además pega en el programa.", "obra negra", "ambiguo", True),
        ("Revisando con el cliente, ninguna de las puertas interiores quedó a la misma altura que las demás.", "carpintería", "contraste", False),
    ],
    "Riesgos de seguridad": [
        ("Vi a dos ayudantes trabajando en el borde de la losa sin arnés ni línea de vida.", "losa de azotea", "directo", False),
        ("La escalera de mano que usan para subir al segundo nivel tiene un peldaño roto.", "estructura", "directo", False),
        ("Hay cables pelados conectados directo al tablero provisional y charcos alrededor.", "instalaciones", "directo", False),
        ("Nadie trae casco, ni siquiera mientras izaban la viga.", "estructura", "negacion", False),
        ("La excavación de la cisterna no tiene ademe y la orilla ya se está desmoronando.", "cisterna", "negacion", False),
        ("Dejaron varillas con las puntas expuestas en el paso de los trabajadores.", "cimentación", "directo", False),
        ("El andamio está apoyado sobre ladrillos sueltos y se mueve cuando suben.", "fachada", "directo", False),
        ("Un trabajador se cortó la mano con la cortadora porque no traía guantes.", "acabados", "negacion", False),
        ("Los tanques de gas del soldador están junto a las cubetas de impermeabilizante.", "herrería", "directo", False),
        ("No hay barandal en el cubo de la escalera del segundo piso, cualquiera se puede caer.", "estructura", "negacion", False),
        ("El ayudante usaba la pulidora sin lentes y le saltó una rebaba cerca del ojo.", "herrería", "directo", False),
        ("La barda vieja del colindante está inclinada y estamos excavando justo al pie.", "cimentación", "directo", False),
        ("No hay extintor en la obra y se está soldando todo el día.", "herrería", "negacion", False),
        ("Están subiendo cubetas de mezcla con una cuerda justo por encima de donde pasa la gente.", "obra negra", "directo", False),
        ("Dejaron el hoyo de la fosa séptica destapado toda la noche y sin señalización.", "instalaciones", "directo", False),
        ("Los muchachos se suben a la azotea sin ninguna protección y está lloviendo.", "azotea", "coloquial", False),
        ("El cable de la revolvedora va arrastrando por el agua y tiene cinta de aislar por todos lados.", "obra negra", "directo", False),
        ("Niños de los vecinos se meten a la obra por la parte de atrás porque no hay malla.", "preliminares", "negacion", False),
        ("Nadie revisó la cimbra antes del colado y se veía pandeada en el centro de la losa.", "losa de entrepiso", "ambiguo", True),
        ("El soldador trabaja sin careta, dice que ya está acostumbrado.", "herrería", "coloquial", False),
        ("Hay un puntal flojo debajo de la losa recién colada y la gente pasa por abajo.", "losa de entrepiso", "directo", False),
        ("Huele a gas en la cocina desde que el plomero conectó la estufa.", "instalaciones", "ambiguo", True),
        ("El escombro está apilado en la banqueta y obliga a los peatones a bajarse a la calle.", "demolición", "directo", False),
        ("Sin botas ni casco no deberían entrar, pero los de la yesería siguen llegando en tenis.", "acabados", "negacion", False),
        ("El muro de colindancia se cuarteó después de la excavación y el vecino teme que se caiga.", "cimentación", "ambiguo", True),
        ("La instalación provisional no tiene pastilla térmica y conectan todo a un mismo contacto.", "instalaciones", "negacion", False),
        ("Un ayudante se resbaló en la escalera de la cimbra; sólo fue un raspón, pero no hay pasamanos.", "estructura", "contraste", False),
        ("Se está demoliendo el muro sin apuntalar la trabe que carga encima.", "demolición", "directo", False),
        ("Suben el block con una polea improvisada que no tiene freno.", "obra negra", "coloquial", False),
        ("Algunos trabajadores operan la revolvedora después de haber tomado en la comida.", "obra negra", "directo", False),
    ],
    "Sin incidencia identificada": [
        ("Se terminó el colado de la losa de azotea sin contratiempos y ya se está curando.", "losa de azotea", "directo", False),
        ("Hoy quedó lista la cimentación de los ejes A a C conforme al programa.", "cimentación", "directo", False),
        ("El cliente revisó los acabados de la cocina y quedó satisfecho.", "acabados", "directo", False),
        ("Llegó el material completo y en las cantidades pedidas.", "obra negra", "directo", False),
        ("La prueba hidrostática de la red de agua salió bien, no se detectaron fugas.", "instalaciones", "negacion", False),
        ("Avance de la semana: muros de planta alta al 100 % y castillos colados.", "obra negra", "directo", False),
        ("No hubo faltas esta semana; la cuadrilla completa trabajó de lunes a sábado.", "obra negra", "negacion", False),
        ("Se aplicó el impermeabilizante en la azotea y se probó con agua sin filtraciones.", "azotea", "negacion", False),
        ("Todo en orden con la instalación eléctrica; el electricista entregó el plano de circuitos.", "instalaciones", "coloquial", False),
        ("Se pintó la fachada a dos manos y quedó pareja.", "pintura", "directo", False),
        ("El DRO hizo su visita de supervisión y no dejó observaciones.", "estructura", "negacion", False),
        ("El aplanado de las recámaras quedó a plomo y regla, listo para pintar.", "aplanados", "directo", False),
        ("El piso se compró en la tienda que cotizamos y al precio acordado.", "pisos", "contraste", False),
        ("Ya se instalaron las ventanas de planta baja y quedaron bien selladas.", "cancelería", "directo", False),
        ("El concreto llegó puntual y el colado terminó antes del mediodía.", "losa de entrepiso", "contraste", False),
        ("Sin novedades hoy, se continuó con el tendido de block en la barda.", "barda perimetral", "coloquial", False),
        ("Quedó listo el baño de visitas; probamos regadera, lavabo y WC y todo funciona.", "instalaciones", "directo", False),
        ("El gasto de la semana se mantuvo dentro de lo presupuestado para la estructura.", "estructura", "contraste", False),
        ("Ningún accidente que reportar; todos trabajaron con casco y chaleco.", "obra negra", "negacion", False),
        ("Se limpió la obra y se retiró el escombro acumulado de la semana.", "obra negra", "directo", False),
        ("Se trazó y niveló el terreno; las medidas coinciden con el plano arquitectónico.", "preliminares", "directo", False),
        ("Llegaron los muebles de cocina y se armaron sin problema.", "carpintería", "negacion", False),
        ("La cuadrilla de herrería terminó el portón y ya quedó colgado y pintado.", "herrería", "directo", False),
        ("Vamos un día adelantados en el programa de acabados.", "acabados", "contraste", False),
        ("Hoy se recibieron las facturas del mes y cuadran con las compras registradas.", "administración", "contraste", False),
        ("El curado de la losa se ha hecho diario; mañana se retira la cimbra según lo programado.", "losa de entrepiso", "directo", False),
        ("Pasó la tormenta de anoche y la azotea no presentó ningún encharcamiento.", "azotea", "negacion", False),
        ("Todo tranquilo, se colocaron los registros eléctricos de la planta alta.", "instalaciones", "coloquial", False),
        ("Se entregaron las llaves al cliente y firmó el acta de recepción sin observaciones.", "entrega", "negacion", False),
        ("Ya quedaron los zoclos y se ven bien alineados.", "acabados", "coloquial", False),
    ],
}

CAMPOS = [
    "id_reporte",
    "texto_reporte",
    "categoria_real",
    "origen",
    "fecha_simulada",
    "descripcion_contexto",
    "tipo_redaccion",
    "multiples_incidencias",
    "particion",
]

PREFIJOS = {
    "Sobrecosto": "SOB",
    "Retraso de ejecución": "RET",
    "Problemas de calidad": "CAL",
    "Riesgos de seguridad": "SEG",
    "Sin incidencia identificada": "SIN",
}


def construir_registros(semilla: int = SEMILLA) -> list[dict]:
    """Construye la lista de registros con fechas, contexto y partición reproducibles."""
    rng = random.Random(semilla)
    dias_rango = (FECHA_FIN - FECHA_INICIO).days
    registros: list[dict] = []

    for categoria in CATEGORIAS:
        filas = REPORTES[categoria]
        # Partición estratificada: se eligen 6 índices por clase para exploración
        indices_exploracion = set(rng.sample(range(len(filas)), N_EXPLORACION_POR_CLASE))
        for i, (texto, etapa, tipo, multiples) in enumerate(filas, start=1):
            fecha = FECHA_INICIO + dt.timedelta(days=rng.randint(0, dias_rango))
            tipo_obra = rng.choice(TIPOS_OBRA)
            registros.append(
                {
                    "id_reporte": f"VRK-{PREFIJOS[categoria]}-{i:03d}",
                    "texto_reporte": texto,
                    "categoria_real": categoria,
                    "origen": "sintetico_academico",
                    "fecha_simulada": fecha.isoformat(),
                    "descripcion_contexto": f"Reporte simulado de {tipo_obra}; etapa: {etapa}",
                    "tipo_redaccion": tipo,
                    "multiples_incidencias": multiples,
                    "particion": "exploracion" if (i - 1) in indices_exploracion else "evaluacion",
                }
            )

    # Mezcla final reproducible para que el CSV no quede ordenado por clase
    rng.shuffle(registros)
    return registros


def guardar_csv(registros: list[dict], ruta: Path) -> None:
    """Guarda en CSV UTF-8 sin BOM (formato estándar compatible con pandas y Colab)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(registros)


def main() -> None:
    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Genera el dataset sintético de VOREKO IA")
    parser.add_argument("--salida", type=Path, default=raiz / "data" / "reportes_obra_sinteticos.csv")
    parser.add_argument("--semilla", type=int, default=SEMILLA)
    args = parser.parse_args()

    registros = construir_registros(args.semilla)
    guardar_csv(registros, args.salida)
    print(f"Dataset generado: {args.salida} ({len(registros)} registros, semilla={args.semilla})")


if __name__ == "__main__":
    main()
