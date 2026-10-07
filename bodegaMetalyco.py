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
# CONTROL DE SESIÓN Y LOGIN
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
        user_input = st.text_input("Usuario")
        pass_input = st.text_input("Contraseña", type="password")
        
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
                    st.success("¡Bienvenido!")
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
    st.rerun()

rol = st.session_state["rol"]

# ====================================================
# VISTA EXCLUSIVA PARA OPERARIOS (CON TAREAS PENDIENTES QUE DESAPARECEN)
# ====================================================
if rol == "operario":
    st.subheader(f"📌 Hola, {st.session_state['nombre_usuario']}")
    
    tab_prog, tab_prod = st.tabs(["📋 Mi Programación por Día", "⚙️ Registrar Producción"])
    
    with tab_prog:
        st.write("### Consulta tus Tareas Asignadas")
        fecha_operario = st.date_input("Selecciona el día a consultar", value=datetime.now().date(), key="cal_op_dia")
        
        try:
            # Solo muestra las tareas que NO estén finalizadas o canceladas
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
            # Traer solo las tareas pendientes del día de hoy para que las seleccione
            tareas_pendientes = ejecutar_consulta(
                """SELECT id, actividad, maquina, referencia FROM programacion_diaria 
                   WHERE operario_nombre = %s AND fecha = CURRENT_DATE AND estado NOT IN ('FINALIZADO', 'CANCELADO')""",
                (st.session_state['nombre_usuario'],)
            )
            
            if tareas_pendientes.empty:
                st.warning("No tienes tareas pendientes asignadas para hoy para reportar.")
            else:
                # Crear opciones descriptivas para el selectbox
                lista_opciones = [
                    f"ID #{row['id']} - {row['actividad']} (Máq: {row['maquina']} | Ref: {row['referencia']})" 
                    for _, row in tareas_pendientes.iterrows()
                ]
                
                with st.form("form_reporte_operario"):
                    tarea_elegida_str = st.selectbox("Selecciona la Tarea a Registrar", lista_opciones)
                    
                    h_inicio = st.time_input("Hora de Inicio Real", time(7, 0))
                    h_fin = st.time_input("Hora de Finalización Real", time(17, 0))
                        
                    unidades = st.number_input("Unidades Producidas", min_value=1, step=1)
                    obs = st.text_area("Observaciones / Novedades")
                    
                    submit = st.form_submit_button("Guardar y Finalizar Tarea", type="primary", use_container_width=True)
                    
                    if submit:
                        # Extraer el ID de la tarea seleccionada del texto
                        id_tarea_str = tarea_elegida_str.split(" - ")[0].replace("ID #", "")
                        id_tarea = int(id_tarea_str)
                        
                        # Obtener detalles de esa tarea para guardarlos en el registro de producción
                        row_t = tareas_pendientes[tareas_pendientes['id'] == id_tarea].iloc[0]
                        
                        # 1. Guardar en registro de producción
                        ejecutar_comando(
                            """INSERT INTO registro_produccion 
                            (operario_nombre, maquina, referencia, hora_inicio_real, hora_fin_real, unidades_producidas, observaciones) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                            (st.session_state['nombre_usuario'], row_t['maquina'], row_t['referencia'], h_inicio, h_fin, unidades, obs)
                        )
                        
                        # 2. Marcar la tarea como FINALIZADA para que desaparezca de pendientes
                        ejecutar_comando(
                            "UPDATE programacion_diaria SET estado = 'FINALIZADO' WHERE id = %s",
                            (id_tarea,)
                        )
                        
                        st.success("¡Producción guardada y tarea completada con éxito!")
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
                    idx_maq = maqs.index(row_sel["maquina"]) if row_sel["maquina"] in maqs else 0
                    idx_ref = refs.index(row_sel["referencia"]) if row_sel["referencia"] in refs else 0
                    
                    edit_op = st.selectbox("Operario", ops, index=idx_op, key="e_op_c")
                    edit_maq = st.selectbox("Máquina", maqs, index=idx_maq, key="e_maq_c")
                    edit_ref = st.selectbox("Referencia", refs, index=idx_ref, key="e_ref_c")
                    edit_act = st.text_input("Actividad", value=row_sel["actividad"], key="e_act_c")
                    edit_meta = st.number_input("Meta Unidades", min_value=1, value=int(row_sel["meta_unidades"]), key="e_meta_c")
                    edit_estado = st.selectbox("Estado", ["PENDIENTE", "EN PROCESO", "FINALIZADO", "CANCELADO"], 
                                                index=["PENDIENTE", "EN PROCESO", "FINALIZADO", "CANCELADO"].index(row_sel["estado"]) if row_sel["estado"] in ["PENDIENTE", "EN PROCESO", "FINALIZADO", "CANCELADO"] else 0, 
                                                key="e_est_c")
                    
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

    # --- TAB 4: REPORTES EXCEL ---
    with tab3:
        st.subheader("📊 Historial General de Producción")
        try:
            df_prod = ejecutar_consulta("SELECT * FROM registro_produccion ORDER BY fecha DESC")
            
            if not df_prod.empty:
                st.dataframe(df_prod, use_container_width=True)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_prod.to_excel(writer, index=False, sheet_name='Produccion_Operarios')
                
                st.download_button(
                    label="📥 Descargar Reporte Histórico Completo en Excel",
                    data=buffer.getvalue(),
                    file_name=f"Reporte_Produccion_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

                if rol == "admin":
                    with st.expander("🗑️ Eliminar Registro"):
                        prod_del = st.selectbox("ID de Reporte a Eliminar", df_prod["id"].tolist(), key="del_prod_sel")
                        if st.button("Eliminar Reporte", type="primary", use_container_width=True):
                            ejecutar_comando("DELETE FROM registro_produccion WHERE id = %s", (prod_del,))
                            st.success(f"Reporte #{prod_del} eliminado.")
                            st.rerun()
            else:
                st.info("Aún no hay reportes registrados.")
        except Exception as e:
            st.error(f"Error en reportes: {e}")

    # --- TAB 5: ENTREGAS Y SALIDAS ---
    with tab4:
        st.subheader("Registrar Salida de Material")
        try:
            ops = ejecutar_consulta("SELECT nombre FROM operarios")['nombre'].tolist()
            mats = ejecutar_consulta("SELECT codigo, nombre, tipo FROM inventario")
            
            if ops and not mats.empty:
                op_sel = st.selectbox("Operario", ops, key="ent_op")
                mat_sel = st.selectbox("Material/Herramienta", mats['nombre'].tolist(), key="ent_mat")
                cant = st.number_input("Cantidad", min_value=1, value=1, key="ent_cant")
                
                if st.button("Registrar Salida", type="primary", use_container_width=True):
                    row = mats[mats['nombre'] == mat_sel].iloc[0]
                    cod, tipo = row['codigo'], row['tipo']
                    estado = "PRESTADO" if tipo == "HERRAMIENTA" else "ENTREGADO"
                    
                    ejecutar_comando(
                        "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (%s, %s, %s, %s, %s, %s)",
                        (datetime.now().strftime("%Y-%m-%d %H:%M"), op_sel, cod, cant, tipo, estado)
                    )
                    if tipo == "CONSUMIBLE":
                        ejecutar_comando("UPDATE inventario SET cantidad = cantidad - %s WHERE codigo = %s", (cant, cod))
                    st.success("Salida registrada.")
        except Exception as e:
            st.error(f"Error en Entregas: {e}")

    # --- TAB 6: HERRAMIENTAS ---
    with tab5:
        st.subheader("Herramientas Prestadas")
        try:
            prestados = ejecutar_consulta("SELECT id, fecha, operario, codigo_material, cantidad FROM consumos WHERE tipo = 'HERRAMIENTA' AND estado = 'PRESTADO'")
            st.dataframe(prestados, use_container_width=True)
            if not prestados.empty:
                id_dev = st.selectbox("ID a Devolver", prestados['id'].tolist(), key="dev_id")
                if st.button("Marcar Devuelto", use_container_width=True):
                    ejecutar_comando("UPDATE consumos SET estado = 'DEVUELTO' WHERE id = %s", (id_dev,))
                    st.success("Herramienta devuelta.")
                    st.rerun()

                if rol == "admin":
                    with st.expander("🗑️ Eliminar Préstamo"):
                        del_pres = st.selectbox("ID Préstamo a Eliminar", prestados['id'].tolist(), key="del_pres_id")
                        if st.button("Eliminar Préstamo", type="primary", use_container_width=True):
                            ejecutar_comando("DELETE FROM consumos WHERE id = %s", (del_pres,))
                            st.success(f"Registro #{del_pres} eliminado.")
                            st.rerun()
        except Exception as e:
            st.error(f"Error en Herramientas: {e}")

    # --- TAB 7: INVENTARIO ---
    with tab6:
        st.subheader("Gestión de Inventario")
        try:
            inv = ejecutar_consulta("SELECT * FROM inventario")
            st.dataframe(inv, use_container_width=True)
            
            with st.expander("➕ Agregar Insumo / Herramienta"):
                c_cod = st.text_input("Código Insumo", key="inv_add_cod")
                c_nom = st.text_input("Nombre", key="inv_add_nom")
                c_tipo = st.selectbox("Tipo", ["CONSUMIBLE", "HERRAMIENTA"], key="inv_add_tipo")
                c_cant = st.number_input("Cantidad Inicial", min_value=0, value=1, key="inv_add_cant")
                c_min = st.number_input("Stock Mínimo", min_value=0, value=5, key="inv_add_min")
                if st.button("Guardar Insumo", use_container_width=True):
                    ejecutar_comando(
                        "INSERT INTO inventario (codigo, nombre, tipo, cantidad, stock_minimo) VALUES (%s, %s, %s, %s, %s)",
                        (c_cod, c_nom, c_tipo, c_cant, c_min)
                    )
                    st.success("Insumo Guardado.")
                    st.rerun()

            if not inv.empty and rol == "admin":
                with st.expander("🗑️ Eliminar del Inventario"):
                    inv_del_cod = st.selectbox("Código a Borrar", inv["codigo"].tolist(), key="inv_del_sel")
                    if st.button("Eliminar Insumo", type="primary", use_container_width=True):
                        ejecutar_comando("DELETE FROM inventario WHERE codigo = %s", (inv_del_cod,))
                        st.success(f"Insumo '{inv_del_cod}' eliminado.")
                        st.rerun()
        except Exception as e:
            st.error(f"Error en Inventario: {e}")

    # --- TAB 8: USUARIOS Y PERMISOS ---
    with tab7:
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
                    if u_rol == "operario":
                        ejecutar_comando("INSERT INTO operarios (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (u_nom,))
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
