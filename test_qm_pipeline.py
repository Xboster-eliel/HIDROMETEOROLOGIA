"""
Suite de pruebas automatizadas con pytest para el motor hidrometeorológico qm_core.py.
Incluye verificación algebraica rigurosa de la identidad estadística del RMSE y KGE.
"""
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from qm_core import (
    cargar_datos_qm,
    generar_inventario,
    preparar_periodo_calibracion,
    fit_eqm_mensual,
    apply_eqm_mensual,
    metricas_precipitacion,
    tabla_metricas_comparativas,
    calcular_ecdf,
    calcular_qq_points,
    ejecutar_ejemplo_pedagogico,
)

DATA_PATH = Path("data QM.csv")


@pytest.fixture(scope="module")
def datasets():
    assert DATA_PATH.exists(), f"No se encontró {DATA_PATH}"
    modelo, observado = cargar_datos_qm(DATA_PATH)
    return modelo, observado


@pytest.fixture(scope="module")
def calibracion_base(datasets):
    modelo, observado = datasets
    f_start = pd.Timestamp("1959-01-01")
    f_end = pd.Timestamp("2014-12-31")
    cal = preparar_periodo_calibracion(modelo, observado, f_start, f_end)
    params = fit_eqm_mensual(cal, wet_threshold=0.1, n_quantiles=1001)
    qm_cal, fuera_cal = apply_eqm_mensual(cal["fecha"], cal["modelo_mm"], params)
    cal["qm_mm"] = qm_cal
    cal["fuera_soporte"] = fuera_cal
    return cal, params


def test_carga_datos(datasets):
    """Verifica la correcta ingestión de los bloques de datos desde CSV."""
    modelo, observado = datasets
    assert len(modelo) == 55152, f"Esperados 55152 registros en modelo, obtenidos {len(modelo)}"
    assert len(observado) == 24462, f"Esperados 24462 registros observados, obtenidos {len(observado)}"
    assert modelo["fecha"].min() == pd.Timestamp("1950-01-01")
    assert modelo["fecha"].max() == pd.Timestamp("2100-12-31")
    assert observado["fecha"].min() == pd.Timestamp("1959-01-01")


def test_inventario(datasets):
    """Verifica la generación de la tabla resumen de inventario."""
    modelo, observado = datasets
    inv = generar_inventario(modelo, observado)
    assert len(inv) == 2
    assert "MPI-ESM1-2-HR" in inv.loc[inv["Serie"] == "Modelo climático", "Identificador"].values[0]
    assert "Carolina" in inv.loc[inv["Serie"] == "Observación pluviométrica", "Identificador"].values[0]


def test_periodo_calibracion(calibracion_base):
    """Verifica la extracción y aislamiento del periodo común de calibración (1959–2014)."""
    cal, _ = calibracion_base
    assert len(cal) == 20454, f"Esperados 20454 días de calibración, obtenidos {len(cal)}"
    assert cal["fecha"].min() == pd.Timestamp("1959-01-01")
    assert cal["fecha"].max() == pd.Timestamp("2014-12-31")


def test_calibracion_eqm_mensual(calibracion_base):
    """Verifica que los 12 meses cuenten con parámetros de cuantiles válidos."""
    _, params = calibracion_base
    assert len(params) == 12
    for m in range(1, 13):
        p = params[m]
        assert "umbral_mod" in p
        assert "p_seco_obs" in p
        assert len(p["q"]) == 1001
        assert len(p["mod_q"]) == 1001
        assert len(p["obs_q"]) == 1001
        assert 0.0 <= p["p_seco_obs"] <= 1.0
        assert p["umbral_mod"] >= 0.0


def test_aplicacion_eqm_y_soporte(datasets, calibracion_base):
    """Verifica la reducción del sesgo medio y la detección de extrapolación mensual."""
    modelo, _ = datasets
    cal, params = calibracion_base

    # Corrección en calibración
    bias_qm = ((cal["qm_mm"].mean() - cal["obs_mm"].mean()) / cal["obs_mm"].mean()) * 100.0
    assert abs(bias_qm) < 0.01, f"El sesgo relativo medio de QM debe ser < 0.01%, obtenido {bias_qm:.4f}%"

    # Eliminación de llovizna espuria
    wet_obs = 100.0 * np.mean(cal["obs_mm"] >= 0.1)
    wet_qm = 100.0 * np.mean(cal["qm_mm"] >= 0.1)
    assert abs(wet_obs - wet_qm) < 0.05, f"La frecuencia húmeda debe coincidir con la observación ({wet_obs:.2f}% vs {wet_qm:.2f}%)"

    # Extrapolación en la serie completa (1950–2100)
    _, fuera_todo = apply_eqm_mensual(modelo["fecha"], modelo["pr_mm_dia"], params)
    assert int(fuera_todo.sum()) == 33, f"Esperados exactamente 33 días fuera de soporte mensual, obtenidos {int(fuera_todo.sum())}"


