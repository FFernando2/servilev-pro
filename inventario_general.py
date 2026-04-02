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
        return "Crítico"
    elif total <= 10:
        return "Bajo"
    return "Normal"


# --------------------------------------------------
# ESTILO DETALLE
# --------------------------------------------------
def estilo_cantidades_detalle(row):
    estilos = []

    try:
        necesaria = float(str(row["Cantidad necesaria"]).replace(",", "."))
        tomada = float(str(row["Cantidad tomada"]).replace(",", "."))
        faltante = float(str(row["Ctd.faltante"]).replace(",", "."))
    except:
        return [""] * len(row)

    for col in row.index:
        if col == "Cantidad necesaria":
            estilos.append("background-color: rgba(79, 195, 247, 0.12); font-weight: 600;")
        elif col == "Cantidad tomada":
            if tomada >= necesaria or abs(tomada - necesaria) < 0.0001:
                estilos.append("background-color: rgba(0, 230, 118, 0.14); font-weight: 700;")
            elif tomada > 0:
                estilos.append("background-color: rgba(255, 213, 79, 0.18); font-weight: 700;")
            else:
                estilos.append("background-color: rgba(255, 82, 82, 0.16); font-weight: 700;")
        elif col == "Ctd.faltante":
            if faltante > 0:
                estilos.append("background-color: rgba(255, 82, 82, 0.16); font-weight: 700;")
            else:
                estilos.append("background-color: rgba(0, 230, 118, 0.14); font-weight: 700;")
        elif col == "Estado":
            if str(row["Estado"]) == "Normal":
                estilos.append("background-color: rgba(0, 230, 118, 0.14); font-weight: 600;")
            elif str(row["Estado"]) == "Bajo":
                estilos.append("background-color: rgba(255, 213, 79, 0.18); font-weight: 600;")
            elif str(row["Estado"]) == "Crítico":
                estilos.append("background-color: rgba(255, 82, 82, 0.16); font-weight: 600;")
            else:
                estilos.append("")
        else:
            estilos.append("")

    return estilos


# --------------------------------------------------
# ESTILO RESUMEN
# --------------------------------------------------
def estilo_resumen(row):
    estilos = []

    try:
        total = float(str(row["Total"]).replace(",", "."))
    except:
        total = 0

    for col in row.index:
        if col == "Total":
            if total <= 5:
                estilos.append("background-color: rgba(255, 82, 82, 0.16); font-weight: 700;")
            elif total <= 10:
                estilos.append("background-color: rgba(255, 213, 79, 0.18); font-weight: 700;")
            else:
                estilos.append("background-color: rgba(0, 230, 118, 0.14); font-weight: 700;")
        elif col == "Estado":
            if str(row["Estado"]) == "Normal":
                estilos.append("background-color: rgba(0, 230, 118, 0.14); font-weight: 600;")
            elif str(row["Estado"]) == "Bajo":
                estilos.append("background-color: rgba(255, 213, 79, 0.18); font-weight: 600;")
            elif str(row["Estado"]) == "Crítico":
                estilos.append("background-color: rgba(255, 82, 82, 0.16); font-weight: 600;")
            else:
                estilos.append("")
        else:
            estilos.append("")

    return estilos


