# crear_usuario.py
from database import conectar

conn = conectar()
c = conn.cursor()

print("=== CREAR USUARIO SERVILEV ===")

usuario = input("Usuario: ")
contrasena = input("Contraseña: ")
rol = input("Rol (admin / bodega / consulta): ")

try:
    c.execute("""
        INSERT INTO usuarios (usuario, contrasena, rol)
        VALUES (%s, %s, %s)
    """, (usuario, contrasena, rol))

    conn.commit()
    print("Usuario creado correctamente ✅")

except Exception as e:
    conn.rollback()
    print(f"⚠️ Error: {e}")

conn.close()