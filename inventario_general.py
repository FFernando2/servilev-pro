import streamlit as st
import pandas as pd
from database import conectar
import matplotlib.pyplot as plt


def formato_excel(valor, unidad):
    try:
        unidad = str(unidad).strip().upper()

        if unidad in ["KG", "M"]:
            return f"{float(valor):.3f}".replace(".", ",")

        return str(int(valor))
    except:
        return "0"


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
            unidad,
            bodega,
            cantidad_tomada
        FROM inventario
    """, conn)

    conn.close()

    if df.empty:
        st.warning("No hay datos")
        return

    # -------------------------
    # LIMPIAR
    # -------------------------
    df["material"] = df["material"].astype(str).str.strip()
    df["texto_material"] = df["texto_material"].astype(str).str.strip()
    df["unidad"] = df["unidad"].astype(str).str.strip().str.upper()
    df["bodega"] = df["bodega"].astype(str).str.strip()
    df["cantidad_tomada"] = pd.to_numeric(df["cantidad_tomada"], errors="coerce").fillna(0)

    # -------------------------
    # CONSOLIDAR
    # -------------------------
    tabla = df.pivot_table(
        index=["material", "texto_material", "unidad"],
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
    # RENOMBRAR
    # -------------------------
    tabla.columns = [
        "Material",
        "Texto material",
        "Unidad",
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
            tabla["Material"].astype(str).str.contains(buscar, case=False, na=False) |
            tabla["Texto material"].astype(str).str.contains(buscar, case=False, na=False)
        ]

    # -------------------------
    # COPIA PARA MOSTRAR FORMATEADA
    # -------------------------
    tabla_mostrar = tabla.copy()

    tabla_mostrar["Constitución"] = tabla_mostrar.apply(
        lambda r: formato_excel(r["Constitución"], r["Unidad"]),
        axis=1
    )

    tabla_mostrar["Hualañé"] = tabla_mostrar.apply(
        lambda r: formato_excel(r["Hualañé"], r["Unidad"]),
        axis=1
    )

    tabla_mostrar["Total"] = tabla_mostrar.apply(
        lambda r: formato_excel(r["Total"], r["Unidad"]),
        axis=1
    )

    # -------------------------
    # COLORES STOCK
    # -------------------------
    def color_stock_fila(row):
        val = float(row["Total_num"])

        if val <= 5:
            color = "color:red"
        elif val <= 10:
            color = "color:orange"
        else:
            color = "color:green"

        return ["", "", "", "", "", color]

    # tabla auxiliar con total numérico para colorear
    tabla_estilo = tabla_mostrar.copy()
    tabla_estilo["Total_num"] = tabla["Total"].values

    st.dataframe(
        tabla_estilo[["Material", "Texto material", "Unidad", "Constitución", "Hualañé", "Total"]]
        .style.apply(
            lambda _: color_stock_fila(tabla_estilo.loc[_ .name]),
            axis=1
        ),
        use_container_width=True,
        hide_index=True
    )

    st.write("Materiales:", len(tabla))

    st.divider()

    # -------------------------
    # GRAFICO
    # -------------------------
    total_const = df[df["bodega"] == "Constitución"]["cantidad_tomada"].sum()
    total_hual = df[df["bodega"] == "Hualañé"]["cantidad_tomada"].sum()

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        fig, ax = plt.subplots(figsize=(4, 3))

        ax.bar(
            ["Constitución", "Hualañé"],
            [total_const, total_hual]
        )

        ax.set_title("Stock total por bodega")

        st.pyplot(fig)