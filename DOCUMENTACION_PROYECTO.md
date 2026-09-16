# 📖 Documentación Integral del Proyecto: Dashboard de Quantile Mapping en Hidrometeorología

Este documento detalla la arquitectura, el fundamento científico, la configuración de infraestructura (Git, GitHub, Streamlit Community Cloud) y las pautas técnicas para futuras implementaciones y ampliaciones del proyecto.

---

## 1. Visión General del Proyecto

El sistema es una plataforma interactiva y computacional diseñada para realizar **ajuste de sesgo estadístico (bias correction)** y **downscaling univariado** de series temporales de precipitación diaria provenientes de Modelos de Circulación General (GCM) hacia observaciones de estaciones meteorológicas puntuales.

- **Modelo Climático de Entrada:** `MPI-ESM1-2-HR` (Simulación diaria global, 1950–2100).
- **Estación Pluviométrica de Referencia:** `Carolina (27010500)` (Registros diarios observados, 1959–2014).
- **Periodo de Calibración:** `1959-01-01` a `2014-12-31` (20,454 días comunes, coincidente con el cierre del experimento histórico de CMIP6).
- **Periodo de Proyección / Demostración:** `2015-01-01` a `2100-12-31` (55,152 días totales en el modelo).

---

## 2. Fundamento Científico y Algorítmico

### 2.1 Formulación de Empirical Quantile Mapping (EQM)
El Quantile Mapping no ajusta únicamente la media o la varianza de forma lineal; alinea toda la función de distribución acumulada (CDF) de la variable simulada con la observada:

$$X_{\mathrm{QM}} = F_o^{-1}\left(F_m(X_m)\right)$$

Donde:
- $X_m$: Precipitación simulada bruta por el modelo.
- $F_m$: CDF empírica del modelo en el periodo de calibración.
- $p = F_m(X_m)$: Probabilidad acumulada o posición cuantílica de la simulación.
- $F_o^{-1}$: Función cuantil inversa (observaciones de referencia).
- $X_{\mathrm{QM}}$: Valor corregido final.

### 2.2 Tratamiento del Efecto Llovizna (*Drizzle Effect*) y Días Secos
Los modelos GCM/RCM generan una frecuencia excesiva de días con lluvia diminuta ($< 0.1\text{ mm/d}$). Para corregir esto:
1. Se define un umbral de día seco/húmedo observado ($P_{\mathrm{wet}} = 0.10\text{ mm/d}$).
2. Se calcula la probabilidad de días secos observados: $P(\text{seco})_{\text{obs}} = \frac{N(P_o < P_{\mathrm{wet}})}{N_{\mathrm{total}}}$.
3. Se identifica el cuantil equivalente en el modelo, obteniendo el umbral adaptativo $U_{\mathrm{mod}} = \text{Quantile}(X_m, P(\text{seco})_{\text{obs}})$.
4. Para cualquier $X_m \le U_{\mathrm{mod}}$, se asigna estrictamente $0.0\text{ mm/d}$.
5. Para los días húmedos ($X_m > U_{\mathrm{mod}}$), se construye la función cuantil empírica sobre $N=1001$ intervalos.

### 2.3 Estacionalidad (Calibración Mensual)
El régimen hidrológico varía a lo largo del año. Por ello, el algoritmo calibra **12 funciones independientes** (una para cada mes calendario del 1 al 12), evitando mezclar eventos convectivos de verano con frentes invernales o periodos secos.

### 2.4 Detección de Extrapolación (Valores Fuera de Soporte)
Si en el periodo futuro el modelo genera una precipitación superior al máximo registrado en la calibración histórica ($X_m > \max(X_{m,\mathrm{cal}})$), el método aplica saturación en el cuantil 1.0 y marca automáticamente la bandera booleana `fuera_soporte = True`. En la base de datos de salida se identificaron 33 eventos con esta condición.

---

## 3. Arquitectura del Código y Módulos

