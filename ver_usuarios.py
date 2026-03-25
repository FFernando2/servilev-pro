from database import conectar

def ver_usuarios():
    conn = None
    try:
        conn = conectar()
        c = conn.cursor()

        c.execute("SELECT usuario, rol FROM usuarios ORDER BY usuario")
        usuarios = c.fetchall()

        print("=== USUARIOS ===")
        for usuario, rol in usuarios:
            print(f"Usuario: {usuario} | Rol: {rol}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    ver_usuarios()