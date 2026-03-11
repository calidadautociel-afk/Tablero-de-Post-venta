import pandas as pd

# 1. Filtrar solo los tipos de orden válidos
tipos_validos = ['O.R. CLIENTE', 'O.R. GARANTIA', 'O.R. CHAPA']
df_filtrado = df[df['TIPO DE ORDEN'].isin(tipos_validos)]

# 2. Definir qué se considera una "respuesta" (Ajusta 'Respondida' al texto exacto de tu hoja)
valor_respuesta = 'Respondida' 

# 3. Calcular la tasa de respuesta por asesor
tasa_respuesta = df_filtrado.groupby('ASESOR').apply(
    lambda x: (x['Estado de la Encuesta'] == valor_respuesta).sum() / len(x)
).reset_index(name='Tasa de Respuesta')

# Formatear como porcentaje para visualizarlo mejor
tasa_respuesta['Tasa de Respuesta'] = (tasa_respuesta['Tasa de Respuesta'] * 100).round(2).astype(str) + '%'

# Mostrar en Streamlit (si estás usando esta librería)
# st.dataframe(tasa_respuesta)
