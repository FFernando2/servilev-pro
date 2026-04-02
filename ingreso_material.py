import streamlit as st
import pandas as pd
from database import conectar
from datetime import date


# --------------------------------------------------
# CREAR TABLA TRABAJOS
# --------------------------------------------------
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


# --------------------------------------------------
# FORMATO EXCEL
# --------------------------------------------------
def formato_excel(valor, unidad):
    try:
        unidad = str(unidad).strip().upper()

        if unidad in ["KG", "M"]:
            return f"{float(valor):.3f}".replace(".", ",")

        return str(int(float(valor)))
    except:
        return "0"


# --------------------------------------------------
# LIMPIAR TEXTO
# --------------------------------------------------
def limpiar_texto(valor):
    if valor is None:
        return ""
    texto = str(valor).strip()
    if texto.lower() in ["nan", "none"]:
        return ""
    return texto


# --------------------------------------------------
# INGRESO MATERIAL
# --------------------------------------------------
def ingreso_material(bodega):

    st.subheader(f"Ingreso de Material - Bodega {bodega}")

    crear_tabla_trabajos()
    conn = conectar()

    try:
        # --------------------------------------------------
        # TIPO DE INGRESO
        # --------------------------------------------------
        opcion = st.radio(
            "Tipo de ingreso",
            ["Crear nuevo trabajo", "Agregar a trabajo existente"],
            horizontal=True,
            key="tipo_ingreso"
        )

        proyecto = ""
        reserva = ""

        if opcion == "Crear nuevo trabajo":

            col1, col2 = st.columns(2)

            with col1:
                proyecto = limpiar_texto(
                    st.text_input("Proyecto", key="nuevo_proyecto")
                )

            with col2:
                reserva = limpiar_texto(
                    st.text_input("Reserva", key="nueva_reserva")
                )

        else:
            proyectos = pd.read_sql("""
                SELECT DISTINCT proyecto
                FROM trabajos
                WHERE bodega=%s
                ORDER BY proyecto
            """, conn, params=(bodega,))

            if proyectos.empty:
                st.warning("No hay proyectos registrados en esta bodega")
                return

            proyecto = st.selectbox(
                "Proyecto",
                proyectos["proyecto"].astype(str).tolist(),
                key="select_proyecto"
            )

            reservas = pd.read_sql("""
                SELECT DISTINCT reserva
                FROM trabajos
                WHERE proyecto=%s AND bodega=%s
                ORDER BY reserva
            """, conn, params=(proyecto, bodega))

            if reservas.empty:
                st.warning("No hay reservas registradas para este proyecto")
                return

            reserva = st.selectbox(
                "Reserva",
                reservas["reserva"].astype(str).tolist(),
                key="select_reserva"
            )

            resumen = pd.read_sql("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN COALESCE(ctd_faltante,0) > 0 THEN 1 ELSE 0 END) AS faltantes
                FROM inventario
                WHERE proyecto=%s AND reserva=%s AND bodega=%s
            """, conn, params=(proyecto, reserva, bodega))

            r1, r2 = st.columns(2)
            r1.metric("Materiales", int(resumen.iloc[0]["total"] or 0))
            r2.metric("Con faltante", int(resumen.iloc[0]["faltantes"] or 0))

        st.divider()

        # --------------------------------------------------
        # CATALOGO DE MATERIALES
        # --------------------------------------------------
        catalogo = pd.read_sql("""
            SELECT DISTINCT material, texto_material, unidad
            FROM inventario
            WHERE COALESCE(material, '') <> ''
            ORDER BY material
        """, conn)

        if catalogo.empty:
            catalogo = pd.DataFrame(columns=["material", "texto_material", "unidad"])

        catalogo["material"] = catalogo["material"].astype(str).fillna("").str.strip()
        catalogo["texto_material"] = catalogo["texto_material"].astype(str).fillna("").str.strip()
        catalogo["unidad"] = catalogo["unidad"].astype(str).fillna("").str.upper().str.strip()

        catalogo["display"] = catalogo["material"] + " | " + catalogo["texto_material"]

        opciones = catalogo["display"].tolist()
        opciones.append("➕ Nuevo material")

        seleccion = st.selectbox(
            "Material",
            opciones,
            key="select_material"
        )

        material = ""
        texto_material = ""
        unidad = ""

        if seleccion == "➕ Nuevo material":

            col1, col2, col3 = st.columns(3)

            with col1:
                material = limpiar_texto(
                    st.text_input("Código", key="nuevo_codigo")
                )

            with col2:
                texto_material = limpiar_texto(
                    st.text_input("Descripción", key="nuevo_desc")
                )

            with col3:
                unidad = st.selectbox(
                    "Unidad",
                    ["UN", "KG", "M"],
                    key="nuevo_unidad"
                )

        else:
            fila = catalogo[catalogo["display"] == seleccion].iloc[0]

            material = limpiar_texto(fila["material"])
            texto_material = limpiar_texto(fila["texto_material"])
            unidad = limpiar_texto(fila["unidad"]).upper()

            col1, col2, col3 = st.columns(3)

            col1.text_input("Código", material, disabled=True, key="mat_codigo")
            col2.text_input("Descripción", texto_material, disabled=True, key="mat_desc")
            col3.text_input("Unidad", unidad, disabled=True, key="mat_unidad")

        st.divider()

        # --------------------------------------------------
        # FORMULARIO
        # --------------------------------------------------
        with st.form("form_ingreso"):

            col1, col2, col3 = st.columns(3)

            with col1:
                if unidad in ["KG", "M"]:
                    cantidad = st.number_input(
                        "Cantidad",
                        min_value=0.0,
                        step=0.001,
                        format="%.3f",
                        key="cantidad_float"
                    )
                else:
                    cantidad = st.number_input(
                        "Cantidad",
                        min_value=1,
                        step=1,
                        key="cantidad_int"
                    )

            with col2:
                fecha = st.date_input(
                    "Fecha",
                    value=date.today(),
                    key="fecha_ingreso"
                )

            with col3:
                responsable = limpiar_texto(
                    st.text_input("Responsable", key="responsable")
                )

            documento = limpiar_texto(
                st.text_input("Documento", key="documento")
            )

            st.markdown("### Resumen")

            x1, x2, x3, x4 = st.columns(4)
            x1.metric("Proyecto", proyecto or "-")
            x2.metric("Reserva", reserva or "-")
            x3.metric("Material", material or "-")
            x4.metric("Cantidad", formato_excel(cantidad, unidad or "UN"))

            submit = st.form_submit_button("Registrar ingreso", use_container_width=True)

        # --------------------------------------------------
        # GUARDAR
        # --------------------------------------------------
        if submit:

            if not proyecto:
                st.warning("Debe ingresar o seleccionar un proyecto")
                return

            if not reserva:
                st.warning("Debe ingresar o seleccionar una reserva")
                return

            if not material:
                st.warning("Debe ingresar o seleccionar un material")
                return

            if not texto_material:
                st.warning("Debe ingresar la descripción del material")
                return

            if not unidad:
                st.warning("Debe indicar la unidad")
                return

            if float(cantidad) <= 0:
                st.warning("La cantidad debe ser mayor a 0")
                return

            c = conn.cursor()

            # --------------------------------------------------
            # CREAR TRABAJO SI NO EXISTE
            # --------------------------------------------------
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

            # --------------------------------------------------
            # REGISTRAR INGRESO
            # --------------------------------------------------
            c.execute("""
                INSERT INTO ingresos
                (
                    fecha,
                    proyecto,
                    reserva,
                    material,
                    texto_material,
                    unidad,
                    cantidad,
                    documento,
                    responsable,
                    bodega
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                str(fecha),
                proyecto,
                reserva,
                material,
                texto_material,
                unidad,
                float(cantidad),
                documento,
                responsable,
                bodega
            ))

            # --------------------------------------------------
            # REGISTRAR MOVIMIENTO
            # --------------------------------------------------
            c.execute("""
                INSERT INTO movimientos
                (
                    fecha,
                    tipo,
                    proyecto,
                    reserva,
                    material,
                    texto_material,
                    unidad,
                    cantidad,
                    usuario,
                    bodega
                )
                VALUES (%s, 'INGRESO', %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                str(fecha),
                proyecto,
                reserva,
                material,
                texto_material,
                unidad,
                float(cantidad),
                responsable or "Sistema",
                bodega
            ))

            # --------------------------------------------------
            # ACTUALIZAR INVENTARIO
            # --------------------------------------------------
            c.execute("""
                SELECT id, cantidad_tomada, cantidad_necesaria
                FROM inventario
                WHERE proyecto=%s
                  AND reserva=%s
                  AND material=%s
                  AND bodega=%s
                ORDER BY id
                LIMIT 1
            """, (proyecto, reserva, material, bodega))

            fila_inv = c.fetchone()

            if fila_inv:
                inventario_id = fila_inv[0]
                cantidad_tomada_actual = float(fila_inv[1] or 0)
                cantidad_necesaria_actual = float(fila_inv[2] or 0)

                nueva_cantidad_tomada = cantidad_tomada_actual + float(cantidad)
                nuevo_faltante = max(cantidad_necesaria_actual - nueva_cantidad_tomada, 0)

                c.execute("""
                    UPDATE inventario
                    SET
                        texto_material=%s,
                        unidad=%s,
                        cantidad_tomada=%s,
                        ctd_faltante=%s
                    WHERE id=%s
                """, (
                    texto_material,
                    unidad,
                    nueva_cantidad_tomada,
                    nuevo_faltante,
                    inventario_id
                ))

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
                    0,
                    float(cantidad),
                    0,
                    bodega
                ))

            conn.commit()
            st.success("Ingreso registrado correctamente")
            st.rerun()

    except Exception as e:
        conn.rollback()
        st.error(f"Error: {e}")

    finally:
        conn.close()