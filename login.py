# login.py
import streamlit as st
from database import conectar
from werkzeug.security import check_password_hash

def login():

    if "logueado" not in st.session_state:
        st.session_state.logueado = False
    if "usuario" not in st.session_state:
        st.session_state.usuario = ""
    if "rol" not in st.session_state:
        st.session_state.rol = ""

    st.markdown("""
    <style>
    .login-box {
        max-width: 420px;
        margin: 60px auto;
        padding: 30px;
        border-radius: 16px;
        background: #111827;
        border: 1px solid #374151;
        box-shadow: 0 8px 25px rgba(0,0,0,0.30);
    }
    .login-title {
        text-align: center;
        font-size: 30px;
        font-weight: bold;
        color: white;
        margin-bottom: 8px;
    }
    .login-subtitle {
        text-align: center;
        color: #9ca3af;
        font-size: 14px;
        margin-bottom: 25px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">🔐 SERVILEV PRO</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Sistema de control de bodega e inventario</div>', unsafe_allow_html=True)

    usuario = st.text_input("Usuario")
    contrasena = st.text_input("Contraseña", type="password")

    if st.button("Ingresar", use_container_width=True):

        usuario = usuario.strip()
        contrasena = contrasena.strip()

        if usuario == "" or contrasena == "":
            st.warning("Ingrese usuario y contraseña")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        conn = None

        try:
            conn = conectar()
            c = conn.cursor()

            # Buscar solo por usuario
            c.execute(
                "SELECT usuario, rol, contrasena FROM usuarios WHERE usuario=%s",
                (usuario,)
            )

            resultado = c.fetchone()

            if resultado:
                usuario_db, rol_db, hash_db = resultado

                if check_password_hash(hash_db, contrasena):
                    st.session_state.logueado = True
                    st.session_state.usuario = usuario_db
                    st.session_state.rol = rol_db

                    st.success("Ingreso correcto ✅")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
            else:
                st.error("Usuario o contraseña incorrectos")

        except Exception as e:
            st.error(f"Error de conexión: {e}")

        finally:
            if conn:
                conn.close()

    st.markdown('</div>', unsafe_allow_html=True)