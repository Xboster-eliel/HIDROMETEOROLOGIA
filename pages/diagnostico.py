"""
Módulo 2: Diagnóstico Detallado de Quantile Mapping.
Pestañas internas: Distribuciones (ECDF) | Diagnóstico Q-Q | Parámetros Mensuales | Métricas Completas.
Completamente sincronizado en tiempo real con la ventana de inspección y periodo de calibración activo.
"""

import streamlit as st
import pandas as pd
from ui.theme import inject_custom_css
from ui.charts import plot_ecdf_comparativa, plot_qq_diagnostico
from ui.constants import MESES_COMPLETOS
from qm_core import tabla_metricas_comparativas

inject_custom_css()

if "cal" not in st.session_state or "params_qm" not in st.session_state:
    st.warning("⚠️ Cargando datos y calibración...")
    st.stop()

cal = st.session_state["cal"]
params_qm = st.session_state["params_qm"]
metricas_df = st.session_state["metricas_df"]
metadata = st.session_state["metadata"]
anios_cal = sorted(cal["fecha"].dt.year.unique())

# ---------------------------------------------------------
# Control de Ventana Dinámica de Diagnóstico (Sincronizado con Resumen)
# ---------------------------------------------------------
opciones_zoom = ["Todo el periodo", "Primeros 5 años", "Primeros 10 años", "Rango personalizado"]
modo_prev = st.session_state.get("inspection_mode", "Primeros 10 años" if len(anios_cal) >= 10 else "Todo el periodo")
idx_def = opciones_zoom.index(modo_prev) if modo_prev in opciones_zoom else (2 if len(anios_cal) >= 10 else 0)

col_head1, col_head2 = st.columns([0.52, 0.48])
with col_head1:
    st.markdown("### ◉ Diagnóstico Estadístico y Curvas de Distribución")
    st.caption(f"Análisis detallado de la transformación cuantil a cuantil para **{metadata['modelo_nombre']}** frente a **{metadata['estacion_nombre']}**.")
with col_head2:
    modo_zoom_diag = st.radio(
        "Ventana de análisis de distribución:",
        options=opciones_zoom,
        index=idx_def,
        horizontal=True,
        key="diag_modo_zoom"
    )

if modo_zoom_diag == "Todo el periodo":
    y_ini, y_fin = anios_cal[0], anios_cal[-1]
elif modo_zoom_diag == "Primeros 5 años":
    y_ini, y_fin = anios_cal[0], min(anios_cal[0] + 4, anios_cal[-1])
elif modo_zoom_diag == "Primeros 10 años":
    y_ini, y_fin = anios_cal[0], min(anios_cal[0] + 9, anios_cal[-1])
else:
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        prev_ini = st.session_state.get("inspection_range", (anios_cal[0], anios_cal[-1]))[0]
        ini_idx = anios_cal.index(prev_ini) if prev_ini in anios_cal else 0
        y_ini = st.selectbox("Año inicial:", anios_cal, index=ini_idx, key="diag_y_ini_custom")
    with col_s2:
        prev_fin = st.session_state.get("inspection_range", (anios_cal[0], anios_cal[-1]))[1]
        fin_idx = anios_cal.index(prev_fin) if prev_fin in anios_cal else (len(anios_cal) - 1 if len(anios_cal) < 10 else 9)
        y_fin = st.selectbox("Año final:", anios_cal, index=fin_idx, key="diag_y_fin_custom")

if y_ini > y_fin:
    st.error("El año inicial no puede ser mayor que el año final.")
    y_ini, y_fin = anios_cal[0], anios_cal[-1]

# Sincronizar en session_state para que Resumen y Diagnóstico compartan la selección
st.session_state["inspection_range"] = (y_ini, y_fin)
st.session_state["inspection_mode"] = modo_zoom_diag

es_sub = (y_ini != anios_cal[0]) or (y_fin != anios_cal[-1])
cal_activa = cal.loc[cal["fecha"].dt.year.between(y_ini, y_fin)]

if es_sub:
    banner_diag = (
        '<div style="font-size: 0.83rem; color: #15803D; background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 6px; padding: 7px 14px; margin: 4px 0 14px 0; display: flex; justify-content: space-between; align-items: center;">'
        f'<span>⚡ <strong>Ventana Dinámica Activa:</strong> {y_ini}–{y_fin} ({len(cal_activa):,} días evaluados) · <em>Figuras ECDF, Q-Q y métricas sincronizadas en tiempo real</em></span>'
        f'<span style="color: #475569; font-size: 0.79rem;">Calibración base: {metadata["cal_inicio"]}–{metadata["cal_fin"]}</span>'
        '</div>'
    )
