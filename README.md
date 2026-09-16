# 🌧️ HIDROMETEOROLOGIA - Dashboard Interactivo de Quantile Mapping (QM)

Plataforma interactiva para el análisis, corrección de sesgo estadístico y downscaling univariado de precipitación diaria utilizando **Empirical Quantile Mapping (EQM) mensual** con corrección de frecuencia de días secos/húmedos.

---

## 📊 Datos y Metodología

- **Modelo Climático:** `MPI-ESM1-2-HR` (Simulación diaria 1950–2100).
- **Observación de Referencia:** Estación pluviométrica `Carolina (27010500)` (1959–2014).
- **Periodo de Calibración Histórico:** 1959–2014 (consistente con el cierre del experimento histórico de CMIP6).
- **Método:** Empirical Quantile Mapping mensual (12 funciones de distribución empírica acumulada ECDF) con determinación del umbral de llovizna del modelo $U_{\text{mod}}$ a partir de la probabilidad de días secos observados $P(\text{seco})_{\text{obs}}$.
- **Tratamiento de Extrapolación:** Detección y marcado explícito de eventos que superan el soporte empírico de calibración.

---

## 🚀 Despliegue en Streamlit Community Cloud

Para desplegar este dashboard en la nube de Streamlit de forma gratuita y con actualización automática en cada `git push`:

1. Ingresa a [share.streamlit.io](https://share.streamlit.io/) e inicia sesión con tu cuenta de GitHub (`Xboster-eliel`).
2. Haz clic en **"New app"** (o **"Create app"**).
3. Selecciona los siguientes parámetros:
   - **Repository:** `Xboster-eliel/HIDROMETEOROLOGIA`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Haz clic en **"Deploy!"**.
5. ¡Listo! Cada vez que realices `git push origin main`, Streamlit Cloud actualizará automáticamente el dashboard en producción.

---

## 💻 Ejecución Local

### Prerrequisitos
Tener instalado Python 3.10 o superior.

### Instalación de dependencias
```bash
pip install -r requirements.txt
```

### Iniciar el Dashboard
```bash
streamlit run app.py
```
O en Windows, haciendo doble clic en `ejecutar_dashboard.bat`.

La aplicación se abrirá en tu navegador en `http://localhost:8501`.

---

## 📁 Estructura del Repositorio

```text
├── app.py                   # Aplicación principal interactiva en Streamlit
├── qm_core.py               # Motor científico de cálculo y algoritmos de QM
├── data QM.csv              # Base de datos de precipitación (Modelo + Estación)
├── Quantil Mapping.ods      # Versión en formato OpenDocument Spreadsheet
├── test_qm_pipeline.py      # Pruebas automatizadas del pipeline numérico
├── ejecutar_dashboard.bat   # Script lanzador rápido para Windows
├── requirements.txt         # Dependencias para Streamlit Cloud y local
├── .gitignore               # Archivos excluidos del control de versiones
└── README.md                # Documentación del proyecto
```

---

## 📚 Referencias Científicas

- **Cannon, A. J., et al. (2015).** Bias correction of GCM precipitation by quantile mapping: How well do methods preserve changes in quantiles and extremes? *Journal of Climate*, 28(17), 6938–6959. [DOI: 10.1175/JCLI-D-14-00754.1](https://doi.org/10.1175/JCLI-D-14-00754.1)
- **Gudmundsson, L., et al. (2012).** Technical Note: Downscaling RCM precipitation to the station scale using statistical transformations. *Hydrology and Earth System Sciences*, 16, 3383–3390. [DOI: 10.5194/hess-16-3383-2012](https://doi.org/10.5194/hess-16-3383-2012)
- **Maraun, D. (2013).** Bias correction, quantile mapping, and downscaling: Revisiting the inflation issue. *Journal of Climate*, 26(6), 2137–2143. [DOI: 10.1175/JCLI-D-12-00821.1](https://doi.org/10.1175/JCLI-D-12-00821.1)
- **Themeßl, M. J., et al. (2011).** Empirical-statistical downscaling and error correction of daily precipitation from regional climate models. *International Journal of Climatology*, 31(10), 1530–1544. [DOI: 10.1002/joc.2168](https://doi.org/10.1002/joc.2168)