def test_consistencia_algebraica_rmse_kge(calibracion_base):
    """
    Comprueba formalmente la identidad algebraica fundamental:
    RMSE^2 = Var(o) + Var(m) - 2*Cov(o, m) + (Mean(m) - Mean(o))^2
    Tanto para el Modelo Bruto (GCM) como para el Modelo Corregido (QM).
    """
    cal, _ = calibracion_base
    o = cal["obs_mm"].to_numpy(dtype=float)
    m_raw = cal["modelo_mm"].to_numpy(dtype=float)
    m_qm = cal["qm_mm"].to_numpy(dtype=float)

    # 1. Modelo Corregido (QM)
    var_o = float(np.var(o))
    var_qm = float(np.var(m_qm))
    cov_qm = float(np.cov(m_qm, o, ddof=0)[0, 1])
    diff_mu_qm = float(np.mean(m_qm) - np.mean(o))
    rmse_teorico_qm = np.sqrt(var_o + var_qm - 2.0 * cov_qm + diff_mu_qm**2)
    rmse_directo_qm = float(np.sqrt(np.mean((m_qm - o)**2)))

    assert np.isclose(rmse_teorico_qm, rmse_directo_qm, atol=1e-5), (
        f"Inconsistencia en RMSE QM: Teórico={rmse_teorico_qm:.6f} vs Directo={rmse_directo_qm:.6f}"
    )
    assert np.isclose(rmse_directo_qm, 18.614788, atol=1e-4), f"RMSE QM debe ser 18.6148, obtenido {rmse_directo_qm:.6f}"

    # 2. Modelo Bruto (GCM)
    var_raw = float(np.var(m_raw))
    cov_raw = float(np.cov(m_raw, o, ddof=0)[0, 1])
    diff_mu_raw = float(np.mean(m_raw) - np.mean(o))
    rmse_teorico_raw = np.sqrt(var_o + var_raw - 2.0 * cov_raw + diff_mu_raw**2)
    rmse_directo_raw = float(np.sqrt(np.mean((m_raw - o)**2)))

    assert np.isclose(rmse_teorico_raw, rmse_directo_raw, atol=1e-5), (
        f"Inconsistencia en RMSE Raw: Teórico={rmse_teorico_raw:.6f} vs Directo={rmse_directo_raw:.6f}"
    )
    assert np.isclose(rmse_directo_raw, 13.996360, atol=1e-4), f"RMSE Raw debe ser 13.9964, obtenido {rmse_directo_raw:.6f}"

    # 3. KGE QM comprobación paramétrica
    r_qm = float(np.corrcoef(m_qm, o)[0, 1])
    alpha_qm = float(np.std(m_qm) / np.std(o))
    beta_qm = float(np.mean(m_qm) / np.mean(o))
    kge_calculado = 1.0 - np.sqrt((r_qm - 1.0)**2 + (alpha_qm - 1.0)**2 + (beta_qm - 1.0)**2)

    tabla_met = tabla_metricas_comparativas(o, m_raw, m_qm)
    row_qm = tabla_met.loc[tabla_met["Serie"] == "Modelo Corregido QM"].iloc[0]
    assert np.isclose(kge_calculado, float(row_qm["KGE"]), atol=1e-5)
    assert np.isclose(kge_calculado, 0.077496, atol=1e-4)
    # Verificar nuevas columnas explícitas
    assert "r" in tabla_met.columns
    assert "alpha" in tabla_met.columns
    assert "beta" in tabla_met.columns
    assert np.isclose(float(row_qm["r"]), r_qm, atol=1e-5)
    assert np.isclose(float(row_qm["alpha"]), alpha_qm, atol=1e-5)
    assert np.isclose(float(row_qm["beta"]), beta_qm, atol=1e-5)


def test_metricas_error_embebidas(calibracion_base):
    """Verifica que la función calcular_metricas_error computa con precisión los errores para los gráficos."""
    from qm_core import calcular_metricas_error
    cal, _ = calibracion_base
    o = cal["obs_mm"].to_numpy(dtype=float)
    m_raw = cal["modelo_mm"].to_numpy(dtype=float)
    m_qm = cal["qm_mm"].to_numpy(dtype=float)

    err = calcular_metricas_error(o, m_raw, m_qm)
    assert np.isclose(err["rmse_qm"], 18.614788, atol=1e-4)
    assert np.isclose(err["rmse_raw"], 13.996360, atol=1e-4)
    assert abs(err["bias_qm_pct"]) < 0.01
    assert err["bias_raw_pct"] < 0.0
    assert err["mae_qm"] > 0.0
    assert err["mae_raw"] > 0.0
    assert np.isclose(err["kge_qm"], 0.077496, atol=1e-4)


def test_ecdf_qq_y_pedagogico(calibracion_base):
    """Verifica utilidades diagnósticas y ejemplo pedagógico interactivo."""
    cal, _ = calibracion_base
    x_ecdf, p_ecdf = calcular_ecdf(cal["qm_mm"])
    assert len(x_ecdf) == len(cal)
    assert p_ecdf[-1] == 1.0

    qq = calcular_qq_points(cal["obs_mm"].to_numpy(), cal["modelo_mm"].to_numpy(), cal["qm_mm"].to_numpy(), n_points=100)
    assert len(qq["quantiles"]) == 100

    tabla_ej, sesgo_ej = ejecutar_ejemplo_pedagogico()
    assert len(tabla_ej) == 10
    assert "QM corregido Xqm (mm)" in tabla_ej.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
