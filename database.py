import os
import streamlit as st
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def conectar():
    database_url = st.secrets.get("DATABASE_URL", os.getenv("DATABASE_URL"))

    if not database_url:
        raise ValueError("DATABASE_URL no está configurada")

    return psycopg2.connect(
        database_url,
        sslmode="require"
    )