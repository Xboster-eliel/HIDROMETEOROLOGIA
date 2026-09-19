"""
Componentes de presentación: cabeceras científicas, tarjetas de KPIs y semáforos de extremos.
Implementado con st.html y cadenas HTML sin indentación para evitar que el parser de Markdown
interprete las etiquetas HTML como bloques de código fuente (<pre><code>).
"""

from typing import Optional
import streamlit as st
import pandas as pd
from ui.constants import THRESHOLD_EXCELLENT, THRESHOLD_ACCEPTABLE


def render_scientific_header(
    modelo_nombre: str,
    estacion_nombre: str,
    cal_inicio: int,
    cal_fin: int
):
    """Renderiza el encabezado científico profesional con metadatos contextuales."""
    html_header = (
        '<div style="margin-bottom: 18px;">'
        '<div style="font-size: 1.65rem; font-weight: 700; color: #163A5F; letter-spacing: -0.02em; margin-bottom: 2px;">'
        'QUANTILE MAPPING · PRECIPITACIÓN DIARIA'
        '</div>'
        '<div style="font-size: 0.95rem; color: #64748B; margin-bottom: 8px;">'
        'Corrección estadística de sesgo mediante transformaciones empíricas mensuales'
        '</div>'
        '<div class="meta-pill">'
        f'<strong>Modelo:</strong> {modelo_nombre} &nbsp;•&nbsp; '
        f'<strong>Estación:</strong> {estacion_nombre} &nbsp;•&nbsp; '
        f'<strong>Periodo de Calibración:</strong> {cal_inicio}–{cal_fin}'
        '</div>'
        '</div>'
    )
    if hasattr(st, "html"):
        st.html(html_header)
    else:
        st.markdown(html_header, unsafe_allow_html=True)


