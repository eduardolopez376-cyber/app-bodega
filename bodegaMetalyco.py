import streamlit as st
import pandas as pd
import psycopg2
import os
import io
from datetime import datetime, time

# Configuración de página con diseño ajustado a móviles
st.set_page_config(
    page_title="Control de Producción - Metal&Co",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS optimizados para dispositivos móviles
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
        st.write("📦 **Metal&Co**")

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

# ----------------------------------------------------
# CONTROL DE SESIÓN Y LOGIN (Estable contra recargas)
# ----------------------------------------------------
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["rol"] = None
    st.session_state["nombre_usuario"] = None
    st.session_state["username"] = None

if not st.session_state["autenticado"]:
    st.title("🔑 Sistema Metal&Co")
    st.subheader("Inicio de Sesión")
    
    c_logo, c_form = st.columns([1, 1], vertical_alignment="center")
    with c_logo:
        mostrar_logo(ancho=250)
    with c_form:
        user_input = st.text_input("Usuario", key="login_user")
        pass_input = st.text_input("Contraseña", type="password", key="login_pass")
        
        if st.button("Ingresar", type="primary", use_container_width=True):
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

# ----------------------------------------------------
# ENCABEZADO Y BARRA LATERAL
# ----------------------------------------------------
col_logo, col_titulo = st.columns([1, 4], vertical_alignment="center")
with col_logo:
    mostrar_logo(ancho=100)
with col_titulo:
    st.title("Metal&Co - Planta")

st.sidebar.markdown(f"👤 **Usuario:** {st.session_state['nombre_usuario']}")
st.sidebar.markdown(f"🔰 **Rol:** `{st.session_state['rol'].upper()}`")

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
    
    tab_prog, tab_prod = st.tabs(["📋 Mi Programación por Día", "⚙️ Registrar Producción"])
    
    with tab_prog:
        st.write("### Consulta tus Tareas Asignadas")
        fecha_operario = st.date_input("Selecciona el día a consultar", value=datetime.now().date(), key="cal_op_dia")
        
        try:
            tareas = ejecutar_consulta(
                """SELECT id, hora_inicio, hora_fin, maquina, referencia, actividad, meta_unidades, estado 
                   FROM programacion_diaria 
                   WHERE operario_nombre = %s AND fecha = %s AND estado NOT IN ('FINALIZADO', 'CANCELADO')
                   ORDER BY id DESC""",
                (st.session_state['nombre_usuario'], fecha_operario)
            )
            if not tareas.empty:
                st.dataframe(tareas, use_container_width=True)
            else:
                st.info(f"No tienes tareas pendientes para el día {fecha_operario}.")
        except Exception as e:
            st.error(f"Error al cargar programación: {e}")
            
        st.write("---")
        st.write("### Mis Materiales A Cargo")
        try:
            herramientas = ejecutar_consulta(
                "SELECT fecha, codigo_material, cantidad, tipo FROM consumos WHERE operario = %s AND estado = 'PRESTADO'",
                (st.session_state['nombre_usuario'],)
            )
            if not herramientas.empty:
                st.dataframe(herramientas, use_container_width=True)
            else:
                st.success("Sin materiales o herramientas pendientes de devolución.")
        except Exception as e:
            st.error(f"Error al cargar consumos: {e}")

    with tab_prod:
        st.write("### Registrar Producción y Completar Tarea")
        try:
            tareas_pendientes = ejecutar_consulta(
                """SELECT id, actividad, maquina, referencia, meta_unidades FROM programacion_diaria 
                   WHERE operario_nombre = %s AND fecha = CURRENT_DATE AND estado NOT IN ('FINALIZADO', 'CANCELADO')""",
                (st.session_state['nombre_usuario'],)
            )
            
            if tareas_pendientes.empty:
                st.warning("No tienes tareas pendientes asignadas para hoy para reportar.")
            else:
                lista_opciones = [
                    f"ID #{row['id']} - {row['actividad']} (Meta: {row['meta_unidades']} u. | Máq: {row['maquina']})" 
                    for _, row in tareas_pendientes.iterrows()
                ]
                
                with st.form("form_reporte_operario"):
                    tarea_elegida_str = st.selectbox("Selecciona la Tarea a Registrar", lista_opciones)
                    
                    h_inicio = st.time_input("Hora de Inicio Real", time(7, 0))
                    h_fin = st.time_input("Hora de Finalización Real", time(17, 0))
                        
                    unidades = st.number_input("Unidades Producidas Realmente", min_value=1, step=1)
                    obs_usuario = st.text_area("Observaciones / Novedades")
                    
                    submit = st.form_submit_button("Guardar Registro y Finalizar Tarea", type="primary", use_container_width=True)
                    
                    if submit:
                        id_tarea_str = tarea_elegida_str.split(" - ")[0].replace("ID #", "")
                        id_tarea = int(id_tarea_str)
                        row_t = tareas_pendientes[tareas_pendientes['id'] == id_tarea].iloc[0]
                        meta_original = int(row_t['meta_unidades'])
                        
                        if unidades < meta_original:
                            faltantes = meta_original - unidades
                            obs_final = f"PRODUCCIÓN PARCIAL: Hizo {unidades} de {meta_original} meta. Faltaron {faltantes} unidades por reagendar. Nota: {obs_usuario}"
                        else:
                            obs_final = f"Meta cumplida ({unidades}/{meta_original}). {obs_usuario}"
                        
                        # 1. Guardar en registro de producción con el detalle de pendientes para el reporte
                        ejecutar_comando(
                            """INSERT INTO registro_produccion 
                            (operario_nombre, maquina, referencia, hora_inicio_real, hora_fin_real, unidades_producidas, observaciones) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                            (st.session_state['nombre_usuario'], row_t['maquina'], row_t['referencia'], h_inicio, h_fin, unidades, obs_final)
                        )
                        
                        # 2. Marcar la tarea como FINALIZADA para que desaparezca de pendientes del operario
                        ejecutar_comando(
                            "UPDATE programacion_diaria SET estado = 'FINALIZADO' WHERE id = %s",
                            (id_tarea,)
                        )
                        
                        st.success("¡Producción registrada con éxito! La tarea ha sido completada.")
                        st.rerun()

            st.write("---")
            st.write("### Mis Reportes de HOY")
            reportes_hoy = ejecutar_consulta(
                """SELECT hora_inicio_real, hora_fin_real, maquina, referencia, unidades_producidas, observaciones 
                   FROM registro_produccion 
                   WHERE operario_nombre = %s AND fecha::date = CURRENT_DATE 
                   ORDER BY id DESC""",
                (st.session_state['nombre_usuario'],)
            )
            if not reportes_hoy.empty:
                st.dataframe(reportes_hoy, use_container_width=True)
            else:
                st.caption("Aún no has registrado producciones hoy.")

        except Exception as e:
            st.error(f"Error al cargar formulario de reporte: {e}")

# ====================================================
# VISTA COMPLETA PARA ADMINISTRADOR Y PRODUCCIÓN
# ====================================================
elif rol in ["admin", "produccion"]:
    tab1, tab_eq, tab_ref, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📅 Programar", 
        "⚙️ Equipos",
        "📄 Referencias",
        "📊 Reportes", 
        "🚀 Entregas", 
        "🔨 Herramientas", 
        "📦 Inventario", 
        "⚙️ Usuarios"
    ])
    
    # --- TAB 1: PROGRAMAR PLANTA CON CALENDARIO ---
    with tab1:
        st.subheader("📅 Programación de Planta por Fecha")
        
        fecha_seleccionada = st.date_input("Selecciona el día a consultar/programar", value=datetime.now().date(), key="cal_admin_dia")
        
        try:
            ops = ejecutar_consulta("SELECT nombre FROM operarios")['nombre'].tolist()
            maqs = ejecutar_consulta("SELECT nombre FROM maquinas")['nombre'].tolist()
            refs = ejecutar_consulta("SELECT codigo FROM referencias")['codigo'].tolist()
            
            if not ops or not maqs or not refs:
                st.warning("Registra Operarios, Máquinas y Referencias primero.")
            else:
                with st.expander(f"➕ Asignar Tarea para el día {fecha_seleccionada}", expanded=False):
                    with st.form(f"form_programacion_{fecha_seleccionada}"):
                        op_p = st.selectbox("Operario", ops)
                        maq_p = st.selectbox("Máquina", maqs)
                        ref_p = st.selectbox("Referencia", refs)
                        act_p = st.text_input("Actividad (Ej: Corte, Plegado)")
                        
                        col_h1, col_h2 = st.columns(2)
                        with col_h1:
                            h_ini_p = st.time_input("Inicio Turno", time(7, 0))
                        with col_h2:
                            h_fin_p = st.time_input("Fin Turno", time(17, 0))
                        
                        meta_p = st.number_input("Meta de Unidades", min_value=1, value=100)
                        btn_prog = st.form_submit_button("Guardar Programación", type="primary", use_container_width=True)
                        
                        if btn_prog:
                            ejecutar_comando(
                                """INSERT INTO programacion_diaria 
                                (fecha, operario_nombre, maquina, referencia, actividad, hora_inicio, hora_fin, meta_unidades, estado) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDIENTE')""",
                                (fecha_seleccionada, op_p, maq_p, ref_p, act_p, h_ini_p, h_fin_p, meta_p)
                            )
                            st.success(f"Asignado a {op_p} para el día {fecha_seleccionada}.")
                            st.rerun()
            
            st.write("---")
            st.write(f"### Actividades Programadas para el: **{fecha_seleccionada}**")
            
            df_prog_actual = ejecutar_consulta(
                "SELECT * FROM programacion_diaria WHERE fecha = %s ORDER BY id DESC", 
                (fecha_seleccionada,)
            )
            
            if not df_prog_actual.empty:
                st.dataframe(df_prog_actual, use_container_width=True)
                
                with st.expander("✏️ Editar Programación de este día"):
                    id_edit = st.selectbox("ID a Modificar", df_prog_actual["id"].tolist(), key="edit_prog_id_cal")
                    row_sel = df_prog_actual[df_prog_actual["id"] == id_edit].iloc[0]
                    
                    idx_op = ops.index(row_sel["operario_nombre"]) if row_sel["operario_nombre"] in ops else 0
