"""
Módulo 4: Marco Metodológico, Ejemplo Pedagógico y Descarga de Datos.
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from ui.theme import inject_custom_css, apply_plotly_theme
from ui.constants import COLOR_RAW, COLOR_OBS, COLOR_QM
from qm_core import ejecutar_ejemplo_pedagogico

inject_custom_css()

if "cal" not in st.session_state or "modelo_todo" not in st.session_state:
    st.warning("⚠️ Cargando datos y calibración...")
    st.stop()

cal = st.session_state["cal"]
params_qm = st.session_state["params_qm"]
modelo_todo = st.session_state["modelo_todo"]
metricas_df = st.session_state["metricas_df"]

st.markdown("### ▤ Metodología, Ejemplo Pedagógico y Exportación")

tabs = st.tabs([
    "🧪 Ejemplo Pedagógico Interactivo",
    "📚 Respuestas Metodológicas",
    "📥 Descarga de Datos",
    "📖 Referencias Bibliográficas"
])

# ---------------------------------------------------------
# Tab 1: Ejemplo Pedagógico Interactivo
# ---------------------------------------------------------
with tabs[0]:
    st.markdown("##### Mecánica Cuantil a Cuantil Paso a Paso")
    st.markdown(
        r"""
        Para cualquier valor simulado $X_m$, se evalúa su posición cuantílica empírica $p = F_m(X_m)$ 
        y se sustituye por el valor observado que ocupa esa misma probabilidad acumulada $F_o^{-1}(p)$:
        """
    )
    st.latex(r"X_{\mathrm{QM}} = F_o^{-1}\left(F_m(X_m)\right)")

    col_p1, col_p2 = st.columns([1, 1.6])
    with col_p1:
        txt_m = st.text_input("Serie Modelo (mm):", "2, 5, 8, 12, 15, 20, 25, 30, 40, 50")
        txt_o = st.text_input("Serie Observada (mm):", "1, 4, 7, 10, 14, 18, 28, 35, 48, 65")
        try:
            arr_m = np.array([float(x.strip()) for x in txt_m.split(",")])
            arr_o = np.array([float(x.strip()) for x in txt_o.split(",")])
            tabla_ej, sesgo_ej = ejecutar_ejemplo_pedagogico(arr_m, arr_o)
            st.dataframe(tabla_ej, hide_index=True, use_container_width=True)
        except Exception as e:
            st.error(f"Error en datos: {e}")
            arr_m, arr_o = None, None

    with col_p2:
        if arr_m is not None and arr_o is not None:
            fig_ej = go.Figure()
            idx = np.arange(1, len(arr_m) + 1)
            fig_ej.add_trace(go.Scatter(x=idx, y=arr_m, mode="lines+markers", name="Modelo Original", line=dict(color=COLOR_RAW, width=1.8), marker=dict(size=7)))
            fig_ej.add_trace(go.Scatter(x=idx, y=arr_o, mode="lines+markers", name="Observado", line=dict(color=COLOR_OBS, width=1.8), marker=dict(size=7)))
            fig_ej.add_trace(go.Scatter(x=idx, y=tabla_ej["QM corregido Xqm (mm)"], mode="lines+markers", name="Modelo QM", line=dict(color=COLOR_QM, width=2.2, dash="dot"), marker=dict(size=7)))
            fig_ej = apply_plotly_theme(fig_ej, title="Transformación Cuantil a Cuantil", x_title="Índice de muestra", y_title="Precipitación (mm)", height=320)
            st.plotly_chart(fig_ej, use_container_width=True)

# ---------------------------------------------------------
# Tab 2: Respuestas Metodológicas
# ---------------------------------------------------------
with tabs[1]:
    with st.expander("1. ¿Qué es Quantile Mapping y qué sesgos corrige?", expanded=True):
        st.markdown(
            """
            Es un método de postprocesamiento estadístico no paramétrico que alinea las funciones acumuladas de distribución (CDF).
            **Lo que sí corrige:** Media, mediana, variabilidad, frecuencia de días secos/húmedos y cuantiles altos.
            **Lo que no garantiza:** No corrige la correlación temporal diaria, no genera variabilidad espacial subgrid ni asegura preservar la señal de cambio climático futuro.
            """
        )
    with st.expander("2. ¿Por qué el tratamiento de días secos es fundamental?", expanded=True):
        st.markdown(
            """
            Los modelos climáticos presentan *drizzle effect* (demasiados días con lluvia muy baja). Si se aplica QM directamente, se sobreestima la lluvia o se alteran las probabilidades. La solución consiste en fijar el umbral del modelo al cuantil de la frecuencia seca observada.
            """
        )
    with st.expander("3. Distinción entre corrección de sesgo y downscaling espacial"):
        st.markdown(
            """
            Maraun (2013) demostró que cuando la escala del GCM (celdas de ~100 km) difiere sustancialmente de la escala de estación puntual, aplicar QM puede generar problemas de *inflación* en la variabilidad y distorsionar extremos. Por ello, se recomienda catalogar este método como **ajuste de sesgo de distribución marginal** y no como downscaling dinámico o estocástico completo.
            """
        )
    with st.expander("4. Recomendación para proyecciones de cambio climático: QDM"):
        st.markdown(
            """
            Cannon et al. (2015) demostraron que el QM clásico altera las tendencias relativas simuladas de precipitación en el futuro. Para estudios de impacto que utilicen escenarios SSP, se aconseja **Quantile Delta Mapping (QDM)** para preservar de manera explícita los cambios proyectados en los cuantiles.
            """
        )

# ---------------------------------------------------------
# Tab 3: Descarga de Datos
# ---------------------------------------------------------
with tabs[2]:
    st.markdown("##### Exportación de Resultados en Formato CSV")

    c_d1, c_d2, c_d3 = st.columns(3)
    with c_d1:
        csv_serie = modelo_todo[[
            "fecha", "modelo", "pr_mm_dia", "pr_qm_mm_dia", "fuera_soporte", "periodo"
        ]].to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📄 Serie Corregida Completa (1950–2100)",
            data=csv_serie,
            file_name="precipitacion_QM_corregida_1950_2100.csv",
            mime="text/csv",
            use_container_width=True
        )

    with c_d2:
        params_df = pd.DataFrame([
            {
                "mes": m,
                "p_seco_obs": p["p_seco_obs"],
                "umbral_mod_mm": p["umbral_mod"],
                "max_mod_cal_mm": p["mod_q"][-1],
                "max_obs_cal_mm": p["obs_q"][-1],
            }
            for m, p in params_qm.items()
        ]).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⚙️ Parámetros Mensuales Calibrados",
            data=params_df,
            file_name="parametros_calibracion_qm.csv",
            mime="text/csv",
            use_container_width=True
        )

    with c_d3:
        metricas_csv = metricas_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📊 Métricas Estadísticas de Desempeño",
            data=metricas_csv,
            file_name="metricas_desempeno_qm.csv",
            mime="text/csv",
            use_container_width=True
        )

# ---------------------------------------------------------
# Tab 4: Bibliografía
# ---------------------------------------------------------
with tabs[3]:
    st.markdown(
        """
        - **Cannon, A. J., Sobie, S. R., & Murdock, T. Q. (2015).** Bias correction of GCM precipitation by quantile mapping: How well do methods preserve changes in quantiles and extremes? *Journal of Climate, 28*(17), 6938–6959. [https://doi.org/10.1175/JCLI-D-14-00754.1](https://doi.org/10.1175/JCLI-D-14-00754.1)
        - **Gudmundsson, L., Bremnes, J. B., Haugen, J. E., & Engen-Skaugen, T. (2012).** Technical Note: Downscaling RCM precipitation to the station scale using statistical transformations – a comparison of methods. *Hydrology and Earth System Sciences, 16*, 3383–3390. [https://doi.org/10.5194/hess-16-3383-2012](https://doi.org/10.5194/hess-16-3383-2012)
        - **Maraun, D. (2013).** Bias correction, quantile mapping, and downscaling: Revisiting the inflation issue. *Journal of Climate, 26*(6), 2137–2143. [https://doi.org/10.1175/JCLI-D-12-00821.1](https://doi.org/10.1175/JCLI-D-12-00821.1)
        - **Themeßl, M. J., Gobiet, A., & Leuprecht, A. (2011).** Empirical-statistical downscaling and error correction of daily precipitation from regional climate models. *International Journal of Climatology, 31*(10), 1530–1544. [https://doi.org/10.1002/joc.2168](https://doi.org/10.1002/joc.2168)
        """
    )
