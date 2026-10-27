import streamlit as st
import pandas as pd
import numpy as np
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
from streamlit_option_menu import option_menu
from streamlit_drawable_canvas import st_canvas
from PIL import Image

st.set_page_config(
    page_title="Control de Producción - Industrias Metal&Co",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="auto"
)

# =====================================================
# CONFIGURACIÓN DE ESTILOS CSS GLOBALES Y MENÚ LATERAL
# =====================================================
estilos_css_globales = """
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
        }
        
        [data-testid="stSidebar"] {
            background-color: rgba(26, 26, 26, 0.92);
            backdrop-filter: blur(10px);
            border-right: 2px solid rgba(255, 122, 0, 0.2);
            padding-top: 1rem;
        }

        .stButton>button {
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
        }
        .stButton>button:hover {
            background: linear-gradient(135deg, #ff9124 0%, #FF7A00 100%) !important;
            box-shadow: 0 6px 20px rgba(255, 122, 0, 0.6) !important;
            transform: translateY(-1px) !important;
        }

        .profile-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            margin-bottom: 10px;
        }
        .profile-img {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid #FF7A00;
            box-shadow: 0 4px 15px rgba(255, 122, 0, 0.3);
        }

        .kpi-container {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .kpi-card {
            flex: 1;
            background: linear-gradient(135deg, #1e1e1e 0%, #2a2a2a 100%);
            border: 1px solid rgba(255, 122, 0, 0.2);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.4);
            min-width: 220px;
            transition: transform 0.3s ease;
        }
        .kpi-card:hover {
            border-color: #FF7A00;
            transform: translateY(-2px);
        }
        .kpi-title {
            color: #888888;
            font-size: 0.8rem;
            font-weight: bold;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .kpi-value {
            color: #ffffff;
            font-size: 1.8rem;
            font-weight: 700;
            margin: 0;
        }

        @media (max-width: 768px) {
            .kpi-container {
                flex-direction: column;
            }
            .kpi-card {
                width: 100%;
                min-width: 100%;
            }
        }
    </style>
"""
st.markdown(estilos_css_globales, unsafe_allow_html=True)

img_css_app = "background-color: #121212;"
ruta_fondo_app = "fondo_app.jpg"
if os.path.exists(ruta_fondo_app):
    with open(ruta_fondo_app, "rb") as image_file:
        encoded_app_bg = base64.b64encode(image_file.read()).decode()
        img_css_app = f"background: linear-gradient(rgba(18,18,18,0.85), rgba(18,18,18,0.92)), url('data:image/jpeg;base64,{encoded_app_bg}'); background-size: cover; background-position: center; background-attachment: fixed;"

st.markdown(f"<style>.stApp {{ {img_css_app} }}</style>", unsafe_allow_html=True)

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

@st.cache_data(ttl=5, show_spinner=False)
def ejecutar_consulta_cached(query, params_key=None):
    conn = psycopg2.connect(**DB_PARAMS)
    df = pd.read_sql_query(query, conn, params=list(params_key) if params_key else None)
    conn.close()
    return df

def ejecutar_consulta(query, params=None):
    params_key = tuple(params) if params else None
    return ejecutar_consulta_cached(query, params_key)

def ejecutar_comando(query, params=None):
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute(query, params or ())
    conn.commit()
    cur.close()
    conn.close()
    ejecutar_consulta_cached.clear()

