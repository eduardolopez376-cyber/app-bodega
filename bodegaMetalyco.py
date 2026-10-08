import streamlit as str_lib
import streamlit as st
import pandas as pd
import psycopg2
import os
import io
from datetime import datetime, time

# Configuración de página con diseño ajustado a móviles
st.set_page_config(
    page_title="Industrias Metal&Co",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------------------------------------------
# ESTILOS CSS: TEMA NEGRO, NARANJA Y PURGA TOTAL DE FLECHAS
# ----------------------------------------------------
st.markdown("""
    <style>
        /* Fondo general negro industrial */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
            background-color: #0b0b0b;
            color: #f3f4f6;
        }
        
        /* Tipografía limpia */
        h1, h2, h3, h4, h5, h6, p, label, span {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }

        /* Ocultar cualquier SVG o icono residual de expander nativo */
        [data-testid="stExpanderToggleIcon"] {
            display: none !important;
        }
        [data-testid="stExpander"] svg {
            display: none !important;
        }

        /* Botones principales en color Naranja Industrial */
        .stButton>button {
            width: 100%;
            height: 3.2rem;
            font-size: 1rem !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            border: none !important;
            background: linear-gradient(135deg, #f97316 0%, #ea580c 100%) !important;
            color: white !important;
            box-shadow: 0 4px 12px rgba(249, 115, 22, 0.3);
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(249, 115, 22, 0.5);
        }

        /* Botón de envío de formularios (Submit) en Naranja */
        .stFormSubmitButton>button {
            width: 100%;
            height: 3.4rem;
            font-size: 1.05rem !important;
            font-weight: 700 !important;
            border-radius: 8px !important;
            background: linear-gradient(135deg, #f97316 0%, #c2410c 100%) !important;
            color: white !important;
            box-shadow: 0 4px 12px rgba(249, 115, 22, 0.3);
            border: none !important;
        }
        .stFormSubmitButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(249, 115, 22, 0.5);
        }

        /* Tarjetas / Expanders con bordes sutiles y limpios */
        div.stExpander {
            background-color: #141414 !important;
            border: 1px solid #262626 !important;
            border-radius: 10px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
        }
        
        /* Asegurar que el texto dentro del expander no muestre artefactos */
        div.stExpander summary {
            color: #f3f4f6 !important;
            font-weight: 600 !important;
        }

        /* Campos de entrada (Inputs y selects) */
        input, select, textarea {
            border-radius: 8px !important;
            background-color: #141414 !important;
            border: 1px solid #262626 !important;
            color: #f3f4f6 !important;
            font-size: 0.95rem !important;
        }
        
        /* Pestañas (Tabs) con selección Naranja */
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
            background-color: #0b0b0b;
            padding: 4px;
            border-radius: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 42px;
            background-color: #141414;
            border-radius: 6px;
            color: #a3a3a3;
            font-weight: 600;
            border: 1px solid #262626;
        }
        .stTabs [aria-selected="true"] {
            background-color: #f97316 !important;
            color: white !important;
            border: 1px solid #ea580c !important;
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
        st.markdown("⚙️ **Industrias Metal&Co**")

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
            CREATE TABLE IF NOT EXISTS servicios_prestados (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) UNIQUE NOT NULL
            );
        """)
        servicios_iniciales = ["TROQUELADO", "CONFORMADO", "CORTE LASER", "PINTURA", "FABRICACION DE ESTRUCTURAS METALICAS"]
        for s in servicios_iniciales:
            ejecutar_comando("INSERT INTO servicios_prestados (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (s,))

        ejecutar_comando("""
            CREATE TABLE IF NOT EXISTS clases_inventario (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) UNIQUE NOT NULL
            );
        """)

        ejecutar_comando("""
            ALTER TABLE maquinas ADD COLUMN IF NOT EXISTS tipo_propiedad VARCHAR(50) DEFAULT 'PROPIA';
        """)

        ejecutar_comando("""
            ALTER TABLE programacion_diaria ADD COLUMN IF NOT EXISTS numero_oc VARCHAR(100);
        """)
        ejecutar_comando("""
            ALTER TABLE registro_produccion ADD COLUMN IF NOT EXISTS numero_oc VARCHAR(100);
        """)
    except Exception as e:
        print(f"Nota en inicialización: {e}")

inicializar_tablas_sistema()

# ----------------------------------------------------
# INICIALIZACIÓN BLINDADA DEL ESTADO DE SESIÓN
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
    st.markdown("<h1 style='text-align: center; color: #f97316;'>Industrias Metal&Co</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #a3a3a3;'>Inicia sesión en el sistema de planta</p>", unsafe_allow_html=True)
    
    col1, col_login_box, col3 = st.columns([1, 1.2, 1])
    with col_login_box:
        with st.form("form_login"):
            mostrar_logo(ancho=120)
            user_input = st.text_input("Usuario")
            pass_input = st.text_input("Contraseña", type="password")
            submit_login = st.form_submit_button("Ingresar al Sistema", use_container_width=True)
            
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
                        st.error("❌ Usuario o contraseña incorrectos")
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
    st.stop()

# ----------------------------------------------------
# ENCABEZADO Y BARRA LATERAL (Usuarios Logueados)
# ----------------------------------------------------
col_logo, col_titulo = st.columns([1, 5], vertical_alignment="center")
with col_logo:
    mostrar_logo(ancho=90)
with col_titulo:
    st.markdown("## Industrias Metal&Co")

st.sidebar.markdown(f"👤 **Usuario:** `{st.session_state['nombre_usuario']}`")
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
# VISTA EXCLUSIVA PARA OPERARIOS (BOTONES SIMPLES)
# ====================================================
if rol == "operario":
    st.markdown(f"### 👋 Hola, {st.session_state['nombre_usuario']}")
    
    tab_prog, tab_prod, tab_nueva = st.tabs(["📅 Programación", "⚙️ Producción", "⚡ Imprevisto"])
    
    with tab_prog:
        st.markdown("#### Tareas Asignadas")
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
            
        st.markdown("---")
        st.markdown("#### Herramientas y Materiales A Cargo")
        try:
            herramientas = ejecutar_consulta(
                "SELECT fecha, codigo_material, cantidad, tipo FROM consumos WHERE operario = %s AND estado = 'PRESTADO'",
                (st.session_state['nombre_usuario'],)
            )
            if not herramientas.empty:
                st.dataframe(herramientas, use_container_width=True)
            else:
                st.success("Sin herramientas o materiales pendientes de devolución.")
        except Exception as e:
            st.error(f"Error al cargar consumos: {e}")

    with tab_prod:
        st.markdown("#### Registrar Producción")
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
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        h_inicio = st.time_input("Hora de Inicio Real", time(7, 0))
                    with c2:
                        h_fin = st.time_input("Hora de Finalización Real", time(17, 0))
                        
                    c3, c4 = st.columns(2)
                    with c3:
                        unidades = st.number_input("Unidades Buenas", min_value=0, step=1)
                    with c4:
                        defectuosas = st.number_input("Unidades Defectuosas (Scrap)", min_value=0, step=1, value=0)
                        
                    obs_usuario = st.text_area("Observaciones / Novedades")
                    
                    submit = st.form_submit_button("Guardar", use_container_width=True)
                    
                    if submit:
                        id_tarea_str = tarea_elegida_str.split(" | ")[0].replace("ID #", "")
                        id_tarea = int(id_tarea_str)
                        row_t = tareas_pendientes[tareas_pendientes['id'] == id_tarea].iloc[0]
                        num_oc_asociada = row_t['numero_oc']
                        
                        ejecutar_comando(
                            """INSERT INTO registro_produccion 
                            (operario_nombre, maquina, referencia, numero_oc, hora_inicio_real, hora_fin_real, unidades_producidas, observaciones) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                            (st.session_state['nombre_usuario'], row_t['maquina'], row_t['referencia'], num_oc_asociada, h_inicio, h_fin, unidades, f"Buenas: {unidades}, Defectuosas: {defectuosas}. {obs_usuario}")
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

                        ejecutar_comando(
                            "UPDATE programacion_diaria SET estado = 'FINALIZADO' WHERE id = %s",
                            (id_tarea,)
                        )
                        
                        st.success("✅ ¡Producción guardada correctamente!")
                        st.rerun()

            st.markdown("---")
            st.markdown("#### Mis Reportes Recientes")
            reportes_recientes = ejecutar_consulta(
                """SELECT numero_oc, hora_inicio_real, hora_fin_real, maquina, referencia, unidades_producidas, observaciones 
                   FROM registro_produccion 
                   WHERE operario_nombre = %s 
                   ORDER BY id DESC LIMIT 10""",
                (st.session_state['nombre_usuario'],)
            )
            if not reportes_recientes.empty:
                st.dataframe(reportes_recientes, use_container_width=True)
            else:
                st.caption("Aún no tienes registros de producción.")

        except Exception as e:
            st.error(f"Error al cargar formulario de reporte: {e}")

    with tab_nueva:
        st.markdown("#### Registrar Tarea Imprevista No Programada")
        try:
            maqs = ejecutar_consulta("SELECT nombre FROM maquinas")['nombre'].tolist()
            refs = ejecutar_consulta("SELECT codigo FROM referencias")['codigo'].tolist()
            ocs_disp = ejecutar_consulta("SELECT numero_oc FROM ordenes_compra WHERE estado != 'COMPLETADO'")['numero_oc'].tolist()
            ocs_disp.insert(0, "SIN OC")
            
            if not maqs or not refs:
                st.warning("Faltan máquinas o referencias registradas en el sistema.")
            else:
                with st.form("form_tarea_imprevista", clear_on_submit=True):
                    oc_imp = st.selectbox("Orden de Compra Asociada (Opcional)", ocs_disp)
                    maq_imp = st.selectbox("Máquina", maqs)
                    ref_imp = st.selectbox("Referencia", refs)
                    act_imp = st.text_input("Motivo imprevisto (Ej: Reparación, Reproceso)")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        h_ini_imp = st.time_input("Hora de Inicio", time(8, 0))
                    with c2:
                        h_fin_imp = st.time_input("Hora de Finalización", time(17, 0))
                        
                    c3, c4 = st.columns(2)
                    with c3:
                        uni_imp = st.number_input("Unidades Buenas", min_value=0, value=1)
                    with c4:
                        def_imp = st.number_input("Unidades Defectuosas", min_value=0, value=0)
                        
                    obs_imp = st.text_area("Observaciones")
                    
                    btn_imp = st.form_submit_button("Guardar", use_container_width=True)
                    
                    if btn_imp:
                        obs_final_imp = f"⚡ TAREA IMPREVISTA: {act_imp} | Buenas: {uni_imp}, Defectuosas: {def_imp}. Nota: {obs_imp}"
                        
                        ejecutar_comando(
                            """INSERT INTO registro_produccion 
                            (operario_nombre, maquina, referencia, numero_oc, hora_inicio_real, hora_fin_real, unidades_producidas, observaciones) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                            (st.session_state['nombre_usuario'], maq_imp, ref_imp, oc_imp, h_ini_imp, h_fin_imp, uni_imp, obs_final_imp)
                        )
                        
                        if oc_imp and oc_imp != "SIN OC":
                            oc_db = ejecutar_consulta("SELECT unidades_entregadas, meta_unidades, requiere_unidades FROM ordenes_compra WHERE numero_oc = %s", (oc_imp,))
                            if not oc_db.empty:
                                ent_actuales = int(oc_db.iloc[0]['unidades_entregadas'])
                                meta_oc = int(oc_db.iloc[0]['meta_unidades'])
                                req_uni = oc_db.iloc[0]['requiere_unidades']
                                nuevo_entregado = ent_actuales + uni_imp
                                nuevo_estado = 'COMPLETADO' if req_uni and nuevo_entregado >= meta_oc else 'EN PROCESO'
                                ejecutar_comando(
                                    "UPDATE ordenes_compra SET unidades_entregadas = %s, estado = %s WHERE numero_oc = %s",
                                    (nuevo_entregado, nuevo_estado, oc_imp)
                                )

                        st.success("✅ ¡Guardado!")
                        st.rerun()
        except Exception as e:
            st.error(f"Error al cargar formulario: {e}")

# ====================================================
# VISTA COMPLETA PARA ADMINISTRADOR Y PRODUCCIÓN
# ====================================================
elif rol in ["admin", "produccion"]:
    tab_prog, tab_oc, tab_eq, tab_serv, tab_ref, tab_rep, tab_ent, tab_herramientas, tab_cargue, tab_inv_gen, tab_clases, tab_usu = st.tabs([
        "📅 Programar", 
        "📋 Órdenes Compra",
        "⚙️ Máquinas",
        "🛠️ Servicios",
        "📄 Referencias",
        "📊 Reportes", 
        "🚀 Entregas", 
        "🔨 Herramientas",
        "📥 Cargue", 
        "📦 Inventario",
        "🏷️ Clases", 
        "⚙️ Usuarios"
    ])
    
    # --- TAB 1: PROGRAMAR PLANTA ---
    with tab_prog:
        st.markdown("### Programación de Planta")
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
                with st.expander("➕ Crear Tarea", expanded=False):
                    k_sufijo = st.session_state["form_key_counter"]
                    oc_prog = st.selectbox("Orden de Compra a Ejecutar", ocs_disp, key=f"select_oc_dinamica_{k_sufijo}")
                    
                    oc_info = ejecutar_consulta("SELECT referencia, servicio, meta_unidades, unidades_entregadas FROM ordenes_compra WHERE numero_oc = %s", (oc_prog,))
                    ref_sugerida = oc_info.iloc[0]['referencia'] if not oc_info.empty else (refs[0] if refs else "")
                    serv_sugerido = oc_info.iloc[0]['servicio'] if not oc_info.empty else ""
                    meta_restante = max(1, int(oc_info.iloc[0]['meta_unidades']) - int(oc_info.iloc[0]['unidades_entregadas'])) if not oc_info.empty else 100
                    
                    st.info(f"📌 **Referencia:** `{ref_sugerida}` &nbsp;|&nbsp; **Servicio:** `{serv_sugerido}` &nbsp;|&nbsp; **Saldo Pendiente:** `{meta_restante} u.`")
                    
                    with st.form(f"form_programacion_{fecha_seleccionada}_{k_sufijo}", clear_on_submit=True):
                        op_p = st.selectbox("Operario", ops, key=f"op_prog_{k_sufijo}")
                        maq_p = st.selectbox("Máquina", maqs, key=f"maq_prog_{k_sufijo}")
                        act_p = st.text_input("Actividad Específica", value=serv_sugerido, key=f"act_prog_{k_sufijo}")
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            h_ini_p = st.time_input("Inicio Turno", time(7, 0), key=f"hini_{k_sufijo}")
                        with c2:
                            h_fin_p = st.time_input("Fin Turno", time(17, 0), key=f"hfin_{k_sufijo}")
                        
                        meta_p = st.number_input("Meta de Unidades", min_value=1, value=meta_restante, key=f"meta_{k_sufijo}")
                        btn_prog = st.form_submit_button("Guardar", use_container_width=True)
                        
                        if btn_prog:
                            ejecutar_comando(
                                """INSERT INTO programacion_diaria 
                                (fecha, numero_oc, operario_nombre, maquina, referencia, actividad, hora_inicio, hora_fin, meta_unidades, estado) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDIENTE')""",
                                (fecha_seleccionada, oc_prog, op_p, maq_p, ref_sugerida, act_p, h_ini_p, h_fin_p, meta_p)
                            )
                            st.session_state["form_key_counter"] += 1
                            st.success("✅ ¡Guardado!")
                            st.rerun()
            
            st.markdown("---")
            st.markdown(f"### Actividades Programadas para el: **{fecha_seleccionada}**")
            
            df_prog_actual = ejecutar_consulta(
                "SELECT * FROM programacion_diaria WHERE fecha = %s ORDER BY id DESC", 
                (fecha_seleccionada,)
            )
            
            if not df_prog_actual.empty:
                st.dataframe(df_prog_actual, use_container_width=True)
                
                with st.expander("🗑️ Eliminar Programación", expanded=False):
                    id_del = st.selectbox("ID a Eliminar", df_prog_actual["id"].tolist(), key="del_prog_id_c")
                    if st.button("Confirmar Eliminación", use_container_width=True):
                        ejecutar_comando("DELETE FROM programacion_diaria WHERE id = %s", (id_del,))
                        st.success("✅ Eliminado.")
                        st.rerun()
            else:
                st.info(f"No hay actividades programadas para la fecha {fecha_seleccionada}.")

        except Exception as e:
            st.error(f"Error en Programación: {e}")

    # --- TAB 2: ÓRDENES DE COMPRA Y SALDOS ---
    with tab_oc:
        st.markdown("### Gestión de Órdenes de Compra")
        try:
            refs_db = ejecutar_consulta("SELECT codigo FROM referencias")
            lista_refs = refs_db['codigo'].tolist() if not refs_db.empty else []
            
            serv_db = ejecutar_consulta("SELECT nombre FROM servicios_prestados")
            lista_servicios = serv_db['nombre'].tolist() if not serv_db.empty else ["TROQUELADO", "CORTE LASER"]
            
            if not lista_refs:
                st.warning("⚠️ Primero debes crear referencias en la pestaña 'Referencias'.")
            else:
                with st.expander("➕ Registrar Orden de Compra", expanded=False):
                    with st.form("form_crear_oc", clear_on_submit=True):
                        num_oc = st.text_input("Número de Orden de Compra (Ej: OC-9021)")
                        cliente = st.text_input("Nombre del Cliente")
                        ref_oc = st.selectbox("Referencia Base", lista_refs)
                        servicio_oc = st.selectbox("Servicio Prestado", lista_servicios)
                        
                        requiere_uni = st.checkbox("¿Requiere control por unidades?", value=True)
                        meta_oc = st.number_input("Cantidad Total Pedida (Meta)", min_value=0, value=1000)
                        
                        btn_guardar_oc = st.form_submit_button("Guardar", use_container_width=True)
                        
                        if btn_guardar_oc:
                            if num_oc.strip() and cliente.strip():
                                meta_final = meta_oc if requiere_uni else 0
                                ejecutar_comando(
                                    """INSERT INTO ordenes_compra 
                                    (numero_oc, cliente, referencia, servicio, requiere_unidades, meta_unidades, unidades_entregadas, estado) 
                                    VALUES (%s, %s, %s, %s, %s, %s, 0, 'PENDIENTE')""",
                                    (num_oc.upper().strip(), cliente.strip(), ref_oc, servicio_oc, requiere_uni, meta_final)
                                )
                                st.success("✅ Guardado.")
                                st.rerun()
                            else:
                                st.error("Completa el número de OC y el cliente.")

            st.markdown("---")
            st.markdown("### Estado y Saldos Pendientes")
            df_oc = ejecutar_consulta("SELECT * FROM ordenes_compra ORDER BY id DESC")
            
            if not df_oc.empty:
                df_oc['saldo_pendiente'] = df_oc.apply(
                    lambda row: row['meta_unidades'] - row['unidades_entregadas'] if row['requiere_unidades'] else 'N/A', 
                    axis=1
                )
                st.dataframe(df_oc, use_container_width=True)

                with st.expander("🗑️ Eliminar Orden de Compra", expanded=False):
                    with st.form("form_del_oc", clear_on_submit=True):
                        oc_del = st.selectbox("Selecciona la OC a Borrar", df_oc["numero_oc"].tolist())
                        if st.form_submit_button("Confirmar Eliminación", use_container_width=True):
                            ejecutar_comando("DELETE FROM ordenes_compra WHERE numero_oc = %s", (oc_del,))
                            ejecutar_comando("DELETE FROM programacion_diaria WHERE numero_oc = %s", (oc_del,))
                            ejecutar_comando("DELETE FROM registro_produccion WHERE numero_oc = %s", (oc_del,))
                            st.success("✅ Eliminado.")
                            st.rerun()
            else:
                st.info("No hay órdenes de compra registradas.")

        except Exception as e:
            st.error(f"Error en Órdenes de Compra: {e}")

    # --- TAB 3: MÁQUINAS ---
    with tab_eq:
        st.markdown("### Gestión de Máquinas")
        try:
            df_maqs = ejecutar_consulta("SELECT * FROM maquinas")
            st.dataframe(df_maqs, use_container_width=True)
            
            with st.expander("➕ Registrar Máquina", expanded=False):
                with st.form("form_crear_maquina", clear_on_submit=True):
                    m_nom = st.text_input("Nombre de la Máquina")
                    m_tipo = st.text_input("Tipo (Ej: Corte, Dobladora)")
                    m_prop = st.selectbox("Tipo de Propiedad", ["PROPIA", "ALQUILADA"])
                    
                    if st.form_submit_button("Guardar", use_container_width=True):
                        if m_nom.strip():
                            ejecutar_comando("INSERT INTO maquinas (nombre, tipo, tipo_propiedad) VALUES (%s, %s, %s)", (m_nom, m_tipo, m_prop))
                            st.success("✅ Guardado.")
                            st.rerun()
                        else:
                            st.error("Escribe el nombre.")

            if not df_maqs.empty and rol == "admin":
                with st.expander("🗑️ Eliminar Máquina", expanded=False):
                    with st.form("form_del_maquina", clear_on_submit=True):
                        m_del = st.selectbox("Máquina a Borrar", df_maqs["nombre"].tolist())
                        if st.form_submit_button("Confirmar Eliminación", use_container_width=True):
                            ejecutar_comando("DELETE FROM maquinas WHERE nombre = %s", (m_del,))
                            st.success("✅ Eliminado.")
                            st.rerun()
        except Exception as e:
            st.error(f"Error en Máquinas: {e}")

    # --- TAB 4: SERVICIOS ---
    with tab_serv:
        st.markdown("### Servicios Prestados")
        try:
            df_serv = ejecutar_consulta("SELECT * FROM servicios_prestados ORDER BY id DESC")
            if not df_serv.empty:
                st.dataframe(df_serv, use_container_width=True)
            else:
                st.info("No hay servicios creados.")
            
            with st.expander("➕ Crear Servicio", expanded=False):
                with st.form("form_crear_serv", clear_on_submit=True):
                    nom_serv = st.text_input("Nombre del Servicio")
                    if st.form_submit_button("Guardar", use_container_width=True):
                        if nom_serv.strip():
                            ejecutar_comando("INSERT INTO servicios_prestados (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (nom_serv.upper().strip(),))
                            st.success("✅ Guardado.")
                            st.rerun()
                        else:
                            st.error("Escribe un nombre.")

            if not df_serv.empty and rol == "admin":
                with st.expander("🗑️ Eliminar Servicio", expanded=False):
                    with st.form("form_del_serv", clear_on_submit=True):
                        serv_del = st.selectbox("Servicio a Borrar", df_serv["nombre"].tolist())
                        if st.form_submit_button("Confirmar Eliminación", use_container_width=True):
                            ejecutar_comando("DELETE FROM servicios_prestados WHERE nombre = %s", (serv_del,))
                            st.success("✅ Eliminado.")
                            st.rerun()
        except Exception as e:
            st.error(f"Error en Servicios: {e}")

    # --- TAB 5: REFERENCIAS ---
    with tab_ref:
        st.markdown("### Catálogo de Referencias")
        try:
            df_refs = ejecutar_consulta("SELECT * FROM referencias")
            st.dataframe(df_refs, use_container_width=True)
            
            with st.expander("➕ Crear Referencia", expanded=False):
                with st.form("form_crear_ref", clear_on_submit=True):
                    r_cod = st.text_input("Código Referencia")
                    r_desc = st.text_input("Descripción del Producto")
                    if st.form_submit_button("Guardar", use_container_width=True):
                        ejecutar_comando("INSERT INTO referencias (codigo, descripcion) VALUES (%s, %s)", (r_cod, r_desc))
                        st.success("✅ Guardado.")
                        st.rerun()

            if not df_refs.empty and rol == "admin":
                with st.expander("🗑️ Eliminar Referencia", expanded=False):
                    with st.form("form_del_ref", clear_on_submit=True):
                        r_del = st.selectbox("Referencia a Borrar", df_refs["codigo"].tolist())
                        if st.form_submit_button("Confirmar Eliminación", use_container_width=True):
                            ejecutar_comando("DELETE FROM referencias WHERE codigo = %s", (r_del,))
                            st.success("✅ Eliminado.")
                            st.rerun()
        except Exception as e:
            st.error(f"Error en Referencias: {e}")

    # --- TAB 6: REPORTES ---
    with tab_rep:
        st.markdown("### Centro de Reportes y Excel")
        try:
            st.markdown("#### 1. Reporte de Saldos de Órdenes de Compra")
            df_oc_rep = ejecutar_consulta("SELECT * FROM ordenes_compra ORDER BY id DESC")
            if not df_oc_rep.empty:
                df_oc_rep['saldo_pendiente'] = df_oc_rep.apply(lambda r: r['meta_unidades'] - r['unidades_entregadas'] if r['requiere_unidades'] else 'N/A', axis=1)
                st.dataframe(df_oc_rep, use_container_width=True)
                
                buffer_oc = io.BytesIO()
                with pd.ExcelWriter(buffer_oc, engine='openpyxl') as writer:
                    df_oc_rep.to_excel(writer, index=False, sheet_name='Saldos_OC')
                st.download_button(
                    label="📥 Descargar Reporte de Saldos OC (Excel)",
                    data=buffer_oc.getvalue(),
                    file_name=f"Saldos_OC_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="dl_oc_excel"
                )

            st.markdown("---")
            st.markdown("#### 2. Reporte de Producción Detallado")
            df_prod_rep = ejecutar_consulta("""
                SELECT r.id, r.fecha, r.numero_oc, r.operario_nombre, r.maquina, m.tipo_propiedad as tipo_maquina, 
                       r.referencia, r.hora_inicio_real, r.hora_fin_real, r.unidades_producidas, r.observaciones 
                FROM registro_produccion r 
                JOIN ordenes_compra oc ON r.numero_oc = oc.numero_oc
                JOIN usuarios u ON r.operario_nombre = u.nombre 
                LEFT JOIN maquinas m ON r.maquina = m.nombre
                ORDER BY r.id DESC
            """)
            if not df_prod_rep.empty:
                st.dataframe(df_prod_rep.head(15), use_container_width=True)
                
                buffer_prod = io.BytesIO()
                with pd.ExcelWriter(buffer_prod, engine='openpyxl') as writer:
                    df_prod_rep.to_excel(writer, index=False, sheet_name='Produccion_Detallada')
                st.download_button(
                    label="📥 Descargar Reporte de Producción (Excel)",
                    data=buffer_prod.getvalue(),
                    file_name=f"Produccion_Detallada_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="dl_prod_excel"
                )
            else:
                st.info("No hay registros de producción.")

            st.markdown("---")
            st.markdown("#### 3. Reporte de Inventario")
            df_inv_rep = ejecutar_consulta("SELECT codigo, nombre, tipo as clase, cantidad, stock_minimo FROM inventario")
            if not df_inv_rep.empty:
                st.dataframe(df_inv_rep, use_container_width=True)
                buffer_inv = io.BytesIO()
                with pd.ExcelWriter(buffer_inv, engine='openpyxl') as writer:
                    df_inv_rep.to_excel(writer, index=False, sheet_name='Inventario')
                st.download_button(
                    label="📥 Descargar Reporte de Inventario (Excel)",
                    data=buffer_inv.getvalue(),
                    file_name=f"Inventario_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="dl_inv_excel"
                )

        except Exception as e:
            st.error(f"Error al generar reportes: {e}")

    # --- TAB 7: ENTREGAS ---
    with tab_ent:
        st.markdown("### Registrar Salida de Insumo / Material")
        try:
            ops_df = ejecutar_consulta("SELECT nombre FROM usuarios WHERE rol = 'operario'")
            ops = ops_df['nombre'].tolist() if not ops_df.empty else []
            mats = ejecutar_consulta("SELECT codigo, nombre, cantidad, tipo FROM inventario")
            
            if ops and not mats.empty:
                with st.form("form_entregas", clear_on_submit=True):
                    op_sel = st.selectbox("Operario", ops)
                    mat_sel = st.selectbox("Ítem en Inventario", mats['nombre'].tolist())
                    cant = st.number_input("Cantidad", min_value=1, value=1)
                    
                    if st.form_submit_button("Registrar Salida", use_container_width=True):
                        row = mats[mats['nombre'] == mat_sel].iloc[0]
                        cod, tipo = row['codigo'], row['tipo']
                        
                        ejecutar_comando(
                            "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (%s, %s, %s, %s, %s, 'ENTREGADO')",
                            (datetime.now().strftime("%Y-%m-%d %H:%M"), op_sel, cod, cant, tipo)
                        )
                        ejecutar_comando("UPDATE inventario SET cantidad = cantidad - %s WHERE codigo = %s", (cant, cod))
                        st.success("✅ Salida registrada.")
                        st.rerun()
            else:
                st.info("No hay operarios o ítems disponibles en inventario.")
        except Exception as e:
            st.error(f"Error: {e}")

    # --- TAB 8: HERRAMIENTAS ---
    with tab_herramientas:
        st.markdown("### Préstamos de Herramientas")
        try:
            herramientas_db = ejecutar_consulta("SELECT codigo, nombre, cantidad FROM inventario WHERE tipo ILIKE '%HERRAMIENTA%'")
            if not herramientas_db.empty:
                st.dataframe(herramientas_db, use_container_width=True)
            else:
                st.info("No hay herramientas registradas con la clase 'HERRAMIENTA'.")
            
            ops_df = ejecutar_consulta("SELECT nombre FROM usuarios WHERE rol = 'operario'")
            ops = ops_df['nombre'].tolist() if not ops_df.empty else []
            
            if ops and not herramientas_db.empty:
                with st.expander("🤝 Prestar Herramienta", expanded=False):
                    with st.form("form_prestar_herramienta", clear_on_submit=True):
                        op_her = st.selectbox("Operario", ops)
                        her_sel = st.selectbox("Herramienta", herramientas_db['nombre'].tolist())
                        cant_her = st.number_input("Cantidad", min_value=1, value=1)
                        btn_prestar = st.form_submit_button("Registrar Préstamo", use_container_width=True)
                        
                        if btn_prestar:
                            row_h = herramientas_db[herramientas_db['nombre'] == her_sel].iloc[0]
                            cod_h = row_h['codigo']
                            
                            ejecutar_comando(
                                "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (%s, %s, %s, %s, 'HERRAMIENTA', 'PRESTADO')",
                                (datetime.now().strftime("%Y-%m-%d %H:%M"), op_her, cod_h, cant_her)
                            )
                            st.success("✅ Préstamo registrado.")
                            st.rerun()

            st.markdown("---")
            st.markdown("#### Herramientas Actualmente Prestadas")
            prestados = ejecutar_consulta("""
                SELECT c.id, c.fecha, c.operario, c.codigo_material, i.nombre as herramienta, c.cantidad, c.estado 
                FROM consumos c 
                JOIN usuarios u ON c.operario = u.nombre
                LEFT JOIN inventario i ON c.codigo_material = i.codigo 
                WHERE c.tipo ILIKE '%HERRAMIENTA%' AND c.estado = 'PRESTADO'
            """)
            if not prestados.empty:
                st.dataframe(prestados, use_container_width=True)
                id_dev = st.selectbox("ID de Préstamo a Devolver", prestados['id'].tolist(), key="dev_id_her")
                if st.button("Marcar como Devuelta", use_container_width=True):
                    ejecutar_comando("UPDATE consumos SET estado = 'DEVUELTO' WHERE id = %s", (id_dev,))
                    st.success("✅ Devuelta.")
                    st.rerun()
            else:
                st.success("No hay herramientas pendientes de devolución.")
        except Exception as e:
            st.error(f"Error: {e}")

    # --- TAB 9: CARGUE ---
    with tab_cargue:
        st.markdown("### Cargue Único de Ítems")
        try:
            clases_df = ejecutar_consulta("SELECT nombre FROM clases_inventario")
            lista_clases = clases_df['nombre'].tolist() if not clases_df.empty else []
            
            if not lista_clases:
                st.warning("⚠️ Crea al menos una clase en la pestaña 'Clases'.")
            else:
                with st.form("form_cargue_item", clear_on_submit=True):
                    c_cod = st.text_input("Código del Ítem")
                    c_nom = st.text_input("Nombre del Ítem")
                    c_clase = st.selectbox("Clase / Categoría", lista_clases)
                    c_cant = st.number_input("Cantidad Inicial", min_value=0, value=10)
                    c_min = st.number_input("Stock Mínimo de Alerta", min_value=0, value=5)
                    
                    if st.form_submit_button("Guardar Ítem", use_container_width=True):
                        if c_cod.strip() and c_nom.strip():
                            ejecutar_comando(
                                "INSERT INTO inventario (codigo, nombre, tipo, cantidad, stock_minimo) VALUES (%s, %s, %s, %s, %s)",
                                (c_cod, c_nom, c_clase, c_cant, c_min)
                            )
                            st.success("✅ Guardado.")
                            st.rerun()
                        else:
                            st.error("Completa código y nombre.")
        except Exception as e:
            st.error(f"Error: {e}")

    # --- TAB 10: INVENTARIO GENERAL ---
    with tab_inv_gen:
        st.markdown("### Inventario General")
        try:
            inv_gen = ejecutar_consulta("SELECT codigo, nombre, tipo as clase, cantidad, stock_minimo FROM inventario")
            if not inv_gen.empty:
                st.dataframe(inv_gen, use_container_width=True)
                if rol == "admin":
                    with st.expander("🗑️ Eliminar Ítem", expanded=False):
                        with st.form("form_del_inv", clear_on_submit=True):
                            del_cod_gen = st.selectbox("Código a Eliminar", inv_gen["codigo"].tolist())
                            if st.form_submit_button("Confirmar Eliminación", use_container_width=True):
                                ejecutar_comando("DELETE FROM inventario WHERE codigo = %s", (del_cod_gen,))
                                st.success("✅ Eliminado.")
                                st.rerun()
            else:
                st.info("Inventario vacío.")
        except Exception as e:
            st.error(f"Error: {e}")

    # --- TAB 11: CLASES ---
    with tab_clases:
        st.markdown("### Clases de Inventario")
        try:
            clases_actuales = ejecutar_consulta("SELECT * FROM clases_inventario")
            if not clases_actuales.empty:
                st.dataframe(clases_actuales, use_container_width=True)
            
            with st.expander("➕ Crear Clase", expanded=False):
                with st.form("form_crear_clase", clear_on_submit=True):
                    nueva_clase = st.text_input("Nombre de Clase")
                    if st.form_submit_button("Guardar", use_container_width=True):
                        if nueva_clase.strip():
                            ejecutar_comando("INSERT INTO clases_inventario (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (nueva_clase.upper().strip(),))
                            st.success("✅ Creado.")
                            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    # --- TAB 12: USUARIOS ---
    with tab_usu:
        st.markdown("### Gestión de Usuarios")
        try:
            users_df = ejecutar_consulta("SELECT id, username, nombre, rol FROM usuarios")
            st.dataframe(users_df, use_container_width=True)
            
            with st.expander("➕ Crear Usuario", expanded=False):
                with st.form("form_crear_usuario", clear_on_submit=True):
                    u_user = st.text_input("Usuario")
                    u_pass = st.text_input("Clave", type="password")
                    u_nom = st.text_input("Nombre Completo")
                    u_rol = st.selectbox("Rol", ["operario", "produccion", "admin"])
                    if st.form_submit_button("Guardar", use_container_width=True):
                        ejecutar_comando("INSERT INTO usuarios (username, password, nombre, rol) VALUES (%s, %s, %s, %s)", (u_user, u_pass, u_nom, u_rol))
                        st.success("✅ Creado.")
                        st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
