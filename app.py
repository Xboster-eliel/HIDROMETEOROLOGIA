"""
Router principal y orquestador del Dashboard de Hidrometeorología.
Utiliza st.navigation y st.Page para una arquitectura multipágina limpia, moderna y desacoplada.
"""

import streamlit as st
import numpy as np
import pandas as pd
from pathlib import Path

from qm_core import (
    cargar_datos_qm,
    preparar_periodo_calibracion,
    fit_eqm_mensual,
    apply_eqm_mensual,
    tabla_metricas_comparativas,
)

# ---------------------------------------------------------
# Configuración inicial global
# ---------------------------------------------------------
st.set_page_config(
    page_title="Hidrometeorología | Quantile Mapping",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# Funciones cacheadas de lectura y procesamiento
# ---------------------------------------------------------
@st.cache_data(show_spinner="Leyendo base de datos...")
def get_data(archivo_subido=None):
    if archivo_subido is not None:
        return cargar_datos_qm(archivo_subido, nombre_archivo=archivo_subido.name)
    candidatos = [
        Path("data QM.csv"),
        Path(__file__).parent / "data QM.csv",
        Path("data Quantil Mapping.ods"),
        Path(__file__).parent / "data Quantil Mapping.ods",
    ]
    for p in candidatos:
        if p.exists():
            return cargar_datos_qm(p)
    raise FileNotFoundError("No se encontró el archivo 'data QM.csv' ni se subió ningún archivo.")


@st.cache_data(show_spinner="Calibrando Quantile Mapping...")
def calibrar_y_procesar(modelo_df, obs_df, start_year, end_year, wet_thresh, n_q):
    f_inicio = pd.Timestamp(f"{start_year}-01-01")
    f_fin = pd.Timestamp(f"{end_year}-12-31")

    cal = preparar_periodo_calibracion(modelo_df, obs_df, f_inicio, f_fin)
    if len(cal) < 100:
        raise ValueError("Periodo de calibración con datos insuficientes.")

    params = fit_eqm_mensual(cal, wet_threshold=wet_thresh, n_quantiles=n_q)
    qm_cal, fuera_cal = apply_eqm_mensual(cal["fecha"], cal["modelo_mm"], params)
    cal["qm_mm"] = qm_cal
    cal["fuera_soporte"] = fuera_cal

    # Aplicar a la serie completa del modelo (1950-2100)
    qm_todo, fuera_todo = apply_eqm_mensual(modelo_df["fecha"], modelo_df["pr_mm_dia"], params)
    modelo_todo = modelo_df.copy()
    modelo_todo["pr_qm_mm_dia"] = qm_todo
    modelo_todo["fuera_soporte"] = fuera_todo
    modelo_todo["periodo"] = np.where(modelo_todo["fecha"] <= f_fin, "Referencia_Histórica", "Proyección_Futura")

    # Tabla comparativa de métricas
    metricas = tabla_metricas_comparativas(
        cal["obs_mm"].to_numpy(),
        cal["modelo_mm"].to_numpy(),
        cal["qm_mm"].to_numpy(),
        wet_threshold=wet_thresh
    )

    metadata = {
        "modelo_nombre": str(modelo_df["modelo"].dropna().iloc[0]),
        "estacion_nombre": str(obs_df["estacion"].dropna().iloc[0]),
        "cal_inicio": start_year,
        "cal_fin": end_year,
        "wet_thresh": wet_thresh,
        "n_quantiles": n_q,
    }

    return cal, params, modelo_todo, metricas, metadata


# ---------------------------------------------------------
# Barra Lateral: Identidad y Parámetros Globales
# ---------------------------------------------------------
with st.sidebar:
    # Marca tipográfica sobria (sin imágenes externas genéricas)
    st.markdown(
        """
        <div style="padding: 6px 0 14px 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 16px;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #163A5F; letter-spacing: -0.01em;">
                🌧️ HIDROMETEOROLOGÍA
            </div>
            <div style="font-size: 0.78rem; color: #64748B; margin-top: 2px;">
                Quantile Mapping · Precipitación Diaria
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("##### ⚙️ Parámetros de Calibración")

    # Carga de datos
    opcion_datos = st.radio(
        "Fuente de datos:",
        ["data QM.csv (Local)", "Subir archivo (CSV/ODS)"],
        index=0,
        label_visibility="collapsed"
    )
    archivo_usuario = None
    if opcion_datos == "Subir archivo (CSV/ODS)":
        archivo_usuario = st.file_uploader("Subir dataset", type=["csv", "ods"])

    try:
        modelo, observado = get_data(archivo_usuario)
        datos_ok = True
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        datos_ok = False

    if datos_ok:
        min_yr = int(max(modelo["fecha"].min().year, observado["fecha"].min().year))
        max_yr = int(min(modelo["fecha"].max().year, observado["fecha"].max().year))

        def_start = max(min_yr, 1959)
        def_end = min(max_yr, 2014)

        cal_range = st.slider(
            "Periodo de referencia:",
            min_value=min_yr,
            max_value=max_yr,
            value=(def_start, def_end),
            help="Periodo común para calcular las distribuciones acumuladas."
        )

        wet_thresh = st.number_input(
            "Umbral húmedo (mm/d):",
            min_value=0.0,
            max_value=5.0,
            value=0.10,
            step=0.05,
            help="Valores menores se consideran días secos."
        )

        n_quantiles = st.select_slider(
            "Cuantiles evaluados:",
            options=[201, 501, 1001, 2001],
            value=1001,
            help="Resolución de la función cuantil empírica."
        )

        st.caption(f"ℹ️ Referencia histórica CMIP6 recomendada: 1959–2014.")

if not datos_ok:
    st.stop()

# Ejecución y almacenamiento centralizado en session_state
cal, params_qm, modelo_todo, metricas_df, metadata = calibrar_y_procesar(
    modelo, observado, cal_range[0], cal_range[1], wet_thresh, n_quantiles
)

st.session_state["cal"] = cal
st.session_state["params_qm"] = params_qm
st.session_state["modelo_todo"] = modelo_todo
st.session_state["metricas_df"] = metricas_df
st.session_state["metadata"] = metadata

# ---------------------------------------------------------
# Navegación Multipágina con st.navigation y st.Page
# ---------------------------------------------------------
resumen_page = st.Page("pages/resumen.py", title="Resumen", icon="📊", default=True)
diagnostico_page = st.Page("pages/diagnostico.py", title="Diagnóstico QM", icon="📈")
clima_page = st.Page("pages/clima.py", title="Climatología y Clima Futuro", icon="🌧️")
metodologia_page = st.Page("pages/metodologia.py", title="Metodología y Exportación", icon="📚")

pg = st.navigation({
    "Navegación": [resumen_page, diagnostico_page, clima_page, metodologia_page]
})


pg.run()