def inicializar_tablas_sistema():
    try:
        ejecutar_comando("""
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(150) UNIQUE NOT NULL,
                nit VARCHAR(50),
                nombre_comercial VARCHAR(150),
                direccion VARCHAR(200),
                ciudad VARCHAR(100),
                telefono VARCHAR(50),
                correo VARCHAR(150),
                contacto VARCHAR(150),
                forma_pago VARCHAR(100)
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
        ejecutar_comando("ALTER TABLE registro_produccion ADD COLUMN IF NOT EXISTS despachado BOOLEAN DEFAULT FALSE;")
        ejecutar_comando("ALTER TABLE programacion_diaria ADD COLUMN IF NOT EXISTS numero_oc VARCHAR(100);")
        ejecutar_comando("ALTER TABLE referencias ADD COLUMN IF NOT EXISTS cliente VARCHAR(150);")
        ejecutar_comando("ALTER TABLE referencias ADD COLUMN IF NOT EXISTS valor_unitario NUMERIC(12,2) DEFAULT 0;")
        
        ejecutar_comando("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS nit VARCHAR(50);")
        ejecutar_comando("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS nombre_comercial VARCHAR(150);")
        ejecutar_comando("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS direccion VARCHAR(200);")
        ejecutar_comando("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS ciudad VARCHAR(100);")
        ejecutar_comando("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS telefono VARCHAR(50);")
        ejecutar_comando("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS correo VARCHAR(150);")
        ejecutar_comando("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS contacto VARCHAR(150);")
        ejecutar_comando("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS forma_pago VARCHAR(100);")

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
    p.drawString(x_margen + 50, y_actual - 26, f"{datos.get('cliente_comercial', datos.get('cliente', 'N/A'))}")
    
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

def generar_pdf_remision_f02_02(datos_remision, items_despacho, firma_img_path=None):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    x_margen = 20  # Margen optimizado para que quepan bien las 9 columnas
    ancho_util = width - 40
    y_actual = height - 35

    if LOGO_PATH and os.path.exists(LOGO_PATH):
        try:
            p.drawImage(LOGO_PATH, x_margen, y_actual - 35, width=100, height=35, preserveAspectRatio=True, mask='auto')
        except:
            p.setFont("Helvetica-Bold", 11)
            p.drawString(x_margen, y_actual - 15, "Metal&Co")
    else:
        p.setFont("Helvetica-Bold", 11)
        p.drawString(x_margen, y_actual - 15, "Metal&Co")

    p.setFont("Helvetica-Bold", 9)
    p.drawString(x_margen + 115, y_actual - 10, "INDUSTRIAS METAL&CO S.A.S")
    p.setFont("Helvetica", 7)
    p.drawString(x_margen + 115, y_actual - 20, "NIT 902024035 | CALLE 79A NO.16-168 LA ROMELIA, DOSQUEBRADAS")
    p.drawString(x_margen + 115, y_actual - 29, "TELÉFONO +57 310 4368657 | metalycosas@gmail.com")

    p.rect(width - 130, y_actual - 35, 110, 35, fill=0, stroke=1)
    p.setFont("Helvetica", 7.5)
    p.drawString(width - 122, y_actual - 12, "Código: F-02-02")
    p.drawString(width - 122, y_actual - 24, "Versión: 1")
    p.setFont("Helvetica-Bold", 8.5)
    p.drawCentredString(width - 75, y_actual - 33, f"NÚMERO: {datos_remision.get('numero_remision', 'S/N')}")

    y_actual -= 45
    p.setLineWidth(0.75)
    p.line(x_margen, y_actual, width - x_margen, y_actual)

    def limpiar_val(val):
        if not val or str(val).lower() == 'none' or str(val).strip() == '':
            return 'N/A'
        return str(val)

    nit_limpio = limpiar_val(datos_remision.get('nit'))
    razon_social_limpia = limpiar_val(datos_remision.get('cliente_nombre'))
    nombre_comercial_limpio = limpiar_val(datos_remision.get('nombre_comercial'))
    dir_limpia = limpiar_val(datos_remision.get('direccion'))
    ciudad_limpia = limpiar_val(datos_remision.get('ciudad'))
    tel_limpio = limpiar_val(datos_remision.get('telefono'))
    correo_limpio = limpiar_val(datos_remision.get('correo'))
    contacto_limpio = limpiar_val(datos_remision.get('contacto'))
    forma_pago_limpia = limpiar_val(datos_remision.get('forma_pago'))

    y_actual -= 15
    p.setFillColorRGB(0.15, 0.15, 0.15)
    p.rect(x_margen, y_actual - 12, ancho_util, 14, fill=1, stroke=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 7.5)
    p.drawCentredString(width / 2.0, y_actual - 8, "DATOS DE DESTINO / CLIENTE")

    y_actual -= 12
    p.setFillColorRGB(0, 0, 0)
    p.rect(x_margen, y_actual - 132, ancho_util, 132, fill=0, stroke=1)

    y_offset = 12
    espacio_linea = 13.5

    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(x_margen + 8, y_actual - y_offset, "CÓDIGO TERCERO (NIT):")
    p.setFont("Helvetica", 7.5)
    p.drawString(x_margen + 130, y_actual - y_offset, f"{nit_limpio}")
    
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(x_margen + 340, y_actual - y_offset, "FECHA DESPACHO:")
    p.setFont("Helvetica", 7.5)
    p.drawString(x_margen + 430, y_actual - y_offset, f"{datos_remision.get('fecha_despacho', '')}")

    y_offset += espacio_linea
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(x_margen + 8, y_actual - y_offset, "RAZÓN SOCIAL:")
    p.setFont("Helvetica", 7.5)
    p.drawString(x_margen + 130, y_actual - y_offset, f"{razon_social_limpia}")

    y_offset += espacio_linea
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(x_margen + 8, y_actual - y_offset, "NOMBRE COMERCIAL:")
    p.setFont("Helvetica", 7.5)
    p.drawString(x_margen + 130, y_actual - y_offset, f"{nombre_comercial_limpio}")

    y_offset += espacio_linea
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(x_margen + 8, y_actual - y_offset, "DIRECCIÓN:")
    p.setFont("Helvetica", 7.5)
    p.drawString(x_margen + 130, y_actual - y_offset, f"{dir_limpia}")

    y_offset += espacio_linea
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(x_margen + 8, y_actual - y_offset, "CIUDAD:")
    p.setFont("Helvetica", 7.5)
    p.drawString(x_margen + 130, y_actual - y_offset, f"{ciudad_limpia}")

    y_offset += espacio_linea
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(x_margen + 8, y_actual - y_offset, "TELÉFONO:")
    p.setFont("Helvetica", 7.5)
    p.drawString(x_margen + 130, y_actual - y_offset, f"{tel_limpio}")

    y_offset += espacio_linea
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(x_margen + 8, y_actual - y_offset, "CORREO:")
    p.setFont("Helvetica", 7.5)
    p.drawString(x_margen + 130, y_actual - y_offset, f"{correo_limpio}")

    y_offset += espacio_linea
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(x_margen + 8, y_actual - y_offset, "CONTACTO:")
    p.setFont("Helvetica", 7.5)
    p.drawString(x_margen + 130, y_actual - y_offset, f"{contacto_limpio}")

    y_offset += espacio_linea
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(x_margen + 8, y_actual - y_offset, "FORMA PAGO:")
    p.setFont("Helvetica", 7.5)
    p.drawString(x_margen + 130, y_actual - y_offset, f"{forma_pago_limpia}")

    y_actual -= 142
    p.setFillColorRGB(0.15, 0.15, 0.15)
    p.rect(x_margen, y_actual - 14, ancho_util, 14, fill=1, stroke=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 7.5)
    p.drawCentredString(width / 2.0, y_actual - 9, "PRODUCTOS DESPACHADOS Y/O TROQUELES ENVIADOS")

    y_actual -= 14
    p.setFillColorRGB(0, 0, 0)
    p.rect(x_margen, y_actual - 18, ancho_util, 18, fill=0, stroke=1)
    
    # Anchos de las 9 columnas exactas que coinciden con tu formato F-02-02
    w_desc = 135
    w_cod = 60
    w_op = 42
    w_oc = 55
    w_und = 42
    w_cant = 42
    w_val = 65
    w_iva = 32
    w_sub = 99  # Total ancho_util = 572
    
    x_col = x_margen
    p.setFont("Helvetica-Bold", 6)
    p.drawString(x_col + 3, y_actual - 12, "DESCRIPCIÓN PRODUCTO")
    
    x_col += w_desc
    p.drawString(x_col + 2, y_actual - 12, "CÓDIGO PROD.")
    
    x_col += w_cod
    p.drawString(x_col + 2, y_actual - 12, "OP")
    
    x_col += w_op
    p.drawString(x_col + 2, y_actual - 12, "OC U OTRO")
    
    x_col += w_oc
    p.drawString(x_col + 2, y_actual - 12, "UND")
    
    x_col += w_und
    p.drawString(x_col + 2, y_actual - 12, "CANTIDAD")
    
    x_col += w_cant
    p.drawString(x_col + 2, y_actual - 12, "PRECIO UNIT.")
    
    x_col += w_val
    p.drawString(x_col + 2, y_actual - 12, "%IVA")
    
    x_col += w_iva
    p.drawString(x_col + 2, y_actual - 12, "SUBTOTAL")

    y_actual -= 18
    subtotal_general = 0.0
    iva_general = 0.0

    for item in items_despacho:
        p.rect(x_margen, y_actual - 16, ancho_util, 16, fill=0, stroke=1)
        p.setFont("Helvetica", 6.5)
        
        xc = x_margen
        p.drawString(xc + 3, y_actual - 11, str(item.get('descripcion', ''))[:38])
        
        xc += w_desc
        p.drawString(xc + 2, y_actual - 11, str(item.get('codigo_producto', 'N/A'))[:15])
        
        xc += w_cod
        p.drawString(xc + 2, y_actual - 11, str(item.get('op', 'N/A'))[:10])
        
        xc += w_op
        p.drawString(xc + 2, y_actual - 11, str(item.get('oc', 'N/A'))[:12])
        
        xc += w_oc
        p.drawString(xc + 2, y_actual - 11, str(item.get('unidad', 'UND'))[:6])
        
        xc += w_und
        cant_val = int(item.get('cantidad', 0))
        p.drawString(xc + 2, y_actual - 11, f"{cant_val:,}")
        
        xc += w_cant
        val_unit = float(item.get('precio_unitario', 0.0))
        p.drawString(xc + 2, y_actual - 11, f"${val_unit:,.2f}")
        
        xc += w_val
        iva_pct = float(item.get('iva_porcentaje', 19))
        p.drawString(xc + 2, y_actual - 11, f"{int(iva_pct)}%")
        
        sub_val = float(item.get('subtotal', 0.0))
        item_iva = sub_val * (iva_pct / 100.0)
        subtotal_general += sub_val
        iva_general += item_iva
        
        xc += w_iva
        p.drawString(xc + 2, y_actual - 11, f"${sub_val:,.2f}")
        
        y_actual -= 16

    total_general = subtotal_general + iva_general

    y_actual -= 10
    p.rect(x_margen, y_actual - 45, 300, 45, fill=0, stroke=1)
    p.setFont("Helvetica-Bold", 7)
    p.drawString(x_margen + 6, y_actual - 10, "NOTAS Y CONDICIONES LOGÍSTICAS:")
    p.setFont("Helvetica", 6.5)
    p.drawString(x_margen + 6, y_actual - 22, "- Horario de despachos: Lunes a Viernes 6:00 am a 2:00 pm.")
    p.drawString(x_margen + 6, y_actual - 33, f"- Observaciones: {datos_remision.get('observaciones', 'Ninguna')}")

    p.rect(x_margen + 305, y_actual - 45, ancho_util - 305, 45, fill=0, stroke=1)
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(x_margen + 315, y_actual - 12, f"SUBTOTAL: ${subtotal_general:,.2f}")
    p.drawString(x_margen + 315, y_actual - 26, f"IVA (19%): ${iva_general:,.2f}")
    p.setFont("Helvetica-Bold", 8.5)
    p.drawString(x_margen + 315, y_actual - 40, f"TOTAL: ${total_general:,.2f}")

    y_actual -= 55
    p.rect(x_margen, y_actual - 45, ancho_util, 45, fill=0, stroke=1)
    p.setFont("Helvetica-Bold", 7)
    p.drawString(x_margen + 8, y_actual - 12, f"SOLICITADO: {datos_remision.get('elaborado', 'Felipe Valdés')}")
    p.drawString(x_margen + 250, y_actual - 12, f"ELABORADO: {datos_remision.get('elaborado', 'Felipe Valdés')}")
    p.drawString(x_margen + 8, y_actual - 28, f"RECIBE: {datos_remision.get('recibe_nombre', '')} - CC: {datos_remision.get('recibe_cc', '')}")
    
    if firma_img_path and os.path.exists(firma_img_path):
        try:
            p.drawImage(firma_img_path, x_margen + 380, y_actual - 34, width=85, height=20, preserveAspectRatio=True, mask='auto')
        except:
            pass
    p.drawString(x_margen + 350, y_actual - 35, "___________________________________")
    p.drawString(x_margen + 350, y_actual - 43, "Firma de quien recibe conforme")

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
    
    rol = st.session_state["rol"]
    
    if rol == "operario":
        opciones_menu = ["Mi Programación", "Registrar Producción", "Tarea Imprevista"]
        iconos_menu = ["calendar-check", "clipboard-plus", "exclamation-triangle"]
    elif rol == "produccion":
        opciones_menu = ["Vista General", "Programar", "Órdenes Compra", "Referencias", "Reportes", "Entregas", "Herramientas", "Cargue Ítems", "Inventario", "Despachos (F-02-02)"]
        iconos_menu = ["grid", "calendar3", "cart3", "journal-richtext", "file-earmark-bar-graph", "box-arrow-right", "wrench", "cloud-arrow-up", "archive", "truck"]
    else:  # Admin
        opciones_menu = [
            "Vista General", "Programar", "Órdenes Compra", "Máquinas", "Servicios", 
            "Referencias", "Reportes", "Entregas", "Herramientas", 
            "Cargue Ítems", "Inventario", "Clases", "Clientes", "Usuarios", "Configuración", "Despachos (F-02-02)"
        ]
        iconos_menu = [
            "grid", "calendar3", "cart3", "cpu", "tools", 
            "journal-richtext", "file-earmark-bar-graph", "box-arrow-right", "wrench", 
            "cloud-arrow-up", "archive", "tags", "building", "people", "gear", "truck"
        ]
    
    menu_seleccionado = option_menu(
        menu_title="Menú Principal",
        options=opciones_menu,
        icons=iconos_menu,
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#FF7A00", "font-size": "15px"}, 
            "nav-link": {
                "font-size": "0.93rem", 
                "text-align": "left", 
                "margin": "4px 0px", 
                "border-radius": "12px",
                "color": "#C0C0C0",
                "border": "1px solid rgba(255, 255, 255, 0.08)",
                "transition": "all 0.3s ease",
                "--hover-color": "rgba(255, 122, 0, 0.18)"
            },
            "nav-link-selected": {
                "background-color": "rgba(255, 122, 0, 0.15)",
                "color": "#FF7A00",
                "font-weight": "bold",
                "border": "1px solid #FF7A00",
                "box-shadow": "0 0 15px rgba(255, 122, 0, 0.4)"
            },
            "menu-title": {
                "color": "#888888",
                "font-size": "0.85rem",
                "font-weight": "bold",
                "text-transform": "uppercase",
                "margin-bottom": "8px"
            }
        }
    )
    
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
                
                tarea_elegida_str = st.selectbox("Selecciona la Tarea a Registrar", lista_opciones, index=0, key="select_tarea_operario_dinamico")
                
                with st.form("form_reporte_operario"):
                    presion_input = st.text_input("Presión de Trabajo (Ej: 150 Ton / 25 MPa / N/A)", key="input_presion_operario")
                    
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
                            
                            cli_com_db = ejecutar_consulta("SELECT nombre_comercial FROM clientes WHERE nombre = %s", (cliente_nombre,))
                            cliente_comercial_val = cli_com_db.iloc[0]['nombre_comercial'] if not cli_com_db.empty and pd.notna(cli_com_db.iloc[0]['nombre_comercial']) else cliente_nombre
                            
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
                                    meta_total_oc = int(oc_db.iloc[0]['meta_unidades']) if pd.notna(oc_db.iloc[0]['meta_unidades']) else nuevo_entregado
                                    estado_oc_calc = 'COMPLETADO' if nuevo_entregado >= meta_total_oc else 'PENDIENTE'
                                    
                                    ejecutar_comando(
                                        "UPDATE ordenes_compra SET unidades_entregadas = %s, estado = %s WHERE numero_oc = %s AND referencia = %s",
                                        (nuevo_entregado, estado_oc_calc, num_oc_asociada, referencia_pieza)
                                    )

                            ejecutar_comando("UPDATE programacion_diaria SET estado = 'FINALIZADO' WHERE id = %s", (id_tarea,))
                            
                            datos_pdf = {
                                "fecha": fecha_exacta_actual,
                                "numero_oc": num_oc_asociada,
                                "cliente": cliente_nombre,
                                "cliente_comercial": cliente_comercial_val,
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
                                st.warning(f"Producción registrada. Atención: Se reportaron piezas pendientes por completar ({meta_asignada_tarea - unidades} u. faltantes).")
                            else:
                                st.success("Producción registrada y formato F-01-01 generado con éxito.")

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
            
            ocs_disp = ["-- Seleccione OC --"]
            mapa_oc_cliente = {}
            if not ocs_db.empty:
                for _, row in ocs_db.iterrows():
                    oc_num = row['numero_oc']
                    cli_nom = row['cliente']
                    ocs_disp.append(oc_num)
                    mapa_oc_cliente[oc_num] = cli_nom
            
            maqs = ["-- Seleccione Máquina --"] + maqs_raw
            refs = ["-- Seleccione Referencia --"] + refs_raw
            serv_db = ["-- Seleccione Actividad --"] + (serv_raw if serv_raw else [])
            
            if not maqs_raw or not refs_raw or not serv_raw or len(ocs_disp) <= 1:
                st.warning("Debes tener máquinas, servicios y Órdenes de Compra activas registradas para reportar una tarea imprevista.")
            else:
                with st.form("form_tarea_imprevista"):
                    oc_imp = st.selectbox("Orden de Compra Asociada", ocs_disp, index=0)
                    cliente_asociado_oc = mapa_oc_cliente.get(oc_imp, "N/A")
                    if oc_imp != "-- Seleccione OC --":
                        st.info(f"Cliente asociado automáticamente: `{cliente_asociado_oc}`")
                    
                    maq_imp = st.selectbox("Máquina", maqs, index=0)
                    presion_imp = st.text_input("Presión de Trabajo (Ej: 150 Ton / 25 MPa / N/A)", key="input_presion_imprevista")
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
                    
                    submit_imp = st.form_submit_button("Guardar", type="primary", use_container_width=True)
                    
                    if submit_imp:
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

                            cli_com_db_imp = ejecutar_consulta("SELECT nombre_comercial FROM clientes WHERE nombre = %s", (cliente_asociado_oc,))
                            cliente_comercial_val_imp = cli_com_db_imp.iloc[0]['nombre_comercial'] if not cli_com_db_imp.empty and pd.notna(cli_com_db_imp.iloc[0]['nombre_comercial']) else cliente_asociado_oc

                            datos_pdf_imp = {
                                "fecha": fecha_exacta_actual_imp,
                                "numero_oc": oc_imp,
                                "cliente": cliente_asociado_oc,
                                "cliente_comercial": cliente_comercial_val_imp,
                                "referencia": ref_imp,
                                "maquina": maq_imp,
                                "actividad": act_imp,
                                "presion": presion_imp,
                                "hora_inicio": str(h_ini_imp),
                                "hora_fin": str(h_fin_imp),
                                "producidas": uni_imp,
                                "defectuosas": def_imp,
                                "observaciones": obs_final_imp,
                                "operario": st.session_state['nombre_usuario']
                            }
                            
                            pdf_buffer_imp = generar_pdf_f01_01(datos_pdf_imp)
                            st.session_state["ultimo_pdf_buffer_imp"] = pdf_buffer_imp.getvalue()
                            st.session_state["ultimo_pdf_nombre_imp"] = f"F-01-01_IMPREVISTO_OC_{oc_imp}_{ref_imp}.pdf"
                            st.success("Tarea imprevista registrada y formato F-01-01 generado con éxito.")

            if "ultimo_pdf_buffer_imp" in st.session_state:
                st.markdown("---")
                st.write("### Formato F-01-01 (Tarea Imprevista) Listo para Descargar")
                st.download_button(
                    label="Descargar Formato F-01-01 (PDF Oficial)",
                    data=st.session_state["ultimo_pdf_buffer_imp"],
                    file_name=st.session_state["ultimo_pdf_nombre_imp"],
                    mime="application/pdf",
                    use_container_width=True
                )
                
                texto_wsp_imp = f"Hola, comparto el formato de tarea imprevista F-01-01 completado por el operario *{st.session_state['nombre_usuario']}*."
                link_whatsapp_imp = f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto_wsp_imp)}"
                st.markdown(f'<a href="{link_whatsapp_imp}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; height:3rem; font-size:1.1rem; font-weight:bold; border:none; border-radius:8px; cursor:pointer;">Enviar Aviso por WhatsApp</button></a>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error al cargar formulario: {e}")

# ====================================================
# VISTA PARA ADMINISTRADOR Y PRODUCCIÓN (DASHBOARD PROFESIONAL)
# ====================================================
elif rol in ["admin", "produccion"]:
    
    if menu_limpio == "Vista General":
        st.subheader("Dashboard Gerencial de Planta - Control en Tiempo Real")
        
        try:
            df_kpi_base = ejecutar_consulta("""
                SELECT * FROM registro_produccion 
                WHERE numero_oc IS NOT NULL 
                AND TRIM(numero_oc) <> '' 
                AND UPPER(TRIM(numero_oc)) <> 'SIN OC'
            """)
            
            ops_list_db = df_kpi_base['operario_nombre'].dropna().unique().tolist() if not df_kpi_base.empty else []
            refs_list_db = df_kpi_base['referencia'].dropna().unique().tolist() if not df_kpi_base.empty else []
        except:
            ops_list_db = []
            refs_list_db = []
            df_kpi_base = pd.DataFrame()
            
        opciones_operario_filtro = ["Todos"] + ops_list_db
        opciones_mes_filtro = ["Todas", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        opciones_ref_filtro = ["Todas"] + refs_list_db
        
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            filtro_op_sel = st.selectbox("Filtrar por Operador", opciones_operario_filtro)
        with f_col2:
            filtro_mes_sel = st.selectbox("Filtrar por Mes", opciones_mes_filtro)
        with f_col3:
            filtro_ref_sel = st.selectbox("Filtrar por Referencia / SKU", opciones_ref_filtro)
        with f_col4:
            usar_rango_fechas = st.checkbox("Activar Rango de Fechas", value=False)
            
        if usar_rango_fechas:
            r_col1, r_col2 = st.columns(2)
            with r_col1:
                fecha_ini_filtro = st.date_input("Fecha Inicio", value=(datetime.utcnow() - timedelta(days=7)).date())
            with r_col2:
                fecha_fin_filtro = st.date_input("Fecha Fin", value=(datetime.utcnow() - timedelta(hours=5)).date())
            
        st.markdown("<br>", unsafe_allow_html=True)

        try:
            if not df_kpi_base.empty:
                if filtro_op_sel != "Todos":
                    df_kpi_base = df_kpi_base[df_kpi_base['operario_nombre'].astype(str).str.strip().str.lower() == filtro_op_sel.strip().lower()]
                
                if filtro_mes_sel != "Todas" and 'fecha_registro' in df_kpi_base.columns:
                    df_kpi_base['dt_temp'] = pd.to_datetime(df_kpi_base['fecha_registro'], errors='coerce')
                    meses_dict_rev = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
                    df_kpi_base['mes_nombre'] = df_kpi_base['dt_temp'].dt.month.map(meses_dict_rev)
                    df_kpi_base = df_kpi_base[df_kpi_base['mes_nombre'] == filtro_mes_sel]
                
                if filtro_ref_sel != "Todas":
                    df_kpi_base = df_kpi_base[df_kpi_base['referencia'].astype(str).str.strip().str.lower() == filtro_ref_sel.strip().lower()]
                    
                if usar_rango_fechas and 'fecha_registro' in df_kpi_base.columns:
                    df_kpi_base['dt_temp'] = pd.to_datetime(df_kpi_base['fecha_registro'], errors='coerce').dt.date
                    df_kpi_base = df_kpi_base[(df_kpi_base['dt_temp'] >= fecha_ini_filtro) & (df_kpi_base['dt_temp'] <= fecha_fin_filtro)]

            total_buenas = int(df_kpi_base['unidades_producidas'].sum()) if not df_kpi_base.empty else 0
            total_horas = float(df_kpi_base['horas_trabajadas'].sum()) if not df_kpi_base.empty else 0.0
            
            total_defectuosas = 0
            if not df_kpi_base.empty:
                for _, row_k in df_kpi_base.iterrows():
                    obs_k = str(row_k.get('observaciones', ''))
                    if 'Defectuosas:' in obs_k:
                        try:
                            partes_k = obs_k.split('Defectuosas:')
                            num_sc_k = int(partes_k[1].split(',')[0].split('.')[0].strip())
                            total_defectuosas += num_sc_k
                        except:
                            pass
                            
            total_producidas_kpi = total_buenas + total_defectuosas
            tasa_scrap_real = round((total_defectuosas / total_producidas_kpi * 100), 2) if total_producidas_kpi > 0 else 0.0
            
            uph_global = round(total_buenas / total_horas, 1) if total_horas > 0 else 0.0
            oee_estimado = min(100.0, round((uph_global / 130.0) * 100, 1)) if uph_global > 0 else 0.0
            
            horas_disponibles_teoricas = max(1.0, total_horas * 1.2)
            disponibilidad_maq = min(100.0, round((total_horas / horas_disponibles_teoricas) * 100, 1)) if total_horas > 0 else 0.0

        except Exception as e:
            total_buenas, total_defectuosas, total_producidas_kpi, tasa_scrap_real, oee_estimado, disponibilidad_maq = 0, 0, 0, 0.0, 0.0, 0.0

        kpi_html = f"""
            <div class="kpi-container">
                <div class="kpi-card">
                    <div class="kpi-title">OEE % (Eficiencia Global)</div>
                    <div class="kpi-value" style="color: #2a9d8f;">{oee_estimado}%</div>
                    <span style="font-size: 0.75rem; color: #888;">Meta: &gt; 85.0%</span>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Disponibilidad de Máquinas</div>
                    <div class="kpi-value" style="color: #457b9d;">{disponibilidad_maq}%</div>
                    <span style="font-size: 0.75rem; color: #888;">Tiempo operativo real</span>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Total Piezas Producidas</div>
                    <div class="kpi-value">{total_buenas:,}</div>
                    <span style="font-size: 0.75rem; color: #2a9d8f;">Registradas en BD</span>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Tasa de Rechazo / Scrap</div>
                    <div class="kpi-value" style="color: #e9c46a;">{tasa_scrap_real}%</div>
                    <span style="font-size: 0.75rem; color: #888;">Defectuosas: {total_defectuosas} u.</span>
                </div>
            </div>
        """
        st.markdown(kpi_html, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        try:
            df_stock_critico = ejecutar_consulta("SELECT codigo, nombre, cantidad, stock_minimo FROM inventario WHERE cantidad <= stock_minimo")
            if not df_stock_critico.empty:
                st.markdown("#### Alertas de Stock Crítico en Inventario")
                for _, row_sc in df_stock_critico.iterrows():
                    st.warning(f"¡Atención! El ítem **{row_sc['nombre']}** (Código: `{row_sc['codigo']}`) tiene **{row_sc['cantidad']} unidades**, lo cual está en o por debajo del stock mínimo permitido ({row_sc['stock_minimo']} u.).")
                st.markdown("<br>", unsafe_allow_html=True)
        except:
            pass

        col_graf1, col_graf2 = st.columns([2, 1])

        with col_graf1:
            st.markdown("#### Rendimiento UPH Real (Área Sombreada UI/UX) vs Meta")
            try:
                if not df_kpi_base.empty and 'fecha_registro' in df_kpi_base.columns:
                    df_uph_real = df_kpi_base.groupby('fecha_registro').agg({
                        'unidades_producidas': 'sum',
                        'horas_trabajadas': 'sum'
                    }).reset_index()
                    df_uph_real.columns = ['fecha', 'produccion', 'horas']
                    df_uph_real = df_uph_real.sort_values('fecha')
                else:
                    df_uph_real = pd.DataFrame()
            except:
                df_uph_real = pd.DataFrame()

            if not df_uph_real.empty and df_uph_real['horas'].sum() > 0:
                df_uph_real['UPH'] = df_uph_real.apply(lambda r: round(r['produccion'] / r['horas'], 1) if r['horas'] > 0 else 0, axis=1)
                df_uph_real['Meta'] = 130

                fig_uph = px.area(
                    df_uph_real, 
                    x='fecha', 
                    y='UPH',
                    markers=True,
                    color_discrete_sequence=['#FF7A00']
                )
                
                fig_uph.add_trace(
                    go.Scatter(
                        x=df_uph_real['fecha'], 
                        y=df_uph_real['Meta'], 
                        mode='lines', 
                        name='Meta (130 UPH)',
                        line=dict(color='#e76f51', dash='dash', width=2)
                    )
                )
            else:
                fig_uph = go.Figure()
                fig_uph.add_annotation(
                    text="No hay registros de producción activos en la base de datos", 
                    x=0.5, y=0.5, showarrow=False, 
                    font=dict(color="#888", size=14)
                )

            fig_uph.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(26,26,26,0.5)',
                font_color="#E0E0E0",
                margin=dict(t=20, b=20, l=20, r=20),
                height=350,
                xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', title="Fecha de Registro"),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', title="Unidades / Hora (UPH)"),
                legend=dict(orientation="h", y=1.1, x=0)
            )
            st.plotly_chart(fig_uph, use_container_width=True)

        with col_graf2:
            st.markdown("#### Distribución de Defectos y Calidad")
            if total_defectuosas > 0:
                df_defectos_real = pd.DataFrame({
                    'Causa': ['Defecto Material', 'Ajuste Máquina', 'Operario', 'Otros'],
                    'Valores': [max(1, int(total_defectuosas * 0.5)), max(1, int(total_defectuosas * 0.3)), max(1, int(total_defectuosas * 0.2)), 1]
                })
                fig_dona = px.pie(
                    df_defectos_real, 
                    names='Causa', 
                    values='Valores',
                    hole=0.6,
                    color_discrete_sequence=['#FF7A00', '#e76f51', '#e9c46a', '#457b9d']
                )
            else:
                fig_dona = go.Figure()
                fig_dona.add_annotation(text="Sin defectos registrados", x=0.5, y=0.5, showarrow=False, font=dict(color="#888", size=14))

            fig_dona.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color="#E0E0E0",
                margin=dict(t=20, b=20, l=10, r=10),
                height=350,
                legend=dict(orientation="h", y=-0.2, font=dict(size=10))
            )
            st.plotly_chart(fig_dona, use_container_width=True)

        st.markdown("---")

        col_pred1, col_pred2 = st.columns(2)

        with col_pred1:
            st.markdown("#### Proyección de Cierre de Órdenes (Forecasting)")
            try:
                df_forecasting = ejecutar_consulta("SELECT numero_oc, referencia, meta_unidades, unidades_entregadas FROM ordenes_compra WHERE estado != 'COMPLETADO'")
                if not df_forecasting.empty:
                    df_forecasting['Pendientes'] = df_forecasting['meta_unidades'] - df_forecasting['unidades_entregadas'].fillna(0)
                    df_forecasting['Estado Proyección'] = df_forecasting['Pendientes'].apply(lambda p: "A tiempo" if p < 500 else "Riesgo de Retraso")
                    st.dataframe(df_forecasting[['numero_oc', 'referencia', 'Pendientes', 'Estado Proyección']], use_container_width=True, hide_index=True)
                else:
                    st.info("No hay órdenes activas pendientes en la base de datos.")
            except:
                st.info("Sin datos suficientes para pronóstico.")

        with col_pred2:
            st.markdown("#### 👥 Desempeño Acumulado por Operario")
            try:
                if not df_kpi_base.empty:
                    df_ops_perf = df_kpi_base.groupby('operario_nombre')['unidades_producidas'].sum().reset_index()
                    df_ops_perf.columns = ['operario_nombre', 'total_prod']
                else:
                    df_ops_perf = pd.DataFrame()

                if not df_ops_perf.empty and df_ops_perf['total_prod'].sum() > 0:
                    lista_operarios_grafico = ["Todos los Operarios"] + df_ops_perf['operario_nombre'].dropna().tolist()
                    operario_seleccionado_grafico = st.selectbox("Filtrar vista por operario:", lista_operarios_grafico, key="select_operario_grafico_ui")
                    
                    if operario_seleccionado_grafico != "Todos los Operarios":
                        df_ops_filtrado = df_ops_perf[df_ops_perf['operario_nombre'] == operario_seleccionado_grafico]
                    else:
                        df_ops_filtrado = df_ops_perf
                    
                    if not df_ops_filtrado.empty:
                        fig_ops = px.bar(
                            df_ops_filtrado, 
                            x='operario_nombre', 
                            y='total_prod', 
                            color='operario_nombre', 
                            color_discrete_sequence=['#FF7A00', '#e76f51', '#457b9d', '#2a9d8f', '#e9c46a'],
                            text='total_prod'
                        )
                        fig_ops.update_traces(texttemplate='%{text:,} u.', textposition='outside', marker_line_color='#FFA500', marker_line_width=2, opacity=0.95, width=0.4 if len(df_ops_filtrado) == 1 else 0.7)
                        fig_ops.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(26,26,26,0.4)', font_color="#E0E0E0", margin=dict(t=40, b=10, l=10, r=10), height=280, showlegend=False, xaxis=dict(title=dict(text="Operario Asignado", font=dict(size=11, color="#888")), showgrid=False, categoryorder="total descending"), yaxis=dict(title=dict(text="Unidades Producidas", font=dict(size=11, color="#888")), showgrid=True, gridcolor='rgba(255,255,255,0.05)'))
                        st.plotly_chart(fig_ops, use_container_width=True)
                else:
                    st.info("No hay registros de producción para graficar el desempeño de operarios.")
            except:
                st.info("Sin registros de producción.")

        st.markdown("---")
        st.markdown("#### Estatus de Órdenes de Trabajo Activas (Base de Datos)")
        try:
            df_tabla_ocs_real = ejecutar_consulta("SELECT numero_oc, cliente, referencia, meta_unidades, unidades_entregadas FROM ordenes_compra ORDER BY id DESC LIMIT 10")
        except:
            df_tabla_ocs_real = pd.DataFrame()

        if not df_tabla_ocs_real.empty:
            df_tabla_ocs_real.columns = ['ID_Orden', 'Cliente', 'Referencia', 'Cant_Planificada', 'Cant_Completada']
            def badge_estado_real(row):
                entregado = row['Cant_Completada'] if pd.notna(row['Cant_Completada']) else 0
                meta = row['Cant_Planificada']
                if entregado >= meta:
                    return "Completada"
                elif entregado > 0:
                    return "En Proceso"
                else:
                    return "Sin Iniciar"
            df_tabla_ocs_real['Estado'] = df_tabla_ocs_real.apply(badge_estado_real, axis=1)
            st.dataframe(df_tabla_ocs_real[['ID_Orden', 'Cliente', 'Referencia', 'Cant_Planificada', 'Cant_Completada', 'Estado']], use_container_width=True, hide_index=True)
        else:
            st.info("No hay órdenes de compra registradas actualmente.")

    elif menu_limpio == "Programar":
        st.subheader("Programación Directa por Orden de Compra y Referencia")
        fecha_seleccionada = st.date_input("Selecciona el día a consultar/programar", value=(datetime.utcnow() - timedelta(hours=5)).date(), key="cal_admin_dia")
        try:
            ops_raw = ejecutar_consulta("SELECT nombre FROM usuarios WHERE rol = 'operario'")['nombre'].tolist()
            maqs_raw = ejecutar_consulta("SELECT nombre FROM maquinas")['nombre'].tolist()
            ops = ["-- Seleccione Operario --"] + (ops_raw if ops_raw else [])
            maqs = ["-- Seleccione Máquina --"] + (maqs_raw if maqs_raw else [])
            
            ocs_db = ejecutar_consulta("SELECT id, numero_oc, referencia, servicio, meta_unidades FROM ordenes_compra WHERE estado != 'COMPLETADO' OR estado IS NULL")
            prog_activas = ejecutar_consulta("SELECT DISTINCT numero_oc, referencia FROM programacion_diaria WHERE estado NOT IN ('FINALIZADO', 'CANCELADO')")
            
            tuplas_ya_programadas = set()
            if not prog_activas.empty:
                for _, p_row in prog_activas.iterrows():
                    tuplas_ya_programadas.add((str(p_row['numero_oc']).strip(), str(p_row['referencia']).strip()))

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
                    info_ocs_dict[clave_combinada] = {"id_oc": oc_id, "numero_oc": oc_num, "referencia": ref_val, "servicio": str(r['servicio']).strip(), "meta": int(r['meta_unidades'])}

            if not ops_raw or not maqs_raw or len(ocs_activas_validas) <= 1:
                st.warning("No hay Órdenes de Compra, Referencias o Máquinas disponibles para programar.")
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
                                st.success(f"Tarea asignada a {op_p} con éxito.")
                                st.rerun()
            
            st.write("---")
            df_prog_actual = ejecutar_consulta("SELECT * FROM programacion_diaria WHERE fecha = %s ORDER BY id DESC", (fecha_seleccionada,))
            if not df_prog_actual.empty:
                df_prog_actual.insert(0, "Seleccionar", False)
                edited_prog = st.data_editor(df_prog_actual, key="editor_prog_mult", use_container_width=True, hide_index=True)
                ids_a_borrar_prog = edited_prog[edited_prog["Seleccionar"] == True]["id"].tolist()
                if st.button("Eliminar", type="primary"):
                    if ids_a_borrar_prog:
                        for id_p in ids_a_borrar_prog:
                            ejecutar_comando("DELETE FROM programacion_diaria WHERE id = %s", (id_p,))
                        st.success("Programaciones eliminadas.")
                        st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Órdenes Compra":
        st.subheader("Gestion de OC")
        try:
            refs_raw = ejecutar_consulta("SELECT codigo FROM referencias")['codigo'].tolist() if not ejecutar_consulta("SELECT codigo FROM referencias").empty else []
            serv_raw = ejecutar_consulta("SELECT nombre FROM servicios_prestados")['nombre'].tolist() if not ejecutar_consulta("SELECT nombre FROM servicios_prestados").empty else []
            clientes_raw = ejecutar_consulta("SELECT nombre FROM clientes")['nombre'].tolist() if not ejecutar_consulta("SELECT nombre FROM clientes").empty else []
            
            lista_refs = ["-- Seleccione Referencia --"] + refs_raw
            lista_servicios = ["-- Seleccione Servicio --"] + (serv_raw if serv_raw else [])
            lista_clientes = ["-- Seleccione Cliente --"] + clientes_raw
            
            with st.expander("Crear Orden de Compra", expanded=True):
                with st.form("form_crear_oc", clear_on_submit=True):
                    num_oc = st.text_input("Número de Orden de Compra (Ej: OC-9021)")
                    cliente_oc = st.selectbox("Cliente Asociado", lista_clientes, index=0)
                    ref_oc = st.selectbox("Referencia Base", lista_refs, index=0)
                    servicio_oc = st.selectbox("Servicio Prestado", lista_servicios, index=0)
                    meta_oc = st.number_input("Cantidad Total Pedida", min_value=1, value=100)
                    
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if not num_oc.strip() or cliente_oc == "-- Seleccione Cliente --" or ref_oc == "-- Seleccione Referencia --" or servicio_oc == "-- Seleccione Servicio --":
                            st.error("Completa todos los campos obligatorios.")
                        else:
                            ej_fecha = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y-%m-%d')
                            ejecutar_comando(
                                """INSERT INTO ordenes_compra 
                                (numero_oc, cliente, referencia, servicio, requiere_unidades, meta_unidades, unidades_entregadas, estado, fecha_registro) 
                                VALUES (%s, %s, %s, %s, TRUE, %s, 0, 'PENDIENTE', %s::date)""",
                                (num_oc.upper().strip(), cliente_oc, ref_oc, servicio_oc, meta_oc, ej_fecha)
                            )
                            st.success(f"Orden de Compra #{num_oc} registrada con éxito.")
                            st.rerun()

            st.write("---")
            df_oc = ejecutar_consulta("SELECT * FROM ordenes_compra ORDER BY id DESC")
            if not df_oc.empty:
                df_oc['saldo_pendiente'] = df_oc['meta_unidades'] - df_oc['unidades_entregadas'].fillna(0)
                df_oc_view = df_oc[['id', 'numero_oc', 'cliente', 'referencia', 'meta_unidades', 'unidades_entregadas', 'saldo_pendiente', 'estado']].copy()
                df_oc_view.insert(0, "Seleccionar", False)
                edited_oc = st.data_editor(df_oc_view, key="editor_oc_mult", use_container_width=True, hide_index=True)
                ids_a_borrar_oc = edited_oc[edited_oc["Seleccionar"] == True]["id"].tolist()
                if st.button("Eliminar", type="primary"):
                    if ids_a_borrar_oc:
                        for id_oc in ids_a_borrar_oc:
                            ejecutar_comando("DELETE FROM ordenes_compra WHERE id = %s", (id_oc,))
                        st.success("Órdenes eliminadas.")
                        st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Máquinas" and rol == "admin":
        st.subheader("Gestión de Máquinas (Propias y Alquiladas)")
        try:
            df_maqs = ejecutar_consulta("SELECT * FROM maquinas")
            with st.expander("Crear Máquina", expanded=False):
                with st.form("form_crear_maquina", clear_on_submit=True):
                    m_nom = st.text_input("Nombre de la Máquina")
                    m_tipo = st.text_input("Tipo")
                    m_prop = st.selectbox("Tipo de Propiedad", ["-- Seleccione Propiedad --", "PROPIA", "ALQUILADA"], index=0)
                    m_costo_alq = st.number_input("Costo por Hora de Alquiler ($)", min_value=0.0, step=1000.0, value=0.0)
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if m_nom.strip() and m_prop != "-- Seleccione Propiedad --":
                            ejecutar_comando("INSERT INTO maquinas (nombre, tipo, tipo_propiedad, costo_hora_alquiler) VALUES (%s, %s, %s, %s)", (m_nom.strip(), m_tipo.strip(), m_prop, m_costo_alq if m_prop == "ALQUILADA" else 0))
                            st.success("Máquina agregada.")
                            st.rerun()
            
            if not df_maqs.empty:
                df_maqs_v = df_maqs.copy()
                df_maqs_v.insert(0, "Seleccionar", False)
                edited_maqs = st.data_editor(df_maqs_v, key="editor_maqs_mult", use_container_width=True, hide_index=True)
                ids_a_borrar_maqs = edited_maqs[edited_maqs["Seleccionar"] == True]["id"].tolist()
                if st.button("Eliminar Máquina(s)", type="primary"):
                    if ids_a_borrar_maqs:
                        for id_m in ids_a_borrar_maqs:
                            ejecutar_comando("DELETE FROM maquinas WHERE id = %s", (id_m,))
                        st.success("Máquinas eliminadas.")
                        st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Servicios" and rol == "admin":
        st.subheader("Administración de Servicios Prestados")
        try:
            df_serv = ejecutar_consulta("SELECT * FROM servicios_prestados ORDER BY id DESC")
            with st.expander("Crear Servicio", expanded=False):
                with st.form("form_crear_serv", clear_on_submit=True):
                    nom_serv = st.text_input("Nombre del Servicio")
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if nom_serv.strip():
                            ejecutar_comando("INSERT INTO servicios_prestados (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (nom_serv.upper().strip(),))
                            st.success("Servicio agregado.")
                            st.rerun()

            if not df_serv.empty:
                df_serv_v = df_serv.copy()
                df_serv_v.insert(0, "Seleccionar", False)
                edited_serv = st.data_editor(df_serv_v, key="editor_serv_mult", use_container_width=True, hide_index=True)
                ids_a_borrar_serv = edited_serv[edited_serv["Seleccionar"] == True]["id"].tolist()
                if st.button("Eliminar Servicio(s)", type="primary"):
                    if ids_a_borrar_serv:
                        for id_s in ids_a_borrar_serv:
                            ejecutar_comando("DELETE FROM servicios_prestados WHERE id = %s", (id_s,))
                        st.success("Servicios eliminados.")
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
                    r_valor_unit = st.number_input("Valor Unitario de la Pieza ($)", min_value=0.0, step=100.0, value=0.0)
                    
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if r_cod.strip() and r_cliente != "-- Seleccione Cliente --":
                            ejecutar_comando("INSERT INTO referencias (codigo, descripcion, cliente, valor_unitario) VALUES (%s, %s, %s, %s)", (r_cod.upper().strip(), r_desc, r_cliente, r_valor_unit))
                            st.success("Referencia guardada.")
                            st.rerun()

            if not df_refs.empty:
                df_refs_view = df_refs.copy()
                df_refs_view.insert(0, "Seleccionar", False)
                edited_refs = st.data_editor(df_refs_view, key="editor_refs_mult", use_container_width=True, hide_index=True)
                codigos_a_borrar_ref = edited_refs[edited_refs["Seleccionar"] == True]["codigo"].tolist()
                if st.button("Eliminar", type="primary"):
                    if codigos_a_borrar_ref:
                        for r_cod_item in codigos_a_borrar_ref:
                            ejecutar_comando("DELETE FROM referencias WHERE codigo = %s", (r_cod_item,))
                        st.success("Referencias eliminadas.")
                        st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Reportes":
        st.subheader("Centro de Reportes Gerenciales y de Producción")
        tipo_reporte_gerencial = st.radio("Selecciona la vista de reporte:", ["Reporte de Producción", "Costos Máquinas Alquiladas"], horizontal=True)
        st.write("---")
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            filtro_periodo = st.selectbox("Filtrar Período:", ["Histórico (Todo)", "Diario", "Semanal", "Mensual"])
        with c_p2:
            if filtro_periodo == "Diario":
                fecha_filtro = st.date_input("Selecciona el Día", value=(datetime.utcnow() - timedelta(hours=5)).date())
            elif filtro_periodo == "Semanal":
                fecha_filtro = st.date_input("Selecciona una fecha de la Semana", value=(datetime.utcnow() - timedelta(hours=5)).date())

        if tipo_reporte_gerencial == "Reporte de Producción":
            try:
                df_produccion_raw = ejecutar_consulta("""
                    SELECT * FROM registro_produccion 
                    WHERE numero_oc IS NOT NULL 
                    AND TRIM(numero_oc) <> '' 
                    AND UPPER(TRIM(numero_oc)) <> 'SIN OC'
                    ORDER BY id DESC
                """)
                
                if not df_produccion_raw.empty:
                    df_final = generar_reporte_produccion_excel(df_produccion_raw)
                    
                    df_final_view = df_final.copy()
                    df_final_view.insert(0, "id_reg", df_produccion_raw['id'].values)
                    df_final_view.insert(0, "Seleccionar", False)
                    
                    st.markdown("#### Listado de Producción Válida (Con OC)")
                    edited_reporte = st.data_editor(
                        df_final_view, 
                        key="editor_reporte_produccion", 
                        use_container_width=True, 
                        hide_index=True
                    )
                    
                    ids_a_borrar_reporte = edited_reporte[edited_reporte["Seleccionar"] == True]["id_reg"].tolist()
                    
                    if st.button("Eliminar Registro(s) Seleccionado(s)", type="primary"):
                        if ids_a_borrar_reporte:
                            for id_r in ids_a_borrar_reporte:
                                ejecutar_comando("DELETE FROM registro_produccion WHERE id = %s", (int(id_r),))
                            st.success("¡Registro(s) de producción eliminado(s) con éxito!")
                            st.rerun()
                        else:
                            st.warning("Selecciona al menos un registro en la casilla de la izquierda para eliminar.")

                    st.write("---")
                    buffer_prod = io.BytesIO()
                    with pd.ExcelWriter(buffer_prod, engine='openpyxl') as writer:
                        df_final.to_excel(writer, index=False, sheet_name='Reporte_Produccion')
                    st.download_button("Descargar Reporte Limpio (Excel)", data=buffer_prod.getvalue(), file_name="reporte_produccion.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                else:
                    st.info("No hay registros de producción asociados a Órdenes de Compra válidas.")
            except Exception as e:
                st.error(f"Error: {e}")

        elif tipo_reporte_gerencial == "Costos Máquinas Alquiladas":
            st.markdown("#### ⚙️ Consolidado de Costos por Uso de Máquinas Alquiladas")
            try:
                df_alq_regs = ejecutar_consulta("""
                    SELECT r.id, r.fecha_registro, r.operario_nombre, r.maquina, r.numero_oc, r.horas_trabajadas, m.costo_hora_alquiler
                    FROM registro_produccion r
                    JOIN maquinas m ON TRIM(UPPER(r.maquina)) = TRIM(UPPER(m.nombre))
                    WHERE (r.es_maquina_alquilada = TRUE OR UPPER(m.tipo_propiedad) = 'ALQUILADA')
                    ORDER BY r.id DESC
                """)

                if not df_alq_regs.empty:
                    df_alq_regs['costo_hora_alquiler'] = pd.to_numeric(df_alq_regs['costo_hora_alquiler'], errors='coerce').fillna(0.0)
                    df_alq_regs['horas_trabajadas'] = pd.to_numeric(df_alq_regs['horas_trabajadas'], errors='coerce').fillna(0.0)
                    df_alq_regs['Costo Total Alquiler ($)'] = df_alq_regs['horas_trabajadas'] * df_alq_regs['costo_hora_alquiler']
                    
                    st.dataframe(df_alq_regs, use_container_width=True, hide_index=True)
                    
                    costo_total_acumulado = df_alq_regs['Costo Total Alquiler ($)'].sum()
                    st.markdown(f"### **Costo Total Acumulado en Alquiler de Máquinas: ${costo_total_acumulado:,.2f}**")
                    
                    buffer_alq = io.BytesIO()
                    with pd.ExcelWriter(buffer_alq, engine='openpyxl') as writer:
                        df_alq_regs.to_excel(writer, index=False, sheet_name='Costos_Maquinas_Alquiladas')
                    st.download_button("Descargar Reporte de Alquileres (Excel)", data=buffer_alq.getvalue(), file_name="costos_maquinas_alquiladas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                else:
                    st.info("No hay registros de producción usando máquinas alquiladas o con costos de alquiler configurados.")
            except Exception as e:
                st.error(f"Error al calcular costos de máquinas alquiladas: {e}")

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
                        if op_sel != "-- Seleccione Operario --" and mat_sel != "-- Seleccione Ítem --":
                            row = mats_raw[mats_raw['nombre'] == mat_sel].iloc[0]
                            ejecutar_comando("INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (%s, %s, %s, %s, %s, 'ENTREGADO')", ((datetime.utcnow() - timedelta(hours=5)).strftime("%Y-%m-%d"), op_sel, row['codigo'], cant, row['tipo']))
                            ejecutar_comando("UPDATE inventario SET cantidad = cantidad - %s WHERE codigo = %s", (cant, row['codigo']))
                            st.success("Salida registrada.")
                            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Herramientas":
        st.subheader("Control y Préstamos de Herramientas")
        try:
            herramientas_db = ejecutar_consulta("SELECT codigo, nombre, cantidad FROM inventario WHERE tipo ILIKE '%HERRAMIENTA%'")
            if not herramientas_db.empty:
                st.dataframe(herramientas_db, use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Cargue Ítems":
        st.subheader("Cargue Único de Ítems al Inventario")
        try:
            clases_raw = ejecutar_consulta("SELECT nombre FROM clases_inventario")['nombre'].tolist() if not ejecutar_consulta("SELECT nombre FROM clases_inventario").empty else []
            lista_clases = ["-- Seleccione Clase --"] + clases_raw
            with st.form("form_cargue_item", clear_on_submit=True):
                c_cod = st.text_input("Código del Ítem")
                c_nom = st.text_input("Nombre del Ítem")
                c_clase = st.selectbox("Clase", lista_clases, index=0)
                c_cant = st.number_input("Cantidad Inicial", min_value=0, value=10)
                c_min = st.number_input("Stock Mínimo", min_value=0, value=5)
                if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                    if c_cod.strip() and c_clase != "-- Seleccione Clase --":
                        ejecutar_comando("INSERT INTO inventario (codigo, nombre, tipo, cantidad, stock_minimo) VALUES (%s, %s, %s, %s, %s)", (c_cod.upper().strip(), c_nom.strip(), c_clase, c_cant, c_min))
                        st.success("Ítem cargado.")
                        st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Inventario":
        st.subheader("Inventario General de la Planta")
        try:
            inv_gen = ejecutar_consulta("SELECT codigo, nombre, tipo as clase, cantidad, stock_minimo FROM inventario")
            if not inv_gen.empty:
                inv_gen_v = inv_gen.copy()
                inv_gen_v.insert(0, "Seleccionar", False)
                edited_inv = st.data_editor(inv_gen_v, key="editor_inv_mult", use_container_width=True, hide_index=True)
                codigos_a_borrar_inv = edited_inv[edited_inv["Seleccionar"] == True]["codigo"].tolist()
                if st.button("Eliminar", type="primary"):
                    if codigos_a_borrar_inv:
                        for c_item in codigos_a_borrar_inv:
                            ejecutar_comando("DELETE FROM inventario WHERE codigo = %s", (c_item,))
                        st.success("Ítems eliminados.")
                        st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Clases" and rol == "admin":
        st.subheader("Administración de Clases de Inventario")
        try:
            clases_actuales = ejecutar_consulta("SELECT * FROM clases_inventario ORDER BY id DESC")
            with st.expander("Crear Clase", expanded=False):
                with st.form("form_crear_clase", clear_on_submit=True):
                    nueva_clase = st.text_input("Nombre de la Clase")
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if nueva_clase.strip():
                            ejecutar_comando("INSERT INTO clases_inventario (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (nueva_clase.upper().strip(),))
                            st.success("Clase creada.")
                            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Clientes" and rol == "admin":
        st.subheader("Administración de Clientes")
        try:
            with st.expander("Crear o Actualizar Cliente", expanded=False):
                with st.form("form_crear_cliente", clear_on_submit=True):
                    nom_cliente = st.text_input("Razón Social (Ej: Pintupartes)")
                    nit_cliente = st.text_input("NIT (Código Tercero)")
                    comercial_cliente = st.text_input("Nombre Comercial")
                    dir_cliente = st.text_input("Dirección")
                    ciudad_cliente = st.text_input("Ciudad")
                    tel_cliente = st.text_input("Teléfono")
                    email_cliente = st.text_input("Correo Electrónico")
                    contacto_cliente = st.text_input("Contacto")
                    forma_pago_cliente = st.text_input("Forma de Pago (Ej: CRÉDITO 30 DÍAS)")

                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if nom_cliente.strip():
                            ejecutar_comando(
                                """INSERT INTO clientes (nombre, nit, nombre_comercial, direccion, ciudad, telefono, correo, contacto, forma_pago) 
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) 
                                   ON CONFLICT (nombre) 
                                   DO UPDATE SET nit = EXCLUDED.nit, nombre_comercial = EXCLUDED.nombre_comercial, direccion = EXCLUDED.direccion, ciudad = EXCLUDED.ciudad, telefono = EXCLUDED.telefono, correo = EXCLUDED.correo, contacto = EXCLUDED.contacto, forma_pago = EXCLUDED.forma_pago""",
                                (nom_cliente.strip(), nit_cliente.strip(), comercial_cliente.strip(), dir_cliente.strip(), ciudad_cliente.strip(), tel_cliente.strip(), email_cliente.strip(), contacto_cliente.strip(), forma_pago_cliente.strip())
                            )
                            st.success("¡Cliente guardado o actualizado con éxito!")
                            st.rerun()

            st.write("---")
            st.markdown("#### Listado de Clientes Registrados")
            clientes_df = ejecutar_consulta("SELECT id, nombre, nit, nombre_comercial, direccion, ciudad, telefono, correo, contacto, forma_pago FROM clientes ORDER BY id DESC")
            
            if not clientes_df.empty:
                clientes_df_view = clientes_df.copy()
                clientes_df_view.insert(0, "Seleccionar", False)
                
                edited_clientes = st.data_editor(
                    clientes_df_view, 
                    key="editor_clientes_mult", 
                    use_container_width=True, 
                    hide_index=True
                )
                
                ids_a_borrar_clientes = edited_clientes[edited_clientes["Seleccionar"] == True]["id"].tolist()
                
                if st.button("Eliminar Cliente(s) Seleccionado(s)", type="primary"):
                    if ids_a_borrar_clientes:
                        for id_cli in ids_a_borrar_clientes:
                            ejecutar_comando("DELETE FROM clientes WHERE id = %s", (id_cli,))
                        st.success("¡Cliente(s) eliminado(s) con éxito!")
                        st.rerun()
                    else:
                        st.warning("Selecciona al menos un cliente en la casilla de la izquierda para eliminar.")
            else:
                st.info("No hay clientes registrados en la base de datos.")
        except Exception as e:
            st.error(f"Error en gestión de clientes: {e}")

    elif menu_limpio == "Usuarios" and rol == "admin":
        st.subheader("Gestión y Seguridad de Usuarios del Sistema")
        try:
            users_df = ejecutar_consulta("SELECT id, username, nombre, rol FROM usuarios ORDER BY id DESC")
            with st.expander("Crear Usuario", expanded=False):
                with st.form("form_crear_usuario", clear_on_submit=True):
                    u_user = st.text_input("Usuario")
                    u_pass = st.text_input("Contraseña", type="password")
                    u_nom = st.text_input("Nombre Completo")
                    u_rol = st.selectbox("Rol", ["-- Seleccione Rol --", "operario", "produccion", "admin"], index=0)
                    if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                        if u_user.strip() and u_pass.strip() and u_nom.strip() and u_rol != "-- Seleccione Rol --":
                            ejecutar_comando("INSERT INTO usuarios (username, password, nombre, rol) VALUES (%s, %s, %s, %s)", (u_user.strip(), u_pass, u_nom.strip(), u_rol))
                            st.success("Usuario creado.")
                            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Configuración" and rol == "admin":
        st.subheader("Configuración General de la Empresa y Sistema")
        try:
            cfg_db = ejecutar_consulta("SELECT clave, valor FROM configuracion_empresa")
            cfg_dict = {row['clave']: row['valor'] for _, row in cfg_db.iterrows()} if not cfg_db.empty else {}
            with st.form("form_configuracion_general"):
                razon_social_val = st.text_input("Razón Social", value=cfg_dict.get("razon_social", "Industrias Metal&Co"))
                if st.form_submit_button("Guardar", type="primary", use_container_width=True):
                    ejecutar_comando("INSERT INTO configuracion_empresa (clave, valor) VALUES ('razon_social', %s) ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor", (razon_social_val,))
                    st.success("Guardado con éxito.")
                    st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu_limpio == "Despachos (F-02-02)":
        st.subheader("Módulo de Despachos y Generación de Remisión (F-02-02)")
        try:
            clientes_db = ejecutar_consulta("SELECT nombre, nit, nombre_comercial, direccion, ciudad, telefono, correo, contacto, forma_pago FROM clientes")
            lista_clientes_despacho = ["-- Seleccione Cliente --"] + (clientes_db['nombre'].tolist() if not clientes_db.empty else [])
            
            cliente_sel = st.selectbox("Seleccione Cliente Destino", lista_clientes_despacho, index=0)
            
            if cliente_sel != "-- Seleccione Cliente --":
                cli_row = clientes_db[clientes_db['nombre'] == cliente_sel].iloc[0]
                
                st.info(f"Cliente: **{cliente_sel}** | NIT (Código Tercero): `{cli_row.get('nit', 'N/A')}` | Dir: `{cli_row.get('direccion', 'N/A')}`")
                
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    num_remision_input = st.text_input("Número de Remisión (Consecutivo Manual)", value="426")
                with col_r2:
                    fecha_remision_input = st.date_input("Fecha de Despacho", value=(datetime.utcnow() - timedelta(hours=5)).date())
                
                obs_remision = st.text_area("Observaciones de la Remisión / Despacho", value="ENTREGA DE PIEZAS TERMINADAS EN PLANTA")

                st.write("---")
                st.markdown("#### Seleccionar Producción Terminada y Asignar Código / Precio Unitario")
                
                prod_registros = ejecutar_consulta("""
                    SELECT id, fecha_registro, numero_oc, referencia, maquina, unidades_producidas 
                    FROM registro_produccion 
                    WHERE (despachado IS NULL OR despachado = FALSE)
                    ORDER BY id DESC
                """)
                
                if not prod_registros.empty:
                    # Preparamos las columnas editables para que el usuario asigne manualmente el código, OP, unidad y precio unitario
                    df_despacho_editable = prod_registros.copy()
                    df_despacho_editable.insert(0, "Seleccionar", False)
                    df_despacho_editable['codigo_producto'] = df_despacho_editable['referencia']
                    df_despacho_editable['op'] = "N/A"
                    df_despacho_editable['orden_compra_otro'] = df_despacho_editable['numero_oc'].fillna("N/A")
                    df_despacho_editable['und_medida'] = "UND"
                    df_despacho_editable['precio_unitario'] = 0.0
                    df_despacho_editable['iva_porcentaje'] = 19.0
                    
                    # Buscamos si hay valor unitario configurado en referencias
                    for idx, row_ref in df_despacho_editable.iterrows():
                        ref_val = row_ref['referencia']
                        ref_db_val = ejecutar_consulta("SELECT valor_unitario FROM referencias WHERE codigo = %s", (ref_val,))
                        if not ref_db_val.empty and pd.notna(ref_db_val.iloc[0]['valor_unitario']):
                            df_despacho_editable.at[idx, 'precio_unitario'] = float(ref_db_val.iloc[0]['valor_unitario'])

                    edited_prod_despacho = st.data_editor(
                        df_despacho_editable, 
                        key="editor_despachos_prod_avanzado", 
                        use_container_width=True, 
                        hide_index=True
                    )
                    
                    filas_seleccionadas = edited_prod_despacho[edited_prod_despacho["Seleccionar"] == True]
                    
                    st.write("---")
                    st.markdown("#### Envío Adicional de Troquel o Ítem para Mantenimiento (Manual)")
                    with st.expander("Agregar Troquel o Ítem Adicional"):
                        troquel_desc = st.text_input("Descripción del Ítem / Troquel", value="SOLO CONFORMADO")
                        troquel_codigo = st.text_input("Código de Producto", value="N/A")
                        troquel_op = st.text_input("OP", value="N/A")
                        troquel_oc = st.text_input("Orden de Compra u Otro", value="N/A")
                        troquel_und = st.text_input("Unidad de Medida", value="UND")
                        troquel_cant = st.number_input("Cantidad", min_value=1, value=1)
                        troquel_precio = st.number_input("Precio Unitario ($)", min_value=0.0, step=100.0, value=0.0)
                        troquel_iva = st.number_input("Porcentaje IVA (%)", min_value=0.0, value=19.0)
                        troquel_incluir = st.checkbox("Incluir este ítem adicional en la remisión")
                    
                    st.write("---")
                    st.markdown("#### Datos de la Persona que Recibe")
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        recibe_nombre_input = st.text_input("Nombre de quien recibe")
                    with col_f2:
                        recibe_cc_input = st.text_input("Cédula de quien recibe")
                    
                    st.markdown("#### ✍️ Firma Digital en Pantalla (Firme abajo)")
                    canvas_result = st_canvas(
                        fill_color="rgba(255, 165, 0, 0.3)",
                        stroke_width=2,
                        stroke_color="#000000",
                        background_color="#FFFFFF",
                        height=150,
                        width=450,
                        drawing_mode="freedraw",
                        return_image_data=True,
                        key="canvas_firma_despacho",
                    )
                    
                    if st.button("Generar Remisión F-02-02 (PDF)", type="primary", use_container_width=True):
                        if not recibe_nombre_input.strip() or not recibe_cc_input.strip():
                            st.error("Por favor ingrese el nombre y la cédula de la persona que recibe.")
                        elif filas_seleccionadas.empty and not troquel_incluir:
                            st.warning("Seleccione al menos un registro de producción o un ítem adicional para despachar.")
                        else:
                            items_finales_despacho = []
                            ids_a_marcar_despachados = []
                            
                            for _, f_row in filas_seleccionadas.iterrows():
                                id_prod_item = int(f_row['id'])
                                ref_val = f_row['referencia']
                                cant_val = int(f_row['unidades_producidas'])
                                
                                # Capturamos los campos editados manualmente por el usuario en la tabla
                                codigo_manual = str(f_row.get('codigo_producto', ref_val))
                                op_manual = str(f_row.get('op', 'N/A'))
                                oc_manual = str(f_row.get('orden_compra_otro', f_row.get('numero_oc', 'N/A')))
                                und_manual = str(f_row.get('und_medida', 'UND'))
                                precio_unit_val = float(f_row.get('precio_unitario', 0.0))
                                iva_pct_val = float(f_row.get('iva_porcentaje', 19.0))
                                
                                ids_a_marcar_despachados.append(id_prod_item)
                                
                                ref_db = ejecutar_consulta("SELECT descripcion FROM referencias WHERE codigo = %s", (ref_val,))
                                desc_ref = ref_db.iloc[0]['descripcion'] if not ref_db.empty and pd.notna(ref_db.iloc[0]['descripcion']) else f"PIEZA {ref_val}"
                                
                                subtotal_item = cant_val * precio_unit_val
                                
                                items_finales_despacho.append({
                                    "descripcion": f"{ref_val} - {desc_ref}",
                                    "codigo_producto": codigo_manual,
                                    "op": op_manual,
                                    "oc": oc_manual,
                                    "unidad": und_manual,
                                    "cantidad": cant_val,
                                    "precio_unitario": precio_unit_val,
                                    "iva_porcentaje": iva_pct_val,
                                    "subtotal": subtotal_item
                                })
                            
                            if troquel_incluir and troquel_desc.strip():
                                subtotal_troquel = int(troquel_cant) * float(troquel_precio)
                                items_finales_despacho.append({
                                    "descripcion": troquel_desc.strip(),
                                    "codigo_producto": troquel_codigo.strip(),
                                    "op": troquel_op.strip(),
                                    "oc": troquel_oc.strip(),
                                    "unidad": troquel_und.strip(),
                                    "cantidad": int(troquel_cant),
                                    "precio_unitario": float(troquel_precio),
                                    "iva_porcentaje": float(troquel_iva),
                                    "subtotal": subtotal_troquel
                                })
                            
                            firma_path_temp = None
                            if canvas_result.image_data is not None:
                                img_arr = canvas_result.image_data
                                if np.any(img_arr[:, :, 3] > 0):
                                    os.makedirs("firmas", exist_ok=True)
                                    firma_path_temp = f"firmas/firma_{num_remision_input}.png"
                                    pil_img = Image.fromarray(img_arr.astype('uint8'), mode="RGBA")
                                    background = Image.new("RGB", pil_img.size, (255, 255, 255))
                                    background.paste(pil_img, mask=pil_img.split()[3])
                                    background.save(firma_path_temp)

                            datos_remision_dict = {
                                "numero_remision": num_remision_input,
                                "cliente_nombre": cliente_sel,
                                "nit": cli_row.get('nit', 'N/A'),
                                "nombre_comercial": cli_row.get('nombre_comercial', 'N/A'),
                                "telefono": cli_row.get('telefono', 'N/A'),
                                "correo": cli_row.get('correo', 'N/A'),
                                "contacto": cli_row.get('contacto', 'N/A'),
                                "forma_pago": cli_row.get('forma_pago', 'CRÉDITO 30 DÍAS'),
                                "fecha_despacho": str(fecha_remision_input),
                                "ciudad": cli_row.get('ciudad', 'Dosquebradas'),
                                "direccion": cli_row.get('direccion', 'N/A'),
                                "observaciones": obs_remision,
                                "elaborado": st.session_state['nombre_usuario'],
                                "recibe_nombre": recibe_nombre_input.strip(),
                                "recibe_cc": recibe_cc_input.strip()
                            }
                            
                            pdf_remision_buffer = generar_pdf_remision_f02_02(datos_remision_dict, items_finales_despacho, firma_path_temp)
                            
                            for id_reg in ids_a_marcar_despachados:
                                ejecutar_comando("UPDATE registro_produccion SET despachado = TRUE WHERE id = %s", (id_reg,))
                            
                            st.session_state["ultimo_pdf_remision"] = pdf_remision_buffer.getvalue()
                            st.session_state["nombre_pdf_remision"] = f"Remision_F-02-02_No_{num_remision_input}.pdf"
                            st.success("¡Formato de Remisión F-02-02 generado con éxito y ítems despachados!")
                            st.rerun()

                else:
                    st.info("No hay registros de producción pendientes por despachar.")

            if "ultimo_pdf_remision" in st.session_state:
                st.markdown("---")
                st.write("### Formato F-02-02 (Remisión) Listo para Descargar")
                st.download_button(
                    label="Descargar Remisión F-02-02 (PDF Oficial)",
                    data=st.session_state["ultimo_pdf_remision"],
                    file_name=st.session_state["nombre_pdf_remision"],
                    mime="application/pdf",
                    use_container_width=True
                )
                
                texto_wsp_rem = f"Hola, comparto la Remisión de Despacho F-02-02 #{num_remision_input} para el cliente *{cliente_sel}*."
                link_whatsapp_rem = f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto_wsp_rem)}"
                st.markdown(f'<a href="{link_whatsapp_rem}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; height:3rem; font-size:1.1rem; font-weight:bold; border:none; border-radius:8px; cursor:pointer;">Enviar Aviso por WhatsApp</button></a>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error en módulo de despachos: {e}")
