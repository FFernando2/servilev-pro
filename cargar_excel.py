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
        df = pd.read_excel(archivo, sheet_name=1)
    except Exception as e:
        st.error(f"Error al leer el archivo Excel: {e}")
        return

    st.write("Vista previa del archivo:")
    st.dataframe(df.head(), use_container_width=True)

    if st.button("Cargar datos al sistema"):

        conn = conectar()
        c = conn.cursor()

        try:
            for _, row in df.iterrows():

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

                if not material:
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

            conn.commit()
            st.success("Excel cargado correctamente ✅")

        except Exception as e:
            conn.rollback()
            st.error(f"Error al cargar datos: {e}")

        finally:
            conn.close()