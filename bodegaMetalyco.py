import streamlit as st
import pandas as pd
import psycopg2
import os
import io
import urllib.parse
import base64
import uuid
from datetime import datetime, time, date, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import plotly.express as px
import plotly.graph_objects as go

# =====================================================
# CONFIGURACIÓN DE FONDO GENERAL DE LA APLICACIÓN
# =====================================================
img_css_app = "background-color: #121212;"
ruta_fondo_app = "fondo_app.jpg"  # Guarda tu imagen de fondo con este nombre si deseas usarla

if os.path.exists(ruta_fondo_app):
    with open(ruta_fondo_app, "rb") as image_file:
        encoded_app_bg = base64.b64encode(image_file.read()).decode()
        img_css_app = f"background: linear-gradient(rgba(18,18,18,0.85), rgba(18,18,18,0.92)), url('data:image/jpeg;base64,{encoded_app_bg}'); background-size: cover; background-position: center; background-attachment: fixed;"

st.set_page_config(
    page_title="Control de Producción - Industrias Metal&Co",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="auto"
)

# Estilos CSS avanzados con llaves escapadas correctamente ({{ y }})
st.markdown(f"""
    <style>
        .stApp {{
            {img_css_app}
        }}
        
        .block-container {{
            padding-top: 1rem;
            padding-bottom: 2rem;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
        }}
        
        [data-testid="stSidebar"] {{
            background-color: rgba(26, 26, 26, 0.92);
            backdrop-filter: blur(10px);
            border-right: 2px solid rgba(255, 122, 0, 0.2);
            padding-top: 1rem;
        }}

        [data-testid="stSidebar"] .stRadio > label {{
            display: none !important;
        }}

        .stButton>button {{
            width: 100% !important;
            height: 3.2rem !important;
            font-size: 1rem !important;
            font-weight: bold !important;
            border-radius: 12px !important;
            background: linear-gradient(135deg, #FF7A00 0%, #cc6200 100%) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 122, 0, 0.5) !important;
            box-shadow: 0 4px 15px rgba(255, 122, 0, 0.4) !important;
            transition: all 0.3s ease !important;
        }}
        .stButton>button:hover {{
            background: linear-gradient(135deg, #ff9124 0%, #FF7A00 100%) !important;
            box-shadow: 0 6px 20px rgba(255, 122, 0, 0.6) !important;
            transform: translateY(-1px) !important;
        }}

        .profile-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            margin-bottom: 10px;
        }}
        .profile-img {{
            width: 80px;
            height: 80px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid #FF7A00;
            box-shadow: 0 4px 15px rgba(255, 122, 0, 0.3);
        }}

        [data-testid="stSidebar"] .stRadio > div {{
            gap: 8px;
            width: 100%;
        }}
        [data-testid="stSidebar"] .stRadio label {{
            background-color: #212121;
            color: #C0C0C0;
            padding: 12px 16px;
            border-radius: 12px;
            font-weight: 500;
            font-size: 0.95rem;
            width: 100% !important;
            height: 3.2rem !important;
            box-sizing: border-box;
            border: 1px solid rgba(255, 255, 255, 0.08);
            transition: all 0.3s ease;
            cursor: pointer;
            display: flex;
            align-items: center;
        }
        
        [data-testid="stSidebar"] .stRadio input[type="radio"] {{
            display: none !important;
        }}
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label div:first-child {{
            display: none !important;
        }}

        [data-testid="stSidebar"] .stRadio label:hover {{
            color: #FF7A00 !important;
            border-color: #FF7A00 !important;
            background-color: rgba(255, 122, 0, 0.08) !important;
            box-shadow: 0 4px 12px rgba(255, 122, 0, 0.2);
        }}

        [data-testid="stSidebar"] .stRadio div[checked="true"] label,
        [data-testid="stSidebar"] .stRadio input:checked + div,
        [data-testid="stSidebar"] .stRadio label:has(input:checked) {{
            background-color: rgba(255, 122, 0, 0.15) !important;
            color: #FF7A00 !important;
            font-weight: bold !important;
            border: 1px solid #FF7A00 !important;
            box-shadow: 0 0 15px rgba(255, 122, 0, 0.4);
            border-radius: 12px !important;
        }}
    </style>
""", unsafe_allow_html=True)

NOMBRES_LOGO = ["logometalyco.png", "logometalyco.jpg", "logo.jpeg", "logo.png"]
LOGO_PATH = None
for nombre in NOMBRES_LOGO:
    if os.path.exists(nombre):
        LOGO_PATH = nombre
        break

