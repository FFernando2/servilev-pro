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

    hoja = st.selectbox("Hoja", xls.sheet_names)

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
    # CARGAR A BD
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

                cant_nec = float(row["Cantidad necesaria"])
                cant_tom = float(row["Cantidad tomada"])

                # -----------------------
                # CREAR TRABAJO
                # -----------------------
                c.execute("""
                    SELECT id
                    FROM trabajos
                    WHERE proyecto=%s AND reserva=%s AND bodega=%s
                """, (proyecto, reserva, bodega))

                if not c.fetchone():
                    c.execute("""
                        INSERT INTO trabajos
                        (proyecto, reserva, bodega)
                        VALUES (%s, %s, %s)
                    """, (proyecto, reserva, bodega))
                    trabajos_creados += 1

                # -----------------------
                # BUSCAR MATERIAL
                # -----------------------
                c.execute("""
                    SELECT id, cantidad_necesaria, cantidad_tomada
                    FROM inventario
                    WHERE proyecto=%s
                      AND reserva=%s
                      AND material=%s
                      AND bodega=%s
                """, (proyecto, reserva, material, bodega))

                existe = c.fetchone()

                if existe:
                    id_inv = existe[0]
                    nec_actual = float(existe[1] or 0)
                    tom_actual = float(existe[2] or 0)

                    nueva_nec = max(nec_actual, cant_nec)
                    nueva_tom = tom_actual + cant_tom
                    faltante = max(nueva_nec - nueva_tom, 0)

                    c.execute("""
                        UPDATE inventario
                        SET texto_material=%s,
                            unidad=%s,
                            cantidad_necesaria=%s,
                            cantidad_tomada=%s,
                            ctd_faltante=%s
                        WHERE id=%s
                    """, (
                        texto_material,
                        unidad,
                        nueva_nec,
                        nueva_tom,
                        faltante,
                        id_inv
                    ))

                    materiales_actualizados += 1

                else:
                    faltante = max(cant_nec - cant_tom, 0)

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

                    materiales_nuevos += 1

            conn.commit()

            st.success("Excel cargado correctamente")
            st.write("Trabajos creados:", trabajos_creados)
            st.write("Materiales nuevos:", materiales_nuevos)
            st.write("Materiales actualizados:", materiales_actualizados)

            st.rerun()

        except Exception as e:
            conn.rollback()
            st.error(f"Error al cargar inventario: {e}")

        finally:
            conn.close()