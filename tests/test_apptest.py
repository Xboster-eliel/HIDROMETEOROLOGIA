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
    # Verificar presencia de tabs y componentes
    assert len(app.tabs) == 4


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
