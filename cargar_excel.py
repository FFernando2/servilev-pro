import streamlit as st
import pandas as pd
from database import conectar


def limpiar_numero(valor, unidad):
    if pd.isna(valor):
        return 0

    unidad = str(unidad).strip().upper()

    # Si pandas ya lo leyó como número
    if isinstance(valor, (int, float)):
        if unidad in ["KG", "M"]:
            return float(valor)
        return int(valor)

    texto = str(valor).strip()

    if texto == "" or texto.lower() == "nan":
        return 0

    texto = texto.replace(" ", "")

    # -------------------------
    # KG y M -> decimal
    # Ej:
    # 5,000 -> 5.0
    # 11,200 -> 11.2
    # 15,300 -> 15.3
    # -------------------------
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

    # -------------------------
    # UN -> entero
    # -------------------------
    try:
        return int(float(texto.replace(",", ".")))
    except:
        return 0


def formato_excel(valor, unidad):
    try:
        unidad = str(unidad).strip().upper()

        if unidad in ["KG", "M"]:
            return f"{float(valor):.3f}".replace(".", ",")

        return str(int(valor))
    except:
        return "0"


def cargar_excel_inventario(bodega):
    st.subheader(f"Cargar Excel Inventario - Bodega {bodega}")

    archivo = st.file_uploader("Seleccionar archivo Excel", type=["xlsx"])

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

    df = df[columnas_obligatorias].copy()

    df["Definición proyecto"] = df["Definición proyecto"].astype(str).str.strip()
    df["Reserva"] = df["Reserva"].astype(str).str.strip()
    df["Material"] = df["Material"].astype(str).str.strip()
    df["Texto material"] = df["Texto material"].astype(str).str.strip()
    df["Unidad"] = df["Unidad"].astype(str).str.strip().str.upper()

    df = df[df["Material"] != ""]
    df = df[df["Material"].str.lower() != "nan"]

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

    st.write("Vista previa del Excel")

    df_preview = df.copy()

    df_preview["Cantidad necesaria"] = df_preview.apply(
        lambda r: formato_excel(r["Cantidad necesaria"], r["Unidad"]),
        axis=1
    )

    df_preview["Cantidad tomada"] = df_preview.apply(
        lambda r: formato_excel(r["Cantidad tomada"], r["Unidad"]),
        axis=1
    )

    df_preview["Ctd.faltante"] = df_preview.apply(
        lambda r: formato_excel(r["Ctd.faltante"], r["Unidad"]),
        axis=1
    )

    st.dataframe(df_preview, use_container_width=True)

    total_filas = len(df)
    materiales_unicos = df["Material"].nunique()

    col1, col2 = st.columns(2)
    col1.metric("Filas válidas", total_filas)
    col2.metric("Materiales únicos", materiales_unicos)

    st.divider()
    st.write("Datos que se cargarán")

    st.dataframe(df_preview, use_container_width=True)

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