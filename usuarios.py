# usuarios.py
import streamlit as st
import pandas as pd
from database import conectar
from werkzeug.security import generate_password_hash


def usuarios():

    # --------------------------------------------------
    # SEGURIDAD (solo admin)
    # --------------------------------------------------

    if st.session_state.rol != "admin":
        st.error("⛔ No tienes permisos para acceder a esta sección")
        st.stop()

    st.title("Administración de Usuarios")

    conn = conectar()
    c = conn.cursor()

    # --------------------------------------------------
    # MOSTRAR USUARIOS
    # --------------------------------------------------

    df = pd.read_sql("SELECT id, usuario, rol FROM usuarios ORDER BY id", conn)

    st.subheader("Usuarios del sistema")
    st.dataframe(df, use_container_width=True)

    st.markdown("---")

    # --------------------------------------------------
    # CREAR USUARIO
    # --------------------------------------------------

    st.subheader("Crear nuevo usuario")

    col1, col2, col3 = st.columns(3)

    with col1:
        nuevo_usuario = st.text_input("Usuario")

    with col2:
        nueva_contrasena = st.text_input("Contraseña", type="password")

    with col3:
        nuevo_rol = st.selectbox(
            "Rol",
            ["admin", "bodega", "consulta"]
        )

    if st.button("Crear usuario"):

        nuevo_usuario = nuevo_usuario.strip()
        nueva_contrasena = nueva_contrasena.strip()

        if nuevo_usuario == "" or nueva_contrasena == "":
            st.warning("Debes completar todos los campos")

        else:
            try:
                # 🔐 Encriptar contraseña antes de guardar
                hash_pw = generate_password_hash(nueva_contrasena)

                c.execute("""
                    INSERT INTO usuarios (usuario, contrasena, rol)
                    VALUES (%s, %s, %s)
                """, (nuevo_usuario, hash_pw, nuevo_rol))

                conn.commit()

                st.success("Usuario creado correctamente ✅")
                st.rerun()

            except Exception as e:
                conn.rollback()
                st.error(f"⚠️ Error: {e}")

    st.markdown("---")

    # --------------------------------------------------
    # ELIMINAR USUARIO
    # --------------------------------------------------

    st.subheader("Eliminar usuario")

    lista_usuarios = df["usuario"].tolist()

    usuario_eliminar = st.selectbox(
        "Seleccionar usuario",
        lista_usuarios
    )

    if st.button("Eliminar usuario"):

        if usuario_eliminar == "admin":
            st.error("No se puede eliminar el usuario administrador")

        else:
            try:
                c.execute(
                    "DELETE FROM usuarios WHERE usuario=%s",
                    (usuario_eliminar,)
                )

                conn.commit()

                st.success("Usuario eliminado correctamente ✅")
                st.rerun()

            except Exception as e:
                conn.rollback()
                st.error(f"Error: {e}")

    conn.close()