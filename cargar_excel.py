import streamlit as st
import pandas as pd
from database import conectar


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
# ASEGURAR COLUMNAS NUEVAS EN INVENTARIO
# --------------------------------------------------
def asegurar_columnas_inventario():
    conn = conectar()
    c = conn.cursor()

    try:
        c.execute("ALTER TABLE inventario ADD COLUMN IF NOT EXISTS grafo TEXT")
        c.execute("ALTER TABLE inventario ADD COLUMN IF NOT EXISTS posicion TEXT")
        c.execute("ALTER TABLE inventario ADD COLUMN IF NOT EXISTS operacion TEXT")
        c.execute("ALTER TABLE inventario ADD COLUMN IF NOT EXISTS batch TEXT")
        c.execute("ALTER TABLE inventario ADD COLUMN IF NOT EXISTS price_lcurrency TEXT")
        c.execute("ALTER TABLE inventario ADD COLUMN IF NOT EXISTS storage_location TEXT")
        c.execute("ALTER TABLE inventario ADD COLUMN IF NOT EXISTS existe_pedido TEXT")
        c.execute("ALTER TABLE inventario ADD COLUMN IF NOT EXISTS movement_type TEXT")
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Error al actualizar columnas de inventario: {e}")
    finally:
        conn.close()


# --------------------------------------------------
# NORMALIZAR TEXTO
# --------------------------------------------------
def normalizar_texto(texto):
    return str(texto).strip().lower()


# --------------------------------------------------
# BUSCAR COLUMNA REAL
# --------------------------------------------------
def buscar_columna_real(df, posibles_nombres):
    columnas_reales = {normalizar_texto(col): col for col in df.columns}

    for nombre in posibles_nombres:
        nombre_norm = normalizar_texto(nombre)
        if nombre_norm in columnas_reales:
            return columnas_reales[nombre_norm]

    return None


# --------------------------------------------------
# ADAPTAR COLUMNAS DEL EXCEL
# --------------------------------------------------
def adaptar_columnas_excel(df_original):
    equivalencias = {
        "Definición proyecto": [
            "Definición proyecto",
            "Definición proye",
            "Definición pr",
            "Proyecto"
        ],
        "Grafo": [
            "Grafo"
        ],
        "Reserva": [
            "Reserva",
            "Reser"
        ],
        "Posición": [
            "Posición",
            "Posicion"
        ],
        "Operación": [
            "Operación",
            "Operacion"
        ],
        "Material": [
            "Material",
            "Mater"
        ],
        "Texto material": [
            "Texto material"
        ],
        "Batch": [
            "Batch"
        ],
        "Cantidad necesaria": [
            "Cantidad necesaria",
            "Cantidad necesa"
        ],
        "Cantidad tomada": [
            "Cantidad tomada",
            "Cantidad toma"
        ],
        "Ctd.faltante": [
            "Ctd.faltante",
            "Ctd.falta"
        ],
        "Unidad medida entrada": [
            "Unidad medida entrada",
            "Unidad medida entra"
        ],
        "Price/LCurrency": [
            "Price/LCurrency",
            "Price/LCurre"
        ],
        "Storage location": [
            "Storage location",
            "Storage locati"
        ],
        "Existe pedido": [
            "Existe pedido",
            "Existe pedi"
        ],
        "Movement type": [
            "Movement type",
            "Movement ty"
        ]
    }

    obligatorias = [
        "Definición proyecto",
        "Reserva",
        "Material",
        "Texto material",
        "Unidad medida entrada",
        "Cantidad necesaria"
    ]

    opcionales_con_default = [
        "Grafo",
        "Posición",
        "Operación",
        "Batch",
        "Cantidad tomada",
        "Ctd.faltante",
        "Price/LCurrency",
        "Storage location",
        "Existe pedido",
        "Movement type"
    ]

    df_nuevo = pd.DataFrame()
    columnas_encontradas = {}
    faltantes = []

    for columna_destino, posibles in equivalencias.items():
        columna_real = buscar_columna_real(df_original, posibles)

        if columna_real is not None:
            df_nuevo[columna_destino] = df_original[columna_real]
            columnas_encontradas[columna_destino] = columna_real
        else:
            if columna_destino in opcionales_con_default:
                df_nuevo[columna_destino] = ""
                if columna_destino in ["Cantidad tomada", "Ctd.faltante"]:
                    df_nuevo[columna_destino] = 0
            elif columna_destino in obligatorias:
                faltantes.append(columna_destino)

    return df_nuevo, columnas_encontradas, faltantes