```text
c:\Users\eliel\Documents\HidroMeteorologia\
├── app.py                       # Interfaz Web interactiva en Streamlit + Plotly
├── qm_core.py                   # Motor científico desacoplado con la matemática de QM
├── test_qm_pipeline.py          # Pruebas automatizadas de cálculo y consistencia
├── data QM.csv                  # Dataset fuente estructurado en 2 bloques (Modelo y Estación)
├── Quantil Mapping.ods          # Dataset original alternativo en formato ODS
├── requirements.txt             # Dependencias exactas para despliegue en la nube
├── .gitignore                   # Archivos excluidos del control de versiones
├── ejecutar_dashboard.bat       # Script lanzador local de un clic para Windows
├── hacer_git_push.bat           # Script automatizado para commits y envíos a GitHub
└── README.md                    # Documentación principal para GitHub
```

### Detalle de Módulos Clave:
- **`qm_core.py`**:
  - `cargar_datos_qm()`: Lee CSV y ODS, convierte números con coma decimal y valida cabeceras.
  - `generar_inventario()`: Genera métricas de calidad y rango de fechas.
  - `fit_eqm_mensual()`: Ajusta los parámetros mensuales (umbral y cuantiles).
  - `apply_eqm_mensual()`: Transformación vectorizada agrupada por mes (computa 55,000 registros en <0.2 s).
  - `tabla_metricas_comparativas()`: Calcula Sesgo Relativo (%), RMSE, MAE, frecuencias seco/húmedo y cuantiles P95/P99.
- **`app.py`**:
  - Organizado en 6 pestañas:
    1. *Diagnóstico y Datos:* KPIs, inventario y visualizador interactivo con range-slider.
    2. *Concepto y Ejemplo Pedagógico:* Demostración interactiva paso a paso con arrays editables.
    3. *Ajuste ECDF y Q-Q:* Curvas ECDF con selector de mes y gráfico Q-Q frente a la línea 1:1.
    4. *Climatología y Series Diarias:* Ciclo anual medio e inspección diaria por año.
    5. *Proyecciones (1950–2100):* Evolución multidecadal y análisis de extrapolación.
    6. *Exportación y Metodología:* Descargas en CSV y síntesis teórica.
  - Incorpora `@st.cache_data` para garantizar navegación instantánea entre pestañas sin recalcular.

---

## 4. Infraestructura, Git y Despliegue Continuo (CI/CD)

### 4.1 Repositorio Remoto
- **URL GitHub:** `https://github.com/Xboster-eliel/HIDROMETEOROLOGIA.git`
- **Rama Principal:** `main`
- **Ruta del Archivo Principal en Streamlit:** `app.py`

