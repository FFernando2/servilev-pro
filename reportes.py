import streamlit as st
import pandas as pd
from database import conectar
import io
from datetime import datetime
import matplotlib.pyplot as plt


# -------------------------
# 🔥 FUNCION STOCK REAL
# -------------------------
def calcular_stock(conn, bodega):

    ingresos = pd.read_sql_query("""
        SELECT material, SUM(cantidad) as total_ingreso
        FROM ingresos
        WHERE bodega=%s
        GROUP BY material
    """, conn, params=(bodega,))

    salidas = pd.read_sql_query("""
        SELECT material, SUM(cantidad) as total_salida
        FROM salidas
        WHERE bodega=%s
        GROUP BY material
    """, conn, params=(bodega,))

    stock = pd.merge(ingresos, salidas, on="material", how="outer").fillna(0)

    stock["stock"] = stock["total_ingreso"] - stock["total_salida"]

    return stock


# -------------------------
# 📊 REPORTES
# -------------------------
def reportes(bodega):

    st.title(f"📊 Reportes del Sistema - Bodega {bodega}")

    conn = conectar()

    inventario = pd.read_sql_query(
        "SELECT * FROM inventario WHERE bodega=%s",
        conn,
        params=(bodega,)
    )

    ingresos = pd.read_sql_query(
        "SELECT * FROM ingresos WHERE bodega=%s",
        conn,
        params=(bodega,)
    )

    salidas = pd.read_sql_query(
        "SELECT * FROM salidas WHERE bodega=%s",
        conn,
        params=(bodega,)
    )

    # -------------------------
    # KPI
    # -------------------------

    total_ingresos = ingresos["cantidad"].sum() if not ingresos.empty else 0
    total_salidas = salidas["cantidad"].sum() if not salidas.empty else 0
    stock_total = total_ingresos - total_salidas

    col1, col2, col3 = st.columns(3)

    col1.metric("📥 Ingresos", int(total_ingresos))
    col2.metric("📤 Salidas", int(total_salidas))
    col3.metric("📦 Stock Total", int(stock_total))

    st.divider()

    # -------------------------
    # CONTROL TOTAL INVENTARIO
    # -------------------------

    st.subheader("📦 Control Total de Inventario")

    stock = calcular_stock(conn, bodega)

    if stock.empty:
        st.warning("No hay movimientos registrados")
    else:

        nombres = pd.read_sql_query("""
            SELECT DISTINCT material, texto_material
            FROM inventario
        """, conn)

        stock = stock.merge(nombres, on="material", how="left")

        stock = stock.sort_values("stock")

        def estado(val):
            if val <= 5:
                return "🔴 Crítico"
            elif val <= 10:
                return "🟠 Bajo"
            else:
                return "🟢 Normal"

        stock["estado"] = stock["stock"].apply(estado)

        def color_stock(val):
            if val <= 5:
                return "color:red"
            elif val <= 10:
                return "color:orange"
            else:
                return "color:green"

        st.dataframe(
            stock.style.map(color_stock, subset=["stock"]),
            use_container_width=True
        )

        criticos = stock[stock["stock"] <= 5]
        bajos = stock[(stock["stock"] > 5) & (stock["stock"] <= 10)]

        if not criticos.empty:
            st.error(f"⚠️ {len(criticos)} materiales en estado CRÍTICO")
            st.dataframe(criticos)

        if not bajos.empty:
            st.warning(f"⚠️ {len(bajos)} materiales con stock BAJO")

        st.divider()

        st.subheader("Materiales más críticos")

        top_criticos = stock.sort_values("stock").head(5)

        fig, ax = plt.subplots()
        ax.bar(top_criticos["material"], top_criticos["stock"])
        ax.set_title("Top materiales críticos")
        ax.set_ylabel("Stock")

        st.pyplot(fig)

    st.divider()

    # -------------------------
    # GRAFICOS
    # -------------------------

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top Ingresos")

        if not ingresos.empty:
            top_ing = ingresos.groupby("material")["cantidad"].sum().sort_values(ascending=False).head(5)

            fig, ax = plt.subplots()
            ax.bar(top_ing.index, top_ing.values)
            st.pyplot(fig)

    with col2:
        st.subheader("Top Salidas")

        if not salidas.empty:
            top_sal = salidas.groupby("material")["cantidad"].sum().sort_values(ascending=False).head(5)

            fig, ax = plt.subplots()
            ax.bar(top_sal.index, top_sal.values)
            st.pyplot(fig)

    st.divider()

    # -------------------------
    # REPORTES
    # -------------------------

    tipo_reporte = st.selectbox(
        "Seleccionar reporte",
        [
            "Inventario completo",
            "Ingresos",
            "Entradas (Detallado)",
            "Salidas",
            "Salidas por proyecto"
        ]
    )

    if tipo_reporte == "Inventario completo":
        df = inventario
        nombre = f"reporte_inventario_{bodega}.xlsx"
        titulo = "REPORTE DE INVENTARIO"

    elif tipo_reporte == "Ingresos":
        df = ingresos
        nombre = f"reporte_ingresos_{bodega}.xlsx"
        titulo = "REPORTE DE INGRESOS"

    elif tipo_reporte == "Entradas (Detallado)":

        ingresos["fecha"] = pd.to_datetime(ingresos["fecha"], errors="coerce")

        fecha_inicio = st.date_input("Desde")
        fecha_fin = st.date_input("Hasta")

        df = ingresos.copy()

        if fecha_inicio and fecha_fin:
            df = df[
                (df["fecha"] >= pd.to_datetime(fecha_inicio)) &
                (df["fecha"] <= pd.to_datetime(fecha_fin))
            ]

        total = df["cantidad"].sum()
        st.metric("Total ingresado", int(total))

        nombre = f"reporte_entradas_{bodega}.xlsx"
        titulo = "REPORTE DE ENTRADAS"

    elif tipo_reporte == "Salidas":
        df = salidas
        nombre = f"reporte_salidas_{bodega}.xlsx"
        titulo = "REPORTE DE SALIDAS"

    else:

        proyecto = st.selectbox("Proyecto", salidas["proyecto"].dropna().unique())

        df = salidas[salidas["proyecto"] == proyecto]

        nombre = f"reporte_{proyecto}.xlsx"
        titulo = f"SALIDAS {proyecto}"

    if df.empty:
        st.info("No hay datos")
        conn.close()
        return

    # LIMPIEZA
    df = df.replace([float("inf"), float("-inf")], 0)
    df = df.fillna("")

    st.dataframe(df, use_container_width=True)

    # -------------------------
    # EXPORTAR EXCEL
    # -------------------------

    buffer = io.BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="xlsxwriter",
        engine_kwargs={"options": {"nan_inf_to_errors": True}}
    ) as writer:

        df.to_excel(writer, sheet_name="Reporte", startrow=7, index=False)

    buffer.seek(0)

    st.download_button(
        "📥 Descargar Excel",
        buffer,
        nombre,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    conn.close()