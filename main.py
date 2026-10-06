import streamlit as st
import pandas as pd
import io
import bodega

# Configuración inicial de la página
st.set_page_config(page_title="Control de Bodega - Metalgas", layout="wide", page_icon="📦")

# Inicializar Base de Datos
bodega.conectar_bd()

st.title("📦 Sistema de Control de Bodega y Herramientas")

# --- ALERTAS DE STOCK BAJO ---
alertas = bodega.obtener_alertas_stock()
if alertas:
    st.warning(f"⚠️ **¡Alerta de Stock Bajo!** Hay {len(alertas)} ítem(s) que están por debajo o en su límite de stock mínimo:")
    cols_alt = st.columns(min(len(alertas), 4))
    for idx, alt in enumerate(alertas):
        with cols_alt[idx % 4]:
            st.metric(label=f"{alt[1]} ({alt[2]})", value=f"{alt[3]} disp.", delta=f"Mínimo: {alt[4]}", delta_color="inverse")

st.divider()

# Menú principal por pestañas
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚀 Entregas y Salidas",
    "🔨 Herramientas Prestadas",
    "📦 Gestión de Inventario",
    "👥 Gestión de Operarios",
    "📊 Reportes Excel"
])

# ---------------------------------------------------------
# PESTAÑA 1: ENTREGAS Y SALIDAS
# ---------------------------------------------------------
with tab1:
    st.header("Registrar Salida de Material o Préstamo de Herramienta")
    
    operarios = bodega.obtener_operarios()
    inventario_items = bodega.obtener_inventario()
    
    if not operarios:
        st.error("⚠️ No hay operarios registrados. Ve a la pestaña '👥 Gestión de Operarios' para añadir uno.")
    elif not inventario_items:
        st.error("⚠️ No hay ítems en el inventario. Ve a '📦 Gestión de Inventario' para agregar materiales o herramientas.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            operario_sel = st.selectbox("Seleccionar Operario:", operarios)
            
            # Formatear opciones para el selector
            opciones_inv = {f"[{item[2]}] {item[1]} (Stock: {item[3]})": item for item in inventario_items}
            item_sel_key = st.selectbox("Seleccionar Material / Herramienta:", list(opciones_inv.keys()))
            item_datos = opciones_inv[item_sel_key]
            
        with col2:
            codigo_item = item_datos[0]
            nombre_item = item_datos[1]
            tipo_item = item_datos[2]
            stock_disp = item_datos[3]
            
            st.info(f"**Tipo:** {tipo_item} | **Código:** `{codigo_item}` | **Disponible:** {stock_disp}")
            cant_salida = st.number_input("Cantidad a Entregar:", min_value=1, max_value=max(1, stock_disp), value=1)
            
            if st.button("🔴 Confirmar Salida / Préstamo", type="primary", use_container_width=True):
                exito, msg = bodega.registrar_entrega(codigo_item, cant_salida, operario_sel)
                if exito:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

# ---------------------------------------------------------
# PESTAÑA 2: HERRAMIENTAS PRESTADAS
# ---------------------------------------------------------
with tab2:
    st.header("🔨 Herramientas actualmente en poder de Operarios")
    
    herramientas_activas = bodega.obtener_herramientas_en_poder()
    
    if herramientas_activas:
        df_herramientas = pd.DataFrame(
            herramientas_activas,
            columns=["ID Registro", "Fecha Préstamo", "Operario", "Código", "Herramienta", "Cantidad"]
        )
        st.dataframe(df_herramientas[["Fecha Préstamo", "Operario", "Código", "Herramienta", "Cantidad"]], use_container_width=True)
        
        st.subheader("Devolver Herramienta a Bodega")
        col_dev1, col_dev2 = st.columns([3, 1])
        
        with col_dev1:
            opciones_dev = {
                f"{h[2]} - {h[4]} ({h[5]} unidad/es) - Prestado el {h[1]}": h for h in herramientas_activas
            }
            dev_key = st.selectbox("Seleccionar préstamo a devolver:", list(opciones_dev.keys()))
            dev_datos = opciones_dev[dev_key]
            
        with col_dev2:
            st.write("")
            st.write("")
            if st.button("🟢 Devolver a Bodega", use_container_width=True):
                # id_consumo, codigo_material, cantidad
                bodega.registrar_devolucion_herramienta(dev_datos[0], dev_datos[3], dev_datos[5])
                st.success(f"Herramienta '{dev_datos[4]}' devuelta por {dev_datos[2]} al inventario.")
                st.rerun()
    else:
        st.info("🟢 No hay herramientas prestadas actualmente en poder de ningún operario.")

# ---------------------------------------------------------
# PESTAÑA 3: GESTIÓN DE INVENTARIO
# ---------------------------------------------------------
with tab3:
    st.header("📦 Control de Inventario (Agregar / Sumar / Eliminar)")
    
    st.subheader("1. Agregar o Sumar Stock")
    with st.form("form_inventario", clear_on_submit=True):
        col_i1, col_i2, col_i3 = st.columns([2, 3, 2])
        
        with col_i1:
            codigo = st.text_input("Código del Ítem:").strip()
            tipo = st.selectbox("Tipo:", ["Material", "Herramienta"])
        with col_i2:
            nombre = st.text_input("Nombre / Descripción:").strip()
            cant = st.number_input("Cantidad a agregar:", min_value=1, value=1)
        with col_i3:
            stock_min = st.number_input("Stock Mínimo (Alerta):", min_value=1, value=5)
            st.write("")
            btn_guardar = st.form_submit_button("➕ Guardar en Inventario", use_container_width=True)
            
        if btn_guardar:
            if codigo and nombre:
                bodega.agregar_o_actualizar_item(codigo, nombre, tipo, cant, stock_min)
                st.success(f"¡Ítem `{codigo}` - {nombre} actualizado correctamente!")
                st.rerun()
            else:
                st.error("Por favor completa el código y el nombre del ítem.")
                
    st.divider()
    
    st.subheader("2. Inventario Actual")
    inv_data = bodega.obtener_inventario()
    if inv_data:
        df_inv = pd.DataFrame(inv_data, columns=["Código", "Nombre", "Tipo", "Cantidad Disponible", "Stock Mínimo"])
        st.dataframe(df_inv, use_container_width=True)
        
        # Eliminar ítem del inventario
        with st.expander("🗑️ Eliminar un ítem del Inventario"):
            opc_elim = {f"{item[0]} - {item[1]}": item[0] for item in inv_data}
            item_a_eliminar = st.selectbox("Selecciona el ítem que deseas eliminar:", list(opc_elim.keys()))
            if st.button("❌ Confirmar Eliminación", type="secondary"):
                bodega.eliminar_item_inventario(opc_elim[item_a_eliminar])
                st.success("Ítem eliminado del inventario.")
                st.rerun()
    else:
        st.info("El inventario está vacío.")

# ---------------------------------------------------------
# PESTAÑA 4: GESTIÓN DE OPERARIOS
# ---------------------------------------------------------
with tab4:
    st.header("👥 Administración de Operarios")
    
    col_op1, col_op2 = st.columns(2)
    
    with col_op1:
        st.subheader("Registrar Nuevo Operario")
        nuevo_op = st.text_input("Nombre Completo del Operario:")
        if st.button("➕ Agregar Operario"):
            if bodega.agregar_operario(nuevo_op):
                st.success(f"Operario '{nuevo_op}' registrado correctamente.")
                st.rerun()
            else:
                st.error("Error: El nombre no puede estar vacío o ya existe.")
                
    with col_op2:
        st.subheader("Operarios Registrados")
        ops = bodega.obtener_operarios()
        if ops:
            for op in ops:
                col_n, col_b = st.columns([3, 1])
                col_n.write(f"• **{op}**")
                if col_b.button("Eliminar", key=f"del_{op}"):
                    bodega.eliminar_operario(op)
                    st.rerun()
        else:
            st.info("No hay operarios registrados.")

# ---------------------------------------------------------
# PESTAÑA 5: REPORTES EN EXCEL
# ---------------------------------------------------------
with tab5:
    st.header("📊 Generar y Descargar Reportes en Excel")
    st.write("Descarga un libro de Excel consolidado con las solicitudes de compra necesarias y el estado actual del personal.")
    
    if st.button("📥 Generar Informe Completo en Excel", type="primary"):
        buffer = io.BytesIO()
        
        # 1. Datos para pedir (Stock Bajo)
        alertas_data = bodega.obtener_alertas_stock()
        df_pedir = pd.DataFrame(alertas_data, columns=["Código", "Nombre", "Tipo", "Stock Actual", "Stock Mínimo"])
        if not df_pedir.empty:
            df_pedir["Sugerido a Comprar"] = df_pedir["Stock Mínimo"] - df_pedir["Stock Actual"] + 5
            
        # 2. Inventario Total
        inv_data = bodega.obtener_inventario()
        df_inv_tot = pd.DataFrame(inv_data, columns=["Código", "Nombre", "Tipo", "Cantidad", "Stock Mínimo"])
        
        # 3. Herramientas en Poder de Operarios
        herramientas_data = bodega.obtener_herramientas_en_poder()
        df_herramientas_ops = pd.DataFrame(
            herramientas_data, 
            columns=["ID Préstamo", "Fecha", "Operario", "Código", "Herramienta", "Cantidad"]
        )
        
        # 4. Historial Completo de Movimientos
        movs = bodega.obtener_historial_movimientos()
        df_movs = pd.DataFrame(
            movs,
            columns=["ID", "Fecha", "Operario", "Código", "Ítem", "Cantidad", "Tipo", "Estado"]
        )

        # Crear Excel con múltiples pestañas
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_pedir.to_excel(writer, sheet_name="Materiales a Pedir", index=False)
            df_herramientas_ops.to_excel(writer, sheet_name="Herramientas por Operario", index=False)
            df_inv_tot.to_excel(writer, sheet_name="Inventario Total", index=False)
            df_movs.to_excel(writer, sheet_name="Historial Completo", index=False)
            
        st.download_button(
            label="💾 Descargar Archivo Excel",
            data=buffer.getvalue(),
            file_name=f"Reporte_Bodega_Metalgas_{pd.Timestamp.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
