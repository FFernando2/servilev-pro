import streamlit as st
import pandas as pd
from database import conectar

def cargar_excel_inventario(bodega):

    st.subheader("Cargar Excel SAP")

    archivo = st.file_uploader("Subir Excel", type=["xlsx"])

    if archivo:

        df = pd.read_excel(archivo, sheet_name=1)

        df.columns = df.columns.str.strip()

        df = df[[
            "Definición proyecto",
            "Reserva",
            "Material",
            "Texto material",
            "Unidad medida entrada",
            "Cantidad necesaria",
            "Cantidad tomada",
            "Ctd.faltante"
        ]]

        st.dataframe(df)

        if st.button("Guardar Excel"):

            conn = conectar()
            c = conn.cursor()

            for _, row in df.iterrows():

                c.execute("""
                INSERT INTO inventario
                (proyecto,reserva,material,texto_material,unidad,
                cantidad_necesaria,cantidad_tomada,ctd_faltante,bodega)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,(
                    row["Definición proyecto"],
                    row["Reserva"],
                    row["Material"],
                    row["Texto material"],
                    row["Unidad medida entrada"],
                    row["Cantidad necesaria"],
                    row["Cantidad tomada"],
                    row["Ctd.faltante"],
                    bodega
                ))

            conn.commit()
            conn.close()

            st.success("Excel cargado correctamente")