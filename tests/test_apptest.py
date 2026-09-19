"""
Suite de pruebas de integración de interfaz con Streamlit AppTest (Streamlit 1.58+).
Valida de forma automatizada la navegación, renderizado y ausencia de excepciones en las 4 páginas.
"""
import pytest
from streamlit.testing.v1 import AppTest

TIMEOUT = 35


@pytest.fixture(scope="module")
def app():
    """Inicializa la aplicación y orquestador multipágina."""
    at = AppTest.from_file("app.py", default_timeout=TIMEOUT)
    at.run(timeout=TIMEOUT)
    return at


def test_apptest_router_y_resumen(app):
    """Verifica que app.py inicie limpiamente, orqueste session_state y renderice Resumen."""
    assert len(app.exception) == 0, f"Excepción detectada en Resumen: {[e.value for e in app.exception]}"
    assert "cal" in app.session_state
    assert "params_qm" in app.session_state
    assert "modelo_todo" in app.session_state
    assert "metricas_df" in app.session_state
    assert "metadata" in app.session_state
    # Verificar que haya elementos renderizados en la página principal
    assert len(app.markdown) > 0
    assert len(app.latex) > 0


def test_apptest_diagnostico_page(app):
    """Verifica la navegación y renderizado del Módulo 2: Diagnóstico QM."""
    app.switch_page("pages/diagnostico.py").run(timeout=TIMEOUT)
    assert len(app.exception) == 0, f"Excepción detectada en Diagnóstico: {[e.value for e in app.exception]}"
    # Verificar presencia de tabs, latex y componentes
    assert len(app.tabs) == 4
    assert len(app.latex) > 0


def test_apptest_clima_page(app):
    """Verifica la navegación y renderizado del Módulo 3: Climatología y Clima Futuro."""
    app.switch_page("pages/clima.py").run(timeout=TIMEOUT)
    assert len(app.exception) == 0, f"Excepción detectada en Clima: {[e.value for e in app.exception]}"
    # Verificar presencia de selectboxes de variable y año
    assert len(app.selectbox) > 0


def test_apptest_metodologia_page(app):
    """Verifica la navegación y renderizado del Módulo 4: Metodología y Exportación."""
    app.switch_page("pages/metodologia.py").run(timeout=TIMEOUT)
    assert len(app.exception) == 0, f"Excepción detectada en Metodología: {[e.value for e in app.exception]}"
    # Verificar presencia de las 4 pestañas metodológicas y dataframe
    assert len(app.tabs) == 4
    assert len(app.dataframe) > 0


def test_apptest_reactividad_periodo_calibracion():
    """Verifica la recalibración y reactividad en tiempo real al variar el periodo de calibración."""
    at = AppTest.from_file("app.py", default_timeout=TIMEOUT)
    at.run(timeout=TIMEOUT)
    assert len(at.exception) == 0, f"Excepciones al iniciar: {[e.value for e in at.exception]}"

    # Cambiar periodo de calibración a 1970–1995 mediante slider de barra lateral
    slider = at.sidebar.slider(key="cal_range_slider")
    slider.set_value((1970, 1995)).run(timeout=TIMEOUT)
    assert len(at.exception) == 0, f"Excepciones tras cambiar slider: {[e.value for e in at.exception]}"
    assert at.session_state["metadata"]["cal_inicio"] == 1970
    assert at.session_state["metadata"]["cal_fin"] == 1995
    assert at.session_state["cal"]["fecha"].dt.year.min() == 1970
    assert at.session_state["cal"]["fecha"].dt.year.max() == 1995

    # Verificar que Resumen renderice limpiamente con el nuevo periodo
    at.switch_page("pages/resumen.py").run(timeout=TIMEOUT)
    assert len(at.exception) == 0, f"Excepciones en Resumen tras recalibración: {[e.value for e in at.exception]}"


