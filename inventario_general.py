import streamlit as st
import pandas as pd
from database import conectar
import io
import matplotlib.pyplot as plt

def inventario_general():

    st.subheader("Inventario General Consolidado")

    # -------------------------
    # LEYENDA COLORES
    # -------------------------

    st.markdown("### Estado de Stock")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("🔴 **Stock crítico (0 - 5)**")

    with col2:
        st.markdown("🟠 **Stock bajo (6 - 10)**")

    with col3:
        st.markdown("🟢 **Stock normal (más de 10)**")

    conn = conectar()

    # 🔥 CAMBIO CLAVE PARA SUPABASE
    df = pd.read_sql_query("""
        SELECT 
            material,
            texto_material,
            bodega,
            cantidad_tomada
        FROM inventario
    """, conn)

    conn.close()

    if df.empty:
        st.warning("No hay datos en inventario")
        return

    # -------------------------
    # LIMPIEZA DATOS (IMPORTANTE)
    # -------------------------

    df["cantidad_tomada"] = pd.to_numeric(df["cantidad_tomada"], errors="coerce").fillna(0)

    # -------------------------
    # CONSOLIDAR INVENTARIO
    # -------------------------

    tabla = df.pivot_table(
        index=["material", "texto_material"],
        columns="bodega",
        values="cantidad_tomada",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    # Asegurar bodegas
    if "Constitución" not in tabla.columns:
        tabla["Constitución"] = 0

    if "Hualañé" not in tabla.columns:
        tabla["Hualañé"] = 0

    tabla["Total"] = tabla["Constitución"] + tabla["Hualañé"]

    tabla = tabla.astype({
        "Constitución": "int",
        "Hualañé": "int",
        "Total": "int"
    })

    tabla.columns = [
        "Material",
        "Texto material",
        "Constitución",
        "Hualañé",
        "Total"
    ]

    # -------------------------
    # BUSCADOR
    # -------------------------

    buscar = st.text_input("Buscar material")

    if buscar:
        tabla = tabla[
            tabla["Material"].astype(str).str.contains(buscar, case=False, na=False) |
            tabla["Texto material"].astype(str).str.contains(buscar, case=False, na=False)
        ]

    # -------------------------
    # COLORES STOCK
    # -------------------------

    def color_stock(val):
        if val <= 5:
            return "color:red"
        elif val <= 10:
            return "color:orange"
        else:
            return "color:lightgreen"

    st.dataframe(
        tabla.style.map(color_stock, subset=["Total"]),
        use_container_width=True
    )

    st.write("Materiales registrados:", len(tabla))

    st.divider()

    # -------------------------
    # EXPORTAR EXCEL PROFESIONAL
    # -------------------------

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:

        tabla.to_excel(writer, sheet_name="Inventario", index=False)

        workbook = writer.book
        worksheet = writer.sheets["Inventario"]

        header_format = workbook.add_format({
            "bold": True,
            "border": 1,
            "align": "center"
        })

        cell_format = workbook.add_format({
            "border": 1,
            "align": "center"
        })

        for col_num, value in enumerate(tabla.columns.values):
            worksheet.write(0, col_num, value, header_format)

        worksheet.set_column("A:A", 15)
        worksheet.set_column("B:B", 35)
        worksheet.set_column("C:E", 15, cell_format)

        worksheet.add_table(
            0, 0,
            len(tabla),
            len(tabla.columns)-1,
            {"columns": [{"header": col} for col in tabla.columns]}
        )

    st.download_button(
        "Descargar Inventario Excel",
        output.getvalue(),
        "inventario_general_servilev.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.divider()

    # -------------------------
    # GRAFICO STOCK
    # -------------------------

    total_const = tabla["Constitución"].sum()
    total_hual = tabla["Hualañé"].sum()

    col1, col2, col3 = st.columns([1,2,1])

    with col2:

        fig, ax = plt.subplots(figsize=(3,2))

        ax.bar(
            ["Constitución", "Hualañé"],
            [total_const, total_hual]
        )

        ax.set_title("Stock total por bodega", fontsize=10)
        ax.set_ylabel("Cantidad", fontsize=9)

        ax.tick_params(axis='x', labelsize=9)
        ax.tick_params(axis='y', labelsize=9)

        st.pyplot(fig)