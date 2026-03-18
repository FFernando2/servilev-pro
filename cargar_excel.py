import streamlit as st
import pandas as pd
from database import conectar

def cargar_excel_inventario(bodega):

    st.subheader(f"Cargar Excel Inventario - Bodega {bodega}")

    proyecto = st.text_input("Proyecto")

    archivo = st.file_uploader("Seleccionar archivo Excel", type=["xlsx"])

    if archivo is None:
        return

    try:
        xls = pd.ExcelFile(archivo)
        hojas = xls.sheet_names
    except Exception as e:
        st.error(f"Error al abrir el archivo Excel: {e}")
        return

    hoja_seleccionada = st.selectbox("Seleccionar hoja del Excel", hojas)

    try:
        df = pd.read_excel(archivo, sheet_name=hoja_seleccionada)
    except Exception as e:
        st.error(f"Error al leer la hoja seleccionada: {e}")
        return

    df.columns = [str(col).strip() for col in df.columns]

    st.write("Vista previa del archivo:")
    st.dataframe(df.head(10), use_container_width=True)

    columnas_esperadas = [
        "Reserva",
        "Material",
        "Texto material",
        "Unidad",
        "Cantidad necesaria",
        "Cantidad tomada",
        "Ctd.faltante"
    ]

    faltantes = [col for col in columnas_esperadas if col not in df.columns]

    if faltantes:
        st.error(f"Faltan columnas en el Excel: {', '.join(faltantes)}")
        return

    # -------------------------
    # RESUMEN DEL EXCEL
    # -------------------------

    total_filas_excel = len(df)

    df_validacion = df.copy()
    df_validacion["Material"] = df_validacion["Material"].astype(str).str.strip()
    df_validacion["Reserva"] = df_validacion["Reserva"].astype(str).str.strip()

    filas_vacias_material = (
        (df_validacion["Material"] == "") |
        (df_validacion["Material"].str.lower() == "nan")
    ).sum()

    filas_validas = total_filas_excel - filas_vacias_material

    materiales_unicos = df_validacion.loc[
        (~df_validacion["Material"].isin(["", "nan", "NaN"])),
        "Material"
    ].nunique()

    repetidos = df_validacion.loc[
        (~df_validacion["Material"].isin(["", "nan", "NaN"]))
    ].duplicated(subset=["Reserva", "Material"], keep=False).sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Filas Excel", int(total_filas_excel))
    col2.metric("Filas válidas", int(filas_validas))
    col3.metric("Materiales únicos", int(materiales_unicos))
    col4.metric("Filas sin material", int(filas_vacias_material))

    if repetidos > 0:
        st.warning(f"Hay {int(repetidos)} filas repetidas por Reserva + Material.")

    st.divider()

    if st.button("Cargar datos al sistema"):

        if proyecto.strip() == "":
            st.warning("Debes ingresar el proyecto")
            return

        conn = conectar()
        c = conn.cursor()

        insertados = 0
        actualizados = 0
        omitidos = 0

        detalle_omitidos = []

        try:
            for i, row in df.iterrows():

                reserva = str(row.get("Reserva", "")).strip()
                material = str(row.get("Material", "")).strip()
                texto_material = str(row.get("Texto material", "")).strip()
                unidad = str(row.get("Unidad", "")).strip()

                cantidad_necesaria = row.get("Cantidad necesaria", 0)
                cantidad_tomada = row.get("Cantidad tomada", 0)
                ctd_faltante = row.get("Ctd.faltante", 0)

                if pd.isna(cantidad_necesaria):
                    cantidad_necesaria = 0
                if pd.isna(cantidad_tomada):
                    cantidad_tomada = 0
                if pd.isna(ctd_faltante):
                    ctd_faltante = 0

                try:
                    cantidad_necesaria = int(float(cantidad_necesaria))
                except:
                    cantidad_necesaria = 0

                try:
                    cantidad_tomada = int(float(cantidad_tomada))
                except:
                    cantidad_tomada = 0

                try:
                    ctd_faltante = int(float(ctd_faltante))
                except:
                    ctd_faltante = 0

                if material == "" or material.lower() == "nan":
                    omitidos += 1
                    detalle_omitidos.append({
                        "Fila Excel": i + 2,
                        "Motivo": "Material vacío"
                    })
                    continue

                c.execute("""
                    SELECT id
                    FROM inventario
                    WHERE proyecto=%s AND reserva=%s AND material=%s AND bodega=%s
                """, (
                    proyecto,
                    reserva,
                    material,
                    bodega
                ))

                existe = c.fetchone()

                if existe:
                    c.execute("""
                        UPDATE inventario
                        SET texto_material=%s,
                            unidad=%s,
                            cantidad_necesaria=%s,
                            cantidad_tomada=%s,
                            ctd_faltante=%s
                        WHERE id=%s
                    """, (
                        texto_material,
                        unidad,
                        cantidad_necesaria,
                        cantidad_tomada,
                        ctd_faltante,
                        existe[0]
                    ))
                    actualizados += 1

                else:
                    c.execute("""
                        INSERT INTO inventario
                        (proyecto, reserva, material, texto_material, unidad,
                         cantidad_necesaria, cantidad_tomada, ctd_faltante, bodega)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        proyecto,
                        reserva,
                        material,
                        texto_material,
                        unidad,
                        cantidad_necesaria,
                        cantidad_tomada,
                        ctd_faltante,
                        bodega
                    ))
                    insertados += 1

            conn.commit()

            st.success("Excel cargado correctamente ✅")

            c1, c2, c3 = st.columns(3)
            c1.metric("Insertados", int(insertados))
            c2.metric("Actualizados", int(actualizados))
            c3.metric("Omitidos", int(omitidos))

            if detalle_omitidos:
                st.write("Detalle de filas omitidas:")
                st.dataframe(pd.DataFrame(detalle_omitidos), use_container_width=True)

        except Exception as e:
            conn.rollback()
            st.error(f"Error al cargar datos: {e}")

        finally:
            conn.close()