else:
    banner_diag = (
        '<div style="font-size: 0.83rem; color: #1E40AF; background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 7px 14px; margin: 4px 0 14px 0; display: flex; justify-content: space-between; align-items: center;">'
        f'<span>📊 <strong>Periodo Completo de Calibración:</strong> {metadata["cal_inicio"]}–{metadata["cal_fin"]} ({len(cal):,} días evaluados · 12 modelos mensuales EQM)</span>'
        '<span style="color: #64748B; font-size: 0.79rem;">⚙️ Sincronizado en tiempo real</span>'
        '</div>'
    )

if hasattr(st, "html"):
    st.html(banner_diag)
else:
    st.markdown(banner_diag, unsafe_allow_html=True)

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
        opciones_mes = [f"Todos los meses ({y_ini}–{y_fin})"] + MESES_COMPLETOS
        mes_sel = st.selectbox("Filtrar por mes estacional:", opciones_mes, index=0)
    with col_c2:
        st.write("")
        st.write("")
        escala_log = st.checkbox("Escala logarítmica (eje X)", value=False)

    mes_num = None if mes_sel.startswith("Todos") else MESES_COMPLETOS.index(mes_sel) + 1
    fig_ecdf = plot_ecdf_comparativa(cal_activa, mes=mes_num, log_scale=escala_log)
    st.plotly_chart(fig_ecdf, use_container_width=True)

# ---------------------------------------------------------
# Tab 2: Diagnóstico Q-Q
# ---------------------------------------------------------
with tabs[1]:
    st.markdown(f"##### Comparativa de Cuantiles vs Recta 1:1 ({y_ini}–{y_fin})")
    st.caption(f"Alineación cuantil-cuantil calculada sobre los {len(cal_activa):,} días de la muestra activa ({y_ini}–{y_fin}):")
    
    n_pts = st.slider("Resolución de cuantiles evaluados:", min_value=50, max_value=200, value=100, step=10)
    fig_qq = plot_qq_diagnostico(cal_activa, n_points=n_pts)
    st.plotly_chart(fig_qq, use_container_width=True)

    # ---------------------------------------------------------
    # Panel Pedagógico: Fundamento Estadístico del Gráfico Q-Q
    # ---------------------------------------------------------
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    st.markdown("###### 📘 Fundamento Estadístico e Interpretación del Gráfico Q-Q")
    st.caption("Alineación cuantil-cuantil y ausencia de unidades físicas en los ejes:")

    st.latex(r"Q(p) = F^{-1}(p) = \inf \left\{ x \in \mathbb{R} : F(x) \ge p \right\}, \quad p \in (0, 1)")

    html_exp_qq = (
        '<div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px 16px; margin-top: 10px; font-size: 0.81rem; color: #334155; line-height: 1.55;">'
        '<div style="font-weight: 700; color: #163A5F; font-size: 0.88rem; margin-bottom: 8px;">'
        '🔍 ¿Por qué los ejes no llevan unidades físicas (mm/día) y cómo se interpreta este gráfico?'
        '</div>'

        '<div style="margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #E2E8F0;">'
        '• <strong>Naturaleza Adimensional de los Ejes de Cuantiles:</strong><br>'
        '<span style="color: #475569;">'
        'Un gráfico Cuantil-Cuantil (Q-Q) contrasta directamente las funciones inversas de distribución acumulada '
        '(<em>Q<sub>sim</sub>(p)</em> frente a <em>Q<sub>obs</sub>(p)</em>) evaluadas en idénticos percentiles de probabilidad <em>p &isin; (0, 1)</em>. '
        'En la literatura estadística rigurosa, los ejes representan posiciones relativas de probabilidad o valores estandarizados (Z-scores / cuantiles empíricos), '
        'omitiendo unidades físicas directas (como mm/día) para reflejar que se está evaluando la equivalencia morfológica de las distribuciones '
        'y no mediciones dimensionales independientes.'
        '</span>'
        '</div>'

        '<div style="margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #E2E8F0;">'
        '• <strong>Línea Diagonal 1:1 (Identidad Distribucional):</strong><br>'
        '<span style="color: #475569;">'
        'La línea discontinua <em>y = x</em> constituye la referencia teórica perfecta: si la distribución simulada fuese idéntica a la observada '
        'en todos sus órdenes (media, varianza, asimetría y colas extremas), los puntos deben alinearse estrictamente sobre ella.'
        '</span>'
        '</div>'

        '<div>'
        '• <strong>Diagnóstico Comparativo de Desempeño:</strong><br>'
        '<span style="color: #475569;">'
        '<strong>GCM Bruto (rojo):</strong> Cae por debajo de la recta 1:1 en los cuantiles moderados y altos, demostrando la subestimación '
        'volumétrica sistemática del modelo global sin calibrar.<br>'
        '<strong>Modelo QM (verde):</strong> Se superpone de forma estricta sobre la diagonal 1:1 en toda la longitud del soporte, '
        'confirmando que la transformación empírica restituyó con éxito tanto la ocurrencia como las magnitudes extremas observadas.'
        '</span>'
        '</div>'

        '</div>'
    )
    if hasattr(st, "html"):
        st.html(html_exp_qq)
    else:
        st.markdown(html_exp_qq, unsafe_allow_html=True)

