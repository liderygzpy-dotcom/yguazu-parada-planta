import streamlit as st
import pandas as pd
import io
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Yguazú Cementos - Seguimiento de Parada de Planta",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PROFESIONALES (CORRECCIÓN DE CONTRASTE Y LEGIBILIDAD) ---
st.markdown("""
<style>
    /* Estilos de fondo y tipografía general con contraste óptimo */
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
    }
    
    /* Forzar que todas las etiquetas de los inputs y selectores sean oscuras y legibles */
    label, .stRadio label, .stSelectbox label, .stSlider label, .stFileUploader label {
        color: #0A2540 !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
    }
    
    /* Texto de los radio buttons */
    .stRadio div[role="radiogroup"] label p {
        color: #1e293b !important;
        font-weight: 600 !important;
    }

    /* Header e identidad visual corporativa (Colores sólidos) */
    .header-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: #0A2540;
        padding: 24px 30px;
        border-radius: 12px;
        margin-bottom: 20px;
        border-bottom: 5px solid #C8102E;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    .header-title {
        color: #ffffff;
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .header-subtitle {
        color: #cbd5e1;
        font-size: 1.05rem;
        margin-top: 5px;
        font-weight: 500;
    }
    
    /* Contenedor de Métricas KPI (Colores sólidos sin gradientes) */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-top: 4px solid #0A2540;
        border-radius: 10px;
        padding: 18px 22px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
    }
    .metric-card.kpi-red { border-top-color: #C8102E; }
    .metric-card.kpi-green { border-top-color: #10b981; }
    .metric-card.kpi-yellow { border-top-color: #f59e0b; }
    
    .metric-label {
        font-size: 0.85rem;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0A2540;
        line-height: 1.1;
    }
    .metric-subtext {
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 6px;
    }
    .text-green { color: #10b981; }
    .text-orange { color: #d97706; }
    .text-red { color: #C8102E; }
    .text-blue { color: #0A2540; }

    /* Tarjetas de Clima (Sólidas) */
    .weather-card {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .weather-card.rain {
        border-top: 3px solid #C8102E;
        background-color: #fef2f2;
    }
    .weather-card.sunny {
        border-top: 3px solid #f59e0b;
        background-color: #fffbeb;
    }
    .weather-date {
        font-size: 0.8rem;
        font-weight: 700;
        color: #475569;
        text-transform: uppercase;
    }
    .weather-temp {
        font-size: 1.25rem;
        font-weight: 800;
        color: #0A2540;
        margin: 4px 0;
    }
    .weather-desc {
        font-size: 0.75rem;
        color: #334155;
        font-weight: 600;
    }

    /* Tarjetas de Tareas (Sólidas) */
    .task-card {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-left: 5px solid #64748b;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .task-card.completed {
        border-left-color: #10b981;
        background-color: #ecfdf5;
    }
    .task-card.delayed {
        border-left-color: #C8102E;
        background-color: #fef2f2;
    }
    .task-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0f172a;
    }
    .task-meta {
        font-size: 0.875rem;
        color: #334155;
        margin-top: 6px;
    }
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-right: 6px;
    }
    .badge-sector { background-color: #e2e8f0; color: #0f172a; }
    .badge-resp { background-color: #0A2540; color: #ffffff; }
    .badge-file { background-color: #C8102E; color: #ffffff; }
</style>
""", unsafe_allow_html=True)

if "task_status" not in st.session_state:
    st.session_state.task_status = {}

if "uploaded_data" not in st.session_state:
    st.session_state.uploaded_data = None

# Encabezado Principal Corporativo Yguazú Cementos
st.markdown("""
<div class="header-container">
    <div>
        <div class="header-title">YGUAZÚ CEMENTOS S.A.</div>
        <div class="header-subtitle">🏗️ Sistema de Seguimiento Operativo — Parada Mayor de Planta</div>
    </div>
    <div>
        <img src="https://www.yguazucementos.com.py/images/logo.png" width="160" alt="Yguazú Cementos Logo" onerror="this.src='https://www.yguazucementos.com.py/favicon.ico'">
    </div>
</div>
""", unsafe_allow_html=True)

# SECCIÓN DE PRONÓSTICO DEL TIEMPO (10 DÍAS - PLANTA VILLA HAYES)
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

