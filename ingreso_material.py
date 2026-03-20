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


def ingreso_material(bodega):

    st.subheader(f"Ingreso de Material - Bodega {bodega}")

    crear_tabla_trabajos()

    conn = conectar()

    # -------------------------
    # SELECCION TRABAJO
    # -------------------------
    opcion = st.radio(
        "Tipo de ingreso",
        ["Crear nuevo trabajo", "Agregar a trabajo existente"]
    )

    proyecto = ""
    reserva = ""

    if opcion == "Crear nuevo trabajo":

        col1, col2 = st.columns(2)

        with col1:
            proyecto = st.text_input("Proyecto")

        with col2:
            reserva = st.text_input("Reserva")

    else:
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
            st.warning("No hay proyectos registrados en esta bodega")
            conn.close()
            return

        proyecto = st.selectbox("Proyecto", proyectos["proyecto"].tolist())

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
            st.warning("No hay reservas registradas para este proyecto")
            conn.close()
            return

        reserva = st.selectbox("Reserva", reservas["reserva"].tolist())

        # -------------------------
        # RESUMEN DEL TRABAJO
        # -------------------------
        resumen = pd.read_sql_query(
            """
            SELECT
                COUNT(*) AS materiales_cargados,
                SUM(CASE WHEN COALESCE(ctd_faltante, 0) > 0 THEN 1 ELSE 0 END) AS materiales_con_faltante
            FROM inventario
            WHERE proyecto=%s AND reserva=%s AND bodega=%s
            """,
            conn,
            params=(proyecto, reserva, bodega)
        )

        materiales_cargados = 0
        materiales_con_faltante = 0

        if not resumen.empty:
            materiales_cargados = int(resumen.iloc[0]["materiales_cargados"] or 0)
            materiales_con_faltante = int(resumen.iloc[0]["materiales_con_faltante"] or 0)

        st.markdown("### Resumen del trabajo")

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Proyecto", proyecto)
        r2.metric("Reserva", reserva)
        r3.metric("Materiales cargados", materiales_cargados)
        r4.metric("Con faltante", materiales_con_faltante)

    st.divider()

    # -------------------------
    # CATALOGO DE MATERIALES
    # -------------------------
    catalogo = pd.read_sql_query("""
        SELECT DISTINCT material, texto_material, unidad
        FROM inventario
        WHERE material IS NOT NULL
          AND material <> ''
        ORDER BY material
    """, conn)

    if catalogo.empty:
        catalogo = pd.DataFrame(columns=["material", "texto_material", "unidad"])

    catalogo["material"] = catalogo["material"].astype(str).str.strip()
    catalogo["texto_material"] = catalogo["texto_material"].astype(str).str.strip()
    catalogo["unidad"] = catalogo["unidad"].astype(str).str.strip().str.upper()

    catalogo["display"] = (
        catalogo["material"].astype(str) + " | " +
        catalogo["texto_material"].astype(str)
    )

    lista_materiales = catalogo["display"].drop_duplicates().tolist()
    lista_materiales.append("➕ Crear material nuevo")

    material_sel = st.selectbox("Material", lista_materiales)

    # -------------------------
    # CREAR MATERIAL NUEVO
    # -------------------------
    if material_sel == "➕ Crear material nuevo":

        st.markdown("### Crear material nuevo")

        c1, c2, c3 = st.columns(3)

        with c1:
            material = st.text_input("Código material")

        with c2:
            texto_material = st.text_input("Descripción")

        with c3:
            unidad = st.selectbox("Unidad", ["UN", "KG", "M"])

    else:
        fila = catalogo[catalogo["display"] == material_sel].iloc[0]

        material = str(fila["material"]).strip()
        texto_material = str(fila["texto_material"]).strip()
        unidad = str(fila["unidad"]).strip().upper()

        c1, c2, c3 = st.columns(3)

        with c1:
            st.text_input("Código material", value=material, disabled=True)

        with c2:
            st.text_input("Descripción", value=texto_material, disabled=True)

        with c3:
            st.text_input("Unidad", value=unidad, disabled=True)

    st.divider()

    # -------------------------
    # DATOS INGRESO
    # -------------------------
    c1, c2, c3 = st.columns(3)

    with c1:
        if str(unidad).strip().upper() in ["KG", "M"]:
            cantidad = st.number_input("Cantidad", min_value=0.0, step=0.001, format="%.3f")
        else:
            cantidad = st.number_input("Cantidad", min_value=1, step=1, format="%d")

    with c2:
        fecha = st.date_input("Fecha", value=date.today())

    with c3:
        responsable = st.text_input("Responsable")

    documento = st.text_input("Documento")

    # -------------------------
    # RESUMEN DEL INGRESO
    # -------------------------
    st.markdown("### Resumen del ingreso")

    x1, x2, x3, x4 = st.columns(4)
    x1.metric("Proyecto", proyecto if proyecto else "-")
    x2.metric("Reserva", reserva if reserva else "-")
    x3.metric("Material", material if material else "-")
    x4.metric("Cantidad", formato_excel(cantidad, unidad))

    st.divider()

    # -------------------------
    # REGISTRAR INGRESO
    # -------------------------
    if st.button("Registrar ingreso", use_container_width=True):

        proyecto = str(proyecto).strip()
        reserva = str(reserva).strip()
        material = str(material).strip()
        texto_material = str(texto_material).strip()
        unidad = str(unidad).strip().upper()
        responsable = str(responsable).strip()
        documento = str(documento).strip()

        if not proyecto or not reserva:
            st.warning("Debe ingresar proyecto y reserva")
            conn.close()
            return

        if not material or not texto_material or not unidad:
            st.warning("Debe completar los datos del material")
            conn.close()
            return

        if float(cantidad) <= 0:
            st.warning("La cantidad debe ser mayor a 0")
            conn.close()
            return

        try:
            c = conn.cursor()

            cantidad = float(cantidad)

            # -------------------------
            # CREAR TRABAJO SI NO EXISTE
            # -------------------------
            c.execute("""
                SELECT id
                FROM trabajos
                WHERE proyecto=%s AND reserva=%s AND bodega=%s
            """, (proyecto, reserva, bodega))

            trabajo = c.fetchone()

            if not trabajo:
                c.execute("""
                    INSERT INTO trabajos (proyecto, reserva, bodega)
                    VALUES (%s, %s, %s)
                """, (proyecto, reserva, bodega))

            # -------------------------
            # INGRESO
            # -------------------------
            c.execute("""
                INSERT INTO ingresos
                (fecha, proyecto, reserva, material, texto_material,
                 unidad, cantidad, documento, responsable, bodega)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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

            # -------------------------
            # MOVIMIENTOS / KARDEX
            # -------------------------
            c.execute("""
                INSERT INTO movimientos
                (fecha, tipo, proyecto, reserva, material,
                 texto_material, unidad, cantidad, usuario, bodega)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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

            # -------------------------
            # INVENTARIO
            # -------------------------
            c.execute("""
                SELECT id, cantidad_tomada, cantidad_necesaria
                FROM inventario
                WHERE proyecto=%s AND reserva=%s AND material=%s AND bodega=%s
                ORDER BY id
                LIMIT 1
            """, (
                proyecto,
                reserva,
                material,
                bodega
            ))

            existe = c.fetchone()

            if existe:
                id_inventario = existe[0]
                cantidad_tomada_actual = float(existe[1] or 0)
                cantidad_necesaria_actual = float(existe[2] or 0)

                nueva_cantidad_tomada = cantidad_tomada_actual + cantidad
                nuevo_faltante = max(cantidad_necesaria_actual - nueva_cantidad_tomada, 0)

                c.execute("""
                    UPDATE inventario
                    SET cantidad_tomada=%s,
                        ctd_faltante=%s,
                        texto_material=%s,
                        unidad=%s
                    WHERE id=%s
                """, (
                    nueva_cantidad_tomada,
                    nuevo_faltante,
                    texto_material,
                    unidad,
                    id_inventario
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
                    0,
                    cantidad,
                    0,
                    bodega
                ))

            conn.commit()

            st.success("Ingreso registrado correctamente")
            conn.close()
            st.rerun()

        except Exception as e:
            conn.rollback()
            conn.close()
            st.error(f"Error al registrar ingreso: {e}")
            return

    conn.close()