import streamlit as st
import pandas as pd
from database import conectar
from datetime import date


def ingreso_material(bodega):

    st.subheader(f"Ingreso de Material - Bodega {bodega}")

    conn = conectar()

    # -------------------------
    # SELECCION TRABAJO
    # -------------------------

    opcion = st.radio(
        "Tipo de ingreso",
        ["Crear nuevo trabajo", "Agregar a trabajo existente"]
    )

    if opcion == "Crear nuevo trabajo":

        col1, col2 = st.columns(2)

        with col1:
            proyecto = st.text_input("Proyecto")

        with col2:
            reserva = st.text_input("Reserva")

    else:

        proyectos = pd.read_sql_query(
            "SELECT DISTINCT proyecto FROM inventario WHERE bodega=%s",
            conn,
            params=(bodega,)
        )

        if proyectos.empty:
            st.warning("No hay proyectos registrados")
            return

        proyecto = st.selectbox("Proyecto", proyectos["proyecto"])

        reservas = pd.read_sql_query(
            "SELECT DISTINCT reserva FROM inventario WHERE proyecto=%s AND bodega=%s",
            conn,
            params=(proyecto, bodega)
        )

        reserva = st.selectbox("Reserva", reservas["reserva"])

    st.divider()

    # -------------------------
    # CATALOGO (DESDE INVENTARIO)
    # -------------------------

    catalogo = pd.read_sql_query("""
        SELECT DISTINCT material, texto_material, unidad 
        FROM inventario
        ORDER BY material
    """, conn)

    if catalogo.empty:
        catalogo = pd.DataFrame(columns=["material","texto_material","unidad"])

    catalogo["display"] = catalogo["material"].astype(str) + " | " + catalogo["texto_material"].astype(str)

    lista_materiales = catalogo["display"].tolist()
    lista_materiales.append("➕ Crear material nuevo")

    material_sel = st.selectbox("Material", lista_materiales)

    # -------------------------
    # CREAR MATERIAL NUEVO
    # -------------------------

    if material_sel == "➕ Crear material nuevo":

        st.markdown("### Crear material nuevo")

        col1, col2, col3 = st.columns(3)

        with col1:
            material = st.text_input("Código material")

        with col2:
            texto_material = st.text_input("Descripción")

        with col3:
            unidad = st.text_input("Unidad")

        if st.button("Guardar material nuevo"):

            if not material or not texto_material or not unidad:
                st.warning("Completar todos los campos")
                return

            st.success("Material listo para usarse")
            st.rerun()

        return

    else:

        fila = catalogo[catalogo["display"] == material_sel].iloc[0]

        material = fila["material"]
        texto_material = fila["texto_material"]
        unidad = fila["unidad"]

    st.divider()

    # -------------------------
    # DATOS INGRESO
    # -------------------------

    col1, col2, col3 = st.columns(3)

    with col1:
        cantidad = st.number_input("Cantidad", min_value=1)

    with col2:
        fecha = st.date_input("Fecha", value=date.today())

    with col3:
        responsable = st.text_input("Responsable")

    documento = st.text_input("Documento")

    st.divider()

    # -------------------------
    # REGISTRAR INGRESO
    # -------------------------

    if st.button("Registrar ingreso"):

        if not proyecto or not reserva:
            st.warning("Debe ingresar proyecto y reserva")
            return

        c = conn.cursor()

        # INGRESO
        c.execute("""
        INSERT INTO ingresos
        (fecha, proyecto, reserva, material, texto_material,
        unidad, cantidad, documento, responsable, bodega)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            str(fecha),
            proyecto,
            reserva,
            material,
            texto_material,
            unidad,
            cantidad,
            documento,
            responsable,
            bodega
        ))

        # KARDEX
        c.execute("""
        INSERT INTO movimientos
        (fecha, tipo, proyecto, reserva, material,
        texto_material, unidad, cantidad, usuario, bodega)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            str(fecha),
            "INGRESO",
            proyecto,
            reserva,
            material,
            texto_material,
            unidad,
            cantidad,
            responsable,
            bodega
        ))

        # INVENTARIO
        c.execute("""
        SELECT id, cantidad_tomada
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
            SET cantidad_tomada = cantidad_tomada + %s
            WHERE id=%s
            """, (
                cantidad,
                existe[0]
            ))

        else:

            c.execute("""
            INSERT INTO inventario
            (proyecto, reserva, material, texto_material, unidad,
            cantidad_necesaria, cantidad_tomada, ctd_faltante, bodega)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                proyecto,
                reserva,
                material,
                texto_material,
                unidad,
                0,
                cantidad,
                0,
                bodega
            ))

        conn.commit()

        st.success("Ingreso registrado correctamente")
        st.rerun()

    conn.close()