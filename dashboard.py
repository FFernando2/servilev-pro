import streamlit as st
import pandas as pd
from database import conectar

def dashboard():

    st.title("Panel de Control")

    conn = conectar()

    inventario = pd.read_sql("SELECT * FROM inventario", conn)
    ingresos = pd.read_sql("SELECT * FROM ingresos", conn)
    salidas = pd.read_sql("SELECT * FROM salidas", conn)

    conn.close()

    total_materiales = len(inventario)
    stock_critico = (inventario["cantidad_tomada"] <= 5).sum()

    col1,col2,col3 = st.columns(3)

    col1.metric("Materiales", total_materiales)
    col2.metric("Stock crítico", stock_critico)
    col3.metric("Movimientos", len(ingresos)+len(salidas))