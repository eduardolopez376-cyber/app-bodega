import streamlit as st
import pandas as pd
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import bodega

# Configuración inicial de la página
st.set_page_config(page_title="Control de Bodega - Metalgas", layout="wide", page_icon="📦")

# Inicializar Base de Datos
bodega.conectar_bd()

col1, col2 = st.columns([1, 4])

with col1:
    st.image("WhatsApp Image 2026-10-06 at 6.50.00 PM", width=120)

with col2:
    st.title("Sistema de Control de Bodega y Herramientas")
    
# --- ALERTAS DE STOCK BAJO (SOLO MATERIALES) ---
alertas = bodega.obtener_alertas_stock()
if alertas:
    st.warning(f"⚠️ **¡Alerta de Recompra de Materiales!** Hay {len(alertas)} material(es) por debajo o en su límite de stock mínimo:")
    cols_alt = st.columns(min(len(alertas), 4))
    for idx, alt in enumerate(alertas):
        with cols_alt[idx % 4]:
            st.metric(label=f"{alt[1]} ({alt[2]})", value=f"{alt[3]} disp.", delta=f"Mínimo: {alt[4]}", delta_color="inverse")

st.divider()

# Menú principal por pestañas
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🚀 Entregas y Salidas",
    "👷 Carga de Operarios",
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
# PESTAÑA 2: CARGA DE OPERARIOS (PANTALLA EN VIVO)
# ---------------------------------------------------------
with tab2:
    st.header("👷 Consulta de Materiales y Herramientas por Operario")
    st.write("Consulta detallada de todo lo asignado o entregado a cada trabajador.")
    
    lista_operarios = bodega.obtener_operarios()
    if lista_operarios:
        opc_filtro = ["Todos"] + lista_operarios
        operario_filtrado = st.selectbox("Filtrar por Operario Especifico:", opc_filtro)
        
        cargos = bodega.obtener_cargos_por_operario(operario_filtrado)
        
        if cargos:
            df_cargos_view = pd.DataFrame(
                cargos,
                columns=["Operario", "Tipo Ítem", "Código", "Descripción", "Cantidad Total", "Estado", "Último Registro"]
            )
            st.dataframe(df_cargos_view, use_container_width=True)
        else:
            st.info("No hay registros ni entregas asignadas para el operario seleccionado.")
    else:
        st.info("No hay operarios registrados actualmente.")

# ---------------------------------------------------------
# PESTAÑA 3: HERRAMIENTAS PRESTADAS
# ---------------------------------------------------------
with tab3:
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
                bodega.registrar_devolucion_herramienta(dev_datos[0], dev_datos[3], dev_datos[5])
                st.success(f"Herramienta '{dev_datos[4]}' devuelta por {dev_datos[2]} al inventario.")
                st.rerun()
    else:
        st.info("🟢 No hay herramientas prestadas actualmente en poder de ningún operario.")

# ---------------------------------------------------------
# PESTAÑA 4: GESTIÓN DE INVENTARIO
# ---------------------------------------------------------
with tab4:
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
# PESTAÑA 5: GESTIÓN DE OPERARIOS
# ---------------------------------------------------------
with tab5:
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
# PESTAÑA 6: REPORTES EN EXCEL ESTILIZADOS
# ---------------------------------------------------------
with tab6:
    st.header("📊 Generar y Descargar Reporte Estilizado en Excel")
    st.write("Genera un libro con formato corporativo (encabezados oscuros, filas alternadas y anchos ajustados).")
    
    if st.button("📥 Generar Informe Completo con Diseño", type="primary"):
        buffer = io.BytesIO()
        
        # Datasets
        cargos_totales = bodega.obtener_cargos_por_operario()
        df_cargos = pd.DataFrame(
            cargos_totales,
            columns=["Operario", "Tipo Ítem", "Código", "Descripción", "Cantidad Total", "Estado", "Último Registro"]
        ) if cargos_totales else pd.DataFrame(columns=["Operario", "Tipo Ítem", "Código", "Descripción", "Cantidad Total", "Estado", "Último Registro"])
        
        # Solo alertas para Tipo 'Material'
        alertas_data = bodega.obtener_alertas_stock()
        if alertas_data:
            df_pedir = pd.DataFrame(alertas_data, columns=["Código", "Nombre", "Tipo", "Stock Actual", "Stock Mínimo"])
            df_pedir["Cantidad Sugerida a Comprar"] = df_pedir["Stock Mínimo"] - df_pedir["Stock Actual"] + 5
        else:
            df_pedir = pd.DataFrame([["N/A", "Sin necesidades de compra activas para materiales", "-", "-", "-", "-"]], 
                                    columns=["Código", "Nombre", "Tipo", "Stock Actual", "Stock Mínimo", "Cantidad Sugerida a Comprar"])
            
        df_inv_tot = pd.DataFrame(bodega.obtener_inventario(), columns=["Código", "Nombre", "Tipo", "Cantidad Disponible", "Stock Mínimo"])
        df_movs = pd.DataFrame(bodega.obtener_historial_movimientos(), columns=["ID", "Fecha", "Operario", "Código", "Ítem", "Cantidad", "Tipo", "Estado"])

        # Generar Excel con formato
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_cargos.to_excel(writer, sheet_name="Carga General por Operario", index=False)
            df_pedir.to_excel(writer, sheet_name="Materiales a Pedir", index=False)
            df_inv_tot.to_excel(writer, sheet_name="Inventario Total", index=False)
            df_movs.to_excel(writer, sheet_name="Historial Completo", index=False)
            
            # Formato visual con openpyxl
            wb = writer.book
            
            # Estilos
            header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid") # Azul oscuro
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            zebra_fill = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid") # Gris suave
            thin_border = Border(
                left=Side(style="thin", color="D9D9D9"),
                right=Side(style="thin", color="D9D9D9"),
                top=Side(style="thin", color="D9D9D9"),
                bottom=Side(style="thin", color="D9D9D9")
            )
            
            for sheetname in wb.sheetnames:
                ws = wb[sheetname]
                ws.views.sheetView[0].showGridLines = True
                
                # Formatear Encabezado
                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                
                # Formatear Celdas de Datos
                for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column), start=2):
                    is_even = row_idx % 2 == 0
                    for cell in row:
                        cell.border = thin_border
                        cell.alignment = Alignment(vertical="center")
                        if is_even:
                            cell.fill = zebra_fill
                            
                # Autoajustar ancho de columnas
                for col in ws.columns:
                    max_len = 0
                    col_letter = get_column_letter(col[0].column)
                    for cell in col:
                        val_str = str(cell.value or '')
                        if len(val_str) > max_len:
                            max_len = len(val_str)
                    ws.column_dimensions[col_letter].width = max(max_len + 4, 12)
            
        st.download_button(
            label="💾 Descargar Archivo Excel Estilizado",
            data=buffer.getvalue(),
            file_name=f"Reporte_Bodega_Metalgas_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
