import streamlit as st
import pandas as pd
from database import conectar
from datetime import date


def crear_tabla_trabajos():
    conn = conectar()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS trabajos (
            id SERIAL PRIMARY KEY,
            proyecto TEXT NOT NULL,
            reserva TEXT NOT NULL,
            bodega TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def formato_excel(valor, unidad):
    try:
        unidad = str(unidad).strip().upper()

        if unidad in ["KG", "M"]:
            return f"{float(valor):.3f}".replace(".", ",")

        return str(int(float(valor)))
    except:
        return "0"


def salida_material(bodega):
    st.subheader(f"Salida de Material - Bodega {bodega}")

    crear_tabla_trabajos()
    conn = conectar()

    try:
        # -------------------------
        # PROYECTO / RESERVA ORIGEN
        # -------------------------
        proyectos = pd.read_sql_query(
            """
            SELECT DISTINCT proyecto
            FROM trabajos
            WHERE bodega=%s
            ORDER BY proyecto
            """,
            conn,
            params=(bodega,)
        )

        if proyectos.empty:
            st.warning("No existen trabajos registrados en esta bodega")
            return

        proyecto = st.selectbox("Proyecto origen", proyectos["proyecto"].tolist())

        reservas = pd.read_sql_query(
            """
            SELECT DISTINCT reserva
            FROM trabajos
            WHERE proyecto=%s AND bodega=%s
            ORDER BY reserva
            """,
            conn,
            params=(proyecto, bodega)
        )

        if reservas.empty:
            st.warning("No existen reservas para este proyecto")
            return

        reserva = st.selectbox("Reserva origen", reservas["reserva"].tolist())

        # -------------------------
        # RESUMEN TRABAJO ORIGEN
        # -------------------------
        resumen = pd.read_sql_query(
            """
            SELECT
                COUNT(*) AS materiales_cargados,
                SUM(CASE WHEN COALESCE(cantidad_tomada, 0) > 0 THEN 1 ELSE 0 END) AS materiales_con_stock,
                SUM(CASE WHEN COALESCE(ctd_faltante, 0) > 0 THEN 1 ELSE 0 END) AS materiales_con_faltante
            FROM inventario
            WHERE proyecto=%s AND reserva=%s AND bodega=%s
            """,
            conn,
            params=(proyecto, reserva, bodega)
        )

        materiales_cargados = 0
        materiales_con_stock = 0
        materiales_con_faltante = 0

        if not resumen.empty:
            materiales_cargados = int(resumen.iloc[0]["materiales_cargados"] or 0)
            materiales_con_stock = int(resumen.iloc[0]["materiales_con_stock"] or 0)
            materiales_con_faltante = int(resumen.iloc[0]["materiales_con_faltante"] or 0)

        st.markdown("### Resumen del trabajo origen")

        r1, r2, r3, r4 = st.columns(4)
        with r1:
            st.markdown(f"**Proyecto:** {proyecto}")
        with r2:
            st.markdown(f"**Reserva:** {reserva}")
        with r3:
            st.metric("Con stock", materiales_con_stock)
        with r4:
            st.metric("Con faltante", materiales_con_faltante)

        st.caption(f"Materiales cargados en total: {materiales_cargados}")

        st.divider()

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

            proyectos_dest = pd.read_sql_query(
                """
                SELECT DISTINCT proyecto
                FROM trabajos
                WHERE bodega=%s
                ORDER BY proyecto
                """,
                conn,
                params=(bodega,)
            )

            lista_proyectos_dest = proyectos_dest["proyecto"].tolist()
            lista_proyectos_dest.append("➕ Crear proyecto destino nuevo")

            proyecto_destino_sel = st.selectbox("Proyecto destino", lista_proyectos_dest)

            if proyecto_destino_sel == "➕ Crear proyecto destino nuevo":
                proyecto_destino = st.text_input("Nuevo proyecto destino")
                reserva_destino = st.text_input("Nueva reserva destino")
            else:
                proyecto_destino = proyecto_destino_sel

                reservas_dest = pd.read_sql_query(
                    """
                    SELECT DISTINCT reserva
                    FROM trabajos
                    WHERE proyecto=%s AND bodega=%s
                    ORDER BY reserva
                    """,
                    conn,
                    params=(proyecto_destino, bodega)
                )

                lista_reservas_dest = reservas_dest["reserva"].tolist() if not reservas_dest.empty else []
                lista_reservas_dest.append("➕ Crear reserva destino nueva")

                reserva_dest_sel = st.selectbox("Reserva destino", lista_reservas_dest)

                if reserva_dest_sel == "➕ Crear reserva destino nueva":
                    reserva_destino = st.text_input("Nueva reserva destino")
                else:
                    reserva_destino = reserva_dest_sel

            motivo = st.text_input("Motivo de transferencia")

        # -------------------------
        # BUSCADOR
        # -------------------------
        buscar = st.text_input("🔎 Buscar material por código o descripción")

        df = pd.read_sql_query(
            """
            SELECT id, material, texto_material, unidad, cantidad_tomada, cantidad_necesaria, ctd_faltante
            FROM inventario
            WHERE proyecto=%s
              AND reserva=%s
              AND bodega=%s
              AND COALESCE(cantidad_tomada, 0) > 0
            ORDER BY material
            """,
            conn,
            params=(proyecto, reserva, bodega)
        )

        if df.empty:
            st.warning("No hay materiales disponibles con stock")
            return

        df["material"] = df["material"].astype(str).str.strip()
        df["texto_material"] = df["texto_material"].astype(str).str.strip()
        df["unidad"] = df["unidad"].astype(str).str.strip().str.upper()
        df["cantidad_tomada"] = pd.to_numeric(df["cantidad_tomada"], errors="coerce").fillna(0)
        df["cantidad_necesaria"] = pd.to_numeric(df["cantidad_necesaria"], errors="coerce").fillna(0)
        df["ctd_faltante"] = pd.to_numeric(df["ctd_faltante"], errors="coerce").fillna(0)

        if buscar:
            texto_busqueda = buscar.strip()
            df = df[
                df["material"].str.contains(texto_busqueda, case=False, na=False) |
                df["texto_material"].str.contains(texto_busqueda, case=False, na=False)
            ]

        if df.empty:
            st.warning("No hay materiales que coincidan con la búsqueda")
            return

        st.divider()
        st.write("### Materiales disponibles")

        materiales_salida = []

        encabezado = st.columns([1, 2, 5, 2, 2])
        encabezado[0].markdown("**Sel.**")
        encabezado[1].markdown("**Código**")
        encabezado[2].markdown("**Descripción**")
        encabezado[3].markdown("**Stock**")
        encabezado[4].markdown("**Cantidad**")

        # -------------------------
        # LISTA DE MATERIALES
        # -------------------------
        for _, row in df.iterrows():
            col1, col2, col3, col4, col5 = st.columns([1, 2, 5, 2, 2])

            with col1:
                usar = st.checkbox("", key=f"use_{row['id']}")

            with col2:
                st.write(row["material"])

            with col3:
                st.write(row["texto_material"])

            with col4:
                st.write(f"{formato_excel(row['cantidad_tomada'], row['unidad'])} {row['unidad']}")

            with col5:
                if row["unidad"] in ["KG", "M"]:
                    cantidad = st.number_input(
                        "Cantidad",
                        min_value=0.0,
                        max_value=float(row["cantidad_tomada"]),
                        step=0.001,
                        format="%.3f",
                        key=f"cant_{row['id']}",
                        label_visibility="collapsed"
                    )
                else:
                    cantidad = st.number_input(
                        "Cantidad",
                        min_value=0,
                        max_value=int(row["cantidad_tomada"]),
                        step=1,
                        format="%d",
                        key=f"cant_{row['id']}",
                        label_visibility="collapsed"
                    )

            if usar and float(cantidad) > 0:
                materiales_salida.append((row, float(cantidad)))

        # -------------------------
        # DATOS SALIDA
        # -------------------------
        st.divider()

        c1, c2, c3 = st.columns(3)

        with c1:
            fecha = st.date_input("Fecha", value=date.today())

        with c2:
            responsable = st.text_input("Responsable")

        with c3:
            documento = st.text_input("Documento / OT")

        # -------------------------
        # RESUMEN DE SALIDA
        # -------------------------
        total_items = len(materiales_salida)

        st.markdown("### Resumen de salida")

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.markdown(f"**Proyecto origen:** {proyecto}")
        with s2:
            st.markdown(f"**Reserva origen:** {reserva}")
        with s3:
            st.metric("Ítems seleccionados", total_items)
        with s4:
            st.markdown(f"**Tipo:** {tipo}")

        # -------------------------
        # REGISTRAR SALIDA
        # -------------------------
        if st.button("Registrar salida", use_container_width=True):
            if len(materiales_salida) == 0:
                st.warning("No seleccionaste materiales")
                return

            if not str(responsable).strip():
                st.warning("Debe ingresar el responsable")
                return

            if tipo == "Transferencia entre proyectos":
                proyecto_destino = str(proyecto_destino).strip()
                reserva_destino = str(reserva_destino).strip()

                if not proyecto_destino or not reserva_destino:
                    st.warning("Debe completar proyecto y reserva destino")
                    return

            c = conn.cursor()

            for row, cantidad in materiales_salida:
                # VALIDAR STOCK ACTUAL
                c.execute(
                    """
                    SELECT cantidad_tomada, cantidad_necesaria
                    FROM inventario
                    WHERE id=%s
                    """,
                    (row["id"],)
                )

                stock_actual = c.fetchone()

                if not stock_actual:
                    st.error(f"No se encontró el material {row['material']}")
                    return

                stock_actual_val = float(stock_actual[0] or 0)
                cantidad_necesaria_actual = float(stock_actual[1] or 0)

                if float(cantidad) > stock_actual_val:
                    st.error(f"Stock insuficiente para el material {row['material']}")
                    return

                # -------------------------
                # INSERTAR SALIDA
                # -------------------------
                c.execute(
                    """
                    INSERT INTO salidas
                    (fecha, proyecto, reserva, material, texto_material,
                     unidad, cantidad, destino, responsable, documento, bodega)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(fecha),
                        proyecto,
                        reserva,
                        row["material"],
                        row["texto_material"],
                        row["unidad"],
                        cantidad,
                        proyecto_destino if tipo == "Transferencia entre proyectos" else "",
                        responsable,
                        documento,
                        bodega
                    )
                )

                # -------------------------
                # INSERTAR MOVIMIENTO
                # -------------------------
                c.execute(
                    """
                    INSERT INTO movimientos
                    (fecha, tipo, proyecto, reserva, material,
                     texto_material, unidad, cantidad, usuario, bodega)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
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
                    )
                )

                # -------------------------
                # ACTUALIZAR INVENTARIO ORIGEN
                # -------------------------
                nuevo_stock = stock_actual_val - float(cantidad)
                nuevo_faltante = max(cantidad_necesaria_actual - nuevo_stock, 0)

                c.execute(
                    """
                    UPDATE inventario
                    SET cantidad_tomada=%s,
                        ctd_faltante=%s
                    WHERE id=%s
                    """,
                    (
                        nuevo_stock,
                        nuevo_faltante,
                        row["id"]
                    )
                )

                # -------------------------
                # TRANSFERENCIA ENTRE PROYECTOS
                # -------------------------
                if tipo == "Transferencia entre proyectos":
                    # crear trabajo destino si no existe
                    c.execute(
                        """
                        SELECT id
                        FROM trabajos
                        WHERE proyecto=%s AND reserva=%s AND bodega=%s
                        """,
                        (proyecto_destino, reserva_destino, bodega)
                    )

                    trabajo_dest = c.fetchone()

                    if not trabajo_dest:
                        c.execute(
                            """
                            INSERT INTO trabajos (proyecto, reserva, bodega)
                            VALUES (%s, %s, %s)
                            """,
                            (proyecto_destino, reserva_destino, bodega)
                        )

                    # registrar en prestamos
                    c.execute(
                        """
                        INSERT INTO prestamos
                        (fecha, proyecto_origen, reserva_origen,
                         proyecto_destino, reserva_destino,
                         material, texto_material, unidad,
                         cantidad, motivo, bodega)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
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
                        )
                    )

                    # buscar si ya existe el material en destino
                    c.execute(
                        """
                        SELECT id, cantidad_tomada, cantidad_necesaria
                        FROM inventario
                        WHERE proyecto=%s AND reserva=%s AND material=%s AND bodega=%s
                        ORDER BY id
                        LIMIT 1
                        """,
                        (
                            proyecto_destino,
                            reserva_destino,
                            row["material"],
                            bodega
                        )
                    )

                    existe_dest = c.fetchone()

                    if existe_dest:
                        nuevo_destino = float(existe_dest[1] or 0) + float(cantidad)
                        cantidad_necesaria_dest = float(existe_dest[2] or 0)
                        faltante_dest = max(cantidad_necesaria_dest - nuevo_destino, 0)

                        c.execute(
                            """
                            UPDATE inventario
                            SET cantidad_tomada=%s,
                                ctd_faltante=%s,
                                texto_material=%s,
                                unidad=%s
                            WHERE id=%s
                            """,
                            (
                                nuevo_destino,
                                faltante_dest,
                                row["texto_material"],
                                row["unidad"],
                                existe_dest[0]
                            )
                        )
                    else:
                        c.execute(
                            """
                            INSERT INTO inventario
                            (proyecto, reserva, material, texto_material, unidad,
                             cantidad_necesaria, cantidad_tomada, ctd_faltante, bodega)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                proyecto_destino,
                                reserva_destino,
                                row["material"],
                                row["texto_material"],
                                row["unidad"],
                                0,
                                float(cantidad),
                                0,
                                bodega
                            )
                        )

            conn.commit()
            st.success("Salida registrada correctamente ✅")
            st.rerun()

    except Exception as e:
        conn.rollback()
        st.error(f"Error: {e}")

    finally:
        conn.close()