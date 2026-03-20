import streamlit as st
import pandas as pd
from database import conectar
import io
from datetime import datetime
import matplotlib.pyplot as plt


def formato_excel(valor, unidad):
    try:
        unidad = str(unidad).strip().upper()

        if unidad in ["KG", "M"]:
            return f"{float(valor):.3f}".replace(".", ",")

        return str(int(float(valor)))
    except:
        return "0"


def convertir_numerico(df, columnas):
    for col in columnas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def aplicar_filtros_basicos(df, buscar="", fecha_inicio=None, fecha_fin=None):
    df_filtrado = df.copy()

    if buscar:
        columnas_busqueda = [
            "material", "texto_material", "reserva",
            "proyecto", "documento", "responsable", "usuario"
        ]

        mascara = False
        for col in columnas_busqueda:
            if col in df_filtrado.columns:
                mascara = mascara | df_filtrado[col].astype(str).str.contains(buscar, case=False, na=False)

        df_filtrado = df_filtrado[mascara]

    if "fecha" in df_filtrado.columns:
        df_filtrado["fecha"] = pd.to_datetime(df_filtrado["fecha"], errors="coerce")

        if fecha_inicio is not None:
            df_filtrado = df_filtrado[df_filtrado["fecha"] >= pd.to_datetime(fecha_inicio)]

        if fecha_fin is not None:
            df_filtrado = df_filtrado[df_filtrado["fecha"] <= pd.to_datetime(fecha_fin)]

    return df_filtrado


def calcular_stock(conn, bodega):
    ingresos = pd.read_sql_query("""
        SELECT 
            material,
            COALESCE(MAX(texto_material), '') AS texto_material,
            COALESCE(MAX(unidad), '') AS unidad,
            SUM(COALESCE(cantidad, 0)) AS total_ingreso
        FROM ingresos
        WHERE bodega=%s
        GROUP BY material
    """, conn, params=(bodega,))

    salidas = pd.read_sql_query("""
        SELECT 
            material,
            SUM(COALESCE(cantidad, 0)) AS total_salida
        FROM salidas
        WHERE bodega=%s
        GROUP BY material
    """, conn, params=(bodega,))

    stock = pd.merge(ingresos, salidas, on="material", how="outer").fillna(0)

    if "texto_material" not in stock.columns:
        stock["texto_material"] = ""

    if "unidad" not in stock.columns:
        stock["unidad"] = ""

    stock["total_ingreso"] = pd.to_numeric(stock["total_ingreso"], errors="coerce").fillna(0)
    stock["total_salida"] = pd.to_numeric(stock["total_salida"], errors="coerce").fillna(0)
    stock["stock"] = stock["total_ingreso"] - stock["total_salida"]

    return stock


def preparar_vista_formateada(df):
    df_mostrar = df.copy()

    if "unidad" in df_mostrar.columns:
        for col in ["cantidad", "cantidad_necesaria", "cantidad_tomada", "ctd_faltante"]:
            if col in df_mostrar.columns:
                df_mostrar[col] = pd.to_numeric(df_mostrar[col], errors="coerce").fillna(0)
                df_mostrar[col] = df_mostrar.apply(
                    lambda r, col=col: formato_excel(r[col], r["unidad"]),
                    axis=1
                )
    else:
        for col in ["cantidad", "cantidad_necesaria", "cantidad_tomada", "ctd_faltante"]:
            if col in df_mostrar.columns:
                df_mostrar[col] = pd.to_numeric(df_mostrar[col], errors="coerce").fillna(0)
                df_mostrar[col] = df_mostrar[col].map("{:,.0f}".format)

    return df_mostrar


