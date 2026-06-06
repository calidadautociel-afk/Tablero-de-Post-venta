import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math

# Configuración de la página en modo ancho (Wide)
st.set_page_config(
    page_title="Indicadores y Seguimiento de Calidad Posventa - Autociel",
    page_icon="🔧",
    layout="wide"
)

# Estilos CSS personalizados
st.markdown("""
    <style>
    .main-title { font-size: 26px; font-weight: bold; color: #1E293B; margin-bottom: 5px; margin-top: -20px; }
    .sub-title { font-size: 20px; font-weight: bold; color: #334155; margin-bottom: 15px; }
    .muestra-box { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 15px; text-align: center; }
    
    div.stButton > button {
        width: 100%;
        border-radius: 5px;
        font-weight: bold;
        padding: 5px 0px;
        border: 1px solid transparent;
        transition: all 0.3s;
    }
    
    div.stButton > button:hover {
        opacity: 0.8;
        border-color: #1E293B;
    }
    </style>
""", unsafe_allow_html=True)

# URL pública de Google Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kMzEHI4uuEWdIG7NfjgVkVVqOSw8ga9p_4-1i5ZN5wo/export?format=csv&gid=754740343"

# Mapeo de meses en español
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# --- INICIALIZACIÓN DE SESSION STATE ---
if 'filtro_comentarios' not in st.session_state:
    st.session_state.filtro_comentarios = 'Todos'

def set_filtro(tipo):
    st.session_state.filtro_comentarios = tipo

@st.cache_data(ttl=60)
def load_data():
    df = pd.read_csv(SHEET_URL)
    df.columns = df.columns.str.strip()
    
    if 'Fecha de la Encuesta' in df.columns:
        df['Fecha_Clean'] = pd.to_datetime(df['Fecha de la Encuesta'], dayfirst=True, errors='coerce')
        df['Año'] = df['Fecha_Clean'].dt.year.fillna(2026).astype(int)
        df['Mes_Num'] = df['Fecha_Clean'].dt.month.fillna(5).astype(int)
        df['Mes'] = df['Mes_Num'].map(MESES_ES)
    else:
        df['Año'] = 2026
        df['Mes'] = "Mayo"
        
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")
    st.stop()

# --- BÚSQUEDA DINÁMICA DE COLUMNA Q4 ---
col_q4 = next((col for col in df_raw.columns if 'Q4' in col and 'Motivo' in col), None)

# --- CÁLCULO MÉTRICAS NPS ---
def calcular_metricas_nps(df, columna):
    if columna not in df.columns:
        return 0.0, 0, 0, 0
    
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
    nps_score = max(0.0, round(nps_score, 1))
    
    return nps_score, promotores, neutros, detractores

