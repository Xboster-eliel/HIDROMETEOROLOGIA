"""
Módulo 2: Diagnóstico Detallado de Quantile Mapping.
Pestañas internas: Distribuciones (ECDF) | Diagnóstico Q-Q | Parámetros Mensuales | Métricas Completas.
"""

import streamlit as st
import pandas as pd
from ui.theme import inject_custom_css
from ui.charts import plot_ecdf_comparativa, plot_qq_diagnostico
from ui.constants import MESES_COMPLETOS

inject_custom_css()

if "cal" not in st.session_state or "params_qm" not in st.session_state:
    st.warning("⚠️ Cargando datos y calibración...")
    st.stop()

cal = st.session_state["cal"]
params_qm = st.session_state["params_qm"]
metricas_df = st.session_state["metricas_df"]
metadata = st.session_state["metadata"]

st.markdown("### ◉ Diagnóstico Estadístico y Curvas de Distribución")
st.caption(f"Análisis detallado de la transformación cuantil a cuantil para {metadata['modelo_nombre']} frente a {metadata['estacion_nombre']}.")

tabs = st.tabs([
    "Curvas ECDF",
    "Diagnóstico Q-Q",
    "Parámetros Calibrados",
    "Tabla Completa de Métricas"
])

# ---------------------------------------------------------
# Tab 1: Distribuciones (ECDF)
# ---------------------------------------------------------
with tabs[0]:
    col_c1, col_c2 = st.columns([2, 1])
    with col_c1:
        opciones_mes = ["Todos los meses (Periodo completo)"] + MESES_COMPLETOS
        mes_sel = st.selectbox("Filtrar por mes estacional:", opciones_mes, index=0)
    with col_c2:
        st.write("")
        st.write("")
        escala_log = st.checkbox("Escala logarítmica (eje X)", value=False)

    mes_num = None if mes_sel.startswith("Todos") else MESES_COMPLETOS.index(mes_sel) + 1
    fig_ecdf = plot_ecdf_comparativa(cal, mes=mes_num, log_scale=escala_log)
    st.plotly_chart(fig_ecdf, use_container_width=True)

# ---------------------------------------------------------
# Tab 2: Diagnóstico Q-Q
# ---------------------------------------------------------
with tabs[1]:
    st.markdown("##### Comparativa de Cuantiles vs Recta 1:1")
    st.caption("Una aproximación estrecha a la línea punteada 1:1 indica que los sesgos de distribución fueron resueltos.")
    
    n_pts = st.slider("Resolución de cuantiles evaluados:", min_value=50, max_value=200, value=100, step=10)
    fig_qq = plot_qq_diagnostico(cal, n_points=n_pts)
    st.plotly_chart(fig_qq, use_container_width=True)

# ---------------------------------------------------------
# Tab 3: Parámetros Mensuales
# ---------------------------------------------------------
with tabs[2]:
    st.markdown("##### Umbrales y Fracciones Secas Calibradas por Mes")
    st.caption("Evolución estacional de la probabilidad seca observada y el umbral correspondiente estimado en el modelo:")

    tabla_param = pd.DataFrame([
        {
            "Mes": m,
            "P(seco) observado": p["p_seco_obs"],
            "Umbral modelo (mm/d)": p["umbral_mod"],
            "Máx. modelo húmedo (mm/d)": p["mod_q"][-1],
            "Máx. observado húmedo (mm/d)": p["obs_q"][-1],
            "Días húmedos obs": p["n_obs_hum"],
            "Días húmedos modelo": p["n_mod_hum"],
        }
        for m, p in params_qm.items()
    ])
    st.dataframe(
        tabla_param.style.format({
            "P(seco) observado": "{:.3f}",
            "Umbral modelo (mm/d)": "{:.4f}",
            "Máx. modelo húmedo (mm/d)": "{:.2f}",
            "Máx. observado húmedo (mm/d)": "{:.2f}",
        }),
        use_container_width=True,
        hide_index=True
    )

# ---------------------------------------------------------
# Tab 4: Tabla Completa de Métricas
# ---------------------------------------------------------
with tabs[3]:
    st.markdown("##### Estadísticas Hidrometeorológicas y Errores Residuales")
    st.dataframe(
        metricas_df.style.format({
            "Media (mm/d)": "{:.3f}",
            "Mediana (mm/d)": "{:.3f}",
            "P95 (mm/d)": "{:.2f}",
            "P99 (mm/d)": "{:.2f}",
            "Máximo (mm/d)": "{:.1f}",
            "Frecuencia húmeda (%)": "{:.1f}%",
            "Frecuencia seca (%)": "{:.1f}%",
            "Sesgo relativo Media (%)": "{:+.2f}%",
            "RMSE (mm/d)": "{:.2f}",
            "MAE (mm/d)": "{:.2f}",
        }),
        use_container_width=True,
        hide_index=True
    )
