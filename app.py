"""
Dashboard Interactivo de Quantile Mapping (QM) en Hidrometeorología
Desarrollado para análisis de ajuste de sesgo estadístico y downscaling de precipitación.
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import datetime

from qm_core import (
    cargar_datos_qm,
    generar_inventario,
    preparar_periodo_calibracion,
    fit_eqm_mensual,
    apply_eqm_mensual,
    tabla_metricas_comparativas,
    calcular_ecdf,
    calcular_qq_points,
    ejecutar_ejemplo_pedagogico,
)

# ---------------------------------------------------------
# Configuración inicial de la página
# ---------------------------------------------------------
st.set_page_config(
    page_title="Quantile Mapping | Hidrometeorología",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos visuales personalizados
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 8px;
        padding: 12px 16px;
        border-left: 4px solid #3B82F6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        background-color: #F1F5F9;
        border-radius: 6px 6px 0px 0px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E3A8A !important;
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Funciones cacheadas de procesamiento
# ---------------------------------------------------------
@st.cache_data(show_spinner="Procesando archivo de datos...")
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


@st.cache_data(show_spinner="Calibrando Quantile Mapping mensual...")
def calibrar_y_aplicar(modelo_df, obs_df, start_year, end_year, wet_thresh, n_q):
    f_inicio = pd.Timestamp(f"{start_year}-01-01")
    f_fin = pd.Timestamp(f"{end_year}-12-31")

    cal = preparar_periodo_calibracion(modelo_df, obs_df, f_inicio, f_fin)
    if len(cal) < 100:
        raise ValueError("Periodo de calibración con datos insuficientes.")

    params = fit_eqm_mensual(cal, wet_threshold=wet_thresh, n_quantiles=n_q)
    qm_cal, fuera_cal = apply_eqm_mensual(cal["fecha"], cal["modelo_mm"], params)
    cal["qm_mm"] = qm_cal
    cal["fuera_soporte"] = fuera_cal

    # Aplicar a toda la serie del modelo
    qm_todo, fuera_todo = apply_eqm_mensual(modelo_df["fecha"], modelo_df["pr_mm_dia"], params)
    modelo_todo = modelo_df.copy()
    modelo_todo["pr_qm_mm_dia"] = qm_todo
    modelo_todo["fuera_soporte"] = fuera_todo
    modelo_todo["periodo"] = np.where(modelo_todo["fecha"] <= f_fin, "Referencia_Histórica", "Proyección_Futura")

    return cal, params, modelo_todo


# ---------------------------------------------------------
# Barra Lateral: Configuración de Parámetros
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1514632595-4944383f2737?w=400&auto=format&fit=crop&q=60", use_container_width=True)
    st.title("⚙️ Parámetros QM")

    st.markdown("### 📂 Fuente de Datos")
    opcion_datos = st.radio("Origen de datos:", ["Predeterminado ('data QM.csv')", "Cargar archivo personalizado (CSV/ODS)"])
    archivo_usuario = None
    if opcion_datos == "Cargar archivo personalizado (CSV/ODS)":
        archivo_usuario = st.file_uploader("Subir dataset", type=["csv", "ods"])

    try:
        modelo, observado = get_data(archivo_usuario)
        datos_cargados = True
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        datos_cargados = False

    if datos_cargados:
        st.markdown("---")
        st.markdown("### ⏱️ Periodo de Calibración")
        min_yr = int(max(modelo["fecha"].min().year, observado["fecha"].min().year))
        max_yr = int(min(modelo["fecha"].max().year, observado["fecha"].max().year))

        # Valores sugeridos CMIP6 (1959-2014)
        def_start = max(min_yr, 1959)
        def_end = min(max_yr, 2014)

        cal_range = st.slider(
            "Años de referencia:",
            min_value=min_yr,
            max_value=max_yr,
            value=(def_start, def_end),
            help="Periodo histórico común entre el modelo y la estación para ajustar las distribuciones."
        )

        st.markdown("### 💧 Ajustes Metodológicos")
        wet_thresh = st.number_input(
            "Umbral de día húmedo (mm/d):",
            min_value=0.0,
            max_value=5.0,
            value=0.10,
            step=0.05,
            help="Valores por debajo de este umbral se consideran días secos (P = 0 mm)."
        )

        n_quantiles = st.select_slider(
            "Resolución de cuantiles:",
            options=[201, 501, 1001, 2001],
            value=1001,
            help="Número de intervalos cuantílicos para la función de transferencia empírica."
        )

        st.info("💡 **Consejo:** El límite 2014 coincide con el cierre del experimento histórico de CMIP6.")

# ---------------------------------------------------------
# Encabezado Principal
# ---------------------------------------------------------
st.markdown('<div class="main-header">🌧️ Quantile Mapping en Hidrometeorología</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Plataforma interactiva para corrección de sesgo estadístico y downscaling univariado de precipitación diaria.</div>',
    unsafe_allow_html=True
)

if not datos_cargados:
    st.warning("Cargue un archivo válido para iniciar la aplicación.")
    st.stop()

# Ejecución del pipeline de calibración
try:
    cal, params_qm, modelo_todo = calibrar_y_aplicar(
        modelo, observado, cal_range[0], cal_range[1], wet_thresh, n_quantiles
    )
except Exception as err:
    st.error(f"Error durante la calibración: {err}")
    st.stop()

# ---------------------------------------------------------
# Organización en Pestañas (Tabs)
# ---------------------------------------------------------
tabs = st.tabs([
    "🧭 Diagnóstico y Datos",
    "🎓 Concepto y Ejemplo Pedagógico",
    "📈 Ajuste ECDF y Q-Q",
    "🌧️ Climatología y Series Diarias",
    "🔮 Proyecciones (1950–2100)",
    "📥 Exportación y Metodología"
])

# =========================================================
# TAB 1: Diagnóstico y Datos
# =========================================================
with tabs[0]:
    st.markdown("### 📊 Inventario General de Series")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Modelo Climático", f"{modelo['modelo'].iloc[0]}", f"{len(modelo):,} registros")
    with col2:
        st.metric("Estación Pluviométrica", f"{observado['estacion'].iloc[0]}", f"{len(observado):,} registros")
    with col3:
        st.metric("Periodo Común Calibración", f"{cal_range[0]} – {cal_range[1]}", f"{len(cal):,} días")
    with col4:
        st.metric("Umbral Seco/Húmedo", f"{wet_thresh} mm/d", f"Cuantiles: {n_quantiles}")

    st.markdown("#### Tabla de Metadatos e Inventario")
    inv_df = generar_inventario(modelo, observado)
    st.dataframe(inv_df, use_container_width=True, hide_index=True)

    st.markdown("#### Explorador Visual de Series Brutas")
    st.write("Inspecciona la serie completa observada frente a la serie simulada sin corregir:")

    # Muestra interactiva de series temporales brutas
    fig_raw = go.Figure()
    # Muestrear si es muy denso para agilidad visual
    fig_raw.add_trace(go.Scatter(
        x=modelo["fecha"], y=modelo["pr_mm_dia"],
        mode="lines", name="Modelo GCM Bruto",
        line=dict(color="#64748B", width=1), opacity=0.7
    ))
    fig_raw.add_trace(go.Scatter(
        x=observado["fecha"], y=observado["pr_mm_dia"],
        mode="lines", name="Observado (Estación)",
        line=dict(color="#2563EB", width=1), opacity=0.8
    ))
    fig_raw.update_layout(
        title="Historial de Precipitación Diaria (Series Brutas)",
        xaxis_title="Fecha",
        yaxis_title="Precipitación diaria (mm/d)",
        xaxis=dict(rangeslider=dict(visible=True)),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40)
    )
    st.plotly_chart(fig_raw, use_container_width=True)

# =========================================================
# TAB 2: Concepto y Ejemplo Pedagógico
# =========================================================
with tabs[1]:
    st.markdown("### 🎓 ¿Qué es Quantile Mapping y cómo funciona?")
    st.markdown(
        r"""
        **Quantile Mapping (QM)** es una técnica no lineal de ajuste de sesgo que alinea la función de distribución acumulada (CDF)
        de los datos simulados por un modelo $X_m$ con la distribución de las observaciones $X_o$.

        Matemáticamente, para cualquier valor modelado $X_m$, se evalúa su posición cuantílica empírica en la distribución simulada
        $p = F_m(X_m)$ y se sustituye por el valor observado que ocupa esa misma probabilidad acumulada $F_o^{-1}(p)$:
        """
    )
    st.latex(r"X_{\mathrm{QM}} = F_o^{-1}\left(F_m(X_m)\right)")

    st.markdown("---")
    st.markdown("### 🧪 Demostración Interactiva con Ejemplo Pedagógico")
    st.caption("Ajusta los valores de prueba o utiliza la serie sintética pedagógica del notebook.")

    col_ped1, col_ped2 = st.columns([1, 2])
    with col_ped1:
        st.write("**Valores del ejemplo:**")
        texto_mod = st.text_input("Valores Modelo (separados por coma):", "2, 5, 8, 12, 15, 20, 25, 30, 40, 50")
        texto_obs = st.text_input("Valores Observados (separados por coma):", "1, 4, 7, 10, 14, 18, 28, 35, 48, 65")

        try:
            arr_mod = np.array([float(x.strip()) for x in texto_mod.split(",")])
            arr_obs = np.array([float(x.strip()) for x in texto_obs.split(",")])
            tabla_ped, sesgo_ped = ejecutar_ejemplo_pedagogico(arr_mod, arr_obs)
            valido_ped = True
        except Exception as e:
            st.error(f"Error en formato de datos: {e}")
            valido_ped = False

        if valido_ped:
            st.write(f"**Sesgo medio inicial (Modelo - Obs):** `{sesgo_ped:+.2f} mm`")
            st.dataframe(tabla_ped, hide_index=True, use_container_width=True)

    with col_ped2:
        if valido_ped:
            fig_ped = go.Figure()
            indices = np.arange(1, len(arr_mod) + 1)
            fig_ped.add_trace(go.Scatter(
                x=indices, y=arr_mod, mode="lines+markers",
                name="Modelo Original", line=dict(color="#EF4444", width=2), marker=dict(size=8)
            ))
            fig_ped.add_trace(go.Scatter(
                x=indices, y=tabla_ped["QM corregido Xqm (mm)"], mode="lines+markers",
                name="Modelo Corregido QM", line=dict(color="#10B981", width=3, dash="dot"), marker=dict(size=8)
            ))
            fig_ped.add_trace(go.Scatter(
                x=indices, y=arr_obs, mode="lines+markers",
                name="Observado Referencia", line=dict(color="#3B82F6", width=2), marker=dict(size=8)
            ))
            fig_ped.update_layout(
                title="Alineación Cuantil a Cuantil (Ejemplo Pedagógico)",
                xaxis_title="Índice de Muestra",
                yaxis_title="Magnitud (mm)",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_ped, use_container_width=True)

# =========================================================
# TAB 3: Ajuste ECDF y Q-Q
# =========================================================
with tabs[2]:
    st.markdown("### 📈 Diagnóstico de Distribución y Métricas Estadísticas")

    col_m1, col_m2 = st.columns([1, 1])

    with col_m1:
        st.markdown("#### Curvas de Distribución Empírica Acumulada (ECDF)")
        filtro_mes_ecdf = st.selectbox(
            "Filtrar ECDF por:",
            ["Todo el periodo común", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        )
        escala_log = st.checkbox("Escala logarítmica en eje X (intensidad)", value=False)

        if filtro_mes_ecdf == "Todo el periodo común":
            sub_ecdf = cal
        else:
            n_mes = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"].index(filtro_mes_ecdf) + 1
            sub_ecdf = cal.loc[cal["mes"] == n_mes]

        x_mod_e, p_mod_e = calcular_ecdf(sub_ecdf["modelo_mm"])
        x_obs_e, p_obs_e = calcular_ecdf(sub_ecdf["obs_mm"])
        x_qm_e, p_qm_e = calcular_ecdf(sub_ecdf["qm_mm"])

        fig_ecdf = go.Figure()
        fig_ecdf.add_trace(go.Scatter(x=x_mod_e, y=p_mod_e, mode="lines", name="Modelo Bruto", line=dict(color="#EF4444", width=2)))
        fig_ecdf.add_trace(go.Scatter(x=x_obs_e, y=p_obs_e, mode="lines", name="Observado", line=dict(color="#3B82F6", width=2)))
        fig_ecdf.add_trace(go.Scatter(x=x_qm_e, y=p_qm_e, mode="lines", name="Modelo Corregido QM", line=dict(color="#10B981", width=2, dash="dash")))

        fig_ecdf.update_layout(
            title=f"ECDF: {filtro_mes_ecdf}",
            xaxis_title="Precipitación diaria (mm/d)",
            yaxis_title="Probabilidad acumulada F(x)",
            xaxis_type="log" if escala_log else "linear",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_ecdf, use_container_width=True)

    with col_m2:
        st.markdown("#### Gráfico de Diagnóstico Q-Q")
        qq_pts = calcular_qq_points(cal["obs_mm"].to_numpy(), cal["modelo_mm"].to_numpy(), cal["qm_mm"].to_numpy(), n_points=120)
        lim_max = max(qq_pts["obs"].max(), qq_pts["mod_raw"].max(), qq_pts["mod_qm"].max()) * 1.05

        fig_qq = go.Figure()
        fig_qq.add_trace(go.Scatter(
            x=qq_pts["obs"], y=qq_pts["mod_raw"],
            mode="markers", name="Modelo Bruto vs Obs",
            marker=dict(color="#EF4444", size=6, opacity=0.7)
        ))
        fig_qq.add_trace(go.Scatter(
            x=qq_pts["obs"], y=qq_pts["mod_qm"],
            mode="markers", name="Modelo Corregido QM vs Obs",
            marker=dict(color="#10B981", size=6, opacity=0.7)
        ))
        fig_qq.add_trace(go.Scatter(
            x=[0, lim_max], y=[0, lim_max],
            mode="lines", name="Línea 1:1 (Ajuste Perfecto)",
            line=dict(color="#64748B", dash="dash", width=1.5)
        ))
        fig_qq.update_layout(
            title="Diagnóstico Cuantil-Cuantil (Q-Q Plot)",
            xaxis_title="Cuantiles Observados (mm/d)",
            yaxis_title="Cuantiles Simulados / Corregidos (mm/d)",
            hovermode="closest",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_qq, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 📋 Métricas de Precipitación y Reducción de Sesgo en el Periodo de Calibración")
    metricas_df = tabla_metricas_comparativas(
        cal["obs_mm"].to_numpy(), cal["modelo_mm"].to_numpy(), cal["qm_mm"].to_numpy(), wet_threshold=wet_thresh
    )
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

    st.markdown("#### ⚙️ Parámetros Calibrados Mensualmente")
    with st.expander("Ver tabla de parámetros mensuales (fracción seca y umbrales)"):
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
        st.dataframe(tabla_param.style.format({
            "P(seco) observado": "{:.3f}",
            "Umbral modelo (mm/d)": "{:.4f}",
            "Máx. modelo húmedo (mm/d)": "{:.2f}",
            "Máx. observado húmedo (mm/d)": "{:.2f}",
        }), use_container_width=True, hide_index=True)

# =========================================================
# TAB 4: Climatología y Series Diarias
# =========================================================
with tabs[3]:
    st.markdown("### 🌧️ Climatología Mensual y Exploración Diaria")

    col_c1, col_c2 = st.columns([1, 1])

    with col_c1:
        st.markdown("#### Ciclo Anual Medio (Climatología Mensual)")
        clim = cal.groupby("mes")[["modelo_mm", "obs_mm", "qm_mm"]].mean().reset_index()
        meses_nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        clim["Nombre_Mes"] = clim["mes"].apply(lambda x: meses_nombres[x - 1])

        fig_clim = go.Figure()
        fig_clim.add_trace(go.Bar(x=clim["Nombre_Mes"], y=clim["modelo_mm"], name="Modelo Bruto", marker_color="#F87171"))
        fig_clim.add_trace(go.Bar(x=clim["Nombre_Mes"], y=clim["obs_mm"], name="Observado", marker_color="#60A5FA"))
        fig_clim.add_trace(go.Bar(x=clim["Nombre_Mes"], y=clim["qm_mm"], name="Modelo QM", marker_color="#34D399"))
        fig_clim.update_layout(
            barmode="group",
            title="Precipitación Media Diaria por Mes (mm/d)",
            xaxis_title="Mes",
            yaxis_title="Precipitación media (mm/d)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_clim, use_container_width=True)

    with col_c2:
        st.markdown("#### Inspección Diaria por Año Específico")
        anios_disponibles = sorted(cal["fecha"].dt.year.unique())
        anio_sel = st.selectbox("Seleccionar año a inspeccionar:", anios_disponibles, index=anios_disponibles.index(2010) if 2010 in anios_disponibles else 0)

        demo_anio = cal.loc[cal["fecha"].dt.year == anio_sel]

        fig_anio = go.Figure()
        fig_anio.add_trace(go.Scatter(x=demo_anio["fecha"], y=demo_anio["modelo_mm"], mode="lines", name="Modelo Bruto", line=dict(color="#EF4444", width=1.5)))
        fig_anio.add_trace(go.Scatter(x=demo_anio["fecha"], y=demo_anio["obs_mm"], mode="lines", name="Observado", line=dict(color="#3B82F6", width=1.5)))
        fig_anio.add_trace(go.Scatter(x=demo_anio["fecha"], y=demo_anio["qm_mm"], mode="lines", name="Modelo QM", line=dict(color="#10B981", width=2)))

        fig_anio.update_layout(
            title=f"Serie Diaria en el Año {anio_sel}",
            xaxis_title="Fecha",
            yaxis_title="Precipitación diaria (mm/d)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_anio, use_container_width=True)

# =========================================================
# TAB 5: Proyecciones (1950–2100)
# =========================================================
with tabs[4]:
    st.markdown("### 🔮 Serie Extendida y Proyecciones Futuras (1950–2100)")

    st.warning(
        """
        ⚠️ **Advertencia Metodológica y Climática:**
        - El archivo provisto contiene datos del modelo hasta el año 2100, pero **no especifica la columna de escenario SSP**
          (por ejemplo SSP1-2.6, SSP2-4.5 o SSP5-8.5). La proyección mostrada debe considerarse como un ejercicio computacional demostrativo.
        - Además, el QM empírico clásico puede alterar la señal de cambio climático de los extremos. Para proyecciones climáticas formales,
          se recomienda **Quantile Delta Mapping (QDM)** (Cannon et al., 2015).
        """
    )

    n_fuera = int(modelo_todo["fuera_soporte"].sum())
    n_fuera_post = int(modelo_todo.loc[modelo_todo["periodo"] == "Proyección_Futura", "fuera_soporte"].sum())

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        st.metric("Total Días Proyectados", f"{len(modelo_todo):,} días", "1950 a 2100")
    with col_f2:
        st.metric("Valores Fuera del Soporte Histórico", f"{n_fuera} días", f"{n_fuera_post} tras {cal_range[1]}")
    with col_f3:
        st.metric("Tasa de Extrapolación", f"{(n_fuera / len(modelo_todo)) * 100:.3f}%", "Saturación en cuantil 1.0")

    # Acumulados Anuales
    modelo_todo["anio"] = modelo_todo["fecha"].dt.year
    anual = modelo_todo.groupby("anio").agg({
        "pr_mm_dia": "sum",
        "pr_qm_mm_dia": "sum",
        "fuera_soporte": "sum"
    }).rename(columns={"pr_mm_dia": "Bruto_Anual_mm", "pr_qm_mm_dia": "QM_Anual_mm"}).reset_index()

    fig_anual = go.Figure()
    fig_anual.add_trace(go.Scatter(
        x=anual["anio"], y=anual["Bruto_Anual_mm"],
        mode="lines", name="Modelo Bruto (mm/año)", line=dict(color="#EF4444", width=1.5)
    ))
    fig_anual.add_trace(go.Scatter(
        x=anual["anio"], y=anual["QM_Anual_mm"],
        mode="lines", name="Modelo QM Corregido (mm/año)", line=dict(color="#10B981", width=2)
    ))
    # Línea vertical dividiendo calibración y futuro
    fig_anual.add_vline(
        x=cal_range[1], line_dash="dash", line_color="#475569",
        annotation_text=f"Fin Calibración ({cal_range[1]})", annotation_position="top left"
    )
    fig_anual.update_layout(
        title="Evolución de la Precipitación Acumulada Anual (1950–2100)",
        xaxis_title="Año",
        yaxis_title="Precipitación acumulada (mm/año)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_anual, use_container_width=True)

# =========================================================
# TAB 6: Exportación y Metodología
# =========================================================
with tabs[5]:
    st.markdown("### 📥 Descargas de Datos Procesados")

    col_d1, col_d2, col_d3 = st.columns(3)

    with col_d1:
        csv_salida = modelo_todo[[
            "fecha", "modelo", "pr_mm_dia", "pr_qm_mm_dia", "fuera_soporte", "periodo"
        ]].to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📄 Descargar Serie Corregida Completa (CSV)",
            data=csv_salida,
            file_name="precipitacion_QM_corregida.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col_d2:
        params_export = pd.DataFrame([
            {
                "mes": m,
                "p_seco_obs": p["p_seco_obs"],
                "umbral_mod_mm": p["umbral_mod"],
                "max_mod_hum_mm": p["mod_q"][-1],
                "max_obs_hum_mm": p["obs_q"][-1],
            }
            for m, p in params_qm.items()
        ]).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⚙️ Descargar Parámetros Calibrados (CSV)",
            data=params_export,
            file_name="parametros_calibracion_qm.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col_d3:
        metricas_export = metricas_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📊 Descargar Métricas Estadísticas (CSV)",
            data=metricas_export,
            file_name="metricas_desempeno_qm.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.markdown("---")
    st.markdown("### 📚 Síntesis Metodológica y Respuestas Clave")

    with st.expander("1. ¿Qué es Quantile Mapping?", expanded=True):
        st.markdown(
            """
            Es un método de postprocesamiento estadístico no paramétrico o paramétrico que ajusta la distribución marginal
            de una serie simulada hacia la distribución observada mediante la transformación $X_{\\mathrm{QM}} = F_o^{-1}(F_m(X_m))$.
            Su principal virtud es corregir no solo la media sino toda la estructura de cuantiles (mediana, variabilidad y extremos).
            """
        )

    with st.expander("2. ¿Cómo se construyen las CDF / ECDF?", expanded=True):
        st.markdown(
            """
            Se construyen a partir del ranking y frecuencias acumuladas empíricas $\\widehat{F}_n(x) = \\frac{1}{n}\\sum \\mathbf{1}(x_i \\le x)$.
            En precipitación, es indispensable tratar la masa en cero (días secos) determinando el umbral del modelo equivalente a la frecuencia
            seca observada antes de calcular los cuantiles de intensidad húmeda.
            """
        )

    with st.expander("3. ¿Cómo se aplica en hidrometeorología y cuáles son sus límites?", expanded=True):
        st.markdown(
            """
            Se calibra con series históricas concurrentes y se aplica para alimentar modelos hidrológicos o evaluar impactos climáticos.
            **Límites:** No genera la variabilidad espacial no resuelta por la malla del modelo (Maraun, 2013), asume estacionariedad del sesgo
            y puede modificar la señal de cambio climático de los extremos, motivo por el cual se sugiere **QDM** para proyecciones futuras (Cannon et al., 2015).
            """
        )

    with st.expander("4. Referencias bibliográficas principales"):
        st.markdown(
            """
            - **Cannon, A. J., et al. (2015).** Bias correction of GCM precipitation by quantile mapping: How well do methods preserve changes in quantiles and extremes? *J. Climate*, 28(17), 6938–6959. [DOI: 10.1175/JCLI-D-14-00754.1](https://doi.org/10.1175/JCLI-D-14-00754.1)
            - **Gudmundsson, L., et al. (2012).** Technical Note: Downscaling RCM precipitation to the station scale using statistical transformations. *HESS*, 16, 3383–3390. [DOI: 10.5194/hess-16-3383-2012](https://doi.org/10.5194/hess-16-3383-2012)
            - **Maraun, D. (2013).** Bias correction, quantile mapping, and downscaling: Revisiting the inflation issue. *J. Climate*, 26(6), 2137–2143. [DOI: 10.1175/JCLI-D-12-00821.1](https://doi.org/10.1175/JCLI-D-12-00821.1)
            - **Themeßl, M. J., et al. (2011).** Empirical-statistical downscaling and error correction of daily precipitation from regional climate models. *Int. J. Climatol.*, 31(10), 1530–1544. [DOI: 10.1002/joc.2168](https://doi.org/10.1002/joc.2168)
            """
        )

# Pie de página
st.markdown("---")
st.caption("Dashboard de Quantile Mapping en Hidrometeorología • Desarrollado con Streamlit y Plotly • Basado en MPI-ESM1-2-HR y Estación Carolina (27010500)")