# --------------------------------------------------
# LIMPIAR TEXTO
# --------------------------------------------------
def limpiar_texto_df(df, columnas):
    df = df.copy()
    for col in columnas:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
            df[col] = df[col].replace("nan", "")
            df[col] = df[col].replace("None", "")
    return df


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
    finally:
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

    df = limpiar_texto_df(df, columnas_texto)

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
        lista_bodegas = ["Todas"] + sorted(
            [b for b in df["bodega"].dropna().unique().tolist() if str(b).strip() != ""]
        )
        bodega_sel = st.selectbox("Bodega", lista_bodegas)

    with col3:
        proyectos = ["Todos"] + sorted(
            [p for p in df["proyecto"].dropna().unique().tolist() if str(p).strip() != ""]
        )
        proyecto_sel = st.selectbox("Proyecto", proyectos)

    with col4:
        vista_sel = st.selectbox(
            "Vista",
            ["Detalle limpio", "Detalle completo SAP", "Resumen consolidado"]
        )

    df_filtrado = df.copy()

    if buscar:
        df_filtrado = df_filtrado[
            df_filtrado["material"].str.contains(buscar, case=False, na=False) |
            df_filtrado["texto_material"].str.contains(buscar, case=False, na=False) |
            df_filtrado["reserva"].str.contains(buscar, case=False, na=False) |
            df_filtrado["proyecto"].str.contains(buscar, case=False, na=False) |
            df_filtrado["grafo"].str.contains(buscar, case=False, na=False) |
            df_filtrado["batch"].str.contains(buscar, case=False, na=False)
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
    st.caption("Azul: necesaria | Verde: completo/normal | Amarillo: parcial/bajo | Rojo: faltante/crítico")

    # ==================================================
    # DETALLE LIMPIO
    # ==================================================
    if vista_sel == "Detalle limpio":
        vista = df_filtrado.copy()
        vista["estado_stock"] = vista["cantidad_tomada"].apply(calcular_estado_stock)

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
            "reserva": "Reserva",
            "material": "Material",
            "texto_material": "Texto material",
            "cantidad_necesaria": "Cantidad necesaria",
            "cantidad_tomada": "Cantidad tomada",
            "ctd_faltante": "Ctd.faltante",
            "unidad": "Unidad medida entrada",
            "estado_stock": "Estado",
            "bodega": "Bodega"
        })

        vista = vista[
            [
                "Definición proyecto",
                "Reserva",
                "Material",
                "Texto material",
                "Cantidad necesaria",
                "Cantidad tomada",
                "Ctd.faltante",
                "Unidad medida entrada",
                "Estado",
                "Bodega"
            ]
        ]

        st.markdown("### Inventario general")
        st.dataframe(
            vista.style.apply(estilo_cantidades_detalle, axis=1),
            use_container_width=True,
            hide_index=True
        )

    # ==================================================
    # DETALLE COMPLETO SAP
    # ==================================================
    elif vista_sel == "Detalle completo SAP":
        vista = df_filtrado.copy()
        vista["estado_stock"] = vista["cantidad_tomada"].apply(calcular_estado_stock)

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
            "estado_stock": "Estado",
            "bodega": "Bodega"
        })

        vista = vista[
            [
                "Definición proyecto",
                "Grafo",
                "Reserva",
                "Posición",
                "Operación",
                "Material",
                "Texto material",
                "Batch",
                "Cantidad necesaria",
                "Cantidad tomada",
                "Ctd.faltante",
                "Unidad medida entrada",
                "Price/LCurrency",
                "Storage location",
                "Existe pedido",
                "Movement type",
                "Estado",
                "Bodega"
            ]
        ]

        st.markdown("### Inventario general completo")
        st.dataframe(
            vista.style.apply(estilo_cantidades_detalle, axis=1),
            use_container_width=True,
            hide_index=True
        )

    # ==================================================
    # RESUMEN CONSOLIDADO
    # ==================================================
    else:
        tabla = df_filtrado.groupby(
            ["material", "texto_material", "unidad"],
            as_index=False,
            dropna=False
        ).agg({
            "cantidad_tomada": "sum"
        })

        tabla["estado"] = tabla["cantidad_tomada"].apply(calcular_estado_stock)
        tabla["Total"] = tabla.apply(
            lambda r: formato_excel(r["cantidad_tomada"], r["unidad"]), axis=1
        )

        tabla = tabla.rename(columns={
            "material": "Material",
            "texto_material": "Texto material",
            "unidad": "Unidad medida entrada",
            "estado": "Estado"
        })

        tabla = tabla[
            ["Material", "Texto material", "Unidad medida entrada", "Total", "Estado"]
        ]

        st.markdown("### Resumen consolidado")
        st.dataframe(
            tabla.style.apply(estilo_resumen, axis=1),
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    # --------------------------------------------------
    # GRAFICO
    # --------------------------------------------------
    resumen = df_filtrado.groupby("bodega", as_index=False)["cantidad_tomada"].sum()

    if not resumen.empty:
        st.markdown("### Gráfico por bodega")

        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.bar(resumen["bodega"], resumen["cantidad_tomada"])
        ax.set_title("Cantidad tomada por bodega")
        ax.set_ylabel("Total")
        ax.set_xlabel("Bodega")
        st.pyplot(fig)