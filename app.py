"""
Simulador de Evolución — dinámica en vivo para conferencia universitaria de IA.

Toda la "Inteligencia Artificial" es simulada localmente: no hay llamadas a
APIs externas. Los textos que escribe el usuario se normalizan y se usan
como semilla de `random`, así la misma entrada produce siempre el mismo
resultado (ilusión de modelo determinista).
"""

import difflib
import os
import random
import re
import time

import qrcode
import streamlit as st

st.set_page_config(page_title="Simulador de Evolución", layout="centered")

LOGO_PATH = os.path.join(os.path.dirname(__file__), "bculinary_logo.png")

APP_URL = "https://bcc-app.streamlit.app"

# Tipografía institucional (Oswald), acorde a la identidad de Basque Culinary Center.
# Streamlit fija font-family con reglas de mayor especificidad (".st-emotion-cache-xxx h1", etc.),
# así que hace falta !important para que la fuente importada gane sobre el default "Source Sans".
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@300;400;500;600&display=swap');

    html, body,
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] *,
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *,
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] *,
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] *,
    [data-testid="stMetricDelta"], [data-testid="stMetricDelta"] *,
    [data-testid^="stAlertContent"], [data-testid^="stAlertContent"] *,
    [data-testid="stTextInputRootElement"] input,
    [data-testid="stStatusWidget"], [data-testid="stStatusWidget"] *,
    label, label *,
    .stTabs [data-baseweb="tab"] p,
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Oswald', sans-serif !important;
    }
    div.stButton > button {
        border-radius: 4px;
        font-family: 'Oswald', sans-serif !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def seed_from_inputs(*textos: str) -> None:
    """Siembra el generador aleatorio con los textos del usuario (minúsculas, sin espacios)."""
    semilla = "".join(t.lower().replace(" ", "") for t in textos)
    random.seed(semilla)


def es_entrada_valida(texto: str) -> bool:
    """
    Filtro de sanidad local (sin IA real ni APIs externas): rechaza texto que no
    tiene forma de palabra reconocible, para que el "modelo" no le dé una respuesta
    con apariencia científica a cualquier entrada sin sentido.
    """
    t = texto.strip()
    if len(t) < 3:
        return False
    if not re.fullmatch(r"[A-Za-zÀ-ÿ\s.'-]+", t):
        return False
    if not re.search(r"[aeiouAEIOUÀ-ÿ]", t):
        return False
    letras = re.sub(r"[^a-zA-ZÀ-ÿ]", "", t.lower())
    if letras and len(set(letras)) / len(letras) < 0.35:
        return False
    return True


# Base de conocimiento cerrada para el Tab 1: "parece una palabra" (es_entrada_valida) no alcanza,
# porque dos palabras reales pero sin relación (ej. "banana" + "amor") también la pasarían y el
# modelo igual devolvería un resultado con apariencia científica. Solo semillas y enzimas reales
# de hidrólisis proteica cuentan como reconocidas; se admite tolerancia a errores de tipeo.
MATERIAS_PRIMAS_VALIDAS = [
    "cucurbita pepo", "calabaza", "zapallo",
    "glycine max", "soja", "soya",
    "pisum sativum", "arveja", "guisante",
    "cicer arietinum", "garbanzo",
    "lens culinaris", "lenteja",
    "helianthus annuus", "girasol",
    "triticum aestivum", "trigo",
    "zea mays", "maiz", "maíz",
    "avena sativa", "avena",
    "phaseolus vulgaris", "poroto", "frijol", "frejol",
    "chenopodium quinoa", "quinoa",
    "salvia hispanica", "chia", "chía",
    "lupinus albus", "lupino", "altramuz",
]

ENZIMAS_VALIDAS = [
    "alcalase", "flavourzyme", "bromelina", "papaina", "papaína",
    "pepsina", "tripsina", "neutrase", "protamex", "protana uboost",
    "quimotripsina", "subtilisina",
]


def coincide_base_conocimiento(texto: str, base: list[str]) -> bool:
    """Compara contra la base cerrada, con tolerancia a typos (no requiere match exacto)."""
    t = texto.strip().lower()
    if t in base:
        return True
    return bool(difflib.get_close_matches(t, base, n=1, cutoff=0.82))


# Misma lógica que en el Tab 1: "Público Objetivo" es un dominio acotado (segmentos de
# audiencia reales), así que se valida contra una base cerrada en vez del chequeo liviano.
# "Concepto de la App" queda con es_entrada_valida porque, a propósito, admite cualquier idea
# de producto — restringirlo a una lista cerrada rompería el punto de la dinámica.
PUBLICOS_VALIDOS = [
    "mascotas", "perros", "gatos",
    "ninos", "niños", "adolescentes", "jovenes", "jóvenes", "universitarios", "estudiantes",
    "adultos mayores", "ancianos", "jubilados",
    "familias", "padres", "madres",
    "deportistas", "runners", "ciclistas", "gamers",
    "emprendedores", "freelancers", "profesionales", "empresas", "pymes", "startups",
    "turistas", "viajeros",
    "musicos", "músicos", "artistas", "fotografos", "fotógrafos", "disenadores", "diseñadores",
    "programadores", "ingenieros", "cientificos", "científicos", "investigadores",
    "profesores", "docentes", "maestros",
    "medicos", "médicos", "enfermeros", "pacientes",
    "agricultores", "chefs", "cocineros",
    "vegetarianos", "veganos",
    "comerciantes", "vendedores", "consumidores", "clientes", "usuarios",
]


def coincide_publico_objetivo(texto: str) -> bool:
    """
    Igual que coincide_base_conocimiento, pero también acepta coincidencias parciales
    (ej. "amantes de los perros") porque las audiencias suelen describirse con frases cortas.
    """
    t = texto.strip().lower()
    palabras = re.findall(r"[a-záéíóúñ]+", t)
    return any(coincide_base_conocimiento(p, PUBLICOS_VALIDOS) for p in palabras) or coincide_base_conocimiento(
        t, PUBLICOS_VALIDOS
    )


# Trayectoria real del TFG de Ander (Basque Culinary Center / NotCo, 2023): el trial score del
# Toolbox AI subió 0.40 -> 0.60 -> ~0.78 a lo largo de 3 batches iterativos. Solo se activa con
# el easter egg exacto; el resto de combinaciones válidas usa una trayectoria ficticia (abajo).
TRAYECTORIA_REAL_TFG = [
    {
        "titulo": "Batch 1 — Exploración inicial",
        "score": 0.40,
        "lectura": "mejor lectura cruda ≈ 68 mg/g",
        "insight": "Resultados dispersos: el equipo identifica que la enzima es la variable que más pesa.",
    },
    {
        "titulo": "Batch 2 — La enzima como palanca",
        "score": 0.60,
        "lectura": "mejora sostenida en las muestras evaluadas",
        "insight": "Se maximiza la dosis de enzima y se varía el tiempo de activación: el trial score sube de 0.40 a 0.60.",
    },
    {
        "titulo": "Batch 3 — Validación",
        "score": 0.78,
        "lectura": "mejor muestra B3E0 ≈ 73 (mg/g, tal como consta en el registro original — el objetivo del proyecto era 80,000 µg/g)",
        "insight": "El toolbox logró optimizar el proceso con una tendencia positiva y progresiva.",
    },
]

INSIGHTS_EXPLORACION = [
    "Resultados dispersos: todavía no hay una variable dominante clara.",
    "Primeras corridas erráticas, útiles para acotar el rango de búsqueda.",
    "El modelo identifica candidatos prometedores entre el ruido inicial.",
]
INSIGHTS_PALANCA = [
    "Se aísla la variable que más pesa y se ajusta su dosis.",
    "El modelo prioriza la variable de mayor impacto y descarta el resto del ruido.",
    "Ajustando la variable clave, el trial score empieza a subir con claridad.",
]
INSIGHTS_CONVERGENCIA = [
    "Ajuste fino final: la curva se estabiliza cerca del objetivo.",
    "La tendencia se vuelve positiva y progresiva, lista para el ensayo físico.",
    "El modelo converge a una combinación que justifica el trial físico.",
]


def generar_trayectoria_ficticia(materia_prima: str, enzima: str) -> list[dict]:
    """Trayectoria de 3 batches, seedeada, que siempre converge a un score aprobatorio."""
    score1 = random.uniform(0.25, 0.45)
    score2 = min(score1 + random.uniform(0.15, 0.30), 0.94)
    score3 = min(max(score2 + random.uniform(0.10, 0.25), 0.75), 0.97)
    lecturas = [random.randint(15, 40), random.randint(45, 65), random.randint(68, 82)]
    return [
        {
            "titulo": "Batch 1 — Exploración inicial",
            "score": score1,
            "lectura": f"mejor lectura cruda ≈ {lecturas[0]} mg/g",
            "insight": random.choice(INSIGHTS_EXPLORACION),
        },
        {
            "titulo": "Batch 2 — Se aísla la palanca",
            "score": score2,
            "lectura": f"mejor lectura cruda ≈ {lecturas[1]} mg/g",
            "insight": random.choice(INSIGHTS_PALANCA),
        },
        {
            "titulo": "Batch 3 — Validación",
            "score": score3,
            "lectura": f"mejor lectura cruda ≈ {lecturas[2]} mg/g",
            "insight": random.choice(INSIGHTS_CONVERGENCIA),
        },
    ]


def generar_trayectoria_batches(materia_prima: str, enzima: str, easter_egg: bool) -> list[dict]:
    if easter_egg:
        return TRAYECTORIA_REAL_TFG
    return generar_trayectoria_ficticia(materia_prima, enzima)


# Datos para el Tab 2: "Base de datos" pasa de ser aleatoria a ser una elección del usuario.
BASES_DE_DATOS = ["PostgreSQL", "MongoDB", "PostgreSQL + Redis", "Supabase"]


def generar_pipeline_ia(concepto: str, publico: str, stack: str, db: str) -> list[str]:
    n_historias = random.randint(6, 14)
    n_colores = random.randint(3, 6)
    n_servicios = random.randint(3, 8)
    n_tests = random.randint(40, 120)
    n_unidades = random.randint(5, 12)
    unidad = "pantallas" if stack == "Mobile-first" else "páginas"
    return [
        f"**Agente de Producto** — define {n_historias} historias de usuario priorizadas para "
        f"{concepto.strip()} orientado a {publico.strip()}.",
        f"**Agente de Diseño** — genera un sistema de diseño {stack.lower()} con {n_unidades} "
        f"{unidad} y paleta de {n_colores} colores.",
        f"**Agente de Backend** — levanta una arquitectura de {n_servicios} microservicios sobre {db}.",
        f"**Agente de QA** — ejecuta {n_tests} casos de prueba automatizados, 0 errores críticos.",
        "**Agente de Despliegue** — publica la aplicación en producción.",
    ]


def generar_cronograma_tradicional(concepto: str, publico: str) -> list[str]:
    return [
        "Semana 1 — Kickoff y relevamiento de requisitos.",
        f"Semana 3 — Primer mockup de {concepto.strip()} para {publico.strip()}.",
        "Semana 6 — Backend inicial, todavía sin integrar con el frontend.",
        "Mes 2 — Primeras pruebas manuales; aparecen bugs de integración.",
        "Mes 3 — Sigue en desarrollo.",
    ]


st.image(LOGO_PATH, width=110)
st.title("Simulador de Evolución")
st.caption("Del ensayo físico en el laboratorio a la orquestación de sistemas por IA.")

with st.expander("Abrí esta app en tu celular", expanded=True):
    col_qr, col_link = st.columns([1, 2])
    with col_qr:
        qr_img = qrcode.make(APP_URL, border=2).convert("RGB")
        st.image(qr_img, width=160)
    with col_link:
        st.markdown(f"**{APP_URL}**")
        st.caption("Escaneá el código o entrá al link para seguir la dinámica desde tu teléfono.")

tab1, tab2 = st.tabs(["2022 — Lab NotCo", "Hoy — Orquestación de Agentes IA"])

# ---------------------------------------------------------------------------
# TAB 1 — 2022: Lab NotCo
# ---------------------------------------------------------------------------
with tab1:
    st.markdown(
        "En 2022, un barrido manual de todas las combinaciones posibles de materia prima, enzima, "
        "tiempo y dosis habría exigido **756 experimentos físicos**. El Toolbox AI de NotCo redujo "
        "esa búsqueda a **3 batches iterativos** de entre 5 y 10 ensayos cada uno, con el trial "
        "score subiendo batch a batch."
    )
    st.caption("Uno de estos batches terminó publicado en una revista científica — seguí la dinámica para descubrir cuál.")

    col_a, col_b = st.columns(2)
    with col_a:
        materia_prima = st.text_input("Materia Prima (ej. Cucurbita pepo)", key="materia_prima")
    with col_b:
        enzima = st.text_input("Enzima (ej. Alcalase)", key="enzima")

    if st.button("Iniciar optimización iterativa"):
        if not materia_prima.strip() or not enzima.strip():
            st.warning("Completa ambos campos antes de iniciar la optimización.")
        elif not coincide_base_conocimiento(materia_prima, MATERIAS_PRIMAS_VALIDAS) or not coincide_base_conocimiento(
            enzima, ENZIMAS_VALIDAS
        ):
            st.error(
                "El modelo no reconoce esta combinación en su base de conocimiento (semillas y "
                "enzimas de hidrólisis proteica) y descarta la optimización sin generar batches. "
                "Probá con un ejemplo real, como Cucurbita pepo + Alcalase."
            )
        else:
            seed_from_inputs(materia_prima, enzima)

            materia_norm = materia_prima.strip().lower()
            enzima_norm = enzima.strip().lower()
            easter_egg = materia_norm == "cucurbita pepo" and enzima_norm in (
                "alcalase",
                "flavourzyme",
            )

            batches = generar_trayectoria_batches(materia_prima, enzima, easter_egg)

            score_anterior = None
            for batch in batches:
                with st.container(border=True):
                    st.markdown(f"**{batch['titulo']}**")
                    delta = None if score_anterior is None else round(batch["score"] - score_anterior, 2)
                    st.metric("Trial Score", f"{batch['score']:.2f}", delta=delta)
                    st.caption(batch["lectura"])
                    st.write(batch["insight"])
                score_anterior = batch["score"]
                time.sleep(0.9)

            st.line_chart({"Trial Score": [b["score"] for b in batches]})

            score_final = batches[-1]["score"]
            if score_final >= 0.75:
                st.success(
                    "Ensayo aprobado. Tres batches bastaron para superar el umbral que hacía "
                    "justificable enviar la mezcla al laboratorio físico."
                )
            else:
                st.error(
                    "El modelo descarta esta mezcla tras 3 batches: no justifica montar el ensayo "
                    "físico.\n\n**Ahorro: $1,500 y 2 semanas de trabajo de laboratorio manual**"
                )

            if easter_egg:
                st.success(
                    "**Este es el batch real.** El trabajo continuó y se publicó como "
                    "*\"A metabolomic approach of AI-driven enzymatic digestion of pumpkin seed "
                    "flour for producing umami metabolites\"*, International Journal of Gastronomy "
                    "and Food Science, vol. 39 (marzo 2025), con Ander de la Hoz como primer autor. "
                    "El paper publicado usó enzimas refinadas distintas a las de estos batches de 2023."
                )

# ---------------------------------------------------------------------------
# TAB 2 — Hoy: Orquestación de Agentes IA
# ---------------------------------------------------------------------------
with tab2:
    st.markdown(
        "Ese mismo principio de comprimir la iteración, en vez de eliminarla, aplica hoy al "
        "software: mientras un equipo tradicional avanza hito a hito, un enjambre de agentes de "
        "IA construye la misma app en paralelo — y termina primero."
    )

    with st.form("orquestacion_form"):
        col_c, col_d = st.columns(2)
        with col_c:
            concepto = st.text_input("Concepto de la App (ej. Tinder)", key="concepto")
        with col_d:
            publico = st.text_input("Público Objetivo (ej. Mascotas)", key="publico")

        col_g, col_h = st.columns(2)
        with col_g:
            stack_choice = st.radio("Enfoque", ["Web-first", "Mobile-first"], key="stack_choice")
        with col_h:
            db_choice = st.selectbox("Base de datos", BASES_DE_DATOS, key="db_choice")

        enviado = st.form_submit_button("Lanzar orquestación")

    if enviado:
        if not concepto.strip() or not publico.strip():
            st.warning("Completa ambos campos antes de orquestar los agentes.")
        elif not es_entrada_valida(concepto):
            st.error(
                "El modelo no reconoce esta entrada como un concepto de producto válido y "
                "detiene la orquestación antes de asignar agentes."
            )
        elif not coincide_publico_objetivo(publico):
            st.error(
                "El modelo no reconoce este público objetivo en su base de segmentos de "
                "audiencia y detiene la orquestación antes de asignar agentes. "
                "Probá con un ejemplo real, como Mascotas o Estudiantes."
            )
        else:
            seed_from_inputs(concepto, publico, stack_choice, db_choice)

            dias_tradicional = random.randint(90, 200)
            cronograma = generar_cronograma_tradicional(concepto, publico)
            pipeline = generar_pipeline_ia(concepto, publico, stack_choice, db_choice)

            col_trad, col_ia = st.columns(2)
            with col_trad:
                st.markdown("**Equipo Tradicional**")
                placeholder_trad = st.empty()
            with col_ia:
                st.markdown("**Orquestación IA**")
                placeholder_ia = st.empty()

            lineas_trad: list[str] = []
            lineas_ia: list[str] = []
            for frame in range(1, 9):
                if frame % 2 == 0 and len(lineas_trad) < len(cronograma) - 1:
                    lineas_trad.append(cronograma[len(lineas_trad)])
                    placeholder_trad.markdown("\n\n".join(lineas_trad) + "\n\n*(en progreso…)*")
                if len(lineas_ia) < len(pipeline):
                    lineas_ia.append(pipeline[len(lineas_ia)])
                    cierre = "\n\n**Listo.**" if len(lineas_ia) == len(pipeline) else ""
                    placeholder_ia.markdown("\n\n".join(lineas_ia) + cierre)
                time.sleep(0.35)

            col_e, col_f = st.columns(2)
            with col_e:
                st.metric("Equipo Tradicional", f"{dias_tradicional} días")
            with col_f:
                st.metric("Orquestación IA", "4 minutos")

            st.info(
                "La IA elimina el ensayo y error. El ingeniero ya no escribe código estático: "
                "orquesta sistemas vivos."
            )
