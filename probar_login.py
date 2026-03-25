from database import conectar
from werkzeug.security import check_password_hash

usuario = input("Usuario: ").strip()
contrasena = input("Contraseña: ").strip()

conn = conectar()
c = conn.cursor()

c.execute(
    "SELECT usuario, rol, contrasena FROM usuarios WHERE usuario=%s",
    (usuario,)
)

resultado = c.fetchone()

if resultado:
    usuario_db, rol_db, hash_db = resultado

    print("Usuario encontrado ✅")
    print("Usuario BD:", usuario_db)
    print("Rol BD:", rol_db)
    print("Hash guardado:", hash_db)

    if check_password_hash(hash_db, contrasena):
        print("Contraseña correcta ✅")
    else:
        print("Contraseña incorrecta ❌")
else:
    print("Usuario no encontrado ❌")

conn.close()