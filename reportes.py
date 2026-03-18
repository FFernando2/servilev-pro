import streamlit as st
import pandas as pd
from database import conectar
import io
from datetime import datetime
import matplotlib.pyplot as plt


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

    stock["total_ingreso"] = pd.to_numeric(stock["total_ingreso"], errors="coerce").fillna(0).astype(int)
    stock["total_salida"] = pd.to_numeric(stock["total_salida"], errors="coerce").fillna(0).astype(int)
    stock["stock"] = stock["total_ingreso"] - stock["total_salida"]

    return stock


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

    if not inventario.empty:
        for col in ["cantidad_necesaria", "cantidad_tomada", "ctd_faltante"]:
            if col in inventario.columns:
                inventario[col] = pd.to_numeric(inventario[col], errors="coerce").fillna(0).astype(int)

    if not ingresos.empty and "cantidad" in ingresos.columns:
        ingresos["cantidad"] = pd.to_numeric(ingresos["cantidad"], errors="coerce").fillna(0).astype(int)

    if not salidas.empty and "cantidad" in salidas.columns:
        salidas["cantidad"] = pd.to_numeric(salidas["cantidad"], errors="coerce").fillna(0).astype(int)

    # KPI

    total_ingresos = ingresos["cantidad"].sum() if not ingresos.empty else 0
    total_salidas = salidas["cantidad"].sum() if not salidas.empty else 0
    stock_total = total_ingresos - total_salidas

    col1, col2, col3 = st.columns(3)

    col1.metric("📥 Ingresos", f"{int(total_ingresos):,}")
    col2.metric("📤 Salidas", f"{int(total_salidas):,}")
    col3.metric("📦 Stock Total", f"{int(stock_total):,}")

    st.divider()

    # CONTROL TOTAL INVENTARIO

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

        stock_mostrar = stock.copy()
        stock_mostrar["total_ingreso"] = stock_mostrar["total_ingreso"].map("{:,}".format)
        stock_mostrar["total_salida"] = stock_mostrar["total_salida"].map("{:,}".format)
        stock_mostrar["stock"] = stock_mostrar["stock"].map("{:,}".format)

        st.dataframe(
            stock_mostrar.style.map(color_stock, subset=["stock"]),
            use_container_width=True
        )

        criticos = stock[stock["stock"] <= 5]
        bajos = stock[(stock["stock"] > 5) & (stock["stock"] <= 10)]

        if not criticos.empty:
            st.error(f"⚠️ {len(criticos)} materiales en estado CRÍTICO")

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

    # GRAFICOS

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

    # REPORTES

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
        df = inventario.copy()
        nombre = f"reporte_inventario_{bodega}.xlsx"
        titulo = "REPORTE DE INVENTARIO"

    elif tipo_reporte == "Ingresos":
        df = ingresos.copy()
        nombre = f"reporte_ingresos_{bodega}.xlsx"
        titulo = "REPORTE DE INGRESOS"

    elif tipo_reporte == "Entradas (Detallado)":

        ingresos_det = ingresos.copy()
        ingresos_det["fecha"] = pd.to_datetime(ingresos_det["fecha"], errors="coerce")

        fecha_inicio = st.date_input("Desde")
        fecha_fin = st.date_input("Hasta")

        df = ingresos_det.copy()

        if fecha_inicio and fecha_fin:
            df = df[
                (df["fecha"] >= pd.to_datetime(fecha_inicio)) &
                (df["fecha"] <= pd.to_datetime(fecha_fin))
            ]

        total = df["cantidad"].sum() if not df.empty else 0
        st.metric("Total ingresado", f"{int(total):,}")

        nombre = f"reporte_entradas_{bodega}.xlsx"
        titulo = "REPORTE DE ENTRADAS"

    elif tipo_reporte == "Salidas":
        df = salidas.copy()
        nombre = f"reporte_salidas_{bodega}.xlsx"
        titulo = "REPORTE DE SALIDAS"

    else:
        proyectos = salidas["proyecto"].dropna().unique() if not salidas.empty else []

        if len(proyectos) == 0:
            st.info("No hay datos")
            conn.close()
            return

        proyecto = st.selectbox("Proyecto", proyectos)

        df = salidas[salidas["proyecto"] == proyecto].copy()

        nombre = f"reporte_{proyecto}.xlsx"
        titulo = f"SALIDAS {proyecto}"

    if df.empty:
        st.info("No hay datos")
        conn.close()
        return

    # LIMPIEZA

    df = df.replace([float("inf"), float("-inf")], 0)
    df = df.fillna("")

    # FORMATO VISTA

    df_mostrar = df.copy()

    for col in ["cantidad", "cantidad_necesaria", "cantidad_tomada", "ctd_faltante"]:
        if col in df_mostrar.columns:
            df_mostrar[col] = pd.to_numeric(df_mostrar[col], errors="coerce").fillna(0).astype(int)
            df_mostrar[col] = df_mostrar[col].map("{:,}".format)

    st.dataframe(df_mostrar, use_container_width=True)

    # EXPORTAR EXCEL

    buffer = io.BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="xlsxwriter",
        engine_kwargs={"options": {"nan_inf_to_errors": True}}
    ) as writer:

        df_excel = df.copy()

        for col in ["cantidad", "cantidad_necesaria", "cantidad_tomada", "ctd_faltante"]:
            if col in df_excel.columns:
                df_excel[col] = pd.to_numeric(df_excel[col], errors="coerce").fillna(0).astype(int)

        df_excel.to_excel(writer, sheet_name="Reporte", startrow=7, index=False)

        workbook = writer.book
        worksheet = writer.sheets["Reporte"]

        formato_empresa = workbook.add_format({
            "bold": True,
            "font_size": 20,
            "align": "center"
        })

        formato_titulo = workbook.add_format({
            "bold": True,
            "font_size": 16,
            "align": "center"
        })

        encabezado = workbook.add_format({
            "bold": True,
            "border": 1,
            "align": "center",
            "bg_color": "#305496",
            "font_color": "white"
        })

        formato_tabla = workbook.add_format({
            "border": 1
        })

        formato_numero = workbook.add_format({
            "border": 1,
            "align": "center",
            "num_format": '#,##0'
        })

        columnas = len(df_excel.columns)

        worksheet.merge_range(0, 0, 0, columnas - 1, "SERVILEV", formato_empresa)
        worksheet.merge_range(2, 0, 2, columnas - 1, titulo, formato_titulo)

        fecha_actual = datetime.now().strftime("%d-%m-%Y %H:%M")
        worksheet.write(4, 0, f"Fecha: {fecha_actual}")

        for col_num, value in enumerate(df_excel.columns.values):
            worksheet.write(7, col_num, value, encabezado)

        columnas_numericas = {"cantidad", "cantidad_necesaria", "cantidad_tomada", "ctd_faltante"}

        for row in range(len(df_excel)):
            for col in range(columnas):
                nombre_col = df_excel.columns[col]
                valor = df_excel.iloc[row, col]

                if nombre_col in columnas_numericas:
                    worksheet.write(row + 8, col, valor, formato_numero)
                else:
                    worksheet.write(row + 8, col, valor, formato_tabla)

        for i, col in enumerate(df_excel.columns):
            ancho = max(df_excel[col].astype(str).map(len).max(), len(col)) + 4
            worksheet.set_column(i, i, ancho)

        worksheet.add_table(
            7, 0,
            7 + len(df_excel),
            columnas - 1,
            {
                "columns": [{"header": col} for col in df_excel.columns],
                "style": "Table Style Medium 9"
            }
        )

    buffer.seek(0)

    st.download_button(
        "📥 Descargar Excel",
        buffer,
        nombre,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    conn.close()