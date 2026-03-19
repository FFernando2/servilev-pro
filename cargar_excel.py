import streamlit as st
import pandas as pd
from database import conectar


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

    # eliminar solo filas totalmente vacías
    df = df.dropna(how="all")

    # eliminar solo si material vacío
    df = df[df["Material"].notna()]
    df = df[df["Material"] != ""]

    st.write("Filas válidas:", len(df))

    # -----------------------------
    # LIMPIAR NUMEROS
    # -----------------------------

    df["Cantidad necesaria"] = df.apply(
        lambda r: limpiar_numero(
            r["Cantidad necesaria"],
            r["Unidad"]
        ),
        axis=1
    )

    df["Cantidad tomada"] = df.apply(
        lambda r: limpiar_numero(
            r["Cantidad tomada"],
            r["Unidad"]
        ),
        axis=1
    )

    df["Ctd.faltante"] = df.apply(
        lambda r: limpiar_numero(
            r["Ctd.faltante"],
            r["Unidad"]
        ),
        axis=1
    )

    # -----------------------------
    # VISTA PREVIA
    # -----------------------------

    df_preview = df.copy()

    df_preview["Cantidad necesaria"] = df_preview.apply(
        lambda r: formato_excel(
            r["Cantidad necesaria"],
            r["Unidad"]
        ),
        axis=1
    )

    df_preview["Cantidad tomada"] = df_preview.apply(
        lambda r: formato_excel(
            r["Cantidad tomada"],
            r["Unidad"]
        ),
        axis=1
    )

    df_preview["Ctd.faltante"] = df_preview.apply(
        lambda r: formato_excel(
            r["Ctd.faltante"],
            r["Unidad"]
        ),
        axis=1
    )

    st.dataframe(df_preview, use_container_width=True)

    # -----------------------------
    # CARGAR A BD
    # -----------------------------

    if st.button("Cargar al inventario"):

        conn = conectar()
        c = conn.cursor()

        insertados = 0
        actualizados = 0

        try:

            for _, row in df.iterrows():

                proyecto = str(row["Definición proyecto"]).strip()
                reserva = str(row["Reserva"]).strip()
                material = str(row["Material"]).strip()
                texto = str(row["Texto material"]).strip()
                unidad = str(row["Unidad"]).strip().upper()

                if unidad in ["KG", "M"]:

                    necesaria = float(row["Cantidad necesaria"])
                    tomada = float(row["Cantidad tomada"])
                    faltante = float(row["Ctd.faltante"])

                else:

                    necesaria = int(row["Cantidad necesaria"])
                    tomada = int(row["Cantidad tomada"])
                    faltante = int(row["Ctd.faltante"])

                c.execute("""
                    SELECT id
                    FROM inventario
                    WHERE proyecto=%s
                    AND reserva=%s
                    AND material=%s
                    AND bodega=%s
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
                        SET texto_material=%s,
                            unidad=%s,
                            cantidad_necesaria=%s,
                            cantidad_tomada=%s,
                            ctd_faltante=%s
                        WHERE id=%s
                    """, (
                        texto,
                        unidad,
                        necesaria,
                        tomada,
                        faltante,
                        existe[0]
                    ))

                    actualizados += 1

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
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        proyecto,
                        reserva,
                        material,
                        texto,
                        unidad,
                        necesaria,
                        tomada,
                        faltante,
                        bodega
                    ))

                    insertados += 1

            conn.commit()

            st.success("Excel cargado correctamente")

            st.write("Insertados:", insertados)
            st.write("Actualizados:", actualizados)

        except Exception as e:

            conn.rollback()
            st.error(f"Error: {e}")

        finally:

            conn.close()