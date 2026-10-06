import psycopg2
from datetime import datetime

# Dirección de conexión a tu base de datos en Supabase
DB_URL = "postgresql://postgres.ngwbaadrmzkbvoqeoync:Metalyco2026@aws-0-us-west-2.pooler.supabase.com:6543/postgres?sslmode=require"
def conectar_bd():
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    # Crear tablas si no existen
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventario (
            codigo TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Material',
            cantidad INTEGER NOT NULL DEFAULT 0,
            stock_minimo INTEGER NOT NULL DEFAULT 5
        );

        CREATE TABLE IF NOT EXISTS operarios (
            id SERIAL PRIMARY KEY,
            nombre TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS consumos (
            id SERIAL PRIMARY KEY,
            fecha TEXT NOT NULL,
            operario TEXT NOT NULL,
            codigo_material TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Material',
            estado TEXT NOT NULL DEFAULT 'Entregado'
        );
    ''')

    conn.commit()
    cursor.close()
    conn.close()

# --- OPERARIOS ---
def obtener_operarios():
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM operarios ORDER BY nombre ASC")
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [f[0] for f in filas]

def agregar_operario(nombre):
    if not nombre.strip():
        return False
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO operarios (nombre) VALUES (%s)", (nombre.strip(),))
        conn.commit()
        exito = True
    except Exception:
        exito = False
    cursor.close()
    conn.close()
    return exito

def eliminar_operario(nombre):
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM operarios WHERE nombre = %s", (nombre,))
    conn.commit()
    cursor.close()
    conn.close()

# --- INVENTARIO ---
def agregar_o_actualizar_item(codigo, nombre, tipo, cantidad, stock_minimo):
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT cantidad FROM inventario WHERE codigo = %s", (codigo,))
    res = cursor.fetchone()
    if res:
        nueva_cant = res[0] + cantidad
        cursor.execute(
            "UPDATE inventario SET nombre = %s, tipo = %s, cantidad = %s, stock_minimo = %s WHERE codigo = %s",
            (nombre, tipo, nueva_cant, stock_minimo, codigo)
        )
    else:
        cursor.execute(
            "INSERT INTO inventario (codigo, nombre, tipo, cantidad, stock_minimo) VALUES (%s, %s, %s, %s, %s)",
            (codigo, nombre, tipo, cantidad, stock_minimo)
        )
    conn.commit()
    cursor.close()
    conn.close()

def obtener_inventario():
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, nombre, tipo, cantidad, stock_minimo FROM inventario ORDER BY nombre ASC")
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items

def eliminar_item_inventario(codigo):
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventario WHERE codigo = %s", (codigo,))
    conn.commit()
    cursor.close()
    conn.close()

def obtener_alertas_stock():
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, nombre, tipo, cantidad, stock_minimo FROM inventario WHERE tipo = 'Material' AND cantidad <= stock_minimo")
    alertas = cursor.fetchall()
    cursor.close()
    conn.close()
    return alertas

# --- SALIDAS Y DEVOLUCIONES ---
def registrar_entrega(codigo, cantidad, operario):
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, tipo, cantidad FROM inventario WHERE codigo = %s", (codigo,))
    item = cursor.fetchone()
    
    if not item:
        cursor.close()
        conn.close()
        return False, "El ítem especificado no existe."
    
    nom_item, tipo_item, cant_actual = item
    
    if cant_actual < cantidad:
        cursor.close()
        conn.close()
        return False, f"Stock insuficiente. Disponible: {cant_actual} unidades."
    
    nuevo_stock = cant_actual - cantidad
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    estado_inicial = "Prestado" if tipo_item == "Herramienta" else "Consumido"
    
    cursor.execute("UPDATE inventario SET cantidad = %s WHERE codigo = %s", (nuevo_stock, codigo))
    cursor.execute(
        "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (%s, %s, %s, %s, %s, %s)",
        (fecha_actual, operario, codigo, cantidad, tipo_item, estado_inicial)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return True, f"Entrega de {tipo_item.lower()} registrada exitosamente."

def registrar_devolucion_herramienta(id_consumo, codigo_material, cantidad):
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("UPDATE inventario SET cantidad = cantidad + %s WHERE codigo = %s", (cantidad, codigo_material))
    cursor.execute("UPDATE consumos SET estado = 'Devuelto' WHERE id = %s", (id_consumo,))
    conn.commit()
    cursor.close()
    conn.close()

def obtener_herramientas_en_poder():
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, c.fecha, c.operario, c.codigo_material, i.nombre, c.cantidad
        FROM consumos c
        JOIN inventario i ON c.codigo_material = i.codigo
        WHERE c.tipo = 'Herramienta' AND c.estado = 'Prestado'
        ORDER BY c.fecha DESC
    ''')
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return filas

def obtener_cargos_por_operario(operario_filtro=None):
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    query = '''
        SELECT c.operario, c.tipo, c.codigo_material, i.nombre, SUM(c.cantidad) as total_cantidad, c.estado, MAX(c.fecha) as ultima_fecha
        FROM consumos c
        JOIN inventario i ON c.codigo_material = i.codigo
        WHERE c.estado IN ('Prestado', 'Consumido')
    '''
    
    params = []
    if operario_filtro and operario_filtro != "Todos":
        query += " AND c.operario = %s"
        params.append(operario_filtro)
        
    query += '''
        GROUP BY c.operario, c.tipo, c.codigo_material, i.nombre, c.estado
        ORDER BY c.operario ASC, c.tipo DESC
    '''
    
    cursor.execute(query, params)
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return filas

def obtener_historial_movimientos():
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, c.fecha, c.operario, c.codigo_material, i.nombre, c.cantidad, c.tipo, c.estado
        FROM consumos c
        JOIN inventario i ON c.codigo_material = i.codigo
        ORDER BY c.id DESC
    ''')
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return filas
