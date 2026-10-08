import streamlit as str_lib
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

# Asegurar tablas auxiliares para clases si no existen
def inicializar_tablas_adicionales():
    try:
        ejecutar_comando("""
            CREATE TABLE IF NOT EXISTS clases_inventario (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) UNIQUE NOT NULL
            );
        """)
        res = ejecutar_consulta("SELECT COUNT(*) as total FROM clases_inventario")
        if res.iloc[0]['total'] == 0:
            for c in ["HERRAMIENTA", "INSUMO", "EPP", "REPUESTO"]:
                ejecutar_comando("INSERT INTO clases_inventario (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (c,))
    except Exception:
        pass

inicializar_tablas_adicionales()

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

# PANTALLA DE LOGIN
if not st.session_state["autenticado"]:
    st.title("🔑 Sistema Metal&Co")
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

# ----------------------------------------------------
# ENCABEZADO Y BARRA LATERAL (Usuarios Logueados)
# ----------------------------------------------------
col_logo, col_titulo = st.columns([1, 4], vertical_alignment="center")
with col_logo:
    mostrar_logo(ancho=100)
with col_titulo:
    st.title("Metal&Co - Planta")

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
        st.write("### Mis Herramientas y Materiales A Cargo")
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
                        
                    unidades = st.number_input("Unidades Producidas Buenas", min_value=0, step=1)
                    defectuosas = st.number_input("Unidades Defectuosas (Scrap)", min_value=0, step=1, value=0)
                    obs_usuario = st.text_area("Observaciones / Novedades")
                    
                    submit = st.form_submit_button("Guardar Registro y Finalizar Tarea", type="primary", use_container_width=True)
                    
                    if submit:
                        id_tarea_str = tarea_elegida_str.split(" - ")[0].replace("ID #", "")
                        id_tarea = int(id_tarea_str)
                        row_t = tareas_pendientes[tareas_pendientes['id'] == id_tarea].iloc[0]
                        meta_original = int(row_t['meta_unidades'])
                        
                        if unidades < meta_original:
                            faltantes = meta_original - unidades
                            obs_final = f"⚠️ PRODUCCIÓN PARCIAL: Buenas {unidades} de {meta_original} meta (Defectuosas: {defectuosas}). Faltaron {faltantes} unidades. Nota: {obs_usuario}"
                        else:
                            obs_final = f"✅ Meta cumplida ({unidades}/{meta_original} buenas, Defectuosas: {defectuosas}). {obs_usuario}"
                        
                        ejecutar_comando(
                            """INSERT INTO registro_produccion 
                            (operario_nombre, maquina, referencia, hora_inicio_real, hora_fin_real, unidades_producidas, observaciones) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                            (st.session_state['nombre_usuario'], row_t['maquina'], row_t['referencia'], h_inicio, h_fin, unidades, obs_final)
                        )
                        
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

    with tab_nueva:
        st.subheader("➕ Registrar e Iniciar Tarea Imprevista No Programada")
        st.write("Si surgieron imprevistos y tuviste que realizar una tarea no programada hoy, repórtala aquí directamente:")
        try:
            maqs = ejecutar_consulta("SELECT nombre FROM maquinas")['nombre'].tolist()
            refs = ejecutar_consulta("SELECT codigo FROM referencias")['codigo'].tolist()
            
            if not maqs or not refs:
                st.warning("Faltan máquinas o referencias registradas en el sistema.")
            else:
                with st.form("form_tarea_imprevista"):
                    maq_imp = st.selectbox("Máquina", maqs)
                    ref_imp = st.selectbox("Referencia", refs)
                    act_imp = st.text_input("Actividad / Motivo imprevisto (Ej: Reproceso, Reparación urgente)")
                    
                    c_h1, c_h2 = st.columns(2)
                    with c_h1:
                        h_ini_imp = st.time_input("Hora de Inicio", time(8, 0))
                    with c_h2:
                        h_fin_imp = st.time_input("Hora de Finalización", time(17, 0))
                        
                    uni_imp = st.number_input("Unidades Producidas Buenas", min_value=0, value=1)
                    def_imp = st.number_input("Unidades Defectuosas (Scrap)", min_value=0, value=0)
                    obs_imp = st.text_area("Observaciones del Imprevisto")
                    
                    btn_imp = st.form_submit_button("Guardar e Iniciar Tarea Imprevista", type="primary", use_container_width=True)
                    
                    if btn_imp:
                        obs_final_imp = f"⚡ TAREA IMPREVISTA: {act_imp} | Buenas: {uni_imp}, Defectuosas: {def_imp}. Nota: {obs_imp}"
                        
                        ejecutar_comando(
                            """INSERT INTO registro_produccion 
                            (operario_nombre, maquina, referencia, hora_inicio_real, hora_fin_real, unidades_producidas, observaciones) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                            (st.session_state['nombre_usuario'], maq_imp, ref_imp, h_ini_imp, h_fin_imp, uni_imp, obs_final_imp)
                        )
                        st.success("¡Tarea imprevista registrada y guardada con éxito en los reportes!")
                        st.rerun()
        except Exception as e:
            st.error(f"Error al cargar formulario de tarea imprevista: {e}")

# ====================================================
# VISTA COMPLETA PARA ADMINISTRADOR Y PRODUCCIÓN
# ====================================================
elif rol in ["admin", "produccion"]:
    tab_prog, tab_eq, tab_ref, tab_rep, tab_ent, tab_herramientas, tab_cargue, tab_inv_gen, tab_clases, tab_usu = st.tabs([
        "📅 Programar", 
        "⚙️ Equipos",
        "📄 Referencias",
        "📊 Reportes", 
        "🚀 Entregas", 
        "🔨 Herramientas",
        "📥 Cargue Ítems", 
        "📦 Inventario General",
        "🏷️ Clases / Categorías", 
        "⚙️ Usuarios"
    ])
    
    # --- TAB 1: PROGRAMAR PLANTA ---
    with tab_prog:
        st.subheader("📅 Programación de Planta por Fecha")
        
        fecha_seleccionada = st.date_input("Selecciona el día a consultar/programar", value=datetime.now().date(), key="cal_admin_dia")
        
        try:
            ops_df = ejecutar_consulta("SELECT nombre FROM usuarios WHERE rol = 'operario'")
            ops = ops_df['nombre'].tolist() if not ops_df.empty else []
            
            maqs = ejecutar_consulta("SELECT nombre FROM maquinas")['nombre'].tolist()
            refs = ejecutar_consulta("SELECT codigo FROM referencias")['codigo'].tolist()
            
            if not ops or not maqs or not refs:
                st.warning("⚠️ Asegúrate de tener al menos un usuario registrado con rol 'operario', una máquina y una referencia creadas.")
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
                    idx_maq = maqs.index(row_sel["maquina"]) if row_sel["maquina"] in maqs else 0
                    idx_ref = refs.index(row_sel["referencia"]) if row_sel["referencia"] in refs else 0
                    
                    edit_op = st.selectbox("Operario", ops, index=idx_op, key="e_op_c")
                    edit_maq = st.selectbox("Máquina", maqs, index=idx_maq, key="e_maq_c")
                    edit_ref = st.selectbox("Referencia", refs, index=idx_ref, key="e_ref_c")
                    edit_act = st.text_input("Actividad", value=row_sel["actividad"], key="e_act_c")
                    edit_meta = st.number_input("Meta Unidades", min_value=1, value=int(row_sel["meta_unidades"]), key="e_meta_c")
                    
                    estados_posibles = ["PENDIENTE", "EN PROCESO", "FINALIZADO", "CANCELADO"]
                    idx_est = estados_posibles.index(row_sel["estado"]) if row_sel["estado"] in estados_posibles else 0
                    edit_estado = st.selectbox("Estado", estados_posibles, index=idx_est, key="e_est_c")
                    
                    if st.button("Guardar Cambios", use_container_width=True):
                        ejecutar_comando(
                            """UPDATE programacion_diaria 
                            SET operario_nombre = %s, maquina = %s, referencia = %s, actividad = %s, meta_unidades = %s, estado = %s 
                            WHERE id = %s""",
                            (edit_op, edit_maq, edit_ref, edit_act, edit_meta, edit_estado, id_edit)
                        )
                        st.success("Modificado con éxito.")
                        st.rerun()

                with st.expander("🗑️ Eliminar Programación"):
                    id_del = st.selectbox("ID a Eliminar", df_prog_actual["id"].tolist(), key="del_prog_id_c")
                    if st.button("Confirmar Eliminación", type="primary", use_container_width=True):
                        ejecutar_comando("DELETE FROM programacion_diaria WHERE id = %s", (id_del,))
                        st.success(f"ID #{id_del} eliminado.")
                        st.rerun()
            else:
                st.info(f"No hay actividades programadas para la fecha {fecha_seleccionada}.")

        except Exception as e:
            st.error(f"Error en Programación: {e}")

    # --- TAB 2: EQUIPOS Y MÁQUINAS ---
    with tab_eq:
        st.subheader("⚙️ Gestión de Máquinas y Equipos")
        try:
            df_maqs = ejecutar_consulta("SELECT * FROM maquinas")
            st.dataframe(df_maqs, use_container_width=True)
            
            with st.expander("➕ Crear Nueva Máquina"):
                m_nom = st.text_input("Nombre de Máquina", key="add_m_nom")
                m_tipo = st.text_input("Tipo (Ej: Corte, Dobladora)", key="add_m_tipo")
                if st.button("Guardar Máquina", use_container_width=True):
                    ejecutar_comando("INSERT INTO maquinas (nombre, tipo) VALUES (%s, %s)", (m_nom, m_tipo))
                    st.success("Máquina agregada.")
                    st.rerun()

            if not df_maqs.empty and rol == "admin":
                with st.expander("🗑️ Eliminar Máquina"):
                    m_del = st.selectbox("Máquina a Borrar", df_maqs["nombre"].tolist(), key="del_m_sel")
                    if st.button("Eliminar Máquina", type="primary", use_container_width=True):
                        ejecutar_comando("DELETE FROM maquinas WHERE nombre = %s", (m_del,))
                        st.success(f"Máquina '{m_del}' eliminada.")
                        st.rerun()
        except Exception as e:
            st.error(f"Error en Máquinas: {e}")

    # --- TAB 3: REFERENCIAS ---
    with tab_ref:
        st.subheader("📄 Gestión de Referencias de Productos")
        try:
            df_refs = ejecutar_consulta("SELECT * FROM referencias")
            st.dataframe(df_refs, use_container_width=True)
            
            with st.expander("➕ Crear Nueva Referencia"):
                r_cod = st.text_input("Código Referencia", key="add_r_cod")
                r_desc = st.text_input("Descripción", key="add_r_desc")
                if st.button("Guardar Referencia", use_container_width=True):
                    ejecutar_comando("INSERT INTO referencias (codigo, descripcion) VALUES (%s, %s)", (r_cod, r_desc))
                    st.success("Referencia agregada.")
                    st.rerun()

            if not df_refs.empty and rol == "admin":
                with st.expander("🗑️ Eliminar Referencia"):
                    r_del = st.selectbox("Referencia a Borrar", df_refs["codigo"].tolist(), key="del_r_sel")
                    if st.button("Eliminar Referencia", type="primary", use_container_width=True):
                        ejecutar_comando("DELETE FROM referencias WHERE codigo = %s", (r_del,))
                        st.success(f"Referencia '{r_del}' eliminada.")
                        st.rerun()
        except Exception as e:
            st.error(f"Error en Referencias: {e}")

    # --- TAB 4: REPORTES EXCEL INDEPENDIENTES ---
    with tab_rep:
        st.subheader("📊 Centro de Reportes y Descargas Independientes")
        st.write("Selecciona y descarga en Excel exactamente el reporte que necesitas:")
        
        try:
            # 1. Reporte de Producción
            st.write("---")
            st.write("### 🏭 1. Reporte de Producción de Operarios")
            df_prod_rep = ejecutar_consulta("SELECT * FROM registro_produccion ORDER BY fecha DESC")
            if not df_prod_rep.empty:
                st.dataframe(df_prod_rep.head(10), use_container_width=True)
                buffer_prod = io.BytesIO()
                with pd.ExcelWriter(buffer_prod, engine='openpyxl') as writer:
                    df_prod_rep.to_excel(writer, index=False, sheet_name='Produccion')
                st.download_button(
                    label="📥 Descargar Reporte de Producción en Excel",
                    data=buffer_prod.getvalue(),
                    file_name=f"Reporte_Produccion_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="dl_prod_excel"
                )
                
                with st.expander("🗑️ Eliminar Reportes de Producción Viejos"):
                    id_reporte_del = st.selectbox("Selecciona el ID del Reporte a Borrar", df_prod_rep["id"].tolist(), key="del_reporte_id")
                    if st.button("Confirmar Eliminación de Reporte", type="primary", use_container_width=True):
                        ejecutar_comando("DELETE FROM registro_produccion WHERE id = %s", (id_reporte_del,))
                        st.success(f"Reporte ID #{id_reporte_del} eliminado correctamente.")
                        st.rerun()
            else:
                st.info("No hay registros de producción todavía.")

            # 2. Reporte de Inventario General
            st.write("---")
            st.write("### 📦 2. Reporte de Inventario General")
            df_inv_rep = ejecutar_consulta("SELECT codigo, nombre, tipo as clase, cantidad, stock_minimo FROM inventario")
            if not df_inv_rep.empty:
                st.dataframe(df_inv_rep, use_container_width=True)
                buffer_inv = io.BytesIO()
                with pd.ExcelWriter(buffer_inv, engine='openpyxl') as writer:
                    df_inv_rep.to_excel(writer, index=False, sheet_name='Inventario_General')
                st.download_button(
                    label="📥 Descargar Reporte de Inventario en Excel",
                    data=buffer_inv.getvalue(),
                    file_name=f"Reporte_Inventario_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="dl_inv_excel"
                )
            else:
                st.info("El inventario está vacío.")

            # 3. Reporte de Herramientas y Préstamos
            st.write("---")
            st.write("### 🔨 3. Reporte de Herramientas y Préstamos")
            df_her_rep = ejecutar_consulta("""
                SELECT c.id, c.fecha, c.operario, c.codigo_material, i.nombre as herramienta, c.cantidad, c.estado 
                FROM consumos c 
                LEFT JOIN inventario i ON c.codigo_material = i.codigo 
                WHERE c.tipo ILIKE '%HERRAMIENTA%'
            """)
            if not df_her_rep.empty:
                st.dataframe(df_her_rep, use_container_width=True)
                buffer_her = io.BytesIO()
                with pd.ExcelWriter(buffer_her, engine='openpyxl') as writer:
                    df_her_rep.to_excel(writer, index=False, sheet_name='Herramientas_Prestamos')
                st.download_button(
                    label="📥 Descargar Reporte de Herramientas en Excel",
                    data=buffer_her.getvalue(),
                    file_name=f"Reporte_Herramientas_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="dl_her_excel"
                )
            else:
                st.info("No hay registros de herramientas o préstamos.")

            # 4. Reporte de Entregas / Consumos de Insumos
            st.write("---")
            st.write("### 🚀 4. Reporte de Entregas y Salidas")
            df_ent_rep = ejecutar_consulta("SELECT * FROM consumos ORDER BY id DESC")
            if not df_ent_rep.empty:
                st.dataframe(df_ent_rep.head(10), use_container_width=True)
                buffer_ent = io.BytesIO()
                with pd.ExcelWriter(buffer_ent, engine='openpyxl') as writer:
                    df_ent_rep.to_excel(writer, index=False, sheet_name='Entregas_Salidas')
                st.download_button(
                    label="📥 Descargar Reporte de Entregas en Excel",
                    data=buffer_ent.getvalue(),
                    file_name=f"Reporte_Entregas_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="dl_ent_excel"
                )
            else:
                st.info("No hay entregas registradas.")

        except Exception as e:
            st.error(f"Error al generar reportes: {e}")

    # --- TAB 5: ENTREGAS Y SALIDAS ---
    with tab_ent:
        st.subheader("Registrar Salida de Insumo / Material")
        try:
            ops_df = ejecutar_consulta("SELECT nombre FROM usuarios WHERE rol = 'operario'")
            ops = ops_df['nombre'].tolist() if not ops_df.empty else []
            mats = ejecutar_consulta("SELECT codigo, nombre, cantidad, tipo FROM inventario")
            
            if ops and not mats.empty:
                op_sel = st.selectbox("Operario", ops, key="ent_op")
                mat_sel = st.selectbox("Ítems en Inventario", mats['nombre'].tolist(), key="ent_mat")
                cant = st.number_input("Cantidad", min_value=1, value=1, key="ent_cant")
                
                if st.button("Registrar Salida", type="primary", use_container_width=True):
                    row = mats[mats['nombre'] == mat_sel].iloc[0]
                    cod, tipo = row['codigo'], row['tipo']
                    
                    ejecutar_comando(
                        "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (%s, %s, %s, %s, %s, 'ENTREGADO')",
                        (datetime.now().strftime("%Y-%m-%d %H:%M"), op_sel, cod, cant, tipo)
                    )
                    ejecutar_comando("UPDATE inventario SET cantidad = cantidad - %s WHERE codigo = %s", (cant, cod))
                    st.success("Salida registrada y descontada del inventario.")
                    st.rerun()
            else:
                st.info("No hay operarios o ítems disponibles en inventario.")
        except Exception as e:
            st.error(f"Error en Entregas: {e}")

    # --- TAB 6: HERRAMIENTAS (Disponibles y Prestadas a Operarios) ---
    with tab_herramientas:
        st.subheader("🔨 Control de Herramientas y Préstamos a Operarios")
        try:
            herramientas_db = ejecutar_consulta("SELECT codigo, nombre, cantidad FROM inventario WHERE tipo ILIKE '%HERRAMIENTA%'")
            
            st.write("### Herramientas Disponibles en Stock")
            if not herramientas_db.empty:
                st.dataframe(herramientas_db, use_container_width=True)
            else:
                st.info("No hay herramientas registradas con la clase 'HERRAMIENTA'.")
            
            ops_df = ejecutar_consulta("SELECT nombre FROM usuarios WHERE rol = 'operario'")
            ops = ops_df['nombre'].tolist() if not ops_df.empty else []
            
            if ops and not herramientas_db.empty:
                with st.expander("🤝 Prestar Herramienta a Operario"):
                    with st.form("form_prestar_herramienta"):
                        op_her = st.selectbox("Operario", ops)
                        her_sel = st.selectbox("Herramienta", herramientas_db['nombre'].tolist())
                        cant_her = st.number_input("Cantidad", min_value=1, value=1)
                        btn_prestar = st.form_submit_button("Registrar Préstamo", type="primary", use_container_width=True)
                        
                        if btn_prestar:
                            row_h = herramientas_db[herramientas_db['nombre'] == her_sel].iloc[0]
                            cod_h = row_h['codigo']
                            
                            ejecutar_comando(
                                "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (%s, %s, %s, %s, 'HERRAMIENTA', 'PRESTADO')",
                                (datetime.now().strftime("%Y-%m-%d %H:%M"), op_her, cod_h, cant_her)
                            )
                            st.success(f"Préstamo de {her_sel} registrado a {op_her}.")
                            st.rerun()

            st.write("---")
            st.write("### Herramientas Actualmente Prestadas (Con Detalle de Operario)")
            prestados = ejecutar_consulta("""
                SELECT c.id, c.fecha, c.operario, c.codigo_material, i.nombre as herramienta, c.cantidad, c.estado 
                FROM consumos c 
                LEFT JOIN inventario i ON c.codigo_material = i.codigo 
                WHERE c.tipo ILIKE '%HERRAMIENTA%' AND c.estado = 'PRESTADO'
            """)
            if not prestados.empty:
                st.dataframe(prestados, use_container_width=True)
                id_dev = st.selectbox("ID de Préstamo a Devolver", prestados['id'].tolist(), key="dev_id_her")
                if st.button("Marcar Herramienta como Devuelta", use_container_width=True):
                    ejecutar_comando("UPDATE consumos SET estado = 'DEVUELTO' WHERE id = %s", (id_dev,))
                    st.success("¡Herramienta marcada como devuelta y restaurada!")
                    st.rerun()
            else:
                st.success("No hay herramientas pendientes de devolución.")
        except Exception as e:
            st.error(f"Error en Herramientas: {e}")

    # --- TAB 7: CARGUE DE ÍTEMS ---
    with tab_cargue:
        st.subheader("📥 Cargue Único de Ítems (Herramientas, Insumos, EPP, Repuestos)")
        try:
            clases_df = ejecutar_consulta("SELECT nombre FROM clases_inventario")
            lista_clases = clases_df['nombre'].tolist() if not clases_df.empty else ["HERRAMIENTA", "INSUMO", "EPP", "REPUESTO"]
            
            with st.form("form_cargue_item"):
                c_cod = st.text_input("Código del Ítem")
                c_nom = st.text_input("Nombre del Ítem")
                c_clase = st.selectbox("Clase / Categoría", lista_clases)
                c_cant = st.number_input("Cantidad Inicial", min_value=0, value=10)
                c_min = st.number_input("Stock Mínimo de Alerta (0 si no aplica)", min_value=0, value=5)
                
                btn_guardar_item = st.form_submit_button("Guardar Ítem en Inventario", type="primary", use_container_width=True)
                
                if btn_guardar_item:
                    if c_cod.strip() and c_nom.strip():
                        ejecutar_comando(
                            "INSERT INTO inventario (codigo, nombre, tipo, cantidad, stock_minimo) VALUES (%s, %s, %s, %s, %s)",
                            (c_cod, c_nom, c_clase, c_cant, c_min)
                        )
                        st.success(f"Ítem '{c_nom}' guardado con éxito bajo la clase {c_clase}.")
                        st.rerun()
                    else:
                        st.error("Por favor completa el código y el nombre del ítem.")
        except Exception as e:
            st.error(f"Error en Cargue de Ítems: {e}")

    # --- TAB 8: INVENTARIO GENERAL ---
    with tab_inv_gen:
        st.subheader("📦 Inventario General de la Empresa")
        try:
            inv_gen = ejecutar_consulta("SELECT codigo, nombre, tipo as clase, cantidad, stock_minimo FROM inventario")
            
            if not inv_gen.empty:
                criticos = inv_gen[(inv_gen['stock_minimo'] > 0) & (inv_gen['cantidad'] <= inv_gen['stock_minimo'])]
                if not criticos.empty:
                    st.warning("⚠️ **¡Alerta de Stock Bajo en los siguientes ítems!**")
                    st.dataframe(criticos, use_container_width=True)
                
                st.write("### Listado Consolidado")
                st.dataframe(inv_gen, use_container_width=True)

                if rol == "admin":
                    with st.expander("🗑️ Eliminar Ítem del Inventario General"):
                        del_cod_gen = st.selectbox("Código a Eliminar", inv_gen["codigo"].tolist(), key="del_gen_sel")
                        if st.button("Confirmar Eliminación de Ítem", type="primary", use_container_width=True):
                            ejecutar_comando("DELETE FROM inventario WHERE codigo = %s", (del_cod_gen,))
                            st.success("Ítem eliminado del inventario.")
                            st.rerun()
            else:
                st.info("El inventario general se encuentra vacío.")
        except Exception as e:
            st.error(f"Error en Inventario General: {e}")

    # --- TAB 9: CLASES / CATEGORÍAS ---
    with tab_clases:
        st.subheader("🏷️ Administración de Clases y Categorías")
        st.write("Crea nuevas clases (como Neumática, Eléctricos, etc.) si tu operación lo requiere.")
        try:
            clases_actuales = ejecutar_consulta("SELECT * FROM clases_inventario")
            st.dataframe(clases_actuales, use_container_width=True)
            
            with st.form("form_crear_clase"):
                nueva_clase = st.text_input("Nombre de la Nueva Clase (Ej: REPUESTO_ELECTRICO)")
                btn_crear_clase = st.form_submit_button("Crear Nueva Clase", type="primary", use_container_width=True)
                
                if btn_crear_clase:
                    if nueva_clase.strip():
                        ejecutar_comando("INSERT INTO clases_inventario (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (nueva_clase.upper().strip(),))
                        st.success(f"Clase '{nueva_clase.upper()}' creada con éxito.")
                        st.rerun()
                    else:
                        st.error("Escribe un nombre válido para la clase.")
        except Exception as e:
            st.error(f"Error en Clases: {e}")

    # --- TAB 10: USUARIOS Y PERMISOS ---
    with tab_usu:
        st.subheader("⚙️ Administrar Usuarios")
        try:
            users_df = ejecutar_consulta("SELECT id, username, nombre, rol FROM usuarios")
            st.dataframe(users_df, use_container_width=True)
            
            with st.expander("➕ Crear Usuario"):
                u_user = st.text_input("Usuario", key="u1")
                u_pass = st.text_input("Clave", type="password", key="u2")
                u_nom = st.text_input("Nombre Completo", key="u3")
                u_rol = st.selectbox("Rol", ["operario", "produccion", "admin"], key="u4")
                if st.button("Guardar Usuario", use_container_width=True):
                    ejecutar_comando("INSERT INTO usuarios (username, password, nombre, rol) VALUES (%s, %s, %s, %s)", (u_user, u_pass, u_nom, u_rol))
                    st.success("Usuario creado.")
                    st.rerun()

            with st.expander("✏️ Editar Permisos/Clave"):
                usr_sel = st.selectbox("Usuario", users_df["username"].tolist(), key="e1")
                n_pass = st.text_input("Nueva Clave", type="password", key="e2")
                n_rol = st.selectbox("Nuevo Rol", ["operario", "produccion", "admin"], key="e3")
                if st.button("Actualizar Usuario", use_container_width=True):
                    if n_pass.strip():
                        ejecutar_comando("UPDATE usuarios SET password = %s, rol = %s WHERE username = %s", (n_pass, n_rol, usr_sel))
                    else:
                        ejecutar_comando("UPDATE usuarios SET rol = %s WHERE username = %s", (n_rol, usr_sel))
                    st.success("Actualizado.")
                    st.rerun()

            with st.expander("🗑️ Eliminar Usuario"):
                u_del = st.selectbox("Usuario a Eliminar", users_df["username"].tolist(), key="d1")
                if st.button("Confirmar Borrado", type="primary", use_container_width=True):
                    if u_del != st.session_state["username"]:
                        ejecutar_comando("DELETE FROM usuarios WHERE username = %s", (u_del,))
                        st.success("Eliminado.")
                        st.rerun()
                    else:
                        st.error("No puedes borrar tu propio usuario.")
        except Exception as e:
            st.error(f"Error en Usuarios: {e}")
