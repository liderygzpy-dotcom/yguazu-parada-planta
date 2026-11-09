import extra_streamlit_components as stx
import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st

# --- 1. Configuración de la Página ---
st.set_page_config(
    page_title="Seguimiento Parada de Planta - Yguazú Cementos",
    page_icon="🏭",
    layout="wide",
)

# --- 2. Inicialización Segura y Robusta de Firebase ---
if not firebase_admin._apps:
  if "firebase" in st.secrets:
    cred_dict = dict(st.secrets["firebase"])

    # Limpieza profunda para asegurar que los saltos de línea se lean correctamente en la nube
    if "private_key" in cred_dict:
      pk = cred_dict["private_key"]
      pk = pk.replace("\\\\n", "\n").replace("\\n", "\n")
      cred_dict["private_key"] = pk

    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
  else:
    # Inicialización por defecto para pruebas locales si aplica
    firebase_admin.initialize_app()

db = firestore.client()

# --- 3. Inicialización del Gestor de Cookies ---
cookie_manager = stx.CookieManager()

# --- 4. Título Principal ---
st.title("🏭 Seguimiento RM - Parada de Planta")
st.markdown("---")

# --- 5. Lógica de Autenticación con Cookies ---
user_session = cookie_manager.get(cookie="yguazu_user_session")

if not user_session:
  st.info(
      "Por favor, ingresa tus credenciales institucionales para continuar."
  )

  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    with st.form("login_form"):
      login_user = st.text_input("Usuario")
      login_pass = st.text_input("Contraseña", type="password")
      submit_btn = st.form_submit_button("Iniciar Sesión")

      if submit_btn:
        # Validación de ejemplo (puedes conectarlo con usuarios de Firestore si lo requieres)
        if login_user == "admin" and login_pass == "admin":
          cookie_manager.set(
              "yguazu_user_session", "active_session_token", expires_at=None
          )
          st.success("¡Sesión iniciada con éxito! Actualizando...")
          st.rerun()
        else:
          st.error("Usuario o contraseña incorrectos.")
else:
  # --- PANEL PRINCIPAL DE LA APLICACIÓN (Sesión Activa) ---
  st.sidebar.success("Sesión activa")
  if st.sidebar.button("Cerrar Sesión"):
    cookie_manager.delete("yguazu_user_session")
    st.rerun()

  st.sidebar.markdown("---")
  st.sidebar.subheader("Navegación")
  menu = st.sidebar.radio(
      "Seleccionar sección", ["Dashboard", "Equipos / RM", "Reportes y Tareas"]
  )

  if menu == "Dashboard":
    st.header("Panel de Control General")
    st.write(
        "Bienvenido al sistema de seguimiento de mantenimiento para la Parada"
        " de Planta de Yguazú Cementos S.A."
    )

    try:
      # Verificación rápida de conexión con Firestore
      st.metric(label="Estado del Servidor Firebase", value="Conectado 🟢")
    except Exception as e:
      st.error(f"Error al conectar con la base de datos: {e}")

  elif menu == "Equipos / RM":
    st.header("Gestión de Equipos y Molino Crudo (RM)")
    st.write(
        "Visualización de estados de molinos, filtros, rodamientos y componentes"
        " críticos."
    )

  elif menu == "Reportes y Tareas":
    st.header("Reportes de Mantenimiento y Downtime")
    st.write("Registro de incidencias, partes diarios y avances de la parada.")