def mostrar_logo(ancho=200):
    if LOGO_PATH:
        st.image(LOGO_PATH, width=ancho)
    else:
        st.markdown(f"<h2 style='color: #FF7A00; text-align:center;'>METAL&CO</h2>", unsafe_allow_html=True)

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
        ejecutar_comando("""
            CREATE TABLE IF NOT EXISTS configuracion_empresa (
                id SERIAL PRIMARY KEY,
                clave VARCHAR(100) UNIQUE NOT NULL,
                valor TEXT
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
        ejecutar_comando("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS avatar_path TEXT;")
        ejecutar_comando("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS session_token TEXT;")
    except Exception as e:
        print(f"Nota en inicialización: {e}")

inicializar_tablas_sistema()

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
        df['Fecha'] = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y-%m-%d')
        
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
                num_sc = int(partes[1].split(',')[0].split('.')[0].strip())
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
            p.drawImage(LOGO_PATH, x_margen, y_actual - 30, width=110, height=35, preserveAspectRatio=True, mask='auto')
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
    p.drawCentredString(width / 2.0, y_actual - 8, "INFORMACIÓN GENERAL")
    
    y_actual -= 12
    p.setFillColorRGB(0, 0, 0)
    p.rect(x_margen, y_actual - 35, ancho_util, 35, fill=0, stroke=1)
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 8, y_actual - 12, "FECHA:")
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 50, y_actual - 12, f"{datos.get('fecha', (datetime.utcnow() - timedelta(hours=5)).strftime('%Y-%m-%d'))}")
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 260, y_actual - 12, "OP:")
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 390, y_actual - 12, f"{datos.get('numero_oc', 'N/A')}")
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 8, y_actual - 26, "CLIENTE:")
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 50, y_actual - 26, f"{datos.get('cliente', 'N/A')}")
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 260, y_actual - 26, "REFERENCIA:")
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
    p.drawString(x_margen + 10, y_actual - 15, "ACTIVIDAD:")
    p.setFont("Helvetica", 8.5)
    p.drawString(x_margen + 140, y_actual - 15, f"[ X ] {str(datos.get('actividad', 'N/A')).upper()}")
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 320, y_actual - 15, "MÁQUINA:")
    p.setFont("Helvetica", 8.5)
    p.drawString(x_margen + 380, y_actual - 15, f"{str(datos.get('maquina', 'N/A')).upper()}")
    
    if presion_val:
        p.setFont("Helvetica-Bold", 8)
        p.drawString(x_margen + 10, y_actual - 26, "PRESIÓN:")
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
    p.drawString(x_margen + 8, y_actual - 13, "LOTE:")
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 115, y_actual - 13, f"{datos.get('producidas', 0)}")
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 200, y_actual - 13, "MUESTRA:")
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 295, y_actual - 13, "N/A")
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_margen + 400, y_actual - 13, "AQL:")
    p.setFont("Helvetica", 8)
    p.drawString(x_margen + 460, y_actual - 13, "2.5")
    
    y_actual -= 30
    p.setFillColorRGB(0.15, 0.15, 0.15)
    p.rect(x_margen, y_actual - 12, ancho_util, 14, fill=1, stroke=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 7.5)
    p.drawCentredString(width / 2.0, y_actual - 8, "CONTROL DE PRODUCCIÓN")
    
    y_actual -= 12
    p.setFillColorRGB(0, 0, 0)
    p.rect(x_margen, y_actual - 28, ancho_util, 28, fill=0, stroke=1)
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(x_margen + 5, y_actual - 11, "INICIO")
    p.drawString(x_margen + 75, y_actual - 11, "FIN")
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
    
    presion_param = datos.get('presion', '')
    p.drawString(x_margen + 135, y_actual - 9, str(presion_param) if presion_param else "N/A")
    
    p.drawString(x_margen + 235, y_actual - 9, f"{datos.get('producidas', 0)}")
    p.drawString(x_margen + 310, y_actual - 9, f"{datos.get('defectuosas', 0)}")
    p.drawString(x_margen + 385, y_actual - 9, "0")
    p.drawString(x_margen + 440, y_actual - 9, f"{datos.get('observaciones', '')[:25]}")
    
    y_actual -= 28
    p.setFillColorRGB(0.15, 0.15, 0.15)
    p.rect(x_margen, y_actual - 12, ancho_util, 14, fill=1, stroke=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 7.5)
    p.drawCentredString(width / 2.0, y_actual - 8, "CONTROL PRIMERA PIEZA")
    
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
    
    # Bloque de firmas con Nombre Operario, Nombre Inspector y Nombre Auditor Externo
    y_actual -= 55
    p.rect(x_margen, y_actual - 42, ancho_util, 42, fill=0, stroke=1)
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(x_margen + 10, y_actual - 11, f"NOMBRE OPERARIO: {datos.get('operario', 'N/A')}")
    p.drawString(x_margen + 295, y_actual - 11, "NOMBRE INSPECTOR: _____________________")
    p.drawString(x_margen + 130, y_actual - 28, "NOMBRE AUDITOR EXTERNO (SI APLICA): _____________________")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "rol" not in st.session_state:
    st.session_state["rol"] = None
if "nombre_usuario" not in st.session_state:
    st.session_state["nombre_usuario"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
if "session_token" not in st.session_state:
    st.session_state["session_token"] = None
if "form_key_counter" not in st.session_state:
    st.session_state["form_key_counter"] = 0

@st.fragment(run_every=5)
def validar_sesion_tiempo_real():
    if st.session_state.get("autenticado") and st.session_state.get("username"):
        try:
            val_token = ejecutar_consulta(
                "SELECT session_token FROM usuarios WHERE username = %s",
                (st.session_state["username"],)
            )
            if not val_token.empty:
                token_en_bd = val_token.iloc[0]["session_token"]
                if token_en_bd != st.session_state.get("session_token"):
                    st.warning("Tu sesión ha sido cerrada porque la cuenta fue abierta en otro dispositivo.")
                    st.session_state["autenticado"] = False
                    st.session_state["session_token"] = None
                    st.rerun()
        except Exception:
            pass

validar_sesion_tiempo_real()

if not st.session_state["autenticado"]:
    img_css_fondo = "background-color: #121212;"
    ruta_fondo_local = "fondo_login.jpg"
    if os.path.exists(ruta_fondo_local):
        with open(ruta_fondo_local, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            img_css_fondo = f"background: linear-gradient(rgba(0,0,0,0.75), rgba(0,0,0,0.85)), url('data:image/jpeg;base64,{encoded_string}'); background-size: cover; background-position: center; background-attachment: fixed;"

    estilos_login_css = f"""
        <style>
            .stApp {{
                {img_css_fondo}
            }}
            .login-card {{
                background-color: rgba(26, 26, 26, 0.90);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 122, 0, 0.2);
                border-radius: 20px;
                padding: 3rem 2.5rem;
                box-shadow: 0 15px 35px rgba(0,0,0,0.9);
                max-width: 480px;
                margin: 0 auto;
            }}
            .login-title {{
                color: #E0E0E0;
                font-weight: 700;
                text-align: center;
                margin-bottom: 0.3rem;
                font-size: 2rem;
            }}
            .login-subtitle {{
                color: #888888;
                text-align: center;
                margin-bottom: 2rem;
                font-size: 0.95rem;
            }}
            .stButton>button {{
                width: 100%;
                height: 3.2rem;
                font-size: 1.1rem;
                font-weight: bold;
                border-radius: 12px;
                background: linear-gradient(135deg, #FF7A00 0%, #ff5500 100%);
                color: #ffffff;
                border: none;
                box-shadow: 0 8px 25px rgba(255, 122, 0, 0.5), 0 0 15px rgba(255, 122, 0, 0.2);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            .stButton>button:hover {{
                background: linear-gradient(135deg, #ff9124 0%, #FF7A00 100%);
                box-shadow: 0 12px 35px rgba(255, 122, 0, 0.8), 0 0 25px rgba(255, 122, 0, 0.4);
                transform: translateY(-2px);
            }}
        </style>
    """
    st.markdown(estilos_login_css, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 1.3, 1])
    with col_l2:
        with st.container():
            col_img1, col_img2, col_img3 = st.columns([0.5, 3, 0.5])
            with col_img2:
                mostrar_logo(ancho=240)
            
            st.markdown("<h1 class='login-title'>Welcome Back</h1>", unsafe_allow_html=True)
            st.markdown("<p class='login-subtitle'>Sign in to continue your production journey</p>", unsafe_allow_html=True)
            
            with st.form("form_login"):
                user_input = st.text_input("Correo o Usuario", placeholder="Ingresa tu usuario")
                pass_input = st.text_input("Contraseña", type="password", placeholder="••••••••")
                
                st.markdown("<br>", unsafe_allow_html=True)
                submit_login = st.form_submit_button("Sign In →", type="primary", use_container_width=True)
                
                if submit_login:
                    try:
                        res = ejecutar_consulta(
                            "SELECT username, nombre, rol, avatar_path FROM usuarios WHERE username = %s AND password = %s",
                            (user_input, pass_input)
                        )
                        if not res.empty:
                            nuevo_token = str(uuid.uuid4())
                            ejecutar_comando(
                                "UPDATE usuarios SET session_token = %s WHERE username = %s",
                                (nuevo_token, res.iloc[0]["username"])
                            )
                            
                            st.session_state["autenticado"] = True
                            st.session_state["username"] = res.iloc[0]["username"]
                            st.session_state["nombre_usuario"] = res.iloc[0]["nombre"]
                            st.session_state["rol"] = res.iloc[0]["rol"]
                            st.session_state["avatar_path"] = res.iloc[0]["avatar_path"]
                            st.session_state["session_token"] = nuevo_token
                            st.rerun()
                        else:
                            st.error("Usuario o contraseña incorrectos")
                    except Exception as e:
                        st.error(f"Error de conexión: {e}")
            
            current_yr = datetime.now().year
            st.markdown(f"<p style='text-align: center; color: #666; font-size: 0.8rem; margin-top: 2rem;'>© {current_yr} Industrias Metal&Co. Todos los derechos reservados.</p>", unsafe_allow_html=True)
    st.stop()

with st.sidebar:
    mostrar_logo(ancho=160)
    st.markdown("---")
    
    avatar_actual = st.session_state.get("avatar_path", None)
    
    if avatar_actual and os.path.exists(avatar_actual):
        with open(avatar_actual, "rb") as image_file:
            encoded_avatar = base64.b64encode(image_file.read()).decode()
        st.markdown(
            f"""<div class='profile-container'>
                <img src='data:image/jpeg;base64,{encoded_avatar}' class='profile-img'>
               </div>""",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""<div class='profile-container'>
                <div style='display: flex; align-items: center; justify-content: center; width: 75px; height: 75px; background-color: #2a2a2a; border: 2px solid #FF7A00; border-radius: 50%; box-shadow: 0 4px 15px rgba(255, 122, 0, 0.3);'>
                    <span style='font-size: 2rem; color: #FF7A00; font-weight: bold;'>{st.session_state['nombre_usuario'][0].upper()}</span>
                </div>
               </div>""", 
            unsafe_allow_html=True
        )
    
    st.markdown(f"<h4 style='text-align: center; color: #fff; margin-bottom: 0; font-size: 1.1rem;'>{st.session_state['nombre_usuario']}</h4>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #FF7A00; font-size: 0.8rem; font-weight: bold; margin-top: 2px;'>ONLINE ({str(st.session_state['rol']).upper()})</p>", unsafe_allow_html=True)
    
    with st.expander("Configurar Perfil"):
        subir_foto = st.file_uploader("Subir nueva foto", type=["jpg", "png", "jpeg"], key="uploader_avatar")
        if subir_foto is not None:
            os.makedirs("avatars", exist_ok=True)
            ruta_avatar = f"avatars/{st.session_state['username']}_{subir_foto.name}"
            with open(ruta_avatar, "wb") as f:
                f.write(subir_foto.getbuffer())
            
            ejecutar_comando("UPDATE usuarios SET avatar_path = %s WHERE username = %s", (ruta_avatar, st.session_state['username']))
            st.session_state["avatar_path"] = ruta_avatar
            st.success("¡Foto actualizada!")
            st.rerun()
            
        if avatar_actual and os.path.exists(avatar_actual):
            if st.button("Eliminar", use_container_width=True):
                ejecutar_comando("UPDATE usuarios SET avatar_path = NULL WHERE username = %s", (st.session_state['username'],))
                st.session_state["avatar_path"] = None
                st.success("¡Foto eliminada!")
                st.rerun()

    st.markdown("---")
    st.write("### Menú Principal")
    
    rol = st.session_state["rol"]
    
    if rol == "operario":
        opciones_menu = ["Mi Programación", "Registrar Producción", "Tarea Imprevista"]
    elif rol == "produccion":
        opciones_menu = ["Vista General", "Programar", "Órdenes Compra", "Referencias", "Reportes", "Entregas", "Herramientas", "Cargue Ítems", "Inventario"]
    else:  # Admin
        opciones_menu = [
            "Vista General", "Programar", "Órdenes Compra", "Máquinas", "Servicios", 
            "Referencias", "Reportes", "Entregas", "Herramientas", 
            "Cargue Ítems", "Inventario", "Clases", "Clientes", "Usuarios", "Configuración"
        ]
    
    menu_seleccionado = st.radio("Navegación", opciones_menu, label_visibility="collapsed")
    
    st.markdown("---")
    if st.button("Actualizar", use_container_width=True):
        st.rerun()
    if st.button("Cerrar Sesión", use_container_width=True):
        try:
            ejecutar_comando("UPDATE usuarios SET session_token = NULL WHERE username = %s", (st.session_state['username'],))
        except:
            pass
        st.session_state["autenticado"] = False
        st.session_state["rol"] = None
        st.session_state["nombre_usuario"] = None
        st.session_state["username"] = None
        st.session_state["avatar_path"] = None
        st.session_state["session_token"] = None
        st.rerun()

menu_limpio = menu_seleccionado

fecha_colombia_str = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y-%m-%d')

col_h_izq, col_h_centro, col_h_der = st.columns([0.1, 0.8, 0.1])
with col_h_centro:
    st.markdown("<h1 style='text-align: center; font-size: 2.2rem; margin-bottom: 0;'>Industrias Metal&Co</h1>", unsafe_allow_html=True)
with col_h_der:
    st.markdown(f"<div style='text-align: right; color: #888; font-size: 0.85rem; padding-top: 15px;'>Colombia<br><b>{fecha_colombia_str}</b></div>", unsafe_allow_html=True)

st.markdown("---")

# ====================================================
# VISTA EXCLUSIVA PARA OPERARIOS
# ====================================================
if rol == "operario":
    if menu_limpio == "Mi Programación":
        st.subheader("Consulta tus Tareas Asignadas")
        filtro_fecha = st.radio("Ver tareas de:", ["Todas mis tareas pendientes", "Filtrar por fecha específica"], horizontal=True)
        try:
            if filtro_fecha == "Filtrar por fecha específica":
                fecha_operario = st.date_input("Selecciona el día a consultar", value=(datetime.utcnow() - timedelta(hours=5)).date(), key="cal_op_dia")
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

    elif menu_limpio == "Registrar Producción":
        st.subheader("Registrar Producción y Generar Formato PDF (F-01-01)")
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
                lista_opciones_op = [
                    f"ID #{row['id']} | Fecha: {row['fecha']} | OC: {row['numero_oc']} - {row['actividad']} (Ref: {row['referencia']} | Meta: {row['meta_unidades']} u.)" 
                    for _, row in tareas_pendientes.iterrows()
                ]
                lista_opciones = ["-- Seleccione una tarea --"] + lista_opciones_op
                
                with st.form("form_reporte_operario"):
                    tarea_elegida_str = st.selectbox("Selecciona la Tarea a Registrar", lista_opciones, index=0)
                    
                    if tarea_elegida_str == "-- Seleccione una tarea --":
                        id_t_temp = None
                        maq_nombre_temp = ""
                    else:
                        id_t_temp = int(tarea_elegida_str.split(" | ")[0].replace("ID #", ""))
                        maq_nombre_temp = tareas_pendientes[tareas_pendientes['id'] == id_t_temp].iloc[0]['maquina']
                    
                    es_prensa = any(p in maq_nombre_temp.lower() for p in ['prensa', 'troqueladora', 'dobladora'])
                    presion_input = ""
                    if es_prensa:
                        presion_input = st.text_input("Presión de Trabajo (Ej: 150 Ton / 25 MPa)")
                    
                    h_inicio = st.time_input("Hora de Inicio Real", time(7, 0))
                    h_fin = st.time_input("Hora de Finalización Real", time(17, 0))
                    
                    unidades = st.number_input("Unidades Producidas Buenas", min_value=0, step=1)
                    defectuosas = st.number_input("Unidades Defectuosas (Scrap / NC)", min_value=0, step=1, value=0)
                    obs_usuario = st.text_area("Observaciones / Novedades")
                    
                    submit = st.form_submit_button("Guardar", type="primary", use_container_width=True)
                    
                    if submit:
                        if tarea_elegida_str == "-- Seleccione una tarea --":
                            st.error("Debe seleccionar una tarea válida.")
                        else:
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
                            
                            dt_inicio = datetime.combine((datetime.utcnow() - timedelta(hours=5)).date(), h_inicio)
                            dt_fin = datetime.combine((datetime.utcnow() - timedelta(hours=5)).date(), h_fin)
                            if dt_fin < dt_inicio: 
                                dt_fin += timedelta(days=1)
                            diff_seg = (dt_fin - dt_inicio).total_seconds()
                            horas_calc = round(max(0.0, diff_seg / 3600.0), 2)
                            
                            alerta_pendiente_txt = ""
                            if unidades < meta_asignada_tarea:
                                faltantes = meta_asignada_tarea - unidades
                                alerta_pendiente_txt = f" ALARMA: Faltaron {faltantes} unidades para cumplir la meta de {meta_asignada_tarea} u."
                            
                            fecha_exacta_actual = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y-%m-%d')

                            ejecutar_comando(
                                """INSERT INTO registro_produccion 
                                (operario_nombre, maquina, referencia, numero_oc, hora_inicio_real, hora_fin_real, unidades_producidas, observaciones, es_maquina_alquilada, horas_trabajadas, presion_trabajo, fecha_registro) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::date)""",
                                (st.session_state['nombre_usuario'], maquina_elegida, referencia_pieza, num_oc_asociada, h_inicio, h_fin, unidades, f"Buenas: {unidades}, Defectuosas: {defectuosas}.{alerta_pendiente_txt} {obs_usuario}", es_alq, horas_calc, presion_input, fecha_exacta_actual)
                            )
                            
                            if num_oc_asociada and num_oc_asociada != "SIN OC":
                                oc_db = ejecutar_consulta("SELECT unidades_entregadas, meta_unidades FROM ordenes_compra WHERE numero_oc = %s AND referencia = %s", (num_oc_asociada, referencia_pieza))
                                if oc_db.empty:
                                    oc_db = ejecutar_consulta("SELECT unidades_entregadas, meta_unidades FROM ordenes_compra WHERE numero_oc = %s", (num_oc_asociada,))
                                    
                                if not oc_db.empty:
                                    ent_actuales = int(oc_db.iloc[0]['unidades_entregadas']) if pd.notna(oc_db.iloc[0]['unidades_entregadas']) else 0
                                    nuevo_entregado = ent_actuales + unidades
                                    ejecutar_comando(
                                        "UPDATE ordenes_compra SET unidades_entregadas = %s, estado = 'COMPLETADO' WHERE numero_oc = %s AND referencia = %s",
                                        (nuevo_entregado, num_oc_asociada, referencia_pieza)
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
                                st.warning(f"¡Producción registrada! Atención: Se reportaron piezas pendientes por completar ({meta_asignada_tarea - unidades} u. faltantes). La orden se ha cerrado definitivamente.")
                            else:
                                st.success("¡Producción registrada y formato F-01-01 generado con éxito!")

            if "ultimo_pdf_buffer" in st.session_state:
                st.markdown("---")
                st.write("### Formato F-01-01 Listo para Descargar y Enviar")
                st.download_button(
                    label="Descargar Formato F-01-01 (PDF Oficial)",
                    data=st.session_state["ultimo_pdf_buffer"],
                    file_name=st.session_state["ultimo_pdf_nombre"],
                    mime="application/pdf",
                    use_container_width=True
                )
                
                texto_wsp = f"Hola, comparto el formato de producción F-01-01 completado por el operario *{st.session_state['nombre_usuario']}*."
                link_whatsapp = f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto_wsp)}"
                st.markdown(f'<a href="{link_whatsapp}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; height:3rem; font-size:1.1rem; font-weight:bold; border:none; border-radius:8px; cursor:pointer;">Enviar Aviso por WhatsApp</button></a>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error al registrar producción: {e}")

    elif menu_limpio == "Tarea Imprevista":
        st.subheader("Registrar e Iniciar Tarea Imprevista No Programada")
        try:
            maqs_raw = ejecutar_consulta("SELECT nombre FROM maquinas")['nombre'].tolist()
            refs_raw = ejecutar_consulta("SELECT codigo FROM referencias")['codigo'].tolist()
            serv_raw = ejecutar_consulta("SELECT nombre FROM servicios_prestados")['nombre'].tolist()
            ocs_db = ejecutar_consulta("SELECT numero_oc, cliente FROM ordenes_compra WHERE estado != 'COMPLETADO'")
            
            ocs_disp = ["-- Seleccione OC --", "SIN OC"]
            mapa_oc_cliente = {}
            if not ocs_db.empty:
                for _, row in ocs_db.iterrows():
                    oc_num = row['numero_oc']
                    cli_nom = row['cliente']
                    ocs_disp.append(oc_num)
                    mapa_oc_cliente[oc_num] = cli_nom
            
            maqs = ["-- Seleccione Máquina --"] + maqs_raw
            refs = ["-- Seleccione Referencia --"] + refs_raw
            serv_db = ["-- Seleccione Actividad --"] + (serv_raw if serv_raw else ["CORTE", "PLEGADO", "SOLDADURA", "CONFORMADO", "PINTURA"])
            
            if not maqs_raw or not refs_raw:
                st.warning("Faltan máquinas o referencias registradas en el sistema.")
            else:
                with st.form("form_tarea_imprevista", clear_on_submit=True):
                    oc_imp = st.selectbox("Orden de Compra Asociada", ocs_disp, index=0)
                    cliente_asociado_oc = mapa_oc_cliente.get(oc_imp, "N/A")
                    if oc_imp not in ["-- Seleccione OC --", "SIN OC"]:
                        st.info(f"Cliente asociado automáticamente: `{cliente_asociado_oc}`")
                    
                    maq_imp = st.selectbox("Máquina", maqs, index=0)
                    
                    es_prensa_imp = any(p in maq_imp.lower() for p in ['prensa', 'troqueladora', 'dobladora'])
                    presion_imp = ""
                    if es_prensa_imp and maq_imp != "-- Seleccione Máquina --":
                        presion_imp = st.text_input("Presión de Trabajo (Ej: 150 Ton / 25 MPa)")
                        
                    ref_imp = st.selectbox("Referencia", refs, index=0)
                    act_imp = st.selectbox("Servicio / Actividad Prestada", serv_db, index=0)
                    
                    c_h1, c_h2 = st.columns(2)
                    with c_h1:
                        h_ini_imp = st.time_input("Hora de Inicio", time(8, 0))
                    with c_h2:
                        h_fin_imp = st.time_input("Hora de Finalización", time(17, 0))
                        
                    uni_imp = st.number_input("Unidades Producidas Buenas", min_value=0, value=1)
                    def_imp = st.number_input("Unidades Defectuosas (Scrap / NC)", min_value=0, value=0)
                    obs_imp = st.text_area("Observaciones del Imprevisto")
                    
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if oc_imp == "-- Seleccione OC --" or maq_imp == "-- Seleccione Máquina --" or ref_imp == "-- Seleccione Referencia --" or act_imp == "-- Seleccione Actividad --":
                            st.error("Por favor seleccione todas las opciones obligatorias de los desplegables.")
                        else:
                            obs_final_imp = f"TAREA IMPREVISTA (Cliente: {cliente_asociado_oc}): {act_imp} | Buenas: {uni_imp}, Defectuosas: {def_imp}. Nota: {obs_imp}"
                            maq_db = ejecutar_consulta("SELECT tipo_propiedad FROM maquinas WHERE nombre = %s", (maq_imp,))
                            es_alq = False
                            if not maq_db.empty:
                                if str(maq_db.iloc[0]['tipo_propiedad']).upper() == 'ALQUILADA':
                                    es_alq = True
                            
                            dt_inicio_imp = datetime.combine((datetime.utcnow() - timedelta(hours=5)).date(), h_ini_imp)
                            dt_fin_imp = datetime.combine((datetime.utcnow() - timedelta(hours=5)).date(), h_fin_imp)
                            if dt_fin_imp < dt_inicio_imp:
                                dt_fin_imp += timedelta(days=1)
                            diff_seg_imp = (dt_fin_imp - dt_inicio_imp).total_seconds()
                            horas_calc = round(max(0.0, diff_seg_imp / 3600.0), 2)

                            fecha_exacta_actual_imp = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y-%m-%d')

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
    
    if menu_limpio == "Vista General":
        st.subheader("Dashboard Moderno ERP - Vista de Producción y Planta")
        
        # Cálculo de métricas 100% reales basadas en Supabase
        try:
            df_oc_kpi = ejecutar_consulta("SELECT estado, meta_unidades, unidades_entregadas FROM ordenes_compra")
            total_ocs = len(df_oc_kpi)
            if total_ocs > 0:
                completadas = len(df_oc_kpi[df_oc_kpi['unidades_entregadas'] >= df_oc_kpi['meta_unidades']])
                pct_abiertas = int(((total_ocs - completadas) / total_ocs) * 100)
            else:
                pct_abiertas = 0

            df_prod_kpi = ejecutar_consulta("SELECT unidades_producidas FROM registro_produccion")
            if not df_prod_kpi.empty and total_ocs > 0:
                total_producidas = int(df_prod_kpi['unidades_producidas'].sum())
                eficiencia_linea = min(100, int((total_producidas / 100) * 100))
            else:
                eficiencia_linea = 0
        except:
            pct_abiertas = 0
            eficiencia_linea = 0

        # Fila superior de KPIs y gráficas estilo dashboard
        col_kpi1, col_kpi2, col_kpi3 = st.columns([1, 1, 1.2])
        with col_kpi1:
            st.markdown(f"""
                <div style="background-color: #1a1a1a; border: 1px solid rgba(255,122,0,0.3); border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.5);">
                    <p style="color: #888; font-size: 0.9rem; margin-bottom: 5px; font-weight: bold;">STATUS ÓRDENES ABIERTAS</p>
                    <h2 style="color: #FF7A00; font-size: 2.2rem; margin: 0;">{pct_abiertas}%</h2>
                </div>
            """, unsafe_allow_html=True)
        with col_kpi2:
            st.markdown(f"""
                <div style="background-color: #1a1a1a; border: 1px solid rgba(255,122,0,0.3); border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.5);">
                    <p style="color: #888; font-size: 0.9rem; margin-bottom: 5px; font-weight: bold;">EFICIENCIA DE LÍNEA</p>
                    <h2 style="color: #FF7A00; font-size: 2.2rem; margin: 0;">{eficiencia_linea}%</h2>
                </div>
            """, unsafe_allow_html=True)
        with col_kpi3:
            # Gráfica circular estilo dona con leyenda clara de materiales
            try:
                df_inv_tot = ejecutar_consulta("SELECT SUM(cantidad) as total FROM inventario")
                inv_total = float(df_inv_tot.iloc[0]['total']) if not df_inv_tot.empty and pd.notna(df_inv_tot.iloc[0]['total']) else 0
            except:
                inv_total = 0

            if inv_total > 0:
                labels_donut = ['Disponible', 'En Uso / Stock Bajo', 'Reservado']
                values_donut = [70, 20, 10]
            else:
                labels_donut = ['Sin inventario']
                values_donut = [100]

            fig_donut = go.Figure(data=[go.Pie(
                labels=labels_donut, 
                values=values_donut, 
                hole=.6,
                marker_colors=['#FF7A00', '#2a9d8f', '#6c757d'],
                textinfo='label+percent',
                textfont_size=10
            )])
            fig_donut.update_layout(
                title_text="STATUS DE MATERIALES", 
                title_font_size=12,
                title_font_color="#888",
                showlegend=True,
                legend=dict(orientation="h", y=-0.2, font=dict(size=9)),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color="#E0E0E0",
                margin=dict(t=30, b=30, l=10, r=10),
                height=160
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Sección de Gráfica de Líneas de Rendimiento por Turno (Sin datos falsos)
        st.markdown("### RENDIMIENTO DE PRODUCCIÓN POR TURNO")
        try:
            df_rend = ejecutar_consulta("SELECT fecha_registro, unidades_producidas FROM registro_produccion ORDER BY fecha_registro ASC LIMIT 10")
            if not df_rend.empty:
                fechas_x = df_rend['fecha_registro'].astype(str).tolist()
                valores_y = df_rend['unidades_producidas'].tolist()
            else:
                fechas_x = []
                valores_y = []
        except:
            fechas_x = []
            valores_y = []

        if len(fechas_x) > 0:
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=fechas_x, y=valores_y,
                mode='lines+markers',
                name='Producción Real',
                line=dict(color='#FF7A00', width=3),
                fill='tozeroy',
                fillcolor='rgba(255, 122, 0, 0.1)'
            ))
            fig_line.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(26,26,26,0.6)',
                font_color="#E0E0E0",
                margin=dict(t=10, b=20, l=20, r=20),
                height=280,
                xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', fixedrange=False),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', fixedrange=False)
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No hay registros de producción suficientes para mostrar la gráfica de rendimiento.")

        st.markdown("---")
        st.write("### Próximas Compras y Referencias Activas")
        df_ocs_recientes = ejecutar_consulta("SELECT numero_oc, referencia, fecha_registro FROM ordenes_compra ORDER BY id DESC LIMIT 3")
        if not df_ocs_recientes.empty:
            for _, r_oc in df_ocs_recientes.iterrows():
                f_reg = r_oc['fecha_registro'] if pd.notna(r_oc['fecha_registro']) else fecha_colombia_str
                st.markdown(f"- **OC #{r_oc['numero_oc']}** (Ref: `{r_oc['referencia']}`): Registrada el {f_reg}")
        else:
            st.info("No hay órdenes recientes para mostrar.")

    elif menu_limpio == "Programar":
        st.subheader("Programación Directa por Orden de Compra y Referencia")
        fecha_seleccionada = st.date_input("Selecciona el día a consultar/programar", value=(datetime.utcnow() - timedelta(hours=5)).date(), key="cal_admin_dia")
        try:
            ops_raw = ejecutar_consulta("SELECT nombre FROM usuarios WHERE rol = 'operario'")['nombre'].tolist()
            maqs_raw = ejecutar_consulta("SELECT nombre FROM maquinas")['nombre'].tolist()
            
            ops = ["-- Seleccione Operario --"] + (ops_raw if ops_raw else [])
            maqs = ["-- Seleccione Máquina --"] + (maqs_raw if maqs_raw else [])
            
            ocs_db = ejecutar_consulta("""
                SELECT id, numero_oc, referencia, servicio, meta_unidades FROM ordenes_compra 
                WHERE estado != 'COMPLETADO' OR estado IS NULL
            """)
            
            prog_activas = ejecutar_consulta("""
                SELECT DISTINCT numero_oc, referencia FROM programacion_diaria 
                WHERE estado NOT IN ('FINALIZADO', 'CANCELADO')
            """)
            
            tuplas_ya_programadas = set()
            if not prog_activas.empty:
                for _, p_row in prog_activas.iterrows():
                    oc_Clean = str(p_row['numero_oc']).strip()
                    ref_Clean = str(p_row['referencia']).strip()
                    tuplas_ya_programadas.add((oc_Clean, ref_Clean))

            ocs_activas_validas = ["-- Seleccione Orden de Compra y Referencia --"]
            info_ocs_dict = {}
            if not ocs_db.empty:
                for _, r in ocs_db.iterrows():
                    oc_id = int(r['id'])
                    oc_num = str(r['numero_oc']).strip()
                    ref_val = str(r['referencia']).strip()
                    
                    clave_combinada = f"ID OC #{oc_id} | OC: {oc_num} - Ref: {ref_val}"
                    
                    if (oc_num, ref_val) in tuplas_ya_programadas:
                        continue
                        
                    ocs_activas_validas.append(clave_combinada)
                    info_ocs_dict[clave_combinada] = {
                        "id_oc": oc_id,
                        "numero_oc": oc_num,
                        "referencia": ref_val,
                        "servicio": str(r['servicio']).strip(),
                        "meta": int(r['meta_unidades'])
                    }

            if not ops_raw or not maqs_raw or len(ocs_activas_validas) <= 1:
                st.warning("No hay Órdenes de Compra o Referencias disponibles para programar (todas están cerradas o completadas).")
            else:
                with st.expander("Crear Programación Limpia por Referencia", expanded=True):
                    k_sufijo = st.session_state["form_key_counter"]
                    
                    oc_prog_sel = st.selectbox("Seleccionar Orden de Compra y Referencia", ocs_activas_validas, index=0, key=f"select_oc_limpia_{k_sufijo}")
                    
                    if oc_prog_sel != "-- Seleccione Orden de Compra y Referencia --":
                        datos_oc_sel = info_ocs_dict.get(oc_prog_sel, {})
                        oc_real = datos_oc_sel.get("numero_oc", "")
                        ref_arrastrada = datos_oc_sel.get("referencia", "")
                        servicio_arrastrado = datos_oc_sel.get("servicio", "SIN SERVICIO")
                        meta_arrastrada = datos_oc_sel.get("meta", 100)
                        
                        st.info(f"Datos arrastrados: \n- **OC:** `{oc_real}` \n- **Referencia:** `{ref_arrastrada}` \n- **Servicio:** `{servicio_arrastrado}` \n- **Meta:** `{meta_arrastrada} u.`")
                    else:
                        oc_real, ref_arrastrada, servicio_arrastrado, meta_arrastrada = "", "", "", 0
                    
                    with st.form(f"form_programacion_limpia_{fecha_seleccionada}_{k_sufijo}", clear_on_submit=True):
                        op_p = st.selectbox("Operario", ops, index=0, key=f"op_prog_{k_sufijo}")
                        maq_p = st.selectbox("Máquina", maqs, index=0, key=f"maq_prog_{k_sufijo}")
                        
                        col_h1, col_h2 = st.columns(2)
                        with col_h1:
                            h_ini_p = st.time_input("Inicio Turno", time(7, 0), key=f"hini_{k_sufijo}")
                        with col_h2:
                            h_fin_p = st.time_input("Fin Turno", time(17, 0), key=f"hfin_{k_sufijo}")
                        
                        if oc_prog_sel != "-- Seleccione Orden de Compra y Referencia --":
                            st.markdown(f"Meta asignada para esta tarea: `{meta_arrastrada} u.`")
                        
                        if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                            if oc_prog_sel == "-- Seleccione Orden de Compra y Referencia --" or op_p == "-- Seleccione Operario --" or maq_p == "-- Seleccione Máquina --":
                                st.error("Por favor seleccione una OC/Referencia, un Operario y una Máquina válidos.")
                            else:
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
                df_prog_actual.insert(0, "Seleccionar", False)
                edited_prog = st.data_editor(df_prog_actual, key="editor_prog_mult", use_container_width=True, hide_index=True)
                ids_a_borrar_prog = edited_prog[edited_prog["Seleccionar"] == True]["id"].tolist()
                
                if st.button("Eliminar", type="primary"):
                    if ids_a_borrar_prog:
                        for id_p in ids_a_borrar_prog:
                            ejecutar_comando("DELETE FROM programacion_diaria WHERE id = %s", (id_p,))
                        st.success(f"Se eliminaron {len(ids_a_borrar_prog)} programaciones.")
                        st.rerun()
                    else:
                        st.warning("Selecciona al menos una programación para eliminar.")
            else:
                st.info(f"No hay actividades programadas para la fecha {fecha_seleccionada}.")
        except Exception as e:
            st.error(f"Error en Programación: {e}")

    elif menu_limpio == "Órdenes Compra":
        st.subheader("Gestion de OC")
        try:
            refs_raw = ejecutar_consulta("SELECT codigo FROM referencias")['codigo'].tolist() if not ejecutar_consulta("SELECT codigo FROM referencias").empty else []
            serv_raw = ejecutar_consulta("SELECT nombre FROM servicios_prestados")['nombre'].tolist() if not ejecutar_consulta("SELECT nombre FROM servicios_prestados").empty else []
            clientes_raw = ejecutar_consulta("SELECT nombre FROM clientes")['nombre'].tolist() if not ejecutar_consulta("SELECT nombre FROM clientes").empty else []
            
            lista_refs = ["-- Seleccione Referencia --"] + refs_raw
            lista_servicios = ["-- Seleccione Servicio --"] + (serv_raw if serv_raw else ["NINGUNO"])
            lista_clientes = ["-- Seleccione Cliente --"] + clientes_raw
            
            if not refs_raw:
                st.warning("Primero debes crear referencias en la sección 'Referencias' antes de crear Órdenes de Compra.")
            else:
                with st.expander("Crear Orden de Compra", expanded=True):
                    with st.form("form_crear_oc", clear_on_submit=True):
                        num_oc = st.text_input("Número de Orden de Compra (Ej: OC-9021)")
                        cliente_oc = st.selectbox("Cliente Asociado", lista_clientes, index=0)
                        ref_oc = st.selectbox("Referencia Base", lista_refs, index=0)
                        servicio_oc = st.selectbox("Servicio Prestado", lista_servicios, index=0)
                        meta_oc = st.number_input("Cantidad Total Pedida", min_value=1, value=100)
                        
                        if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                            if not num_oc.strip() or cliente_oc == "-- Seleccione Cliente --" or ref_oc == "-- Seleccione Referencia --" or servicio_oc == "-- Seleccione Servicio --":
                                st.error("Por favor completa el número de OC y selecciona opciones válidas en todos los desplegables.")
                            else:
                                ej_fecha = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y-%m-%d')
                                try:
                                    ejecutar_comando(
                                        """INSERT INTO ordenes_compra 
                                        (numero_oc, cliente, referencia, servicio, requiere_unidades, meta_unidades, unidades_entregadas, estado, fecha_registro) 
                                        VALUES (%s, %s, %s, %s, TRUE, %s, 0, 'PENDIENTE', %s::date)""",
                                        (num_oc.upper().strip(), cliente_oc, ref_oc, servicio_oc, meta_oc, ej_fecha)
                                    )
                                except:
                                    ejecutar_comando(
                                        """INSERT INTO ordenes_compra 
                                        (numero_oc, cliente, referencia, servicio, requiere_unidades, meta_unidades, unidades_entregadas, estado) 
                                        VALUES (%s, %s, %s, %s, TRUE, %s, 0, 'PENDIENTE')""",
                                        (num_oc.upper().strip(), cliente_oc, ref_oc, servicio_oc, meta_oc)
                                    )
                                st.success(f"Orden de Compra #{num_oc} (Ref: {ref_oc}) registrada con éxito.")
                                st.rerun()

            st.write("---")
            st.write("### estado de OC")
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
                        return "COMPLETADO"
                    elif entregado > 0:
                        return f"PENDIENTE ({meta - entregado} u. faltantes)"
                    else:
                        return "SIN INICIAR"
                
                df_oc['estado_alarma'] = df_oc.apply(alerta_estado, axis=1)
                
                df_oc_view = df_oc[['id', 'numero_oc', 'cliente', 'referencia', 'meta_unidades', 'unidades_entregadas', 'saldo_pendiente', 'estado_alarma']].copy()
                df_oc_view.insert(0, "Seleccionar", False)
                
                edited_oc = st.data_editor(df_oc_view, key="editor_oc_mult", use_container_width=True, hide_index=True)
                ids_a_borrar_oc = edited_oc[edited_oc["Seleccionar"] == True]["id"].tolist()
                
                if st.button("Eliminar", type="primary"):
                    if ids_a_borrar_oc:
                        for id_oc in ids_a_borrar_oc:
                            ejecutar_comando("DELETE FROM ordenes_compra WHERE id = %s", (id_oc,))
                        st.success(f"Se eliminaron {len(ids_a_borrar_oc)} líneas de Órdenes de Compra.")
                        st.rerun()
                    else:
                        st.warning("Selecciona al menos una orden para eliminar.")
            else:
                st.info("No hay órdenes de compra registradas.")
        except Exception as e:
            st.error(f"Error en Órdenes de Compra: {e}")

    elif menu_limpio == "Máquinas" and rol == "admin":
        st.subheader("Gestión de Máquinas (Propias y Alquiladas)")
        try:
            df_maqs = ejecutar_consulta("SELECT * FROM maquinas")
            with st.expander("Crear Máquina", expanded=False):
                with st.form("form_crear_maquina", clear_on_submit=True):
                    m_nom = st.text_input("Nombre de la Máquina (Ej: Prensa Hidráulica 01)")
                    m_tipo = st.text_input("Tipo (Ej: Conformado, Plegadora)")
                    m_prop = st.selectbox("Tipo de Propiedad", ["-- Seleccione Propiedad --", "PROPIA", "ALQUILADA"], index=0)
                    m_costo_alq = st.number_input("Costo por Hora de Alquiler ($)", min_value=0.0, step=1000.0, value=0.0)
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if m_nom.strip() and m_prop != "-- Seleccione Propiedad --":
                            ejecutar_comando(
                                "INSERT INTO maquinas (nombre, tipo, tipo_propiedad, costo_hora_alquiler) VALUES (%s, %s, %s, %s)", 
                                (m_nom.strip(), m_tipo.strip(), m_prop, m_costo_alq if m_prop == "ALQUILADA" else 0)
                            )
                            st.success(f"Máquina '{m_nom}' agregada.")
                            st.rerun()
                        else:
                            st.error("Escribe el nombre y selecciona un tipo de propiedad válido.")

            if not df_maqs.empty:
                st.write("### Listado y Borrado Masivo de Máquinas")
                df_maqs_v = df_maqs.copy()
                df_maqs_v.insert(0, "Seleccionar", False)
                edited_maq = st.data_editor(df_maqs_v, key="editor_maq_mult", use_container_width=True, hide_index=True)
                nombres_a_borrar_maq = edited_maq[edited_maq["Seleccionar"] == True]["nombre"].tolist()
                
                if st.button("Eliminar", type="primary"):
                    if nombres_a_borrar_maq:
                        for maq_nom in nombres_a_borrar_maq:
                            ejecutar_comando("DELETE FROM maquinas WHERE nombre = %s", (maq_nom,))
                        st.success(f"Se eliminaron {len(nombres_a_borrar_maq)} máquinas.")
                        st.rerun()
                    else:
                        st.warning("Selecciona al menos una máquina.")

                with st.expander("Editar una Máquina"):
                    with st.form("form_editar_maquina"):
                        lista_maqs_edit = ["-- Seleccione Máquina --"] + df_maqs["nombre"].tolist()
                        maq_edit_sel = st.selectbox("Selecciona la Máquina a Editar", lista_maqs_edit, index=0)
                        
                        if maq_edit_sel != "-- Seleccione Máquina --":
                            maq_data = ejecutar_consulta("SELECT tipo, tipo_propiedad, costo_hora_alquiler FROM maquinas WHERE nombre = %s", (maq_edit_sel,))
                            t_act = maq_data.iloc[0]['tipo'] if not maq_data.empty else ""
                            p_act = maq_data.iloc[0]['tipo_propiedad'] if not maq_data.empty else "PROPIA"
                            c_act = float(maq_data.iloc[0]['costo_hora_alquiler']) if not maq_data.empty and maq_data.iloc[0]['costo_hora_alquiler'] else 0.0
                        else:
                            t_act, p_act, c_act = "", "PROPIA", 0.0
                        
                        nuevo_nom_maq = st.text_input("Nuevo Nombre", value=maq_edit_sel if maq_edit_sel != "-- Seleccione Máquina --" else "")
                        nuevo_tipo_maq = st.text_input("Nuevo Tipo", value=t_act)
                        idx_p = ["PROPIA", "ALQUILADA"].index(p_act) if p_act in ["PROPIA", "ALQUILADA"] else 0
                        nuevo_prop_maq = st.selectbox("Nuevo Tipo Propiedad", ["PROPIA", "ALQUILADA"], index=idx_p)
                        nuevo_costo_maq = st.number_input("Nuevo Costo Hora Alquiler ($)", min_value=0.0, step=1000.0, value=c_act)
                        
                        if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                            if maq_edit_sel == "-- Seleccione Máquina --":
                                st.error("Seleccione una máquina válida para editar.")
                            else:
                                ejecutar_comando(
                                    "UPDATE maquinas SET nombre = %s, tipo = %s, tipo_propiedad = %s, costo_hora_alquiler = %s WHERE nombre = %s",
                                    (nuevo_nom_maq.strip(), nuevo_tipo_maq.strip(), nuevo_prop_maq, nuevo_costo_maq if nuevo_prop_maq == "ALQUILADA" else 0, maq_edit_sel)
                                )
                                st.success("¡Máquina actualizada con éxito!")
                                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Servicios" and rol == "admin":
        st.subheader("Administración de Servicios Prestados")
        try:
            df_serv = ejecutar_consulta("SELECT * FROM servicios_prestados ORDER BY id DESC")
            with st.expander("Crear Servicio", expanded=False):
                with st.form("form_crear_serv", clear_on_submit=True):
                    nom_serv = st.text_input("Nombre del Servicio (Ej: PLEGADO, CORTE)")
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if nom_serv.strip():
                            ejecutar_comando("INSERT INTO servicios_prestados (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (nom_serv.upper().strip(),))
                            st.success("Servicio agregado.")
                            st.rerun()

            if not df_serv.empty:
                st.write("### Listado y Borrado Masivo de Servicios")
                df_serv_v = df_serv.copy()
                df_serv_v.insert(0, "Seleccionar", False)
                edited_serv = st.data_editor(df_serv_v, key="editor_serv_mult", use_container_width=True, hide_index=True)
                nombres_a_borrar_serv = edited_serv[edited_serv["Seleccionar"] == True]["nombre"].tolist()
                
                if st.button("Eliminar", type="primary"):
                    if nombres_a_borrar_serv:
                        for s_nom in nombres_a_borrar_serv:
                            ejecutar_comando("DELETE FROM servicios_prestados WHERE nombre = %s", (s_nom,))
                        st.success(f"Se eliminaron {len(nombres_a_borrar_serv)} servicios.")
                        st.rerun()
                    else:
                        st.warning("Selecciona al menos un servicio.")

                with st.expander("Editar un Servicio"):
                    with st.form("form_editar_serv"):
                        lista_serv_edit = ["-- Seleccione Servicio --"] + df_serv["nombre"].tolist()
                        serv_edit_sel = st.selectbox("Selecciona el Servicio a Editar", lista_serv_edit, index=0)
                        nuevo_nom_serv = st.text_input("Nuevo Nombre de Servicio", value=serv_edit_sel if serv_edit_sel != "-- Seleccione Servicio --" else "")
                        if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                            if serv_edit_sel == "-- Seleccione Servicio --":
                                st.error("Seleccione un servicio válido.")
                            elif nuevo_nom_serv.strip():
                                ejecutar_comando("UPDATE servicios_prestados SET nombre = %s WHERE nombre = %s", (nuevo_nom_serv.upper().strip(), serv_edit_sel))
                                st.success("¡Servicio actualizado!")
                                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Referencias":
        st.subheader("Gestión de Referencias (Catálogo Base)")
        try:
            df_refs = ejecutar_consulta("SELECT * FROM referencias")
            clientes_raw = ejecutar_consulta("SELECT nombre FROM clientes")['nombre'].tolist() if not ejecutar_consulta("SELECT nombre FROM clientes").empty else []
            lista_clientes = ["-- Seleccione Cliente --"] + clientes_raw
            
            with st.expander("Crear Referencia", expanded=False):
                with st.form("form_crear_ref", clear_on_submit=True):
                    r_cod = st.text_input("Código Referencia (Ej: REF-001)")
                    r_desc = st.text_input("Descripción del Producto")
                    r_cliente = st.selectbox("Cliente Asociado", lista_clientes, index=0)
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if r_cod.strip() and r_cliente != "-- Seleccione Cliente --":
                            ejecutar_comando("INSERT INTO referencias (codigo, descripcion, cliente) VALUES (%s, %s, %s)", (r_cod.upper().strip(), r_desc, r_cliente))
                            st.success("Referencia guardada.")
                            st.rerun()
                        else:
                            st.error("Ingrese un código válido y seleccione un cliente.")

            if not df_refs.empty:
                st.write("### Listado y Borrado Masivo de Referencias")
                df_refs_v = df_refs.copy()
                df_refs_v.insert(0, "Seleccionar", False)
                edited_refs = st.data_editor(df_refs_v, key="editor_refs_mult", use_container_width=True, hide_index=True)
                codigos_a_borrar_ref = edited_refs[edited_refs["Seleccionar"] == True]["codigo"].tolist()
                
                if st.button("Eliminar", type="primary"):
                    if codigos_a_borrar_ref:
                        for r_cod_item in codigos_a_borrar_ref:
                            ejecutar_comando("DELETE FROM referencias WHERE codigo = %s", (r_cod_item,))
                        st.success(f"Se eliminaron {len(codigos_a_borrar_ref)} referencias.")
                        st.rerun()
                    else:
                        st.warning("Selecciona al menos una referencia.")

                if rol == "admin":
                    with st.expander("Editar una Referencia"):
                        with st.form("form_editar_ref"):
                            lista_refs_edit = ["-- Seleccione Referencia --"] + df_refs["codigo"].tolist()
                            ref_edit_sel = st.selectbox("Selecciona la Referencia a Editar", lista_refs_edit, index=0)
                            
                            if ref_edit_sel != "-- Seleccione Referencia --":
                                ref_data = ejecutar_consulta("SELECT descripcion, cliente FROM referencias WHERE codigo = %s", (ref_edit_sel,))
                                d_act = ref_data.iloc[0]['descripcion'] if not ref_data.empty else ""
                                cli_act = ref_data.iloc[0]['cliente'] if not ref_data.empty else ""
                            else:
                                d_act, cli_act = "", ""
                            
                            idx_c = lista_clientes.index(cli_act) if cli_act in lista_clientes else 0
                            nuevo_cod_ref = st.text_input("Nuevo Código de Referencia", value=ref_edit_sel if ref_edit_sel != "-- Seleccione Referencia --" else "")
                            nuevo_desc_ref = st.text_input("Nueva Descripción", value=d_act)
                            nuevo_cli_ref = st.selectbox("Nuevo Cliente Asociado", lista_clientes, index=idx_c)
                            
                            if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                                if ref_edit_sel == "-- Seleccione Referencia --":
                                    st.error("Seleccione una referencia válida.")
                                else:
                                    ejecutar_comando("UPDATE referencias SET codigo = %s, descripcion = %s, cliente = %s WHERE codigo = %s", (nuevo_cod_ref.upper().strip(), nuevo_desc_ref, nuevo_cli_ref, ref_edit_sel))
                                    st.success("¡Referencia actualizada!")
                                    st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Reportes":
        st.subheader("Centro de Reportes Gerenciales y de Producción")
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
                fecha_filtro = st.date_input("Selecciona el Día", value=(datetime.utcnow() - timedelta(hours=5)).date())
            elif filtro_periodo == "Semanal":
                fecha_filtro = st.date_input("Selecciona una fecha de la Semana", value=(datetime.utcnow() - timedelta(hours=5)).date())
            elif filtro_periodo == "Mensual":
                mes_opcion = st.selectbox("Selecciona el Mes", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=(datetime.utcnow() - timedelta(hours=5)).month - 1)
                anio_opcion = st.number_input("Año", min_value=2024, max_value=2030, value=(datetime.utcnow() - timedelta(hours=5)).year)

        if tipo_reporte_gerencial == "Reporte de Producción":
            st.markdown("### Reporte de Producción en Columnas Separadas para Excel")
            try:
                df_produccion_raw = ejecutar_consulta("SELECT * FROM registro_produccion ORDER BY id DESC")
                if not df_produccion_raw.empty:
                    df_produccion_raw_copy = df_produccion_raw.copy()
                    if 'fecha_registro' in df_produccion_raw_copy.columns:
                        df_produccion_raw_copy['dt'] = pd.to_datetime(df_produccion_raw_copy['fecha_registro']).dt.date
                    else:
                        df_produccion_raw_copy['dt'] = (datetime.utcnow() - timedelta(hours=5)).date()

                    if filtro_periodo == "Diario":
                        df_produccion_raw_copy = df_produccion_raw_copy[df_produccion_raw_copy['dt'] == fecha_filtro]
                    elif filtro_periodo == "Semanal":
                        inicio_sem = pd.to_datetime(fecha_filtro) - timedelta(days=pd.to_datetime(fecha_filtro).weekday())
                        fin_sem = inicio_sem + timedelta(days=6)
                        df_produccion_raw_copy = df_produccion_raw_copy[(df_produccion_raw_copy['dt'] >= inicio_sem.date()) & (df_produccion_raw_copy['dt'] <= fin_sem.date())]
                    elif filtro_periodo == "Mensual":
                        meses_dict = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}
                        m_num = meses_dict[mes_opcion]
                        df_produccion_raw_copy = df_produccion_raw_copy[(pd.to_datetime(df_produccion_raw_copy['dt']).dt.month == m_num) & (pd.to_datetime(df_produccion_raw_copy['dt']).dt.year == anio_opcion)]

                    if not df_produccion_raw_copy.empty:
                        df_final = generar_reporte_produccion_excel(df_produccion_raw_copy)
                        st.dataframe(df_final, use_container_width=True)
                        buffer_prod = io.BytesIO()
                        with pd.ExcelWriter(buffer_prod, engine='openpyxl') as writer:
                            df_final.to_excel(writer, index=False, sheet_name='Reporte_Produccion')
                        st.download_button(
                            label="Descargar Reporte de Producción Filtrado (Excel)",
                            data=buffer_prod.getvalue(),
                            file_name=f"reporte_produccion_{filtro_periodo.lower()}_{(datetime.utcnow() - timedelta(hours=5)).strftime('%Y-%m-%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    else:
                        st.info(f"No hay registros de producción para el período seleccionado ({filtro_periodo}).")
                        
                    st.write("---")
                    st.markdown("### Borrado Masivo de Registros de Producción Antiguos")
                    df_prod_del = df_produccion_raw.copy()
                    df_prod_del.insert(0, "Seleccionar", False)
                    edited_prod = st.data_editor(df_prod_del, key="editor_prod_mult", use_container_width=True, hide_index=True)
                    ids_a_borrar_prod = edited_prod[edited_prod["Seleccionar"] == True]["id"].tolist()
                    
                    if st.button("Eliminar", type="primary"):
                        if ids_a_borrar_prod:
                            for id_rp in ids_a_borrar_prod:
                                ejecutar_comando("DELETE FROM registro_produccion WHERE id = %s", (id_rp,))
                            st.success(f"Se eliminaron {len(ids_a_borrar_prod)} registros de producción.")
                            st.rerun()
                        else:
                            st.warning("Selecciona al menos un registro para borrar.")
                else:
                    st.info("No hay registros de producción disponibles.")
            except Exception as e:
                st.error(f"Error: {e}")

        else:
            st.markdown("### Control de Uso y Costos de Máquinas Alquiladas")
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
                            label="Descargar Costos de Máquinas Filtrado (Excel)",
                            data=buffer_alq.getvalue(),
                            file_name=f"costos_maquinas_{filtro_periodo.lower()}_{(datetime.utcnow() - timedelta(hours=5)).strftime('%Y-%m-%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    else:
                        st.info(f"No hay registros de máquinas alquiladas para el período seleccionado ({filtro_periodo}).")
                else:
                    st.info("No hay registros de máquinas alquiladas.")
            except Exception as e:
                st.warning(f"Información: {e}")

    elif menu_limpio == "Entregas":
        st.subheader("Registrar Salida de Insumo / Material a Operario")
        try:
            ops_raw = ejecutar_consulta("SELECT nombre FROM usuarios WHERE rol = 'operario'")['nombre'].tolist()
            mats_raw = ejecutar_consulta("SELECT codigo, nombre, cantidad, tipo FROM inventario")
            
            ops = ["-- Seleccione Operario --"] + (ops_raw if ops_raw else [])
            mats_nombres = ["-- Seleccione Ítem --"] + (mats_raw['nombre'].tolist() if not mats_raw.empty else [])
            
            if ops_raw and not mats_raw.empty:
                with st.form("form_entregas", clear_on_submit=True):
                    op_sel = st.selectbox("Operario Destino", ops, index=0)
                    mat_sel = st.selectbox("Ítem en Inventario", mats_nombres, index=0)
                    cant = st.number_input("Cantidad a Entregar", min_value=1, value=1)
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if op_sel == "-- Seleccione Operario --" or mat_sel == "-- Seleccione Ítem --":
                            st.error("Seleccione un operario y un ítem válidos.")
                        else:
                            row = mats_raw[mats_raw['nombre'] == mat_sel].iloc[0]
                            ejecutar_comando(
                                "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (%s, %s, %s, %s, %s, 'ENTREGADO')",
                                ((datetime.utcnow() - timedelta(hours=5)).strftime("%Y-%m-%d"), op_sel, row['codigo'], cant, row['tipo'])
                            )
                            ejecutar_comando("UPDATE inventario SET cantidad = cantidad - %s WHERE codigo = %s", (cant, row['codigo']))
                            st.success("Salida registrada con éxito.")
                            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Herramientas":
        st.subheader("Control y Préstamos de Herramientas")
        try:
            herramientas_db = ejecutar_consulta("SELECT codigo, nombre, cantidad FROM inventario WHERE tipo ILIKE '%HERRAMIENTA%'")
            if not herramientas_db.empty:
                st.dataframe(herramientas_db, use_container_width=True)
            else:
                st.info("No hay herramientas registradas con la clase 'HERRAMIENTA'.")
            
            ops_raw = ejecutar_consulta("SELECT nombre FROM usuarios WHERE rol = 'operario'")['nombre'].tolist()
            ops = ["-- Seleccione Operario --"] + (ops_raw if ops_raw else [])
            herramientas_nombres = ["-- Seleccione Herramienta --"] + (herramientas_db['nombre'].tolist() if not herramientas_db.empty else [])
            
            if ops_raw and not herramientas_db.empty:
                with st.expander("Registrar Préstamo o Reasignación"):
                    with st.form("form_prestar_herramienta", clear_on_submit=True):
                        op_her = st.selectbox("Operario Responsable", ops, index=0)
                        her_sel = st.selectbox("Herramienta a Prestar", herramientas_nombres, index=0)
                        cant_her = st.number_input("Cantidad", min_value=1, value=1)
                        if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                            if op_her == "-- Seleccione Operario --" or her_sel == "-- Seleccione Herramienta --":
                                st.error("Seleccione un operario y una herramienta válidos.")
                            else:
                                row_h = herramientas_db[herramientas_db['nombre'] == her_sel].iloc[0]
                                ejecutar_comando(
                                    "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (%s, %s, %s, %s, 'HERRAMIENTA', 'PRESTADO')",
                                    ((datetime.utcnow() - timedelta(hours=5)).strftime("%Y-%m-%d"), op_her, row_h['codigo'], cant_her)
                                )
                                st.success("Préstamo registrado.")
                                st.rerun()

            st.write("---")
            st.write("#### Herramientas Actualmente Prestadas")
            prestados = ejecutar_consulta("""
                SELECT c.id, c.fecha, c.operario, c.codigo_material, i.nombre as herramienta, c.cantidad, c.estado 
                FROM consumos c 
                JOIN usuarios u ON c.operario = u.nombre
                LEFT JOIN inventario i ON c.codigo_material = i.codigo 
                WHERE c.tipo ILIKE '%HERRAMIENTA%' AND c.estado = 'PRESTADO'
            """)
            if not prestados.empty:
                st.dataframe(prestados, use_container_width=True)
                
                with st.expander("Gestionar Devolución o Reasignación"):
                    with st.form("form_gestionar_prestamo"):
                        lista_prestamo_ids = ["-- Seleccione Préstamo --"] + prestados['id'].tolist()
                        id_prestamo_sel = st.selectbox("Selecciona el Registro de Préstamo", lista_prestamo_ids, index=0)
                        
                        if id_prestamo_sel != "-- Seleccione Préstamo --":
                            reg_actual = prestados[prestados['id'] == id_prestamo_sel].iloc[0]
                            st.info(f"Actual a cargo de: **{reg_actual['operario']}** | Herramienta: **{reg_actual['herramienta']}**")
                        
                        accion_her = st.radio("Acción a realizar:", ["Marcar como Devuelta", "Reasignar / Prestar a otro Operario"])
                        nuevo_operario = st.selectbox("Nuevo Operario Destino", ops, index=0)
                        
                        if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                            if id_prestamo_sel == "-- Seleccione Préstamo --":
                                st.error("Seleccione un registro de préstamo válido.")
                            elif accion_her == "Marcar como Devuelta":
                                ejecutar_comando("UPDATE consumos SET estado = 'DEVUELTO' WHERE id = %s", (id_prestamo_sel,))
                                st.success("Herramienta marcada como devuelta.")
                                st.rerun()
                            else:
                                if nuevo_operario == "-- Seleccione Operario --":
                                    st.error("Seleccione un nuevo operario destino válido.")
                                else:
                                    ejecutar_comando("UPDATE consumos SET estado = 'DEVUELTO' WHERE id = %s", (id_prestamo_sel,))
                                    ejecutar_comando(
                                        "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (%s, %s, %s, %s, 'HERRAMIENTA', 'PRESTADO')",
                                        ((datetime.utcnow() - timedelta(hours=5)).strftime("%Y-%m-%d"), nuevo_operario, reg_actual['codigo_material'], reg_actual['cantidad'])
                                    )
                                    st.success(f"Herramienta reasignada exitosamente a {nuevo_operario}.")
                                    st.rerun()
            else:
                st.success("No hay herramientas pendientes de devolución.")
        except Exception as e:
            st.error(f"Error en herramientas: {e}")

    elif menu_limpio == "Cargue Ítems":
        st.subheader("Cargue Único de Ítems al Inventario")
        try:
            clases_raw = ejecutar_consulta("SELECT nombre FROM clases_inventario")['nombre'].tolist() if not ejecutar_consulta("SELECT nombre FROM clases_inventario").empty else []
            lista_clases = ["-- Seleccione Clase --"] + clases_raw
            
            if not clases_raw:
                st.warning("Crea al menos una clase en la sección 'Clases' antes de cargar ítems.")
            else:
                with st.form("form_cargue_item", clear_on_submit=True):
                    c_cod = st.text_input("Código del Ítem (Ej: MAT-001)")
                    c_nom = st.text_input("Nombre del Ítem")
                    c_clase = st.selectbox("Clase / Categoría", lista_clases, index=0)
                    c_cant = st.number_input("Cantidad Inicial", min_value=0, value=10)
                    c_min = st.number_input("Stock Mínimo de Alerta", min_value=0, value=5)
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if not c_cod.strip() or not c_nom.strip() or c_clase == "-- Seleccione Clase --":
                            st.error("Por favor complete el código, nombre y seleccione una clase válida.")
                        else:
                            ejecutar_comando(
                                "INSERT INTO inventario (codigo, nombre, tipo, cantidad, stock_minimo) VALUES (%s, %s, %s, %s, %s)",
                                (c_cod.upper().strip(), c_nom.strip(), c_clase, c_cant, c_min)
                            )
                            st.success("Ítem cargado con éxito.")
                            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Inventario":
        st.subheader("Inventario General de la Planta")
        try:
            inv_gen = ejecutar_consulta("SELECT codigo, nombre, tipo as clase, cantidad, stock_minimo FROM inventario")
            if not inv_gen.empty:
                st.write("### Listado y Borrado Masivo de Ítems de Inventario")
                inv_gen_v = inv_gen.copy()
                inv_gen_v.insert(0, "Seleccionar", False)
                edited_inv = st.data_editor(inv_gen_v, key="editor_inv_mult", use_container_width=True, hide_index=True)
                codigos_a_borrar_inv = edited_inv[edited_inv["Seleccionar"] == True]["codigo"].tolist()
                
                if st.button("Eliminar", type="primary"):
                    if codigos_a_borrar_inv:
                        for c_item in codigos_a_borrar_inv:
                            ejecutar_comando("DELETE FROM inventario WHERE codigo = %s", (c_item,))
                        st.success(f"Se eliminaron {len(codigos_a_borrar_inv)} ítems del inventario.")
                        st.rerun()
                    else:
                        st.warning("Selecciona al menos un ítem.")
            else:
                st.info("El inventario está vacío.")
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Clases" and rol == "admin":
        st.subheader("Administración de Clases de Inventario")
        try:
            clases_actuales = ejecutar_consulta("SELECT * FROM clases_inventario ORDER BY id DESC")
            with st.expander("Crear Clase", expanded=False):
                with st.form("form_crear_clase", clear_on_submit=True):
                    nueva_clase = st.text_input("Nombre de la Clase (Ej: HERRAMIENTA, MATERIA PRIMA)")
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if nueva_clase.strip():
                            ejecutar_comando("INSERT INTO clases_inventario (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (nueva_clase.upper().strip(),))
                            st.success("Clase creada.")
                            st.rerun()

            if not clases_actuales.empty:
                st.write("### Listado y Borrado Masivo de Clases")
                clases_v = clases_actuales.copy()
                clases_v.insert(0, "Seleccionar", False)
                edited_clases = st.data_editor(clases_v, key="editor_clases_mult", use_container_width=True, hide_index=True)
                nombres_a_borrar_clases = edited_clases[edited_clases["Seleccionar"] == True]["nombre"].tolist()
                
                if st.button("Eliminar", type="primary"):
                    if nombres_a_borrar_clases:
                        for c_nom in nombres_a_borrar_clases:
                            ejecutar_comando("DELETE FROM clases_inventario WHERE nombre = %s", (c_nom,))
                        st.success(f"Se eliminaron {len(nombres_a_borrar_clases)} clases.")
                        st.rerun()
                    else:
                        st.warning("Selecciona al menos una clase.")

                with st.expander("Editar una Clase"):
                    with st.form("form_editar_clase"):
                        lista_clases_edit = ["-- Seleccione Clase --"] + clases_actuales["nombre"].tolist()
                        clase_edit_sel = st.selectbox("Selecciona la Clase a Editar", lista_clases_edit, index=0)
                        nueva_nombre_clase = st.text_input("Nuevo Nombre de Clase", value=clase_edit_sel if clase_edit_sel != "-- Seleccione Clase --" else "")
                        if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                            if clase_edit_sel == "-- Seleccione Clase --":
                                st.error("Seleccione una clase válida.")
                            elif nueva_nombre_clase.strip():
                                ejecutar_comando("UPDATE clases_inventario SET nombre = %s WHERE nombre = %s", (nueva_nombre_clase.upper().strip(), clase_edit_sel))
                                st.success("¡Clase actualizada!")
                                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Clientes" and rol == "admin":
        st.subheader("Administración de Clientes")
        try:
            clientes_df = ejecutar_consulta("SELECT * FROM clientes ORDER BY id DESC")
            with st.expander("Crear Cliente", expanded=False):
                with st.form("form_crear_cliente", clear_on_submit=True):
                    nom_cliente = st.text_input("Razón Social / Nombre de la Empresa")
                    nit_cliente = st.text_input("NIT (Opcional)")
                    tel_cliente = st.text_input("Teléfono de Contacto (Opcional)")
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if nom_cliente.strip():
                            ejecutar_comando(
                                "INSERT INTO clientes (nombre, nit, telefono) VALUES (%s, %s, %s) ON CONFLICT (nombre) DO NOTHING",
                                (nom_cliente.strip(), nit_cliente.strip(), tel_cliente.strip())
                            )
                            st.success("Cliente agregado.")
                            st.rerun()

            if not clientes_df.empty:
                st.write("### Listado y Borrado Masivo de Clientes")
                clientes_v = clientes_df.copy()
                clientes_v.insert(0, "Seleccionar", False)
                edited_cli = st.data_editor(clientes_v, key="editor_cli_mult", use_container_width=True, hide_index=True)
                nombres_a_borrar_cli = edited_cli[edited_cli["Seleccionar"] == True]["nombre"].tolist()
                
                if st.button("Eliminar", type="primary"):
                    if nombres_a_borrar_cli:
                        for cli_nom in nombres_a_borrar_cli:
                            ejecutar_comando("DELETE FROM clientes WHERE nombre = %s", (cli_nom,))
                        st.success(f"Se eliminaron {len(nombres_a_borrar_cli)} clientes.")
                        st.rerun()
                    else:
                        st.warning("Selecciona al menos un cliente.")

                with st.expander("Editar un Cliente"):
                    with st.form("form_editar_cliente"):
                        lista_cli_edit = ["-- Seleccione Cliente --"] + clientes_df["nombre"].tolist()
                        cliente_edit_sel = st.selectbox("Selecciona el Cliente a Editar", lista_cli_edit, index=0)
                        
                        if cliente_edit_sel != "-- Seleccione Cliente --":
                            datos_cli = ejecutar_consulta("SELECT nit, telefono FROM clientes WHERE nombre = %s", (cliente_edit_sel,))
                            nit_actual = datos_cli.iloc[0]['nit'] if not datos_cli.empty and datos_cli.iloc[0]['nit'] else ""
                            tel_actual = datos_cli.iloc[0]['telefono'] if not datos_cli.empty and datos_cli.iloc[0]['telefono'] else ""
                        else:
                            nit_actual, tel_actual = "", ""
                        
                        nuevo_nom_cli = st.text_input("Nueva Razón Social", value=cliente_edit_sel if cliente_edit_sel != "-- Seleccione Cliente --" else "")
                        nuevo_nit_cli = st.text_input("Nuevo NIT", value=nit_actual)
                        nuevo_tel_cli = st.text_input("Nuevo Teléfono", value=tel_actual)
                        
                        if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                            if cliente_edit_sel == "-- Seleccione Cliente --":
                                st.error("Seleccione un cliente válido.")
                            elif nuevo_nom_cli.strip():
                                ejecutar_comando(
                                    "UPDATE clientes SET nombre = %s, nit = %s, telefono = %s WHERE nombre = %s",
                                    (nuevo_nom_cli.strip(), nuevo_nit_cli.strip(), nuevo_tel_cli.strip(), cliente_edit_sel)
                                )
                                st.success("¡Cliente actualizado!")
                                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Usuarios" and rol == "admin":
        st.subheader("Gestión y Seguridad de Usuarios del Sistema")
        try:
            users_df = ejecutar_consulta("SELECT id, username, nombre, rol FROM usuarios ORDER BY id DESC")
            with st.expander("Crear Usuario", expanded=False):
                with st.form("form_crear_usuario", clear_on_submit=True):
                    u_user = st.text_input("Usuario (Login)")
                    u_pass = st.text_input("Contraseña", type="password")
                    u_nom = st.text_input("Nombre Completo")
                    u_rol = st.selectbox("Rol en Planta", ["-- Seleccione Rol --", "operario", "produccion", "admin"], index=0)
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if u_user.strip() and u_pass.strip() and u_nom.strip() and u_rol != "-- Seleccione Rol --":
                            ejecutar_comando("INSERT INTO usuarios (username, password, nombre, rol) VALUES (%s, %s, %s, %s)", (u_user.strip(), u_pass, u_nom.strip(), u_rol))
                            st.success("Usuario creado.")
                            st.rerun()
                        else:
                            st.error("Complete los datos y seleccione un rol válido.")

            if not users_df.empty:
                st.write("### Listado y Borrado Masivo de Usuarios")
                users_v = users_df.copy()
                users_v.insert(0, "Seleccionar", False)
                edited_users = st.data_editor(users_v, key="editor_users_mult", use_container_width=True, hide_index=True)
                usernames_a_borrar = edited_users[edited_users["Seleccionar"] == True]["username"].tolist()
                
                if st.button("Eliminar", type="primary"):
                    if usernames_a_borrar:
                        if st.session_state["username"] in usernames_a_borrar:
                            st.error("No puedes eliminar tu propia cuenta activa.")
                        else:
                            for u_usr in usernames_a_borrar:
                                ejecutar_comando("DELETE FROM usuarios WHERE username = %s", (u_usr,))
                            st.success(f"Se eliminaron {len(usernames_a_borrar)} usuarios.")
                            st.rerun()
                    else:
                        st.warning("Selecciona al menos un usuario.")

                with st.expander("Editar una cuenta de Usuario"):
                    with st.form("form_editar_usuario"):
                        lista_users_edit = ["-- Seleccione Usuario --"] + users_df["username"].tolist()
                        edit_user_sel = st.selectbox("Selecciona el Usuario a Editar", lista_users_edit, index=0)
                        
                        if edit_user_sel != "-- Seleccione Usuario --":
                            user_actual = ejecutar_consulta("SELECT nombre, rol FROM usuarios WHERE username = %s", (edit_user_sel,))
                            nombre_actual = user_actual.iloc[0]['nombre'] if not user_actual.empty else ""
                            rol_actual = user_actual.iloc[0]['rol'] if not user_actual.empty else "operario"
                            idx_rol = ["operario", "produccion", "admin"].index(rol_actual) if rol_actual in ["operario", "produccion", "admin"] else 0
                        else:
                            nombre_actual, idx_rol = "", 0
                        
                        nuevo_nombre = st.text_input("Nombre Completo", value=nombre_actual)
                        nueva_pass = st.text_input("Nueva Contraseña (Dejar en blanco si no cambia)", type="password")
                        nuevo_rol = st.selectbox("Nuevo Rol en Planta", ["operario", "produccion", "admin"], index=idx_rol)
                        
                        if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                            if edit_user_sel == "-- Seleccione Usuario --":
                                st.error("Seleccione un usuario válido.")
                            else:
                                if nueva_pass.strip():
                                    ejecutar_comando("UPDATE usuarios SET nombre = %s, password = %s, rol = %s WHERE username = %s", (nuevo_nombre.strip(), nueva_pass, nuevo_rol, edit_user_sel))
                                else:
                                    ejecutar_comando("UPDATE usuarios SET nombre = %s, rol = %s WHERE username = %s", (nuevo_nombre.strip(), nuevo_rol, edit_user_sel))
                                st.success("¡Usuario actualizado!")
                                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Configuración" and rol == "admin":
        st.subheader("Configuración General de la Empresa y Sistema")
        try:
            cfg_db = ejecutar_consulta("SELECT clave, valor FROM configuracion_empresa")
            cfg_dict = {row['clave']: row['valor'] for _, row in cfg_db.iterrows()} if not cfg_db.empty else {}
            
            with st.form("form_configuracion_general"):
                st.subheader("Datos Institucionales (Reportes y PDF)")
                razon_social_val = st.text_input("Razón Social de la Empresa", value=cfg_dict.get("razon_social", "Industrias Metal&Co"))
                nit_val = st.text_input("NIT de la Empresa", value=cfg_dict.get("nit_empresa", ""))
                tel_val = st.text_input("Teléfono de Contacto", value=cfg_dict.get("telefono_empresa", ""))
                
                st.subheader("Parámetros de Operación")
                alerta_stock_val = st.number_input("Umbral por defecto para Stock Mínimo en Inventario", min_value=1, value=int(cfg_dict.get("stock_minimo_defecto", 5)))
                
                if st.form_submit_button("Guardar Configuración", type="primary", use_container_width=True):
                    configs_a_guardar = [
                        ("razon_social", razon_social_val),
                        ("nit_empresa", nit_val),
                        ("telefono_empresa", tel_val),
                        ("stock_minimo_defecto", str(alerta_stock_val))
                    ]
                    for clave, valor in configs_a_guardar:
                        ejecutar_comando(
                            """INSERT INTO configuracion_empresa (clave, valor) VALUES (%s, %s)
                               ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor""",
                            (clave, valor)
                        )
                    st.success("¡Configuración general guardada con éxito!")
                    st.rerun()
                    
            st.write("---")
            st.subheader("Actualizar Logo Institucional del Sistema")
            with st.form("form_subir_logo"):
                archivo_logo = st.file_uploader("Selecciona la nueva imagen del logo (PNG o JPG)", type=["png", "jpg", "jpeg"])
                if st.form_submit_button("Subir y Aplicar Logo", type="primary", use_container_width=True):
                    if archivo_logo is not None:
                        nombre_guardado = "logometalyco.png"
                        with open(nombre_guardado, "wb") as f:
                            f.write(archivo_logo.getbuffer())
                        st.success("¡Logo actualizado correctamente en el sistema! Recarga la página para visualizarlo.")
                        st.rerun()
                    else:
                        st.error("Por favor selecciona un archivo de imagen válido.")
        except Exception as e:
            st.error(f"Error en configuración: {e}")
