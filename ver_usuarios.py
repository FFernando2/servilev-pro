from database import conectar

conn = conectar()
c = conn.cursor()

c.execute("SELECT * FROM usuarios")
usuarios = c.fetchall()

for u in usuarios:
    print(u)

conn.close()