# --- VELOCÍMETROS ---
def crear_velocimetro(score, titulo, mini=False):
    if score >= 90:
        color_bar = '#22C55E'
    elif score >= 70:
        color_bar = '#EAB308'
    else:
        color_bar = '#EF4444'

    font_size = 20 if mini else 42

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={'suffix': "%", 'font': {'size': font_size, 'color': '#1E293B'}},
        gauge={
            'axis': {'range': [0, 100], 'showticklabels': False},
            'bar': {'color': color_bar, 'thickness': 0.15},
            'bgcolor': "#F1F5F9",
            'borderwidth': 0,
        }
    ))
    
    height_chart = 130 if mini else 240
    margin_bottom = 0 if mini else 10
    
    fig.update_layout(
        title={'text': f"<b>{titulo}</b>", 'y': 0.85, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top', 'font': {'size': 12 if mini else 14, 'color': '#475569'}},
        margin=dict(l=20, r=20, t=40, b=margin_bottom),
        height=height_chart,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# --- GRÁFICOS DE TORTA (ANILLOS) ---
def crear_torta(df, columna, titulo):
    if columna not in df.columns:
        fig = go.Figure()
        fig.update_layout(title={'text': f"<b>{titulo}</b>", 'x': 0.5, 'y': 0.85, 'xanchor': 'center', 'yanchor': 'top', 'font': {'size': 12, 'color': '#475569'}}, height=160, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        return fig
        
    datos = df[columna].value_counts()
    fig = go.Figure(data=[go.Pie(
        labels=datos.index, 
        values=datos.values, 
        hole=.5, 
        textinfo='label+percent', 
        textposition='inside', 
        insidetextorientation='radial'
    )])
    
    fig.update_layout(
        title={'text': f"<b>{titulo}</b>", 'x': 0.5, 'y': 0.95, 'xanchor': 'center', 'yanchor': 'top', 'font': {'size': 12, 'color': '#475569'}}, 
        margin=dict(l=10, r=10, t=40, b=10), 
        height=160, 
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# ==============================================================================
# PANEL LATERAL DE FILTROS GLOBALES
# ==============================================================================
st.sidebar.header("Filtros Globales")

years_available = sorted(df_raw['Año'].unique(), reverse=True)
selected_years = st.sidebar.multiselect("Año", options=years_available, default=years_available[:1])

months_available = list(MESES_ES.values())
existing_months = df_raw[df_raw['Año'].isin(selected_years)]['Mes'].unique()
selected_months = st.sidebar.multiselect("Seleccione Mes(es)", options=months_available, default=[m for m in months_available if m in existing_months][:1])

if 'Marca' in df_raw.columns:
    marcas_available = sorted(df_raw['Marca'].dropna().unique())
    selected_marcas = st.sidebar.multiselect("MARCA", options=marcas_available, default=marcas_available[:1] if marcas_available else [])
else:
    selected_marcas = []

# APLICAR FILTROS (Q4 Removido del panel lateral)
df_filtrado = df_raw[df_raw['Año'].isin(selected_years) & df_raw['Mes'].isin(selected_months)]
if selected_marcas:
    df_filtrado = df_filtrado[df_filtrado['Marca'].isin(selected_marcas)]

# ==============================================================================
# TÍTULO PRINCIPAL
# ==============================================================================
st.markdown("<h1 style='font-size: 36px; color: #1E293B; display: flex; align-items: center;'><span style='font-size: 40px; margin-right: 15px;'>📊</span> INDICADORES Y SEGUIMIENTO DE CALIDAD POSTVENTA AUTOCIEL</h1>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# PESTAÑAS PRINCIPALES
# ==============================================================================
tab_monitor, tab_tabla, tab_ficha, tab_carga, tab_quejas = st.tabs([
    "🏠 Monitor Global Comparativo", 
    "👥 Tabla Unificada de Asesores", 
    "👤 Ficha Individual por Asesor", 
    "📊 Análisis de Carga Operativa",
    "⚠️ Gestión de Quejas"
])

# ------------------------------------------------------------------------------
# 1. MONITOR GLOBAL COMPARATIVO
# ------------------------------------------------------------------------------
with tab_monitor:
    st.markdown(f"<div class='sub-title'>Resultados en Paralelo: {', '.join(selected_months)}</div>", unsafe_allow_html=True)
    st.markdown("🏢 **Datos de Origen: Encuestas de Marca**")
    
    with st.container():
        col_q1, col_q2, col_muestra = st.columns([4, 4, 2])
        
        with col_q1:
            score_q1, p_q1, n_q1, d_q1 = calcular_metricas_nps(df_filtrado, "Q1 - Satisfacción general")
            st.plotly_chart(crear_velocimetro(score_q1, "Q1 - SATISFACCIÓN (NPS)"), use_container_width=True)
            
            sub_c1, sub_c2, sub_c3 = st.columns(3)
            with sub_c1:
                st.button(f"😄 {p_q1} Prom", key="btn_prom_q1", on_click=set_filtro, args=('Promotor',), use_container_width=True)
            with sub_c2:
                st.button(f"😐 {n_q1} Neu", key="btn_neu_q1", on_click=set_filtro, args=('Neutro',), use_container_width=True)
            with sub_c3:
                st.button(f"😠 {d_q1} Det", key="btn_det_q1", on_click=set_filtro, args=('Detractor',), use_container_width=True)

        with col_q2:
            score_q2, p_q2, n_q2, d_q2 = calcular_metricas_nps(df_filtrado, "Q2 - Recomendación - taller")
            st.plotly_chart(crear_velocimetro(score_q2, "Q2 - RECOMENDACIÓN (NPS)"), use_container_width=True)
            
            sub_c4, sub_c5, sub_c6 = st.columns(3)
            with sub_c4:
                st.button(f"😄 {p_q2} Prom", key="btn_prom_q2", on_click=set_filtro, args=('Promotor',), use_container_width=True)
            with sub_c5:
                st.button(f"😐 {n_q2} Neu", key="btn_neu_q2", on_click=set_filtro, args=('Neutro',), use_container_width=True)
            with sub_c6:
                st.button(f"😠 {d_q2} Det", key="btn_det_q2", on_click=set_filtro, args=('Detractor',), use_container_width=True)
            
        with col_muestra:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown(f"""
                <div class='muestra-box'>
                    <span style='font-size: 14px; color: #64748B; font-weight: bold;'>Muestra</span><br>
                    <span style='font-size: 42px; color: #0F172A; font-weight: bold;'>{len(df_filtrado)}</span>
                </div>
            """, unsafe_allow_html=True)

    # CSS botones P/N/D
    st.markdown("""
        <style>
        button[kind="secondary"] { background-color: transparent; }
        div[data-testid="stVerticalBlock"] div:nth-child(1) > div > button { background-color: #D4EDDA; color: #155724; border-color: #C3E6CB;}
        div[data-testid="stVerticalBlock"] div:nth-child(2) > div > button { background-color: #FFF3CD; color: #856404; border-color: #FFEEBA;}
        div[data-testid="stVerticalBlock"] div:nth-child(3) > div > button { background-color: #F8D7DA; color: #721C24; border-color: #F5C6CB;}
        </style>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<p style='font-size: 14px; color: #475569;'><b>Segmentación actual Marca:</b> Todos</p>", unsafe_allow_html=True)
    
    # --- PESTAÑAS OPERATIVAS AJUSTADAS ---
    subtab_agendamiento, subtab_asesor, subtab_taller, subtab_contacto = st.tabs([
        "📅 Agendamiento e Instalaciones", 
        "👔 Atención del Asesor", 
        "⚙️ Calidad y Taller", 
        "📞 Contacto Posterior"
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
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q7 - Cortesía y Amabilidad")
            st.plotly_chart(crear_velocimetro(score, "Q7 - Cortesía y Amabilidad", mini=True), use_container_width=True)
        with c2:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q8 - Competencia Asesor de Servicio")
            st.plotly_chart(crear_velocimetro(score, "Q8 - Competencia Asesor", mini=True), use_container_width=True)
        with c3:
            st.plotly_chart(crear_torta(df_filtrado, "Q9 - Oferta movilidad", "Q9 - Oferta Movilidad"), use_container_width=True)
        with c4:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q10 - Explicación presupuesto")
            st.plotly_chart(crear_velocimetro(score, "Q10 - Explicación Presupuesto", mini=True), use_container_width=True)
        with c5:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q11 - Explicación trabajo - costo")
            st.plotly_chart(crear_velocimetro(score, "Q11 - Explicación Trabajo/Costo", mini=True), use_container_width=True)

    with subtab_taller:
        c1, c2, c3 = st.columns(3)
        with c1:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q12 - Calidad del trabajo")
            st.plotly_chart(crear_velocimetro(score, "Q12 - Calidad del Trabajo", mini=True), use_container_width=True)
        with c2:
            st.plotly_chart(crear_torta(df_filtrado, "Q13 - Trabajo realizado en primera visita", "Q13 - Reparado 1ra Visita (FIR)"), use_container_width=True)
        with c3:
            st.plotly_chart(crear_torta(df_filtrado, "Q14 - Motivo del trabajo no realizado", "Q14 - Motivo Trabajo No Realizado"), use_container_width=True)
            
        c4, c5 = st.columns(2)
        with c4:
            st.plotly_chart(crear_torta(df_filtrado, "Q15 - Entrega según momento acordado", "Q15 - Entrega a Tiempo"), use_container_width=True)
        with c5:
            st.plotly_chart(crear_torta(df_filtrado, "Q16 - Información del retraso", "Q16 - Información de Retraso"), use_container_width=True)

    with subtab_contacto:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(crear_torta(df_filtrado, "Q18 - Contactado", "Q18 - Contactado"), use_container_width=True)
        with c2:
            score, _, _, _ = calcular_metricas_nps(df_filtrado, "Q19 - Satisfacción con el Contacto")
            st.plotly_chart(crear_velocimetro(score, "Q19 - Satisfacción con Contacto", mini=True), use_container_width=True)

    # --- TABLA GLOBAL DE COMENTARIOS INYECTADA ---
    st.markdown("---")
    col_tit, col_btn = st.columns([8, 2])
    with col_tit:
        st.markdown(f"#### 💬 Comentarios de Clientes: Segmento **{st.session_state.filtro_comentarios}**")
    with col_btn:
        if st.session_state.filtro_comentarios != 'Todos':
            st.button("🔄 Ver Todos", on_click=set_filtro, args=('Todos',), use_container_width=True)
    
    if "Q3 - Verbalización" in df_filtrado.columns:
        df_comentarios = df_filtrado.copy()
        
        if st.session_state.filtro_comentarios != 'Todos':
            q_base = pd.to_numeric(df_comentarios["Q1 - Satisfacción general"], errors='coerce')
            if st.session_state.filtro_comentarios == 'Promotor':
                df_comentarios = df_comentarios[q_base >= 9]
            elif st.session_state.filtro_comentarios == 'Neutro':
                df_comentarios = df_comentarios[(q_base >= 7) & (q_base <= 8)]
            elif st.session_state.filtro_comentarios == 'Detractor':
                df_comentarios = df_comentarios[q_base <= 6]
                
        comentarios_mostrar = df_comentarios[["Fecha de la Encuesta", "Marca", "Q3 - Verbalización"]].dropna(subset=["Q3 - Verbalización"])
        
        if len(comentarios_mostrar) > 0:
            st.dataframe(comentarios_mostrar, use_container_width=True, hide_index=True)
        else:
            st.info(f"No hay comentarios registrados para el segmento '{st.session_state.filtro_comentarios}' en el período seleccionado.")
    else:
        st.info("No se encontró la columna 'Q3 - Verbalización' en la base de datos.")

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
            
            # Cálculos de NPS
            nps_q2, p_q2, n_q2, d_q2 = calcular_metricas_nps(df_ase, "Q2 - Recomendación - taller")
            nps_q7, _, _, _ = calcular_metricas_nps(df_ase, "Q7 - Cortesía y Amabilidad")
            nps_q8, _, _, _ = calcular_metricas_nps(df_ase, "Q8 - Competencia Asesor de Servicio")
            nps_q10, _, _, _ = calcular_metricas_nps(df_ase, "Q10 - Explicación presupuesto")
            nps_q11, _, _, _ = calcular_metricas_nps(df_ase, "Q11 - Explicación trabajo - costo")
            
            # Cálculo de la meta de promotores faltantes
            t_validos = p_q2 + n_q2 + d_q2
            if nps_q2 >= 94.0:
                meta_str = "✅ Alcanzado"
            elif t_validos > 0:
                faltantes = math.ceil((94 * t_validos - 100 * (p_q2 - d_q2)) / 6.0)
                faltantes = max(0, faltantes)
                meta_str = f"Faltan {faltantes} Promotor{'es' if faltantes != 1 else ''}"
            else:
                meta_str = "Sin datos"
            
            ranking_data.append({
                "Asesor de Servicio": p_asesor,
                "NPS Q2 (Recomendación)": nps_q2,
                "Muestra": muestra_ase,
                "NPS Q7 (Cortesía)": nps_q7,
                "NPS Q8 (Competencia)": nps_q8,
                "NPS Q10 (Presupuesto)": nps_q10,
                "NPS Q11 (Trabajo/Costo)": nps_q11,
                "Meta 94%": meta_str
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
# 4. ANÁLISIS DE CARGA OPERATIVA (NUEVA PESTAÑA)
# ------------------------------------------------------------------------------
with tab_carga:
    if col_q4:
        st.markdown(f"### 📊 Análisis de Carga Operativa: {col_q4}")
        st.markdown("<p style='font-size: 14px; color: #64748B; margin-top:-10px;'>Cruza el volumen de cada servicio con su puntaje de Recomendación (Q2). Los colores indican: <span style='color:#22C55E; font-weight:bold;'>Verde (Excelente)</span>, <span style='color:#EAB308; font-weight:bold;'>Amarillo (Alerta)</span>, <span style='color:#EF4444; font-weight:bold;'>Rojo (Crítico)</span>.</p>", unsafe_allow_html=True)
        
        motivos_data = []
        for motivo in df_filtrado[col_q4].dropna().unique():
            df_motivo = df_filtrado[df_filtrado[col_q4] == motivo]
            nps_q2, _, _, _ = calcular_metricas_nps(df_motivo, "Q2 - Recomendación - taller")
            motivos_data.append({
                "Motivo": motivo,
                "Volumen": len(df_motivo),
                "NPS_Q2": nps_q2
            })
            
        if motivos_data:
            df_m = pd.DataFrame(motivos_data).sort_values(by="Volumen", ascending=True)
            
            # Gráfico de barras interactivo de Plotly
            fig_q4 = go.Figure()
            fig_q4.add_trace(go.Bar(
                y=df_m["Motivo"],
                x=df_m["Volumen"],
                orientation='h',
                marker=dict(
                    color=df_m["NPS_Q2"],
                    colorscale=[[0, '#EF4444'], [0.7, '#EAB308'], [1, '#22C55E']], # Escala de Rojo a Verde
                    cmin=0, cmax=100,
                    colorbar=dict(title="NPS Q2")
                ),
                text=df_m["Volumen"],
                textposition='auto',
                hovertemplate="<b>Motivo:</b> %{y}<br><b>Autos:</b> %{x}<br><b>NPS Recomendación:</b> %{marker.color:.1f}%<extra></extra>"
            ))
            
            fig_q4.update_layout(
                height=350 if len(df_m) > 3 else 250,
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=True, gridcolor='#E2E8F0', title="Volumen de Vehículos"),
                yaxis=dict(showgrid=False)
            )
            st.plotly_chart(fig_q4, use_container_width=True)
    else:
        st.info("Columna de motivos de visita (Q4) no encontrada.")

# ------------------------------------------------------------------------------
# 5. GESTIÓN DE QUEJAS
# ------------------------------------------------------------------------------
with tab_quejas:
    st.markdown("### Alertas de Clientes Detractores")
    st.markdown("Casos críticos detectados donde la puntuación en Satisfacción (Q1) o Recomendación (Q2) es igual o menor a 6.")
    
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
