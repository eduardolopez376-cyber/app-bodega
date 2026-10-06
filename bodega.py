import sqlite3
from datetime import datetime

def conectar_bd():
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Tabla de Inventario
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventario (
            codigo TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Material',
            cantidad INTEGER NOT NULL,
            stock_minimo INTEGER NOT NULL DEFAULT 5
        )
    ''')
    
    # Asegurar que existan las nuevas columnas si la tabla ya existia previamente
    cursor.execute("PRAGMA table_info(inventario)")
    columnas = [col[1] for col in cursor.fetchall()]
    
    if "tipo" not in columnas:
        cursor.execute("ALTER TABLE inventario ADD COLUMN tipo TEXT NOT NULL DEFAULT 'Material'")
    if "stock_minimo" not in columnas:
        cursor.execute("ALTER TABLE inventario ADD COLUMN stock_minimo INTEGER NOT NULL DEFAULT 5")
    
    # Tabla de Operarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        )
    ''')
    
    # Tabla de Consumos y Préstamos
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
    
    # Asegurar columnas en consumos
    cursor.execute("PRAGMA table_info(consumos)")
    columnas_consumos = [col[1] for col in cursor.fetchall()]
    if "tipo" not in columnas_consumos:
        cursor.execute("ALTER TABLE consumos ADD COLUMN tipo TEXT NOT NULL DEFAULT 'Material'")
    if "estado" not in columnas_consumos:
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

# --- INVENTARIO ---
def agregar_o_sumar_material(codigo, nombre, tipo, cantidad_nueva, stock_minimo=5):
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT cantidad FROM inventario WHERE codigo = ?", (codigo,))
    resultado = cursor.fetchone()
    if resultado:
        nueva_cantidad = resultado[0] + cantidad_nueva
        cursor.execute("UPDATE inventario SET cantidad = ?, tipo = ? WHERE codigo = ?", (nueva_cantidad, tipo, codigo))
    else:
        cursor.execute("INSERT INTO inventario VALUES (?, ?, ?, ?, ?)", (codigo, nombre, tipo, cantidad_nueva, stock_minimo))
    conn.commit()
    conn.close()

def obtener_inventario():
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, nombre, tipo, cantidad, stock_minimo FROM inventario")
    items = cursor.fetchall()
    conn.close()
    return items

def eliminar_material(codigo):
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventario WHERE codigo = ?", (codigo,))
    conn.commit()
    conn.close()

# --- ENTREGAS Y HERRAMIENTAS ---
def registrar_entrega(codigo, cantidad_entregada, operario):
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, tipo, cantidad FROM inventario WHERE codigo = ?", (codigo,))
    item = cursor.fetchone()
    
    if not item or item[2] < cantidad_entregada:
        conn.close()
        return False, "Stock insuficiente o ítem no existe"
    
    tipo_item = item[1]
    nuevo_stock = item[2] - cantidad_entregada
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    estado = "Prestado" if tipo_item == "Herramienta" else "Consumido"
    
    cursor.execute("UPDATE inventario SET cantidad = ? WHERE codigo = ?", (nuevo_stock, codigo))
    cursor.execute(
        "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (?, ?, ?, ?, ?, ?)",
        (fecha_actual, operario, codigo, cantidad_entregada, tipo_item, estado)
    )
    conn.commit()
    conn.close()
    return True, "Entrega registrada correctamente"

def registrar_devolucion_herramienta(id_consumo, codigo_material, cantidad):
    conn = sqlite3.connect("bodega.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Devolver stock
    cursor.execute("UPDATE inventario SET cantidad = cantidad + ? WHERE codigo = ?", (cantidad, codigo_material))
    # Cambiar estado
    cursor.execute("UPDATE consumos SET estado = 'Devuelto' WHERE id = ?", (id_consumo,))
    
    conn.commit()
    conn.close()

def obtener_movimientos():
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
