import streamlit as st
import extra_streamlit_components as stx
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. Inicialización de Firebase (Evita errores de reinicio) ---
if not firebase_admin._apps:
    # Si usas credenciales desde los secretos de Streamlit Cloud:
    if "firebase" in st.secrets:
        cred_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    else:
        # Fallback local o inicialización por defecto si aplica
        firebase_admin.initialize_app()

db = firestore.client()

# --- 2. Inicialización del Gestor de Cookies ---
cookie_manager = stx.CookieManager()

# --- 3. Configuración de la Página ---
st.set_page_config(
    page_title="Seguimiento Parada de Planta",
    page_icon="🏭",
    layout="wide"
)

st.title("🏭 Seguimiento RM - Parada de Planta")

# Ejemplo de lectura/escritura de cookies para autenticación o sesión
user_session = cookie_manager.get(cookie="yguazu_user_session")

if not user_session:
    st.info("Por favor, inicia sesión para continuar.")
    # Aquí puedes colocar tu formulario de login
    login_user = st.text_input("Usuario")
    login_pass = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar"):
        if login_user == "admin" and login_pass == "admin": # Reemplaza con tu lógica de Firebase
            cookie_manager.set("yguazu_user_session", "active_token", expires_at=None)
            st.success("¡Sesión iniciada con éxito! Recargando...")
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
else:
    st.success("Sesión activa detectada.")
    if st.button("Cerrar Sesión"):
        cookie_manager.delete("yguazu_user_session")
        st.rerun()
        
    # --- AQUÍ VA EL RESTO DE TU APLICACIÓN PRINCIPAL ---
    st.write("Bienvenido al panel de control de la parada de planta de Yguazú Cementos S.A.")