# --------------------------------------------------
# LIMPIAR NUMEROS
# --------------------------------------------------
def limpiar_numero(valor, unidad):
    if pd.isna(valor):
        return 0

    unidad = str(unidad).strip().upper()

    if isinstance(valor, (int, float)):
        if unidad in ["KG", "M"]:
            return float(valor)
        return int(float(valor))

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


# --------------------------------------------------
# FORMATO PARA MOSTRAR
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
# LIMPIAR FILAS
# --------------------------------------------------
def limpiar_filas(df):
    df = df.copy()

    columnas_texto = [
        "Definición proyecto", "Grafo", "Reserva", "Posición", "Operación",
        "Material", "Texto material", "Batch", "Unidad medida entrada",
        "Price/LCurrency", "Storage location", "Existe pedido", "Movement type"
    ]

    for col in columnas_texto:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    df = df.dropna(how="all")

    for col in ["Definición proyecto", "Reserva", "Material"]:
        df = df[df[col].notna()]
        df = df[df[col] != ""]
        df = df[df[col].str.lower() != "nan"]

    return df


# --------------------------------------------------
# AGRUPAR MATERIALES
# --------------------------------------------------
def agrupar_materiales(df):
    return df.groupby(
        [
            "Definición proyecto",
            "Grafo",
            "Reserva",
            "Posición",
            "Operación",
            "Material",
            "Texto material",
            "Batch",
            "Unidad medida entrada",
            "Price/LCurrency",
            "Storage location",
            "Existe pedido",
            "Movement type"
        ],
        as_index=False
    ).agg({
        "Cantidad necesaria": "sum",
        "Cantidad tomada": "sum",
        "Ctd.faltante": "sum"
    })


