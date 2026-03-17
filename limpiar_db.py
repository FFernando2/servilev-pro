from database import conectar

conn = conectar()
c = conn.cursor()

# borrar inventario
c.execute("DELETE FROM inventario")

# borrar ingresos
c.execute("DELETE FROM ingresos")

# borrar salidas
c.execute("DELETE FROM salidas")

conn.commit()
conn.close()

print("Base de datos limpia correctamente")