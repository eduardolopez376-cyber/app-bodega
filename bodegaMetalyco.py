import streamlit as st
import pandas as pd
import psycopg2
import os
import io
from datetime import datetime, time

# Configuración de página
st.set_page_config(
    page_title="Control de Producción - Metal&Co",
    page_icon="⚙️",
    layout="wide"
)

# Buscar imagen disponible en el directorio
NOMBRES_LOGO = ["WhatsApp Image 2026-10-06 at 6.50.00 PM.jpeg", "logo.jpeg", "logo.png", "logo.jpg"]
LOGO_PATH = None
for nombre in NOMBRES_LOGO:
    if os.path.exists(nombre):
        LOGO_PATH = nombre
        break

def mostrar_logo(ancho=120):
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
    st.title("🔑 Sistema de Control y Producción - Metal&Co")
    st.subheader("Inicio de Sesión")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        mostrar_logo(ancho=130)
    with col2:
        user_input = st.text_input("Usuario")
        pass_input = st.text_input("Contraseña", type="password")
        
        if st.button("Ingresar", type="primary"):
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
col_logo, col_titulo = st.columns([1, 5], vertical_alignment="center")
with col_logo:
    mostrar_logo(ancho=110)
with col_titulo:
    st.title("Sistema de Gestión de Producción y Bodega")

st.sidebar.markdown(f"👤 **Usuario:** {st.session_state['nombre_usuario']}")
st.sidebar.markdown(f"🔰 **Rol:** `{st.session_state['rol'].upper()}`")

