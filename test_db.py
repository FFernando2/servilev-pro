from database import conectar

try:
    conn = conectar()
    print("✅ Conectado correctamente a Supabase")
    conn.close()
except Exception as e:
    print("❌ Error:", e)