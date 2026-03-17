import pandas as pd
import streamlit as st
from database import conectar
import io

def generar_guia(reserva, bodega):

    conn = conectar()

    df = pd.read_sql("""
        SELECT
        material AS Material,
        texto_material AS Descripcion,
        unidad AS Unidad,
        cantidad AS Cantidad,
        destino AS Destino,
        responsable AS Responsable
        FROM salidas
        WHERE reserva=? AND bodega=?
    """, conn, params=(reserva, bodega))

    conn.close()

    if df.empty:
        st.warning("No hay salidas registradas para esta reserva")
        return

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:

        df.to_excel(writer, sheet_name="Guia despacho", index=False)

        workbook = writer.book
        worksheet = writer.sheets["Guia despacho"]

        titulo = workbook.add_format({
            'bold': True,
            'font_size': 18
        })

        header = workbook.add_format({
            'bold': True,
            'border':1
        })

        worksheet.write("A1","SERVILEV",titulo)
        worksheet.write("A2",f"Reserva: {reserva}")
        worksheet.write("A3",f"Bodega: {bodega}")

        for col_num, value in enumerate(df.columns.values):
            worksheet.write(4, col_num, value, header)

        worksheet.set_column('A:F',25)

    st.download_button(
        "Descargar Guía de Despacho",
        output.getvalue(),
        file_name=f"guia_despacho_{reserva}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )