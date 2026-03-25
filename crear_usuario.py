# crear_usuario.py
from database import conectar
from werkzeug.security import generate_password_hash

conn = conectar()
c = conn.cursor()

print("=== CREAR USUARIO SERVILEV ===")

usuario = input("Usuario: ").strip()
contrasena = input("Contraseña: ").strip()
rol = input("Rol (admin / bodega / consulta): ").strip()

try:

    # 🔐 encriptar contraseña
    hash_pw = generate_password_hash(contrasena)

    c.execute("""
        INSERT INTO usuarios (usuario, contrasena, rol)
        VALUES (%s, %s, %s)
    """, (usuario, hash_pw, rol))

    conn.commit()

    print("Usuario creado correctamente ✅")
    print("Contraseña guardada como HASH 🔐")

except Exception as e:
    conn.rollback()
    print(f"⚠️ Error: {e}")

conn.close()