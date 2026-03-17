import streamlit as st
from login import login
from ingreso_material import ingreso_material
from salida_material import salida_material
from inventario import inventario
from inventario_general import inventario_general
from reportes import reportes
from cargar_excel import cargar_excel_inventario
from usuarios import usuarios
from gestion_trabajos import gestion_trabajos

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------

st.set_page_config(
    page_title="SERVILEV PRO",
    page_icon="📦",
    layout="wide"
)

# --------------------------------------------------
# INICIALIZAR SESIÓN
# --------------------------------------------------

def inicializar_sesion():

    if "logueado" not in st.session_state:
        st.session_state.logueado = False

    if "usuario" not in st.session_state:
        st.session_state.usuario = ""

    if "rol" not in st.session_state:
        st.session_state.rol = ""

    if "bodega" not in st.session_state:
        st.session_state.bodega = "Constitución"


inicializar_sesion()

# --------------------------------------------------
# LOGIN
# --------------------------------------------------

if not st.session_state.logueado:
    login()
    st.stop()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.markdown("## 🏭 SERVILEV PRO")

st.sidebar.info(f"""
👤 **Usuario:** {st.session_state.usuario}

🔑 **Rol:** {st.session_state.rol}
""")

# --------------------------------------------------
# SELECCIÓN DE BODEGA
# --------------------------------------------------

st.session_state.bodega = st.sidebar.selectbox(
    "Seleccionar Bodega",
    ["Constitución", "Hualañé"]
)

bodega = st.session_state.bodega

st.sidebar.markdown("---")

# --------------------------------------------------
# MENÚ SEGÚN ROL
# --------------------------------------------------

def obtener_menu(rol):

    if rol == "admin":
        return [
            "🛠 Trabajos",
            "📥 Entrada",
            "📤 Salida",
            "📦 Inventario",
            "📊 Inventario General",
            "📑 Reportes",
            "📂 Cargar Excel",
            "👥 Usuarios"
        ]

    elif rol == "bodega":
        return [
            "🛠 Trabajos",
            "📥 Entrada",
            "📤 Salida",
            "📦 Inventario",
            "📊 Inventario General",
            "📑 Reportes"
        ]

    else:
        return [
            "📦 Inventario",
            "📊 Inventario General",
            "📑 Reportes"
        ]


menu = obtener_menu(st.session_state.rol)

accion = st.sidebar.selectbox("Menú", menu)

# --------------------------------------------------
# TÍTULO
# --------------------------------------------------

st.title(f"📦 Sistema SERVILEV - Bodega {bodega}")

# --------------------------------------------------
# ROUTER DE PÁGINAS (MEJORADO 🔥)
# --------------------------------------------------

paginas = {
    "🛠 Trabajos": gestion_trabajos,
    "📥 Entrada": ingreso_material,
    "📤 Salida": salida_material,
    "📦 Inventario": inventario,
    "📊 Inventario General": inventario_general,
    "📑 Reportes": reportes,
    "📂 Cargar Excel": cargar_excel_inventario,
    "👥 Usuarios": usuarios
}

# 🔥 EJECUCIÓN INTELIGENTE (NUEVO)

if accion in paginas:
    try:
        paginas[accion](bodega)
    except TypeError:
        paginas[accion]()

# --------------------------------------------------
# SIDEBAR EXTRA
# --------------------------------------------------

st.sidebar.markdown("---")

if st.sidebar.button("🔄 Actualizar sistema"):
    st.rerun()

# --------------------------------------------------
# CERRAR SESIÓN
# --------------------------------------------------

if st.sidebar.button("🚪 Cerrar sesión"):

    st.session_state.logueado = False
    st.session_state.usuario = ""
    st.session_state.rol = ""

    st.rerun()

# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.markdown("---")
st.caption("SERVILEV PRO • Sistema de Gestión de Inventario")