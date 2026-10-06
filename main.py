import streamlit as st
import pandas as pd
import io
import bodega

st.set_page_config(page_title="Gestión de Bodega", page_icon="📦", layout="wide")

# Inicializar BD
bodega.conectar_bd()

st.title("📦 Sistema de Control de Bodega")

pestana1, pestana2, pestana3, pestana4, pestana5 = st.tabs([
    "📤 Entregas", 
    "🛠️ Herramientas en Poder", 
    "👥 Operarios", 
    "📊 Reportes Excel", 
    "📋 Inventario"
])

# --- PESTAÑA 1: ENTREGAS ---
with pestana1:
    st.header("Registrar Salida de Material o Herramienta")
    lista_operarios = bodega.obtener_operarios()
    items_inv = bodega.obtener_inventario()
    
    if not lista_operarios:
        st.warning("⚠️ Debes agregar al menos un operario en la pestaña '👥 Operarios' primero.")
    elif not items_inv:
        st.warning("⚠️ No hay elementos en el inventario.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            op_seleccionado = st.selectbox("Seleccionar Operario:", lista_operarios)
            # Formatear opciones de inventario
            df_inv = pd.DataFrame(items_inv, columns=["Codigo", "Nombre", "Tipo", "Cantidad", "Stock Min"])
            item_sel_str = st.selectbox("Seleccionar Ítem:", df_inv["Codigo"] + " - " + df_inv["Nombre"])
            cod_item = item_sel_str.split(" - ")[0]
            
            row_item = df_inv[df_inv["Codigo"] == cod_item].iloc[0]
            st.info(f"**Tipo:** {row_item['Tipo']} | **Disponible:** {row_item['Cantidad']}")

        with col2:
            cant_entregar = st.number_input("Cantidad a entregar:", min_value=1, value=1)
            if st.button("🚀 Confirmar Entrega", use_container_width=True):
                exito, msg = bodega.registrar_entrega(cod_item, cant_entregar, op_seleccionado)
                if exito:
                    st.success(f"✅ Se entregó a {op_seleccionado}.")
                    st.rerun()
                else:
                    st.error(f"❌ Error: {msg}")

# --- PESTAÑA 2: HERRAMIENTAS EN PODER ---
with pestana2:
    st.header("🛠️ Herramientas Prestadas por Operario")
    movs = bodega.obtener_movimientos()
    
    if movs:
        df_movs = pd.DataFrame(movs, columns=["ID", "Fecha", "Operario", "Codigo", "Nombre", "Cantidad", "Tipo", "Estado"])
        prestados = df_movs[(df_movs["Tipo"] == "Herramienta") & (df_movs["Estado"] == "Prestado")]
        
        if prestados.empty:
            st.success("🎉 No hay herramientas prestadas actualmente.")
        else:
            op_filtro = st.selectbox("Filtrar por Operario:", ["Todos"] + bodega.obtener_operarios())
            if op_filtro != "Todos":
                prestados = prestados[prestados["Operario"] == op_filtro]
            
            st.dataframe(prestados[["Fecha", "Operario", "Codigo", "Nombre", "Cantidad", "Estado"]], use_container_width=True)
            
            st.subheader("Registrar Devolución")
            opciones_dev = {row["ID"]: f"{row['Operario']} - {row['Nombre']} (Cant: {row['Cantidad']})" for _, row in prestados.iterrows()}
            id_dev = st.selectbox("Seleccionar herramienta a devolver:", list(opciones_dev.keys()), format_func=lambda x: opciones_dev[x])
            
            if st.button("🔄 Devolver a Bodega"):
                row_dev = prestados[prestados["ID"] == id_dev].iloc[0]
                bodega.registrar_devolucion_herramienta(id_dev, row_dev["Codigo"], row_dev["Cantidad"])
                st.success("✅ Herramienta devuelta al inventario.")
                st.rerun()
    else:
        st.info("No hay registros de movimientos.")

# --- PESTAÑA 3: OPERARIOS ---
with pestana3:
    st.header("👥 Gestión de Operarios")
    col_a, col_b = st.columns(2)
    with col_a:
        nuevo_op = st.text_input("Nombre completo del Operario:")
        if st.button("➕ Guardar Operario"):
            if nuevo_op.strip():
                if bodega.agregar_operario(nuevo_op):
                    st.success(f"Operario '{nuevo_op}' guardado.")
                    st.rerun()
                else:
                    st.error("El operario ya existe.")
            else:
                st.warning("Escribe un nombre válido.")
    with col_b:
        st.subheader("Lista de Operarios Registrados")
        ops = bodega.obtener_operarios()
        st.dataframe(pd.DataFrame(ops, columns=["Nombre del Operario"]), use_container_width=True)

# --- PESTAÑA 4: EXCEL ---
with pestana4:
    st.header("📊 Exportar Reportes en Excel")
    movs = bodega.obtener_movimientos()
    
    if movs:
        df_movs = pd.DataFrame(movs, columns=["ID", "Fecha", "Operario", "Codigo", "Nombre", "Cantidad", "Tipo", "Estado"])
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_movs.to_excel(writer, sheet_name="Historial General", index=False)
            
            mat_df = df_movs[df_movs["Tipo"] == "Material"]
            if not mat_df.empty:
                resumen = mat_df.groupby(["Operario", "Nombre"])["Cantidad"].sum().reset_index()
                resumen.to_excel(writer, sheet_name="Consumo por Operario", index=False)
                
            herr_df = df_movs[(df_movs["Tipo"] == "Herramienta") & (df_movs["Estado"] == "Prestado")]
            herr_df.to_excel(writer, sheet_name="Herramientas Prestadas", index=False)

        output.seek(0)
        st.download_button(
            label="📥 Descargar Reporte Completo en Excel (.xlsx)",
            data=output,
            file_name="Reporte_Bodega.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        st.dataframe(df_movs, use_container_width=True)
    else:
        st.info("No hay datos para exportar.")

# --- PESTAÑA 5: INVENTARIO Y REGISTRO ---
with pestana5:
    st.header("📋 Gestión de Inventario")
    
    with st.expander("➕ Agregar / Actualizar Producto o Herramienta"):
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            cod = st.text_input("Código de Ítem:")
            nom = st.text_input("Nombre / Descripción:")
            tipo_item = st.selectbox("Tipo de Ítem:", ["Material", "Herramienta"])
        with col_i2:
            cant = st.number_input("Cantidad a Ingresar:", min_value=1, value=1)
            min_st = st.number_input("Stock Mínimo:", min_value=1, value=5)
            
        if st.button("Guardar en Inventario"):
            if cod and nom:
                bodega.agregar_o_sumar_material(cod, nom, tipo_item, cant, min_st)
                st.success("Guardado correctamente.")
                st.rerun()
            else:
                st.warning("Completa los campos obligatorios.")

    items = bodega.obtener_inventario()
    if items:
        df_i = pd.DataFrame(items, columns=["Código", "Nombre", "Tipo", "Cantidad", "Stock Mínimo"])
        st.dataframe(df_i, use_container_width=True)
    
