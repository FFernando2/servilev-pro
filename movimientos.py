import sqlite3
from database import conectar


def registrar_movimiento(
    tipo,
    material,
    cantidad,
    bodega,
    proyecto=None,
    usuario=None
):

    conn = conectar()
    cursor = conn.cursor()

    # obtener stock actual
    cursor.execute(
        """
        SELECT cantidad_tomada 
        FROM inventario 
        WHERE material=? AND bodega=?
        """,
        (material,bodega)
    )

    resultado = cursor.fetchone()

    if resultado:
        stock_actual = resultado[0]
    else:
        stock_actual = 0

    # -------------------------
    # INGRESO
    # -------------------------

    if tipo == "ingreso":

        nuevo_stock = stock_actual + cantidad

        cursor.execute(
        """
        UPDATE inventario
        SET cantidad_tomada=?
        WHERE material=? AND bodega=?
        """,
        (nuevo_stock,material,bodega)
        )

        cursor.execute(
        """
        INSERT INTO ingresos(material,cantidad,bodega,fecha)
        VALUES(?,?,?,datetime('now'))
        """,
        (material,cantidad,bodega)
        )

    # -------------------------
    # SALIDA
    # -------------------------

    elif tipo == "salida":

        if cantidad > stock_actual:
            conn.close()
            return "Stock insuficiente"

        nuevo_stock = stock_actual - cantidad

        cursor.execute(
        """
        UPDATE inventario
        SET cantidad_tomada=?
        WHERE material=? AND bodega=?
        """,
        (nuevo_stock,material,bodega)
        )

        cursor.execute(
        """
        INSERT INTO salidas(material,cantidad,bodega,proyecto,fecha)
        VALUES(?,?,?,?,datetime('now'))
        """,
        (material,cantidad,bodega,proyecto)
        )

    # -------------------------
    # DEVOLUCION
    # -------------------------

    elif tipo == "devolucion":

        nuevo_stock = stock_actual + cantidad

        cursor.execute(
        """
        UPDATE inventario
        SET cantidad_tomada=?
        WHERE material=? AND bodega=?
        """,
        (nuevo_stock,material,bodega)
        )

        cursor.execute(
        """
        INSERT INTO ingresos(material,cantidad,bodega,fecha)
        VALUES(?,?,?,datetime('now'))
        """,
        (material,cantidad,bodega)
        )

    conn.commit()
    conn.close()

    return "ok"