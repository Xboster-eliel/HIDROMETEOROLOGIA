"""
Script de verificación y pruebas automatizadas del motor qm_core.py con data QM.csv.
"""
import sys
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
    ejecutar_ejemplo_pedagogico
)

def run_tests():
    data_file = Path("data QM.csv")
    assert data_file.exists(), f"No se encontró {data_file}"
    print("[1/6] Cargando datos...")
    modelo, observado = cargar_datos_qm(data_file)
    print(f"   Modelo: {len(modelo)} registros | Rango: {modelo['fecha'].min().date()} a {modelo['fecha'].max().date()}")
    print(f"   Observado: {len(observado)} registros | Rango: {observado['fecha'].min().date()} a {observado['fecha'].max().date()}")
    assert len(modelo) > 50000, "Registros de modelo insuficientes"
    assert len(observado) > 20000, "Registros observados insuficientes"

    print("[2/6] Verificando inventario...")
    inv = generar_inventario(modelo, observado)
    print(inv)
    assert len(inv) == 2, "El inventario debe tener 2 filas"

    print("[3/6] Preparando calibración 1959–2014...")
    f_start = pd.Timestamp("1959-01-01")
    f_end = pd.Timestamp("2014-12-31")
    cal = preparar_periodo_calibracion(modelo, observado, f_start, f_end)
    print(f"   Días de calibración comunes: {len(cal)}")
    assert len(cal) == 20454, f"Esperado 20454 días, obtenido {len(cal)}"

    print("[4/6] Calibrando EQM mensual...")
    params = fit_eqm_mensual(cal, wet_threshold=0.1, n_quantiles=1001)
    assert len(params) == 12, "Deben calibrarse los 12 meses"
    for m in range(1, 13):
        assert "umbral_mod" in params[m]
        assert "p_seco_obs" in params[m]
        assert len(params[m]["q"]) == 1001

    print("[5/6] Aplicando EQM a serie de calibración y a serie completa 1950–2100...")
    qm_cal, fuera_cal = apply_eqm_mensual(cal["fecha"], cal["modelo_mm"], params)
    cal["qm_mm"] = qm_cal
    cal["fuera_soporte"] = fuera_cal

    # Comparar métricas
    m_cal = tabla_metricas_comparativas(cal["obs_mm"].to_numpy(), cal["modelo_mm"].to_numpy(), qm_cal)
    print("   Tabla de métricas de calibración:")
    print(m_cal[["Serie", "Media (mm/d)", "Mediana (mm/d)", "P95 (mm/d)", "Frecuencia seca (%)", "Sesgo relativo Media (%)"]])

    # Aplicar a serie completa
    qm_todo, fuera_todo = apply_eqm_mensual(modelo["fecha"], modelo["pr_mm_dia"], params)
    print(f"   Casos fuera de soporte en serie completa: {int(fuera_todo.sum())}")

    print("[6/6] Probando ECDF, QQ y ejemplo pedagógico...")
    x_ecdf, p_ecdf = calcular_ecdf(qm_cal)
    assert len(x_ecdf) == len(qm_cal)

    qq = calcular_qq_points(cal["obs_mm"].to_numpy(), cal["modelo_mm"].to_numpy(), qm_cal)
    assert len(qq["quantiles"]) == 100

    tabla_ej, sesgo_ej = ejecutar_ejemplo_pedagogico()
    assert len(tabla_ej) == 10

    print("========================================")
    print("TODAS LAS PRUEBAS COMPLETADAS CON ÉXITO.")
    print("========================================")

if __name__ == "__main__":
    run_tests()
