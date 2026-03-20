import streamlit as st
import pandas as pd
from database import conectar


# -----------------------------
# CREAR TABLA TRABAJOS
# -----------------------------
def crear_tabla_trabajos():
    conn = conectar()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS trabajos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    hoja = st.selectbox("Seleccionar hoja", hojas)

    try:
        df = pd.read_excel(archivo, sheet_name=hoja)
    except Exception as e:
        st.error(f"Error leyendo hoja: {e}")
        return

    st.write("Filas Excel:", len(df))

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

    faltantes = [c for c in columnas if c not in df.columns]

    if faltantes:
        st.error(f"Faltan columnas: {faltantes}")
        return

    df = df[columnas].copy()

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

    # -----------------------------
    # AGRUPAR DUPLICADOS DEL MISMO EXCEL
    # -----------------------------
    df = df.groupby(
        ["Definición proyecto", "Reserva", "Material", "Texto material", "Unidad"],
        as_index=False
    ).agg({
        "Cantidad necesaria": "max",
        "Cantidad tomada": "sum"
    })

    # recalcular faltante
    df["Ctd.faltante"] = df.apply(
        lambda r: max(float(r["Cantidad necesaria"]) - float(r["Cantidad tomada"]), 0),
        axis=1
    )

    # -----------------------------
    # VISTA PREVIA
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
        materiales_nuevos = 0
        materiales_actualizados = 0

        try:
            for _, row in df.iterrows():
                proyecto = str(row["Definición proyecto"]).strip()
                reserva = str(row["Reserva"]).strip()
                material = str(row["Material"]).strip()
                texto_material = str(row["Texto material"]).strip()
                unidad = str(row["Unidad"]).strip().upper()

                cantidad_necesaria_excel = float(row["Cantidad necesaria"])
                cantidad_tomada_excel = float(row["Cantidad tomada"])

                # -----------------------------
                # CREAR TRABAJO SI NO EXISTE
                # -----------------------------
                c.execute("""
                    SELECT id
                    FROM trabajos
                    WHERE proyecto = ? AND reserva = ? AND bodega = ?
                """, (proyecto, reserva, bodega))

                trabajo = c.fetchone()

                if not trabajo:
                    c.execute("""
                        INSERT INTO trabajos (proyecto, reserva, bodega)
                        VALUES (?, ?, ?)
                    """, (proyecto, reserva, bodega))
                    trabajos_creados += 1

                # -----------------------------
                # BUSCAR MATERIAL EXISTENTE
                # -----------------------------
                c.execute("""
                    SELECT id, cantidad_necesaria, cantidad_tomada
                    FROM inventario
                    WHERE proyecto = ? AND reserva = ? AND material = ? AND bodega = ?
                """, (proyecto, reserva, material, bodega))

                existe = c.fetchone()

                if existe:
                    id_inventario = existe[0]
                    cantidad_necesaria_actual = float(existe[1] or 0)
                    cantidad_tomada_actual = float(existe[2] or 0)

                    # mantener la mayor cantidad necesaria
                    nueva_cantidad_necesaria = max(cantidad_necesaria_actual, cantidad_necesaria_excel)

                    # sumar lo nuevo que llegó
                    nueva_cantidad_tomada = cantidad_tomada_actual + cantidad_tomada_excel

                    # recalcular faltante
                    nuevo_ctd_faltante = max(nueva_cantidad_necesaria - nueva_cantidad_tomada, 0)

                    c.execute("""
                        UPDATE inventario
                        SET texto_material = ?,
                            unidad = ?,
                            cantidad_necesaria = ?,
                            cantidad_tomada = ?,
                            ctd_faltante = ?
                        WHERE id = ?
                    """, (
                        texto_material,
                        unidad,
                        nueva_cantidad_necesaria,
                        nueva_cantidad_tomada,
                        nuevo_ctd_faltante,
                        id_inventario
                    ))

                    materiales_actualizados += 1

                else:
                    nuevo_ctd_faltante = max(cantidad_necesaria_excel - cantidad_tomada_excel, 0)

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
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        proyecto,
                        reserva,
                        material,
                        texto_material,
                        unidad,
                        cantidad_necesaria_excel,
                        cantidad_tomada_excel,
                        nuevo_ctd_faltante,
                        bodega
                    ))

                    materiales_nuevos += 1

            conn.commit()

            st.success("Inventario cargado correctamente")
            st.info(f"Trabajos nuevos creados: {trabajos_creados}")
            st.info(f"Materiales nuevos: {materiales_nuevos}")
            st.info(f"Materiales actualizados: {materiales_actualizados}")

            st.rerun()

        except Exception as e:
            conn.rollback()
            st.error(f"Error al cargar inventario: {e}")

        finally:
            conn.close()