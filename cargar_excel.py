import streamlit as st
import pandas as pd
from database import conectar


def formato_excel(valor):
    try:
        return f"{int(valor):,}".replace(",", ".")
    except:
        return "0"


def limpiar_numero(x):

    if pd.isna(x):
        return 0

    if isinstance(x, (int, float)):
        return int(x)

    x = str(x).strip()

    if x == "" or x.lower() == "nan":
        return 0

    # quitar separadores
    x = x.replace(".", "")
    x = x.replace(",", "")
    x = x.replace(" ", "")

    try:
        return int(float(x))
    except:
        return 0


def cargar_excel_inventario(bodega):

    st.subheader(f"Cargar Excel Inventario - Bodega {bodega}")

    archivo = st.file_uploader("Seleccionar archivo Excel", type=["xlsx"])

    if archivo is None:
        return

    # -------------------------
    # LEER EXCEL
    # -------------------------

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

    df.columns = [str(c).strip() for c in df.columns]

    columnas_obligatorias = [
        "Definición proyecto",
        "Reserva",
        "Material",
        "Texto material",
        "Unidad",
        "Cantidad necesaria",
        "Cantidad tomada",
        "Ctd.faltante"
    ]

    faltantes = [col for col in columnas_obligatorias if col not in df.columns]

    if faltantes:
        st.error(f"Faltan columnas en el Excel: {', '.join(faltantes)}")
        return

    # -------------------------
    # SOLO ESTAS COLUMNAS
    # -------------------------

    df = df[columnas_obligatorias].copy()

    # -------------------------
    # LIMPIAR TEXTO
    # -------------------------

    df["Definición proyecto"] = df["Definición proyecto"].astype(str).str.strip()
    df["Reserva"] = df["Reserva"].astype(str).str.strip()
    df["Material"] = df["Material"].astype(str).str.strip()
    df["Texto material"] = df["Texto material"].astype(str).str.strip()
    df["Unidad"] = df["Unidad"].astype(str).str.strip()

    df = df[df["Material"] != ""]
    df = df[df["Material"].str.lower() != "nan"]

    # -------------------------
    # LIMPIAR NUMEROS
    # -------------------------

    df["Cantidad necesaria"] = df["Cantidad necesaria"].apply(limpiar_numero)
    df["Cantidad tomada"] = df["Cantidad tomada"].apply(limpiar_numero)
    df["Ctd.faltante"] = df["Ctd.faltante"].apply(limpiar_numero)

    # -------------------------
    # VISTA PREVIA
    # -------------------------

    st.write("Vista previa del Excel")

    df_preview = df.copy()

    df_preview["Cantidad necesaria"] = df_preview["Cantidad necesaria"].apply(formato_excel)
    df_preview["Cantidad tomada"] = df_preview["Cantidad tomada"].apply(formato_excel)
    df_preview["Ctd.faltante"] = df_preview["Ctd.faltante"].apply(formato_excel)

    st.dataframe(df_preview, use_container_width=True)

    # -------------------------
    # CONSOLIDAR REPETIDOS
    # -------------------------

    df_consolidado = df.groupby(
        [
            "Definición proyecto",
            "Reserva",
            "Material",
            "Texto material",
            "Unidad"
        ],
        as_index=False
    ).agg({
        "Cantidad necesaria": "sum",
        "Cantidad tomada": "sum",
        "Ctd.faltante": "sum"
    })

    st.divider()

    st.write("Datos que se cargarán")

    st.dataframe(df_consolidado, use_container_width=True)

    # -------------------------
    # GUARDAR
    # -------------------------

    if st.button("Cargar al inventario"):

        conn = conectar()
        c = conn.cursor()

        insertados = 0
        actualizados = 0

        try:

            for _, row in df_consolidado.iterrows():

                proyecto = str(row["Definición proyecto"]).strip()
                reserva = str(row["Reserva"]).strip()
                material = str(row["Material"]).strip()
                texto = str(row["Texto material"]).strip()
                unidad = str(row["Unidad"]).strip()

                necesaria = int(row["Cantidad necesaria"])
                tomada = int(row["Cantidad tomada"])
                faltante = int(row["Ctd.faltante"])

                c.execute("""
                    SELECT id
                    FROM inventario
                    WHERE proyecto=?
                    AND reserva=?
                    AND material=?
                    AND bodega=?
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
                        SET texto_material=?,
                            unidad=?,
                            cantidad_necesaria=?,
                            cantidad_tomada=?,
                            ctd_faltante=?
                        WHERE id=?
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
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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

            c1, c2 = st.columns(2)
            c1.metric("Insertados", insertados)
            c2.metric("Actualizados", actualizados)

        except Exception as e:

            conn.rollback()
            st.error(f"Error: {e}")

        finally:

            conn.close()