"""
Módulo de cálculo y procesamiento para Quantile Mapping (QM) en Hidrometeorología.
Implementa Empirical Quantile Mapping (EQM) mensual con corrección de días secos/húmedos,
diagnósticos estadísticos, métricas hidrometeorológicas y detección de soporte.
"""

from typing import Dict, Any, Tuple, Optional, Union
import numpy as np
import pandas as pd
from pathlib import Path
import io


def a_numero_serie(s: pd.Series) -> pd.Series:
    """Convierte una serie de texto con posibles comas decimales a flotante."""
    return pd.to_numeric(
        s.astype(str).str.strip().str.replace(",", ".", regex=False),
        errors="coerce"
    )


def cargar_datos_qm(
    fuente: Union[str, Path, io.BytesIO, io.StringIO],
    nombre_archivo: Optional[str] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Carga y procesa el archivo de datos (CSV u ODS) con la estructura de 2 bloques:
    Bloque 1 (cols 0..2): Modelo climático (fecha, pr_mm_dia, modelo)
    Bloque 2 (cols 4..6): Observación estación (fecha, pr_mm_dia, estacion)
    """
    ext = ""
    if isinstance(fuente, (str, Path)):
        ext = Path(fuente).suffix.lower()
    elif nombre_archivo:
        ext = Path(nombre_archivo).suffix.lower()
    else:
        ext = ".csv"

    if ext == ".csv":
        raw = pd.read_csv(fuente, header=2, dtype=str)
    elif ext == ".ods":
        raw = pd.read_excel(fuente, header=2, dtype=str, engine="odf")
    else:
        # Intento fallback con csv
        raw = pd.read_csv(fuente, header=2, dtype=str)

    if raw.shape[1] < 7:
        raise ValueError(
            f"El archivo debe contener al menos 7 columnas estructuradas en dos bloques. "
            f"Columnas detectadas: {raw.shape[1]}"
        )

    # Serie simulada por el modelo
    modelo = pd.DataFrame({
        "fecha": pd.to_datetime(raw.iloc[:, 0], dayfirst=True, errors="coerce"),
        "pr_mm_dia": a_numero_serie(raw.iloc[:, 1]),
        "modelo": raw.iloc[:, 2].astype(str).str.strip()
    }).dropna(subset=["fecha", "pr_mm_dia"])

    # Serie observada en estación
    observado = pd.DataFrame({
        "fecha": pd.to_datetime(raw.iloc[:, 4], dayfirst=True, errors="coerce"),
        "pr_mm_dia": a_numero_serie(raw.iloc[:, 5]),
        "estacion": raw.iloc[:, 6].astype(str).str.strip()
    }).dropna(subset=["fecha", "pr_mm_dia"])

    modelo = modelo.sort_values("fecha").reset_index(drop=True)
    observado = observado.sort_values("fecha").reset_index(drop=True)

    return modelo, observado


def generar_inventario(modelo: pd.DataFrame, observado: pd.DataFrame) -> pd.DataFrame:
    """Genera una tabla de resumen del inventario de datos para ambas series."""
    def fila_inventario(df: pd.DataFrame, etiqueta: str, col_id: str):
        ids = df[col_id].dropna().astype(str).unique()
        id_str = ", ".join(ids) if len(ids) > 0 else "N/A"
        f_min = df["fecha"].min().strftime("%Y-%m-%d") if not df.empty else "N/A"
        f_max = df["fecha"].max().strftime("%Y-%m-%d") if not df.empty else "N/A"
        return {
            "Serie": etiqueta,
            "Identificador": id_str,
            "Fecha inicial": f_min,
            "Fecha final": f_max,
            "Registros (N)": len(df),
            "NaNs precipitación": int(df["pr_mm_dia"].isna().sum()),
            "Mínimo (mm/d)": float(df["pr_mm_dia"].min()) if not df.empty else 0.0,
            "Máximo (mm/d)": float(df["pr_mm_dia"].max()) if not df.empty else 0.0,
        }

    return pd.DataFrame([
        fila_inventario(modelo, "Modelo climático", "modelo"),
        fila_inventario(observado, "Observación pluviométrica", "estacion")
    ])


def preparar_periodo_calibracion(
    modelo: pd.DataFrame,
    observado: pd.DataFrame,
    f_inicio: pd.Timestamp,
    f_fin: pd.Timestamp
) -> pd.DataFrame:
    """Extrae y cruza el periodo común de calibración entre modelo y observaciones."""
    mod_cal = modelo.loc[
        modelo["fecha"].between(f_inicio, f_fin),
        ["fecha", "pr_mm_dia"]
    ].rename(columns={"pr_mm_dia": "modelo_mm"})

    obs_cal = observado.loc[
        observado["fecha"].between(f_inicio, f_fin),
        ["fecha", "pr_mm_dia"]
    ].rename(columns={"pr_mm_dia": "obs_mm"})

    cal = mod_cal.merge(obs_cal, on="fecha", how="inner").dropna()
    cal["mes"] = cal["fecha"].dt.month
    return cal.sort_values("fecha").reset_index(drop=True)


def fit_eqm_mensual(
    cal_df: pd.DataFrame,
    wet_threshold: float = 0.1,
    n_quantiles: int = 1001
) -> Dict[int, Dict[str, Any]]:
    """
    Ajusta Empirical Quantile Mapping (EQM) mensual con corrección de frecuencia seca.
    """
    qs = np.linspace(0.0, 1.0, n_quantiles)
    params = {}

    for mes in range(1, 13):
        sub = cal_df.loc[cal_df["mes"] == mes]
        if sub.empty:
            raise ValueError(f"No hay registros de calibración para el mes {mes}.")

        m = sub["modelo_mm"].to_numpy(dtype=float)
        o = sub["obs_mm"].to_numpy(dtype=float)

        # Truncar valores bajo el umbral húmedo a 0
        o_trunc = np.where(o < wet_threshold, 0.0, o)
        p_seco_obs = float(np.mean(o_trunc == 0.0))

        # Determinar el umbral en el modelo correspondiente a p_seco_obs
        umbral_mod = float(np.quantile(m, p_seco_obs))

        m_hum = m[m > umbral_mod]
        o_hum = o_trunc[o_trunc > 0.0]

        if len(m_hum) < 10 or len(o_hum) < 10:
            raise ValueError(
                f"Muestra de días húmedos insuficiente en el mes {mes} "
                f"(Modelo: {len(m_hum)}, Observado: {len(o_hum)})."
            )

        params[mes] = {
            "q": qs,
            "mod_q": np.quantile(m_hum, qs),
            "obs_q": np.quantile(o_hum, qs),
            "p_seco_obs": p_seco_obs,
            "umbral_mod": umbral_mod,
            "wet_threshold_obs": wet_threshold,
            "n_obs_hum": len(o_hum),
            "n_mod_hum": len(m_hum),
        }

    return params


def apply_eqm_mensual(
    fechas: pd.Series,
    valores: Union[pd.Series, np.ndarray],
    params: Dict[int, Dict[str, Any]]
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Aplica EQM mensual de manera vectorizada y rápida.
    Retorna: (valores_corregidos, mascara_fuera_soporte)
    """
    fechas = pd.to_datetime(fechas)
    valores = np.asarray(valores, dtype=float)
    meses = fechas.dt.month.to_numpy()

    corregidos = np.zeros(len(valores), dtype=float)
    fuera_soporte = np.zeros(len(valores), dtype=bool)

    for mes in range(1, 13):
        p = params[mes]
        idx_mes = np.where(meses == mes)[0]
        if len(idx_mes) == 0:
            continue

        vals_mes = valores[idx_mes]
        umbral_mod = p["umbral_mod"]
        mod_q_max = p["mod_q"][-1]

        # Días secos modelados
        mask_seco = vals_mes <= umbral_mod
        corregidos[idx_mes[mask_seco]] = 0.0

        # Días húmedos
        mask_hum = ~mask_seco
        if np.any(mask_hum):
            idx_hum = idx_mes[mask_hum]
            vals_hum = vals_mes[mask_hum]

            # Marcar extrapolación si excede el máximo de calibración del modelo
            fuera_soporte[idx_hum[vals_hum > mod_q_max]] = True

            # Interpolar percentil en distribución de modelo húmedo
            prob = np.interp(vals_hum, p["mod_q"], p["q"], left=0.0, right=1.0)
            # Evaluar cuantil en distribución observada húmeda
            corregidos[idx_hum] = np.interp(prob, p["q"], p["obs_q"])

    return corregidos, fuera_soporte


def metricas_precipitacion(x: Union[pd.Series, np.ndarray], wet_threshold: float = 0.1) -> Dict[str, float]:
    """Calcula estadísticas hidrometeorológicas descriptivas para una serie."""
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return {}
    return {
        "N": len(x),
        "Media (mm/d)": float(np.mean(x)),
        "Mediana (mm/d)": float(np.median(x)),
        "Desv. Estándar (mm/d)": float(np.std(x)),
        "P95 (mm/d)": float(np.quantile(x, 0.95)),
        "P99 (mm/d)": float(np.quantile(x, 0.99)),
        "Máximo (mm/d)": float(np.max(x)),
        "Frecuencia húmeda (%)": float(100.0 * np.mean(x >= wet_threshold)),
        "Frecuencia seca (%)": float(100.0 * np.mean(x < wet_threshold)),
    }


def tabla_metricas_comparativas(
    obs: np.ndarray,
    mod_raw: np.ndarray,
    mod_qm: np.ndarray,
    wet_threshold: float = 0.1
) -> pd.DataFrame:
    """Compara métricas de precipitación, sesgos e índices de eficiencia hidrológica (KGE, RMSE)."""
    m_obs = metricas_precipitacion(obs, wet_threshold)
    m_raw = metricas_precipitacion(mod_raw, wet_threshold)
    m_qm = metricas_precipitacion(mod_qm, wet_threshold)

    # Sesgos porcentuales relativos
    bias_media_raw = ((m_raw["Media (mm/d)"] - m_obs["Media (mm/d)"]) / (m_obs["Media (mm/d)"] + 1e-9)) * 100
    bias_media_qm = ((m_qm["Media (mm/d)"] - m_obs["Media (mm/d)"]) / (m_obs["Media (mm/d)"] + 1e-9)) * 100

    rmse_raw = float(np.sqrt(np.mean((mod_raw - obs)**2)))
    rmse_qm = float(np.sqrt(np.mean((mod_qm - obs)**2)))
    mae_raw = float(np.mean(np.abs(mod_raw - obs)))
    mae_qm = float(np.mean(np.abs(mod_qm - obs)))

    # Ratios de variabilidad (desviación estándar)
    std_obs = m_obs["Desv. Estándar (mm/d)"]
    ratio_std_raw = m_raw["Desv. Estándar (mm/d)"] / (std_obs + 1e-9)
    ratio_std_qm = m_qm["Desv. Estándar (mm/d)"] / (std_obs + 1e-9)

    # Kling-Gupta Efficiency (KGE)
    r_raw = float(np.corrcoef(mod_raw, obs)[0, 1]) if std_obs > 0 else 0.0
    r_qm = float(np.corrcoef(mod_qm, obs)[0, 1]) if std_obs > 0 else 0.0

    beta_raw = m_raw["Media (mm/d)"] / (m_obs["Media (mm/d)"] + 1e-9)
    beta_qm = m_qm["Media (mm/d)"] / (m_obs["Media (mm/d)"] + 1e-9)

    kge_raw = float(1.0 - np.sqrt((r_raw - 1.0)**2 + (ratio_std_raw - 1.0)**2 + (beta_raw - 1.0)**2))
    kge_qm = float(1.0 - np.sqrt((r_qm - 1.0)**2 + (ratio_std_qm - 1.0)**2 + (beta_qm - 1.0)**2))

    # Construcción de la tabla
    df = pd.DataFrame([
        {
            "Serie": "Observado (Estación)",
            **m_obs,
            "Ratio Variabilidad (σ/σ_obs)": 1.0,
            "Sesgo relativo Media (%)": 0.0,
            "RMSE (mm/d)": 0.0,
            "MAE (mm/d)": 0.0,
            "KGE": 1.0,
            "r": 1.0,
            "alpha": 1.0,
            "beta": 1.0,
        },
        {
            "Serie": "Modelo Bruto (GCM)",
            **m_raw,
            "Ratio Variabilidad (σ/σ_obs)": ratio_std_raw,
            "Sesgo relativo Media (%)": bias_media_raw,
            "RMSE (mm/d)": rmse_raw,
            "MAE (mm/d)": mae_raw,
            "KGE": kge_raw,
            "r": r_raw,
            "alpha": ratio_std_raw,
            "beta": beta_raw,
        },
        {
            "Serie": "Modelo Corregido QM",
            **m_qm,
            "Ratio Variabilidad (σ/σ_obs)": ratio_std_qm,
            "Sesgo relativo Media (%)": bias_media_qm,
            "RMSE (mm/d)": rmse_qm,
            "MAE (mm/d)": mae_qm,
            "KGE": kge_qm,
            "r": r_qm,
            "alpha": ratio_std_qm,
            "beta": beta_qm,
        }
    ])
    return df


def calcular_metricas_error(
    obs: np.ndarray,
    mod_raw: np.ndarray,
    mod_qm: np.ndarray,
    wet_threshold: float = 0.1
) -> Dict[str, float]:
    """
    Calcula de forma instantánea el resumen de errores y eficiencias
    entre las observaciones y las series de modelo (bruto y QM).
    """
    obs = np.asarray(obs, dtype=float)
    raw = np.asarray(mod_raw, dtype=float)
    qm = np.asarray(mod_qm, dtype=float)

    mu_obs = float(np.mean(obs))
    mu_raw = float(np.mean(raw))
    mu_qm = float(np.mean(qm))

    std_obs = float(np.std(obs))
    std_raw = float(np.std(raw))
    std_qm = float(np.std(qm))

    rmse_raw = float(np.sqrt(np.mean((raw - obs)**2)))
    rmse_qm = float(np.sqrt(np.mean((qm - obs)**2)))

    mae_raw = float(np.mean(np.abs(raw - obs)))
    mae_qm = float(np.mean(np.abs(qm - obs)))

    bias_raw_pct = ((mu_raw - mu_obs) / (mu_obs + 1e-9)) * 100.0
    bias_qm_pct = ((mu_qm - mu_obs) / (mu_obs + 1e-9)) * 100.0

    r_raw = float(np.corrcoef(raw, obs)[0, 1]) if (std_obs > 0 and std_raw > 0) else 0.0
    r_qm = float(np.corrcoef(qm, obs)[0, 1]) if (std_obs > 0 and std_qm > 0) else 0.0

    alpha_raw = std_raw / (std_obs + 1e-9)
    alpha_qm = std_qm / (std_obs + 1e-9)

    beta_raw = mu_raw / (mu_obs + 1e-9)
    beta_qm = mu_qm / (mu_obs + 1e-9)

    kge_raw = float(1.0 - np.sqrt((r_raw - 1.0)**2 + (alpha_raw - 1.0)**2 + (beta_raw - 1.0)**2))
    kge_qm = float(1.0 - np.sqrt((r_qm - 1.0)**2 + (alpha_qm - 1.0)**2 + (beta_qm - 1.0)**2))

    red_rmse_pct = ((rmse_raw - rmse_qm) / (rmse_raw + 1e-9)) * 100.0
    red_mae_pct = ((mae_raw - mae_qm) / (mae_raw + 1e-9)) * 100.0

    return {
        "rmse_raw": rmse_raw,
        "rmse_qm": rmse_qm,
        "red_rmse_pct": red_rmse_pct,
        "mae_raw": mae_raw,
        "mae_qm": mae_qm,
        "red_mae_pct": red_mae_pct,
        "bias_raw_pct": bias_raw_pct,
        "bias_qm_pct": bias_qm_pct,
        "kge_raw": kge_raw,
        "kge_qm": kge_qm,
        "r_raw": r_raw,
        "r_qm": r_qm,
        "alpha_raw": alpha_raw,
        "alpha_qm": alpha_qm,
        "beta_raw": beta_raw,
        "beta_qm": beta_qm,
    }



def calcular_ecdf(valores: Union[pd.Series, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
    """Calcula la función de distribución empírica acumulada (ECDF)."""
    x = np.sort(np.asarray(valores, dtype=float))
    p = np.arange(1, len(x) + 1) / len(x)
    return x, p


def calcular_qq_points(
    obs: np.ndarray,
    mod_raw: np.ndarray,
    mod_qm: np.ndarray,
    n_points: int = 100
) -> Dict[str, np.ndarray]:
    """Calcula cuantiles ordenados para graficar el diagnóstico Q-Q."""
    qplot = np.linspace(0.01, 0.99, n_points)
    return {
        "quantiles": qplot,
        "obs": np.quantile(obs, qplot),
        "mod_raw": np.quantile(mod_raw, qplot),
        "mod_qm": np.quantile(mod_qm, qplot),
    }


def ejecutar_ejemplo_pedagogico(
    modelo_ej: Optional[np.ndarray] = None,
    observado_ej: Optional[np.ndarray] = None
) -> Tuple[pd.DataFrame, float]:
    """
    Ejemplo pedagógico demostrativo con vectores cortos de prueba
    (replica celdas 8 y 9 del notebook).
    """
    if modelo_ej is None:
        modelo_ej = np.array([2, 5, 8, 12, 15, 20, 25, 30, 40, 50], dtype=float)
    if observado_ej is None:
        observado_ej = np.array([1, 4, 7, 10, 14, 18, 28, 35, 48, 65], dtype=float)

    modelo_ord = np.sort(modelo_ej)
    obs_ord = np.sort(observado_ej)

    percentiles = np.searchsorted(modelo_ord, modelo_ej, side="right") / len(modelo_ord)
    qm_ej = np.quantile(obs_ord, percentiles)

    tabla = pd.DataFrame({
        "Modelo original Xm (mm)": modelo_ej,
        "Cuantil empírico p": np.round(percentiles, 4),
        "QM corregido Xqm (mm)": np.round(qm_ej, 2),
        "Observado referencia Xo (mm)": observado_ej,
    })

    sesgo_antes = float(np.mean(modelo_ej) - np.mean(observado_ej))
    return tabla, sesgo_antes
