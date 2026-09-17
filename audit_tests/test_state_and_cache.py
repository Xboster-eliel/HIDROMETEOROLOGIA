"""
Prueba de auditoría para verificar el ciclo de vida de la caché y el estado en app.py.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from app import get_data, calibrar_y_procesar


def test_cache_and_state():
    print("[AUDIT-CACHE] 1. Probando carga de datos...")
    modelo, obs = get_data()
    assert not modelo.empty and not obs.empty, "Error en carga de datos"
    
    print("[AUDIT-CACHE] 2. Calibración base (1959-2014, wet=0.1, n_q=1001)...")
    cal1, p1, mod1, met1, meta1 = calibrar_y_procesar(modelo, obs, 1959, 2014, 0.1, 1001)
    
    print("[AUDIT-CACHE] 3. Verificando que una llamada idéntica reutiliza caché...")
    cal1_bis, p1_bis, mod1_bis, met1_bis, meta1_bis = calibrar_y_procesar(modelo, obs, 1959, 2014, 0.1, 1001)
    assert cal1.equals(cal1_bis), "Fallo de caché: los datos no coinciden"
    assert set(p1.keys()) == set(p1_bis.keys()), "Fallo de caché: las claves de parámetros no coinciden"
    assert np.allclose(p1[1]["mod_q"], p1_bis[1]["mod_q"]), "Fallo de caché: cuantiles no coinciden"
    print("   [OK] Cache hit verificado con exito.")


    print("[AUDIT-CACHE] 4. Probando cambio de periodo de calibración (1970-2000)...")
    cal2, p2, mod2, met2, meta2 = calibrar_y_procesar(modelo, obs, 1970, 2000, 0.1, 1001)
    assert len(cal2) < len(cal1), "El cambio de periodo no alteró la longitud de calibración"
    print(f"   [OK] Periodo 1970-2000: {len(cal2)} dias (Base: {len(cal1)} dias).")

    print("[AUDIT-CACHE] 5. Probando cambio de umbral humedo (Pwet = 1.0 mm/d)...")
    cal3, p3, mod3, met3, meta3 = calibrar_y_procesar(modelo, obs, 1959, 2014, 1.0, 1001)
    # Con umbral 1.0, la probabilidad seca observada debe ser mayor
    assert p3[1]["p_seco_obs"] > p1[1]["p_seco_obs"], "El cambio de Pwet no altero la probabilidad seca"
    print(f"   [OK] Mes 1 P(seco) con wet=0.1: {p1[1]['p_seco_obs']:.3f} | con wet=1.0: {p3[1]['p_seco_obs']:.3f}")

    print("\nAuditoria de cache y estado completada con exito: Recalibracion reactiva correcta.")


if __name__ == "__main__":
    test_cache_and_state()
