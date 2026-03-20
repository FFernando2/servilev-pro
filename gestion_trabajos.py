import streamlit as st
import pandas as pd
from database import conectar


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


def gestion_trabajos(bodega):

    st.subheader(f"Gestión de Trabajos - Bodega {bodega}")

    crear_tabla_trabajos()

    conn = conectar()

    # -------------------------
    # CREAR TRABAJO
    # -------------------------
    st.markdown("### Crear nuevo trabajo")

    col1, col2 = st.columns(2)

    with col1:
        proyecto = st.text_input("Proyecto")

    with col2:
        reserva = st.text_input("Número de reserva")

    if st.button("Crear trabajo", use_container_width=True):

        proyecto = str(proyecto).strip()
        reserva = str(reserva).strip()

        if proyecto == "" or reserva == "":
            st.warning("Completar campos")
        else:
            try:
                c = conn.cursor()

                c.execute("""
                    SELECT id
                    FROM trabajos
                    WHERE proyecto=%s AND reserva=%s AND bodega=%s
                """, (proyecto, reserva, bodega))

                existe = c.fetchone()

                if existe:
                    st.warning("Ese trabajo ya existe en esta bodega")
                else:
                    c.execute("""
                        INSERT INTO trabajos (proyecto, reserva, bodega)
                        VALUES (%s, %s, %s)
                    """, (
                        proyecto,
                        reserva,
                        bodega
                    ))

                    conn.commit()
                    st.success("Trabajo creado correctamente")
                    st.rerun()

            except Exception as e:
                conn.rollback()
                st.error(f"Error al crear trabajo: {e}")

    st.divider()

    # -------------------------
    # LISTA DE TRABAJOS
    # -------------------------
    st.markdown("### Trabajos activos")

    df = pd.read_sql_query("""
        SELECT
            t.id,
            t.proyecto,
            t.reserva,
            COALESCE(COUNT(i.id), 0) AS materiales,
            COALESCE(SUM(CASE WHEN COALESCE(i.ctd_faltante, 0) > 0 THEN 1 ELSE 0 END), 0) AS con_faltante
        FROM trabajos t
        LEFT JOIN inventario i
            ON t.proyecto = i.proyecto
           AND t.reserva = i.reserva
           AND t.bodega = i.bodega
        WHERE t.bodega=%s
        GROUP BY t.id, t.proyecto, t.reserva
        ORDER BY t.proyecto, t.reserva
    """, conn, params=(bodega,))

    if df.empty:
        st.info("No hay trabajos registrados")
        conn.close()
        return

    df_mostrar = df.rename(columns={
        "proyecto": "Proyecto",
        "reserva": "Reserva",
        "materiales": "Materiales cargados",
        "con_faltante": "Con faltante"
    })

    st.dataframe(
        df_mostrar[["Proyecto", "Reserva", "Materiales cargados", "Con faltante"]],
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # -------------------------
    # ELIMINAR TRABAJO
    # -------------------------
    st.markdown("### Eliminar trabajo")

    opciones = df.apply(
        lambda x: f"{x['proyecto']} | {x['reserva']}",
        axis=1
    ).tolist()

    trabajo_sel = st.selectbox("Seleccionar trabajo", opciones)

    if "confirmar_eliminar_trabajo" not in st.session_state:
        st.session_state.confirmar_eliminar_trabajo = False

    if not st.session_state.confirmar_eliminar_trabajo:

        if st.button("🗑️ Eliminar trabajo", use_container_width=True):
            st.session_state.confirmar_eliminar_trabajo = True
            st.rerun()

    else:
        st.warning("⚠️ Esto eliminará el trabajo seleccionado. Si tiene materiales en inventario, también se eliminarán.")

        c1, c2 = st.columns(2)

        with c1:
            if st.button("✅ Confirmar eliminación", use_container_width=True):

                try:
                    proyecto_sel = trabajo_sel.split(" | ")[0].strip()
                    reserva_sel = trabajo_sel.split(" | ")[1].strip()

                    c = conn.cursor()

                    # eliminar inventario asociado
                    c.execute("""
                        DELETE FROM inventario
                        WHERE proyecto=%s AND reserva=%s AND bodega=%s
                    """, (proyecto_sel, reserva_sel, bodega))

                    # eliminar trabajo
                    c.execute("""
                        DELETE FROM trabajos
                        WHERE proyecto=%s AND reserva=%s AND bodega=%s
                    """, (proyecto_sel, reserva_sel, bodega))

                    conn.commit()

                    st.session_state.confirmar_eliminar_trabajo = False
                    st.success("Trabajo eliminado correctamente")
                    st.rerun()

                except Exception as e:
                    conn.rollback()
                    st.session_state.confirmar_eliminar_trabajo = False
                    st.error(f"Error al eliminar trabajo: {e}")

        with c2:
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state.confirmar_eliminar_trabajo = False
                st.rerun()

    conn.close()