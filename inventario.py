import streamlit as st
import pandas as pd
from database import conectar

def inventario(bodega):

    st.subheader("Inventario")

    conn = conectar()

    df = pd.read_sql("""
    SELECT 
        proyecto,
        reserva,
        material,
        texto_material,
        unidad,
        cantidad_necesaria,
        cantidad_tomada,
        ctd_faltante
    FROM inventario
    WHERE bodega=?
    """, conn, params=(bodega,))

    conn.close()

    if df.empty:
        st.info("No hay materiales en el inventario")
        return

    # -------------------------
    # PANEL DE CONTROL
    # -------------------------

    total_materiales = len(df)
    reservas_activas = df["reserva"].nunique()
    faltantes = (df["ctd_faltante"] > 0).sum()
    sin_stock = (df["cantidad_tomada"] <= 0).sum()

    col1,col2,col3,col4 = st.columns(4)

    col1.metric("Materiales", total_materiales)
    col2.metric("Reservas activas", reservas_activas)
    col3.metric("Material faltante", faltantes)
    col4.metric("Sin stock", sin_stock)

    st.divider()

    # -------------------------
    # BUSCADOR
    # -------------------------

    buscar = st.text_input("Buscar por reserva, material o descripción")

    if buscar:
        df = df[
            df["reserva"].astype(str).str.contains(buscar, case=False) |
            df["material"].astype(str).str.contains(buscar, case=False) |
            df["texto_material"].astype(str).str.contains(buscar, case=False)
        ]

    # -------------------------
    # ESTADO MATERIAL
    # -------------------------

    def estado(row):

        if row["cantidad_tomada"] <= 0:
            return "🔴 Sin stock"

        elif row["cantidad_tomada"] < row["cantidad_necesaria"]:
            return "🟡 Pendiente"

        else:
            return "🟢 Completo"

    df["estado"] = df.apply(estado, axis=1)

    # -------------------------
    # RENOMBRAR COLUMNAS
    # -------------------------

    df = df.rename(columns={
        "proyecto":"Proyecto",
        "reserva":"Reserva",
        "material":"Material",
        "texto_material":"Texto material",
        "unidad":"Unidad",
        "cantidad_necesaria":"Cantidad necesaria",
        "cantidad_tomada":"Cantidad tomada",
        "ctd_faltante":"Cantidad faltante",
        "estado":"Estado"
    })

    # -------------------------
    # TABLA INVENTARIO
    # -------------------------

    st.dataframe(df, use_container_width=True)