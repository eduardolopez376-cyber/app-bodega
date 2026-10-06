import sqlite3
import pandas as pd
from datetime import datetime

def conectar_bd():
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # 1. Tabla Inventario
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventario (
            codigo TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Material',
            cantidad INTEGER NOT NULL,
            stock_minimo INTEGER NOT NULL DEFAULT 5
        )
    ''')
    
    # Adaptar columnas si la BD ya existía
    cursor.execute("PRAGMA table_info(inventario)")
    cols_inv = [col[1] for col in cursor.fetchall()]
    if "tipo" not in cols_inv:
        cursor.execute("ALTER TABLE inventario ADD COLUMN tipo TEXT NOT NULL DEFAULT 'Material'")
    if "stock_minimo" not in cols_inv:
        cursor.execute("ALTER TABLE inventario ADD COLUMN stock_minimo INTEGER NOT NULL DEFAULT 5")

    # 2. Tabla Operarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        )
    ''')
    
    # 3. Tabla Consumos y Préstamos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consumos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            operario TEXT NOT NULL,
            codigo_material TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Material',
            estado TEXT NOT NULL DEFAULT 'Entregado',
            FOREIGN KEY (codigo_material) REFERENCES inventario (codigo)
        )
    ''')
    
    cursor.execute("PRAGMA table_info(consumos)")
    cols_cons = [col[1] for col in cursor.fetchall()]
    if "tipo" not in cols_cons:
        cursor.execute("ALTER TABLE consumos ADD COLUMN tipo TEXT NOT NULL DEFAULT 'Material'")
    if "estado" not in cols_cons:
        cursor.execute("ALTER TABLE consumos ADD COLUMN estado TEXT NOT NULL DEFAULT 'Entregado'")

    conn.commit()
    conn.close()

# --- OPERARIOS ---
def obtener_operarios():
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM operarios ORDER BY nombre ASC")
    filas = cursor.fetchall()
    conn.close()
    return [f[0] for f in filas]

def agregar_operario(nombre):
    if not nombre.strip():
        return False
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO operarios (nombre) VALUES (?)", (nombre.strip(),))
        conn.commit()
        exito = True
    except:
        exito = False
    conn.close()
    return exito

def eliminar_operario(nombre):
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM operarios WHERE nombre = ?", (nombre,))
    conn.commit()
    conn.close()

# --- INVENTARIO ---
def agregar_o_actualizar_item(codigo, nombre, tipo, cantidad, stock_minimo):
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT cantidad FROM inventario WHERE codigo = ?", (codigo,))
    res = cursor.fetchone()
    if res:
        nueva_cant = res[0] + cantidad
        cursor.execute(
            "UPDATE inventario SET nombre = ?, tipo = ?, cantidad = ?, stock_minimo = ? WHERE codigo = ?",
            (nombre, tipo, nueva_cant, stock_minimo, codigo)
        )
    else:
        cursor.execute(
            "INSERT INTO inventario (codigo, nombre, tipo, cantidad, stock_minimo) VALUES (?, ?, ?, ?, ?)",
            (codigo, nombre, tipo, cantidad, stock_minimo)
        )
    conn.commit()
    conn.close()

def obtener_inventario():
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, nombre, tipo, cantidad, stock_minimo FROM inventario ORDER BY nombre ASC")
    items = cursor.fetchall()
    conn.close()
    return items

def eliminar_item_inventario(codigo):
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventario WHERE codigo = ?", (codigo,))
    conn.commit()
    conn.close()

def obtener_alertas_stock():
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, nombre, tipo, cantidad, stock_minimo FROM inventario WHERE cantidad <= stock_minimo")
    alertas = cursor.fetchall()
    conn.close()
    return alertas

# --- SALIDAS Y DEVOLUCIONES ---
def registrar_entrega(codigo, cantidad, operario):
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, tipo, cantidad FROM inventario WHERE codigo = ?", (codigo,))
    item = cursor.fetchone()
    
    if not item:
        conn.close()
        return False, "El ítem especificado no existe."
    
    nom_item, tipo_item, cant_actual = item
    
    if cant_actual < cantidad:
        conn.close()
        return False, f"Stock insuficiente. Disponible: {cant_actual} unidades."
    
    nuevo_stock = cant_actual - cantidad
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    estado_inicial = "Prestado" if tipo_item == "Herramienta" else "Consumido"
    
    cursor.execute("UPDATE inventario SET cantidad = ? WHERE codigo = ?", (nuevo_stock, codigo))
    cursor.execute(
        "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (?, ?, ?, ?, ?, ?)",
        (fecha_actual, operario, codigo, cantidad, tipo_item, estado_inicial)
    )
    conn.commit()
    conn.close()
    return True, f"Entrega de {tipo_item.lower()} registrada exitosamente."

def registrar_devolucion_herramienta(id_consumo, codigo_material, cantidad):
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE inventario SET cantidad = cantidad + ? WHERE codigo = ?", (cantidad, codigo_material))
    cursor.execute("UPDATE consumos SET estado = 'Devuelto' WHERE id = ?", (id_consumo,))
    conn.commit()
    conn.close()

def obtener_herramientas_en_poder():
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, c.fecha, c.operario, c.codigo_material, i.nombre, c.cantidad
        FROM consumos c
        JOIN inventario i ON c.codigo_material = i.codigo
        WHERE c.tipo = 'Herramienta' AND c.estado = 'Prestado'
        ORDER BY c.fecha DESC
    ''')
    filas = cursor.fetchall()
    conn.close()
    return filas

def obtener_cargos_por_operario(operario_filtro=None):
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    
    query = '''
        SELECT c.operario, c.tipo, c.codigo_material, i.nombre, SUM(c.cantidad) as total_cantidad, c.estado, MAX(c.fecha) as ultima_fecha
        FROM consumos c
        JOIN inventario i ON c.codigo_material = i.codigo
        WHERE c.estado IN ('Prestado', 'Consumido')
    '''
    
    params = []
    if operario_filtro and operario_filtro != "Todos":
        query += " AND c.operario = ?"
        params.append(operario_filtro)
        
    query += '''
        GROUP BY c.operario, c.tipo, c.codigo_material, i.nombre, c.estado
        ORDER BY c.operario ASC, c.tipo DESC
    '''
    
    cursor.execute(query, params)
    filas = cursor.fetchall()
    conn.close()
    return filas

def obtener_historial_movimientos():
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, c.fecha, c.operario, c.codigo_material, i.nombre, c.cantidad, c.tipo, c.estado
        FROM consumos c
        JOIN inventario i ON c.codigo_material = i.codigo
        ORDER BY c.id DESC
    ''')
    filas = cursor.fetchall()
    conn.close()
    return filas