# Barra Lateral (Soporte Multi-Archivo)
with st.sidebar:
    st.image("https://www.yguazucementos.com.py/images/logo.png", use_container_width=True)
    st.markdown("<h2 style='color:#0A2540;'>⚙️ Carga de Datos</h2>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Cargar Archivos Excel de Sectores (Gantt)", type=["xlsx", "xls"], accept_multiple_files=True)
    
    if uploaded_files:
        try:
            all_parsed_data = []
            
            for uploaded_file in uploaded_files:
                file_name = uploaded_file.name
                xls = pd.ExcelFile(uploaded_file)
                
                for sheet in xls.sheet_names:
                    sheet_upper = sheet.upper()
                    if "GANTT" in sheet_upper:
                        discipline = "MECÁNICA" if "MEC" in sheet_upper else ("ELECTRO-INSTRUMENTACIÓN" if ("ETR" in sheet_upper or "ELEC" in sheet_upper) else "OTRO")
                        
                        df_raw = pd.read_excel(uploaded_file, sheet_name=sheet, header=None)
                        
                        header_row_idx = None
                        for idx, row in df_raw.iterrows():
                            row_str = [str(val).strip().upper() for val in row.values]
                            if "OT" in row_str and "TAG" in row_str:
                                header_row_idx = idx
                                break
                        
                        if header_row_idx is not None:
                            df = pd.read_excel(uploaded_file, sheet_name=sheet, header=header_row_idx)
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
            
            if all_parsed_data:
                st.session_state.uploaded_data = pd.DataFrame(all_parsed_data)
                st.sidebar.success(f"✅ {len(all_parsed_data)} tareas cargadas de {len(uploaded_files)} archivo(s).")
            else:
                st.sidebar.warning("⚠️ No se encontraron tareas en los Gantt de los archivos.")
        except Exception as e:
            st.error(f"Error al procesar los archivos: {e}")

# SI NO HAY ARCHIVOS, MOSTRAR MENSAJE DE ESPERA CON MARCA CORPORATIVA
if st.session_state.uploaded_data is None:
    st.warning("⚠️ **No hay archivos cargados.** Por favor, carga los archivos Excel de tus sectores (ej. `Horno.xlsx`) en la barra lateral para iniciar el seguimiento.")
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

# Filtrar Base Global según filtros seleccionados
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

# Tarjetas KPI Corporativas (Sólidas)
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

# SECCIÓN DE GRÁFICO POR OPERADOR Y CHECKLIST EN DOS COLUMNAS
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
                new_status = st.checkbox("", value=is_done, key=f"chk_{t_id}")
                if new_status != is_done:
                    st.session_state.task_status[t_id] = new_status
                    st.rerun()
            
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
                
                st.markdown(f"""
                <div class="{card_class}">
                    <div class="task-title">OT {row['OT']} — {row['Actividad']}</div>
                    <div class="task-meta">
                        <span class="badge badge-file">📁 {row['Archivo']}</span>
                        <span class="badge badge-sector">📍 {row['Ubicacion']}</span>
                        <span class="badge badge-resp">👤 {row['Responsable']}</span>
                        {status_str}
                    </div>
                </div>
                """, unsafe_allow_html=True)

# Sección de Exportación
st.markdown("---")
st.markdown("### 📥 Exportar Reportes Consolidados")
df_export = df_tasks.copy()
df_export["ESTADO"] = df_export["ID"].apply(lambda tid: "EJECUTADO" if st.session_state.task_status.get(tid, False) else "PENDIENTE")
df_export["ATRASADO"] = df_export.apply(lambda r: "SÍ" if (r["Dia"] < current_plant_day and not st.session_state.task_status.get(r["ID"], False)) else "NO", axis=1)

col_exp1, col_exp2 = st.columns(2)
col_exp1.download_button("📄 Exportar Consolidado CSV", df_export.to_csv(index=False).encode('utf-8'), "avance_yguazu_cementos.csv", "text/css", use_container_width=True)

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Avance_Yguazu')
    return output.getvalue()

col_exp2.download_button("📊 Exportar Consolidado Excel", to_excel(df_export), "avance_yguazu_cementos.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
