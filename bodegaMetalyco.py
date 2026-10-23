import streamlit as st
import pandas as pd
import psycopg2
import os
import io
import urllib.parse
from datetime import datetime, time, date, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Configuración de página con diseño ajustado a móviles
st.set_page_config(
    page_title="Control de Producción - Industrias Metal&Co",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS optimizados
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .stButton>button {
            width: 100%;
            height: 3rem;
            font-size: 1.1rem;
            font-weight: bold;
            border-radius: 8px;
        }
        input {
            font-size: 1rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# Buscar imagen disponible en el directorio
NOMBRES_LOGO = ["WhatsApp Image 2026-10-06 at 6.50.00 PM.jpeg", "logo.jpeg", "logo.png", "logo.jpg"]
LOGO_PATH = None
for nombre in NOMBRES_LOGO:
    if os.path.exists(nombre):
        LOGO_PATH = nombre
        break

def mostrar_logo(ancho=100):
    if LOGO_PATH:
        st.image(LOGO_PATH, width=ancho)
    else:
        st.write("📦 **Industrias Metal&Co**")

# Parámetros de Conexión a Supabase
DB_PARAMS = {
    "dbname": "postgres",
    "user": "postgres.ngwbaadrmzkbvoqeoync",
    "password": "Metalgas2026",
    "host": "aws-1-us-west-2.pooler.supabase.com",
    "port": "6543",
    "sslmode": "require"
}

def ejecutar_consulta(query, params=None):
    conn = psycopg2.connect(**DB_PARAMS)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def ejecutar_comando(query, params=None):
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute(query, params or ())
    conn.commit()
    cur.close()
    conn.close()

# Inicializar y actualizar tablas del sistema
def inicializar_tablas_sistema():
    try:
        ejecutar_comando("""
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(150) UNIQUE NOT NULL,
                nit VARCHAR(50),
                telefono VARCHAR(50)
            );
        """)
        ejecutar_comando("""
            CREATE TABLE IF NOT EXISTS servicios_prestados (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) UNIQUE NOT NULL
            );
        """)
        ejecutar_comando("""
            CREATE TABLE IF NOT EXISTS clases_inventario (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) UNIQUE NOT NULL
            );
        """)
        ejecutar_comando("ALTER TABLE maquinas ADD COLUMN IF NOT EXISTS tipo_propiedad VARCHAR(50) DEFAULT 'PROPIA';")
        ejecutar_comando("ALTER TABLE maquinas ADD COLUMN IF NOT EXISTS costo_hora_alquiler NUMERIC(12,2) DEFAULT 0;")
        ejecutar_comando("ALTER TABLE registro_produccion ADD COLUMN IF NOT EXISTS numero_oc VARCHAR(100);")
        ejecutar_comando("ALTER TABLE registro_produccion ADD COLUMN IF NOT EXISTS es_maquina_alquilada BOOLEAN DEFAULT FALSE;")
        ejecutar_comando("ALTER TABLE registro_produccion ADD COLUMN IF NOT EXISTS horas_trabajadas NUMERIC(5,2) DEFAULT 0;")
        ejecutar_comando("ALTER TABLE registro_produccion ADD COLUMN IF NOT EXISTS presion_trabajo VARCHAR(50) DEFAULT '';")
        ejecutar_comando("ALTER TABLE registro_produccion ADD COLUMN IF NOT EXISTS fecha_registro DATE;")
        ejecutar_comando("ALTER TABLE programacion_diaria ADD COLUMN IF NOT EXISTS numero_oc VARCHAR(100);")
        ejecutar_comando("ALTER TABLE referencias ADD COLUMN IF NOT EXISTS cliente VARCHAR(150);")
        ejecutar_comando("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS nit VARCHAR(50);")
        ejecutar_comando("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS telefono VARCHAR(50);")
        ejecutar_comando("ALTER TABLE ordenes_compra ADD COLUMN IF NOT EXISTS fecha_registro DATE;")
    except Exception as e:
        print(f"Nota en inicialización: {e}")

inicializar_tablas_sistema()

# ----------------------------------------------------
# FUNCIONES AUXILIARES Y GENERACIÓN DE PDF (F-01-01)
# ----------------------------------------------------
def calcular_tipo_hora(inicio_str, fin_str):
    try:
        inicio = pd.to_datetime(str(inicio_str), format='%H:%M:%S', errors='coerce').time()
        if not inicio:
            inicio = pd.to_datetime(str(inicio_str), format='%H:%M', errors='coerce').time()
        fin = pd.to_datetime(str(fin_str), format='%H:%M:%S', errors='coerce').time()
        if not fin:
            fin = pd.to_datetime(str(fin_str), format='%H:%M', errors='coerce').time()
        if not inicio or not fin:
            return "Diurna"
        inicio_nocturno = time(19, 0)
        inicio_diurno = time(6, 0)
        if inicio >= inicio_diurno and fin <= inicio_nocturno and fin > inicio:
            return "Diurna"
        elif (inicio >= inicio_nocturno) or (fin <= inicio_diurno):
            return "Nocturna"
        else:
            return "Mixta"
    except Exception:
        return "Diurna"

def generar_reporte_produccion_excel(df_original):
    df = df_original.copy()
    if 'fecha_registro' in df.columns:
        df['Fecha'] = pd.to_datetime(df['fecha_registro']).dt.strftime('%Y-%m-%d')
    else:
        df['Fecha'] = (datetime.now() - timedelta(hours=5)).strftime('%Y-%m-%d')
        
    df['Orden'] = df['numero_oc'] if 'numero_oc' in df.columns else 'SIN OC'
    df['Area'] = 'Producción'
    df['Operario'] = df['operario_nombre'] if 'operario_nombre' in df.columns else ''
    df['MAQUINA UTILIZADA'] = df['maquina'] if 'maquina' in df.columns else ''
    df['Cantidad Producidad'] = df['unidades_producidas'] if 'unidades_producidas' in df.columns else 0
    df['Cantidad procesadas NC'] = 0
    
    for idx, row in df.iterrows():
        obs = str(row.get('observaciones', ''))
        if 'Defectuosas:' in obs:
            try:
                partes = obs.split('Defectuosas:')
                num_sc = int(partes[1].split(',')[0].strip())
                df.at[idx, 'Cantidad procesadas NC'] = num_sc
            except:
                pass

    col_ini = 'hora_inicio_real' if 'hora_inicio_real' in df.columns else 'Inicio'
    col_fin = 'hora_fin_real' if 'hora_fin_real' in df.columns else 'Fin'
    
    if col_ini in df.columns and col_fin in df.columns:
        df['Inicio'] = df[col_ini].astype(str)
        df['Fin'] = df[col_fin].astype(str)
        df['Tipo de hora'] = df.apply(lambda row: calcular_tipo_hora(row['Inicio'], row['Fin']), axis=1)
    else:
        df['Inicio'] = "07:00"
        df['Fin'] = "17:00"
        df['Tipo de hora'] = "Diurna"

    columnas_ordenadas = ["Fecha", "Orden", "Area", "Operario", "MAQUINA UTILIZADA", "Cantidad Producidad", "Cantidad procesadas NC", "Tipo de hora", "Inicio", "Fin"]
    for col in columnas_ordenadas:
        if col not in df.columns:
            df[col] = ""
    return df[columnas_ordenadas]

def generar_pdf_f01_01(datos):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    x_margen = 30
    ancho_util = width - 60
    y_actual = height - 40

    if LOGO_PATH and os.path.exists(LOGO_PATH):
        try:
            p.drawImage(LOGO_PATH, x_margen, y_actual - 25, width=80, height=25, preserveAspectRatio=True, mask='auto')
        except:
            p.setFont("Helvetica-Bold", 12)
            p.drawString(x_margen, y_actual - 15, "Metal&Co")
    else:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(x_margen, y_actual - 15, "Metal&Co")

    p.setFont("Helvetica-Bold", 10)
    p.drawCentredString(width / 2.0, y_actual - 10, "CONTROL DE PRODUCCIÓN Y CALIDAD PIEZAS TERMINADAS")
    
    p.setFont("Helvetica", 7)
    p.drawRightString(width - x_margen, y_actual - 8, "Código: F-01-01")
    p.drawRightString(width - x_margen, y_actual - 18, "Versión: 1")
    
    y_actual -= 35
    p.setLineWidth(0.75)
    p.line(x_margen, y_actual, width - x_margen, y_actual)
    
    y_actual -= 15
    p.setFillColorRGB(0.15, 0.15, 0.15)
    p.rect(x_margen, y_actual - 12, ancho_util, 14, fill=1, stroke=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 7.5)
    p.drawCentredString(width / 2.0, y_actual - 8, "INFORMACIÓN GENERAL (DILIGENCIA PROGRAMADOR/COORDINADOR PRODUCCIÓN)")
    
    y_actual -= 12
    p.setFillColorRGB(0, 0, 0)
    p.rect(x_margen, y_actual - 35, ancho_util, 35, fill=0, stroke=1)
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 8, y_actual - 12, "FECHA:")
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 50, y_actual - 12, f"{datos.get('fecha', (datetime.now() - timedelta(hours=5)).strftime('%Y-%m-%d'))}")
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 260, y_actual - 12, "OP (ORDEN DE PRODUCCIÓN):")
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 390, y_actual - 12, f"{datos.get('numero_oc', 'N/A')}")
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 8, y_actual - 26, "CLIENTE:")
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 50, y_actual - 26, f"{datos.get('cliente', 'N/A')}")
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 260, y_actual - 26, "REFERENCIA PIEZA:")
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 350, y_actual - 26, f"{datos.get('referencia', 'N/A')}")
    
    y_actual -= 45
    p.setFillColorRGB(0.15, 0.15, 0.15)
    p.rect(x_margen, y_actual - 14, ancho_util, 14, fill=1, stroke=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 8)
    p.drawCentredString(width / 2.0, y_actual - 9, "PROCESOS Y MÁQUINAS")
    
    y_actual -= 14
    p.setFillColorRGB(0, 0, 0)
    
    presion_val = datos.get('presion', '')
    alto_bloque = 30 if presion_val else 22
    p.rect(x_margen, y_actual - alto_bloque, ancho_util, alto_bloque, fill=0, stroke=1)
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 10, y_actual - 15, "PROCESO / ACTIVIDAD:")
    p.setFont("Helvetica", 8.5)
    p.drawString(x_margen + 140, y_actual - 15, f"[ X ] {str(datos.get('actividad', 'N/A')).upper()}")
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 320, y_actual - 15, "MÁQUINA:")
    p.setFont("Helvetica", 8.5)
    p.drawString(x_margen + 380, y_actual - 15, f"{str(datos.get('maquina', 'N/A')).upper()}")
    
    if presion_val:
        p.setFont("Helvetica-Bold", 8)
        p.drawString(x_margen + 10, y_actual - 26, "PRESIÓN DE TRABAJO:")
        p.setFont("Helvetica", 8.5)
        p.drawString(x_margen + 140, y_actual - 26, f"{presion_val}")
        y_actual -= 8

    y_actual -= (alto_bloque + 10)
    p.setFillColorRGB(0.15, 0.15, 0.15)
    p.rect(x_margen, y_actual - 12, ancho_util, 14, fill=1, stroke=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 7.5)
    p.drawCentredString(width / 2.0, y_actual - 8, "MATERIALES Y CANTIDADES")
    
    y_actual -= 12
    p.rect(x_margen, y_actual - 25, ancho_util, 25, fill=0, stroke=1)
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 8, y_actual - 10, "DESCRIPCIÓN")
    p.drawString(x_margen + 200, y_actual - 10, "CANTIDAD")
    p.drawString(x_margen + 290, y_actual - 10, "DESCRIPCIÓN")
    p.drawString(x_margen + 480, y_actual - 10, "CANTIDAD")
    p.line(x_margen, y_actual - 14, width - x_margen, y_actual - 14)
    
    y_actual -= 35
    p.rect(x_margen, y_actual - 20, ancho_util, 20, fill=0, stroke=1)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 8, y_actual - 13, "CANTIDAD DEL LOTE:")
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 115, y_actual - 13, f"{datos.get('producidas', 0)}")
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 200, y_actual - 13, "TAMAÑO MUESTRA:")
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 295, y_actual - 13, "N/A")
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 400, y_actual - 13, "NIVEL AQL:")
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 460, y_actual - 13, "2.5")
    
    y_actual -= 30
    p.setFillColorRGB(0.15, 0.15, 0.15)
    p.rect(x_margen, y_actual - 12, ancho_util, 14, fill=1, stroke=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 7.5)
    p.drawCentredString(width / 2.0, y_actual - 8, "CONTROL DE PRODUCCIÓN (DILIGENCIA OPERARIO)")
    
    y_actual -= 12
    p.setFillColorRGB(0, 0, 0)
    p.rect(x_margen, y_actual - 28, ancho_util, 28, fill=0, stroke=1)
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(x_margen + 5, y_actual - 11, "HORA INICIO")
    p.drawString(x_margen + 75, y_actual - 11, "HORA FIN")
    p.drawString(x_margen + 135, y_actual - 11, "PARÁMETROS")
    p.drawString(x_margen + 220, y_actual - 11, "PRODUCIDAS")
    p.drawString(x_margen + 290, y_actual - 11, "RECHAZADAS")
    p.drawString(x_margen + 370, y_actual - 11, "RETRABAJO")
    p.drawString(x_margen + 440, y_actual - 11, "OBSERVACIONES")
    p.line(x_margen, y_actual - 14, width - x_margen, y_actual - 14)
    
    y_actual -= 14
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 8, y_actual - 9, f"{datos.get('hora_inicio', '')}")
    p.drawString(x_margen + 78, y_actual - 9, f"{datos.get('hora_fin', '')}")
    p.drawString(x_margen + 145, y_actual - 9, "OK")
    p.drawString(x_margen + 235, y_actual - 9, f"{datos.get('producidas', 0)}")
    p.drawString(x_margen + 310, y_actual - 9, f"{datos.get('defectuosas', 0)}")
    p.drawString(x_margen + 385, y_actual - 9, "0")
    p.drawString(x_margen + 440, y_actual - 9, f"{datos.get('observaciones', '')[:25]}")
    
    y_actual -= 28
    p.setFillColorRGB(0.15, 0.15, 0.15)
    p.rect(x_margen, y_actual - 12, ancho_util, 14, fill=1, stroke=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 7.5)
    p.drawCentredString(width / 2.0, y_actual - 8, "CONTROL PRIMERA PIEZA TERMINADA PUESTA A PUNTO (DILIGENCIA OPERARIO Y/O INSPECTOR)")
    
    y_actual -= 12
    p.setFillColorRGB(0, 0, 0)
    p.rect(x_margen, y_actual - 45, ancho_util, 45, fill=0, stroke=1)
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 8, y_actual - 11, "TIPO")
    p.drawString(x_margen + 250, y_actual - 11, "OK")
    p.drawString(x_margen + 350, y_actual - 11, "NC")
    p.drawString(x_margen + 450, y_actual - 11, "NA")
    p.line(x_margen, y_actual - 14, width - x_margen, y_actual - 14)
    
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 8, y_actual - 23, "DIMENSIONES")
    p.drawString(x_margen + 252, y_actual - 23, "X")
    
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 8, y_actual - 32, "ACABADO SUPERFICIAL")
    p.drawString(x_margen + 252, y_actual - 32, "X")
    
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 8, y_actual - 41, "SOLDADURA / PINTURA")
    p.drawString(x_margen + 252, y_actual - 41, "X")
    
    y_actual -= 55
    p.rect(x_margen, y_actual - 32, ancho_util, 32, fill=0, stroke=1)
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(x_margen + 10, y_actual - 11, f"NOMBRE OPERARIO: {datos.get('operario', 'N/A')}")
    p.drawString(x_margen + 300, y_actual - 11, "NOMBRE INSPECTOR: _____________________")
    p.drawString(x_margen + 150, y_actual - 24, "NOMBRE AUDITOR EXTERNO (SI APLICA): _____________________")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# ----------------------------------------------------
