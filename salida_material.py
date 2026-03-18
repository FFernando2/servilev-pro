import streamlit as st
import pandas as pd
from database import conectar
from datetime import date


def salida_material(bodega):

    st.subheader(f"Salida de Material - Bodega {bodega}")

    conn = conectar()

    # -------------------------
    # PROYECTO ORIGEN
    # -------------------------

    proyectos = pd.read_sql_query(
        "SELECT DISTINCT proyecto FROM inventario WHERE bodega=%s ORDER BY proyecto",
        conn,
        params=(bodega,)
    )

    if proyectos.empty:
        st.warning("No existen proyectos en inventario")
        conn.close()
        return

    proyecto = st.selectbox("Proyecto origen", proyectos["proyecto"])

    reservas = pd.read_sql_query(
        "SELECT DISTINCT reserva FROM inventario WHERE proyecto=%s AND bodega=%s ORDER BY reserva",
        conn,
        params=(proyecto, bodega)
    )

    if reservas.empty:
        st.warning("No existen reservas para este proyecto")
        conn.close()
        return

    reserva = st.selectbox("Reserva origen", reservas["reserva"])

    # -------------------------
    # TIPO DE SALIDA
    # -------------------------

    tipo = st.selectbox(
        "Tipo de salida",
        ["Salida normal", "Transferencia entre proyectos"]
    )

    proyecto_destino = ""
    reserva_destino = ""
    motivo = ""

    if tipo == "Transferencia entre proyectos":

        st.markdown("### Proyecto destino")

        proyecto_destino = st.selectbox("Proyecto destino", proyectos["proyecto"])

        reservas_dest = pd.read_sql_query(
            "SELECT DISTINCT reserva FROM inventario WHERE proyecto=%s AND bodega=%s ORDER BY reserva",
            conn,
            params=(proyecto_destino, bodega)
        )

        if not reservas_dest.empty:
            reserva_destino = st.selectbox("Reserva destino", reservas_dest["reserva"])
        else:
            reserva_destino = st.text_input("Reserva destino")

        motivo = st.text_input("Motivo de transferencia")

    # -------------------------
    # BUSCADOR
    # -------------------------

    buscar = st.text_input("🔎 Buscar material")

    df = pd.read_sql_query("""
        SELECT id, material, texto_material, unidad, cantidad_tomada
        FROM inventario
        WHERE proyecto=%s AND reserva=%s AND bodega=%s AND cantidad_tomada > 0
        ORDER BY material
    """, conn, params=(proyecto, reserva, bodega))

    if df.empty:
        st.warning("No hay materiales disponibles")
        conn.close()
        return

    df["cantidad_tomada"] = pd.to_numeric(df["cantidad_tomada"], errors="coerce").fillna(0).astype(int)

    if buscar:
        df = df[
            df["material"].astype(str).str.contains(buscar, case=False, na=False) |
            df["texto_material"].astype(str).str.contains(buscar, case=False, na=False)
        ]

    if df.empty:
        st.warning("No hay materiales disponibles")
        conn.close()
        return

    st.divider()
    st.write("### Materiales disponibles")

    materiales_salida = []

    # -------------------------
    # LISTA DE MATERIALES
    # -------------------------

    for _, row in df.iterrows():

        col1, col2, col3, col4, col5 = st.columns([1, 2, 3, 2, 2])

        with col1:
            usar = st.checkbox("", key=f"use_{row['id']}")

        with col2:
            st.write(row["material"])

        with col3:
            st.write(row["texto_material"])

        with col4:
            st.write(f"Stock: {row['cantidad_tomada']:,}")

        with col5:
            cantidad = st.number_input(
                "Cantidad",
                min_value=0,
                max_value=int(row["cantidad_tomada"]),
                step=1,
                format="%d",
                key=f"cant_{row['id']}"
            )

        if usar and cantidad > 0:
            materiales_salida.append((row, int(cantidad)))

    # -------------------------
    # DATOS SALIDA
    # -------------------------

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        fecha = st.date_input("Fecha", value=date.today())

    with col2:
        responsable = st.text_input("Responsable")

    with col3:
        documento = st.text_input("Documento / OT")

    # -------------------------
    # REGISTRAR SALIDA
    # -------------------------

    if st.button("Registrar salida"):

        if len(materiales_salida) == 0:
            st.warning("No seleccionaste materiales")
            conn.close()
            return

        try:
            c = conn.cursor()

            for row, cantidad in materiales_salida:

                # VALIDACIÓN REAL DE STOCK
                c.execute("""
                    SELECT cantidad_tomada
                    FROM inventario
                    WHERE id=%s
                """, (row["id"],))

                stock_actual = c.fetchone()

                if not stock_actual:
                    st.error(f"No se encontró el material {row['material']}")
                    conn.close()
                    return

                stock_actual = int(stock_actual[0] or 0)

                if cantidad > stock_actual:
                    st.error(f"Stock insuficiente para {row['material']}")
                    conn.close()
                    return

                # -------------------------
                # REGISTRAR SALIDA
                # -------------------------

                c.execute("""
                    INSERT INTO salidas
                    (fecha, proyecto, reserva, material, texto_material,
                     unidad, cantidad, destino, responsable, documento, bodega)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(fecha),
                    proyecto,
                    reserva,
                    row["material"],
                    row["texto_material"],
                    row["unidad"],
                    cantidad,
                    proyecto_destino,
                    responsable,
                    documento,
                    bodega
                ))

                # -------------------------
                # MOVIMIENTOS
                # -------------------------

                c.execute("""
                    INSERT INTO movimientos
                    (fecha, tipo, proyecto, reserva, material,
                     texto_material, unidad, cantidad, usuario, bodega)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(fecha),
                    "SALIDA",
                    proyecto,
                    reserva,
                    row["material"],
                    row["texto_material"],
                    row["unidad"],
                    cantidad,
                    responsable,
                    bodega
                ))

                # -------------------------
                # DESCONTAR INVENTARIO
                # -------------------------

                nuevo_stock = stock_actual - cantidad

                c.execute("""
                    UPDATE inventario
                    SET cantidad_tomada=%s,
                        ctd_faltante=GREATEST(cantidad_necesaria - %s, 0)
                    WHERE id=%s
                """, (
                    nuevo_stock,
                    nuevo_stock,
                    row["id"]
                ))

                # -------------------------
                # TRANSFERENCIA
                # -------------------------

                if tipo == "Transferencia entre proyectos":

                    c.execute("""
                        INSERT INTO prestamos
                        (fecha, proyecto_origen, reserva_origen,
                         proyecto_destino, reserva_destino,
                         material, texto_material, unidad,
                         cantidad, motivo, bodega)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        str(fecha),
                        proyecto,
                        reserva,
                        proyecto_destino,
                        reserva_destino,
                        row["material"],
                        row["texto_material"],
                        row["unidad"],
                        cantidad,
                        motivo,
                        bodega
                    ))

                    c.execute("""
                        SELECT id, cantidad_tomada, cantidad_necesaria
                        FROM inventario
                        WHERE proyecto=%s AND reserva=%s AND material=%s AND bodega=%s
                    """, (
                        proyecto_destino,
                        reserva_destino,
                        row["material"],
                        bodega
                    ))

                    existe = c.fetchone()

                    if existe:
                        nuevo_destino = int(existe[1] or 0) + cantidad
                        cantidad_necesaria_dest = int(existe[2] or 0)
                        faltante_dest = max(cantidad_necesaria_dest - nuevo_destino, 0)

                        c.execute("""
                            UPDATE inventario
                            SET cantidad_tomada=%s,
                                ctd_faltante=%s
                            WHERE id=%s
                        """, (
                            nuevo_destino,
                            faltante_dest,
                            existe[0]
                        ))
                    else:
                        c.execute("""
                            INSERT INTO inventario
                            (proyecto, reserva, material, texto_material, unidad,
                             cantidad_necesaria, cantidad_tomada, ctd_faltante, bodega)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            proyecto_destino,
                            reserva_destino,
                            row["material"],
                            row["texto_material"],
                            row["unidad"],
                            0,
                            cantidad,
                            0,
                            bodega
                        ))

            conn.commit()
            st.success("Salida registrada correctamente ✅")
            conn.close()
            st.rerun()

        except Exception as e:
            conn.rollback()
            conn.close()
            st.error(f"Error: {e}")
            return

    conn.close()