# --------------------------------------------------
# FUNCION PRINCIPAL
# --------------------------------------------------
def cargar_excel_inventario(bodega):
    st.subheader(f"Cargar Excel Inventario - Bodega {bodega}")

    crear_tabla_trabajos()
    asegurar_columnas_inventario()

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
                    c.execute("DELETE FROM inventario WHERE bodega = %s", (bodega,))
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

    archivo = st.file_uploader("Seleccionar archivo Excel", type=["xlsx"])

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
        df_original = pd.read_excel(archivo, sheet_name=hoja)
    except Exception as e:
        st.error(f"Error leyendo hoja: {e}")
        return

    df_original.columns = [str(c).strip() for c in df_original.columns]

    st.markdown("### Columnas detectadas en el Excel")
    st.write(list(df_original.columns))

    df, columnas_encontradas, faltantes = adaptar_columnas_excel(df_original)

    if faltantes:
        st.error(f"Faltan columnas obligatorias: {faltantes}")
        return

    st.markdown("### Columnas usadas por el sistema")
    st.write(columnas_encontradas)

    st.write("Filas Excel originales:", len(df))

    df = limpiar_filas(df)

    st.write("Filas válidas:", len(df))

    if df.empty:
        st.warning("No hay filas válidas para cargar")
        return

    df["Unidad medida entrada"] = df["Unidad medida entrada"].astype(str).str.strip().str.upper()

    df["Cantidad necesaria"] = df.apply(
        lambda r: limpiar_numero(r["Cantidad necesaria"], r["Unidad medida entrada"]),
        axis=1
    )

    df["Cantidad tomada"] = df.apply(
        lambda r: limpiar_numero(r["Cantidad tomada"], r["Unidad medida entrada"]),
        axis=1
    )

    df["Ctd.faltante"] = df.apply(
        lambda r: limpiar_numero(r["Ctd.faltante"], r["Unidad medida entrada"]),
        axis=1
    )

    df["Ctd.faltante"] = df["Ctd.faltante"].apply(abs)

    df["Ctd.faltante"] = df.apply(
        lambda r: abs(float(r["Cantidad necesaria"]) - float(r["Cantidad tomada"]))
        if float(r["Ctd.faltante"]) == 0 else float(r["Ctd.faltante"]),
        axis=1
    )

    df = df.drop_duplicates()

    st.write("Filas sin duplicados exactos:", len(df))

    df = agrupar_materiales(df)

    st.write("Filas consolidadas para cargar:", len(df))

    vista = df.copy()

    vista["Cantidad necesaria"] = vista.apply(
        lambda r: formato_excel(r["Cantidad necesaria"], r["Unidad medida entrada"]),
        axis=1
    )

    vista["Cantidad tomada"] = vista.apply(
        lambda r: formato_excel(r["Cantidad tomada"], r["Unidad medida entrada"]),
        axis=1
    )

    vista["Ctd.faltante"] = vista.apply(
        lambda r: formato_excel(r["Ctd.faltante"], r["Unidad medida entrada"]),
        axis=1
    )

    st.markdown("### Vista previa consolidada")
    st.dataframe(vista, use_container_width=True, hide_index=True)

    if st.button("Cargar inventario", use_container_width=True):
        conn = conectar()
        c = conn.cursor()

        trabajos_creados = 0
        filas_insertadas = 0
        filas_omitidas = 0

        try:
            for _, row in df.iterrows():
                proyecto = str(row["Definición proyecto"]).strip()
                grafo = str(row["Grafo"]).strip()
                reserva = str(row["Reserva"]).strip()
                posicion = str(row["Posición"]).strip()
                operacion = str(row["Operación"]).strip()
                material = str(row["Material"]).strip()
                texto_material = str(row["Texto material"]).strip()
                batch = str(row["Batch"]).strip()
                unidad = str(row["Unidad medida entrada"]).strip().upper()
                price_lcurrency = str(row["Price/LCurrency"]).strip()
                storage_location = str(row["Storage location"]).strip()
                existe_pedido = str(row["Existe pedido"]).strip()
                movement_type = str(row["Movement type"]).strip()

                cant_nec = float(row["Cantidad necesaria"])
                cant_tom = float(row["Cantidad tomada"])
                faltante = float(row["Ctd.faltante"])

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

                c.execute("""
                    SELECT id
                    FROM inventario
                    WHERE proyecto = %s
                      AND COALESCE(grafo, '') = %s
                      AND reserva = %s
                      AND COALESCE(posicion, '') = %s
                      AND COALESCE(operacion, '') = %s
                      AND material = %s
                      AND texto_material = %s
                      AND COALESCE(batch, '') = %s
                      AND unidad = %s
                      AND cantidad_necesaria = %s
                      AND cantidad_tomada = %s
                      AND ctd_faltante = %s
                      AND COALESCE(price_lcurrency, '') = %s
                      AND COALESCE(storage_location, '') = %s
                      AND COALESCE(existe_pedido, '') = %s
                      AND COALESCE(movement_type, '') = %s
                      AND bodega = %s
                """, (
                    proyecto,
                    grafo,
                    reserva,
                    posicion,
                    operacion,
                    material,
                    texto_material,
                    batch,
                    unidad,
                    cant_nec,
                    cant_tom,
                    faltante,
                    price_lcurrency,
                    storage_location,
                    existe_pedido,
                    movement_type,
                    bodega
                ))

                if c.fetchone():
                    filas_omitidas += 1
                    continue

                c.execute("""
                    INSERT INTO inventario (
                        proyecto,
                        grafo,
                        reserva,
                        posicion,
                        operacion,
                        material,
                        texto_material,
                        batch,
                        unidad,
                        cantidad_necesaria,
                        cantidad_tomada,
                        ctd_faltante,
                        price_lcurrency,
                        storage_location,
                        existe_pedido,
                        movement_type,
                        bodega
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    proyecto,
                    grafo,
                    reserva,
                    posicion,
                    operacion,
                    material,
                    texto_material,
                    batch,
                    unidad,
                    cant_nec,
                    cant_tom,
                    faltante,
                    price_lcurrency,
                    storage_location,
                    existe_pedido,
                    movement_type,
                    bodega
                ))

                filas_insertadas += 1

            conn.commit()

            st.success("Excel cargado correctamente")
            st.write("Trabajos creados:", trabajos_creados)
            st.write("Filas insertadas:", filas_insertadas)
            st.write("Filas omitidas por duplicado:", filas_omitidas)

            st.rerun()

        except Exception as e:
            conn.rollback()
            st.error(f"Error al cargar inventario: {e}")

        finally:
            conn.close()