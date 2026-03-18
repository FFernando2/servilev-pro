import streamlit as st
import pandas as pd
from database import conectar


def cargar_excel_inventario(bodega):

    st.subheader(f"Cargar Excel Inventario - Bodega {bodega}")

    proyecto = st.text_input("Proyecto")
    archivo = st.file_uploader("Seleccionar archivo Excel", type=["xlsx"])

    if archivo is None:
        return

    # -------------------------
    # LEER EXCEL
    # -------------------------

    try:
        xls = pd.ExcelFile(archivo)
        hojas = xls.sheet_names
    except Exception as e:
        st.error(f"Error al abrir Excel: {e}")
        return

    hoja = st.selectbox("Seleccionar hoja", hojas)

    try:
        df = pd.read_excel(archivo, sheet_name=hoja)
    except Exception as e:
        st.error(f"Error leyendo hoja: {e}")
        return

    df.columns = [str(c).strip() for c in df.columns]

    st.write("Vista previa del Excel:")
    st.dataframe(df.head(10), use_container_width=True)

    columnas_obligatorias = [
        "Reserva",
        "Material",
        "Texto material",
        "Unidad",
        "Cantidad necesaria",
        "Cantidad tomada",
        "Ctd.faltante"
    ]

    faltantes = [col for col in columnas_obligatorias if col not in df.columns]

    if faltantes:
        st.error(f"Faltan columnas en el Excel: {', '.join(faltantes)}")
        return

    # -------------------------
    # LIMPIEZA
    # -------------------------

    df["Reserva"] = df["Reserva"].astype(str).str.strip()
    df["Material"] = df["Material"].astype(str).str.strip()
    df["Texto material"] = df["Texto material"].astype(str).str.strip()
    df["Unidad"] = df["Unidad"].astype(str).str.strip()

    df = df[df["Material"] != ""]
    df = df[df["Material"].str.lower() != "nan"]

    df["Cantidad necesaria"] = pd.to_numeric(df["Cantidad necesaria"], errors="coerce").fillna(0)
    df["Cantidad tomada"] = pd.to_numeric(df["Cantidad tomada"], errors="coerce").fillna(0)
    df["Ctd.faltante"] = pd.to_numeric(df["Ctd.faltante"], errors="coerce").fillna(0)

    # -------------------------
    # RESUMEN
    # -------------------------

    total_filas = len(df)
    materiales_unicos = df["Material"].nunique()

    col1, col2 = st.columns(2)
    col1.metric("Filas Excel válidas", int(total_filas))
    col2.metric("Materiales únicos", int(materiales_unicos))

    # -------------------------
    # CONSOLIDAR REPETIDOS
    # -------------------------

    df_consolidado = df.groupby(
        ["Reserva", "Material", "Texto material", "Unidad"],
        as_index=False
    ).agg({
        "Cantidad necesaria": "sum",
        "Cantidad tomada": "sum",
        "Ctd.faltante": "sum"
    })

    df_consolidado["Cantidad necesaria"] = df_consolidado["Cantidad necesaria"].astype(int)
    df_consolidado["Cantidad tomada"] = df_consolidado["Cantidad tomada"].astype(int)
    df_consolidado["Ctd.faltante"] = df_consolidado["Ctd.faltante"].astype(int)

    st.divider()
    st.write("Vista consolidada que se cargará al sistema:")
    st.dataframe(df_consolidado, use_container_width=True)

    st.write("Registros consolidados a cargar:", len(df_consolidado))

    # -------------------------
    # GUARDAR EN BASE DE DATOS
    # -------------------------

    if st.button("Cargar al inventario"):

        if proyecto.strip() == "":
            st.warning("Debes ingresar el proyecto")
            return

        conn = conectar()
        c = conn.cursor()

        insertados = 0
        actualizados = 0

        try:
            for _, row in df_consolidado.iterrows():

                reserva = str(row["Reserva"]).strip()
                material = str(row["Material"]).strip()
                texto_material = str(row["Texto material"]).strip()
                unidad = str(row["Unidad"]).strip()

                cantidad_necesaria = int(row["Cantidad necesaria"])
                cantidad_tomada = int(row["Cantidad tomada"])
                ctd_faltante = int(row["Ctd.faltante"])

                c.execute("""
                    SELECT id
                    FROM inventario
                    WHERE proyecto=%s
                      AND reserva=%s
                      AND material=%s
                      AND bodega=%s
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
                        (
                            proyecto,
                            reserva,
                            material,
                            texto_material,
                            unidad,
                            cantidad_necesaria,
                            cantidad_tomada,
                            ctd_faltante,
                            bodega
                        )
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

            c1, c2 = st.columns(2)
            c1.metric("Insertados", int(insertados))
            c2.metric("Actualizados", int(actualizados))

        except Exception as e:
            conn.rollback()
            st.error(f"Error al cargar datos: {e}")

        finally:
            conn.close()