import streamlit as st
import pandas as pd
from database import conectar


# --------------------------------------------------
# FORMATO NUMEROS TIPO EXCEL / SAP
# --------------------------------------------------
def formato_excel(valor, unidad):
    try:
        unidad = str(unidad).strip().upper()

        if unidad in ["KG", "M"]:
            return f"{float(valor):.3f}".replace(".", ",")

        return str(int(float(valor)))
    except:
        return "0"


# --------------------------------------------------
# CALCULAR ESTADO DEL MATERIAL
# --------------------------------------------------
def calcular_estado(row):
    try:
        necesaria = float(row["cantidad_necesaria"])
        tomada = float(row["cantidad_tomada"])
        faltante = float(row["ctd_faltante"])

        if tomada <= 0:
            return "Sin stock"
        elif faltante > 0 or tomada < necesaria:
            return "Pendiente"
        else:
            return "Completo"
    except:
        return "Pendiente"


# --------------------------------------------------
# FUNCION PRINCIPAL
# --------------------------------------------------
def inventario(bodega):

    st.subheader(f"Inventario - Bodega {bodega}")

    conn = conectar()

    try:
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
            WHERE bodega = %s
            ORDER BY proyecto, reserva, material
        """, conn, params=(bodega,))
    except Exception as e:
        conn.close()
        st.error(f"Error al cargar inventario: {e}")
        return

    conn.close()

    if df.empty:
        st.info(f"No hay materiales en el inventario de {bodega}")
        return

    # --------------------------------------------------
    # LIMPIAR DATOS
    # --------------------------------------------------
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
    ).fillna(0).abs()

    # --------------------------------------------------
    # ESTADO
    # --------------------------------------------------
    df["estado"] = df.apply(calcular_estado, axis=1)

    # --------------------------------------------------
    # PANEL DE CONTROL
    # --------------------------------------------------
    total_filas = len(df)
    materiales_unicos = df["material"].nunique()
    proyectos_activos = df["proyecto"].nunique()
    reservas_activas = df["reserva"].nunique()
    faltantes = (df["ctd_faltante"] > 0).sum()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Filas", int(total_filas))
    col2.metric("Materiales únicos", int(materiales_unicos))
    col3.metric("Proyectos", int(proyectos_activos))
    col4.metric("Reservas", int(reservas_activas))
    col5.metric("Con faltante", int(faltantes))

    st.divider()

    # --------------------------------------------------
    # FILTROS
    # --------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        buscar = st.text_input(
            "Buscar",
            placeholder="Proyecto, reserva, material o descripción"
        )

    with col2:
        proyectos = ["Todos"] + sorted(
            [p for p in df["proyecto"].dropna().unique().tolist() if p.strip() != ""]
        )
        proyecto_sel = st.selectbox("Proyecto", proyectos)

    with col3:
        reservas = ["Todas"] + sorted(
            [r for r in df["reserva"].dropna().unique().tolist() if r.strip() != ""]
        )
        reserva_sel = st.selectbox("Reserva", reservas)

    with col4:
        estados = ["Todos", "Sin stock", "Pendiente", "Completo"]
        estado_sel = st.selectbox("Estado", estados)

    # --------------------------------------------------
    # APLICAR FILTROS
    # --------------------------------------------------
    if buscar:
        df = df[
            df["proyecto"].str.contains(buscar, case=False, na=False) |
            df["reserva"].str.contains(buscar, case=False, na=False) |
            df["material"].str.contains(buscar, case=False, na=False) |
            df["texto_material"].str.contains(buscar, case=False, na=False)
        ]

    if proyecto_sel != "Todos":
        df = df[df["proyecto"] == proyecto_sel]

    if reserva_sel != "Todas":
        df = df[df["reserva"] == reserva_sel]

    if estado_sel != "Todos":
        df = df[df["estado"] == estado_sel]

    if df.empty:
        st.info(f"No hay resultados para la bodega {bodega}")
        return

    # --------------------------------------------------
    # ORDENAR TABLA FINAL
    # --------------------------------------------------
    df = df.sort_values(
        by=["proyecto", "reserva", "material"],
        ascending=[True, True, True]
    )

    # --------------------------------------------------
    # VISTA FORMATEADA
    # --------------------------------------------------
    vista = df.copy()

    vista["estado"] = vista["estado"].map({
        "Sin stock": "🔴 Sin stock",
        "Pendiente": "🟡 Pendiente",
        "Completo": "🟢 Completo"
    })

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

    # --------------------------------------------------
    # RENOMBRAR COLUMNAS TIPO SAP
    # --------------------------------------------------
    vista = vista.rename(columns={
        "proyecto": "Definición proyecto",
        "reserva": "Reserva",
        "material": "Material",
        "texto_material": "Texto material",
        "unidad": "Unidad medida entrada",
        "cantidad_necesaria": "Cantidad necesaria",
        "cantidad_tomada": "Cantidad tomada",
        "ctd_faltante": "Ctd.faltante",
        "estado": "Estado"
    })

    # --------------------------------------------------
    # ORDEN FINAL DE COLUMNAS
    # --------------------------------------------------
    vista = vista[
        [
            "Definición proyecto",
            "Reserva",
            "Material",
            "Texto material",
            "Unidad medida entrada",
            "Cantidad necesaria",
            "Cantidad tomada",
            "Ctd.faltante",
            "Estado"
        ]
    ]

    # --------------------------------------------------
    # TABLA INVENTARIO
    # --------------------------------------------------
    st.markdown("### Detalle de inventario")
    st.dataframe(vista, use_container_width=True, hide_index=True)