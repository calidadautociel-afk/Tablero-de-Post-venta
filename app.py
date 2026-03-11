import streamlit as st
import pandas as pd
# Importar otras librerías si te conectas a Google Sheets (gspread, etc.)

# 1. Configuración de la página
st.title("Tasa de Respuesta de Asesores de Servicio")

# 2. CARGAR LOS DATOS (¡Aquí es donde defines 'df'!)
# --- SI USAS UN ARCHIVO EXCEL LOCAL / SUBIDO A GITHUB ---
# df = pd.read_excel('nombre_de_tu_archivo.xlsx', sheet_name='TRABAJO DE CAMPO ROAR')

# --- SI USAS CSV ---
# df = pd.read_csv('nombre_de_tu_archivo.csv')

# --- (Si estás conectándote a Google Sheets, aquí iría el código de conexión 
# que usa tus credenciales para descargar la pestaña y convertirla en 'df') ---

# IMPORTANTE: Asegúrate de que para este punto, 'df' ya contenga tus datos.

# 3. PROCESAR LOS DATOS (El código que te pasé)
try:
    # Filtrar solo los tipos de orden válidos
    tipos_validos = ['O.R. CLIENTE', 'O.R. GARANTIA', 'O.R. CHAPA']
    df_filtrado = df[df['TIPO DE ORDEN'].isin(tipos_validos)]

    # Definir qué se considera una "respuesta"
    valor_respuesta = 'Respondida' 

    # Calcular la tasa de respuesta por asesor
    tasa_respuesta = df_filtrado.groupby('ASESOR').apply(
        lambda x: (x['Estado de la Encuesta'] == valor_respuesta).sum() / len(x)
    ).reset_index(name='Tasa de Respuesta')

    # Formatear como porcentaje
    tasa_respuesta['Tasa de Respuesta'] = (tasa_respuesta['Tasa de Respuesta'] * 100).round(2).astype(str) + '%'

    # 4. MOSTRAR LOS RESULTADOS
    st.subheader("Resultados por Asesor")
    st.dataframe(tasa_respuesta)

except NameError:
    st.error("Error: Aún no has cargado los datos en la variable 'df'. Revisa el Paso 2.")
except KeyError as e:
    st.error(f"Error: No se encontró la columna {e} en tu tabla. Verifica que los nombres de las columnas estén escritos exactamente igual que en tu hoja.")
