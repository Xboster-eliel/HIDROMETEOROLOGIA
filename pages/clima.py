"""
Módulo 3: Climatología y Comportamiento Temporal del Modelo (1950–2100).
Incluye ciclo anual con selector de variable y análisis en doble escala temporal.
"""

import streamlit as st
import plotly.graph_objects as go
from ui.theme import inject_custom_css
from ui.charts import plot_climatologia_variable, plot_serie_multidecadal
from ui.constants import COLOR_RAW, COLOR_OBS, COLOR_QM
from ui.theme import apply_plotly_theme

inject_custom_css()

if "cal" not in st.session_state or "modelo_todo" not in st.session_state:
    st.warning("⚠️ Cargando datos y calibración...")
    st.stop()

cal = st.session_state["cal"]
modelo_todo = st.session_state["modelo_todo"]
metadata = st.session_state["metadata"]

st.markdown("### ▥ Climatología Estacional y Señal Temporal del Modelo")
st.caption(f"Evaluación del ciclo anual multivariable y comportamiento multidecadal (1950–2100) · 🎯 <strong>Periodo Calibrado: {metadata['cal_inicio']}–{metadata['cal_fin']}</strong>.", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. Ciclo Anual Multivariable
# ---------------------------------------------------------
st.markdown("#### 🌧️ Ciclo Anual Medio")

col_v1, col_v2 = st.columns([1.5, 2.5])
with col_v1:
    var_sel = st.selectbox(
        "Variable climatológica a evaluar:",
        options=[
            ("acumulado", "Precipitación acumulada mensual (mm/mes)"),
            ("media", "Precipitación media diaria (mm/d)"),
            ("dias_humedos", "Frecuencia de días húmedos (%)"),
            ("p95", "Lluvias intensas - Percentil 95 (mm/d)"),
            ("p99", "Extremos - Percentil 99 (mm/d)"),
        ],
        format_func=lambda opt: opt[1],
        index=0
    )

fig_clim = plot_climatologia_variable(cal, variable_tipo=var_sel[0], wet_thresh=metadata.get("wet_thresh", 0.1))
st.plotly_chart(fig_clim, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# 2. Doble Escala Temporal: Contexto Climático (1950–2100) y Detalle
# ---------------------------------------------------------
st.markdown("#### 🔮 Periodo Histórico y Aplicación Futura del Modelo (1950–2100)")

st.info(
    """
    ⚠️ **Rigor de Escenario y Cambio Climático:**
    - El archivo suministrado contiene simulación hasta 2100 para `MPI-ESM1-2-HR`, pero **no especifica la etiqueta del escenario SSP** (ej. SSP1-2.6, SSP2-4.5 o SSP5-8.5). Por ello, el tramo futuro debe entenderse como ejercicio computacional demostrativo.
    - El Quantile Mapping clásico puede alterar la señal de cambio climático de los extremos. Para proyecciones formales, se recomienda **Quantile Delta Mapping (QDM)** (Cannon et al., 2015).
    """
)

# Gráfico 1: Contexto Anual Multidecadal
fig_multi = plot_serie_multidecadal(
    modelo_todo,
    cal_fin_year=metadata["cal_fin"],
    cal_inicio_year=metadata["cal_inicio"]
)
st.plotly_chart(fig_multi, use_container_width=True)

# Gráfico 2: Detalle Diario por Año
st.markdown("##### 🔍 Inspección Diaria a Escala Anual")
anios_todos = sorted(modelo_todo["fecha"].dt.year.unique())
anio_sel = st.selectbox("Seleccionar año a inspeccionar:", anios_todos, index=anios_todos.index(2010) if 2010 in anios_todos else 0)

sub_anio = modelo_todo.loc[modelo_todo["fecha"].dt.year == anio_sel]

# Buscar observaciones (primero en cal, y si no en observado_full si está disponible)
obs_sub_anio = None
if anio_sel in cal["fecha"].dt.year.values:
    obs_sub_anio = cal.loc[cal["fecha"].dt.year == anio_sel]
elif "observado_full" in st.session_state:
    obs_full = st.session_state["observado_full"]
    if anio_sel in obs_full["fecha"].dt.year.values:
        obs_sub_anio = obs_full.loc[obs_full["fecha"].dt.year == anio_sel].rename(columns={"pr_mm_dia": "obs_mm"})

fig_dia = go.Figure()
fig_dia.add_trace(go.Scatter(
    x=sub_anio["fecha"], y=sub_anio["pr_mm_dia"],
    mode="lines", name="Modelo Bruto", line=dict(color=COLOR_RAW, width=1.4)
))
if obs_sub_anio is not None and not obs_sub_anio.empty:
    fig_dia.add_trace(go.Scatter(
        x=obs_sub_anio["fecha"], y=obs_sub_anio["obs_mm"],
        mode="lines", name="Observado (Estación)", line=dict(color=COLOR_OBS, width=1.5)
    ))
fig_dia.add_trace(go.Scatter(
    x=sub_anio["fecha"], y=sub_anio["pr_qm_mm_dia"],
    mode="lines", name="Modelo Corregido QM", line=dict(color=COLOR_QM, width=1.8)
))

# Marcar si hubo extrapolación en ese año
fuera_anio = sub_anio.loc[sub_anio["fuera_soporte"]]
if not fuera_anio.empty:
    fig_dia.add_trace(go.Scatter(
        x=fuera_anio["fecha"], y=fuera_anio["pr_qm_mm_dia"],
        mode="markers", name="Fuera de Soporte (> Máx Histórico)",
        marker=dict(color="#D97706", size=8, symbol="triangle-up")
    ))

fig_dia = apply_plotly_theme(
    fig_dia,
    title=f"Serie de Precipitación Diaria en el Año {anio_sel}",
    x_title="Fecha",
    y_title="Precipitación diaria (mm/d)",
    height=360
)
st.plotly_chart(fig_dia, use_container_width=True)