### 4.2 Despliegue en Streamlit Community Cloud
La aplicación se encuentra enlazada a GitHub mediante Streamlit Cloud.
- **Enlace de Despliegue Rápido:**
  [https://share.streamlit.io/deploy?repository=Xboster-eliel/HIDROMETEOROLOGIA&branch=main&mainModule=app.py](https://share.streamlit.io/deploy?repository=Xboster-eliel/HIDROMETEOROLOGIA&branch=main&mainModule=app.py)

### 4.3 Flujo de Trabajo para Actualizaciones Continuas (`git push`)
Cualquier modificación futura sigue el siguiente ciclo automatizado:

1. **Editar código o datos:** Modificar `app.py`, `qm_core.py` o actualizar `data QM.csv`.
2. **Enviar a GitHub:**
   - **Método A (Con un clic):** Ejecutar `hacer_git_push.bat`.
   - **Método B (Por consola):**
     ```bash
     git add .
     git commit -m "feat: descripcion del cambio"
     git push origin main
     ```
3. **Despliegue Automático:** Streamlit Community Cloud detecta el `push` mediante Webhooks y actualiza la aplicación en producción en menos de 60 segundos sin necesidad de reiniciar manualmente el servidor.

---

## 5. Guía Técnica para Futuras Implementaciones y Extensiones

### 5.1 Agregar Nuevas Estaciones Pluviométricas
Para añadir estaciones adicionales al sistema:
1. **En la carga de datos (`qm_core.py`):**
   - Si el archivo contiene múltiples estaciones en columnas separadas o apiladas, extender `cargar_datos_qm()` para filtrar por `id_estacion`.
2. **En la interfaz (`app.py`):**
   - Agregar en la barra lateral un `st.selectbox("Seleccione Estación:", lista_estaciones)` para que el usuario pueda alternar entre estaciones dinámicamente.

### 5.2 Incorporar Nuevos Modelos Climáticos (Ensemble CMIP6)
Para comparar varios modelos (ej. *MPI-ESM1-2-HR*, *CanESM5*, *EC-Earth3*):
- Estructurar el DataFrame de modelos con una columna identificadora `modelo`.
- En la pestaña de Proyecciones de `app.py`, superponer las curvas corregidas de cada modelo para visualizar la dispersión del ensamble e incertidumbre climática.

### 5.3 Migración a Quantile Delta Mapping (QDM) para Proyecciones Climáticas
El QM clásico modifica las tendencias relativas de cambio climático proyectadas por el modelo (Cannon et al., 2015). Para futuros estudios de impacto hidrológico formal:
1. Implementar la función `fit_apply_qdm()` en `qm_core.py`:
   - Descomponer la señal en: tendencia relativa del modelo multiplicativa ($\Delta = \frac{X_{m,\mathrm{fut}}}{X_{m,\mathrm{cal}}}$) y corrección de sesgo respecto a la observación histórica.
2. Añadir un selector en la barra lateral: `Método: [Empirical Quantile Mapping (EQM), Quantile Delta Mapping (QDM)]`.

### 5.4 Corrección de Temperatura Diaria (Tmax, Tmin)
Si se desea aplicar QM a series de temperatura:
- A diferencia de la precipitación, la temperatura es una variable continua sin masa en cero (no hay días secos).
- En `qm_core.py`, prescindir del filtro de umbral húmedo $U_{\text{mod}}$ y aplicar la función cuantil sobre el 100% de los datos (ajuste aditivo: $T_{\mathrm{QM}} = X_o + \Delta$).

### 5.5 Mantenimiento de Librerías (`requirements.txt`)
Si se agregan nuevas librerías al proyecto (por ejemplo `geopandas`, `xarray` o `seaborn`):
1. Añadir el paquete con su versión mínima a `requirements.txt`:
   ```text
   geopandas>=0.14.0
   ```
2. Realizar `git push origin main` para que Streamlit Cloud instale la librería en su contenedor automáticamente.

---

## 6. Referencias Bibliográficas

1. **Cannon, A. J., Sobie, S. R., & Murdock, T. Q. (2015).** Bias correction of GCM precipitation by quantile mapping: How well do methods preserve changes in quantiles and extremes? *Journal of Climate, 28*(17), 6938–6959. [https://doi.org/10.1175/JCLI-D-14-00754.1](https://doi.org/10.1175/JCLI-D-14-00754.1)
2. **Gudmundsson, L., Bremnes, J. B., Haugen, J. E., & Engen-Skaugen, T. (2012).** Technical Note: Downscaling RCM precipitation to the station scale using statistical transformations – a comparison of methods. *Hydrology and Earth System Sciences, 16*, 3383–3390. [https://doi.org/10.5194/hess-16-3383-2012](https://doi.org/10.5194/hess-16-3383-2012)
3. **Maraun, D. (2013).** Bias correction, quantile mapping, and downscaling: Revisiting the inflation issue. *Journal of Climate, 26*(6), 2137–2143. [https://doi.org/10.1175/JCLI-D-12-00821.1](https://doi.org/10.1175/JCLI-D-12-00821.1)
4. **Themeßl, M. J., Gobiet, A., & Leuprecht, A. (2011).** Empirical-statistical downscaling and error correction of daily precipitation from regional climate models. *International Journal of Climatology, 31*(10), 1530–1544. [https://doi.org/10.1002/joc.2168](https://doi.org/10.1002/joc.2168)
