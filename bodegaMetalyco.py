import streamlit as st
import pandas as pd
import psycopg2
import os
from datetime import datetime

# Configuración de página
st.set_page_config(
    page_title="Control de Bodega - Metal&Co",
    page_icon="📦",
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
    st.title("🔑 Sistema de Control - Metal&Co")
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
# ENCABEZADO Y BARRA LATERAL (Cerrar Sesión)
# ----------------------------------------------------
col_logo, col_titulo = st.columns([1, 5], vertical_alignment="center")
with col_logo:
    mostrar_logo(ancho=110)
with col_titulo:
    st.title("Sistema de Control de Bodega y Herramientas")

st.sidebar.markdown(f"👤 **Usuario:** {st.session_state['nombre_usuario']}")
st.sidebar.markdown(f"🔰 **Rol:** `{st.session_state['rol'].upper()}`")

if st.sidebar.button("🔒 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# ----------------------------------------------------
# VISTAS SEGÚN ROL
# ----------------------------------------------------
rol = st.session_state["rol"]

# ====================================================
# VISTA EXCLUSIVA PARA OPERARIOS
# ====================================================
if rol == "operario":
    st.subheader(f"📌 Panel del Operario: {st.session_state['nombre_usuario']}")
    
    tab_prog, tab_prod = st.tabs(["📋 Tareas y Materiales Asignados", "⚙️ Registrar Producción"])
    
    with tab_prog:
        st.write("### Mis Tareas Programadas para Hoy")
        try:
            tareas = ejecutar_consulta(
                "SELECT fecha, tarea, estado FROM programacion_diaria WHERE operario_nombre = %s ORDER BY id DESC",
                (st.session_state['nombre_usuario'],)
            )
            if not tareas.empty:
                st.dataframe(tareas, use_container_width=True)
            else:
                st.info("No tienes tareas programadas asignadas para hoy.")
        except Exception as e:
            st.error(f"Error al cargar tareas: {e}")
            
        st.write("### Mis Materiales y Herramientas a Cargo")
        try:
            herramientas = ejecutar_consulta(
                "SELECT fecha, codigo_material, cantidad, tipo FROM consumos WHERE operario = %s AND estado = 'PRESTADO'",
                (st.session_state['nombre_usuario'],)
            )
            if not herramientas.empty:
                st.dataframe(herramientas, use_container_width=True)
            else:
                st.success("No tienes herramientas ni materiales pendientes de devolución.")
        except Exception as e:
            st.error(f"Error al cargar materiales: {e}")

    with tab_prod:
        st.write("### Registrar Reporte Diario de Producción")
        with st.form("form_reporte_operario"):
            unidades = st.number_input("Cantidad de unidades producidas hoy", min_value=1, step=1)
            obs = st.text_area("Observaciones o Novedades")
            submit = st.form_submit_button("Guardar Registro de Producción")
            
            if submit:
                try:
                    ejecutar_comando(
                        "INSERT INTO registro_produccion (operario_nombre, unidades_producidas, observaciones) VALUES (%s, %s, %s)",
                        (st.session_state['nombre_usuario'], unidades, obs)
                    )
                    st.success("¡Registro de producción guardado exitosamente!")
                except Exception as e:
                    st.error(f"Error al registrar producción: {e}")

# ====================================================
# VISTA COMPLETA PARA ADMINISTRADOR Y PRODUCCIÓN
# ====================================================
elif rol in ["admin", "produccion"]:
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🚀 Entregas y Salidas", 
        "🔨 Herramientas Prestadas", 
        "📦 Gestión de Inventario", 
        "👥 Gestión de Operarios", 
        "📅 Programar Producción", 
        "📊 Reportes Producción",
        "⚙️ Gestión Usuarios"
    ])
    
    with tab1:
        st.subheader("Registrar Salida de Material o Préstamo de Herramienta")
        try:
            ops = ejecutar_consulta("SELECT nombre FROM operarios")['nombre'].tolist()
            mats = ejecutar_consulta("SELECT codigo, nombre, tipo FROM inventario")
            
            if not ops:
                st.warning("No hay operarios registrados. Ve a la pestaña '👥 Gestión de Operarios'.")
            else:
                op_sel = st.selectbox("Seleccionar Operario", ops)
                mat_sel = st.selectbox("Seleccionar Material/Herramienta", mats['nombre'].tolist())
                cant = st.number_input("Cantidad", min_value=1, value=1)
                
                if st.button("Registrar Salida/Préstamo"):
                    row = mats[mats['nombre'] == mat_sel].iloc[0]
                    cod = row['codigo']
                    tipo = row['tipo']
                    
                    estado = "PRESTADO" if tipo == "HERRAMIENTA" else "ENTREGADO"
                    
                    ejecutar_comando(
                        "INSERT INTO consumos (fecha, operario, codigo_material, cantidad, tipo, estado) VALUES (%s, %s, %s, %s, %s, %s)",
                        (datetime.now().strftime("%Y-%m-%d %H:%M"), op_sel, cod, cant, tipo, estado)
                    )
                    
                    if tipo == "CONSUMIBLE":
                        ejecutar_comando("UPDATE inventario SET cantidad = cantidad - %s WHERE codigo = %s", (cant, cod))
                    
                    st.success(f"Registrado correctamente a {op_sel}.")
        except Exception as e:
            st.error(f"Error en Entregas: {e}")

    with tab2:
        st.subheader("Herramientas en Préstamo")
        try:
            prestados = ejecutar_consulta("SELECT id, fecha, operario, codigo_material, cantidad FROM consumos WHERE tipo = 'HERRAMIENTA' AND estado = 'PRESTADO'")
            st.dataframe(prestados, use_container_width=True)
            
            if not prestados.empty:
                id_dev = st.selectbox("Seleccionar ID para Devolución", prestados['id'].tolist())
                if st.button("Marcar Devuelto"):
                    ejecutar_comando("UPDATE consumos SET estado = 'DEVUELTO' WHERE id = %s", (id_dev,))
                    st.success("Herramienta devuelta al inventario.")
                    st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    with tab3:
        st.subheader("Inventario de Bodega")
        try:
            inv = ejecutar_consulta("SELECT * FROM inventario")
            st.dataframe(inv, use_container_width=True)
            
            with st.expander("➕ Agregar Nuevo Material u Herramienta"):
                c_cod = st.text_input("Código")
                c_nom = st.text_input("Nombre / Descripción")
                c_tipo = st.selectbox("Tipo", ["CONSUMIBLE", "HERRAMIENTA"])
                c_cant = st.number_input("Cantidad Inicial", min_value=0, value=1)
                c_min = st.number_input("Stock Mínimo", min_value=0, value=5)
                
                if st.button("Guardar en Inventario"):
                    ejecutar_comando(
                        "INSERT INTO inventario (codigo, nombre, tipo, cantidad, stock_minimo) VALUES (%s, %s, %s, %s, %s)",
                        (c_cod, c_nom, c_tipo, c_cant, c_min)
                    )
                    st.success("Material guardado.")
                    st.rerun()
        except Exception as e:
            st.error(f"Error en Inventario: {e}")

    with tab4:
        st.subheader("Lista de Operarios")
        try:
            ops_df = ejecutar_consulta("SELECT * FROM operarios")
            st.dataframe(ops_df, use_container_width=True)
            
            with st.form("form_add_op"):
                nom_op = st.text_input("Nombre Completo del Operario")
                if st.form_submit_button("Añadir Operario"):
                    ejecutar_comando("INSERT INTO operarios (nombre) VALUES (%s)", (nom_op,))
                    st.success("Operario añadido.")
                    st.rerun()
        except Exception as e:
            st.error(f"Error en Operarios: {e}")

    with tab5:
        st.subheader("📅 Programar Ordenes de Trabajo Diarias")
        try:
            ops_list = ejecutar_consulta("SELECT nombre FROM operarios")['nombre'].tolist()
            if ops_list:
                op_prog = st.selectbox("Operario a Asignar", ops_list)
                tarea_prog = st.text_area("Descripción de la Tarea / Orden de Producción")
                if st.button("Asignar Tarea"):
                    ejecutar_comando(
                        "INSERT INTO programacion_diaria (operario_nombre, tarea) VALUES (%s, %s)",
                        (op_prog, tarea_prog)
                    )
                    st.success(f"Tarea asignada a {op_prog}.")
            
            st.write("---")
            st.write("### Programación Actual")
            st.dataframe(ejecutar_consulta("SELECT * FROM programacion_diaria ORDER BY id DESC"), use_container_width=True)
        except Exception as e:
            st.error(f"Error en Programación: {e}")

    with tab6:
        st.subheader("📊 Reportes de Producción Diaria por Operario")
        try:
            rep = ejecutar_consulta("SELECT * FROM registro_produccion ORDER BY fecha DESC")
            st.dataframe(rep, use_container_width=True)
        except Exception as e:
            st.error(f"Error en Reportes: {e}")

    with tab7:
        st.subheader("⚙️ Administrar Usuarios, Contraseñas y Permisos")
        try:
            users_df = ejecutar_consulta("SELECT id, username, nombre, rol FROM usuarios")
            st.dataframe(users_df, use_container_width=True)
            
            col_add, col_edit, col_del = st.columns(3)
            
            # --- 1. CREAR NUEVO USUARIO ---
            with col_add:
                with st.expander("➕ Añadir Usuario"):
                    nu_user = st.text_input("Usuario (Login)", key="add_user")
                    nu_pass = st.text_input("Contraseña", type="password", key="add_pass")
                    nu_nom = st.text_input("Nombre Completo", key="add_nom")
                    nu_rol = st.selectbox("Rol/Permiso", ["operario", "produccion", "admin"], key="add_rol")
                    
                    if st.button("Guardar Usuario"):
                        if nu_user and nu_pass and nu_nom:
                            ejecutar_comando(
                                "INSERT INTO usuarios (username, password, nombre, rol) VALUES (%s, %s, %s, %s)",
                                (nu_user, nu_pass, nu_nom, nu_rol)
                            )
                            st.success("Usuario creado exitosamente.")
                            st.rerun()
                        else:
                            st.warning("Completa todos los campos.")

            # --- 2. EDITAR ROL O CAMBIAR CONTRASEÑA ---
            with col_edit:
                with st.expander("✏️ Editar Usuario / Clave"):
                    lista_usuarios = users_df["username"].tolist()
                    usr_sel = st.selectbox("Seleccionar Usuario", lista_usuarios, key="edit_usr_sel")
                    
                    nueva_clave = st.text_input("Nueva Contraseña (dejar vacío si no cambia)", type="password", key="edit_pass")
                    nuevo_rol = st.selectbox("Cambiar Rol/Permiso", ["operario", "produccion", "admin"], key="edit_rol")
                    
                    if st.button("Actualizar Usuario"):
                        if nueva_clave.strip():
                            ejecutar_comando(
                                "UPDATE usuarios SET password = %s, rol = %s WHERE username = %s",
                                (nueva_clave, nuevo_rol, usr_sel)
                            )
                        else:
                            ejecutar_comando(
                                "UPDATE usuarios SET rol = %s WHERE username = %s",
                                (nuevo_rol, usr_sel)
                            )
                        st.success(f"Usuario '{usr_sel}' actualizado.")
                        st.rerun()

            # --- 3. ELIMINAR USUARIO ---
            with col_del:
                with st.expander("🗑️ Eliminar Usuario"):
                    usr_del_sel = st.selectbox("Usuario a Eliminar", users_df["username"].tolist(), key="del_usr_sel")
                    
                    if st.button("Confirmar Eliminación", type="primary"):
                        if usr_del_sel == st.session_state["username"]:
                            st.error("No puedes eliminar tu propia cuenta en uso.")
                        else:
                            ejecutar_comando("DELETE FROM usuarios WHERE username = %s", (usr_del_sel,))
                            st.success(f"Usuario '{usr_del_sel}' eliminado.")
                            st.rerun()
                            
        except Exception as e:
            st.error(f"Error en Gestión de Usuarios: {e}")
