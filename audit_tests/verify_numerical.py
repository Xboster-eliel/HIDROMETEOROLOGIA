"""
Script de auditoría numérica independiente para verificar los cálculos científicos de V2.
Ejecuta cálculos sin reutilizar la lógica de presentación para evitar comprobaciones circulares.
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path

def run_independent_audit():
    csv_path = Path("data QM.csv")
    assert csv_path.exists(), "No se encontró data QM.csv"

    # 1. Lectura directa e independiente del CSV
    raw = pd.read_csv(csv_path, header=2, dtype=str)
    
    def parse_col(col):
        return pd.to_numeric(col.astype(str).str.strip().str.replace(",", ".", regex=False), errors="coerce")

    mod_raw = pd.DataFrame({
        "fecha": pd.to_datetime(raw.iloc[:, 0], dayfirst=True, errors="coerce"),
        "pr_mm": parse_col(raw.iloc[:, 1]),
        "modelo": raw.iloc[:, 2].astype(str).str.strip()
    }).dropna(subset=["fecha", "pr_mm"]).sort_values("fecha").reset_index(drop=True)

    obs_raw = pd.DataFrame({
        "fecha": pd.to_datetime(raw.iloc[:, 4], dayfirst=True, errors="coerce"),
        "pr_mm": parse_col(raw.iloc[:, 5]),
        "estacion": raw.iloc[:, 6].astype(str).str.strip()
    }).dropna(subset=["fecha", "pr_mm"]).sort_values("fecha").reset_index(drop=True)

    print(f"[AUDIT-DATA] Registros Modelo: {len(mod_raw)}, Rango: {mod_raw['fecha'].min().date()} a {mod_raw['fecha'].max().date()}")
    print(f"[AUDIT-DATA] Registros Observado: {len(obs_raw)}, Rango: {obs_raw['fecha'].min().date()} a {obs_raw['fecha'].max().date()}")

    # 2. Periodo de calibración 1959-01-01 a 2014-12-31
    CAL_START = pd.Timestamp("1959-01-01")
    CAL_END = pd.Timestamp("2014-12-31")
    WET_THRESH = 0.1

    cal_m = mod_raw.loc[mod_raw["fecha"].between(CAL_START, CAL_END), ["fecha", "pr_mm"]].rename(columns={"pr_mm": "mod_mm"})
    cal_o = obs_raw.loc[obs_raw["fecha"].between(CAL_START, CAL_END), ["fecha", "pr_mm"]].rename(columns={"pr_mm": "obs_mm"})
    cal = cal_m.merge(cal_o, on="fecha", how="inner").dropna().sort_values("fecha").reset_index(drop=True)
    cal["mes"] = cal["fecha"].dt.month

    N_cal = len(cal)
    print(f"[AUDIT-CAL] Días comunes en calibración: {N_cal}")

    # 3. Métricas independientes de la serie bruta y observada
    m_obs = cal["obs_mm"].to_numpy(dtype=float)
    m_raw_arr = cal["mod_mm"].to_numpy(dtype=float)

    mean_obs = float(np.mean(m_obs))
    mean_raw = float(np.mean(m_raw_arr))
    bias_raw_pct = float(((mean_raw - mean_obs) / mean_obs) * 100.0)
    wet_freq_obs = float(100.0 * np.mean(m_obs >= WET_THRESH))
    wet_freq_raw = float(100.0 * np.mean(m_raw_arr >= WET_THRESH))
    
    print(f"[AUDIT-METRICS] Media Obs: {mean_obs:.6f} mm/d")
    print(f"[AUDIT-METRICS] Media GCM Bruto: {mean_raw:.6f} mm/d")
    print(f"[AUDIT-METRICS] Sesgo Relativo GCM Bruto: {bias_raw_pct:.4f}%")
    print(f"[AUDIT-METRICS] Frecuencia Húmeda Obs: {wet_freq_obs:.4f}%")
    print(f"[AUDIT-METRICS] Frecuencia Húmeda GCM: {wet_freq_raw:.4f}%")

    # 4. Calibración mensual independiente de EQM
    qs = np.linspace(0.0, 1.0, 1001)
    params = {}
    for mes in range(1, 13):
        sub = cal.loc[cal["mes"] == mes]
        m = sub["mod_mm"].to_numpy(dtype=float)
        o = sub["obs_mm"].to_numpy(dtype=float)
        o_clean = np.where(o < WET_THRESH, 0.0, o)
        p_seco = float(np.mean(o_clean == 0.0))
        u_mod = float(np.quantile(m, p_seco))
        m_hum = m[m > u_mod]
        o_hum = o_clean[o_clean > 0.0]
        params[mes] = {
            "p_seco": p_seco,
            "u_mod": u_mod,
            "mod_q": np.quantile(m_hum, qs),
            "obs_q": np.quantile(o_hum, qs),
            "max_mod_cal": np.max(m_hum),
            "max_obs_cal": np.max(o_hum)
        }

    # Aplicar a calibración
    qm_cal = np.zeros(N_cal, dtype=float)
    fuera_cal = np.zeros(N_cal, dtype=bool)
    meses_cal = cal["mes"].to_numpy()

    for mes in range(1, 13):
        idx = np.where(meses_cal == mes)[0]
        vals = m_raw_arr[idx]
        p = params[mes]
        
        mask_sec = vals <= p["u_mod"]
        qm_cal[idx[mask_sec]] = 0.0
        
        mask_hum = ~mask_sec
        if np.any(mask_hum):
            idx_h = idx[mask_hum]
            vals_h = vals[mask_hum]
            fuera_cal[idx_h[vals_h > p["max_mod_cal"]]] = True
            prob = np.interp(vals_h, p["mod_q"], qs, left=0.0, right=1.0)
            qm_cal[idx_h] = np.interp(prob, qs, p["obs_q"])

    mean_qm = float(np.mean(qm_cal))
    bias_qm_pct = float(((mean_qm - mean_obs) / mean_obs) * 100.0)
    rmse_qm = float(np.sqrt(np.mean((qm_cal - m_obs)**2)))
    mae_qm = float(np.mean(np.abs(qm_cal - m_obs)))
    wet_freq_qm = float(100.0 * np.mean(qm_cal >= WET_THRESH))

    # KGE
    std_obs = float(np.std(m_obs))
    std_qm = float(np.std(qm_cal))
    std_raw = float(np.std(m_raw_arr))
    alpha_qm = std_qm / std_obs
    beta_qm = mean_qm / mean_obs
    r_qm = float(np.corrcoef(qm_cal, m_obs)[0, 1])
    kge_qm = float(1.0 - np.sqrt((r_qm - 1.0)**2 + (alpha_qm - 1.0)**2 + (beta_qm - 1.0)**2))

    print(f"[AUDIT-QM] Media QM Corregido: {mean_qm:.6f} mm/d")
    print(f"[AUDIT-QM] Sesgo Relativo QM: {bias_qm_pct:+.6f}%")
    print(f"[AUDIT-QM] RMSE QM: {rmse_qm:.4f} mm/d")
    print(f"[AUDIT-QM] MAE QM: {mae_qm:.4f} mm/d")
    print(f"[AUDIT-QM] Frecuencia Húmeda QM: {wet_freq_qm:.4f}%")
    print(f"[AUDIT-QM] Std Obs: {std_obs:.4f} | Std QM: {std_qm:.4f} (Ratio: {alpha_qm:.4f})")
    print(f"[AUDIT-QM] KGE QM: {kge_qm:.4f}")

    # 5. Aplicar a toda la serie del modelo (1950 a 2100) para contar extrapolación
    mod_all_arr = mod_raw["pr_mm"].to_numpy(dtype=float)
    mod_all_mes = mod_raw["fecha"].dt.month.to_numpy()
    N_all = len(mod_raw)
    fuera_all = np.zeros(N_all, dtype=bool)

    for mes in range(1, 13):
        idx = np.where(mod_all_mes == mes)[0]
        vals = mod_all_arr[idx]
        p = params[mes]
        mask_hum = vals > p["u_mod"]
        if np.any(mask_hum):
            idx_h = idx[mask_hum]
            vals_h = vals[mask_hum]
            fuera_all[idx_h[vals_h > p["max_mod_cal"]]] = True

    n_fuera_total = int(np.sum(fuera_all))
    pct_fuera_total = float((n_fuera_total / N_all) * 100.0)

    # Fuera post 2014
    post_mask = mod_raw["fecha"] > CAL_END
    n_fuera_post = int(np.sum(fuera_all & post_mask))

    print(f"[AUDIT-EXTRAP] Total eventos fuera de soporte (1950-2100): {n_fuera_total} ({pct_fuera_total:.4f}%)")
    print(f"[AUDIT-EXTRAP] Eventos fuera de soporte post-2014: {n_fuera_post}")

    # 6. Sesgo mensual independiente (Ene-Dic)
    print("[AUDIT-MONTHLY-BIAS]")
    monthly_results = []
    for mes in range(1, 13):
        idx = np.where(meses_cal == mes)[0]
        o_m = np.mean(m_obs[idx])
        r_m = np.mean(m_raw_arr[idx])
        q_m = np.mean(qm_cal[idx])
        b_raw = float(((r_m - o_m) / o_m) * 100.0)
        b_qm = float(((q_m - o_m) / o_m) * 100.0)
        monthly_results.append({
            "mes": mes, "mean_obs": o_m, "mean_raw": r_m, "mean_qm": q_m,
            "bias_raw_pct": b_raw, "bias_qm_pct": b_qm
        })
        print(f"   Mes {mes:02d}: Bias Raw = {b_raw:+7.2f}% | Bias QM = {b_qm:+7.4f}%")

    # 7. Cuantiles y extremos
    p95_obs = float(np.quantile(m_obs, 0.95))
    p95_raw = float(np.quantile(m_raw_arr, 0.95))
    p95_qm = float(np.quantile(qm_cal, 0.95))
    p99_obs = float(np.quantile(m_obs, 0.99))
    p99_raw = float(np.quantile(m_raw_arr, 0.99))
    p99_qm = float(np.quantile(qm_cal, 0.99))
    max_obs = float(np.max(m_obs))
    max_raw = float(np.max(m_raw_arr))
    max_qm = float(np.max(qm_cal))
    med_obs = float(np.median(m_obs))
    med_raw = float(np.median(m_raw_arr))
    med_qm = float(np.median(qm_cal))

    print(f"[AUDIT-EXTREMES] P95: Obs={p95_obs:.2f}, Raw={p95_raw:.2f}, QM={p95_qm:.2f}")
    print(f"[AUDIT-EXTREMES] P99: Obs={p99_obs:.2f}, Raw={p99_raw:.2f}, QM={p99_qm:.2f}")
    print(f"[AUDIT-EXTREMES] Max: Obs={max_obs:.2f}, Raw={max_raw:.2f}, QM={max_qm:.2f}")
    print(f"[AUDIT-EXTREMES] Med: Obs={med_obs:.2f}, Raw={med_raw:.2f}, QM={med_qm:.2f}")

    return {
        "N_cal": N_cal,
        "mean_obs": mean_obs, "mean_raw": mean_raw, "mean_qm": mean_qm,
        "bias_raw_pct": bias_raw_pct, "bias_qm_pct": bias_qm_pct,
        "rmse_qm": rmse_qm, "mae_qm": mae_qm,
        "wet_freq_obs": wet_freq_obs, "wet_freq_raw": wet_freq_raw, "wet_freq_qm": wet_freq_qm,
        "std_obs": std_obs, "std_raw": std_raw, "std_qm": std_qm,
        "kge_qm": kge_qm,
        "n_fuera_total": n_fuera_total, "pct_fuera_total": pct_fuera_total, "n_fuera_post": n_fuera_post,
        "monthly_results": monthly_results,
        "extremes": {
            "p95": (p95_obs, p95_raw, p95_qm),
            "p99": (p99_obs, p99_raw, p99_qm),
            "max": (max_obs, max_raw, max_qm),
            "med": (med_obs, med_raw, med_qm)
        }
    }

if __name__ == "__main__":
    res = run_independent_audit()
    print("\nAuditoría numérica independiente completada exitosamente.")
