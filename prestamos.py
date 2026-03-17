import streamlit as st
import pandas as pd
from database import conectar

def prestamos(bodega):

    st.subheader("Préstamos entre proyectos")

    conn = conectar()

    df = pd.read_sql("""
    SELECT *
    FROM prestamos
    WHERE bodega=?
    """, conn, params=(bodega,))

    conn.close()

    if df.empty:
        st.info("No hay préstamos registrados")
        return

    st.dataframe(df, use_container_width=True)