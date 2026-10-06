import streamlit as st
import pandas as pd
import bodega  # Importa las funciones de tu archivo bodega.py

# Configuración inicial de la página
st.set_page_config(page_title="Sistema de Gestión de Bodega", page_icon="📦", layout="wide")

# Inicializar la base de datos
bodega.conectar_bd()

st.title("📦 Sistema de Gestión de Bodega e Inventario")

# Menú lateral para navegar entre secciones
opcion = st.sidebar.radio(
    "Selecciona una opción:",
    ["📋 Ver Inventario", "➕ Agregar / Sumar Material", "📤 Registrar Entrega", "🗑️ Eliminar Material"]
)

# ---------------------------------------------------------
# OPCIÓN 1: VER INVENTARIO Y REPORTE (AQUÍ PEGAS EL CÓDIGO)
# ---------------------------------------------------------
if opcion == "📋 Ver Inventario":
    st.header("Inventario Actual y Reorden")
    items = bodega.obtener_inventario()
    
    if items:
        # Crear DataFrame para visualizar
        df = pd.DataFrame(items, columns=["Código", "Nombre", "Cantidad", "Stock Mínimo"])
        
        # Resaltar filas con stock en o por debajo del mínimo
        def resaltar_bajo_stock(val):
            color = 'background-color: #ffcccc' if val['Cantidad'] <= val['Stock Mínimo'] else ''
            return [color] * len(val)
        
        st.dataframe(df.style.apply(resaltar_bajo_stock, axis=1), use_container_width=True)
        
        # Filtrar materiales faltantes
        df_faltantes = df[df["Cantidad"] <= df["Stock Mínimo"]].copy()
        
        if not df_faltantes.empty:
            # Calcular cuántas unidades faltan para alcanzar el stock mínimo
            df_faltantes["Cantidad a Pedir"] = df_faltantes["Stock Mínimo"] - df_faltantes["Cantidad"]
            
            st.warning(f"⚠️ **Alerta:** Hay {len(df_faltantes)} material(es) con stock en límite o crítico.")
            st.subheader("🛒 Materiales a Solicitar")
            st.dataframe(df_faltantes[["Código", "Nombre", "Cantidad", "Stock Mínimo", "Cantidad a Pedir"]], use_container_width=True)
            
            # Generar archivo Excel en memoria para descarga
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_faltantes.to_excel(writer, index=False, sheet_name='Materiales_A_Pedir')
            excel_data = output.getvalue()
            
            # Botón de descarga
            st.download_button(
                label="📥 Descargar Reporte de Reorden (Excel)",
                data=excel_data,
                file_name="reporte_materiales_faltantes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.success("✅ Todo el inventario se encuentra sobre el stock mínimo.")
    else:
        st.info("El inventario está vacío actualmente.")

# ---------------------------------------------------------
# OPCIÓN 2: AGREGAR O SUMAR MATERIAL
# ---------------------------------------------------------
elif opcion == "➕ Agregar / Sumar Material":
    st.header("Ingresar Material al Inventario")
    st.caption("Si el código ya existe, la cantidad se sumará al inventario existente.")
    
    with st.form("form_agregar"):
        codigo = st.text_input("Código del Material:").strip()
        nombre = st.text_input("Nombre / Descripción:").strip()
        cantidad = st.number_input("Cantidad a agregar:", min_value=1, step=1, value=1)
        stock_minimo = st.number_input("Stock Mínimo recomendado:", min_value=1, step=1, value=5)
        
        submit = st.form_submit_button("Guardar Material")
        
        if submit:
            if codigo and nombre:
                bodega.agregar_o_sumar_material(codigo, nombre, cantidad, stock_minimo)
                st.success(f"✅ Material '{nombre}' ({codigo}) guardado correctamente.")
            else:
                st.error("❌ Por favor completa el código y el nombre del material.")

# ---------------------------------------------------------
# OPCIÓN 3: REGISTRAR ENTREGA A OPERARIO
# ---------------------------------------------------------
elif opcion == "📤 Registrar Entrega":
    st.header("Salida de Material para Operario")
    items = bodega.obtener_inventario()
    
    if items:
        opciones = {f"{item[0]} - {item[1]} (Disponible: {item[2]})": item[0] for item in items}
        
        operario = st.text_input("Nombre del Operario:").strip()
        seleccion = st.selectbox("Selecciona el Material:", list(opciones.keys()))
        cantidad_entregada = st.number_input("Cantidad a entregar:", min_value=1, step=1, value=1)
        
        if st.button("Registrar Salida", type="primary"):
            if operario:
                codigo_sel = opciones[seleccion]
                exito = bodega.registrar_entrega_operario(codigo_sel, cantidad_entregada, operario)
                
                if exito:
                    st.success(f"✅ Entrega de {cantidad_entregada} unidad(es) registrada a {operario}.")
                    st.rerun()
                else:
                    st.error("❌ No hay suficiente stock disponible para realizar esta entrega.")
            else:
                st.error("❌ Ingresa el nombre del operario.")
    else:
        st.info("No hay materiales registrados en el inventario.")

# ---------------------------------------------------------
# OPCIÓN 4: ELIMINAR MATERIAL
# ---------------------------------------------------------
elif opcion == "🗑️ Eliminar Material":
    st.header("Eliminar Registro de Material")
    items = bodega.obtener_inventario()
    
    if items:
        opciones = {f"{item[0]} - {item[1]} (Stock: {item[2]})": item[0] for item in items}
        seleccion = st.selectbox("Selecciona el material a eliminar de la base de datos:", list(opciones.keys()))
        
        confirmar = st.checkbox("Confirmo que deseo eliminar este material permanentemente.")
        
        if st.button("Eliminar Definitivamente", type="primary"):
            if confirmar:
                codigo_sel = opciones[seleccion]
                bodega.eliminar_material(codigo_sel)
                st.success("✅ Material eliminado de la base de datos.")
                st.rerun()
            else:
                st.warning("⚠️ Debes marcar la casilla de confirmación para eliminar.")
    else:
        st.info("No hay materiales registrados para eliminar.")