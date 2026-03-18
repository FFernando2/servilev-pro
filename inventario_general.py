import streamlit as st
import pandas as pd
from database import conectar
import io
import matplotlib.pyplot as plt


def inventario_general():

    st.subheader("Inventario General Consolidado")

    st.markdown("### Estado de Stock")

    col1, col2, col3 = st.columns(3)

    col1.markdown("🔴 Stock crítico (0 - 5)")
    col2.markdown("🟠 Stock bajo (6 - 10)")
    col3.markdown("🟢 Stock normal (>10)")

    conn = conectar()

    df = pd.read_sql("""
        SELECT 
            material,
            texto_material,
            bodega,
            cantidad_tomada
        FROM inventario
    """, conn)

    conn.close()

    if df.empty:
        st.warning("No hay datos")
        return

    # -------------------------
    # CONSOLIDAR
    # -------------------------

    tabla = df.pivot_table(
        index=["material", "texto_material"],
        columns="bodega",
        values="cantidad_tomada",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    if "Constitución" not in tabla.columns:
        tabla["Constitución"] = 0

    if "Hualañé" not in tabla.columns:
        tabla["Hualañé"] = 0

    tabla["Total"] = tabla["Constitución"] + tabla["Hualañé"]

    # -------------------------
    # SIN DECIMALES
    # -------------------------

    tabla["Constitución"] = tabla["Constitución"].astype(int)
    tabla["Hualañé"] = tabla["Hualañé"].astype(int)
    tabla["Total"] = tabla["Total"].astype(int)

    # -------------------------
    # RENOMBRAR
    # -------------------------

    tabla.columns = [
        "Material",
        "Texto material",
        "Constitución",
        "Hualañé",
        "Total"
    ]

    # -------------------------
    # BUSCAR
    # -------------------------

    buscar = st.text_input("Buscar material")

    if buscar:

        tabla = tabla[
            tabla["Material"].str.contains(buscar, case=False, na=False) |
            tabla["Texto material"].str.contains(buscar, case=False, na=False)
        ]

    # -------------------------
    # COLORES STOCK
    # -------------------------

    def color_stock(val):

        val = int(val)

        if val <= 5:
            return "color:red"

        elif val <= 10:
            return "color:orange"

        else:
            return "color:green"

    # -------------------------
    # FORMATO EXCEL (MILES)
    # -------------------------

    tabla["Constitución"] = tabla["Constitución"].map("{:,}".format)
    tabla["Hualañé"] = tabla["Hualañé"].map("{:,}".format)
    tabla["Total"] = tabla["Total"].map("{:,}".format)

    st.dataframe(
        tabla.style.map(color_stock, subset=["Total"]),
        use_container_width=True
    )

    st.write("Materiales:", len(tabla))

    st.divider()

    # -------------------------
    # GRAFICO
    # -------------------------

    total_const = df[df["bodega"] == "Constitución"]["cantidad_tomada"].sum()
    total_hual = df[df["bodega"] == "Hualañé"]["cantidad_tomada"].sum()

    col1, col2, col3 = st.columns([1,2,1])

    with col2:

        fig, ax = plt.subplots(figsize=(4,3))

        ax.bar(
            ["Constitución","Hualañé"],
            [total_const, total_hual]
        )

        ax.set_title("Stock total por bodega")

        st.pyplot(fig)