# INICIALIZACIÓN DE SESIÓN
# ----------------------------------------------------
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "rol" not in st.session_state:
    st.session_state["rol"] = None
if "nombre_usuario" not in st.session_state:
    st.session_state["nombre_usuario"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
if "form_key_counter" not in st.session_state:
    st.session_state["form_key_counter"] = 0

# PANTALLA DE LOGIN
if not st.session_state["autenticado"]:
    st.title("🔑 Sistema Industrias Metal&Co")
    st.subheader("Inicio de Sesión")
    
    c_logo, c_form = st.columns([1, 1], vertical_alignment="center")
    with c_logo:
        mostrar_logo(ancho=250)
    with c_form:
        with st.form("form_login"):
            user_input = st.text_input("Usuario")
            pass_input = st.text_input("Contraseña", type="password")
            submit_login = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
            
            if submit_login:
                try:
                    res = ejecutar_consulta(
                        "SELECT username, nombre, rol FROM usuarios WHERE username = %s AND password = %s",
                        (user_input, pass_input)
                    )
                    if not res.empty:
                        st.session_state["autenticado"] = True
                        st.session_state["username"] = res.iloc[0]["username"]
                        st.session_state["nombre_usuario"] = res.iloc[0]["nombre"]
                        st.session_state["rol"] = res.iloc[0]["rol"]
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos")
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
    st.stop()

# ENCABEZADO Y BARRA LATERAL
col_logo, col_titulo = st.columns([1, 4], vertical_alignment="center")
with col_logo:
    mostrar_logo(ancho=100)
with col_titulo:
    st.title("Industrias Metal&Co")

st.sidebar.markdown(f"👤 **Usuario:** {st.session_state['nombre_usuario']}")
st.sidebar.markdown(f"🔰 **Rol:** `{str(st.session_state['rol']).upper()}`")
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Actualizar Datos", use_container_width=True):
    st.rerun()
st.sidebar.markdown("---")
if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    st.session_state["autenticado"] = False
    st.session_state["rol"] = None
    st.session_state["nombre_usuario"] = None
    st.session_state["username"] = None
    st.rerun()

rol = st.session_state["rol"]

# ====================================================
# VISTA EXCLUSIVA PARA OPERARIOS
# ====================================================
if rol == "operario":
    st.subheader(f"📌 Hola, {st.session_state['nombre_usuario']}")
    
    tab_prog, tab_prod, tab_nueva = st.tabs(["📋 Mi Programación", "⚙️ Registrar Producción", "➕ Agregar Tarea Imprevista"])
    
    with tab_prog:
        st.write("### Consulta tus Tareas Asignadas")
        filtro_fecha = st.radio("Ver tareas de:", ["Todas mis tareas pendientes", "Filtrar por fecha específica"], horizontal=True)
        try:
            if filtro_fecha == "Filtrar por fecha específica":
                fecha_operario = st.date_input("Selecciona el día a consultar", value=(datetime.now() - timedelta(hours=5)).date(), key="cal_op_dia")
                tareas = ejecutar_consulta(
                    """SELECT id, fecha, numero_oc, hora_inicio, hora_fin, maquina, referencia, actividad, meta_unidades, estado 
                       FROM programacion_diaria 
                       WHERE operario_nombre = %s AND fecha = %s AND estado NOT IN ('FINALIZADO', 'CANCELADO')
                       ORDER BY fecha ASC, id DESC""",
                    (st.session_state['nombre_usuario'], fecha_operario)
                )
            else:
                tareas = ejecutar_consulta(
                    """SELECT id, fecha, numero_oc, hora_inicio, hora_fin, maquina, referencia, actividad, meta_unidades, estado 
                       FROM programacion_diaria 
                       WHERE operario_nombre = %s AND estado NOT IN ('FINALIZADO', 'CANCELADO')
                       ORDER BY fecha ASC, id DESC""",
                    (st.session_state['nombre_usuario'],)
                )
            if not tareas.empty:
                st.dataframe(tareas, use_container_width=True)
            else:
                st.info("No tienes tareas pendientes registradas.")
        except Exception as e:
            st.error(f"Error al cargar programación: {e}")

    with tab_prod:
        st.write("### Registrar Producción y Generar Formato PDF (F-01-01)")
        try:
            tareas_pendientes = ejecutar_consulta(
                """SELECT id, fecha, numero_oc, actividad, maquina, referencia, meta_unidades FROM programacion_diaria 
                   WHERE operario_nombre = %s AND estado NOT IN ('FINALIZADO', 'CANCELADO')
                   ORDER BY fecha ASC, id DESC""",
                (st.session_state['nombre_usuario'],)
            )
            
            if tareas_pendientes.empty:
                st.warning("No tienes tareas pendientes asignadas para reportar.")
            else:
                lista_opciones = [
                    f"ID #{row['id']} | Fecha: {row['fecha']} | OC: {row['numero_oc']} - {row['actividad']} (Ref: {row['referencia']} | Meta: {row['meta_unidades']} u.)" 
                    for _, row in tareas_pendientes.iterrows()
                ]
                
                with st.form("form_reporte_operario"):
                    tarea_elegida_str = st.selectbox("Selecciona la Tarea a Registrar", lista_opciones)
                    
                    id_t_temp = int(tarea_elegida_str.split(" | ")[0].replace("ID #", ""))
                    maq_nombre_temp = tareas_pendientes[tareas_pendientes['id'] == id_t_temp].iloc[0]['maquina']
                    
                    es_prensa = any(p in maq_nombre_temp.lower() for p in ['prensa', 'troqueladora', 'dobladora'])
                    presion_input = ""
                    if es_prensa:
                        presion_input = st.text_input("Presión de Trabajo (Ej: 150 Ton / 25 MPa)")
                    
                    h_inicio = st.time_input("Hora de Inicio Real", time(7, 0))
                    h_fin = st.time_input("Hora de Finalización Real", time(17, 0))
                    
                    unidades = st.number_input("Unidades Producidas Buenas", min_value=0, step=1)
                    defectuosas = st.number_input("Unidades Defectuosas (Scrap)", min_value=0, step=1, value=0)
                    obs_usuario = st.text_area("Observaciones / Novedades")
                    
                    submit = st.form_submit_button("Guardar y Generar PDF", type="primary", use_container_width=True)
                    
                    if submit:
                        id_tarea_str = tarea_elegida_str.split(" | ")[0].replace("ID #", "")
                        id_tarea = int(id_tarea_str)
                        row_t = tareas_pendientes[tareas_pendientes['id'] == id_tarea].iloc[0]
                        num_oc_asociada = row_t['numero_oc']
                        maquina_elegida = row_t['maquina']
                        referencia_pieza = row_t['referencia']
                        actividad_tarea = row_t['actividad']
                        meta_asignada_tarea = int(row_t['meta_unidades'])
                        
                        cli_db = ejecutar_consulta("SELECT cliente FROM ordenes_compra WHERE numero_oc = %s AND referencia = %s", (num_oc_asociada, referencia_pieza))
                        if cli_db.empty:
                            cli_db = ejecutar_consulta("SELECT cliente FROM ordenes_compra WHERE numero_oc = %s", (num_oc_asociada,))
                        cliente_nombre = cli_db.iloc[0]['cliente'] if not cli_db.empty else "N/A"
                        
                        maq_db = ejecutar_consulta("SELECT tipo_propiedad FROM maquinas WHERE nombre = %s", (maquina_elegida,))
                        es_alq = False
                        if not maq_db.empty:
                            if str(maq_db.iloc[0]['tipo_propiedad']).upper() == 'ALQUILADA':
                                es_alq = True
                        
                        dt_inicio = datetime.combine((datetime.now() - timedelta(hours=5)).date(), h_inicio)
                        dt_fin = datetime.combine((datetime.now() - timedelta(hours=5)).date(), h_fin)
                        if dt_fin < dt_inicio: 
                            dt_fin += timedelta(days=1)
                        diff_seg = (dt_fin - dt_inicio).total_seconds()
                        horas_calc = round(max(0.0, diff_seg / 3600.0), 2)
                        
                        alerta_pendiente_txt = ""
                        if unidades < meta_asignada_tarea:
                            faltantes = meta_asignada_tarea - unidades
                            alerta_pendiente_txt = f" ⚠️ ALARMA: Faltaron {faltantes} unidades para cumplir la meta de {meta_asignada_tarea} u."
                        
                        fecha_exacta_actual = (datetime.now() - timedelta(hours=5)).strftime('%Y-%m-%d')

                        ejecutar_comando(
                            """INSERT INTO registro_produccion 
                            (operario_nombre, maquina, referencia, numero_oc, hora_inicio_real, hora_fin_real, unidades_producidas, observaciones, es_maquina_alquilada, horas_trabajadas, presion_trabajo, fecha_registro) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::date)""",
                            (st.session_state['nombre_usuario'], maquina_elegida, referencia_pieza, num_oc_asociada, h_inicio, h_fin, unidades, f"Buenas: {unidades}, Defectuosas: {defectuosas}.{alerta_pendiente_txt} {obs_usuario}", es_alq, horas_calc, presion_input, fecha_exacta_actual)
                        )
                        
                        if num_oc_asociada and num_oc_asociada != "SIN OC":
                            oc_db = ejecutar_consulta("SELECT unidades_entregadas, meta_unidades, requiere_unidades FROM ordenes_compra WHERE numero_oc = %s AND referencia = %s", (num_oc_asociada, referencia_pieza))
                            if oc_db.empty:
                                oc_db = ejecutar_consulta("SELECT unidades_entregadas, meta_unidades, requiere_unidades FROM ordenes_compra WHERE numero_oc = %s", (num_oc_asociada,))
                                
                            if not oc_db.empty:
                                ent_actuales = int(oc_db.iloc[0]['unidades_entregadas']) if pd.notna(oc_db.iloc[0]['unidades_entregadas']) else 0
                                meta_oc = int(oc_db.iloc[0]['meta_unidades'])
                                req_uni = oc_db.iloc[0]['requiere_unidades']
                                nuevo_entregado = ent_actuales + unidades
                                nuevo_estado = 'COMPLETADO' if req_uni and nuevo_entregado >= meta_oc else 'EN PROCESO'
                                ejecutar_comando(
                                    "UPDATE ordenes_compra SET unidades_entregadas = %s, estado = %s WHERE numero_oc = %s AND referencia = %s",
                                    (nuevo_entregado, nuevo_estado, num_oc_asociada, referencia_pieza)
                                )

                        ejecutar_comando("UPDATE programacion_diaria SET estado = 'FINALIZADO' WHERE id = %s", (id_tarea,))
                        
                        datos_pdf = {
                            "fecha": fecha_exacta_actual,
                            "numero_oc": num_oc_asociada,
                            "cliente": cliente_nombre,
                            "referencia": referencia_pieza,
                            "maquina": maquina_elegida,
                            "actividad": actividad_tarea,
                            "presion": presion_input,
                            "hora_inicio": str(h_inicio),
                            "hora_fin": str(h_fin),
                            "producidas": unidades,
                            "defectuosas": defectuosas,
                            "observaciones": obs_usuario + alerta_pendiente_txt,
                            "operario": st.session_state['nombre_usuario']
                        }
                        
                        pdf_buffer = generar_pdf_f01_01(datos_pdf)
                        st.session_state["ultimo_pdf_buffer"] = pdf_buffer.getvalue()
                        st.session_state["ultimo_pdf_nombre"] = f"F-01-01_OC_{num_oc_asociada}_{referencia_pieza}.pdf"
                        
                        if unidades < meta_asignada_tarea:
                            st.warning(f"¡Producción registrada! ⚠️ **Atención:** Se reportaron piezas pendientes por completar ({meta_asignada_tarea - unidades} u. faltantes). La orden quedará en seguimiento.")
                        else:
                            st.success("¡Producción registrada y formato F-01-01 generado con éxito!")

            if "ultimo_pdf_buffer" in st.session_state:
                st.markdown("---")
                st.write("### 📄 Formato F-01-01 Listo para Descargar y Enviar")
                st.download_button(
                    label="📥 Descargar Formato F-01-01 (PDF Oficial)",
                    data=st.session_state["ultimo_pdf_buffer"],
                    file_name=st.session_state["ultimo_pdf_nombre"],
                    mime="application/pdf",
                    use_container_width=True
                )
                
                texto_wsp = f"Hola, comparto el formato de producción F-01-01 completado por el operario *{st.session_state['nombre_usuario']}*."
                link_whatsapp = f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto_wsp)}"
                st.markdown(f'<a href="{link_whatsapp}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; height:3rem; font-size:1.1rem; font-weight:bold; border:none; border-radius:8px; cursor:pointer;">💬 Enviar Aviso por WhatsApp</button></a>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error al registrar producción: {e}")

    with tab_nueva:
        st.subheader("➕ Registrar e Iniciar Tarea Imprevista No Programada")
        try:
            maqs = ejecutar_consulta("SELECT nombre FROM maquinas")['nombre'].tolist()
            refs = ejecutar_consulta("SELECT codigo FROM referencias")['codigo'].tolist()
            serv_db = ejecutar_consulta("SELECT nombre FROM servicios_prestados")['nombre'].tolist()
            ocs_db = ejecutar_consulta("SELECT numero_oc, cliente FROM ordenes_compra WHERE estado != 'COMPLETADO'")
            
            ocs_disp = ["SIN OC"]
            mapa_oc_cliente = {}
            if not ocs_db.empty:
                for _, row in ocs_db.iterrows():
                    oc_num = row['numero_oc']
                    cli_nom = row['cliente']
                    ocs_disp.append(oc_num)
                    mapa_oc_cliente[oc_num] = cli_nom
            
            if not maqs or not refs:
                st.warning("Faltan máquinas o referencias registradas en el sistema.")
            else:
                with st.form("form_tarea_imprevista", clear_on_submit=True):
                    oc_imp = st.selectbox("Orden de Compra Asociada", ocs_disp)
                    cliente_asociado_oc = mapa_oc_cliente.get(oc_imp, "N/A (Sin OC)")
                    st.info(f"🏢 **Cliente asociado automáticamente:** `{cliente_asociado_oc}`")
                    
                    maq_imp = st.selectbox("Máquina", maqs)
                    
                    es_prensa_imp = any(p in maq_imp.lower() for p in ['prensa', 'troqueladora', 'dobladora'])
                    presion_imp = ""
                    if es_prensa_imp:
                        presion_imp = st.text_input("Presión de Trabajo (Ej: 150 Ton / 25 MPa)")
                        
                    ref_imp = st.selectbox("Referencia", refs)
                    act_imp = st.selectbox("Servicio / Actividad Prestada", serv_db if serv_db else ["CORTE", "PLEGADO", "SOLDADURA", "CONFORMADO", "PINTURA"])
                    
                    c_h1, c_h2 = st.columns(2)
                    with c_h1:
                        h_ini_imp = st.time_input("Hora de Inicio", time(8, 0))
                    with c_h2:
                        h_fin_imp = st.time_input("Hora de Finalización", time(17, 0))
                        
                    uni_imp = st.number_input("Unidades Producidas Buenas", min_value=0, value=1)
                    def_imp = st.number_input("Unidades Defectuosas (Scrap)", min_value=0, value=0)
                    obs_imp = st.text_area("Observaciones del Imprevisto")
                    
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        obs_final_imp = f"⚡ TAREA IMPREVISTA (Cliente: {cliente_asociado_oc}): {act_imp} | Buenas: {uni_imp}, Defectuosas: {def_imp}. Nota: {obs_imp}"
                        maq_db = ejecutar_consulta("SELECT tipo_propiedad FROM maquinas WHERE nombre = %s", (maq_imp,))
                        es_alq = False
                        if not maq_db.empty:
                            if str(maq_db.iloc[0]['tipo_propiedad']).upper() == 'ALQUILADA':
                                es_alq = True
                        
                        dt_inicio_imp = datetime.combine((datetime.now() - timedelta(hours=5)).date(), h_ini_imp)
                        dt_fin_imp = datetime.combine((datetime.now() - timedelta(hours=5)).date(), h_fin_imp)
                        if dt_fin_imp < dt_inicio_imp:
                            dt_fin_imp += timedelta(days=1)
                        diff_seg_imp = (dt_fin_imp - dt_inicio_imp).total_seconds()
                        horas_calc = round(max(0.0, diff_seg_imp / 3600.0), 2)

                        fecha_exacta_actual_imp = (datetime.now() - timedelta(hours=5)).strftime('%Y-%m-%d')

                        ejecutar_comando(
                            """INSERT INTO registro_produccion 
                            (operario_nombre, maquina, referencia, numero_oc, hora_inicio_real, hora_fin_real, unidades_producidas, observaciones, es_maquina_alquilada, horas_trabajadas, presion_trabajo, fecha_registro) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::date)""",
                            (st.session_state['nombre_usuario'], maq_imp, ref_imp, oc_imp, h_ini_imp, h_fin_imp, uni_imp, obs_final_imp, es_alq, horas_calc, presion_imp, fecha_exacta_actual_imp)
                        )
                        st.success("¡Tarea imprevista registrada!")
                        st.rerun()
        except Exception as e:
            st.error(f"Error al cargar formulario: {e}")

# ====================================================
# VISTA PARA ADMINISTRADOR Y PRODUCCIÓN
# ====================================================
elif rol in ["admin", "produccion"]:
    if rol == "admin":
        tab_prog, tab_oc, tab_eq, tab_serv, tab_ref, tab_rep, tab_ent, tab_herramientas, tab_cargue, tab_inv_gen, tab_clases, tab_clientes, tab_usu = st.tabs([
            "📅 Programar", "📋 Órdenes Compra", "⚙️ Máquinas", "🛠️ Servicios", "📄 Referencias", "📊 Reportes", 
            "🚀 Entregas", "🔨 Herramientas", "📥 Cargue Ítems", "📦 Inventario", "🏷️ Clases", "👥 Clientes", "⚙️ Usuarios"
        ])
    else:
        tab_prog, tab_oc, tab_ref, tab_rep, tab_ent, tab_herramientas, tab_cargue, tab_inv_gen = st.tabs([
            "📅 Programar", "📋 Órdenes Compra", "📄 Referencias", "📊 Reportes", "🚀 Entregas", "🔨 Herramientas", "📥 Cargue Ítems", "📦 Inventario"
        ])
    
    with tab_prog:
        st.subheader("📅 Programación Directa por Orden de Compra y Referencia")
        fecha_seleccionada = st.date_input("Selecciona el día a consultar/programar", value=(datetime.now() - timedelta(hours=5)).date(), key="cal_admin_dia")
        try:
            ops_df = ejecutar_consulta("SELECT nombre FROM usuarios WHERE rol = 'operario'")
            ops = ops_df['nombre'].tolist() if not ops_df.empty else []
            maqs = ejecutar_consulta("SELECT nombre FROM maquinas")['nombre'].tolist()
            
            ocs_db = ejecutar_consulta("""
                SELECT id, numero_oc, referencia, servicio, meta_unidades FROM ordenes_compra 
                WHERE estado != 'COMPLETADO'
            """)
            
            ocs_activas_validas = []
            info_ocs_dict = {}
            if not ocs_db.empty:
                for _, r in ocs_db.iterrows():
                    oc_id = int(r['id'])
                    oc_num = str(r['numero_oc']).strip()
                    ref_val = str(r['referencia']).strip()
                    clave_combinada = f"ID OC #{oc_id} | OC: {oc_num} - Ref: {ref_val}"
                    
                    # 💡 Filtro estricto: Si ya existe en programacion_diaria con estado activo/pendiente, NO se muestra
                    ya_prog = ejecutar_consulta(
                        "SELECT id FROM programacion_diaria WHERE TRIM(numero_oc) = %s AND TRIM(referencia) = %s AND estado NOT IN ('FINALIZADO', 'CANCELADO')",
                        (oc_num, ref_val)
                    )
                    
                    if ya_prog.empty:
                        ocs_activas_validas.append(clave_combinada)
                        info_ocs_dict[clave_combinada] = {
                            "id_oc": oc_id,
                            "numero_oc": oc_num,
                            "referencia": ref_val,
                            "servicio": str(r['servicio']).strip(),
                            "meta": int(r['meta_unidades'])
                        }

            if not ops or not maqs or not ocs_activas_validas:
                st.warning("⚠️ No hay Órdenes de Compra o Referencias disponibles para programar (las activas ya fueron programadas o se completaron).")
            else:
                with st.expander("Crear Programación Limpia por Referencia", expanded=True):
                    k_sufijo = st.session_state["form_key_counter"]
                    
                    oc_prog_sel = st.selectbox("Seleccionar Orden de Compra y Referencia", ocs_activas_validas, key=f"select_oc_limpia_{k_sufijo}")
                    
                    datos_oc_sel = info_ocs_dict.get(oc_prog_sel, {})
                    oc_real = datos_oc_sel.get("numero_oc", "")
                    ref_arrastrada = datos_oc_sel.get("referencia", "")
                    servicio_arrastrado = datos_oc_sel.get("servicio", "SIN SERVICIO")
                    meta_arrastrada = datos_oc_sel.get("meta", 100)
                    
                    st.info(f"🔒 **Datos limpios arrastrados:** \n- **OC:** `{oc_real}` \n- **Referencia:** `{ref_arrastrada}` \n- **Servicio:** `{servicio_arrastrado}` \n- **Meta de esta Referencia:** `{meta_arrastrada} u.`")
                    
                    with st.form(f"form_programacion_limpia_{fecha_seleccionada}_{k_sufijo}", clear_on_submit=True):
                        op_p = st.selectbox("Operario", ops, key=f"op_prog_{k_sufijo}")
                        maq_p = st.selectbox("Máquina", maqs, key=f"maq_prog_{k_sufijo}")
                        
                        col_h1, col_h2 = st.columns(2)
                        with col_h1:
                            h_ini_p = st.time_input("Inicio Turno", time(7, 0), key=f"hini_{k_sufijo}")
                        with col_h2:
                            h_fin_p = st.time_input("Fin Turno", time(17, 0), key=f"hfin_{k_sufijo}")
                        
                        st.markdown(f"📌 **Meta asignada para esta tarea:** `{meta_arrastrada} u.`")
                        
                        if st.form_submit_button("Guardar Programación de Tarea", type="primary", use_container_width=True):
                            ejecutar_comando(
                                """INSERT INTO programacion_diaria 
                                (fecha, numero_oc, operario_nombre, maquina, referencia, actividad, hora_inicio, hora_fin, meta_unidades, estado) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDIENTE')""",
                                (fecha_seleccionada, oc_real, op_p, maq_p, ref_arrastrada, servicio_arrastrado, h_ini_p, h_fin_p, meta_arrastrada)
                            )
                            st.session_state["form_key_counter"] += 1
                            st.success(f"¡Tarea asignada a {op_p} para la OC #{oc_real} (Ref: {ref_arrastrada}) con meta de {meta_arrastrada} u.!")
                            st.rerun()
            
            st.write("---")
            st.write(f"### Actividades Programadas para el: **{fecha_seleccionada}**")
            df_prog_actual = ejecutar_consulta("SELECT * FROM programacion_diaria WHERE fecha = %s ORDER BY id DESC", (fecha_seleccionada,))
            if not df_prog_actual.empty:
                st.dataframe(df_prog_actual, use_container_width=True)
                with st.expander("Eliminar Programación"):
                    id_del = st.selectbox("ID a Eliminar", df_prog_actual["id"].tolist(), key="del_prog_id_c")
                    if st.button("Confirmar Eliminación", type="primary", use_container_width=True):
                        ejecutar_comando("DELETE FROM programacion_diaria WHERE id = %s", (id_del,))
                        st.success(f"ID #{id_del} eliminado.")
                        st.rerun()
            else:
                st.info(f"No hay actividades programadas para la fecha {fecha_seleccionada}.")
        except Exception as e:
            st.error(f"Error en Programación: {e}")

    with tab_oc:
        st.subheader("📋 Gestión de Órdenes de Compra (OC), Clientes y Alarma de Pendientes")
        try:
            refs_db = ejecutar_consulta("SELECT codigo FROM referencias")
            lista_refs = refs_db['codigo'].tolist() if not refs_db.empty else []
            serv_db = ejecutar_consulta("SELECT nombre FROM servicios_prestados")
            lista_servicios = serv_db['nombre'].tolist() if not serv_db.empty else []
            clientes_db = ejecutar_consulta("SELECT nombre FROM clientes")
            lista_clientes = clientes_db['nombre'].tolist() if not clientes_db.empty else []
            
            if not lista_refs:
                st.warning("⚠️ Primero debes crear referencias en la pestaña 'Referencias' antes de crear Órdenes de Compra.")
            else:
                with st.expander("Crear", expanded=True):
                    with st.form("form_crear_oc", clear_on_submit=True):
                        num_oc = st.text_input("Número de Orden de Compra (Ej: OC-9021)")
                        cliente_oc = st.selectbox("Cliente Asociado", lista_clientes if lista_clientes else ["SIN CLIENTE REGISTRADO"])
                        ref_oc = st.selectbox("Referencia Base", lista_refs)
                        servicio_oc = st.selectbox("Servicio Prestado", lista_servicios if lista_servicios else ["NINGUNO"])
                        meta_oc = st.number_input("Cantidad Total Pedida (Meta de este Ítems/Referencia)", min_value=1, value=100)
                        
                        if st.form_submit_button("Guardar Orden de Compra", type="primary", use_container_width=True):
                            if num_oc.strip() and cliente_oc != "SIN CLIENTE REGISTRADO":
                                ej_fecha = (datetime.now() - timedelta(hours=5)).strftime('%Y-%m-%d')
                                try:
                                    ejecutar_comando(
                                        """INSERT INTO ordenes_compra 
                                        (numero_oc, cliente, referencia, servicio, requiere_unidades, meta_unidades, unidades_entregadas, estado, fecha_registro) 
                                        VALUES (%s, %s, %s, %s, TRUE, %s, 0, 'PENDIENTE', %s::date)""",
                                        (num_oc.upper().strip(), cliente_oc, ref_oc, servicio_oc, meta_oc, ej_fecha)
                                    )
                                except:
                                    # Fallback por si la columna fecha_registro aún no existe en Supabase
                                    ejecutar_comando(
                                        """INSERT INTO ordenes_compra 
                                        (numero_oc, cliente, referencia, servicio, requiere_unidades, meta_unidades, unidades_entregadas, estado) 
                                        VALUES (%s, %s, %s, %s, TRUE, %s, 0, 'PENDIENTE')""",
                                        (num_oc.upper().strip(), cliente_oc, ref_oc, servicio_oc, meta_oc)
                                    )
                                st.success(f"Orden de Compra #{num_oc} (Ref: {ref_oc}) registrada con éxito.")
                                st.rerun()
                            else:
                                st.error("Por favor completa el número de OC y selecciona un cliente válido.")

            st.write("---")
            st.write("### 📊 Estado y Reporte de Alarma de Piezas Pendientes por OC")
            df_oc = ejecutar_consulta("SELECT * FROM ordenes_compra ORDER BY id DESC")
            if not df_oc.empty:
                if 'fecha_registro' in df_oc.columns:
                    df_oc['fecha_registro'] = pd.to_datetime(df_oc['fecha_registro']).dt.strftime('%Y-%m-%d')
                
                df_oc['saldo_pendiente'] = df_oc.apply(
                    lambda row: row['meta_unidades'] - (row['unidades_entregadas'] if pd.notna(row['unidades_entregadas']) else 0), axis=1
                )
                
                def alerta_estado(row):
                    entregado = row['unidades_entregadas'] if pd.notna(row['unidades_entregadas']) else 0
                    meta = row['meta_unidades']
                    if entregado >= meta:
                        return "✅ COMPLETADO"
                    elif entregado > 0:
                        return f"⚠️ PENDIENTE ({meta - entregado} u. faltantes)"
                    else:
                        return "⏳ SIN INICIAR"
                
                df_oc['estado_alarma'] = df_oc.apply(alerta_estado, axis=1)
                st.dataframe(df_oc[['id', 'numero_oc', 'cliente', 'referencia', 'meta_unidades', 'unidades_entregadas', 'saldo_pendiente', 'estado_alarma']], use_container_width=True)
                
                with st.expander("Eliminar una Referencia Específica de la OC (Por ID de Línea)"):
                    with st.form("form_del_oc_fila", clear_on_submit=True):
                        id_oc_del = st.selectbox("Selecciona el ID de la línea de OC a borrar", df_oc["id"].tolist())
                        fila_borrar = df_oc[df_oc['id'] == id_oc_del].iloc[0]
                        st.warning(f"Vas a eliminar la línea ID #{id_oc_del} | OC: **{fila_borrar['numero_oc']}** | Ref: **{fila_borrar['referencia']}**")
                        
                        if st.form_submit_button("Confirmar Eliminación de esta Referencia", type="primary", use_container_width=True):
                            ejecutar_comando("DELETE FROM ordenes_compra WHERE id = %s", (id_oc_del,))
                            st.success(f"La referencia de la orden fue eliminada correctamente sin afectar las demás.")
                            st.rerun()
            else:
                st.info("No hay órdenes de compra registradas.")
        except Exception as e:
            st.error(f"Error en Órdenes de Compra: {e}")

    if rol == "admin":
        with tab_eq:
            st.subheader("⚙️ Gestión de Máquinas (Propias y Alquiladas)")
            try:
                df_maqs = ejecutar_consulta("SELECT * FROM maquinas")
                st.dataframe(df_maqs, use_container_width=True)
                with st.expander("Crear"):
                    with st.form("form_crear_maquina", clear_on_submit=True):
                        m_nom = st.text_input("Nombre de la Máquina (Ej: Prensa Hidráulica 01)")
                        m_tipo = st.text_input("Tipo (Ej: Conformado, Plegadora)")
                        m_prop = st.selectbox("Tipo de Propiedad", ["PROPIA", "ALQUILADA"])
                        m_costo_alq = st.number_input("Costo por Hora de Alquiler ($)", min_value=0.0, step=1000.0, value=0.0)
                        if st.form_submit_button("Guardar Máquina", type="primary", use_container_width=True):
                            if m_nom.strip():
                                ejecutar_comando(
                                    "INSERT INTO maquinas (nombre, tipo, tipo_propiedad, costo_hora_alquiler) VALUES (%s, %s, %s, %s)", 
                                    (m_nom.strip(), m_tipo.strip(), m_prop, m_costo_alq if m_prop == "ALQUILADA" else 0)
                                )
                                st.success(f"Máquina '{m_nom}' agregada.")
                                st.rerun()
                            else:
                                st.error("Escribe el nombre de la máquina.")

                if not df_maqs.empty:
                    with st.expander("Editar"):
                        with st.form("form_editar_maquina"):
                            maq_edit_sel = st.selectbox("Selecciona la Máquina a Editar", df_maqs["nombre"].tolist())
                            maq_data = ejecutar_consulta("SELECT tipo, tipo_propiedad, costo_hora_alquiler FROM maquinas WHERE nombre = %s", (maq_edit_sel,))
                            t_act = maq_data.iloc[0]['tipo'] if not maq_data.empty else ""
                            p_act = maq_data.iloc[0]['tipo_propiedad'] if not maq_data.empty else "PROPIA"
                            c_act = float(maq_data.iloc[0]['costo_hora_alquiler']) if not maq_data.empty and maq_data.iloc[0]['costo_hora_alquiler'] else 0.0
                            
                            nuevo_nom_maq = st.text_input("Nuevo Nombre", value=maq_edit_sel)
                            nuevo_tipo_maq = st.text_input("Nuevo Tipo", value=t_act)
                            idx_p = ["PROPIA", "ALQUILADA"].index(p_act) if p_act in ["PROPIA", "ALQUILADA"] else 0
                            nuevo_prop_maq = st.selectbox("Nuevo Tipo Propiedad", ["PROPIA", "ALQUILADA"], index=idx_p)
                            nuevo_costo_maq = st.number_input("Nuevo Costo Hora Alquiler ($)", min_value=0.0, step=1000.0, value=c_act)
                            
                            if st.form_submit_button("Actualizar Máquina", type="primary", use_container_width=True):
                                ejecutar_comando(
                                    "UPDATE maquinas SET nombre = %s, tipo = %s, tipo_propiedad = %s, costo_hora_alquiler = %s WHERE nombre = %s",
                                    (nuevo_nom_maq.strip(), nuevo_tipo_maq.strip(), nuevo_prop_maq, nuevo_costo_maq if nuevo_prop_maq == "ALQUILADA" else 0, maq_edit_sel)
                                )
                                st.success("¡Máquina actualizada con éxito!")
                                st.rerun()

                    with st.expander("Eliminar"):
                        with st.form("form_del_maquina", clear_on_submit=True):
                            m_del = st.selectbox("Máquina a Borrar", df_maqs["nombre"].tolist())
                            if st.form_submit_button("Eliminar Máquina", type="primary", use_container_width=True):
                                ejecutar_comando("DELETE FROM maquinas WHERE nombre = %s", (m_del,))
                                st.success("Máquina eliminada.")
                                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        with tab_serv:
            st.subheader("🛠️ Administración de Servicios Prestados")
            try:
                df_serv = ejecutar_consulta("SELECT * FROM servicios_prestados ORDER BY id DESC")
                if not df_serv.empty:
                    st.dataframe(df_serv, use_container_width=True)
                with st.expander("Crear"):
                    with st.form("form_crear_serv", clear_on_submit=True):
                        nom_serv = st.text_input("Nombre del Servicio (Ej: PLEGADO, CORTE)")
                        if st.form_submit_button("Guardar Servicio", type="primary", use_container_width=True):
                            if nom_serv.strip():
                                ejecutar_comando("INSERT INTO servicios_prestados (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (nom_serv.upper().strip(),))
                                st.success("Servicio agregado.")
                                st.rerun()

                if not df_serv.empty:
                    with st.expander("Editar"):
                        with st.form("form_editar_serv"):
                            serv_edit_sel = st.selectbox("Selecciona el Servicio a Editar", df_serv["nombre"].tolist())
                            nuevo_nom_serv = st.text_input("Nuevo Nombre de Servicio", value=serv_edit_sel)
                            if st.form_submit_button("Actualizar Servicio", type="primary", use_container_width=True):
                                if nuevo_nom_serv.strip():
                                    ejecutar_comando("UPDATE servicios_prestados SET nombre = %s WHERE nombre = %s", (nuevo_nom_serv.upper().strip(), serv_edit_sel))
                                    st.success("¡Servicio actualizado!")
                                    st.rerun()

                    with st.expander("Eliminar"):
                        with st.form("form_del_serv", clear_on_submit=True):
                            serv_del = st.selectbox("Servicio a Borrar", df_serv["nombre"].tolist())
                            if st.form_submit_button("Eliminar Servicio", type="primary", use_container_width=True):
                                ejecutar_comando("DELETE FROM servicios_prestados WHERE nombre = %s", (serv_del,))
                                st.success("Servicio eliminado.")
                                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    with tab_ref:
        st.subheader("📄 Gestión de Referencias (Catálogo Base)")
        try:
            df_refs = ejecutar_consulta("SELECT * FROM referencias")
            clientes_db = ejecutar_consulta("SELECT nombre FROM clientes")
            lista_clientes = clientes_db['nombre'].tolist() if not clientes_db.empty else []
            if not df_refs.empty:
                st.dataframe(df_refs, use_container_width=True)
            with st.expander("Crear"):
                with st.form("form_crear_ref", clear_on_submit=True):
                    r_cod = st.text_input("Código Referencia (Ej: REF-001)")
                    r_desc = st.text_input("Descripción del Producto")
                    r_cliente = st.selectbox("Cliente Asociado", lista_clientes if lista_clientes else ["SIN CLIENTE REGISTRADO"])
                    if st.form_submit_button("Guardar Referencia", type="primary", use_container_width=True):
                        if r_cod.strip() and r_cliente != "SIN CLIENTE REGISTRADO":
                            ejecutar_comando("INSERT INTO referencias (codigo, descripcion, cliente) VALUES (%s, %s, %s)", (r_cod.upper().strip(), r_desc, r_cliente))
                            st.success("Referencia guardada.")
                            st.rerun()

            if not df_refs.empty and rol == "admin":
                with st.expander("Editar"):
                    with st.form("form_editar_ref"):
                        ref_edit_sel = st.selectbox("Selecciona la Referencia a Editar", df_refs["codigo"].tolist())
                        ref_data = ejecutar_consulta("SELECT descripcion, cliente FROM referencias WHERE codigo = %s", (ref_edit_sel,))
                        d_act = ref_data.iloc[0]['descripcion'] if not ref_data.empty else ""
                        cli_act = ref_data.iloc[0]['cliente'] if not ref_data.empty else ""
                        
                        idx_c = lista_clientes.index(cli_act) if cli_act in lista_clientes else 0
                        nuevo_cod_ref = st.text_input("Nuevo Código de Referencia", value=ref_edit_sel)
                        nuevo_desc_ref = st.text_input("Nueva Descripción", value=d_act)
                        nuevo_cli_ref = st.selectbox("Nuevo Cliente Asociado", lista_clientes if lista_clientes else ["SIN CLIENTE"], index=idx_c)
                        
                        if st.form_submit_button("Actualizar Referencia", type="primary", use_container_width=True):
                            ejecutar_comando("UPDATE referencias SET codigo = %s, descripcion = %s, cliente = %s WHERE codigo = %s", (nuevo_cod_ref.upper().strip(), nuevo_desc_ref, nuevo_cli_ref, ref_edit_sel))
                            st.success("¡Referencia actualizada!")
                            st.rerun()

                with st.expander("Eliminar"):
                    with st.form("form_del_ref", clear_on_submit=True):
                        r_del = st.selectbox("Referencia a Borrar", df_refs["codigo"].tolist())
                        if st.form_submit_button("Eliminar Referencia", type="primary", use_container_width=True):
                            ejecutar_comando("DELETE FROM referencias WHERE codigo = %s", (r_del,))
                            st.success("Referencia eliminada.")
                            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    with tab_rep:
        st.subheader("📊 Centro de Reportes Gerenciales y de Producción")
        tipo_reporte_gerencial = st.radio(
            "Selecciona la vista de reporte:", 
            ["Reporte de Producción", "Costos Máquinas Alquiladas"], 
            horizontal=True
        )
        
        st.write("---")
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            filtro_periodo = st.selectbox("Filtrar Período:", ["Histórico (Todo)", "Diario", "Semanal", "Mensual"])
        with c_p2:
            if filtro_periodo == "Diario":
                fecha_filtro = st.date_input("Selecciona el Día", value=(datetime.now() - timedelta(hours=5)).date())
            elif filtro_periodo == "Semanal":
                fecha_filtro = st.date_input("Selecciona una fecha de la Semana", value=(datetime.now() - timedelta(hours=5)).date())
            elif filtro_periodo == "Mensual":
                mes_opcion = st.selectbox("Selecciona el Mes", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=(datetime.now() - timedelta(hours=5)).month - 1)
                anio_opcion = st.number_input("Año", min_value=2024, max_value=2030, value=(datetime.now() - timedelta(hours=5)).year)

        if tipo_reporte_gerencial == "Reporte de Producción":
            st.markdown("### 📥 Reporte de Producción en Columnas Separadas para Excel")
            try:
                df_produccion_raw = ejecutar_consulta("SELECT * FROM registro_produccion ORDER BY id DESC")
                if not df_produccion_raw.empty:
                    if 'fecha_registro' in df_produccion_raw.columns:
                        df_produccion_raw['dt'] = pd.to_datetime(df_produccion_raw['fecha_registro']).dt.date
                    else:
                        df_produccion_raw['dt'] = (datetime.now() - timedelta(hours=5)).date()

                    if filtro_periodo == "Diario":
                        df_produccion_raw = df_produccion_raw[df_produccion_raw['dt'] == fecha_filtro]
                    elif filtro_periodo == "Semanal":
                        inicio_sem = pd.to_datetime(fecha_filtro) - timedelta(days=pd.to_datetime(fecha_filtro).weekday())
                        fin_sem = inicio_sem + timedelta(days=6)
                        df_produccion_raw = df_produccion_raw[(df_produccion_raw['dt'] >= inicio_sem.date()) & (df_produccion_raw['dt'] <= fin_sem.date())]
                    elif filtro_periodo == "Mensual":
                        meses_dict = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}
                        m_num = meses_dict[mes_opcion]
                        df_produccion_raw = df_produccion_raw[(pd.to_datetime(df_produccion_raw['dt']).dt.month == m_num) & (pd.to_datetime(df_produccion_raw['dt']).dt.year == anio_opcion)]

                    if not df_produccion_raw.empty:
                        df_final = generar_reporte_produccion_excel(df_produccion_raw)
                        st.dataframe(df_final, use_container_width=True)
                        buffer_prod = io.BytesIO()
                        with pd.ExcelWriter(buffer_prod, engine='openpyxl') as writer:
                            df_final.to_excel(writer, index=False, sheet_name='Reporte_Produccion')
                        st.download_button(
                            label="📥 Descargar Reporte de Producción Filtrado (Excel)",
                            data=buffer_prod.getvalue(),
                            file_name=f"reporte_produccion_{filtro_periodo.lower()}_{(datetime.now() - timedelta(hours=5)).strftime('%Y-%m-%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    else:
                        st.info(f"No hay registros de producción para el período seleccionado ({filtro_periodo}).")
                        
                    with st.expander("🧹 Limpiar o Borrar Registros de Producción Antiguos"):
                        with st.form("form_limpiar_prod"):
                            reg_produccion_ids = df_produccion_raw['id'].tolist() if 'id' in df_produccion_raw.columns else []
                            id_a_borrar = st.selectbox("Selecciona el ID de Registro de Producción a Borrar", reg_produccion_ids)
                            if st.form_submit_button("Eliminar este Registro Antiguo", type="primary", use_container_width=True):
                                ejecutar_comando("DELETE FROM registro_produccion WHERE id = %s", (id_a_borrar,))
                                st.success(f"Registro de producción #{id_a_borrar} eliminado con éxito.")
                                st.rerun()
                else:
                    st.info("No hay registros de producción disponibles.")
            except Exception as e:
                st.error(f"Error: {e}")

        else:
            st.markdown("### 💰 Control de Uso y Costos de Máquinas Alquiladas")
            try:
                query_alq = """
                    SELECT R.id, R.fecha_registro, R.operario_nombre, R.maquina, R.horas_trabajadas, 
                    M.costo_hora_alquiler, (R.horas_trabajadas * M.costo_hora_alquiler) AS costo_total
                    FROM registro_produccion R
                    JOIN maquinas M ON R.maquina = M.nombre
                    WHERE M.tipo_propiedad = 'ALQUILADA'
                    ORDER BY R.id DESC
                """
                df_alq = ejecutar_consulta(query_alq)
                if not df_alq.empty:
                    df_alq['dt'] = pd.to_datetime(df_alq['fecha_registro']).dt.date
                    df_alq['fecha_registro'] = df_alq['dt'].astype(str)
                    
                    if filtro_periodo == "Diario":
                        df_alq = df_alq[df_alq['dt'] == fecha_filtro]
                    elif filtro_periodo == "Semanal":
                        inicio_sem = pd.to_datetime(fecha_filtro) - timedelta(days=pd.to_datetime(fecha_filtro).weekday())
                        fin_sem = inicio_sem + timedelta(days=6)
                        df_alq = df_alq[(df_alq['dt'] >= inicio_sem.date()) & (df_alq['dt'] <= fin_sem.date())]
                    elif filtro_periodo == "Mensual":
                        meses_dict = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}
                        m_num = meses_dict[mes_opcion]
                        df_alq = df_alq[(pd.to_datetime(df_alq['dt']).dt.month == m_num) & (pd.to_datetime(df_alq['dt']).dt.year == anio_opcion)]

                    if not df_alq.empty:
                        tot_horas = df_alq['horas_trabajadas'].sum()
                        tot_costo = df_alq['costo_total'].sum()
                        col_m1, col_m2 = st.columns(2)
                        col_m1.metric("Total Horas Alquiladas", f"{tot_horas:.2f} hrs")
                        col_m2.metric("Costo Total Acumulado", f"${tot_costo:,.2f}")
                        st.dataframe(df_alq.drop(columns=['dt']), use_container_width=True)

                        buffer_alq = io.BytesIO()
                        with pd.ExcelWriter(buffer_alq, engine='openpyxl') as writer:
                            df_alq.drop(columns=['dt']).to_excel(writer, index=False, sheet_name='Costos_Maquinas_Alquiladas')
                        st.download_button(
                            label="📥 Descargar Costos de Máquinas Filtrado (Excel)",
                            data=buffer_alq.getvalue(),
                            file_name=f"costos_maquinas_{filtro_periodo.lower()}_{(datetime.now() - timedelta(hours=5)).strftime('%Y-%m-%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    else:
                        st.info(f"No hay registros de máquinas alquiladas para el período seleccionado ({filtro_periodo}).")
                else:
                    st.info("No hay registros de máquinas alquiladas.")
            except Exception as e:
                st.warning(f"Información: {e}")

    with tab_ent:
        st.subheader("🚀 Registrar Salida de Insumo / Material a Operario")
        try:
            ops_df = ejecutar_consulta("SELECT nombre FROM usuarios WHERE rol = 'operario'")
            ops = ops_df['nombre'].tolist() if not ops_df.empty else []
            mats = ejecutar_consulta("SELECT codigo, nombre, cantidad, tipo FROM inventario")
            if ops and not mats.empty:
                with st.form("form_entregas", clear_on_submit=True):
                    op_sel = st.selectbox("Operario Destino", ops)
                    mat_sel = st.selectbox("Ítem en Inventario", mats['nombre'].tolist())
                    cant = st.number_input("Cantidad a Entregar", min_value=1, value=1)
                    if st.form_submit_button("Registrar Salida y Descontar", type="primary", use_container_width=True):
                        row = mats[mats['nombre'] == mat_sel].iloc[0]
                        ejecutar_comando(
                            "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (%s, %s, %s, %s, %s, 'ENTREGADO')",
                            ((datetime.now() - timedelta(hours=5)).strftime("%Y-%m-%d"), op_sel, row['codigo'], cant, row['tipo'])
                        )
                        ejecutar_comando("UPDATE inventario SET cantidad = cantidad - %s WHERE codigo = %s", (cant, row['codigo']))
                        st.success("Salida registrada con éxito.")
                        st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    with tab_herramientas:
        st.subheader("🔨 Control y Préstamos de Herramientas")
        try:
            herramientas_db = ejecutar_consulta("SELECT codigo, nombre, cantidad FROM inventario WHERE tipo ILIKE '%HERRAMIENTA%'")
            if not herramientas_db.empty:
                st.dataframe(herramientas_db, use_container_width=True)
            else:
                st.info("No hay herramientas registradas con la clase 'HERRAMIENTA'.")
            
            ops_df = ejecutar_consulta("SELECT nombre FROM usuarios WHERE rol = 'operario'")
            ops = ops_df['nombre'].tolist() if not ops_df.empty else []
            
            if ops and not herramientas_db.empty:
                with st.expander("Registrar Préstamo o Reasignación"):
                    with st.form("form_prestar_herramienta", clear_on_submit=True):
                        op_her = st.selectbox("Operario Responsable", ops)
                        her_sel = st.selectbox("Herramienta a Prestar", herramientas_db['nombre'].tolist())
                        cant_her = st.number_input("Cantidad", min_value=1, value=1)
                        if st.form_submit_button("Registrar Préstamo", type="primary", use_container_width=True):
                            row_h = herramientas_db[herramientas_db['nombre'] == her_sel].iloc[0]
                            ejecutar_comando(
                                "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (%s, %s, %s, %s, 'HERRAMIENTA', 'PRESTADO')",
                                ((datetime.now() - timedelta(hours=5)).strftime("%Y-%m-%d"), op_her, row_h['codigo'], cant_her)
                            )
                            st.success("Préstamo registrado.")
                            st.rerun()

            st.write("---")
            st.write("#### Herramientas Actualmente Prestadas (Ver quién las tiene)")
            prestados = ejecutar_consulta("""
                SELECT c.id, c.fecha, c.operario, c.codigo_material, i.nombre as herramienta, c.cantidad, c.estado 
                FROM consumos c 
                JOIN usuarios u ON c.operario = u.nombre
                LEFT JOIN inventario i ON c.codigo_material = i.codigo 
                WHERE c.tipo ILIKE '%HERRAMIENTA%' AND c.estado = 'PRESTADO'
            """)
            if not prestados.empty:
                st.dataframe(prestados, use_container_width=True)
                
                with st.expander("Gestionar Devolución o Reasignación (Prestar a otro operario)"):
                    with st.form("form_gestionar_prestamo"):
                        id_prestamo_sel = st.selectbox("Selecciona el Registro de Préstamo", prestados['id'].tolist())
                        reg_actual = prestados[prestados['id'] == id_prestamo_sel].iloc[0]
                        st.info(f"Actual a cargo de: **{reg_actual['operario']}** | Herramienta: **{reg_actual['herramienta']}**")
                        
                        accion_her = st.radio("Acción a realizar:", ["Marcar como Devuelta", "Reasignar / Prestar a otro Operario"])
                        nuevo_operario = st.selectbox("Nuevo Operario Destino (Si reasignas)", ops)
                        
                        if st.form_submit_button("Aplicar Acción", type="primary", use_container_width=True):
                            if accion_her == "Marcar como Devuelta":
                                ejecutar_comando("UPDATE consumos SET estado = 'DEVUELTO' WHERE id = %s", (id_prestamo_sel,))
                                st.success("Herramienta marcada como devuelta.")
                                st.rerun()
                            else:
                                ejecutar_comando("UPDATE consumos SET estado = 'DEVUELTO' WHERE id = %s", (id_prestamo_sel,))
                                ejecutar_comando(
                                    "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (%s, %s, %s, %s, 'HERRAMIENTA', 'PRESTADO')",
                                    ((datetime.now() - timedelta(hours=5)).strftime("%Y-%m-%d"), nuevo_operario, reg_actual['codigo_material'], reg_actual['cantidad'])
                                )
                                st.success(f"Herramienta reasignada exitosamente a {nuevo_operario}.")
                                st.rerun()
            else:
                st.success("No hay herramientas pendientes de devolución.")
        except Exception as e:
            st.error(f"Error en herramientas: {e}")

    with tab_cargue:
        st.subheader("📥 Cargue Único de Ítems al Inventario")
        try:
            clases_df = ejecutar_consulta("SELECT nombre FROM clases_inventario")
            lista_clases = clases_df['nombre'].tolist() if not clases_df.empty else []
            if not lista_clases:
                st.warning("⚠️ Crea al menos una clase en la pestaña 'Clases' antes de cargar ítems.")
            else:
                with st.form("form_cargue_item", clear_on_submit=True):
                    c_cod = st.text_input("Código del Ítem (Ej: MAT-001)")
                    c_nom = st.text_input("Nombre del Ítem")
                    c_clase = st.selectbox("Clase / Categoría", lista_clases)
                    c_cant = st.number_input("Cantidad Inicial", min_value=0, value=10)
                    c_min = st.number_input("Stock Mínimo de Alerta", min_value=0, value=5)
                    if st.form_submit_button("Guardar Ítem en Inventario", type="primary", use_container_width=True):
                        if c_cod.strip() and c_nom.strip():
                            ejecutar_comando(
                                "INSERT INTO inventario (codigo, nombre, tipo, cantidad, stock_minimo) VALUES (%s, %s, %s, %s, %s)",
                                (c_cod.upper().strip(), c_nom.strip(), c_clase, c_cant, c_min)
                            )
                            st.success("Ítem cargado con éxito.")
                            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    with tab_inv_gen:
        st.subheader("📦 Inventario General de la Planta")
        try:
            inv_gen = ejecutar_consulta("SELECT codigo, nombre, tipo as clase, cantidad, stock_minimo FROM inventario")
            if not inv_gen.empty:
                st.dataframe(inv_gen, use_container_width=True)
                if rol == "admin":
                    with st.expander("Eliminar"):
                        with st.form("form_del_inv", clear_on_submit=True):
                            del_cod_gen = st.selectbox("Código a Eliminar", inv_gen["codigo"].tolist())
                            if st.form_submit_button("Confirmar Eliminación de Ítem", type="primary", use_container_width=True):
                                ejecutar_comando("DELETE FROM inventario WHERE codigo = %s", (del_cod_gen,))
                                st.success("Ítem eliminado del inventario.")
                                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    if rol == "admin":
        with tab_clases:
            st.subheader("🏷️ Administración de Clases de Inventario")
            try:
                clases_actuales = ejecutar_consulta("SELECT * FROM clases_inventario ORDER BY id DESC")
                if not clases_actuales.empty:
                    st.dataframe(clases_actuales, use_container_width=True)
                with st.expander("Crear"):
                    with st.form("form_crear_clase", clear_on_submit=True):
                        nueva_clase = st.text_input("Nombre de la Clase (Ej: HERRAMIENTA, MATERIA PRIMA)")
                        if st.form_submit_button("Guardar Clase", type="primary", use_container_width=True):
                            if nueva_clase.strip():
                                ejecutar_comando("INSERT INTO clases_inventario (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (nueva_clase.upper().strip(),))
                                st.success("Clase creada.")
                                st.rerun()

                if not clases_actuales.empty:
                    with st.expander("Editar"):
                        with st.form("form_editar_clase"):
                            clase_edit_sel = st.selectbox("Selecciona la Clase a Editar", clases_actuales["nombre"].tolist())
                            nueva_nombre_clase = st.text_input("Nuevo Nombre de Clase", value=clase_edit_sel)
                            if st.form_submit_button("Actualizar Clase", type="primary", use_container_width=True):
                                if nueva_nombre_clase.strip():
                                    ejecutar_comando("UPDATE clases_inventario SET nombre = %s WHERE nombre = %s", (nueva_nombre_clase.upper().strip(), clase_edit_sel))
                                    st.success("¡Clase actualizada!")
                                    st.rerun()

                    with st.expander("Eliminar"):
                        with st.form("form_del_clase", clear_on_submit=True):
                            clase_del = st.selectbox("Selecciona la Clase a Borrar", clases_actuales["nombre"].tolist())
                            if st.form_submit_button("Eliminar Clase", type="primary", use_container_width=True):
                                ejecutar_comando("DELETE FROM clases_inventario WHERE nombre = %s", (clase_del,))
                                st.success("Clase eliminada.")
                                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        with tab_clientes:
            st.subheader("👥 Administración de Clientes")
            try:
                clientes_df = ejecutar_consulta("SELECT * FROM clientes ORDER BY id DESC")
                if not clientes_df.empty:
                    st.dataframe(clientes_df, use_container_width=True)
                with st.expander("Crear"):
                    with st.form("form_crear_cliente", clear_on_submit=True):
                        nom_cliente = st.text_input("Razón Social / Nombre de la Empresa")
                        nit_cliente = st.text_input("NIT (Opcional)")
                        tel_cliente = st.text_input("Teléfono de Contacto (Opcional)")
                        if st.form_submit_button("Guardar Cliente", type="primary", use_container_width=True):
                            if nom_cliente.strip():
                                ejecutar_comando(
                                    "INSERT INTO clientes (nombre, nit, telefono) VALUES (%s, %s, %s) ON CONFLICT (nombre) DO NOTHING",
                                    (nom_cliente.strip(), nit_cliente.strip(), tel_cliente.strip())
                                )
                                st.success("Cliente agregado.")
                                st.rerun()

                if not clientes_df.empty:
                    with st.expander("Editar"):
                        with st.form("form_editar_cliente"):
                            cliente_edit_sel = st.selectbox("Selecciona el Cliente a Editar", clientes_df["nombre"].tolist())
                            datos_cli = ejecutar_consulta("SELECT nit, telefono FROM clientes WHERE nombre = %s", (cliente_edit_sel,))
                            nit_actual = datos_cli.iloc[0]['nit'] if not datos_cli.empty and datos_cli.iloc[0]['nit'] else ""
                            tel_actual = datos_cli.iloc[0]['telefono'] if not datos_cli.empty and datos_cli.iloc[0]['telefono'] else ""
                            
                            nuevo_nom_cli = st.text_input("Nueva Razón Social", value=cliente_edit_sel)
                            nuevo_nit_cli = st.text_input("Nuevo NIT", value=nit_actual)
                            nuevo_tel_cli = st.text_input("Nuevo Teléfono", value=tel_actual)
                            
                            if st.form_submit_button("Actualizar Cliente", type="primary", use_container_width=True):
                                if nuevo_nom_cli.strip():
                                    ejecutar_comando(
                                        "UPDATE clientes SET nombre = %s, nit = %s, telefono = %s WHERE nombre = %s",
                                        (nuevo_nom_cli.strip(), nuevo_nit_cli.strip(), nuevo_tel_cli.strip(), cliente_edit_sel)
                                    )
                                    st.success("¡Cliente actualizado!")
                                    st.rerun()

                    with st.expander("Eliminar"):
                        with st.form("form_del_cliente", clear_on_submit=True):
                            cliente_del = st.selectbox("Selecciona el Cliente a Borrar", clientes_df["nombre"].tolist(), key="del_cli_key")
                            if st.form_submit_button("Eliminar Cliente", type="primary", use_container_width=True):
                                ejecutar_comando("DELETE FROM clientes WHERE nombre = %s", (cliente_del,))
                                st.success("Cliente eliminado.")
                                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        with tab_usu:
            st.subheader("⚙️ Gestión y Seguridad de Usuarios del Sistema")
            try:
                users_df = ejecutar_consulta("SELECT id, username, nombre, rol FROM usuarios ORDER BY id DESC")
                if not users_df.empty:
                    st.dataframe(users_df, use_container_width=True)
                with st.expander("Crear"):
                    with st.form("form_crear_usuario", clear_on_submit=True):
                        u_user = st.text_input("Usuario (Login)")
                        u_pass = st.text_input("Contraseña", type="password")
                        u_nom = st.text_input("Nombre Completo")
                        u_rol = st.selectbox("Rol en Planta", ["operario", "produccion", "admin"])
                        if st.form_submit_button("Guardar Usuario", type="primary", use_container_width=True):
                            if u_user.strip() and u_pass.strip() and u_nom.strip():
                                ejecutar_comando("INSERT INTO usuarios (username, password, nombre, rol) VALUES (%s, %s, %s, %s)", (u_user.strip(), u_pass, u_nom.strip(), u_rol))
                                st.success("Usuario creado.")
                                st.rerun()

                if not users_df.empty:
                    with st.expander("Editar"):
                        with st.form("form_editar_usuario"):
                            edit_user_sel = st.selectbox("Selecciona el Usuario a Editar", users_df["username"].tolist())
                            user_actual = ejecutar_consulta("SELECT nombre, rol FROM usuarios WHERE username = %s", (edit_user_sel,))
                            nombre_actual = user_actual.iloc[0]['nombre'] if not user_actual.empty else ""
                            rol_actual = user_actual.iloc[0]['rol'] if not user_actual.empty else "operario"
                            idx_rol = ["operario", "produccion", "admin"].index(rol_actual) if rol_actual in ["operario", "produccion", "admin"] else 0
                            
                            nuevo_nombre = st.text_input("Nombre Completo", value=nombre_actual)
                            nueva_pass = st.text_input("Nueva Contraseña (Dejar en blanco si no cambia)", type="password")
                            nuevo_rol = st.selectbox("Nuevo Rol en Planta", ["operario", "produccion", "admin"], index=idx_rol)
                            
                            if st.form_submit_button("Actualizar Usuario", type="primary", use_container_width=True):
                                if nueva_pass.strip():
                                    ejecutar_comando("UPDATE usuarios SET nombre = %s, password = %s, rol = %s WHERE username = %s", (nuevo_nombre.strip(), nueva_pass, nuevo_rol, edit_user_sel))
                                else:
                                    ejecutar_comando("UPDATE usuarios SET nombre = %s, rol = %s WHERE username = %s", (nuevo_nombre.strip(), nuevo_rol, edit_user_sel))
                                st.success("¡Usuario actualizada!")
                                st.rerun()

                    with st.expander("Eliminar"):
                        with st.form("form_del_usuario", clear_on_submit=True):
                            usuario_del = st.selectbox("Selecciona el Usuario a Borrar", users_df["username"].tolist(), key="del_u_key")
                            if st.form_submit_button("Eliminar Usuario", type="primary", use_container_width=True):
                                if usuario_del == st.session_state["username"]:
                                    st.error("No puedes eliminar tu propia cuenta activa.")
                                else:
                                    ejecutar_comando("DELETE FROM usuarios WHERE username = %s", (usuario_del,))
                                    st.success("Usuario eliminado.")
                                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