# ---------------------------------------------------------
# Tab 3: Parámetros Mensuales
# ---------------------------------------------------------
with tabs[2]:
    st.markdown("##### Umbrales y Fracciones Secas Calibradas por Mes")
    st.caption(f"Parámetros empíricos ajustados en la calibración base ({metadata['cal_inicio']}–{metadata['cal_fin']}) y ocurrencia observada vs QM en la muestra activa ({y_ini}–{y_fin}):")

    tabla_param = pd.DataFrame([
        {
            "Mes": m,
            "P(seco) observado": p["p_seco_obs"],
            "Umbral modelo (mm/d)": p["umbral_mod"],
            "Máx. modelo húmedo (mm/d)": p["mod_q"][-1],
            "Máx. observado húmedo (mm/d)": p["obs_q"][-1],
            f"Días húmedos obs ({y_ini}–{y_fin})": int((cal_activa.loc[cal_activa["mes"] == m, "obs_mm"] >= metadata.get("wet_thresh", 0.1)).sum()),
            f"Días húmedos QM ({y_ini}–{y_fin})": int((cal_activa.loc[cal_activa["mes"] == m, "qm_mm"] >= metadata.get("wet_thresh", 0.1)).sum()),
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
    # Panel Pedagógico: Explicación e Interpretación de Parámetros Calibrados
    # ---------------------------------------------------------
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown("###### 📘 Formulación e Interpretación de los Parámetros Calibrados")
    st.caption("Ecuaciones aplicadas por el algoritmo Empirical Quantile Mapping (EQM) para separar días secos y húmedos:")

    st.latex(r"P(\text{seco})_{\mathrm{obs}, m} = \frac{1}{N_m} \sum_{t=1}^{N_m} \mathbb{I}\left(P_{\mathrm{obs}, m}(t) < 0.10\,\mathrm{mm/d}\right)")
    st.latex(r"x_{\mathrm{th, mod}, m} = F_{m, \mathrm{mod}}^{-1}\left( P(\text{seco})_{\mathrm{obs}, m} \right)")

    explicacion_param_html = (
        '<div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px 16px; margin-top: 10px; font-size: 0.81rem; color: #334155; line-height: 1.55;">'
        '<div style="font-weight: 700; color: #163A5F; font-size: 0.88rem; margin-bottom: 8px;">'
        '🔍 ¿Cómo se calcula cada parámetro, qué significa y cómo se interpreta?'
        '</div>'

        '<div style="margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #E2E8F0;">'
        '• <strong>P(seco) observado (Fracción seca):</strong><br>'
        '<span style="color: #475569;">'
        '<strong>¿Cómo se calcula?</strong> Es la proporción empírica de días del mes <em>m</em> en los que la estación pluviométrica registró precipitación inferior a 0.10 mm/d (umbral de lluvia medible o efectiva).<br>'
        '<strong>¿Qué significa?</strong> Representa la probabilidad climatológica real de ausencia de precipitación en la cuenca para ese mes específico.<br>'
        '<strong>¿Cómo se interpreta?</strong> Varía estacionalmente (ej. valores altos de 0.60–0.70 en meses de estiaje y bajos de 0.30–0.45 en temporada de lluvias). Es la cota observacional obligatoria que el modelo debe igualar.'
        '</span>'
        '</div>'

        '<div style="margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #E2E8F0;">'
        '• <strong>Umbral modelo (mm/d) y Efecto Llovizna (<em>Drizzle Effect</em>):</strong><br>'
        '<span style="color: #475569;">'
        '<strong>¿Cómo se calcula?</strong> Es el valor de precipitación diaria simulada por el GCM que corresponde exactamente al percentil P(seco)<sub>obs</sub> dentro de la distribución del modelo para el mes <em>m</em>.<br>'
        '<strong>¿Qué significa?</strong> Los modelos climáticos globales (GCM) padecen del defecto numérico conocido como <em>drizzle effect</em>: debido a la parametrización de convección en celdas extensas (~100 km), generan lloviznas persistentes de baja intensidad (0.01 a 0.80 mm/d) casi a diario.<br>'
        '<strong>¿Cómo se interpreta?</strong> Actúa como un filtro de poda física: cualquier lluvia simulada por el GCM menor o igual a este umbral se trunca a <strong>0.0 mm/d</strong>. Esto extirpa las lloviznas espurias y calibra la alternancia seco/húmedo antes de transformar los cuantiles de días lluviosos.'
        '</span>'
        '</div>'

        '<div style="margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #E2E8F0;">'
        '• <strong>Máx. modelo húmedo vs. Máx. observado húmedo (Soporte Empírico):</strong><br>'
        '<span style="color: #475569;">'
        '<strong>¿Cómo se calcula?</strong> Corresponden al cuantil 1.0 (máximo histórico) de la serie de calibración para días con lluvia activa en cada mes.<br>'
        '<strong>¿Qué significa?</strong> Definen los límites del soporte físico de las funciones empíricas. El GCM bruto frecuentemente atenúa los picos máximos (ej. 50–70 mm/d) por promediado espacial, mientras la estación puntual capta núcleos convectivos severos (ej. 120–160 mm/d).<br>'
        '<strong>¿Cómo se interpreta?</strong> Refleja la amplificación necesaria para reproducir tormentas extremas reales. En EQM clásico, si una proyección futura supera el máximo del modelo, la transformación satura en el cuantil 1.0 (máximo observado) (Themeßl et al., 2011; Gudmundsson et al., 2012).'
        '</span>'
        '</div>'

        '<div>'
        '• <strong>Días húmedos obs vs. Días húmedos QM (Muestra evaluada):</strong><br>'
        '<span style="color: #475569;">'
        '<strong>¿Cómo se calcula?</strong> Conteo de días con lluvia &ge; 0.10 mm/d en la ventana temporal activa.<br>'
        '<strong>¿Qué significa?</strong> Verifica mes a mes que la frecuencia de eventos de precipitación corregidos coincida con la persistencia real de la estación pluviométrica.<br>'
        '<strong>¿Cómo se interpreta?</strong> La igualdad de conteos confirma que el modelo QM corrigió con precisión tanto la ocurrencia como la magnitud de la precipitación mensual.'
        '</span>'
        '</div>'

        '</div>'
    )
    if hasattr(st, "html"):
        st.html(explicacion_param_html)
    else:
        st.markdown(explicacion_param_html, unsafe_allow_html=True)

# ---------------------------------------------------------
# Tab 4: Tabla Completa de Métricas
# ---------------------------------------------------------
with tabs[3]:
    st.markdown(f"##### Estadísticas Hidrometeorológicas y Errores Residuales ({y_ini}–{y_fin})")
    if es_sub:
        metricas_tab4 = tabla_metricas_comparativas(
            cal_activa["obs_mm"].to_numpy(),
            cal_activa["modelo_mm"].to_numpy(),
            cal_activa["qm_mm"].to_numpy(),
            wet_threshold=float(metadata.get("wet_thresh", 0.1))
        )
    else:
        metricas_tab4 = metricas_df

    st.dataframe(
        metricas_tab4.style.format({
            "Media (mm/d)": "{:.3f}",
            "Mediana (mm/d)": "{:.3f}",
            "Desv. Estándar (mm/d)": "{:.3f}",
            "P95 (mm/d)": "{:.2f}",
            "P99 (mm/d)": "{:.2f}",
            "Máximo (mm/d)": "{:.1f}",
            "Frecuencia húmeda (%)": "{:.1f}%",
            "Frecuencia seca (%)": "{:.1f}%",
            "Sesgo relativo Media (%)": "{:+.2f}%",
            "RMSE (mm/d)": "{:.2f}",
            "MAE (mm/d)": "{:.2f}",
            "KGE": "{:.3f}",
            "r": "{:.3f}",
            "alpha": "{:.3f}",
            "beta": "{:.3f}",
        }),
        use_container_width=True,
        hide_index=True
    )
