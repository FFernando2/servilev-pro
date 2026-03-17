import streamlit as st
import pandas as pd
from database import conectar

def gestion_trabajos(bodega):

    st.subheader("Gestión de Trabajos")

    conn = conectar()

    # -------------------------
    # CREAR TRABAJO
    # -------------------------

    st.markdown("### Crear nuevo trabajo")

    col1, col2 = st.columns(2)

    with col1:
        proyecto = st.text_input("Proyecto")

    with col2:
        reserva = st.text_input("Número de reserva")

    if st.button("Crear trabajo"):

        if proyecto.strip() == "" or reserva.strip() == "":
            st.warning("Completar campos")

        else:

            c = conn.cursor()

            c.execute("""
            INSERT INTO inventario
            (proyecto,reserva,material,texto_material,unidad,
            cantidad_necesaria,cantidad_tomada,ctd_faltante,bodega)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,(
                proyecto,
                reserva,
                "",
                "",
                "",
                0,
                0,
                0,
                bodega
            ))

            conn.commit()

            st.success("Trabajo creado")

            st.rerun()

    st.divider()

    # -------------------------
    # LISTA DE TRABAJOS
    # -------------------------

    st.markdown("### Trabajos activos")

    df = pd.read_sql("""
    SELECT DISTINCT proyecto,reserva
    FROM inventario
    WHERE bodega=?
    """, conn, params=(bodega,))

    if df.empty:
        st.info("No hay trabajos")

    else:
        st.dataframe(df, use_container_width=True)

    conn.close()