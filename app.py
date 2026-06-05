import streamlit as str
import pandas as pd
import plotly.graph_objects as go

# Configuración de la página en modo ancho (Wide)
st.set_page_config(
    page_title="Indicadores y Seguimiento de Calidad Posventa - Autociel",
    page_icon="🔧",
    layout="wide"
)

# Estilos CSS personalizados para replicar la estética de la imagen
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: #1E293B; margin-bottom: 20px; }
    .metric-box { padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin: 5px; }
    .promotor { background-color: #D4EDDA; color: #155724; border: 1px solid #C3E6CB; }
    .neutro { background-color: #FFF3CD; color: #856404; border: 1px solid #FFEEBA; }
    .detractor { background-color: #F8D7DA; color: #721C24; border: 1px solid #F5C6CB; }
    .muestra-box { background-color: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 8px; padding: 20px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# URL pública de Google Sheets corregida para exportación directa en CSV
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kMzEHI4uuEWdIG7NfjgVkVVqOSw8ga9p_4-1i5ZN5wo/export?format=csv&gid=754740343"

# Mapeo de meses en español
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

@st.cache_data(ttl=600)  # Se actualiza cada 10 minutos
def load_data():
    df = pd.read_csv(SHEET_URL)
    # Limpieza de espacios en los nombres de las columnas
    df.columns = df.columns.str.strip()
    
    # Procesar la fecha dinámicamente
    if 'Fecha de la Encuesta' in df.columns:
        df['Fecha_Clean'] = pd.to_datetime(df['Fecha de la Encuesta'], errors='coerce')
        df['Año'] = df['Fecha_Clean'].dt.year.fillna(2026).astype(int)
        df['Mes_Num'] = df['Fecha_Clean'].dt.month.fillna(1).astype(int)
        df['Mes'] = df['Mes_Num'].map(MESES_ES)
    else:
        # Fallback en caso de que la columna no se llame idéntica
        df['Año'] = 2026
        df['Mes'] = "Mayo"
        
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Error al conectar con la base de datos de Google Sheets: {e}")
    st.stop()

# --- FUNCIONES DE CÁLCULO MÉTRICAS NPS ---
def calcular_metricas_nps(df, columna):
    if columna not in df.columns:
        return 0.0, 0, 0, 0
    
    # Convertir a numérico eliminando vacíos
    valores = pd.to_numeric(df[columna], errors='coerce').dropna()
    total = len(valores)
    
    if total == 0:
        return 0.0, 0, 0, 0
    
    promotores = len(valores[valores >= 9])
    detractores = len(valores[valores <= 6])
    neutros = len(valores[(valores >= 7) & (valores <= 8)])
    
    pct_promotores = (promotores / total) * 100
    pct_detractores = (detractores / total) * 100
    
    nps_score = pct_promotores - pct_detractores
    return round(nps_score, 1), promotores, neutros, detractors

# --- FUNCIÓN PARA GRAFICAR VELOCÍMETROS (GAUGE CHARTS) ---
def crear_velocimetro(score, titulo, mini=False):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={'suffix': "%", 'font': {'size': 24 if mini else 40}},
        gauge={
            'axis': {'range': [-100, 100], 'tickwidth': 1, 'tickcolor': "#475569"},
            'bar': {'color': "#0F172A"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#CBD5E1",
            'steps': [
                {'range': [-100, 0], 'color': '#FCA5A5'},  # Rojo claro
                {'range': [0, 50], 'color': '#FEF08A'},   # Amarillo claro
                {'range': [50, 100], 'color': '#86EFAC'}  # Verde claro
            ],
        }
    ))
    
    height_chart = 160 if mini else 280
    fig.update_layout(
        title={'text': titulo, 'y': 0.9, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top', 'font': {'size': 14 if mini else 18, 'bold': True}},
        margin=dict(l=20, r=20, t=50, b=20),
        height=height_chart,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# ==============================================================================
# PANEL LATERAL DE FILTROS GLOBALES
# ==============================================================================
st.sidebar.header("Filtros Globales")

# Filtro Año (Dinamizado)
years_available = sorted(df_raw['Año'].unique(), reverse=True)
selected_years = st.sidebar.multiselect("Año", options=years_available, default=years_available[:1])

# Filtro Mes (Dinamizado)
months_available = list(MESES_ES.values())
# Filtrar meses que realmente existen para el año seleccionado para evitar filtros vacíos
existing_months = df_raw[df_raw['Año'].isin(selected_years)]['Mes'].unique()
selected_months = st.sidebar.multiselect("Seleccione Mes(es)", options=months_available, default=[m for m in months_available if m in existing_months][:1])

# Filtro Marca
if 'Marca' in df_raw.columns:
    marcas_available = sorted(df_raw['Marca'].dropna().unique())
    selected_marcas = st.sidebar.multiselect("MARCA", options=marcas_available, default=marcas_available[:1] if marcas_available else [])
else:
    selected_marcas = []

# Aplicar Filtros a la Base de Datos
df_filtrado = df_raw[df_raw['Año'].isin(selected_years) & df_raw['Mes'].isin(selected_months)]
if selected_marcas:
    df_filtrado = df_filtrado[df_filtrado['Marca'].isin(selected_marcas)]

# ==============================================================================
# PESTAÑAS PRINCIPALES DEL TABLERO
# ==============================================================================
tab_monitor, tab_tabla, tab_ficha, tab_quejas = st.tabs([
    "🏠 Monitor Global Comparativo", 
    "👥 Tabla Unificada de Asesores", 
    "👤 Ficha Individual por Asesor", 
    "⚠️ Gestión de Quejas"
])

# ------------------------------------------------------------------------------
# 1. MONITOR GLOBAL COMPARATIVO
# ------------------------------------------------------------------------------
with tab_monitor:
    st.markdown(f"<div class='main-title'>Resultados en Paralelo: {', '.join(selected_months)}</div>", unsafe_allow_html=True)
    
    # Bloque Superior: Indicadores Principales
    col_q1, col_q2, col_muestra = st.columns([4, 4, 2])
    
    with col_q1:
        score_q1, p_q1, n_q1, d_q1 = calcular_metricas_nps(df_filtrado, "Q1 - Satisfacción general")
        st.plotly_chart(crear_velocimetro(score_q1, "Q1 - SATISFACCIÓN GENERAL (NPS)"), use_container_width=True)
        
        # Desglose de bloques Promotor/Neutro/Detractor
        sub_c1, sub_c2, sub_c3 = st.columns(3)
        sub_c1.markdown(f"<div class='metric-box promotor'>🟢 {p_q1}<br><span style='font-size:12px;'>Prom</span></div>", unsafe_allow_html=True)
        sub_c2.markdown(f"<div class='metric-box neutro'>🟡 {n_q1}<br><span style='font-size:12px;'>Neu</span></div>", unsafe_allow_html=True)
        sub_c3.markdown(f"<div class='metric-box detractor'>🔴 {d_q1}<br><span style='font-size:12px;'>Det</span></div>", unsafe_allow_html=True)

    with col_q2:
        score_q2, p_q2, n_q2, d_q2 = calcular_metricas_nps(df_filtrado, "Q2 - Recomendación - taller")
        st.plotly_chart(crear_velocimetro(score_q2, "Q2 - RECOMENDACIÓN (NPS)"), use_container_width=True)
        
        sub_c4, sub_c5, sub_c6 = st.columns(3)
        sub_c4.markdown(f"<div class='metric-box promotor'>🟢 {p_q2}<br><span style='font-size:12px;'>Prom</span></div>", unsafe_allow_html=True)
        sub_c5.markdown(f"<div class='metric-box neutro'>🟡 {n_q2}<br><span style='font-size:12px;'>Neu</span></div>", unsafe_allow_html=True)
        sub_c6.markdown(f"<div class='metric-box detractor'>🔴 {d_q2}<br><span style='font-size:12px;'>Det</span></div>", unsafe_allow_html=True)
        
    with col_muestra:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""
            <div class='muestra-box'>
                <span style='font-size: 16px; color: #64748B; font-weight: bold;'>Muestra</span><br>
                <span style='font-size: 48px; color: #0F172A; font-weight: bold;'>{len(df_filtrado)}</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # Bloque Inferior: Sub-pestañas de Procesos
    st.markdown("### Segmentación Operativa de Posventa")
    subtab_agendamiento, subtab_asesor, subtab_taller, subtab_entrega, subtab_comentarios = st.tabs([
        "📅 Agendamiento e Instalaciones", 
        "👔 Atención del Asesor", 
        "⚙️ Calidad y Taller", 
        "🚗 Entrega y Seguimiento",
        "💬 Comentarios Verbalizaciones"
    ])
    
    with subtab_agendamiento:
        c1, c2 = st.columns(2)
        with c1:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q5 - Facilidad de agendamiento")
            st.plotly_chart(crear_velocimetro(score, "Q5 - Facilidad de Agendamiento", mini=True), use_container_width=True)
        with c2:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q6 - Satisfacción instalaciones")
            st.plotly_chart(crear_velocimetro(score, "Q6 - Satisfacción Instalaciones", mini=True), use_container_width=True)
            
    with subtab_asesor:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q7 - Cortesía y Amabilidad")
            st.plotly_chart(crear_velocimetro(score, "Q7 - Cortesía y Amabilidad", mini=True), use_container_width=True)
        with c2:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q8 - Competencia Asesor de Servicio")
            st.plotly_chart(crear_velocimetro(score, "Q8 - Competencia Asesor", mini=True), use_container_width=True)
        with c3:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q9 - Oferta movilidad")
            st.plotly_chart(crear_velocimetro(score, "Q9 - Oferta Movilidad", mini=True), use_container_width=True)
        with c4:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q10 - Explicación presupuesto")
            st.plotly_chart(crear_velocimetro(score, "Q10 - Explicación Presupuesto", mini=True), use_container_width=True)

    with subtab_taller:
        c1, c2, c3 = st.columns(3)
        with c1:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q11 - Explicación trabajo - costo")
            st.plotly_chart(crear_velocimetro(score, "Q11 - Explicación Trabajo/Costo", mini=True), use_container_width=True)
        with c2:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q12 - Calidad del trabajo")
            st.plotly_chart(crear_velocimetro(score, "Q12 - Calidad del Trabajo", mini=True), use_container_width=True)
        with c3:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q13 - Trabajo realizado en primera visita")
            st.plotly_chart(crear_velocimetro(score, "Q13 - Reparado Primera Visita (FIR)", mini=True), use_container_width=True)

    with subtab_entrega:
        c1, c2, c3 = st.columns(3)
        with c1:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q15 - Entrega según momento acordado")
            st.plotly_chart(crear_velocimetro(score, "Q15 - Entrega a Tiempo", mini=True), use_container_width=True)
        with c2:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q16 - Información del retraso")
            st.plotly_chart(crear_velocimetro(score, "Q16 - Información de Retraso", mini=True), use_container_width=True)
        with c3:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q19 - Satisfacción con el Contacto")
            st.plotly_chart(crear_velocimetro(score, "Q19 - Satisfacción con Contacto", mini=True), use_container_width=True)

    with subtab_comentarios:
        st.markdown("#### Comentarios Literales de los Clientes (Q3 - Verbalización)")
        if "Q3 - Verbalización" in df_filtrado.columns:
            comentarios = df_filtrado[["Fecha de la Encuesta", "Marca", "Q3 - Verbalización"]].dropna()
            st.dataframe(comentarios, use_container_width=True, hide_index=True)
        else:
            st.info("No se encontró la columna 'Q3 - Verbalización' en este corte de datos.")

# ------------------------------------------------------------------------------
# 2. TABLA UNIFICADA DE ASESORES
# ------------------------------------------------------------------------------
with tab_tabla:
    st.markdown("### Ranking de Desempeño General de Asesores")
    
    col_asesor_key = next((col for col in df_filtrado.columns if 'Asesor' in col), None)
    
    if col_asesor_key:
        asesores = df_filtrado[col_asesor_key].dropna().unique()
        ranking_data = []
        
        for p_asesor in asesores:
            df_ase = df_filtrado[df_filtrado[col_asesor_key] == p_asesor]
            muestra_ase = len(df_ase)
            nps_q2, _, _, _ = calcular_metricas_nps(df_ase, "Q2 - Recomendación - taller")
            nps_q1, _, _, _ = calcular_metricas_nps(df_ase, "Q1 - Satisfacción general")
            
            ranking_data.append({
                "Asesor de Servicio": p_asesor,
                "Muestra": muestra_ase,
                "NPS Q2 (Recomendación)": nps_q2,
                "NPS Q1 (Satisfacción)": nps_q1
            })
            
        df_ranking = pd.DataFrame(ranking_data).sort_values(by="NPS Q2 (Recomendación)", ascending=False)
        st.dataframe(df_ranking, use_container_width=True, hide_index=True)
    else:
        st.warning("Para activar esta pestaña, asegúrate de tener una columna que contenga la palabra 'Asesor' en tu hoja 'Enc. de Marca'.")

# ------------------------------------------------------------------------------
# 3. FICHA INDIVIDUAL POR ASESOR
# ------------------------------------------------------------------------------
with tab_ficha:
    st.markdown("### Perfil de Calidad Individual")
    if col_asesor_key:
        lista_asesores = sorted(df_filtrado[col_asesor_key].dropna().unique())
        asesor_seleccionado = st.selectbox("Seleccione el Asesor de Servicio:", options=lista_asesores)
        
        df_individual = df_filtrado[df_filtrado[col_asesor_key] == asesor_seleccionado]
        
        c_ind1, c_ind2, c_ind3 = st.columns([4, 4, 2])
        with c_ind1:
            score_ind_q1, _, _, _ = calcular_metricas_nps(df_individual, "Q1 - Satisfacción general")
            st.plotly_chart(crear_velocimetro(score_ind_q1, "Q1 - Satisfacción"), use_container_width=True)
        with c_ind2:
            score_ind_q2, _, _, _ = calcular_metricas_nps(df_individual, "Q2 - Recomendación - taller")
            st.plotly_chart(crear_velocimetro(score_ind_q2, "Q2 - Recomendación (Métrica Principal)"), use_container_width=True)
        with c_ind3:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown(f"""
                <div class='muestra-box'>
                    <span style='font-size: 14px; color: #64748B; font-weight: bold;'>Encuestas</span><br>
                    <span style='font-size: 36px; color: #0F172A; font-weight: bold;'>{len(df_individual)}</span>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Filtro por asesor no disponible (Revisa los nombres de las columnas).")

# ------------------------------------------------------------------------------
# 4. GESTIÓN DE QUEJAS
# ------------------------------------------------------------------------------
with tab_quejas:
    st.markdown("### Alertas de Clientes Detractores")
    st.markdown("Casos críticos detectados donde la puntuación en Satisfacción (Q1) o Recomendación (Q2) es igual o menor a 6.")
    
    # Identificar detractores en Q1 o Q2
    if "Q1 - Satisfacción general" in df_filtrado.columns and "Q2 - Recomendación - taller" in df_filtrado.columns:
        q1_num = pd.to_numeric(df_filtrado["Q1 - Satisfacción general"], errors='coerce')
        q2_num = pd.to_numeric(df_filtrado["Q2 - Recomendación - taller"], errors='coerce')
        
        df_detractores = df_filtrado[(q1_num <= 6) | (q2_num <= 6)]
        
        if len(df_detractores) > 0:
            columnas_queja = ["Fecha de la Encuesta", "Marca", "Q1 - Satisfacción general", "Q2 - Recomendación - taller"]
            if col_asesor_key:
                columnas_queja.append(col_asesor_key)
            if "Q3 - Verbalización" in df_filtrado.columns:
                columnas_queja.append("Q3 - Verbalización")
                
            st.dataframe(df_detractores[columnas_queja], use_container_width=True, hide_index=True)
        else:
            st.success("🎉 ¡Excelente! No se registraron clientes detractores para los filtros seleccionados.")
    else:
        st.info("Columnas de análisis de quejas no encontradas.")
