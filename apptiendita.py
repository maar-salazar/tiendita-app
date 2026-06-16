import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Control de Tiendita", layout="centered")
st.title("Control de ventas e inventario")

# Establecer la conexión con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    # Lectura de los datos directamente desde la nube
    inventario = conn.read(worksheet="Inventario", ttl=0)
    ventas = conn.read(worksheet="Ventas", ttl=0)
    
    # 1. Aislar exclusivamente las primeras 3 columnas (evita errores por columnas vacías extra)
    inventario = inventario.iloc[:, :3]
    
    # 2. Forzar los nombres exactos de las columnas
    inventario.columns = ["Producto", "Precio Venta", "Stock Inicial"]
    
    # 3. Rellenar celdas de stock vacías con 0
    inventario["Stock Inicial"] = inventario["Stock Inicial"].fillna(0)
    
    return inventario, ventas

def guardar_datos(inventario, ventas):
    # Actualización de datos hacia Google Sheets
    conn.update(worksheet="Inventario", data=inventario)
    conn.update(worksheet="Ventas", data=ventas)
    st.cache_data.clear()

df_inventario, df_ventas = cargar_datos()

def obtener_existencia_actual(inventario, ventas):
    df_inv = inventario.copy()
    existencias = []
    for _, row in df_inv.iterrows():
        total_vendido = ventas[ventas["Producto"] == row["Producto"]]["Cantidad"].sum()
        existencias.append(row["Stock Inicial"] - total_vendido)
    df_inv["Existencia Actual"] = existencias
    return df_inv

tab1, tab2 = st.tabs(["Registrar ventas", " Inventario y precios"])

with tab1:
    st.header("Registrar una venta")
    df_actualizado = obtener_existencia_actual(df_inventario, df_ventas)
    lista_productos = df_actualizado["Producto"].tolist()
    
    if lista_productos:
        producto_seleccionado = st.selectbox("Selecciona el producto:", lista_productos)
        datos_prod = df_actualizado[df_actualizado["Producto"] == producto_seleccionado].iloc[0]
        precio_u = datos_prod["Precio Venta"]
        stock_disp = datos_prod["Existencia Actual"]
        
        st.info(f"Precio: ${precio_u:.2f} | Disponibles: {stock_disp} piezas")
        cantidad = st.number_input("Cantidad:", min_value=1, max_value=int(stock_disp) if stock_disp > 0 else 1, value=1)
        total_venta = cantidad * precio_u
        st.write(f"### Total a cobrar: **${total_venta:.2f}**")
        
        if st.button("Confirmar Venta", disabled=(stock_disp <= 0)):
            nueva_venta = {
                "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Producto": producto_seleccionado,
                "Cantidad": cantidad,
                "Precio U.": precio_u,
                "Total": total_venta
            }
            df_ventas = pd.concat([df_ventas, pd.DataFrame([nueva_venta])], ignore_index=True)
            guardar_datos(df_inventario, df_ventas)
            st.success("¡Venta registrada en Google Sheets!")
            st.rerun()
    else:
        st.warning("No hay productos en el inventario.")

    st.subheader("Historial de Ventas")
    st.dataframe(df_ventas, use_container_width=True)

with tab2:
    st.header("Estado del Inventario")
    busqueda = st.text_input("🔍 Buscar producto:")
    df_mostrar = obtener_existencia_actual(df_inventario, df_ventas)
    
    if busqueda:
        df_mostrar = df_mostrar[df_mostrar["Producto"].str.contains(busqueda, case=False, na=False)]
        
    st.dataframe(df_mostrar, use_container_width=True)
    
    st.subheader("Agregar Nuevo Producto")
    with st.form("nuevo_producto"):
        nuevo_nombre = st.text_input("Nombre del Producto:")
        nuevo_precio = st.number_input("Precio de Venta ($):", min_value=0.0, format="%.2f")
        nuevo_stock = st.number_input("Stock Inicial (piezas):", min_value=0, step=1)
        
        if st.form_submit_button("Guardar Producto"):
            if nuevo_nombre.strip() == "":
                st.error("El nombre no puede estar vacío.")
            elif nuevo_nombre in df_inventario["Producto"].values:
                st.error("Este producto ya existe.")
            else:
                nuevo_prod = {"Producto": nuevo_nombre, "Precio Venta": nuevo_precio, "Stock Inicial": nuevo_stock}
                df_inventario = pd.concat([df_inventario, pd.DataFrame([nuevo_prod])], ignore_index=True)
                guardar_datos(df_inventario, df_ventas)
                st.success("¡Producto guardado en Google Sheets!")
                st.rerun()