def test_apptest_reactividad_ventana_inspeccion():
    """Verifica que la tabla de semáforo hidrometeorológico se sincronice con la ventana de inspección."""
    at = AppTest.from_file("app.py", default_timeout=TIMEOUT)
    at.run(timeout=TIMEOUT)
    assert len(at.exception) == 0

    # Seleccionar "Primeros 5 años" en la ventana de inspección diaria
    radio_zoom = at.radio(key="res_modo_zoom")
    radio_zoom.set_value("Primeros 5 años").run(timeout=TIMEOUT)
    assert len(at.exception) == 0, f"Excepciones tras cambiar zoom: {[e.value for e in at.exception]}"

    # Verificar que el selector de ámbito de la tabla aparezca y funcione
    radio_eval = at.radio(key="res_modo_eval_tabla")
    assert radio_eval is not None
    # Alternar a "Periodo completo"
    opciones = radio_eval.options
    assert len(opciones) == 2
    radio_eval.set_value(opciones[1]).run(timeout=TIMEOUT)
    assert len(at.exception) == 0, f"Excepciones tras alternar ámbito: {[e.value for e in at.exception]}"


def test_apptest_sincronizacion_diagnostico_qm():
    """Verifica que la página Diagnóstico QM esté sincronizada en tiempo real con la ventana dinámica."""
    at = AppTest.from_file("app.py", default_timeout=TIMEOUT)
    at.run(timeout=TIMEOUT)
    assert len(at.exception) == 0

    # 1. Seleccionar "Primeros 5 años" en Resumen
    at.radio(key="res_modo_zoom").set_value("Primeros 5 años").run(timeout=TIMEOUT)
    assert len(at.exception) == 0
    assert at.session_state["inspection_mode"] == "Primeros 5 años"

    # 2. Navegar a Diagnóstico QM y comprobar que hereda la ventana
    at.switch_page("pages/diagnostico.py").run(timeout=TIMEOUT)
    assert len(at.exception) == 0, f"Excepciones en Diagnóstico QM: {[e.value for e in at.exception]}"
    radio_diag = at.radio(key="diag_modo_zoom")
    assert radio_diag.value == "Primeros 5 años"
    assert len(at.tabs) == 4
    assert len(at.dataframe) > 0

    # 3. Modificar la ventana en Diagnóstico QM a "Primeros 10 años"
    radio_diag.set_value("Primeros 10 años").run(timeout=TIMEOUT)
    assert len(at.exception) == 0
    assert at.session_state["inspection_mode"] == "Primeros 10 años"

    # 4. Regresar a Resumen y comprobar sincronización bidireccional
    at.switch_page("pages/resumen.py").run(timeout=TIMEOUT)
    assert len(at.exception) == 0
    assert at.radio(key="res_modo_zoom").value == "Primeros 10 años"


def test_render_scientific_kpis_compatibilidad():
    """Verifica que render_scientific_kpis tolere firmas anteriores, nuevas y parámetros inesperados."""
    from ui.cards import render_scientific_kpis
    from unittest.mock import patch, MagicMock

    def mock_columns(spec):
        n = spec if isinstance(spec, int) else len(spec)
        return [MagicMock() for _ in range(n)]

    # Simular contexto de Streamlit para probar llamadas sin errores de ejecución
    with patch("streamlit.columns", side_effect=mock_columns):
        with patch("streamlit.html"), patch("streamlit.markdown"):
            # 1. Llamada clásica / mínima (evita missing argument si sólo se pasan los originales)
            render_scientific_kpis(
                bias_raw=-10.98,
                bias_qm=0.0,
                wet_obs=45.2,
                wet_raw=55.1,
                wet_qm=45.2,
                extrap_count=3,
                extrap_pct=0.005,
                rmse_qm=12.4
            )

            # 2. Llamada completa moderna con kwargs nuevos y argumentos extra imprevistos
            render_scientific_kpis(
                bias_raw=-10.98,
                bias_qm=0.0,
                wet_obs=45.2,
                wet_raw=55.1,
                wet_qm=45.2,
                extrap_count=3,
                extrap_pct=0.005,
                extrap_subtexto="3 posteriores a 2010",
                media_obs=8.62,
                media_raw=7.67,
                media_qm=8.62,
                cal_inicio=1981,
                cal_fin=2010,
                rmse_qm=12.4,
                parametro_desconocido=999,
                otro_parametro="test",
            )

            # 3. Llamada con valores None y vacíos
            render_scientific_kpis(
                bias_raw=None,
                bias_qm=None,
                wet_obs=None,
                wet_raw=None,
                wet_qm=None,
                extrap_count=None,
                extrap_pct=None,
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

