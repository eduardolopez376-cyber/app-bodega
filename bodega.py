import sqlite3
from datetime import datetime
import pandas as pd

def conectar_bd():
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventario (
            codigo TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            stock_minimo INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consumos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            operario TEXT NOT NULL,
            codigo_material TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            FOREIGN KEY (codigo_material) REFERENCES inventario (codigo)
        )
    ''')
    conn.commit()
    conn.close()

def agregar_o_sumar_material(codigo, nombre, cantidad_nueva, stock_minimo=5):
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT cantidad FROM inventario WHERE codigo = ?", (codigo,))
    resultado = cursor.fetchone()
    if resultado:
        nueva_cantidad = resultado[0] + cantidad_nueva
        cursor.execute("UPDATE inventario SET cantidad = ? WHERE codigo = ?", (nueva_cantidad, codigo))
    else:
        cursor.execute("INSERT INTO inventario VALUES (?, ?, ?, ?)", (codigo, nombre, cantidad_nueva, stock_minimo))
    conn.commit()
    conn.close()

def registrar_entrega_operario(codigo, cantidad_entregada, operario):
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, cantidad, stock_minimo FROM inventario WHERE codigo = ?", (codigo,))
    item = cursor.fetchone()
    if not item or item[1] < cantidad_entregada:
        conn.close()
        return False
    nuevo_stock = item[1] - cantidad_entregada
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE inventario SET cantidad = ? WHERE codigo = ?", (nuevo_stock, codigo))
    cursor.execute("INSERT INTO consumos (fecha, operario, codigo_material, cantidad) VALUES (?, ?, ?, ?)",
                   (fecha_actual, operario, codigo, cantidad_entregada))
    conn.commit()
    conn.close()
    return True

def eliminar_material(codigo):
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventario WHERE codigo = ?", (codigo,))
    conn.commit()
    conn.close()

def obtener_inventario():
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, nombre, cantidad, stock_minimo FROM inventario")
    items = cursor.fetchall()
    conn.close()
    return items