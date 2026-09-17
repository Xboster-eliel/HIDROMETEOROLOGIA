"""
Generadores centralizados de gráficos interactivos de Plotly con convención cromática uniforme.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from ui.constants import COLOR_OBS, COLOR_RAW, COLOR_QM, COLOR_REF, MESES_CORTOS
from ui.theme import apply_plotly_theme
from qm_core import calcular_ecdf, calcular_qq_points


def plot_comparativa_principal(cal_df: pd.DataFrame, anio_inicio: int = None, anio_fin: int = None) -> go.Figure:
    """Gráfico principal de precipitación diaria en el periodo de referencia/calibración."""
    df = cal_df
    if anio_inicio and anio_fin:
        df = cal_df.loc[cal_df["fecha"].dt.year.between(anio_inicio, anio_fin)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["fecha"], y=df["modelo_mm"],
        mode="lines", name="Modelo Bruto (GCM)",
        line=dict(color=COLOR_RAW, width=1.0), opacity=0.7
    ))
    fig.add_trace(go.Scatter(
        x=df["fecha"], y=df["obs_mm"],
        mode="lines", name="Observado (Estación)",
        line=dict(color=COLOR_OBS, width=1.2), opacity=0.85
    ))
    fig.add_trace(go.Scatter(
        x=df["fecha"], y=df["qm_mm"],
        mode="lines", name="Modelo Corregido QM",
        line=dict(color=COLOR_QM, width=1.5), opacity=0.9
    ))

    fig = apply_plotly_theme(
        fig,
        title="Histórico de Precipitación Diaria: Comparativa Observación vs GCM vs QM",
        x_title="Fecha",
        y_title="Precipitación diaria (mm/d)",
        height=380
    )
    fig.update_xaxes(rangeslider=dict(visible=False))
    return fig


def plot_sesgo_mensual(cal_df: pd.DataFrame) -> go.Figure:
    """
    Gráfico de barras divergentes: Reducción del sesgo relativo porcentual mes a mes (Ene–Dic)
    antes y después de aplicar Quantile Mapping.
    """
    agrupado = cal_df.groupby("mes")[["obs_mm", "modelo_mm", "qm_mm"]].mean().reset_index()
    agrupado["bias_raw"] = ((agrupado["modelo_mm"] - agrupado["obs_mm"]) / agrupado["obs_mm"]) * 100.0
    agrupado["bias_qm"]  = ((agrupado["qm_mm"] - agrupado["obs_mm"]) / agrupado["obs_mm"]) * 100.0
    agrupado["mes_nombre"] = agrupado["mes"].apply(lambda m: MESES_CORTOS[m - 1])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=agrupado["mes_nombre"],
        y=agrupado["bias_raw"],
        name="Sesgo GCM Bruto (%)",
        marker_color=COLOR_RAW,
        opacity=0.85
    ))
    fig.add_trace(go.Bar(
        x=agrupado["mes_nombre"],
        y=agrupado["bias_qm"],
        name="Sesgo Modelo QM (%)",
        marker_color=COLOR_QM,
        opacity=0.95
    ))

    # Línea de referencia de sesgo cero
    fig.add_hline(y=0, line_dash="solid", line_color=COLOR_REF, line_width=1.2)

    fig = apply_plotly_theme(
        fig,
        title="Reducción del Sesgo Relativo Medio Mensual (%)",
        x_title="Mes",
        y_title="Sesgo respecto a Observado (%)",
        hovermode="x unified",
        height=380
    )
    fig.update_layout(barmode="group")
    return fig


def plot_ecdf_comparativa(cal_df: pd.DataFrame, mes: int = None, log_scale: bool = False) -> go.Figure:
    """Gráfico de funciones de distribución empírica acumulada (ECDF)."""
    sub = cal_df if mes is None else cal_df.loc[cal_df["mes"] == mes]
    etiqueta = "Todo el periodo común" if mes is None else f"Mes: {MESES_CORTOS[mes-1]}"

    x_mod, p_mod = calcular_ecdf(sub["modelo_mm"])
    x_obs, p_obs = calcular_ecdf(sub["obs_mm"])
    x_qm, p_qm   = calcular_ecdf(sub["qm_mm"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_mod, y=p_mod, mode="lines", name="Modelo Bruto", line=dict(color=COLOR_RAW, width=1.8)))
    fig.add_trace(go.Scatter(x=x_obs, y=p_obs, mode="lines", name="Observado", line=dict(color=COLOR_OBS, width=2.0)))
    fig.add_trace(go.Scatter(x=x_qm, y=p_qm, mode="lines", name="Modelo Corregido QM", line=dict(color=COLOR_QM, width=2.0, dash="dash")))

    fig = apply_plotly_theme(
        fig,
        title=f"ECDF: {etiqueta}",
        x_title="Precipitación diaria (mm/d)",
        y_title="Probabilidad acumulada F(x)",
        height=400
    )
    if log_scale:
        fig.update_xaxes(type="log")
    return fig


def plot_qq_diagnostico(cal_df: pd.DataFrame, n_points: int = 120) -> go.Figure:
    """Gráfico de diagnóstico Cuantil-Cuantil (Q-Q) con línea 1:1."""
    qq_pts = calcular_qq_points(cal_df["obs_mm"].to_numpy(), cal_df["modelo_mm"].to_numpy(), cal_df["qm_mm"].to_numpy(), n_points=n_points)
    lim_max = max(qq_pts["obs"].max(), qq_pts["mod_raw"].max(), qq_pts["mod_qm"].max()) * 1.05

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=qq_pts["obs"], y=qq_pts["mod_raw"],
        mode="markers", name="Modelo Bruto vs Obs",
        marker=dict(color=COLOR_RAW, size=6, opacity=0.7)
    ))
    fig.add_trace(go.Scatter(
        x=qq_pts["obs"], y=qq_pts["mod_qm"],
        mode="markers", name="Modelo Corregido QM vs Obs",
        marker=dict(color=COLOR_QM, size=6, opacity=0.85)
    ))
    fig.add_trace(go.Scatter(
        x=[0, lim_max], y=[0, lim_max],
        mode="lines", name="Línea 1:1 (Ajuste Perfecto)",
        line=dict(color=COLOR_REF, dash="dash", width=1.5)
    ))

    fig = apply_plotly_theme(
        fig,
        title="Diagnóstico Q-Q: Cuantiles Observados vs Simulados",
        x_title="Cuantiles Observados (mm/d)",
        y_title="Cuantiles Simulados / Corregidos (mm/d)",
        hovermode="closest",
        height=400
    )
    return fig


def plot_climatologia_variable(cal_df: pd.DataFrame, variable_tipo: str = "acumulado", wet_thresh: float = 0.1) -> go.Figure:
    """Calcula y grafica el ciclo anual para diferentes variables climatológicas."""
    # Variable types: 'acumulado', 'media', 'dias_humedos', 'p95', 'p99'
    agrup = cal_df.groupby("mes")
    
    if variable_tipo == "acumulado":
        # Acumulado promedio mensual en mm/mes
        n_anios = cal_df["fecha"].dt.year.nunique()
        serie_obs = agrup["obs_mm"].sum() / n_anios
        serie_raw = agrup["modelo_mm"].sum() / n_anios
        serie_qm  = agrup["qm_mm"].sum() / n_anios
        y_label = "Precipitación acumulada media (mm/mes)"
        t_label = "Ciclo Anual: Precipitación Acumulada Mensual"
    elif variable_tipo == "media":
        serie_obs = agrup["obs_mm"].mean()
        serie_raw = agrup["modelo_mm"].mean()
        serie_qm  = agrup["qm_mm"].mean()
        y_label = "Precipitación media diaria (mm/d)"
        t_label = "Ciclo Anual: Precipitación Media Diaria"
    elif variable_tipo == "dias_humedos":
        serie_obs = agrup["obs_mm"].apply(lambda s: 100.0 * (s >= wet_thresh).mean())
        serie_raw = agrup["modelo_mm"].apply(lambda s: 100.0 * (s >= wet_thresh).mean())
        serie_qm  = agrup["qm_mm"].apply(lambda s: 100.0 * (s >= wet_thresh).mean())
        y_label = "Frecuencia de días húmedos (%)"
        t_label = f"Ciclo Anual: Frecuencia de Días Húmedos (P ≥ {wet_thresh} mm/d)"
    elif variable_tipo == "p95":
        serie_obs = agrup["obs_mm"].apply(lambda s: np.quantile(s, 0.95))
        serie_raw = agrup["modelo_mm"].apply(lambda s: np.quantile(s, 0.95))
        serie_qm  = agrup["qm_mm"].apply(lambda s: np.quantile(s, 0.95))
        y_label = "Percentil 95 (mm/d)"
        t_label = "Ciclo Anual: Intensidad de Lluvia Intensa (P95)"
    else:  # p99
        serie_obs = agrup["obs_mm"].apply(lambda s: np.quantile(s, 0.99))
        serie_raw = agrup["modelo_mm"].apply(lambda s: np.quantile(s, 0.99))
        serie_qm  = agrup["qm_mm"].apply(lambda s: np.quantile(s, 0.99))
        y_label = "Percentil 99 (mm/d)"
        t_label = "Ciclo Anual: Extremos Pluviométricos (P99)"

    fig = go.Figure()
    fig.add_trace(go.Bar(x=MESES_CORTOS, y=serie_raw, name="Modelo Bruto", marker_color=COLOR_RAW, opacity=0.85))
    fig.add_trace(go.Bar(x=MESES_CORTOS, y=serie_obs, name="Observado", marker_color=COLOR_OBS, opacity=0.85))
    fig.add_trace(go.Bar(x=MESES_CORTOS, y=serie_qm, name="Modelo QM", marker_color=COLOR_QM, opacity=0.95))

    fig = apply_plotly_theme(
        fig,
        title=t_label,
        x_title="Mes",
        y_title=y_label,
        height=380
    )
    fig.update_layout(barmode="group")
    return fig


def plot_serie_multidecadal(modelo_todo: pd.DataFrame, cal_fin_year: int) -> go.Figure:
    """Evolución anual multidecadal (1950–2100) con sombreado de calibración vs proyección."""
    modelo_todo["anio"] = modelo_todo["fecha"].dt.year
    anual = modelo_todo.groupby("anio").agg({
        "pr_mm_dia": "sum",
        "pr_qm_mm_dia": "sum",
        "fuera_soporte": "sum"
    }).rename(columns={"pr_mm_dia": "Bruto_Anual", "pr_qm_mm_dia": "QM_Anual"}).reset_index()

    fig = go.Figure()

    # Área sombreada para calibración histórica
    fig.add_vrect(
        x0=anual["anio"].min(), x1=cal_fin_year,
        fillcolor="#E2E8F0", opacity=0.25, layer="below", line_width=0,
        annotation_text="Periodo Histórico de Calibración", annotation_position="top left",
        annotation_font=dict(size=10, color="#64748B")
    )
    # Área sombreada para aplicación futura
    fig.add_vrect(
        x0=cal_fin_year, x1=anual["anio"].max(),
        fillcolor="#FEF3C7", opacity=0.25, layer="below", line_width=0,
        annotation_text="Aplicación Fuera de Calibración (Proyección)", annotation_position="top right",
        annotation_font=dict(size=10, color="#B45309")
    )

    fig.add_trace(go.Scatter(
        x=anual["anio"], y=anual["Bruto_Anual"],
        mode="lines", name="Modelo GCM Bruto (mm/año)",
        line=dict(color=COLOR_RAW, width=1.6)
    ))
    fig.add_trace(go.Scatter(
        x=anual["anio"], y=anual["QM_Anual"],
        mode="lines", name="Modelo Corregido QM (mm/año)",
        line=dict(color=COLOR_QM, width=2.0)
    ))

    fig = apply_plotly_theme(
        fig,
        title="Evolución de la Precipitación Acumulada Anual (1950–2100)",
        x_title="Año",
        y_title="Precipitación acumulada (mm/año)",
        height=400
    )
    return fig
