from database import conectar

conn = conectar()
c = conn.cursor()

# Borra todo el inventario
c.execute("DELETE FROM inventario")

conn.commit()
conn.close()

print("Inventario eliminado correctamente")