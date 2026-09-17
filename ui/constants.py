"""
Constantes globales de diseño, paleta cromática unificada y etiquetas.
"""

# Paleta cromática oficial e inmutable para todo el dashboard
COLOR_OBS = "#2563EB"   # Azul observación pluviométrica (Estación)
COLOR_RAW = "#DC5A4A"   # Rojo simulación climática bruta (GCM)
COLOR_QM  = "#16A34A"   # Verde modelo corregido con Quantile Mapping
COLOR_REF = "#64748B"   # Gris neutro (referencia 1:1, guías y cuadrícula)

# Paleta auxiliar de estado
COLOR_SUCCESS = "#16A34A"
COLOR_WARNING = "#F59E0B"
COLOR_DANGER  = "#DC2626"
COLOR_MUTED   = "#94A3B8"

# Meses calendario
MESES_CORTOS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
MESES_COMPLETOS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

# Umbrales para semáforo de desempeño
THRESHOLD_EXCELLENT = 2.0   # Diferencia relativa < 2%
THRESHOLD_ACCEPTABLE = 5.0  # Diferencia relativa 2% - 5%
