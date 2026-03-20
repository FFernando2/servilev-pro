import streamlit as st
import pandas as pd
from database import conectar


def formato_excel(valor, unidad):
    try:
        unidad = str(unidad).strip().upper()

        if unidad in ["KG", "M"]:
            return f"{float(valor):.3f}".replace(".", ",")

        return str(int(float(valor)))
    except:
        return "0"


def inventario(bodega):

    st.subheader("Inventario")

    conn = conectar()

    df = pd.read_sql_query("""
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
        WHERE bodega=%s
        ORDER BY proyecto, reserva, material
    """, conn, params=(bodega,))

    conn.close()

    if df.empty:
        st.info("No hay materiales en el inventario")
        return

    # -------------------------
    # LIMPIAR DATOS
    # -------------------------
    df["proyecto"] = df["proyecto"].astype(str).str.strip()
    df["reserva"] = df["reserva"].astype(str).str.strip()
    df["material"] = df["material"].astype(str).str.strip()
    df["texto_material"] = df["texto_material"].astype(str).str.strip()
    df["unidad"] = df["unidad"].astype(str).str.strip().str.upper()

    df["cantidad_necesaria"] = pd.to_numeric(
        df["cantidad_necesaria"], errors="coerce"
    ).fillna(0)

    df["cantidad_tomada"] = pd.to_numeric(
        df["cantidad_tomada"], errors="coerce"
    ).fillna(0)

    df["ctd_faltante"] = pd.to_numeric(
        df["ctd_faltante"], errors="coerce"
    ).fillna(0)

    # -------------------------
    # PANEL DE CONTROL
    # -------------------------
    total_materiales = len(df)
    reservas_activas = df["reserva"].nunique()
    faltantes = (df["ctd_faltante"] > 0).sum()
    sin_stock = (df["cantidad_tomada"] <= 0).sum()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Materiales", int(total_materiales))
    col2.metric("Reservas activas", int(reservas_activas))
    col3.metric("Material faltante", int(faltantes))
    col4.metric("Sin stock", int(sin_stock))

    st.divider()

    # -------------------------
    # BUSCADOR
    # -------------------------
    buscar = st.text_input("Buscar por reserva, material o descripción")

    if buscar:
        df = df[
            df["reserva"].astype(str).str.contains(buscar, case=False, na=False) |
            df["material"].astype(str).str.contains(buscar, case=False, na=False) |
            df["texto_material"].astype(str).str.contains(buscar, case=False, na=False)
        ]

    if df.empty:
        st.info("No se encontraron resultados")
        return

    # -------------------------
    # ESTADO MATERIAL
    # -------------------------
    def estado(row):
        if float(row["cantidad_tomada"]) <= 0:
            return "🔴 Sin stock"
        elif float(row["cantidad_tomada"]) < float(row["cantidad_necesaria"]):
            return "🟡 Pendiente"
        else:
            return "🟢 Completo"

    df["estado"] = df.apply(estado, axis=1)

    # -------------------------
    # FORMATO PARA MOSTRAR
    # -------------------------
    vista = df.copy()

    vista["cantidad_necesaria"] = vista.apply(
        lambda r: formato_excel(r["cantidad_necesaria"], r["unidad"]),
        axis=1
    )

    vista["cantidad_tomada"] = vista.apply(
        lambda r: formato_excel(r["cantidad_tomada"], r["unidad"]),
        axis=1
    )

    vista["ctd_faltante"] = vista.apply(
        lambda r: formato_excel(r["ctd_faltante"], r["unidad"]),
        axis=1
    )

    # -------------------------
    # RENOMBRAR COLUMNAS
    # -------------------------
    vista = vista.rename(columns={
        "proyecto": "Proyecto",
        "reserva": "Reserva",
        "material": "Material",
        "texto_material": "Texto material",
        "unidad": "Unidad",
        "cantidad_necesaria": "Cantidad necesaria",
        "cantidad_tomada": "Cantidad tomada",
        "ctd_faltante": "Cantidad faltante",
        "estado": "Estado"
    })

    # -------------------------
    # ORDEN DE COLUMNAS
    # -------------------------
    vista = vista[
        [
            "Proyecto",
            "Reserva",
            "Material",
            "Texto material",
            "Unidad",
            "Cantidad necesaria",
            "Cantidad tomada",
            "Cantidad faltante",
            "Estado"
        ]
    ]

    # -------------------------
    # TABLA INVENTARIO
    # -------------------------
    st.dataframe(vista, use_container_width=True, hide_index=True)