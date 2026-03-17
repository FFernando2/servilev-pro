# login.py
import streamlit as st
from database import conectar

def login():

    st.title("🔐 Login Sistema SERVILEV")

    usuario = st.text_input("Usuario")
    contrasena = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):

        conn = conectar()
        c = conn.cursor()

        c.execute(
            "SELECT usuario, rol FROM usuarios WHERE usuario=? AND contrasena=?",
            (usuario, contrasena)
        )

        resultado = c.fetchone()
        conn.close()

        if resultado:

            st.session_state['logueado'] = True
            st.session_state['usuario'] = resultado[0]
            st.session_state['rol'] = resultado[1]

            st.success("Ingreso correcto ✅")
            st.rerun()

        else:
            st.error("Usuario o contraseña incorrectos ❌")