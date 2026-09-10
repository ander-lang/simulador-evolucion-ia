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

# TODO: confirmar esta URL una vez completado el deploy en Streamlit Community Cloud.
APP_URL = "https://simulador-evolucion-ia.streamlit.app"

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
    "pepsina", "tripsina", "neutrase", "protamex",
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
        "En 2022, NotCo utilizaba un modelo de IA para **predecir** qué combinaciones de "
        "materia prima y enzima justificaban un ensayo en laboratorio físico, en la búsqueda "
        "de extracción de sabor a carne (MSG) a partir de semillas — minimizando trials costosos."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        materia_prima = st.text_input("Materia Prima (ej. Cucurbita pepo)", key="materia_prima")
    with col_b:
        enzima = st.text_input("Enzima (ej. Alcalase)", key="enzima")

    if st.button("Simular Trial Físico"):
        if not materia_prima.strip() or not enzima.strip():
            st.warning("Completa ambos campos antes de simular el trial.")
        elif not coincide_base_conocimiento(materia_prima, MATERIAS_PRIMAS_VALIDAS) or not coincide_base_conocimiento(
            enzima, ENZIMAS_VALIDAS
        ):
            st.error(
                "El modelo no reconoce esta combinación en su base de conocimiento (semillas y "
                "enzimas de hidrólisis proteica) y descarta el trial sin generar una predicción. "
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

            score = 0.91 if easter_egg else random.uniform(0.10, 0.99)

            st.metric("Trial Score", f"{score:.2f}")

            if easter_egg:
                st.success(
                    "**Batch #3 exitoso.** Esta combinación ya fue validada en laboratorio: "
                    "extracción de MSG confirmada muy por encima del umbral objetivo."
                )
            elif score < 0.75:
                st.error(
                    "El modelo descarta esta mezcla: no justifica montar el ensayo físico.\n\n"
                    "**Ahorro: $1,500 y 2 semanas de trabajo de laboratorio manual**"
                )
            else:
                st.success(
                    "Ensayo aprobado. La predicción de extracción de MSG supera los "
                    "70,000 µg/g y justifica enviar esta mezcla al laboratorio físico."
                )

# ---------------------------------------------------------------------------
# TAB 2 — Hoy: Orquestación de Agentes IA
# ---------------------------------------------------------------------------
with tab2:
    st.markdown(
        "Hoy, ese mismo principio de eliminar el ensayo y error aplica al software: un enjambre "
        "de agentes de IA reemplaza al equipo que antes tardaba meses en levantar un producto. "
        "Cada agente reporta su avance en tiempo real."
    )

    col_c, col_d = st.columns(2)
    with col_c:
        concepto = st.text_input("Concepto de la App (ej. Tinder)", key="concepto")
    with col_d:
        publico = st.text_input("Público Objetivo (ej. Mascotas)", key="publico")

    if st.button("Orquestar Agentes IA"):
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
            seed_from_inputs(concepto, publico)

            dias_tradicional = random.randint(90, 200)
            n_historias = random.randint(6, 14)
            n_colores = random.randint(3, 6)
            n_servicios = random.randint(3, 8)
            base_datos = random.choice(["PostgreSQL", "MongoDB", "PostgreSQL + Redis", "Supabase"])
            n_tests = random.randint(40, 120)

            with st.status("Orquestando agentes de IA...", expanded=True) as pipeline:
                st.write(
                    f"**Agente de Producto** — define {n_historias} historias de usuario "
                    f"priorizadas para {concepto.strip()} orientado a {publico.strip()}."
                )
                time.sleep(0.5)
                st.write(f"**Agente de Diseño** — genera un sistema de diseño con paleta de {n_colores} colores.")
                time.sleep(0.5)
                st.write(
                    f"**Agente de Backend** — levanta una arquitectura de {n_servicios} "
                    f"microservicios sobre {base_datos}."
                )
                time.sleep(0.5)
                st.write(f"**Agente de QA** — ejecuta {n_tests} casos de prueba automatizados, 0 errores críticos.")
                time.sleep(0.5)
                st.write("**Agente de Despliegue** — publica la aplicación en producción.")
                time.sleep(0.4)
                pipeline.update(label="Arquitectura post-nativa lista.", state="complete", expanded=True)

            col_e, col_f = st.columns(2)
            with col_e:
                st.metric("Equipo Tradicional", f"{dias_tradicional} días")
            with col_f:
                st.metric("Orquestación IA", "4 minutos")

            st.info(
                "La IA elimina el ensayo y error. El ingeniero ya no escribe código estático: "
                "orquesta sistemas vivos."
            )
