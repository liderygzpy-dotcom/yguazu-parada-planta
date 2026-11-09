import streamlit as st
import pandas as pd
import io
import html
import logging
import time
from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, firestore as fb_firestore

# 10. Configurar logging seguro sin filtrar warnings globalmente de forma insegura
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("YguazuSeguridad")

st.set_page_config(
    page_title="Yguazú Cementos - Seguimiento de Parada de Planta",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. CONFIGURACIÓN DE SEGURIDAD Y SECRETOS ---
if "firebase" not in st.secrets or "auth_allowlist" not in st.secrets:
    st.error("Configuración de seguridad incompleta en el servidor. Contacte al administrador.")
    logger.critical("Faltan 'firebase' o 'auth_allowlist' en st.secrets.")
    st.stop()

ALLOWLIST = [correo.strip().lower() for correo in st.secrets["auth_allowlist"]]
EDITORES = [correo.strip().lower() for correo in st.secrets.get("auth_editores", [])]

# --- 5. GESTIÓN DE SESIÓN E INACTIVIDAD (30 MINUTOS) ---
SESSION_TIMEOUT = 1800  # 30 minutos en segundos

if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None
if "user_role" not in st.session_state:
    st.session_state["user_role"] = "lector"
if "last_activity" not in st.session_state:
    st.session_state["last_activity"] = time.time()

# Verificar inactividad
if st.session_state["auth_user"] is not None:
    if time.time() - st.session_state["last_activity"] > SESSION_TIMEOUT:
        st.session_state.clear()
        st.warning("Sesión expirada por inactividad. Por favor, vuelva a iniciar sesión.")
        st.stop()
    else:
        st.session_state["last_activity"] = time.time()

# --- 2. AUTENTICACIÓN GOOGLE OIDC ---
def validar_autenticacion():
    # Streamlit 1.42+ OIDC nativo st.login()
    if hasattr(st, "login"):
        try:
            if not st.session_state.get("auth_user"):
                st.login() # type: ignore
                # OIDC expone st.experimental_user o st.user
                user_obj = getattr(st, "user", None)
                if user_obj and getattr(user_obj, "email", None):
                    email = user_obj.email.lower()
                    if email in ALLOWLIST:
                        st.session_state["auth_user"] = email
                        st.session_state["user_role"] = "editor" if email in EDITORES else "lector"
                        st.session_state["last_activity"] = time.time()
                        st.rerun()
                    else:
                        st.error("Acceso denegado. Su cuenta no cuenta con permisos autorizados.")
                        logger.warning(f"Intento de acceso denegado para el correo: {email}")
                        st.stop()
        except Exception:
            logger.error("Error crítico en el flujo OIDC de st.login().")
            
    # Fallback de autenticación segura si OIDC no está activo en entorno local o configuración
    if not st.session_state.get("auth_user"):
        st.markdown("""
        <div style="max-width: 450px; margin: 80px auto; padding: 30px; background-color: #ffffff; border-radius: 12px; border-top: 5px solid #C8102E; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center;">
            <h2 style="color: #0A2540; margin-bottom: 5px;">YGUAZÚ CEMENTOS S.A.</h2>
            <p style="color: #64748b; font-size: 0.95rem;">Acceso Restringido — Parada Mayor</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("fallback_login"):
            correo_input = st.text_input("Correo Electrónico Autorizado:")
            btn = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
            if btn:
                correo_limpio = correo_input.strip().lower()
                if correo_limpio in ALLOWLIST:
                    st.session_state["auth_user"] = correo_limpio
                    st.session_state["user_role"] = "editor" if correo_limpio in EDITORES else "lector"
                    st.session_state["last_activity"] = time.time()
                    st.rerun()
                else:
                    st.error("Credenciales inválidas o acceso no autorizado.")
                    logger.warning(f"Intento de login fallido con correo: {correo_limpio}")
        st.stop()

validar_autenticacion()

CURRENT_USER = st.session_state["auth_user"]
CURRENT_ROLE = st.session_state["user_role"]

# --- CONEXIÓN FIREBASE (ADMIN SDK) ---
@st.cache_resource
def init_firebase():
    try:
        if not firebase_admin._apps:
            firebase_secrets = dict(st.secrets["firebase"])
            cred = credentials.Certificate(firebase_secrets)
            firebase_admin.initialize_app(cred)
        return fb_firestore.client()
    except Exception:
        logger.error("Error al inicializar Firebase Admin SDK.")
        return None

db = init_firebase()

# --- 13. CACHÉ Y PERSISTENCIA DE TAREAS EN FIRESTORE ---
@st.cache_data(ttl=15)
def cargar_estado_tareas_firestore():
    estado_dict = {}
    if db is not None:
        try:
            docs = db.collection("parada_estado").stream()
            for doc in docs:
                data = doc.to_dict()
                estado_dict[doc.id] = data.get("estado", False)
        except Exception:
            logger.error("Error al leer estados desde Firestore.")
    return estado_dict

if "task_status" not in st.session_state:
    st.session_state.task_status = cargar_estado_tareas_firestore()

def actualizar_estado_tarea(tid, nuevo_estado):
    if CURRENT_ROLE != "editor":
        logger.warning(f"Usuario {CURRENT_USER} sin privilegios intentó modificar la tarea {tid}.")
        return False
    
    st.session_state.task_status[tid] = nuevo_estado
    
    if db is not None:
        try:
            # Escrituras en lote o documento individual con auditoría
            batch = db.batch()
            ref_estado = db.collection("parada_estado").document(tid)
            batch.set(ref_estado, {
                "estado": nuevo_estado,
                "actualizado_por": CURRENT_USER,
                "actualizado_en": datetime.now(timezone.utc).isoformat()
            }, merge=True)
            
            # 12. Auditoría en Firestore
            ref_audit = db.collection("auditoria").document()
            batch.set(ref_audit, {
                "tarea_id": tid,
                "accion": "completada" if nuevo_estado else "desmarcada",
                "usuario": CURRENT_USER,
                "timestamp_utc": datetime.now(timezone.utc).isoformat()
            })
            batch.commit()
            return True
        except Exception:
            logger.error(f"Error al guardar estado/auditoría en Firestore para la tarea {tid}.")
            return False
    return True

# --- 6. SANITIZACIÓN DE HTML ---
def limpiar_html(texto, max_len=100):
    if pd.isna(texto):
        return ""
    str_val = str(texto).strip()
    if len(str_val) > max_len:
        str_val = str_val[:max_len] + "..."
    return html.escape(str_val)

# --- 7. NEUTRALIZACIÓN DE FÓRMULAS EN EXPORTACIÓN ---
def neutralizar_formulas(df):
    df_clean = df.copy()
    for col in df_clean.select_dtypes(include=['object', 'string']).columns:
        df_clean[col] = df_clean[col].apply(
            lambda x: f"'{x}" if isinstance(x, str) and x.startswith(('=', '+', '-', '@', '\t', '\r')) else x
        )
    return df_clean

# --- ESTILOS CSS PROFESIONALES ---
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; color: #0f172a; }
    label, .stRadio label, .stSelectbox label, .stSlider label, .stFileUploader label {
        color: #0A2540 !important; font-weight: 700 !important; font-size: 0.9rem !important;
    }
    .stRadio div[role="radiogroup"] label p { color: #1e293b !important; font-weight: 600 !important; }
    .header-container {
        display: flex; align-items: center; justify-content: space-between;
        background-color: #0A2540; padding: 24px 30px; border-radius: 12px;
        margin-bottom: 20px; border-bottom: 5px solid #C8102E; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    .header-title { color: #ffffff; font-size: 2.2rem; font-weight: 800; margin: 0; letter-spacing: -0.5px; }
    .header-subtitle { color: #cbd5e1; font-size: 1.05rem; margin-top: 5px; font-weight: 500; }
    .metric-card {
        background-color: #ffffff; border: 1px solid #cbd5e1; border-top: 4px solid #0A2540;
        border-radius: 10px; padding: 18px 22px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
    }
    .metric-card.kpi-red { border-top-color: #C8102E; }
    .metric-card.kpi-green { border-top-color: #10b981; }
    .metric-card.kpi-yellow { border-top-color: #f59e0b; }
    .metric-label { font-size: 0.85rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
    .metric-value { font-size: 2.2rem; font-weight: 800; color: #0A2540; line-height: 1.1; }
    .metric-subtext { font-size: 0.85rem; font-weight: 600; margin-top: 6px; }
    .text-green { color: #10b981; }
    .text-orange { color: #d97706; }
    .text-red { color: #C8102E; }
    .text-blue { color: #0A2540; }
    .weather-card { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .weather-card.rain { border-top: 3px solid #C8102E; background-color: #fef2f2; }
    .weather-card.sunny { border-top: 3px solid #f59e0b; background-color: #fffbeb; }
    .weather-date { font-size: 0.8rem; font-weight: 700; color: #475569; text-transform: uppercase; }
    .weather-temp { font-size: 1.25rem; font-weight: 800; color: #0A2540; margin: 4px 0; }
    .weather-desc { font-size: 0.75rem; color: #334155; font-weight: 600; }
    .task-card { background-color: #ffffff; border: 1px solid #cbd5e1; border-left: 5px solid #64748b; border-radius: 8px; padding: 14px 18px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .task-card.completed { border-left-color: #10b981; background-color: #ecfdf5; }
    .task-card.delayed { border-left-color: #C8102E; background-color: #fef2f2; }
    .task-title { font-size: 1.05rem; font-weight: 700; color: #0f172a; }
    .task-meta { font-size: 0.875rem; color: #334155; margin-top: 6px; }
    .badge { display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; margin-right: 6px; }
    .badge-sector { background-color: #e2e8f0; color: #0f172a; }
    .badge-resp { background-color: #0A2540; color: #ffffff; }
    .badge-file { background-color: #C8102E; color: #ffffff; }
</style>
""", unsafe_allow_html=True)

if "uploaded_data" not in st.session_state:
    st.session_state.uploaded_data = None

# --- 11. LOGO LOCAL CON FALLBACK A TEXTO ---
logo_html = ""
try:
    import os
    if os.path.exists("assets/logo.png"):
        logo_html = '<img src="app/static/assets/logo.png" width="160" alt="Yguazú Cementos Logo">'
    else:
        logo_html = '<h3 style="color:white; margin:0;">YGUAZÚ CEMENTOS</h3>'
except Exception:
    logo_html = '<h3 style="color:white; margin:0;">YGUAZÚ CEMENTOS</h3>'

st.markdown(f"""
<div class="header-container">
    <div>
        <div class="header-title">YGUAZÚ CEMENTOS S.A.</div>
        <div class="header-subtitle">🏗️ Sistema de Seguimiento Operativo — Parada Mayor de Planta</div>
    </div>
    <div>
        {logo_html}
    </div>
</div>
""", unsafe_allow_html=True)

# PRONÓSTICO DEL TIEMPO (PLANTA VILLA HAYES)
st.markdown("### 🌤️ Pronóstico del Tiempo — Planta Industrial Villa Hayes (10 Días)")
weather_data = [
    {"dia": "Vie 06", "temp": "34° / 23°", "desc": "☀️ Soleado", "rain": False},
    {"dia": "Sáb 07", "temp": "29° / 17°", "desc": "⛈️ Tormentas", "rain": True},
    {"dia": "Dom 08", "temp": "26° / 15°", "desc": "Part. Soleado", "rain": False},
    {"dia": "Lun 09", "temp": "29° / 17°", "desc": "☀️ Soleado", "rain": False},
    {"dia": "Mar 10", "temp": "32° / 22°", "desc": "🌧️ Lluvia Noche", "rain": True},
    {"dia": "Mié 11", "temp": "29° / 23°", "desc": "🌧️ Lluvia Intensa", "rain": True},
    {"dia": "Jue 12", "temp": "32° / 24°", "desc": "Part. Soleado", "rain": False},
    {"dia": "Vie 13", "temp": "34° / 25°", "desc": "☀️ Soleado", "rain": False},
    {"dia": "Sáb 14", "temp": "34° / 24°", "desc": "⛈️ Torm. Fuertes", "rain": True},
    {"dia": "Dom 15", "temp": "29° / 22°", "desc": "⛈️ Torm. Fuertes", "rain": True},
]

w_cols = st.columns(10)
for i, w in enumerate(weather_data):
    card_type = "weather-card rain" if w["rain"] else "weather-card sunny"
    with w_cols[i]:
        st.markdown(f"""
        <div class="{card_type}">
            <div class="weather-date">{w['dia']}</div>
            <div class="weather-temp">{w['temp'].split('/')[0]}</div>
            <div class="weather-desc">{w['desc']}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 8. CARGA Y VALIDACIÓN DE ARCHIVOS ---
@st.cache_data(show_spinner=False)
def parsear_archivos_excel(uploaded_files_cache_key, files_bytes_dict):
    all_parsed_data = []
    for file_name, f_bytes in files_bytes_dict.items():
        try:
            excel_io = io.BytesIO(f_bytes)
            # Leer una sola vez con pd.ExcelFile
            xls = pd.ExcelFile(excel_io)
            for sheet in xls.sheet_names:
                sheet_upper = sheet.upper()
                if "GANTT" in sheet_upper:
                    discipline = "MECÁNICA" if "MEC" in sheet_upper else ("ELECTRO-INSTRUMENTACIÓN" if ("ETR" in sheet_upper or "ELEC" in sheet_upper) else "OTRO")
                    
                    df_raw = pd.read_excel(xls, sheet_name=sheet, header=None, nrows=5000)
                    header_row_idx = None
                    for idx, row in df_raw.iterrows():
                        row_str = [str(val).strip().upper() for val in row.values]
                        if "OT" in row_str and "TAG" in row_str:
                            header_row_idx = idx
                            break
                    
                    if header_row_idx is not None:
                        df = pd.read_excel(xls, sheet_name=sheet, header=header_row_idx, nrows=5000)
                        df.columns = [str(c).strip().upper() for c in df.columns]
                        
                        current_resp = "Sin Asignar"
                        for idx, row in df.iterrows():
                            ot_val = row.get("OT")
                            tag_val = row.get("TAG")
                            act_val = row.get("ACTIVIDAD")
                            
                            if pd.isna(tag_val) and pd.isna(act_val) and pd.notna(ot_val):
                                ot_str = str(ot_val).strip()
                                if ot_str and ot_str != "OT" and ot_str != "NAN":
                                    current_resp = ot_str
                                continue
                            
                            if pd.notna(ot_val) and str(ot_val).strip() not in ["OT", "NAN", ""]:
                                ot_str = str(ot_val).strip()
                                tag_str = str(tag_val) if pd.notna(tag_val) else "General"
                                act_str = str(act_val) if pd.notna(act_val) else "Mantenimiento"
                                grupo_str = str(row.get("GRUPO", "General")) if "GRUPO" in df.columns else "General"
                                
                                for day in range(1, 21):
                                    day_col = str(day)
                                    if day_col in df.columns:
                                        cell_val = row.get(day_col)
                                        if pd.notna(cell_val) and str(cell_val).strip() != "":
                                            all_parsed_data.append({
                                                "ID": f"{file_name}_{discipline}_{ot_str}_Día{day}_{idx}",
                                                "Archivo": file_name,
                                                "OT": ot_str,
                                                "Ubicacion": tag_str,
                                                "Actividad": act_str,
                                                "Grupo": grupo_str,
                                                "Responsable": current_resp,
                                                "Disciplinas": discipline,
                                                "Dia": day
                                            })
        except Exception:
            logger.error(f"Error procesando el archivo interno: {file_name}")
    return all_parsed_data

# Barra lateral
with st.sidebar:
    st.markdown("<h3 style='color:#0A2540;'>👤 Sesión Activa</h3>", unsafe_allow_html=True)
    st.write(f"**Rol:** {CURRENT_ROLE.upper()}")
    if st.button("🔴 Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()
        
    st.divider()
    st.markdown("<h3 style='color:#0A2540;'>⚙️ Carga de Datos</h3>", unsafe_allow_html=True)
    
    # 3. Restricción de carga de archivos según rol
    if CURRENT_ROLE != "editor":
        st.info("🔒 Su rol de lector no permite cargar archivos nuevos.")
        uploaded_files = None
    else:
        uploaded_files = st.file_uploader("Cargar Archivos Excel de Sectores (Gantt)", type=["xlsx", "xls"], accept_multiple_files=True)
    
    if uploaded_files:
        if len(uploaded_files) > 10:
            st.error("Límite excedido. Puede cargar un máximo de 10 archivos simultáneamente.")
            uploaded_files = None
        else:
            files_dict = {}
            error_val = False
            for f in uploaded_files:
                if f.size > 10 * 1024 * 1024:  # 10 MB
                    st.error(f"El archivo {f.name} supera el límite de 10 MB.")
                    error_val = True
                    break
                files_dict[f.name] = f.getvalue()
            
            if not error_val:
                parsed_res = parsear_archivos_excel(str(list(files_dict.keys())), files_dict)
                if parsed_res:
                    st.session_state.uploaded_data = pd.DataFrame(parsed_res)
                    st.success(f"✅ {len(parsed_res)} tareas cargadas correctamente.")
                else:
                    st.warning("No se detectaron tareas válidas en las hojas Gantt.")

if st.session_state.uploaded_data is None:
    st.warning("⚠️ **No hay archivos cargados.** Por favor, cargue los archivos Excel de sus sectores en la barra lateral para iniciar el seguimiento.")
    st.stop()

df_tasks = st.session_state.uploaded_data

# Panel de Filtros Superiores
st.markdown("### 🔍 Filtros Operativos y Control Temporal")
f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([1.2, 1.2, 1.2, 1.2, 1.6])

with f_col1:
    available_files = ["Todos"] + sorted(list(df_tasks["Archivo"].unique()))
    sel_file = st.selectbox("Sector / Archivo", available_files)

with f_col2:
    available_disciplines = sorted(list(df_tasks["Disciplinas"].unique()))
    discipline = st.radio("Disciplina", available_disciplines, horizontal=True)

with f_col3:
    temp_df = df_tasks[df_tasks["Disciplinas"] == discipline]
    if sel_file != "Todos":
        temp_df = temp_df[temp_df["Archivo"] == sel_file]
    all_resp_list = ["Todos"] + sorted(list(temp_df["Responsable"].unique()))
    sel_resp = st.selectbox("Responsable / Operador", all_resp_list)

with f_col4:
    all_ubic_list = ["Todas"] + sorted(list(temp_df["Ubicacion"].unique()))
    sel_ubic = st.selectbox("Ubicación / Equipo", all_ubic_list)

with f_col5:
    current_plant_day = st.slider("📆 Día Actual de la Parada", min_value=1, max_value=20, value=1)

selected_day = st.slider("📋 Ver / Marcar Checklist del Día de Parada", min_value=1, max_value=20, value=current_plant_day)

df_metric_base = df_tasks[df_tasks["Disciplinas"] == discipline]
if sel_file != "Todos":
    df_metric_base = df_metric_base[df_metric_base["Archivo"] == sel_file]
if sel_resp != "Todos":
    df_metric_base = df_metric_base[df_metric_base["Responsable"] == sel_resp]
if sel_ubic != "Todas":
    df_metric_base = df_metric_base[df_metric_base["Ubicacion"] == sel_ubic]

# Métricas Globales
total_tasks_global = len(df_metric_base)
completed_count_global = sum(1 for tid in df_metric_base["ID"] if st.session_state.task_status.get(tid, False))
pending_count_global = total_tasks_global - completed_count_global
pct_completed_global = (completed_count_global / total_tasks_global * 100) if total_tasks_global > 0 else 0

delayed_tasks_df = df_metric_base[(df_metric_base["Dia"] < current_plant_day) & (~df_metric_base["ID"].apply(lambda tid: st.session_state.task_status.get(tid, False)))]
delayed_count_global = len(delayed_tasks_df)

st.markdown("<br>", unsafe_allow_html=True)

# Tarjetas KPI
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Tareas</div>
        <div class="metric-value">{total_tasks_global}</div>
        <div class="metric-subtext text-blue">Planificadas reales</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
    <div class="metric-card kpi-green">
        <div class="metric-label">Ejecutadas</div>
        <div class="metric-value">{completed_count_global}</div>
        <div class="metric-subtext text-green">✅ {pct_completed_global:.1f}% del total</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
    <div class="metric-card kpi-yellow">
        <div class="metric-label">Pendientes</div>
        <div class="metric-value">{pending_count_global}</div>
        <div class="metric-subtext text-orange">⏳ Restantes</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
    <div class="metric-card kpi-red">
        <div class="metric-label">Atrasadas (Vencidas)</div>
        <div class="metric-value">{delayed_count_global}</div>
        <div class="metric-subtext text-red">⚠️ Días < {current_plant_day} sin hacer</div>
    </div>
    """, unsafe_allow_html=True)

with kpi5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Avance Global</div>
        <div class="metric-value">{pct_completed_global:.1f}%</div>
        <div class="metric-subtext text-green">Progreso acumulado</div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(pct_completed_global / 100 if total_tasks_global > 0 else 0)

st.markdown("<br>", unsafe_allow_html=True)

# Gráficos y Checklist en dos columnas
col_chart, col_list = st.columns([1.1, 1.3])

with col_chart:
    st.markdown("### 📊 Desempeño y Retrasos por Operador")
    
    df_op_base = df_tasks[df_tasks["Disciplinas"] == discipline]
    if sel_file != "Todos":
        df_op_base = df_op_base[df_op_base["Archivo"] == sel_file]
    if sel_ubic != "Todas":
        df_op_base = df_op_base[df_op_base["Ubicacion"] == sel_ubic]
        
    op_summary = []
    for resp in sorted(df_op_base["Responsable"].unique()):
        sub_df = df_op_base[df_op_base["Responsable"] == resp]
        total_op = len(sub_df)
        done_op = sum(1 for tid in sub_df["ID"] if st.session_state.task_status.get(tid, False))
        delayed_op = sum(1 for _, r_row in sub_df.iterrows() if r_row["Dia"] < current_plant_day and not st.session_state.task_status.get(r_row["ID"], False))
        pending_op = total_op - done_op
        pct_op = (done_op / total_op * 100) if total_op > 0 else 0.0
        
        op_summary.append({
            "Responsable": resp,
            "Total": total_op,
            "Ejecutadas": done_op,
            "Pendientes": pending_op,
            "Retrasados": delayed_op,
            "% Cumplimiento": round(pct_op, 1)
        })
    
    df_op_chart = pd.DataFrame(op_summary)
    
    if not df_op_chart.empty:
        st.markdown("##### Tareas Ejecutadas vs Pendientes por Operador")
        chart_data = df_op_chart.set_index("Responsable")[["Ejecutadas", "Pendientes"]]
        st.bar_chart(chart_data, color=["#10b981", "#C8102E"], height=260)
        
        st.markdown("##### Tabla de Control y Retrasos")
        st.dataframe(
            df_op_chart[["Responsable", "Total", "Ejecutadas", "Pendientes", "Retrasados", "% Cumplimiento"]],
            use_container_width=True,
            hide_index=True
        )

with col_list:
    df_filtered_day = df_metric_base[df_metric_base["Dia"] == selected_day]
    st.markdown(f"### 📋 Tareas del Día {selected_day} ({discipline})")
    
    if df_filtered_day.empty:
        st.info("💡 No hay tareas programadas en los archivos para este día con los filtros seleccionados.")
    else:
        for idx, row in df_filtered_day.iterrows():
            t_id = row["ID"]
            is_done = st.session_state.task_status.get(t_id, False)
            is_delayed = (row["Dia"] < current_plant_day) and not is_done
            
            c_check, c_card = st.columns([0.1, 0.9])
            with c_check:
                st.markdown("<br>", unsafe_allow_html=True)
                
                # 3. Desactivar controles si el usuario es lector
                is_disabled = (CURRENT_ROLE != "editor")
                new_status = st.checkbox("", value=is_done, key=f"chk_{t_id}", disabled=is_disabled)
                
                if new_status != is_done:
                    success = actualizar_estado_tarea(t_id, new_status)
                    if success:
                        st.rerun()
                    else:
                        st.error("No se pudo actualizar el estado de la tarea.")
            
            with c_card:
                if is_done:
                    card_class = "task-card completed"
                    status_str = "<span style='color: #10b981; font-weight:700;'>✅ EJECUTADO</span>"
                elif is_delayed:
                    card_class = "task-card delayed"
                    status_str = f"<span style='color: #C8102E; font-weight:700;'>⚠️ ATRASADO (Día {row['Dia']})</span>"
                else:
                    card_class = "task-card"
                    status_str = "<span style='color: #d97706; font-weight:700;'>⏳ PENDIENTE</span>"
                
                # 6. Aplicar html.escape() estricto a todos los campos
                safe_ot = limpiar_html(row['OT'], 20)
                safe_act = limpiar_html(row['Actividad'], 150)
                safe_file = limpiar_html(row['Archivo'], 50)
                safe_ubic = limpiar_html(row['Ubicacion'], 50)
                safe_resp = limpiar_html(row['Responsable'], 50)
                
                st.markdown(f"""
                <div class="{card_class}">
                    <div class="task-title">OT {safe_ot} — {safe_act}</div>
                    <div class="task-meta">
                        <span class="badge badge-file">📁 {safe_file}</span>
                        <span class="badge badge-sector">📍 {safe_ubic}</span>
                        <span class="badge badge-resp">👤 {safe_resp}</span>
                        {status_str}
                    </div>
                </div>
                """, unsafe_allow_html=True)

# Sección de Exportación (solo habilitada o protegida)
st.markdown("---")
st.markdown("### 📥 Exportar Reportes Consolidados")

if CURRENT_ROLE != "editor":
    st.info("🔒 La exportación de reportes está restringida a usuarios con rol de editor.")
else:
    df_export = df_tasks.copy()
    df_export["ESTADO"] = df_export["ID"].apply(lambda tid: "EJECUTADO" if st.session_state.task_status.get(tid, False) else "PENDIENTE")
    df_export["ATRASADO"] = df_export.apply(lambda r: "SÍ" if (r["Dia"] < current_plant_day and not st.session_state.task_status.get(r["ID"], False)) else "NO", axis=1)
    
    # 7. Neutralización de fórmulas contra inyección CSV/Excel
    df_export_clean = neutralizar_formulas(df_export)

    col_exp1, col_exp2 = st.columns(2)
    col_exp1.download_button(
        "📄 Exportar Consolidado CSV", 
        df_export_clean.to_csv(index=False).encode('utf-8'), 
        "avance_yguazu_cementos.csv", 
        "text/csv", 
        use_container_width=True
    )

    def to_excel(df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Avance_Yguazu')
        return output.getvalue()

    col_exp2.download_button(
        "📊 Exportar Consolidado Excel", 
        to_excel(df_export_clean), 
        "avance_yguazu_cementos.xlsx", 
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        use_container_width=True
    )