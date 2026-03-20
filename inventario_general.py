import streamlit as st
import pandas as pd
from database import conectar
import matplotlib.pyplot as plt


def formato_excel(valor, unidad):
    try:
        unidad = str(unidad).strip().upper()

        if unidad in ["KG", "M"]:
            return f"{float(valor):.3f}".replace(".", ",")

        return str(int(float(valor)))
    except:
        return "0"


def inventario_general():

    st.subheader("Inventario General")

    conn = conectar()

    try:
        df = pd.read_sql("""
            SELECT
                proyecto,
                reserva,
                material,
                texto_material,
                unidad,
                cantidad_necesaria,
                cantidad_tomada,
                ctd_faltante,
                bodega
            FROM inventario
            ORDER BY proyecto, reserva, material
        """, conn)
    except Exception as e:
        conn.close()
        st.error(f"Error al cargar inventario: {e}")
        return

    conn.close()

    if df.empty:
        st.warning("No hay datos en inventario")
        return

    # -------------------------
    # LIMPIEZA
    # -------------------------
    df["proyecto"] = df["proyecto"].astype(str).str.strip()
    df["reserva"] = df["reserva"].astype(str).str.strip()
    df["material"] = df["material"].astype(str).str.strip()
    df["texto_material"] = df["texto_material"].astype(str).str.strip()
    df["unidad"] = df["unidad"].astype(str).str.strip().str.upper()
    df["bodega"] = df["bodega"].astype(str).str.strip()

    df["cantidad_necesaria"] = pd.to_numeric(df["cantidad_necesaria"], errors="coerce").fillna(0)
    df["cantidad_tomada"] = pd.to_numeric(df["cantidad_tomada"], errors="coerce").fillna(0)
    df["ctd_faltante"] = pd.to_numeric(df["ctd_faltante"], errors="coerce").fillna(0)

    # -------------------------
    # FILTROS
    # -------------------------
    st.markdown("### Filtros")

    col1, col2, col3 = st.columns(3)

    with col1:
        buscar = st.text_input("Buscar material / descripción / reserva")

    with col2:
        lista_bodegas = ["Todas"] + sorted(df["bodega"].dropna().unique().tolist())
        bodega_sel = st.selectbox("Bodega", lista_bodegas)

    with col3:
        vista_sel = st.selectbox(
            "Vista",
            ["Detalle Excel", "Resumen consolidado"]
        )

    df_filtrado = df.copy()

    if buscar:
        df_filtrado = df_filtrado[
            df_filtrado["material"].str.contains(buscar, case=False, na=False) |
            df_filtrado["texto_material"].str.contains(buscar, case=False, na=False) |
            df_filtrado["reserva"].str.contains(buscar, case=False, na=False) |
            df_filtrado["proyecto"].str.contains(buscar, case=False, na=False)
        ]

    if bodega_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado["bodega"] == bodega_sel]

    if df_filtrado.empty:
        st.info("No hay resultados para los filtros seleccionados")
        return

    # -------------------------
    # METRICAS
    # -------------------------
    st.markdown("### Resumen rápido")

    m1, m2, m3 = st.columns(3)
    m1.metric("Filas", len(df_filtrado))
    m2.metric("Materiales únicos", df_filtrado["material"].nunique())
    m3.metric("Reservas", df_filtrado["reserva"].nunique())

    st.divider()

    # ==================================================
    # VISTA 1: DETALLE EXCEL
    # ==================================================
    if vista_sel == "Detalle Excel":

        vista = df_filtrado.copy()

        vista["cantidad_necesaria"] = vista.apply(
            lambda r: formato_excel(r["cantidad_necesaria"], r["unidad"]),
            axis=1
        )

        vista["cantidad_tomada"] = vista.apply(
            lambda r: formato_excel(r["cantidad_tomada"], r["unidad"]),
            axis=1
        )

        vista["ctd_faltante"] = vista.apply(
            lambda r: formato_excel(r["ctd_faltante"], r["unidad"]),
            axis=1
        )

        vista = vista.rename(columns={
            "proyecto": "Definición proyecto",
            "reserva": "Reserva",
            "material": "Material",
            "texto_material": "Texto material",
            "unidad": "Unidad",
            "cantidad_necesaria": "Cantidad necesaria",
            "cantidad_tomada": "Cantidad tomada",
            "ctd_faltante": "Ctd.faltante",
            "bodega": "Bodega"
        })

        vista = vista[
            [
                "Definición proyecto",
                "Reserva",
                "Material",
                "Texto material",
                "Unidad",
                "Cantidad necesaria",
                "Cantidad tomada",
                "Ctd.faltante",
                "Bodega"
            ]
        ]

        st.markdown("### Vista detalle igual al Excel")
        st.dataframe(vista, use_container_width=True, hide_index=True)

    # ==================================================
    # VISTA 2: RESUMEN CONSOLIDADO
    # ==================================================
    else:

        tabla = df_filtrado.pivot_table(
            index=["material", "texto_material", "unidad"],
            columns="bodega",
            values="cantidad_tomada",
            aggfunc="sum",
            fill_value=0
        ).reset_index()

        if "Constitución" not in tabla.columns:
            tabla["Constitución"] = 0

        if "Hualañé" not in tabla.columns:
            tabla["Hualañé"] = 0

        otras_bodegas = [
            c for c in tabla.columns
            if c not in ["material", "texto_material", "unidad", "Constitución", "Hualañé"]
        ]

        tabla["Total"] = tabla[["Constitución", "Hualañé"] + otras_bodegas].sum(axis=1)

        tabla_mostrar = tabla.copy()

        for col in [c for c in tabla_mostrar.columns if c not in ["material", "texto_material", "unidad"]]:
            tabla_mostrar[col] = tabla_mostrar.apply(
                lambda r, col=col: formato_excel(r[col], r["unidad"]),
                axis=1
            )

        tabla_mostrar = tabla_mostrar.rename(columns={
            "material": "Material",
            "texto_material": "Texto material",
            "unidad": "Unidad"
        })

        columnas_orden = ["Material", "Texto material", "Unidad"]
        for col in ["Constitución", "Hualañé"]:
            if col in tabla_mostrar.columns:
                columnas_orden.append(col)

        for col in tabla_mostrar.columns:
            if col not in columnas_orden and col != "Total":
                columnas_orden.append(col)

        columnas_orden.append("Total")
        tabla_mostrar = tabla_mostrar[columnas_orden]

        st.markdown("### Resumen consolidado por material")
        st.dataframe(tabla_mostrar, use_container_width=True, hide_index=True)

        st.markdown("### Estado de stock")

        st.caption("🔴 Stock crítico (0 - 5) | 🟠 Stock bajo (6 - 10) | 🟢 Stock normal (>10)")

        def color_total(val):
            try:
                val = float(val)
            except:
                return ""

            if val <= 5:
                return "color:red"
            elif val <= 10:
                return "color:orange"
            return "color:green"

        tabla_color = tabla.copy()
        tabla_color = tabla_color.rename(columns={
            "material": "Material",
            "texto_material": "Texto material",
            "unidad": "Unidad"
        })

        st.dataframe(
            tabla_color[["Material", "Texto material", "Unidad", "Total"]]
            .style.map(color_total, subset=["Total"]),
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    # -------------------------
    # GRAFICO
    # -------------------------
    resumen_bodega = df_filtrado.groupby("bodega", as_index=False)["cantidad_tomada"].sum()

    if not resumen_bodega.empty:
        st.markdown("### Gráfico por bodega")

        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            fig, ax = plt.subplots(figsize=(5, 3))
            ax.bar(resumen_bodega["bodega"], resumen_bodega["cantidad_tomada"])
            ax.set_title("Cantidad tomada por bodega")
            ax.set_ylabel("Total")
            st.pyplot(fig)