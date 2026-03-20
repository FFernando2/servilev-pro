import streamlit as st
import pandas as pd
from database import conectar


# -----------------------------
# CREAR TABLA TRABAJOS (POSTGRES)
# -----------------------------
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


# -----------------------------
# LIMPIAR NUMEROS
# -----------------------------
def limpiar_numero(valor, unidad):
    if pd.isna(valor):
        return 0

    unidad = str(unidad).strip().upper()

    if isinstance(valor, (int, float)):
        if unidad in ["KG", "M"]:
            return float(valor)
        return int(valor)

    texto = str(valor).strip()

    if texto == "" or texto.lower() == "nan":
        return 0

    texto = texto.replace(" ", "")

    if unidad in ["KG", "M"]:
        try:
            if "," in texto and "." not in texto:
                return float(texto.replace(",", "."))

            if "." in texto and "," not in texto:
                return float(texto)

            if "," in texto and "." in texto:
                texto = texto.replace(".", "").replace(",", ".")
                return float(texto)

            return float(texto)
        except:
            return 0

    try:
        return int(float(texto.replace(",", ".")))
    except:
        return 0


# -----------------------------
# FORMATO PARA MOSTRAR
# -----------------------------
def formato_excel(valor, unidad):
    try:
        unidad = str(unidad).strip().upper()

        if unidad in ["KG", "M"]:
            return f"{float(valor):.3f}".replace(".", ",")

        return str(int(valor))
    except:
        return "0"


