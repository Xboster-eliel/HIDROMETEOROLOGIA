"""
Página principal / Portada ejecutiva del Dashboard: Resumen del Desempeño Científico.
Responde de inmediato a la pregunta: ¿Cuánto mejoró la corrección de sesgo el modelo climático?
"""

import streamlit as st
from ui.theme import inject_custom_css
from ui.cards import render_scientific_header, render_scientific_kpis, render_extreme_diagnostics_table
from ui.charts import plot_comparativa_principal, plot_sesgo_mensual
from qm_core import tabla_metricas_comparativas

inject_custom_css()

# Validar que los datos estén cargados en session_state
if "cal" not in st.session_state or "metricas_df" not in st.session_state:
    st.warning("⚠️ Cargando datos y calibración...")
    st.stop()

cal = st.session_state["cal"]
metricas_df = st.session_state["metricas_df"]
metadata = st.session_state["metadata"]
modelo_todo = st.session_state["modelo_todo"]

# ---------------------------------------------------------
# 1. Encabezado Científico Riguroso
# ---------------------------------------------------------
render_scientific_header(
    modelo_nombre=metadata["modelo_nombre"],
    estacion_nombre=metadata["estacion_nombre"],
    cal_inicio=metadata["cal_inicio"],
    cal_fin=metadata["cal_fin"]
)

# ---------------------------------------------------------
# 2. Fila de 5 KPIs Científicos de Desempeño
# ---------------------------------------------------------
row_obs = metricas_df.loc[metricas_df["Serie"] == "Observado (Estación)"].iloc[0]
row_raw = metricas_df.loc[metricas_df["Serie"] == "Modelo Bruto (GCM)"].iloc[0]
row_qm  = metricas_df.loc[metricas_df["Serie"] == "Modelo Corregido QM"].iloc[0]

cal_ini = int(metadata["cal_inicio"])
cal_fin = int(metadata["cal_fin"])
fuera_mask = modelo_todo["fuera_soporte"]
n_fuera = int(fuera_mask.sum())
pct_fuera = (n_fuera / len(modelo_todo)) * 100.0

n_pre = int((fuera_mask & (modelo_todo["fecha"].dt.year < cal_ini)).sum())
n_cal = int((fuera_mask & modelo_todo["fecha"].dt.year.between(cal_ini, cal_fin)).sum())
n_post = int((fuera_mask & (modelo_todo["fecha"].dt.year > cal_fin)).sum())
subtexto_extrap = f"{n_post} posteriores a {cal_fin} · {n_pre} anteriores a {cal_ini} · {n_cal} durante calibración"

render_scientific_kpis(
    bias_raw=float(row_raw["Sesgo relativo Media (%)"]),
    bias_qm=float(row_qm["Sesgo relativo Media (%)"]),
    wet_obs=float(row_obs["Frecuencia húmeda (%)"]),
    wet_raw=float(row_raw["Frecuencia húmeda (%)"]),
    wet_qm=float(row_qm["Frecuencia húmeda (%)"]),
    extrap_count=n_fuera,
    extrap_pct=pct_fuera,
    extrap_subtexto=subtexto_extrap,
    media_obs=float(row_obs["Media (mm/d)"]),
    media_raw=float(row_raw["Media (mm/d)"]),
    media_qm=float(row_qm["Media (mm/d)"]),
    cal_inicio=cal_ini,
    cal_fin=cal_fin,
)

banner_cal = (
    '<div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px 14px; margin: 12px 0 16px 0; display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; color: #334155;">'
    f'<span>🎯 <strong>Periodo de Calibración Activo:</strong> {cal_ini}–{cal_fin} ({len(cal):,} días evaluados · 12 modelos mensuales EQM)</span>'
    '<span style="color: #64748B; font-size: 0.80rem;">⚙️ Modificable en tiempo real desde la barra lateral</span>'
    '</div>'
)
if hasattr(st, "html"):
    st.html(banner_cal)