def exportar_excel(df, titulo, nombre_archivo, bodega):
    buffer = io.BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="xlsxwriter",
        engine_kwargs={"options": {"nan_inf_to_errors": True}}
    ) as writer:

        df_excel = df.copy()

        for col in ["cantidad", "cantidad_necesaria", "cantidad_tomada", "ctd_faltante"]:
            if col in df_excel.columns:
                df_excel[col] = pd.to_numeric(df_excel[col], errors="coerce").fillna(0)

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

        formato_numero_entero = workbook.add_format({
            "border": 1,
            "align": "center",
            "num_format": '#,##0'
        })

        formato_numero_decimal = workbook.add_format({
            "border": 1,
            "align": "center",
            "num_format": '#,##0.000'
        })

        columnas = len(df_excel.columns)

        worksheet.merge_range(0, 0, 0, columnas - 1, "SERVILEV", formato_empresa)
        worksheet.merge_range(2, 0, 2, columnas - 1, titulo, formato_titulo)

        fecha_actual = datetime.now().strftime("%d-%m-%Y %H:%M")
        worksheet.write(4, 0, f"Fecha: {fecha_actual}")
        worksheet.write(5, 0, f"Bodega: {bodega}")

        for col_num, value in enumerate(df_excel.columns.values):
            worksheet.write(7, col_num, value, encabezado)

        columnas_numericas = {"cantidad", "cantidad_necesaria", "cantidad_tomada", "ctd_faltante"}
        col_unidad = df_excel.columns.get_loc("unidad") if "unidad" in df_excel.columns else None

        for row in range(len(df_excel)):
            for col in range(columnas):
                nombre_col = df_excel.columns[col]
                valor = df_excel.iloc[row, col]

                if nombre_col in columnas_numericas:
                    if col_unidad is not None:
                        unidad = str(df_excel.iloc[row, col_unidad]).strip().upper()
                        if unidad in ["KG", "M"]:
                            worksheet.write(row + 8, col, valor, formato_numero_decimal)
                        else:
                            worksheet.write(row + 8, col, valor, formato_numero_entero)
                    else:
                        worksheet.write(row + 8, col, valor, formato_numero_entero)
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
        nombre_archivo,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


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

    inventario = convertir_numerico(inventario, ["cantidad_necesaria", "cantidad_tomada", "ctd_faltante"])
    ingresos = convertir_numerico(ingresos, ["cantidad"])
    salidas = convertir_numerico(salidas, ["cantidad"])

    tab1, tab2, tab3 = st.tabs(["Resumen", "Control de stock", "Exportación"])

    # =========================================================
    # TAB 1 - RESUMEN
    # =========================================================
    with tab1:
        st.subheader("Resumen general")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_inicio = st.date_input("Desde", value=None, key="resumen_fecha_inicio")
        with col_f2:
            fecha_fin = st.date_input("Hasta", value=None, key="resumen_fecha_fin")

        ingresos_res = aplicar_filtros_basicos(ingresos, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
        salidas_res = aplicar_filtros_basicos(salidas, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

        total_ingresos = ingresos_res["cantidad"].sum() if not ingresos_res.empty else 0
        total_salidas = salidas_res["cantidad"].sum() if not salidas_res.empty else 0
        stock_total = total_ingresos - total_salidas

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📥 Ingresos", f"{total_ingresos:,.3f}")
        col2.metric("📤 Salidas", f"{total_salidas:,.3f}")
        col3.metric("📦 Stock neto", f"{stock_total:,.3f}")
        col4.metric("📄 Reservas", int(inventario["reserva"].nunique()) if not inventario.empty else 0)

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Top Ingresos")
            if not ingresos_res.empty:
                top_ing = ingresos_res.groupby("material")["cantidad"].sum().sort_values(ascending=False).head(5)
                fig, ax = plt.subplots(figsize=(6, 3))
                ax.bar(top_ing.index.astype(str), top_ing.values)
                ax.set_title("Top ingresos")
                plt.xticks(rotation=45, ha="right")
                st.pyplot(fig)
            else:
                st.info("No hay ingresos en el rango seleccionado")

        with col2:
            st.subheader("Top Salidas")
            if not salidas_res.empty:
                top_sal = salidas_res.groupby("material")["cantidad"].sum().sort_values(ascending=False).head(5)
                fig, ax = plt.subplots(figsize=(6, 3))
                ax.bar(top_sal.index.astype(str), top_sal.values)
                ax.set_title("Top salidas")
                plt.xticks(rotation=45, ha="right")
                st.pyplot(fig)
            else:
                st.info("No hay salidas en el rango seleccionado")

    # =========================================================
    # TAB 2 - CONTROL DE STOCK
    # =========================================================
    with tab2:
        st.subheader("Control total de inventario")

        stock = calcular_stock(conn, bodega)

        if stock.empty:
            st.warning("No hay movimientos registrados")
        else:
            buscar_material = st.text_input("Buscar material", key="buscar_stock")

            if buscar_material:
                stock = stock[
                    stock["material"].astype(str).str.contains(buscar_material, case=False, na=False) |
                    stock["texto_material"].astype(str).str.contains(buscar_material, case=False, na=False)
                ]

            if stock.empty:
                st.info("No hay resultados")
            else:
                stock = stock.sort_values("stock")

                def estado(val):
                    if val <= 5:
                        return "🔴 Crítico"
                    elif val <= 10:
                        return "🟠 Bajo"
                    else:
                        return "🟢 Normal"

                stock["estado"] = stock["stock"].apply(estado)

                criticos = stock[stock["stock"] <= 5]
                bajos = stock[(stock["stock"] > 5) & (stock["stock"] <= 10)]

                c1, c2, c3 = st.columns(3)
                c1.metric("Materiales controlados", len(stock))
                c2.metric("Críticos", len(criticos))
                c3.metric("Bajos", len(bajos))

                stock_mostrar = stock.copy()
                stock_mostrar["total_ingreso"] = stock_mostrar.apply(
                    lambda r: formato_excel(r["total_ingreso"], r["unidad"]),
                    axis=1
                )
                stock_mostrar["total_salida"] = stock_mostrar.apply(
                    lambda r: formato_excel(r["total_salida"], r["unidad"]),
                    axis=1
                )
                stock_mostrar["stock"] = stock_mostrar.apply(
                    lambda r: formato_excel(r["stock"], r["unidad"]),
                    axis=1
                )

                stock_mostrar = stock_mostrar.rename(columns={
                    "material": "Material",
                    "texto_material": "Texto material",
                    "unidad": "Unidad",
                    "total_ingreso": "Total ingreso",
                    "total_salida": "Total salida",
                    "stock": "Stock",
                    "estado": "Estado"
                })

                st.dataframe(
                    stock_mostrar[
                        ["Material", "Texto material", "Unidad", "Total ingreso", "Total salida", "Stock", "Estado"]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

                if not criticos.empty:
                    st.error(f"⚠️ {len(criticos)} materiales en estado crítico")

                if not bajos.empty:
                    st.warning(f"⚠️ {len(bajos)} materiales con stock bajo")

                st.divider()

                st.subheader("Materiales más críticos")

                top_criticos = stock.sort_values("stock").head(5)

                fig, ax = plt.subplots(figsize=(6, 3))
                ax.bar(top_criticos["material"].astype(str), top_criticos["stock"])
                ax.set_title("Top materiales críticos")
                ax.set_ylabel("Stock")
                plt.xticks(rotation=45, ha="right")
                st.pyplot(fig)

    # =========================================================
    # TAB 3 - EXPORTACION
    # =========================================================
    with tab3:
        st.subheader("Generar reporte")

        colf1, colf2 = st.columns(2)
        with colf1:
            buscar = st.text_input("Buscar material / reserva / proyecto", key="buscar_export")
        with colf2:
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

        fecha_inicio_exp = None
        fecha_fin_exp = None

        if tipo_reporte in ["Ingresos", "Entradas (Detallado)", "Salidas", "Salidas por proyecto"]:
            colx1, colx2 = st.columns(2)
            with colx1:
                fecha_inicio_exp = st.date_input("Desde", value=None, key="exp_desde")
            with colx2:
                fecha_fin_exp = st.date_input("Hasta", value=None, key="exp_hasta")

        if tipo_reporte == "Inventario completo":
            df = inventario.copy()
            df = aplicar_filtros_basicos(df, buscar=buscar)
            nombre = f"reporte_inventario_{bodega}.xlsx"
            titulo = "REPORTE DE INVENTARIO"

        elif tipo_reporte == "Ingresos":
            df = ingresos.copy()
            df = aplicar_filtros_basicos(df, buscar=buscar, fecha_inicio=fecha_inicio_exp, fecha_fin=fecha_fin_exp)
            nombre = f"reporte_ingresos_{bodega}.xlsx"
            titulo = "REPORTE DE INGRESOS"

        elif tipo_reporte == "Entradas (Detallado)":
            df = ingresos.copy()
            df = aplicar_filtros_basicos(df, buscar=buscar, fecha_inicio=fecha_inicio_exp, fecha_fin=fecha_fin_exp)
            total = df["cantidad"].sum() if not df.empty and "cantidad" in df.columns else 0
            st.metric("Total ingresado", f"{total:,.3f}")
            nombre = f"reporte_entradas_{bodega}.xlsx"
            titulo = "REPORTE DE ENTRADAS"

        elif tipo_reporte == "Salidas":
            df = salidas.copy()
            df = aplicar_filtros_basicos(df, buscar=buscar, fecha_inicio=fecha_inicio_exp, fecha_fin=fecha_fin_exp)
            nombre = f"reporte_salidas_{bodega}.xlsx"
            titulo = "REPORTE DE SALIDAS"

        else:
            if salidas.empty or "proyecto" not in salidas.columns:
                st.info("No hay datos")
                conn.close()
                return

            proyectos = sorted(salidas["proyecto"].dropna().astype(str).unique().tolist())

            if not proyectos:
                st.info("No hay datos")
                conn.close()
                return

            proyecto = st.selectbox("Proyecto", proyectos)

            df = salidas.copy()
            df = df[df["proyecto"].astype(str) == proyecto]
            df = aplicar_filtros_basicos(df, buscar=buscar, fecha_inicio=fecha_inicio_exp, fecha_fin=fecha_fin_exp)

            nombre = f"reporte_{proyecto}_{bodega}.xlsx"
            titulo = f"SALIDAS {proyecto}"

        if df.empty:
            st.info("No hay datos para el reporte seleccionado")
        else:
            df = df.replace([float("inf"), float("-inf")], 0)
            df = df.fillna("")

            df_mostrar = preparar_vista_formateada(df)

            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

            exportar_excel(df, titulo, nombre, bodega)

    conn.close()