if st.sidebar.button("🔒 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

rol = st.session_state["rol"]

# ====================================================
# VISTA EXCLUSIVA PARA OPERARIOS
# ====================================================
if rol == "operario":
    st.subheader(f"📌 Panel de Trabajo: {st.session_state['nombre_usuario']}")
    
    tab_prog, tab_prod = st.tabs(["📋 Mi Programación del Día", "⚙️ Registrar Reporte de Producción"])
    
    with tab_prog:
        st.write("### Mis Tareas Asignadas para Hoy")
        try:
            tareas = ejecutar_consulta(
                "SELECT hora_inicio, hora_fin, maquina, referencia, actividad, meta_unidades, estado FROM programacion_diaria WHERE operario_nombre = %s ORDER BY id DESC",
                (st.session_state['nombre_usuario'],)
            )
            if not tareas.empty:
                st.dataframe(tareas, use_container_width=True)
            else:
                st.info("No tienes tareas asignadas programadas actualmente.")
        except Exception as e:
            st.error(f"Error al cargar programación: {e}")
            
        st.write("### Mis Materiales y Herramientas a Cargo")
        try:
            herramientas = ejecutar_consulta(
                "SELECT fecha, codigo_material, cantidad, tipo FROM consumos WHERE operario = %s AND estado = 'PRESTADO'",
                (st.session_state['nombre_usuario'],)
            )
            if not herramientas.empty:
                st.dataframe(herramientas, use_container_width=True)
            else:
                st.success("No tienes materiales pendientes a cargo.")
        except Exception as e:
            st.error(f"Error al cargar consumos: {e}")

    with tab_prod:
        st.write("### Registrar Tiempo y Unidades Producidas")
        try:
            ref_df = ejecutar_consulta("SELECT codigo FROM referencias")
            maq_df = ejecutar_consulta("SELECT nombre FROM maquinas")
            
            lista_refs = ref_df["codigo"].tolist() if not ref_df.empty else ["N/A"]
            lista_maqs = maq_df["nombre"].tolist() if not maq_df.empty else ["N/A"]
            
            with st.form("form_reporte_operario"):
                ref_selected = st.selectbox("Seleccionar Referencia Producida", lista_refs)
                maq_selected = st.selectbox("Máquina Utilizada", lista_maqs)
                
                c_h1, c_h2 = st.columns(2)
                with c_h1:
                    h_inicio = st.time_input("Hora de Inicio de Producción", time(7, 0))
                with c_h2:
                    h_fin = st.time_input("Hora de Finalización de Producción", time(17, 0))
                    
                unidades = st.number_input("Cantidad de Unidades Producidas", min_value=1, step=1)
                obs = st.text_area("Observaciones o Novedades en Planta")
                
                submit = st.form_submit_button("Guardar Registro de Producción")
                
                if submit:
                    ejecutar_comando(
                        """INSERT INTO registro_produccion 
                        (operario_nombre, maquina, referencia, hora_inicio_real, hora_fin_real, unidades_producidas, observaciones) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (st.session_state['nombre_usuario'], maq_selected, ref_selected, h_inicio, h_fin, unidades, obs)
                    )
                    st.success("¡Registro de producción guardado correctamente!")
        except Exception as e:
            st.error(f"Error al guardar reporte: {e}")

# ====================================================
# VISTA COMPLETA PARA ADMINISTRADOR Y PRODUCCIÓN
# ====================================================
elif rol in ["admin", "produccion"]:
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📅 Programar Planta", 
        "⚙️ Maquinas y Referencias",
        "📊 Reportes Excel", 
        "🚀 Entregas y Salidas", 
        "🔨 Herramientas", 
        "📦 Inventario", 
        "⚙️ Usuarios y Permisos"
    ])
    
    # --- TAB 1: PROGRAMAR PLANTA ---
    with tab1:
        st.subheader("📅 Asignación de Turnos, Máquinas y Tareas a Operarios")
        try:
            ops = ejecutar_consulta("SELECT nombre FROM operarios")['nombre'].tolist()
            maqs = ejecutar_consulta("SELECT nombre FROM maquinas")['nombre'].tolist()
            refs = ejecutar_consulta("SELECT codigo FROM referencias")['codigo'].tolist()
            
            if not ops or not maqs or not refs:
                st.warning("Asegúrate de registrar Operarios, Máquinas y Referencias antes de programar.")
            else:
                with st.expander("➕ Crear Nueva Programación", expanded=True):
                    with st.form("form_programacion"):
                        col_p1, col_p2, col_p3 = st.columns(3)
                        with col_p1:
                            op_p = st.selectbox("Seleccionar Operario", ops)
                            maq_p = st.selectbox("Asignar Máquina", maqs)
                        with col_p2:
                            ref_p = st.selectbox("Asignar Referencia", refs)
                            act_p = st.text_input("Actividad / Operación (Ej: Corte, Plegado, Soldadura)")
                        with col_p3:
                            h_ini_p = st.time_input("Hora Inicio Turno", time(7, 0))
                            h_fin_p = st.time_input("Hora Fin Turno", time(17, 0))
                        
                        meta_p = st.number_input("Meta de Unidades A Producir", min_value=1, value=100)
                        btn_prog = st.form_submit_button("Asignar Programación al Operario")
                        
                        if btn_prog:
                            ejecutar_comando(
                                """INSERT INTO programacion_diaria 
                                (operario_nombre, maquina, referencia, actividad, hora_inicio, hora_fin, meta_unidades) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                                (op_p, maq_p, ref_p, act_p, h_ini_p, h_fin_p, meta_p)
                            )
                            st.success(f"Programación asignada correctamente a {op_p}.")
                            st.rerun()
            
            st.write("---")
            st.write("### Programación Actual en Planta")
            df_prog_actual = ejecutar_consulta("SELECT * FROM programacion_diaria ORDER BY id DESC")
            st.dataframe(df_prog_actual, use_container_width=True)

            if not df_prog_actual.empty:
                col_e1, col_e2 = st.columns(2)
                
                # --- EDITAR PROGRAMACIÓN ---
                with col_e1:
                    with st.expander("✏️ Editar Programación Existente"):
                        id_edit = st.selectbox("Seleccionar ID a Modificar", df_prog_actual["id"].tolist(), key="edit_prog_id")
                        row_sel = df_prog_actual[df_prog_actual["id"] == id_edit].iloc[0]
                        
                        # Preselección de datos
                        idx_op = ops.index(row_sel["operario_nombre"]) if row_sel["operario_nombre"] in ops else 0
                        idx_maq = maqs.index(row_sel["maquina"]) if row_sel["maquina"] in maqs else 0
                        idx_ref = refs.index(row_sel["referencia"]) if row_sel["referencia"] in refs else 0
                        
                        edit_op = st.selectbox("Operario", ops, index=idx_op, key="e_op")
                        edit_maq = st.selectbox("Máquina", maqs, index=idx_maq, key="e_maq")
                        edit_ref = st.selectbox("Referencia", refs, index=idx_ref, key="e_ref")
                        edit_act = st.text_input("Actividad", value=row_sel["actividad"], key="e_act")
                        edit_meta = st.number_input("Meta Unidades", min_value=1, value=int(row_sel["meta_unidades"]), key="e_meta")
                        edit_estado = st.selectbox("Estado", ["PENDIENTE", "EN PROCESO", "FINALIZADO", "CANCELADO"], 
                                                   index=["PENDIENTE", "EN PROCESO", "FINALIZADO", "CANCELADO"].index(row_sel["estado"]) if row_sel["estado"] in ["PENDIENTE", "EN PROCESO", "FINALIZADO", "CANCELADO"] else 0, 
                                                   key="e_est")
                        
                        if st.button("Guardar Cambios de Programación"):
                            ejecutar_comando(
                                """UPDATE programacion_diaria 
                                SET operario_nombre = %s, maquina = %s, referencia = %s, actividad = %s, meta_unidades = %s, estado = %s 
                                WHERE id = %s""",
                                (edit_op, edit_maq, edit_ref, edit_act, edit_meta, edit_estado, id_edit)
                            )
                            st.success("Programación modificada con éxito.")
                            st.rerun()

                # --- ELIMINAR PROGRAMACIÓN ---
                with col_e2:
                    with st.expander("🗑️ Eliminar Programación"):
                        id_del = st.selectbox("Seleccionar ID a Eliminar", df_prog_actual["id"].tolist(), key="del_prog_id")
                        
                        if st.button("Confirmar Eliminación de Registro", type="primary"):
                            ejecutar_comando("DELETE FROM programacion_diaria WHERE id = %s", (id_del,))
                            st.success(f"Programación ID #{id_del} eliminada.")
                            st.rerun()

        except Exception as e:
            st.error(f"Error en Programación: {e}")

    # --- TAB 2: MÁQUINAS Y REFERENCIAS ---
    with tab2:
        st.subheader("⚙️ Configuración de Máquinas y Referencias de Producción")
        c_m, c_r = st.columns(2)
        
        with c_m:
            st.write("#### 🛠️ Gestión de Máquinas")
            try:
                st.dataframe(ejecutar_consulta("SELECT * FROM maquinas"), use_container_width=True)
                with st.expander("➕ Crear Nueva Máquina"):
                    m_nom = st.text_input("Nombre / Código de Máquina")
                    m_tipo = st.text_input("Área / Tipo (Ej: Corte Laser, Dobladora)")
                    if st.button("Guardar Máquina"):
                        ejecutar_comando("INSERT INTO maquinas (nombre, tipo) VALUES (%s, %s)", (m_nom, m_tipo))
                        st.success("Máquina agregada.")
                        st.rerun()
            except Exception as e:
                st.error(f"Error en Máquinas: {e}")

        with c_r:
            st.write("#### 📄 Gestión de Referencias")
            try:
                st.dataframe(ejecutar_consulta("SELECT * FROM referencias"), use_container_width=True)
                with st.expander("➕ Crear Nueva Referencia"):
                    r_cod = st.text_input("Código de Referencia")
                    r_desc = st.text_input("Descripción del Producto")
                    if st.button("Guardar Referencia"):
                        ejecutar_comando("INSERT INTO referencias (codigo, descripcion) VALUES (%s, %s)", (r_cod, r_desc))
                        st.success("Referencia agregada.")
                        st.rerun()
            except Exception as e:
                st.error(f"Error en Referencias: {e}")

    # --- TAB 3: REPORTES EXCEL Y TIEMPOS ---
    with tab3:
        st.subheader("📊 Reporte Consolidado de Producción y Tiempos Trabajos")
        try:
            df_prod = ejecutar_consulta("SELECT * FROM registro_produccion ORDER BY fecha DESC")
            
            if not df_prod.empty:
                st.write("### Registros de Planta")
                st.dataframe(df_prod, use_container_width=True)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_prod.to_excel(writer, index=False, sheet_name='Produccion_Operarios')
                
                st.download_button(
                    label="📥 Descargar Reporte Completo en Excel",
                    data=buffer.getvalue(),
                    file_name=f"Reporte_Produccion_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("Aún no hay reportes registrados por los operarios.")
        except Exception as e:
            st.error(f"Error cargando reportes: {e}")

    # --- TAB 4: ENTREGAS Y SALIDAS ---
    with tab4:
        st.subheader("Registrar Salida de Material o Préstamo")
        try:
            ops = ejecutar_consulta("SELECT nombre FROM operarios")['nombre'].tolist()
            mats = ejecutar_consulta("SELECT codigo, nombre, tipo FROM inventario")
            
            if ops and not mats.empty:
                op_sel = st.selectbox("Operario", ops, key="ent_op")
                mat_sel = st.selectbox("Material/Herramienta", mats['nombre'].tolist(), key="ent_mat")
                cant = st.number_input("Cantidad", min_value=1, value=1, key="ent_cant")
                
                if st.button("Registrar Salida/Préstamo"):
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

    # --- TAB 5: HERRAMIENTAS ---
    with tab5:
        st.subheader("Herramientas Prestadas")
        try:
            prestados = ejecutar_consulta("SELECT id, fecha, operario, codigo_material, cantidad FROM consumos WHERE tipo = 'HERRAMIENTA' AND estado = 'PRESTADO'")
            st.dataframe(prestados, use_container_width=True)
            if not prestados.empty:
                id_dev = st.selectbox("ID a Devolver", prestados['id'].tolist())
                if st.button("Marcar Devuelto"):
                    ejecutar_comando("UPDATE consumos SET estado = 'DEVUELTO' WHERE id = %s", (id_dev,))
                    st.success("Herramienta devuelta.")
                    st.rerun()
        except Exception as e:
            st.error(f"Error en Herramientas: {e}")

    # --- TAB 6: INVENTARIO ---
    with tab6:
        st.subheader("Gestión de Inventario")
        try:
            inv = ejecutar_consulta("SELECT * FROM inventario")
            st.dataframe(inv, use_container_width=True)
            with st.expander("➕ Agregar Insumo"):
                c_cod = st.text_input("Código Insumo")
                c_nom = st.text_input("Nombre")
                c_tipo = st.selectbox("Tipo", ["CONSUMIBLE", "HERRAMIENTA"])
                c_cant = st.number_input("Cantidad", min_value=0, value=1)
                c_min = st.number_input("Stock Mínimo", min_value=0, value=5)
                if st.button("Guardar Insumo"):
                    ejecutar_comando(
                        "INSERT INTO inventario (codigo, nombre, tipo, cantidad, stock_minimo) VALUES (%s, %s, %s, %s, %s)",
                        (c_cod, c_nom, c_tipo, c_cant, c_min)
                    )
                    st.success("Insumo Guardado.")
                    st.rerun()
        except Exception as e:
            st.error(f"Error en Inventario: {e}")

    # --- TAB 7: USUARIOS Y PERMISOS ---
    with tab7:
        st.subheader("⚙️ Administrar Usuarios y Permisos")
        try:
            users_df = ejecutar_consulta("SELECT id, username, nombre, rol FROM usuarios")
            st.dataframe(users_df, use_container_width=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                with st.expander("➕ Crear Usuario"):
                    u_user = st.text_input("Usuario", key="u1")
                    u_pass = st.text_input("Clave", type="password", key="u2")
                    u_nom = st.text_input("Nombre Completo", key="u3")
                    u_rol = st.selectbox("Rol", ["operario", "produccion", "admin"], key="u4")
                    if st.button("Guardar Usuario"):
                        ejecutar_comando("INSERT INTO usuarios (username, password, nombre, rol) VALUES (%s, %s, %s, %s)", (u_user, u_pass, u_nom, u_rol))
                        if u_rol == "operario":
                            ejecutar_comando("INSERT INTO operarios (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (u_nom,))
                        st.success("Usuario creado.")
                        st.rerun()
            with c2:
                with st.expander("✏️ Editar Permisos/Clave"):
                    usr_sel = st.selectbox("Usuario", users_df["username"].tolist(), key="e1")
                    n_pass = st.text_input("Nueva Clave", type="password", key="e2")
                    n_rol = st.selectbox("Nuevo Rol", ["operario", "produccion", "admin"], key="e3")
                    if st.button("Actualizar"):
                        if n_pass.strip():
                            ejecutar_comando("UPDATE usuarios SET password = %s, rol = %s WHERE username = %s", (n_pass, n_rol, usr_sel))
                        else:
                            ejecutar_comando("UPDATE usuarios SET rol = %s WHERE username = %s", (n_rol, usr_sel))
                        st.success("Actualizado.")
                        st.rerun()
            with c3:
                with st.expander("🗑️ Eliminar Usuario"):
                    u_del = st.selectbox("Eliminar", users_df["username"].tolist(), key="d1")
                    if st.button("Confirmar Borrado", type="primary"):
                        if u_del != st.session_state["username"]:
                            ejecutar_comando("DELETE FROM usuarios WHERE username = %s", (u_del,))
                            st.success("Eliminado.")
                            st.rerun()
                        else:
                            st.error("No puedes borrar tu usuario en sesión.")
        except Exception as e:
            st.error(f"Error en Usuarios: {e}")
 