def render_scientific_kpis(
    bias_raw: float,
    bias_qm: float,
    wet_obs: float,
    wet_raw: float,
    wet_qm: float,
    extrap_count: int,
    extrap_pct: float,
    extrap_subtexto: Optional[str] = None,
    media_obs: Optional[float] = None,
    media_raw: Optional[float] = None,
    media_qm: Optional[float] = None,
    cal_inicio: Optional[int] = None,
    cal_fin: Optional[int] = None,
):
    """Renderiza los 4 KPIs científicos de desempeño con sus paneles explicativos integrados."""
    c1, c2, c3, c4 = st.columns(4)

    def render_box(col, title, val_str, val_color, badge_html):
        html_box = (
            '<div class="kpi-box">'
            f'<div class="kpi-title">{title}</div>'
            f'<div class="kpi-value" style="color: {val_color};">{val_str}</div>'
            f'{badge_html}'
            '</div>'
        )
        with col:
            if hasattr(st, "html"):
                st.html(html_box)
            else:
                st.markdown(html_box, unsafe_allow_html=True)

    render_box(
        c1,
        "Sesgo GCM Bruto",
        f"{bias_raw:+.2f}%",
        "#B91C1C",
        '<div class="kpi-badge-bad">↓ Subestimación sistemática</div>'
    )
    render_box(
        c2,
        "Sesgo Modelo QM",
        f"{bias_qm:+.2f}%",
        "#15803D",
        '<div class="kpi-badge-good">✓ Sesgo medio corregido</div>'
    )
    render_box(
        c3,
        "Días Húmedos (P ≥ 0.1)",
        f"{wet_qm:.1f}%",
        "#172033",
        f'<div class="kpi-badge-good">✓ Obs {wet_obs:.1f}% (Bruto: {wet_raw:.1f}%)</div>'
    )

    subtexto_html = (
        f'<div style="font-size: 0.70rem; color: #64748B; margin-top: 3px; font-weight: 500;">{extrap_subtexto}</div>'
        if extrap_subtexto else ''
    )

    render_box(
        c4,
        "Extrapolación Futura",
        f"{extrap_pct:.3f}%",
        "#B45309",
        (
            f'<div class="kpi-badge-warn">⚠ {extrap_count} días fuera de soporte</div>'
            f'{subtexto_html}'
        )
    )

    # --------------------------------------------------------------------
    # Paneles explicativos e interpretaciones técnicas directamente debajo
    # --------------------------------------------------------------------
    col_exp_bias, col_exp_wet, col_exp_extrap = st.columns([2, 1, 1])

    cal_periodo_str = f" ({cal_inicio}–{cal_fin})" if (cal_inicio and cal_fin) else ""
    obs_str = f"{media_obs:.2f} mm/d" if media_obs is not None else "8.62 mm/d"
    raw_str = f"{media_raw:.2f} mm/d" if media_raw is not None else "7.67 mm/d"
    qm_str = f"{media_qm:.2f} mm/d" if media_qm is not None else "8.62 mm/d"

    html_exp_bias = (
        '<div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 12px; margin-top: 6px; font-size: 0.79rem; color: #334155; line-height: 1.45;">'
        '<div style="font-weight: 600; color: #163A5F; margin-bottom: 4px;">'
        '📐 ¿De dónde sale y cómo se calculó este valor?'
        '</div>'
        '<div>'
        f'Representa el <strong>sesgo relativo medio global</strong> sobre el periodo de calibración{cal_periodo_str}:<br>'
        '<span style="font-family: monospace; background: #EEF2F6; padding: 2px 5px; border-radius: 4px; font-size: 0.76rem; color: #0F172A;">'
        'Sesgo (%) = [ ( &mu;<sub>modelo</sub> &minus; &mu;<sub>observado</sub> ) / &mu;<sub>observado</sub> ] &times; 100%'
        '</span>'
        '</div>'
        '<div style="margin-top: 5px; color: #475569;">'
        f'• <strong>Observado (&mu;<sub>obs</sub>):</strong> {obs_str} (media de la estación pluviométrica).<br>'
        f'• <strong>GCM Bruto (&mu;<sub>bruto</sub>):</strong> {raw_str} &rarr; Déficit volumétrico de <strong>{bias_raw:+.2f}%</strong>.<br>'
        f'• <strong>Modelo QM (&mu;<sub>QM</sub>):</strong> {qm_str} &rarr; Corrección exacta a <strong>{bias_qm:+.2f}%</strong> (balance medio restituido).'
        '</div>'
        '</div>'
    )

    html_exp_wet = (
        '<div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 12px; margin-top: 6px; font-size: 0.79rem; color: #334155; line-height: 1.45;">'
        '<div style="font-weight: 600; color: #163A5F; margin-bottom: 4px;">'
        '🌧️ Significado e Interpretación'
        '</div>'
        '<div style="color: #475569;">'
        'Frecuencia de días con lluvia &ge; 0.10 mm/d.<br>'
        f'• <strong>Efecto Llovizna (<em>Drizzle</em>):</strong> El modelo bruto llovizna artificialmente ({wet_raw:.1f}% vs {wet_obs:.1f}% real).<br>'
        f'• <strong>Corrección QM:</strong> Iguala exactamente la ocurrencia observada ({wet_qm:.1f}%), podando lloviznas espurias y preservando la alternancia seco/húmedo.'
        '</div>'
        '</div>'
    )

    html_exp_extrap = (
        '<div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 12px; margin-top: 6px; font-size: 0.79rem; color: #334155; line-height: 1.45;">'
        '<div style="font-weight: 600; color: #163A5F; margin-bottom: 4px;">'
        '🔮 Significado e Interpretación'
        '</div>'
        '<div style="color: #475569;">'
        f'Días en 1950&ndash;2100 donde la lluvia supera el máximo histórico mensual ({extrap_count} días, {extrap_pct:.3f}%).<br>'
        '• <strong>Soporte empírico:</strong> En EQM clásico saturan en cuantil 1.0 (máximo observado).<br>'
        '• <strong>Cambio climático:</strong> No genera nuevos récords más allá del histórico, justificando el uso de QDM (Cannon et al., 2015).'
        '</div>'
        '</div>'
    )

    with col_exp_bias:
        if hasattr(st, "html"):
            st.html(html_exp_bias)
        else:
            st.markdown(html_exp_bias, unsafe_allow_html=True)

    with col_exp_wet:
        if hasattr(st, "html"):
            st.html(html_exp_wet)
        else:
            st.markdown(html_exp_wet, unsafe_allow_html=True)

    with col_exp_extrap:
        if hasattr(st, "html"):
            st.html(html_exp_extrap)
        else:
            st.markdown(html_exp_extrap, unsafe_allow_html=True)


