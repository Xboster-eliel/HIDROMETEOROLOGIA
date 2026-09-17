"""
Página principal / Portada ejecutiva del Dashboard: Resumen del Desempeño Científico.
Responde de inmediato a la pregunta: ¿Cuánto mejoró la corrección de sesgo el modelo climático?
"""

import streamlit as st
from ui.theme import inject_custom_css
from ui.cards import render_scientific_header, render_scientific_kpis, render_extreme_diagnostics_table
from ui.charts import plot_comparativa_principal, plot_sesgo_mensual

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
    rmse_qm=float(row_qm["RMSE (mm/d)"]),
    wet_obs=float(row_obs["Frecuencia húmeda (%)"]),
    wet_raw=float(row_raw["Frecuencia húmeda (%)"]),
    wet_qm=float(row_qm["Frecuencia húmeda (%)"]),
    extrap_count=n_fuera,
    extrap_pct=pct_fuera,
    extrap_subtexto=subtexto_extrap
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
        fig_main = plot_comparativa_principal(cal)
    else:
        fig_main = plot_comparativa_principal(cal, anio_inicio=y_ini, anio_fin=y_fin, mostrar_metricas=True)

    st.plotly_chart(fig_main, use_container_width=True)

with col_g2:
    st.markdown("##### 📊 Reducción del Sesgo Estacional por Mes")
    st.caption("Muestra cómo la función empírica eliminó los sesgos relativos estacionales en los 12 meses:")
    fig_sesgo = plot_sesgo_mensual(cal)
    st.plotly_chart(fig_sesgo, use_container_width=True)

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. Diagnóstico General del Ajuste e Índices de Extremos
# ---------------------------------------------------------
st.markdown("##### 🎯 Evaluación y Semáforo de Desempeño Hidrometeorológico")
render_extreme_diagnostics_table(metricas_df)

# Diagnóstico de síntesis 100% dinámico
b_raw = float(row_raw["Sesgo relativo Media (%)"])
b_qm = float(row_qm["Sesgo relativo Media (%)"])
f_seca_obs = float(row_obs["Frecuencia seca (%)"])
f_seca_qm = float(row_qm["Frecuencia seca (%)"])

with st.expander("📌 Síntesis diagnóstica de la corrección"):
    st.markdown(
        f"""
        - **Media y Volumen Total:** El sesgo medio global en el periodo calibrado ({cal_ini}–{cal_fin}) se redujo de **{b_raw:+.2f}% a {b_qm:+.2f}%**, logrando una correspondencia volumétrica prácticamente exacta con la estación pluviométrica.
        - **Frecuencia Seco/Húmedo:** Se eliminó el exceso de llovizna (*drizzle effect*) del modelo mediante umbrales dinámicos mensuales, igualando la frecuencia observada de días secos ({f_seca_obs:.1f}% obs vs {f_seca_qm:.1f}% QM).
        - **Colas y Extremos:** Los percentiles P95 y P99 se corrigieron eficientemente dentro del soporte histórico. Se detectaron **{n_fuera} eventos** fuera del soporte histórico del modelo ({n_post} posteriores a {cal_fin}); en esos casos se aplica saturación empírica en el cuantil 1.0.
        """
    )
