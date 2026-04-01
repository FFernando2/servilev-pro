import streamlit as st
import pandas as pd
from database import conectar
import matplotlib.pyplot as plt


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
# CALCULAR ESTADO DE STOCK
# --------------------------------------------------
def calcular_estado_stock(total):
    try:
        total = float(total)
    except:
        return "Sin dato"

    if total <= 5:
        return "🔴 Crítico"
    elif total <= 10:
        return "🟠 Bajo"
    return "🟢 Normal"


# --------------------------------------------------
# FUNCION PRINCIPAL
# --------------------------------------------------
def inventario_general():

    st.subheader("Inventario General")

    conn = conectar()

    try:
        df = pd.read_sql("""
            SELECT
                proyecto,
                grafo,
                reserva,
                posicion,
                operacion,
                material,
                texto_material,
                batch,
                unidad,
                cantidad_necesaria,
                cantidad_tomada,
                ctd_faltante,
                price_lcurrency,
                storage_location,
                existe_pedido,
                movement_type,
                bodega
            FROM inventario
            ORDER BY proyecto, reserva, material
        """, conn)
    except Exception as e:
        conn.close()
        st.error(f"Error al cargar inventario: {e}")
        return

    conn.close()

    if df.empty:
        st.warning("No hay datos en inventario")
        return

    # --------------------------------------------------
    # LIMPIEZA
    # --------------------------------------------------
    columnas_texto = [
        "proyecto", "grafo", "reserva", "posicion", "operacion",
        "material", "texto_material", "batch", "unidad",
        "price_lcurrency", "storage_location",
        "existe_pedido", "movement_type", "bodega"
    ]

    for col in columnas_texto:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    df["unidad"] = df["unidad"].str.upper()

    df["cantidad_necesaria"] = pd.to_numeric(df["cantidad_necesaria"], errors="coerce").fillna(0)
    df["cantidad_tomada"] = pd.to_numeric(df["cantidad_tomada"], errors="coerce").fillna(0)
    df["ctd_faltante"] = pd.to_numeric(df["ctd_faltante"], errors="coerce").fillna(0).abs()

    # --------------------------------------------------
    # FILTROS
    # --------------------------------------------------
    st.markdown("### Filtros")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        buscar = st.text_input("Buscar", placeholder="Proyecto, reserva, material...")

    with col2:
        lista_bodegas = ["Todas"] + sorted(df["bodega"].dropna().unique().tolist())
        bodega_sel = st.selectbox("Bodega", lista_bodegas)

    with col3:
        proyectos = ["Todos"] + sorted(df["proyecto"].dropna().unique().tolist())
        proyecto_sel = st.selectbox("Proyecto", proyectos)

    with col4:
        vista_sel = st.selectbox("Vista", ["Detalle SAP", "Resumen consolidado"])

    df_filtrado = df.copy()

    if buscar:
        df_filtrado = df_filtrado[
            df_filtrado["material"].str.contains(buscar, case=False, na=False) |
            df_filtrado["texto_material"].str.contains(buscar, case=False, na=False) |
            df_filtrado["reserva"].str.contains(buscar, case=False, na=False) |
            df_filtrado["proyecto"].str.contains(buscar, case=False, na=False)
        ]

    if bodega_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado["bodega"] == bodega_sel]

    if proyecto_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["proyecto"] == proyecto_sel]

    if df_filtrado.empty:
        st.info("No hay resultados")
        return

    # --------------------------------------------------
    # METRICAS
    # --------------------------------------------------
    st.markdown("### Resumen")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Filas", len(df_filtrado))
    m2.metric("Materiales", df_filtrado["material"].nunique())
    m3.metric("Reservas", df_filtrado["reserva"].nunique())
    m4.metric("Proyectos", df_filtrado["proyecto"].nunique())

    st.divider()

    # ==================================================
    # VISTA DETALLE SAP
    # ==================================================
    if vista_sel == "Detalle SAP":

        vista = df_filtrado.copy()

        vista["cantidad_necesaria"] = vista.apply(
            lambda r: formato_excel(r["cantidad_necesaria"], r["unidad"]), axis=1
        )

        vista["cantidad_tomada"] = vista.apply(
            lambda r: formato_excel(r["cantidad_tomada"], r["unidad"]), axis=1
        )

        vista["ctd_faltante"] = vista.apply(
            lambda r: formato_excel(r["ctd_faltante"], r["unidad"]), axis=1
        )

        vista = vista.rename(columns={
            "proyecto": "Definición proyecto",
            "grafo": "Grafo",
            "reserva": "Reserva",
            "posicion": "Posición",
            "operacion": "Operación",
            "material": "Material",
            "texto_material": "Texto material",
            "batch": "Batch",
            "unidad": "Unidad medida entrada",
            "cantidad_necesaria": "Cantidad necesaria",
            "cantidad_tomada": "Cantidad tomada",
            "ctd_faltante": "Ctd.faltante",
            "price_lcurrency": "Price/LCurrency",
            "storage_location": "Storage location",
            "existe_pedido": "Existe pedido",
            "movement_type": "Movement type",
            "bodega": "Bodega"
        })

        columnas = [
            "Definición proyecto", "Grafo", "Reserva", "Posición",
            "Operación", "Material", "Texto material", "Batch",
            "Cantidad necesaria", "Cantidad tomada", "Ctd.faltante",
            "Unidad medida entrada", "Price/LCurrency",
            "Storage location", "Existe pedido",
            "Movement type", "Bodega"
        ]

        st.dataframe(vista[columnas], use_container_width=True, hide_index=True)

    # ==================================================
    # VISTA RESUMEN
    # ==================================================
    else:

        tabla = df_filtrado.groupby(
            ["material", "texto_material", "unidad"],
            as_index=False
        )["cantidad_tomada"].sum()

        tabla["Estado"] = tabla["cantidad_tomada"].apply(calcular_estado_stock)

        tabla["cantidad_tomada"] = tabla.apply(
            lambda r: formato_excel(r["cantidad_tomada"], r["unidad"]), axis=1
        )

        tabla = tabla.rename(columns={
            "material": "Material",
            "texto_material": "Texto material",
            "unidad": "Unidad medida entrada",
            "cantidad_tomada": "Total"
        })

        st.dataframe(tabla, use_container_width=True, hide_index=True)

    # --------------------------------------------------
    # GRAFICO
    # --------------------------------------------------
    resumen = df_filtrado.groupby("bodega")["cantidad_tomada"].sum().reset_index()

    if not resumen.empty:
        st.markdown("### Gráfico por bodega")

        fig, ax = plt.subplots()
        ax.bar(resumen["bodega"], resumen["cantidad_tomada"])
        st.pyplot(fig)