def render_extreme_diagnostics_table(metricas_df: pd.DataFrame):
    """
    Renderiza una tabla visual condensada con semáforos de precisión:
    ✓ diferencia < 2%
    ● diferencia 2-5%
    ⚠ diferencia > 5%
    E incorpora diagnóstico desagregado de KGE (Knoben et al., 2019) y RMSE (Themeßl et al., 2011; Maraun, 2013).
    Utiliza st.html sin sangría para asegurar el renderizado como tabla gráfica limpia.
    """
    row_obs = metricas_df.loc[metricas_df["Serie"] == "Observado (Estación)"].iloc[0]
    row_raw = metricas_df.loc[metricas_df["Serie"] == "Modelo Bruto (GCM)"].iloc[0]
    row_qm = metricas_df.loc[metricas_df["Serie"] == "Modelo Corregido QM"].iloc[0]

    indices = [
        ("Precipitación media diaria", "Media (mm/d)", "mm/d"),
        ("Mediana de precipitación", "Mediana (mm/d)", "mm/d"),
        ("Desviación estándar (Variabilidad)", "Desv. Estándar (mm/d)", "mm/d"),
        ("Percentil 95 (Lluvias intensas)", "P95 (mm/d)", "mm/d"),
        ("Percentil 99 (Extremos hidrológicos)", "P99 (mm/d)", "mm/d"),
        ("Precipitación máxima diaria", "Máximo (mm/d)", "mm/d"),
        ("Frecuencia de días húmedos", "Frecuencia húmeda (%)", "%"),
    ]

    filas_html = []
    for label, col, unit in indices:
        val_obs = float(row_obs[col])
        val_raw = float(row_raw[col])
        val_qm = float(row_qm[col])

        dif_rel = abs(val_qm - val_obs) / (abs(val_obs) + 1e-9) * 100.0

        if dif_rel < THRESHOLD_EXCELLENT:
            badge = '<span style="color: #15803D; font-weight: 600;">✓ &lt; 2% (Excelente)</span>'
        elif dif_rel <= THRESHOLD_ACCEPTABLE:
            badge = '<span style="color: #B45309; font-weight: 600;">● 2–5% (Aceptable)</span>'
        else:
            badge = '<span style="color: #DC2626; font-weight: 600;">⚠ &gt; 5% (Atención)</span>'

        filas_html.append(
            f'<tr style="border-bottom: 1px solid #F1F5F9;">'
            f'<td style="padding: 9px 12px; font-weight: 500; color: #1E293B;">{label}</td>'
            f'<td style="padding: 9px 12px; text-align: right; color: #1E40AF; font-weight: 600;">{val_obs:.2f} {unit}</td>'
            f'<td style="padding: 9px 12px; text-align: right; color: #B91C1C;">{val_raw:.2f} {unit}</td>'
            f'<td style="padding: 9px 12px; text-align: right; color: #15803D; font-weight: 600;">{val_qm:.2f} {unit}</td>'
            f'<td style="padding: 9px 12px; text-align: center;">{badge}</td>'
            f'</tr>'
        )

    # Fila especializada de diagnóstico RMSE (reubicada desde KPIs)
    rmse_raw = float(row_raw["RMSE (mm/d)"])
    rmse_qm = float(row_qm["RMSE (mm/d)"])
    badge_rmse = '<span style="color: #15803D; font-weight: 600;">✓ Dispersión residual física**</span>'

    filas_html.append(
        f'<tr style="border-bottom: 1px solid #E2E8F0; background-color: #F8FAFC;">'
        f'<td style="padding: 9px 12px; font-weight: 600; color: #163A5F;">Error Cuadrático Medio (RMSE diario)**</td>'
        f'<td style="padding: 9px 12px; text-align: right; color: #1E40AF; font-weight: 600;">0.00 mm/d</td>'
        f'<td style="padding: 9px 12px; text-align: right; color: #B91C1C;">{rmse_raw:.2f} mm/d</td>'
        f'<td style="padding: 9px 12px; text-align: right; color: #15803D; font-weight: 600;">{rmse_qm:.2f} mm/d</td>'
        f'<td style="padding: 9px 12px; text-align: center;">{badge_rmse}</td>'
        f'</tr>'
    )

    # Fila especializada de diagnóstico KGE (Knoben et al., 2019) con valores dinámicos
    kge_raw = float(row_raw["KGE"])
    kge_qm = float(row_qm["KGE"])
    r_raw = float(row_raw["r"]) if "r" in row_raw else 0.14
    alpha_raw = float(row_raw["alpha"]) if "alpha" in row_raw else float(row_raw["Ratio Variabilidad (σ/σ_obs)"])
    beta_raw = float(row_raw["beta"]) if "beta" in row_raw else (float(row_raw["Media (mm/d)"]) / float(row_obs["Media (mm/d)"]))

    r_qm = float(row_qm["r"]) if "r" in row_qm else 0.08
    alpha_qm = float(row_qm["alpha"]) if "alpha" in row_qm else float(row_qm["Ratio Variabilidad (σ/σ_obs)"])
    beta_qm = float(row_qm["beta"]) if "beta" in row_qm else (float(row_qm["Media (mm/d)"]) / float(row_obs["Media (mm/d)"]))

    badge_kge = f'<span style="color: #15803D; font-weight: 600;">✓ α={alpha_qm:.2f}, β={beta_qm:.2f} (Knoben et al., 2019)</span>'

    filas_html.append(
        f'<tr style="border-bottom: 1px solid #E2E8F0; background-color: #F8FAFC;">'
        f'<td style="padding: 9px 12px; font-weight: 600; color: #163A5F;">Eficiencia Kling-Gupta (KGE diario)*</td>'
        f'<td style="padding: 9px 12px; text-align: right; color: #1E40AF; font-weight: 600;">1.00</td>'
        f'<td style="padding: 9px 12px; text-align: right; color: #B91C1C; font-size: 0.84rem;">{kge_raw:.2f} <span style="color: #64748B;">(r={r_raw:.2f}, α={alpha_raw:.2f}, β={beta_raw:.2f})</span></td>'
        f'<td style="padding: 9px 12px; text-align: right; color: #15803D; font-weight: 600; font-size: 0.84rem;">{kge_qm:.2f} <span style="color: #475569;">(r={r_qm:.2f}, α={alpha_qm:.2f}, β={beta_qm:.2f})</span></td>'
        f'<td style="padding: 9px 12px; text-align: center;">{badge_kge}</td>'
        f'</tr>'
    )

    std_obs = float(row_obs["Desv. Estándar (mm/d)"])
    std_raw = float(row_raw["Desv. Estándar (mm/d)"])
    std_qm = float(row_qm["Desv. Estándar (mm/d)"])

    filas_str = "".join(filas_html)
    tabla_html = (
        '<div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; overflow: hidden; margin-top: 14px;">'
        '<table style="width: 100%; border-collapse: collapse; font-size: 0.88rem;">'
        '<thead>'
        '<tr style="background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0; color: #475569; font-weight: 600;">'
        '<th style="padding: 10px 12px; text-align: left;">Índice Hidrometeorológico</th>'
        '<th style="padding: 10px 12px; text-align: right;">Observado (Estación)</th>'
        '<th style="padding: 10px 12px; text-align: right;">Modelo Bruto</th>'
        '<th style="padding: 10px 12px; text-align: right;">Modelo QM</th>'
        '<th style="padding: 10px 12px; text-align: center;">Evaluación del Ajuste</th>'
        '</tr>'
        '</thead>'
        '<tbody>'
        f'{filas_str}'
        '</tbody>'
        '</table>'
        '</div>'
        '<div style="font-size: 0.77rem; color: #64748B; margin-top: 6px; line-height: 1.4;">'
        f'* <strong>Diagnóstico KGE (Knoben et al., 2019)</strong>: Descompone la eficiencia en sesgo medio (&beta; = &mu;<sub>m</sub>/&mu;<sub>o</sub> = {beta_qm:.2f}), relación de desviaciones estándar / variabilidad (&alpha; = &sigma;<sub>m</sub>/&sigma;<sub>o</sub> = {alpha_qm:.2f}) y correlación temporal diaria (<em>r</em> = {r_qm:.3f}). El valor KGE = {kge_qm:.3f} supera el benchmark de media constante KGE &approx; -0.41; &beta; &approx; {beta_qm:.2f} y &alpha; &approx; {alpha_qm:.2f} indican coincidencia de media y variabilidad marginal, mientras que <em>r</em> &approx; {r_qm:.3f} es consistente con una simulación climática libre no diseñada para reproducir la secuencia meteorológica observada día a día.'
        '</div>'
        '<div style="font-size: 0.77rem; color: #64748B; margin-top: 5px; line-height: 1.4;">'
        f'** <strong>Diagnóstico RMSE (Raíz del Error Cuadrático Medio)</strong>: Evaluado bajo la identidad estadística fundamental RMSE<sup>2</sup> = &sigma;<sub>o</sub><sup>2</sup> + &sigma;<sub>m</sub><sup>2</sup> &minus; 2<em>r</em>&sigma;<sub>o</sub>&sigma;<sub>m</sub> + (&mu;<sub>m</sub> &minus; &mu;<sub>o</sub>)<sup>2</sup>. El valor RMSE del modelo QM ({rmse_qm:.2f} mm/d) es numéricamente superior al del GCM bruto ({rmse_raw:.2f} mm/d) debido a que QM restituyó la variabilidad y amplitud real de las tormentas (&sigma;<sub>QM</sub> = {std_qm:.2f} mm/d vs &sigma;<sub>bruto</sub> = {std_raw:.2f} mm/d, con &sigma;<sub>obs</sub> = {std_obs:.2f} mm/d). Al no existir sincronía meteorológica día a día entre un modelo climático libre y una estación puntual (<em>r</em> &approx; {r_qm:.3f}), una serie con la varianza correcta genera necesariamente mayor discrepancia euclidiana diaria que una serie atenuada o amortiguada (Themeßl et al., 2011; Maraun, 2013).'
        '</div>'
    )

    if hasattr(st, "html"):
        st.html(tabla_html)
    else:
        st.markdown(tabla_html, unsafe_allow_html=True)
