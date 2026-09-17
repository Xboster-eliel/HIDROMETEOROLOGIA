"""
Estilos CSS e integración de temas para Streamlit y Plotly.
"""

import streamlit as st
import plotly.graph_objects as go
from ui.constants import COLOR_REF

def inject_custom_css():
    """Inyecta reglas CSS para una interfaz hidroclimática sobria y limpia."""
    st.markdown(
        """
        <style>
        /* Tipografía y márgenes generales */
        h1, h2, h3, h4 {
            color: #163A5F !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-weight: 600;
        }
        
        /* Contenedores y tarjetas limpias */
        .sc-card {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 14px;
        }
        
        /* Pastilla de metadatos */
        .meta-pill {
            display: inline-block;
            background-color: #F1F5F9;
            color: #475569;
            border: 1px solid #CBD5E1;
            border-radius: 20px;
            padding: 4px 12px;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 12px;
        }
        
        /* Tarjetas de KPIs científicos */
        .kpi-box {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 14px 16px;
            text-align: left;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
        }
        .kpi-title {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748B;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .kpi-value {
            font-size: 1.6rem;
            font-weight: 700;
            color: #172033;
            line-height: 1.2;
        }
        .kpi-badge-good {
            color: #15803D;
            font-size: 0.82rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .kpi-badge-warn {
            color: #B45309;
            font-size: 0.82rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .kpi-badge-bad {
            color: #DC2626;
            font-size: 0.82rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        /* Marca minimalista de barra lateral */
        .brand-header {
            padding: 4px 0 16px 0;
            border-bottom: 1px solid #E2E8F0;
            margin-bottom: 16px;
        }
        .brand-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #163A5F;
            letter-spacing: -0.02em;
            margin: 0;
        }
        .brand-sub {
            font-size: 0.8rem;
            color: #64748B;
            margin: 2px 0 0 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_plotly_theme(
    fig: go.Figure,
    title: str = "",
    x_title: str = "",
    y_title: str = "",
    hovermode: str = "x unified",
    height: int = 420
) -> go.Figure:
    """Aplica formato gráfico uniforme para todas las figuras de Plotly."""
    fig.update_layout(
        template="plotly_white",
        title=dict(
            text=f"<b>{title}</b>" if title else "",
            font=dict(size=14, color="#172033"),
            x=0.01,
            y=0.96
        ),
        xaxis=dict(
            title=x_title,
            title_font=dict(size=12, color="#475569"),
            tickfont=dict(size=11, color="#475569"),
            gridcolor="#F1F5F9",
            linecolor="#CBD5E1",
            zeroline=False
        ),
        yaxis=dict(
            title=y_title,
            title_font=dict(size=12, color="#475569"),
            tickfont=dict(size=11, color="#475569"),
            gridcolor="#F1F5F9",
            linecolor="#CBD5E1",
            zeroline=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=11, color="#334155")
        ),
        hovermode=hovermode,
        height=height,
        margin=dict(l=45, r=25, t=55, b=45),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
    )
    return fig
