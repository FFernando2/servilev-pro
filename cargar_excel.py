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

    st.write("Vista previa")
    st.dataframe(df.head())

    columnas = [
        "Reserva",
        "Material",
        "Texto material",
        "Unidad",
        "Cantidad necesaria",
        "Cantidad tomada",
        "Ctd.faltante"
    ]

    for col in columnas:
        if col not in df.columns:
            st.error(f"Falta columna: {col}")
            return

    # -------------------------
    # RESUMEN
    # -------------------------

    total = len(df)

    df["Material"] = df["Material"].astype(str).str.strip()
    df["Reserva"] = df["Reserva"].astype(str).str.strip()

    validas = df[df["Material"] != ""]
    materiales_unicos = validas["Material"].nunique()

    col1, col2 = st.columns(2)

    col1.metric("Filas Excel", total)
    col2.metric("Materiales únicos", materiales_unicos)

    # -------------------------
    # CONSOLIDAR
    # -------------------------

    df = df.groupby(
        ["Reserva", "Material", "Texto material", "Unidad"],
        as_index=False
    ).agg({
        "Cantidad necesaria": "sum",
        "Cantidad tomada": "sum",
        "Ctd.faltante": "sum"
    })

    st.write("Después de consolidar:")
    st.dataframe(df)

    st.divider()

    # -------------------------
    # GUARDAR
    # -------------------------

    if st.button("Cargar al inventario"):

        if proyecto.strip() == "":
            st.warning("Ingrese proyecto")
            return

        conn = conectar()
        c = conn.cursor()

        insertados = 0
        actualizados = 0

        try:

            for _, row in df.iterrows():

                reserva = str(row["Reserva"]).strip()
                material = str(row["Material"]).strip()
                texto = str(row["Texto material"]).strip()
                unidad = str(row["Unidad"]).strip()

                necesaria = int(row["Cantidad necesaria"])
                tomada = int(row["Cantidad tomada"])
                faltante = int(row["Ctd.faltante"])

                # verificar si existe

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
                        texto,
                        unidad,
                        necesaria,
                        tomada,
                        faltante,
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
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        proyecto,
                        reserva,
                        material,
                        texto,
                        unidad,
                        necesaria,
                        tomada,
                        faltante,
                        bodega
                    ))

                    insertados += 1

            conn.commit()

            st.success("Excel cargado correctamente")

            st.write("Insertados:", insertados)
            st.write("Actualizados:", actualizados)

        except Exception as e:

            conn.rollback()
            st.error(e)

        finally:
            conn.close()