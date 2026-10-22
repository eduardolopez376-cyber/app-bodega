import streamlit as st
import pandas as pd
import psycopg2
import os
import io
import urllib.parse
from datetime import datetime, time, date
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
        ejecutar_comando("ALTER TABLE programacion_diaria ADD COLUMN IF NOT EXISTS numero_oc VARCHAR(100);")
        ejecutar_comando("ALTER TABLE referencias ADD COLUMN IF NOT EXISTS cliente VARCHAR(150);")
        ejecutar_comando("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS nit VARCHAR(50);")
        ejecutar_comando("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS telefono VARCHAR(50);")
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
    df['Fecha'] = date.today().strftime('%Y-%m-%d')
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
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, height - 40, "Metal&Co")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(240, height - 40, "CONTROL DE PRODUCCIÓN Y CALIDAD PIEZAS TERMINADAS")
    p.setFont("Helvetica", 8)
    p.drawString(450, height - 35, "Código: F-01-01")
    p.drawString(450, height - 45, "Versión: 1")
    
    p.setLineWidth(1)
    p.rect(40, height - 60, width - 80, 25)
    
    p.rect(40, height - 140, width - 80, 80)
    p.setFillColorRGB(0.1, 0.1, 0.1)
    p.rect(40, height - 85, width - 80, 15, fill=1, stroke=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(200, height - 80, "INFORMACIÓN GENERAL (DILIGENCIA PROGRAMADOR/COORDINADOR PRODUCCIÓN)")
    
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(50, height - 105, f"FECHA: {datos.get('fecha', date.today())}")
    p.drawString(300, height - 105, f"OP (ORDEN DE PRODUCCIÓN): {datos.get('numero_oc', 'N/A')}")
    p.drawString(50, height - 125, f"CLIENTE: {datos.get('cliente', 'N/A')}")
    p.drawString(300, height - 125, f"REFERENCIA PIEZA: {datos.get('referencia', 'N/A')}")
    
    p.rect(40, height - 200, width - 80, 60)
    p.setFillColorRGB(0.1, 0.1, 0.1)
    p.rect(40, height - 160, width - 80, 15, fill=1, stroke=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(250, height - 155, "PROCESOS Y MÁQUINAS")
    
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(50, height - 180, "PROCESOS: CORTE / PLEGADO / SOLDADURA")
    p.drawString(300, height - 180, f"MÁQUINA: {datos.get('maquina', 'N/A')}")
    
    p.rect(40, height - 280, width - 80, 80)
    p.setFillColorRGB(0.1, 0.1, 0.1)
    p.rect(40, height - 225, width - 80, 15, fill=1, stroke=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(220, height - 220, "CONTROL DE PRODUCCIÓN (DILIGENCIA OPERARIO)")
    
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica", 9)
    p.drawString(50, height - 250, f"Hora Inicio: {datos.get('hora_inicio', '')}")
    p.drawString(130, height - 250, f"Hora Fin: {datos.get('hora_fin', '')}")
    p.drawString(210, height - 250, f"Producidas: {datos.get('producidas', 0)}")
    p.drawString(300, height - 250, f"Rechazadas: {datos.get('defectuosas', 0)}")
    p.drawString(420, height - 250, f"Obs: {datos.get('observaciones', '')[:30]}")
    
    p.rect(40, height - 390, width - 80, 100)
    p.setFillColorRGB(0.1, 0.1, 0.1)
    p.rect(40, height - 305, width - 80, 15, fill=1, stroke=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(180, height - 300, "CONTROL PRIMERA PIEZA TERMINADA PUESTA A PUNTO")
    
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica", 8)
    p.drawString(50, height - 330, "DIMENSIONES: OK")
    p.drawString(50, height - 350, "ACABADO SUPERFICIAL: OK")
    p.drawString(50, height - 370, "SOLDADURA / PINTURA: OK")
    
    p.rect(40, height - 460, width - 80, 60)
    p.setFont("Helvetica", 8)
    p.drawString(50, height - 425, f"NOMBRE OPERARIO: {datos.get('operario', 'N/A')}")
    p.drawString(350, height - 425, "NOMBRE INSPECTOR: ______________")
    
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
                fecha_operario = st.date_input("Selecciona el día a consultar", value=datetime.now().date(), key="cal_op_dia")
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
                        
                        cli_db = ejecutar_consulta("SELECT cliente FROM ordenes_compra WHERE numero_oc = %s", (num_oc_asociada,))
                        cliente_nombre = cli_db.iloc[0]['cliente'] if not cli_db.empty else "N/A"
                        
                        maq_db = ejecutar_consulta("SELECT tipo_propiedad FROM maquinas WHERE nombre = %s", (maquina_elegida,))
                        es_alq = False
                        horas_calc = 0.0
                        if not maq_db.empty:
                            if str(maq_db.iloc[0]['tipo_propiedad']).upper() == 'ALQUILADA':
                                es_alq = True
                                dt_inicio = datetime.combine(datetime.today(), h_inicio)
                                dt_fin = datetime.combine(datetime.today(), h_fin)
                                diff = (dt_fin - dt_inicio).total_seconds() / 3600.0
                                horas_calc = round(max(0.0, diff), 2)
                        
                        ejecutar_comando(
                            """INSERT INTO registro_produccion 
                            (operario_nombre, maquina, referencia, numero_oc, hora_inicio_real, hora_fin_real, unidades_producidas, observaciones, es_maquina_alquilada, horas_trabajadas) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (st.session_state['nombre_usuario'], maquina_elegida, referencia_pieza, num_oc_asociada, h_inicio, h_fin, unidades, f"Buenas: {unidades}, Defectuosas: {defectuosas}. {obs_usuario}", es_alq, horas_calc)
                        )
                        
                        if num_oc_asociada and num_oc_asociada != "SIN OC":
                            oc_db = ejecutar_consulta("SELECT unidades_entregadas, meta_unidades, requiere_unidades FROM ordenes_compra WHERE numero_oc = %s", (num_oc_asociada,))
                            if not oc_db.empty:
                                ent_actuales = int(oc_db.iloc[0]['unidades_entregadas'])
                                meta_oc = int(oc_db.iloc[0]['meta_unidades'])
                                req_uni = oc_db.iloc[0]['requiere_unidades']
                                nuevo_entregado = ent_actuales + unidades
                                nuevo_estado = 'COMPLETADO' if req_uni and nuevo_entregado >= meta_oc else 'EN PROCESO'
                                ejecutar_comando(
                                    "UPDATE ordenes_compra SET unidades_entregadas = %s, estado = %s WHERE numero_oc = %s",
                                    (nuevo_entregado, nuevo_estado, num_oc_asociada)
                                )

                        ejecutar_comando("UPDATE programacion_diaria SET estado = 'FINALIZADO' WHERE id = %s", (id_tarea,))
                        
                        datos_pdf = {
                            "fecha": date.today().strftime('%Y-%m-%d'),
                            "numero_oc": num_oc_asociada,
                            "cliente": cliente_nombre,
                            "referencia": referencia_pieza,
                            "maquina": maquina_elegida,
                            "hora_inicio": str(h_inicio),
                            "hora_fin": str(h_fin),
                            "producidas": unidades,
                            "defectuosas": defectuosas,
                            "observaciones": obs_usuario,
                            "operario": st.session_state['nombre_usuario']
                        }
                        
                        pdf_buffer = generar_pdf_f01_01(datos_pdf)
                        st.session_state["ultimo_pdf_buffer"] = pdf_buffer.getvalue()
                        st.session_state["ultimo_pdf_nombre"] = f"F-01-01_OC_{num_oc_asociada}.pdf"
                        
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
                    ref_imp = st.selectbox("Referencia", refs)
                    act_imp = st.text_input("Actividad / Motivo imprevisto")
                    
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
                        horas_calc = 0.0
                        if not maq_db.empty:
                            if str(maq_db.iloc[0]['tipo_propiedad']).upper() == 'ALQUILADA':
                                es_alq = True
                                dt_inicio = datetime.combine(datetime.today(), h_ini_imp)
                                dt_fin = datetime.combine(datetime.today(), h_fin_imp)
                                diff = (dt_fin - dt_inicio).total_seconds() / 3600.0
                                horas_calc = round(max(0.0, diff), 2)

                        ejecutar_comando(
                            """INSERT INTO registro_produccion 
                            (operario_nombre, maquina, referencia, numero_oc, hora_inicio_real, hora_fin_real, unidades_producidas, observaciones, es_maquina_alquilada, horas_trabajadas) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (st.session_state['nombre_usuario'], maq_imp, ref_imp, oc_imp, h_ini_imp, h_fin_imp, uni_imp, obs_final_imp, es_alq, horas_calc)
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
        st.subheader("📅 Programación de Planta por Fecha y Orden de Compra")
        fecha_seleccionada = st.date_input("Selecciona el día a consultar/programar", value=datetime.now().date(), key="cal_admin_dia")
        try:
            ops_df = ejecutar_consulta("SELECT nombre FROM usuarios WHERE rol = 'operario'")
            ops = ops_df['nombre'].tolist() if not ops_df.empty else []
            maqs = ejecutar_consulta("SELECT nombre FROM maquinas")['nombre'].tolist()
            refs = ejecutar_consulta("SELECT codigo FROM referencias")['codigo'].tolist()
            ocs_disp = ejecutar_consulta("SELECT numero_oc FROM ordenes_compra WHERE estado != 'COMPLETADO'")['numero_oc'].tolist()
            
            if not ops or not maqs or not refs or not ocs_disp:
                st.warning("⚠️ Asegúrate de tener operarios, máquinas, referencias y al menos una **Orden de Compra activa** creada.")
            else:
                with st.expander("Crear", expanded=True):
                    k_sufijo = st.session_state["form_key_counter"]
                    oc_prog = st.selectbox("Orden de Compra a Ejecutar", ocs_disp, key=f"select_oc_dinamica_{k_sufijo}")
                    
                    oc_info = ejecutar_consulta("SELECT referencia, servicio, meta_unidades, unidades_entregadas FROM ordenes_compra WHERE numero_oc = %s", (oc_prog,))
                    ref_sugerida = oc_info.iloc[0]['referencia'] if not oc_info.empty else (refs[0] if refs else "")
                    serv_sugerido = oc_info.iloc[0]['servicio'] if not oc_info.empty else ""
                    meta_restante = max(1, int(oc_info.iloc[0]['meta_unidades']) - int(oc_info.iloc[0]['unidades_entregadas'])) if not oc_info.empty else 100
                    
                    st.markdown(f"📌 **Referencia de la OC:** `{ref_sugerida}` &nbsp;|&nbsp; **Servicio:** `{serv_sugerido}` &nbsp;|&nbsp; **Saldo Pendiente:** `{meta_restante} u.`")
                    
                    with st.form(f"form_programacion_{fecha_seleccionada}_{k_sufijo}", clear_on_submit=True):
                        op_p = st.selectbox("Operario", ops, key=f"op_prog_{k_sufijo}")
                        maq_p = st.selectbox("Máquina", maqs, key=f"maq_prog_{k_sufijo}")
                        act_p = st.text_input("Actividad Específica", value=serv_sugerido, key=f"act_prog_{k_sufijo}")
                        
                        col_h1, col_h2 = st.columns(2)
                        with col_h1:
                            h_ini_p = st.time_input("Inicio Turno", time(7, 0), key=f"hini_{k_sufijo}")
                        with col_h2:
                            h_fin_p = st.time_input("Fin Turno", time(17, 0), key=f"hfin_{k_sufijo}")
                        
                        meta_p = st.number_input("Meta de Unidades para esta Tarea", min_value=1, value=meta_restante, key=f"meta_{k_sufijo}")
                        
                        if st.form_submit_button("Guardar Programación de Tarea", type="primary", use_container_width=True):
                            ejecutar_comando(
                                """INSERT INTO programacion_diaria 
                                (fecha, numero_oc, operario_nombre, maquina, referencia, actividad, hora_inicio, hora_fin, meta_unidades, estado) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDIENTE')""",
                                (fecha_seleccionada, oc_prog, op_p, maq_p, ref_sugerida, act_p, h_ini_p, h_fin_p, meta_p)
                            )
                            st.session_state["form_key_counter"] += 1
                            st.success(f"¡Tarea asignada a {op_p} con éxito!")
                            st.rerun()
            
            st.write("---")
            st.write(f"### Actividades Programadas para el: **{fecha_seleccionada}**")
            df_prog_actual = ejecutar_consulta("SELECT * FROM programacion_diaria WHERE fecha = %s ORDER BY id DESC", (fecha_seleccionada,))
            if not df_prog_actual.empty:
                st.dataframe(df_prog_actual, use_container_width=True)
                with st.expander("Eliminar"):
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
        st.subheader("📋 Gestión de Órdenes de Compra (OC), Clientes y Saldos")
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
                        requiere_uni = st.checkbox("¿Este servicio requiere control por unidades?", value=True)
                        meta_oc = st.number_input("Cantidad Total Pedida (Meta)", min_value=0, value=1000)
                        
                        if st.form_submit_button("Guardar Orden de Compra", type="primary", use_container_width=True):
                            if num_oc.strip() and cliente_oc != "SIN CLIENTE REGISTRADO":
                                meta_final = meta_oc if requiere_uni else 0
                                ejecutar_comando(
                                    """INSERT INTO ordenes_compra 
                                    (numero_oc, cliente, referencia, servicio, requiere_unidades, meta_unidades, unidades_entregadas, estado) 
                                    VALUES (%s, %s, %s, %s, %s, %s, 0, 'PENDIENTE')""",
                                    (num_oc.upper().strip(), cliente_oc, ref_oc, servicio_oc, requiere_uni, meta_final)
                                )
                                st.success(f"Orden de Compra #{num_oc} registrada con éxito.")
                                st.rerun()
                            else:
                                st.error("Por favor completa el número de OC y selecciona un cliente válido.")

            st.write("---")
            st.write("### 📊 Estado y Saldos Pendientes de Órdenes de Compra")
            df_oc = ejecutar_consulta("SELECT * FROM ordenes_compra ORDER BY id DESC")
            if not df_oc.empty:
                df_oc['saldo_pendiente'] = df_oc.apply(
                    lambda row: row['meta_unidades'] - row['unidades_entregadas'] if row['requiere_unidades'] else 'N/A', axis=1
                )
                st.dataframe(df_oc, use_container_width=True)
                with st.expander("Eliminar"):
                    with st.form("form_del_oc", clear_on_submit=True):
                        oc_del = st.selectbox("Selecciona la OC a Borrar", df_oc["numero_oc"].tolist())
                        if st.form_submit_button("Confirmar Eliminación de OC", type="primary", use_container_width=True):
                            ejecutar_comando("DELETE FROM registro_produccion WHERE numero_oc = %s", (oc_del,))
                            ejecutar_comando("DELETE FROM programacion_diaria WHERE numero_oc = %s", (oc_del,))
                            ejecutar_comando("DELETE FROM ordenes_compra WHERE numero_oc = %s", (oc_del,))
                            st.success(f"Orden de Compra #{oc_del} eliminada por completo.")
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
                        m_nom = st.text_input("Nombre de la Máquina (Ej: Láser CNC 01)")
                        m_tipo = st.text_input("Tipo (Ej: Corte, Dobladora)")
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
                        nom_serv = st.text_input("Nombre del Servicio (Ej: SOLDADURA TIG)")
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
            ["Reporte de Producción", "Costos Máquinas Alquiladas", "Saldos de Órdenes de Compra e Inventario"], 
            horizontal=True
        )
        
        if tipo_reporte_gerencial == "Reporte de Producción":
            st.markdown("### 📥 Reporte de Producción en Columnas Separadas para Excel")
            try:
                df_produccion_raw = ejecutar_consulta("SELECT * FROM registro_produccion ORDER BY id DESC")
                if not df_produccion_raw.empty:
                    df_final = generar_reporte_produccion_excel(df_produccion_raw)
                    st.dataframe(df_final, use_container_width=True)
                    buffer_prod = io.BytesIO()
                    with pd.ExcelWriter(buffer_prod, engine='openpyxl') as writer:
                        df_final.to_excel(writer, index=False, sheet_name='Reporte_Produccion')
                    st.download_button(
                        label="📥 Descargar Reporte de Producción (Excel)",
                        data=buffer_prod.getvalue(),
                        file_name=f"reporte_produccion_{date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.info("No hay registros de producción disponibles.")
            except Exception as e:
                st.error(f"Error: {e}")

        elif tipo_reporte_gerencial == "Costos Máquinas Alquiladas":
            st.markdown("### 💰 Control de Uso y Costos de Máquinas Alquiladas")
            try:
                query_alq = """
                    SELECT R.id, R.fecha, R.operario_nombre, R.maquina, R.horas_trabajadas, 
                    M.costo_hora_alquiler, (R.horas_trabajadas * M.costo_hora_alquiler) AS costo_total
                    FROM registro_produccion R
                    JOIN maquinas M ON R.maquina = M.nombre
                    WHERE M.tipo_propiedad = 'ALQUILADA'
                    ORDER BY R.id DESC
                """
                df_alq = ejecutar_consulta(query_alq)
                if not df_alq.empty:
                    tot_horas = df_alq['horas_trabajadas'].sum()
                    tot_costo = df_alq['costo_total'].sum()
                    col_m1, col_m2 = st.columns(2)
                    col_m1.metric("Total Horas Alquiladas", f"{tot_horas:.2f} hrs")
                    col_m2.metric("Costo Total Acumulado", f"${tot_costo:,.2f}")
                    st.dataframe(df_alq, use_container_width=True)
                else:
                    st.info("No hay registros de máquinas alquiladas.")
            except Exception as e:
                st.warning(f"Información: {e}")

        else:
            try:
                st.write("#### Saldos de Órdenes de Compra")
                df_oc_rep = ejecutar_consulta("SELECT * FROM ordenes_compra ORDER BY id DESC")
                if not df_oc_rep.empty:
                    df_oc_rep['saldo_pendiente'] = df_oc_rep.apply(lambda r: r['meta_unidades'] - r['unidades_entregadas'] if r['requiere_unidades'] else 'N/A', axis=1)
                    st.dataframe(df_oc_rep, use_container_width=True)
            except Exception as e:
                st.error(f"Error: {e}")

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
                            (datetime.now().strftime("%Y-%m-%d %H:%M"), op_sel, row['codigo'], cant, row['tipo'])
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
                                (datetime.now().strftime("%Y-%m-%d %H:%M"), op_her, row_h['codigo'], cant_her)
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
                                # Marcar anterior devuelto y crear nuevo préstamo al nuevo operario
                                ejecutar_comando("UPDATE consumos SET estado = 'DEVUELTO' WHERE id = %s", (id_prestamo_sel,))
                                ejecutar_comando(
                                    "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (%s, %s, %s, %s, 'HERRAMIENTA', 'PRESTADO')",
                                    (datetime.now().strftime("%Y-%m-%d %H:%M"), nuevo_operario, reg_actual['codigo_material'], reg_actual['cantidad'])
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
                                st.success("¡Usuario actualizado!")
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