# -----------------------------
# FUNCION PRINCIPAL
# -----------------------------
def cargar_excel_inventario(bodega):

    st.subheader(f"Cargar Excel Inventario - Bodega {bodega}")

    crear_tabla_trabajos()

    # -----------------------------
    # BOTON BORRAR INVENTARIO
    # -----------------------------
    st.divider()
    st.subheader("Eliminar inventario")

    if "confirmar_borrar_inventario" not in st.session_state:
        st.session_state.confirmar_borrar_inventario = False

    if not st.session_state.confirmar_borrar_inventario:

        if st.button("🗑️ Borrar inventario de esta bodega", use_container_width=True):
            st.session_state.confirmar_borrar_inventario = True
            st.rerun()

    else:
        st.warning("⚠️ Esto eliminará todo el inventario de la bodega actual.")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Confirmar borrado", use_container_width=True):
                conn = conectar()
                c = conn.cursor()

                try:
                    c.execute("""
                        DELETE FROM inventario
                        WHERE bodega = %s
                    """, (bodega,))

                    conn.commit()
                    st.success("Inventario eliminado correctamente")

                except Exception as e:
                    conn.rollback()
                    st.error(f"Error al borrar inventario: {e}")

                finally:
                    conn.close()

                st.session_state.confirmar_borrar_inventario = False
                st.rerun()

        with col2:
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state.confirmar_borrar_inventario = False
                st.rerun()

    st.divider()

    # -----------------------------
    # SUBIR ARCHIVO
    # -----------------------------
    archivo = st.file_uploader(
        "Seleccionar archivo Excel",
        type=["xlsx"]
    )

    if archivo is None:
        return

    try:
        xls = pd.ExcelFile(archivo)
        hojas = xls.sheet_names
    except Exception as e:
        st.error(f"Error al abrir Excel: {e}")
        return

    hoja = st.selectbox("Hoja", hojas)

    try:
        df = pd.read_excel(archivo, sheet_name=hoja)
    except Exception as e:
        st.error(f"Error leyendo hoja: {e}")
        return

    df.columns = [str(c).strip() for c in df.columns]

    columnas = [
        "Definición proyecto",
        "Reserva",
        "Material",
        "Texto material",
        "Unidad",
        "Cantidad necesaria",
        "Cantidad tomada",
        "Ctd.faltante"
    ]

    for c in columnas:
        if c not in df.columns:
            st.error(f"Falta columna: {c}")
            return

    df = df[columnas].copy()

    st.write("Filas Excel:", len(df))

    # -----------------------------
    # LIMPIAR TEXTO
    # -----------------------------
    df["Definición proyecto"] = df["Definición proyecto"].astype(str).str.strip()
    df["Reserva"] = df["Reserva"].astype(str).str.strip()
    df["Material"] = df["Material"].astype(str).str.strip()
    df["Texto material"] = df["Texto material"].astype(str).str.strip()
    df["Unidad"] = df["Unidad"].astype(str).str.strip().str.upper()

    df = df.dropna(how="all")

    df = df[df["Definición proyecto"].notna()]
    df = df[df["Reserva"].notna()]
    df = df[df["Material"].notna()]

    df = df[df["Definición proyecto"] != ""]
    df = df[df["Reserva"] != ""]
    df = df[df["Material"] != ""]

    df = df[df["Definición proyecto"].str.lower() != "nan"]
    df = df[df["Reserva"].str.lower() != "nan"]
    df = df[df["Material"].str.lower() != "nan"]

    st.write("Filas válidas:", len(df))

    if df.empty:
        st.warning("No hay filas válidas para cargar")
        return

    # -----------------------------
    # LIMPIAR NUMEROS
    # -----------------------------
    df["Cantidad necesaria"] = df.apply(
        lambda r: limpiar_numero(r["Cantidad necesaria"], r["Unidad"]),
        axis=1
    )

    df["Cantidad tomada"] = df.apply(
        lambda r: limpiar_numero(r["Cantidad tomada"], r["Unidad"]),
        axis=1
    )

    df["Ctd.faltante"] = df.apply(
        lambda r: limpiar_numero(r["Ctd.faltante"], r["Unidad"]),
        axis=1
    )

    # mantener faltante positivo visualmente
    df["Ctd.faltante"] = df["Ctd.faltante"].apply(abs)

    # -----------------------------
    # VISTA PREVIA FORMATEADA
    # -----------------------------
    vista = df.copy()

    vista["Cantidad necesaria"] = vista.apply(
        lambda r: formato_excel(r["Cantidad necesaria"], r["Unidad"]),
        axis=1
    )

    vista["Cantidad tomada"] = vista.apply(
        lambda r: formato_excel(r["Cantidad tomada"], r["Unidad"]),
        axis=1
    )

    vista["Ctd.faltante"] = vista.apply(
        lambda r: formato_excel(r["Ctd.faltante"], r["Unidad"]),
        axis=1
    )

    st.markdown("### Vista previa")
    st.dataframe(vista, use_container_width=True, hide_index=True)

    # -----------------------------
    # CARGAR A BASE DE DATOS
    # -----------------------------
    if st.button("Cargar inventario", use_container_width=True):

        conn = conectar()
        c = conn.cursor()

        trabajos_creados = 0
        filas_insertadas = 0

        try:
            for _, row in df.iterrows():

                proyecto = str(row["Definición proyecto"]).strip()
                reserva = str(row["Reserva"]).strip()
                material = str(row["Material"]).strip()
                texto_material = str(row["Texto material"]).strip()
                unidad = str(row["Unidad"]).strip().upper()

                cant_nec = float(row["Cantidad necesaria"])
                cant_tom = float(row["Cantidad tomada"])
                faltante = float(row["Ctd.faltante"])

                # -----------------------
                # CREAR TRABAJO SI NO EXISTE
                # -----------------------
                c.execute("""
                    SELECT id
                    FROM trabajos
                    WHERE proyecto = %s AND reserva = %s AND bodega = %s
                """, (proyecto, reserva, bodega))

                if not c.fetchone():
                    c.execute("""
                        INSERT INTO trabajos (proyecto, reserva, bodega)
                        VALUES (%s, %s, %s)
                    """, (proyecto, reserva, bodega))
                    trabajos_creados += 1

                # -----------------------
                # INSERTAR FILA TAL CUAL VIENE DEL EXCEL
                # -----------------------
                c.execute("""
                    INSERT INTO inventario (
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
                    cant_nec,
                    cant_tom,
                    faltante,
                    bodega
                ))

                filas_insertadas += 1

            conn.commit()

            st.success("Excel cargado correctamente")
            st.write("Trabajos creados:", trabajos_creados)
            st.write("Filas insertadas:", filas_insertadas)

            st.rerun()

        except Exception as e:
            conn.rollback()
            st.error(f"Error al cargar inventario: {e}")

        finally:
            conn.close()