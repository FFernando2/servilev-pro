from database import conectar

conn = conectar()
c = conn.cursor()

c.execute("UPDATE usuarios SET rol='admin' WHERE usuario='admin'")

conn.commit()
conn.close()

print("Rol de admin actualizado a ADMIN ✅")