else:
    st.markdown(banner_cal, unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. Bloque Gráfico Dual: Serie Comparativa y Sesgo Mensual
# ---------------------------------------------------------
col_g1, col_g2 = st.columns([1.1, 0.9])

with col_g1:
    st.markdown("##### 🌧️ Precipitación Diaria y Métricas de Error Embebidas")
    st.caption("Serie temporal calibrada con tarjeta técnica de error integrada dentro del lienzo de Plotly:")

    anios_cal = sorted(cal["fecha"].dt.year.unique())
    modo_zoom = st.radio(
        "Ventana de inspección diaria:",
        options=["Todo el periodo", "Primeros 5 años", "Primeros 10 años", "Rango personalizado"],
        index=2 if len(anios_cal) >= 10 else 0,
        horizontal=True,
        key="res_modo_zoom"
    )

    if modo_zoom == "Todo el periodo":
        y_ini, y_fin = anios_cal[0], anios_cal[-1]
    elif modo_zoom == "Primeros 5 años":
        y_ini, y_fin = anios_cal[0], min(anios_cal[0] + 4, anios_cal[-1])
    elif modo_zoom == "Primeros 10 años":
        y_ini, y_fin = anios_cal[0], min(anios_cal[0] + 9, anios_cal[-1])
    else:
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            y_ini = st.selectbox("Año inicial:", anios_cal, index=0, key="res_y_ini_custom")
        with col_s2:
            y_fin_def_idx = len(anios_cal) - 1 if len(anios_cal) < 10 else 9
            y_fin = st.selectbox("Año final:", anios_cal, index=y_fin_def_idx, key="res_y_fin_custom")

    if y_ini > y_fin:
        st.error("El año inicial no puede ser mayor que el año final.")
        y_ini, y_fin = anios_cal[0], anios_cal[-1]
        fig_main = plot_comparativa_principal(cal)
    else:
        fig_main = plot_comparativa_principal(cal, anio_inicio=y_ini, anio_fin=y_fin, mostrar_metricas=True)

    st.plotly_chart(fig_main, use_container_width=True)

with col_g2:
    st.markdown("##### 📊 Reducción del Sesgo Estacional por Mes")
    st.caption("Muestra cómo la función empírica eliminó los sesgos relativos estacionales en los 12 meses:")
    fig_sesgo = plot_sesgo_mensual(cal)
    st.plotly_chart(fig_sesgo, use_container_width=True)

    # Texto explicativo, ecuación formal y desglose de sesgo relativo estacional
    st.markdown("###### 📘 Formulación del Sesgo Estacional Relativo")
    st.caption("Ecuación aplicada de forma independiente a cada mes m ∈ {Ene, Feb, ..., Dic}:")
    st.latex(r"\text{Bias}_m (\%) = \left( \frac{\bar{P}_{m, \mathrm{mod}} - \bar{P}_{m, \mathrm{obs}}}{\bar{P}_{m, \mathrm{obs}}} \right) \times 100\%")

    desglose_sesgo_html = (
        '<div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 12px; margin-top: 6px; font-size: 0.79rem; color: #334155; line-height: 1.45;">'
        '<div style="font-weight: 600; color: #163A5F; margin-bottom: 4px;">'
        '🔍 Desglose de variables y qué dice la ecuación:'
        '</div>'
        '<div style="color: #475569;">'
        '• <strong>P&#772;<sub>m, mod</sub>:</strong> Precipitación media diaria del mes <em>m</em> para el modelo (GCM Bruto o Modelo QM).<br>'
        '• <strong>P&#772;<sub>m, obs</sub>:</strong> Precipitación media diaria observada en la estación meteorológica en el mes <em>m</em>.<br>'
        '• <strong>Bias<sub>m</sub> &gt; 0%:</strong> <em>Sobreestimación sistemática</em> del volumen de lluvia en ese mes.<br>'
        '• <strong>Bias<sub>m</sub> &lt; 0%:</strong> <em>Subestimación sistemática</em> (el modelo simula un déficit volumétrico estacional).<br>'
        '• <strong>Bias<sub>m</sub> &approx; 0%:</strong> <em>Corrección volumétrica completa</em>; la calibración empírica mensual (EQM) elimina las barras de sesgo y alinea cada mes con el régimen hidrológico real de la cuenca.'
        '</div>'
        '</div>'
    )
    if hasattr(st, "html"):
        st.html(desglose_sesgo_html)
    else:
        st.markdown(desglose_sesgo_html, unsafe_allow_html=True)

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. Diagnóstico General del Ajuste e Índices de Extremos
# ---------------------------------------------------------
es_subperiodo = (y_ini != anios_cal[0]) or (y_fin != anios_cal[-1])

col_t1, col_t2 = st.columns([0.58, 0.42])
with col_t1:
    st.markdown("##### 🎯 Evaluación y Semáforo de Desempeño Hidrometeorológico")
with col_t2:
    if es_subperiodo:
        modo_eval = st.radio(
            "Muestra evaluada en la tabla:",
            options=[f"Ventana activa ({y_ini}–{y_fin})", f"Periodo completo ({cal_ini}–{cal_fin})"],
            index=0,
            horizontal=True,
            key="res_modo_eval_tabla"
        )
    else:
        modo_eval = f"Periodo completo ({cal_ini}–{cal_fin})"

if es_subperiodo and modo_eval.startswith("Ventana activa"):
    cal_eval = cal.loc[cal["fecha"].dt.year.between(y_ini, y_fin)]
    metricas_eval = tabla_metricas_comparativas(
        cal_eval["obs_mm"].to_numpy(),
        cal_eval["modelo_mm"].to_numpy(),
        cal_eval["qm_mm"].to_numpy(),
        wet_threshold=float(metadata.get("wet_thresh", 0.1))
    )
    periodo_eval_str = f"Ventana activa {y_ini}–{y_fin}"
    dias_eval_str = f"{len(cal_eval):,} días"
    banner_tabla = (
        '<div style="font-size: 0.82rem; color: #15803D; background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 6px; padding: 6px 12px; margin: 4px 0 10px 0;">'
        f'⚡ <strong>Sincronización en tiempo real activa:</strong> Evaluando <strong>{len(cal_eval):,} días</strong> de la ventana visible (<strong>{y_ini}–{y_fin}</strong>). '
        '<span style="color: #475569;">Los semáforos, sesgos, KGE y RMSE corresponden exactamente al tramo inspeccionado.</span>'
        '</div>'
    )
else:
    cal_eval = cal
    metricas_eval = metricas_df
    periodo_eval_str = f"Periodo completo {cal_ini}–{cal_fin}"
    dias_eval_str = f"{len(cal):,} días"
    banner_tabla = (
        '<div style="font-size: 0.82rem; color: #1E40AF; background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 6px 12px; margin: 4px 0 10px 0;">'
        f'📊 <strong>Climatología de referencia:</strong> Evaluando <strong>{len(cal):,} días</strong> del periodo de calibración completo (<strong>{cal_ini}–{cal_fin}</strong>).'
        '</div>'
    )

if hasattr(st, "html"):
    st.html(banner_tabla)
else:
    st.markdown(banner_tabla, unsafe_allow_html=True)

render_extreme_diagnostics_table(metricas_eval)

# Diagnóstico de síntesis 100% dinámico con la muestra evaluada
row_raw_ev = metricas_eval.loc[metricas_eval["Serie"] == "Modelo Bruto (GCM)"].iloc[0]
row_qm_ev = metricas_eval.loc[metricas_eval["Serie"] == "Modelo Corregido QM"].iloc[0]
row_obs_ev = metricas_eval.loc[metricas_eval["Serie"] == "Observado (Estación)"].iloc[0]

b_raw_ev = float(row_raw_ev["Sesgo relativo Media (%)"])
b_qm_ev = float(row_qm_ev["Sesgo relativo Media (%)"])
f_seca_obs_ev = float(row_obs_ev["Frecuencia seca (%)"])
f_seca_qm_ev = float(row_qm_ev["Frecuencia seca (%)"])

with st.expander(f"📌 Síntesis diagnóstica de la corrección ({periodo_eval_str})"):
    st.markdown(
        f"""
        - **Media y Volumen Total ({periodo_eval_str}):** El sesgo medio relativo en la muestra evaluada se redujo de **{b_raw_ev:+.2f}% a {b_qm_ev:+.2f}%**, alcanzando correspondencia volumétrica frente a la estación pluviométrica.
        - **Frecuencia Seco/Húmedo:** Frecuencia de días secos observados vs corregidos: **{f_seca_obs_ev:.1f}% obs vs {f_seca_qm_ev:.1f}% QM** (eliminación del exceso de llovizna).
        - **Colas y Extremos:** Percentiles P95 y P99 calculados sobre los {dias_eval_str} de la muestra evaluada. En la proyección histórica completa (1950–2100) se detectaron **{n_fuera} eventos** fuera del soporte histórico del modelo ({n_post} posteriores a {cal_fin}).
        """
    )
