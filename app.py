import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import datetime

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
    .kpi-card { background-color: #ffffff; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .kpi-value { font-size: 32px; font-weight: bold; color: #0F172A; line-height: 1; }
    .kpi-label { font-size: 14px; color: #64748B; margin-top: 5px; font-weight: 500; }
    .kpi-sub { font-size: 13px; color: #22C55E; font-weight: bold; margin-top: 10px; }
    
    div.stButton > button { width: 100%; border-radius: 5px; font-weight: bold; padding: 5px 0px; border: 1px solid transparent; transition: all 0.3s; }
    div.stButton > button:hover { opacity: 0.8; border-color: #1E293B; }
    .vertical-divider { border-left: 2px solid #E2E8F0; height: 100%; margin-left: 10px; margin-right: 10px; }
    
    /* ================================================================= */
    /* CSS DEFINITIVO PARA ROMPER EL SCROLL DE STREAMLIT AL IMPRIMIR     */
    /* ================================================================= */
    @media print {
        /* Forzar impresion de colores reales de Plotly en Chrome */
        * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }

        /* Ocultar barra lateral y encabezados grises */
        .no-print, [data-testid="stSidebar"], [data-testid="stHeader"], header, footer { 
            display: none !important; 
        }
        
        /* Destruir TODAS las cajas restrictivas de Streamlit */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], .main, .block-container {
            display: block !important;
            height: auto !important;
            min-height: 100% !important;
            max-height: none !important;
            overflow: visible !important;
            position: static !important;
        }
        
        /* Expandir a lo ancho de la hoja */
        .block-container {
            max-width: 100% !important;
            width: 100% !important;
            padding: 0 !important;
        }

        /* Evitar que los graficos se corten por la mitad al cambiar de hoja */
        div[data-testid="stVerticalBlock"] > div, .js-plotly-plot, .stDataFrame {
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }
    }
    </style>
""", unsafe_allow_html=True)
# URLs públicas de Google Sheets
SHEET_URL_MARCA = "https://docs.google.com/spreadsheets/d/1kMzEHI4uuEWdIG7NfjgVkVVqOSw8ga9p_4-1i5ZN5wo/export?format=csv&gid=754740343"
SHEET_URL_INTERNA = "https://docs.google.com/spreadsheets/d/1kMzEHI4uuEWdIG7NfjgVkVVqOSw8ga9p_4-1i5ZN5wo/export?format=csv&gid=1128023355"
SHEET_URL_EMAIL_LLAVE = "https://docs.google.com/spreadsheets/d/1kMzEHI4uuEWdIG7NfjgVkVVqOSw8ga9p_4-1i5ZN5wo/export?format=csv&gid=1942714178"

# Mapeo de meses en español
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# Mapeo de meses en formato corto
MESES_SHORT = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
    7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"
}

# --- INICIALIZACIÓN DE SESSION STATE (DOBLE) ---
if 'filtro_comentarios_marca' not in st.session_state:
    st.session_state.filtro_comentarios_marca = 'Todos'
if 'filtro_comentarios_int' not in st.session_state:
    st.session_state.filtro_comentarios_int = 'Todos'

def set_filtro_marca(tipo):
    st.session_state.filtro_comentarios_marca = tipo

def set_filtro_int(tipo):
    st.session_state.filtro_comentarios_int = tipo

@st.cache_data(ttl=60)
def load_data(url):
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    
    col_fecha = 'Fecha de la Encuesta' if 'Fecha de la Encuesta' in df.columns else 'Marca temporal'
    
    if col_fecha in df.columns:
        df['Fecha_Clean'] = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
        df['Año'] = df['Fecha_Clean'].dt.year.fillna(2026).astype(int)
        df['Mes_Num'] = df['Fecha_Clean'].dt.month.fillna(5).astype(int)
        df['Mes'] = df['Mes_Num'].map(MESES_ES)
    else:
        df['Año'] = 2026
        df['Mes'] = "Mayo"
        df['Mes_Num'] = 5
        
    return df

@st.cache_data(ttl=60)
def load_email_sheet(url):
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    return df

try:
    df_marca_raw = load_data(SHEET_URL_MARCA)
    df_int_raw = load_data(SHEET_URL_INTERNA)
    df_email_llave_raw = load_email_sheet(SHEET_URL_EMAIL_LLAVE)
except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")
    st.stop()

# --- BÚSQUEDA DINÁMICA DE COLUMNAS Q4 Y Q13 (Base Marca) ---
col_q4 = next((col for col in df_marca_raw.columns if 'Q4' in col and 'Motivo' in col), None)
col_q13 = next((col for col in df_marca_raw.columns if 'Q13' in col), "Q13 - Trabajo realizado en primera visita")

# --- CÁLCULOS MÉTRICAS ---
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

def calcular_promedio(df, columna):
    if columna not in df.columns:
        return 0.0
    
    if df[columna].dtype == object:
        s_limpia = df[columna].astype(str).str.replace(',', '.')
    else:
        s_limpia = df[columna]
        
    valores = pd.to_numeric(s_limpia, errors='coerce').dropna()
    valores = valores[(valores > 0) & (valores <= 10)]
    
    if len(valores) == 0:
        return 0.0
        
    return round(valores.mean() * 10, 1)

# --- VELOCÍMETROS ---
def crear_velocimetro(score, titulo, mini=False, is_promedio=False):
    if is_promedio:
        color_bar = '#22C55E' if score >= 90 else ('#EAB308' if score >= 80 else '#EF4444')
    else:
        color_bar = '#22C55E' if score >= 90 else ('#EAB308' if score >= 70 else '#EF4444')

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

# --- GRÁFICOS DE TORTA ---
def crear_torta(df, columna, titulo):
    if columna not in df.columns:
        fig = go.Figure()
        fig.update_layout(title={'text': f"<b>{titulo}</b>", 'x': 0.5, 'y': 0.85, 'xanchor': 'center', 'yanchor': 'top', 'font': {'size': 12, 'color': '#475569'}}, height=160, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        return fig
        
    datos = df[columna].value_counts()
    fig = go.Figure(data=[go.Pie(labels=datos.index, values=datos.values, hole=.5, textinfo='label+percent', textposition='inside', insidetextorientation='radial')])
    
    fig.update_layout(
        title={'text': f"<b>{titulo}</b>", 'x': 0.5, 'y': 0.95, 'xanchor': 'center', 'yanchor': 'top', 'font': {'size': 12, 'color': '#475569'}}, 
        margin=dict(l=10, r=10, t=40, b=10), height=160, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig
# ==============================================================================
# PANEL LATERAL DE FILTROS GLOBALES
# ==============================================================================
st.sidebar.header("Filtros Globales")
# --- NUEVO INTERRUPTOR MODO REPORTE ---
modo_reporte = st.sidebar.checkbox("🖨️ Activar Modo Reporte (PDF)", value=False, help="Agrupa todas las pestañas verticalmente para imprimir con Ctrl+P.")

years_available = sorted(df_marca_raw['Año'].unique(), reverse=True)
selected_years = st.sidebar.multiselect("Año", options=years_available, default=years_available[:1])

months_available = list(MESES_ES.values())
existing_months = df_marca_raw[df_marca_raw['Año'].isin(selected_years)]['Mes'].unique()
selected_months = st.sidebar.multiselect("Seleccione Mes(es)", options=months_available, default=[m for m in months_available if m in existing_months][:1])

if 'Marca' in df_marca_raw.columns:
    marcas_available = sorted(df_marca_raw['Marca'].dropna().unique())
    selected_marcas = st.sidebar.multiselect("MARCA", options=marcas_available, default=marcas_available[:1] if marcas_available else [])
else:
    selected_marcas = []

# APLICAR FILTROS A AMBAS BASES
df_filtrado = df_marca_raw[df_marca_raw['Año'].isin(selected_years) & df_marca_raw['Mes'].isin(selected_months)]
df_interna_filtrado = df_int_raw[df_int_raw['Año'].isin(selected_years) & df_int_raw['Mes'].isin(selected_months)]

if selected_marcas:
    if 'Marca' in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado['Marca'].isin(selected_marcas)]
    if 'Marca' in df_interna_filtrado.columns: df_interna_filtrado = df_interna_filtrado[df_interna_filtrado['Marca'].isin(selected_marcas)]
# ==============================================================================
# TÍTULO PRINCIPAL
# ==============================================================================
st.markdown("<h1 style='font-size: 36px; color: #1E293B; display: flex; align-items: center;'><span style='font-size: 40px; margin-right: 15px;'>📊</span> INDICADORES Y SEGUIMIENTO DE CALIDAD POSTVENTA AUTOCIEL</h1>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)
# ==============================================================================
# LÓGICA DE ENRUTAMIENTO (PESTAÑAS WEB VS MODO REPORTE APILADO)
# ==============================================================================
if not modo_reporte:
    # ------------------------------------------------------------------------------
    # MODO TRADICIONAL (PESTAÑAS WEB)
    # ------------------------------------------------------------------------------
    tab_monitor, tab_tabla, tab_ficha, tab_carga, tab_quejas, tab_telemarketer, tab_prima = st.tabs([
        "🏠 Monitor Global Comparativo", 
        "👥 Tabla Unificada de Asesores", 
        "👤 Ficha Histórica Asesor", 
        "📊 Análisis de Carga Operativa",
        "⚠️ Gestión de Quejas",
        "📞 Telemarketer",
        "💰 Prima de Calidad"
    ])
else:
    # ------------------------------------------------------------------------------
    # MODO REPORTE (CONTENEDORES VERTICALES)
    # ------------------------------------------------------------------------------
    st.markdown("<div style='background-color:#FFF3CD; padding:15px; border-radius:5px; color:#856404; font-weight:bold;' class='no-print'>🖨️ MODO REPORTE ACTIVADO. Presioná 'Ctrl + P' en tu teclado y elegí la opción 'Guardar como PDF' para exportar.</div><br>", unsafe_allow_html=True)
    
    tab_monitor = st.container()
    tab_monitor.markdown("<h2 style='color:#1E293B;'>🏠 Monitor Global Comparativo</h2>", unsafe_allow_html=True)
    
    st.markdown("<hr class='no-print' style='border: 2px solid #E2E8F0;'>", unsafe_allow_html=True)
    tab_tabla = st.container()
    tab_tabla.markdown("<h2 style='color:#1E293B;'>👥 Tabla Unificada de Asesores</h2>", unsafe_allow_html=True)
    
    st.markdown("<hr class='no-print' style='border: 2px solid #E2E8F0;'>", unsafe_allow_html=True)
    tab_ficha = st.container()
    tab_ficha.markdown("<h2 style='color:#1E293B;'>👤 Ficha Histórica Asesor</h2>", unsafe_allow_html=True)
    
    st.markdown("<hr class='no-print' style='border: 2px solid #E2E8F0;'>", unsafe_allow_html=True)
    tab_carga = st.container()
    tab_carga.markdown("<h2 style='color:#1E293B;'>📊 Análisis de Carga Operativa</h2>", unsafe_allow_html=True)
    
    st.markdown("<hr class='no-print' style='border: 2px solid #E2E8F0;'>", unsafe_allow_html=True)
    tab_quejas = st.container()
    tab_quejas.markdown("<h2 style='color:#1E293B;'>⚠️ Gestión de Quejas</h2>", unsafe_allow_html=True)
    
    st.markdown("<hr class='no-print' style='border: 2px solid #E2E8F0;'>", unsafe_allow_html=True)
    tab_telemarketer = st.container()
    tab_telemarketer.markdown("<h2 style='color:#1E293B;'>📞 Telemarketer</h2>", unsafe_allow_html=True)
    
    st.markdown("<hr class='no-print' style='border: 2px solid #E2E8F0;'>", unsafe_allow_html=True)
    tab_prima = st.container()
    tab_prima.markdown("<h2 style='color:#1E293B;'>💰 Prima de Calidad</h2>", unsafe_allow_html=True)
# ------------------------------------------------------------------------------
# 1. MONITOR GLOBAL COMPARATIVO
# ------------------------------------------------------------------------------
with tab_monitor:
    st.markdown(f"<div class='sub-title'>Resultados en Paralelo: {', '.join(selected_months)}</div>", unsafe_allow_html=True)
    
    col_izq, col_der = st.columns(2)
    
    # === LADO IZQUIERDO: MARCA ===
    with col_izq:
        with st.container(border=True):
            st.markdown("<h3 style='text-align:center; color:#2563EB; margin-top: 10px;'>🏢 ENCUESTA DE MARCA</h3>", unsafe_allow_html=True)
            st.markdown("---")
            col_q1, col_q2 = st.columns(2)
            with col_q1:
                score_q1, p_q1, n_q1, d_q1 = calcular_metricas_nps(df_filtrado, "Q1 - Satisfacción general")
                st.plotly_chart(crear_velocimetro(score_q1, "Q1 - SATISFACCIÓN (NPS)"), use_container_width=True)
                sub_c1, sub_c2, sub_c3 = st.columns(3)
                with sub_c1: st.button(f"😄 {p_q1}", key="btn_m_p1", on_click=set_filtro_marca, args=('Promotor',))
                with sub_c2: st.button(f"😐 {n_q1}", key="btn_m_n1", on_click=set_filtro_marca, args=('Neutro',))
                with sub_c3: st.button(f"😠 {d_q1}", key="btn_m_d1", on_click=set_filtro_marca, args=('Detractor',))

            with col_q2:
                score_q2, p_q2, n_q2, d_q2 = calcular_metricas_nps(df_filtrado, "Q2 - Recomendación - taller")
                st.plotly_chart(crear_velocimetro(score_q2, "Q2 - RECOMENDACIÓN (NPS)"), use_container_width=True)
                sub_c4, sub_c5, sub_c6 = st.columns(3)
                with sub_c4: st.button(f"😄 {p_q2}", key="btn_m_p2", on_click=set_filtro_marca, args=('Promotor',))
                with sub_c5: st.button(f"😐 {n_q2}", key="btn_m_n2", on_click=set_filtro_marca, args=('Neutro',))
                with sub_c6: st.button(f"😠 {d_q2}", key="btn_m_d2", on_click=set_filtro_marca, args=('Detractor',))
                
            st.markdown("<br>", unsafe_allow_html=True)
            subtab_agendamiento, subtab_asesor, subtab_taller, subtab_contacto = st.tabs(["📅 Agend.", "👔 Asesor", "⚙️ Taller", "📞 Cont. "])
            with subtab_agendamiento:
                c1, c2 = st.columns(2)
                with c1: st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_filtrado, "Q5 - Facilidad de agendamiento")[0], "Q5 - Agendamiento", mini=True), use_container_width=True)
                with c2: st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_filtrado, "Q6 - Satisfacción instalaciones")[0], "Q6 - Instalaciones", mini=True), use_container_width=True)
            with subtab_asesor:
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_filtrado, "Q7 - Cortesía y Amabilidad")[0], "Q7 - Cortesía", mini=True), use_container_width=True)
                with c2: st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_filtrado, "Q8 - Competencia Asesor de Servicio")[0], "Q8 - Competencia", mini=True), use_container_width=True)
                with c3: st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_filtrado, "Q10 - Explicación presupuesto")[0], "Q10 - Presupuesto", mini=True), use_container_width=True)
                with c4: st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_filtrado, "Q11 - Explicación trabajo - costo")[0], "Q11 - Expl. Trabajo", mini=True), use_container_width=True)
            with subtab_taller:
                c1, c2, c3 = st.columns(3)
                with c1: st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_filtrado, "Q12 - Calidad del trabajo")[0], "Q12 - Calidad", mini=True), use_container_width=True)
                with c2: st.plotly_chart(crear_torta(df_filtrado, col_q13, "Q13 - FIR"), use_container_width=True)
                with c3: st.plotly_chart(crear_torta(df_filtrado, "Q15 - Entrega según momento acordado", "Q15 - Entrega"), use_container_width=True)
            with subtab_contacto:
                st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_filtrado, "Q19 - Satisfacción con el Contacto")[0], "Q19 - Satisfacción Contacto", mini=True), use_container_width=True)

    # === LADO DERECHO: INTERNA ===
    with col_der:
        with st.container(border=True):
            st.markdown("<h3 style='text-align:center; color:#10B981; margin-top: 10px;'>🎯 ENCUESTA INTERNA</h3>", unsafe_allow_html=True)
            st.markdown("---")
            col_i1, col_i2 = st.columns(2)
            with col_i1:
                score_i1 = calcular_promedio(df_interna_filtrado, "Promedio")
                st.plotly_chart(crear_velocimetro(score_i1, "SATISFACCIÓN (Promedio)", is_promedio=True), use_container_width=True)
                
            with col_i2:
                score_i2, p_i2, n_i2, d_i2 = calcular_metricas_nps(df_interna_filtrado, "1-NPS")
                st.plotly_chart(crear_velocimetro(score_i2, "RECOMENDACIÓN (NPS)"), use_container_width=True)
                sub_i4, sub_i5, sub_i6 = st.columns(3)
                with sub_i4: st.button(f"😄 {p_i2}", key="btn_i_p2", on_click=set_filtro_int, args=('Promotor',))
                with sub_i5: st.button(f"😐 {n_i2}", key="btn_i_n2", on_click=set_filtro_int, args=('Neutro',))
                with sub_i6: st.button(f"😠 {d_i2}", key="btn_i_d2", on_click=set_filtro_int, args=('Detractor',))
                
            st.markdown("<br>", unsafe_allow_html=True)
            subtab_agend_int, subtab_asesor_int, subtab_taller_int, subtab_contacto_int = st.tabs(["📅 Agend.", "👔 Asesor", "⚙️ Taller", "📞 Cont. "])
            with subtab_agend_int:
                st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_interna_filtrado, "2-Obtener turno")[0], "2-Obtener turno", mini=True), use_container_width=True)
            with subtab_asesor_int:
                st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_interna_filtrado, "4-Atención de necesidades")[0], "4-Atención necesidades", mini=True), use_container_width=True)
            with subtab_taller_int:
                c1, c2 = st.columns(2)
                with c1: st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_interna_filtrado, "6-Calidad de trabajo")[0], "6-Calidad trabajo", mini=True), use_container_width=True)
                with c2: st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_interna_filtrado, "7-Limpieza del vehículo")[0], "7-Limpieza", mini=True), use_container_width=True)
            with subtab_contacto_int:
                st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_interna_filtrado, "11-Contacto Servicio Oficial")[0], "11-Contacto Oficial", mini=True), use_container_width=True)

    # === TABLA GLOBAL DE COMENTARIOS DOBLE (RECUADROS) ===
    st.markdown("---")
    st.markdown("### 💬 Comentarios de Clientes")
    col_com_m, col_com_i = st.columns(2)
    
    with col_com_m:
        with st.container(border=True):
            st.markdown(f"**🏢 Marca (Filtro: {st.session_state.filtro_comentarios_marca})**")
            if st.session_state.filtro_comentarios_marca != 'Todos':
                st.button("🔄 Ver Todos (Marca)", on_click=set_filtro_marca, args=('Todos',))
            
            if "Q3 - Verbalización" in df_filtrado.columns:
                df_com_m = df_filtrado.copy()
                if st.session_state.filtro_comentarios_marca != 'Todos':
                    q_base = pd.to_numeric(df_com_m["Q1 - Satisfacción general"], errors='coerce')
                    if st.session_state.filtro_comentarios_marca == 'Promotor': df_com_m = df_com_m[q_base >= 9]
                    elif st.session_state.filtro_comentarios_marca == 'Neutro': df_com_m = df_com_m[(q_base >= 7) & (q_base <= 8)]
                    elif st.session_state.filtro_comentarios_marca == 'Detractor': df_com_m = df_com_m[q_base <= 6]
                    
                col_nombre_m = 'Nombre Principal' if 'Nombre Principal' in df_com_m.columns else next((c for c in df_com_m.columns if 'Nombre' in c or 'Cliente' in c), None)
                col_fecha_m = 'Fecha de la Encuesta' if 'Fecha de la Encuesta' in df_com_m.columns else next((c for c in df_com_m.columns if 'Fecha' in c), None)
                
                cols_m = []
                if col_nombre_m: cols_m.append(col_nombre_m)
                if col_fecha_m: cols_m.append(col_fecha_m)
                if "Marca" in df_com_m.columns: cols_m.append("Marca")
                cols_m.append("Q3 - Verbalización")
                
                cm_view = df_com_m[cols_m].dropna(subset=["Q3 - Verbalización"])
                if len(cm_view) > 0: st.dataframe(cm_view, use_container_width=True, hide_index=True)
                else: st.info("Sin comentarios para este segmento.")
            
    with col_com_i:
        with st.container(border=True):
            st.markdown(f"**🎯 Interna (Filtro: {st.session_state.filtro_comentarios_int})**")
            if st.session_state.filtro_comentarios_int != 'Todos':
                st.button("🔄 Ver Todos (Interna)", on_click=set_filtro_int, args=('Todos',))
                
            if "CONCATENADO" in df_interna_filtrado.columns:
                df_com_i = df_interna_filtrado.copy()
                if st.session_state.filtro_comentarios_int != 'Todos':
                    qi_base = pd.to_numeric(df_com_i["1-NPS"], errors='coerce')
                    if st.session_state.filtro_comentarios_int == 'Promotor': df_com_i = df_com_i[qi_base >= 9]
                    elif st.session_state.filtro_comentarios_int == 'Neutro': df_com_i = df_com_i[(qi_base >= 7) & (qi_base <= 8)]
                    elif st.session_state.filtro_comentarios_int == 'Detractor': df_com_i = df_com_i[qi_base <= 6]
                
                col_nombre_i = 'Cliente' if 'Cliente' in df_com_i.columns else next((c for c in df_com_i.columns if 'Nombre' in c), None)
                
                if 'Fecha de la Encuesta' in df_com_i.columns:
                    col_fecha_i = 'Fecha de la Encuesta'
                elif 'Marca temporal' in df_com_i.columns:
                    col_fecha_i = 'Marca temporal'
                else:
                    col_fecha_i = next((c for c in df_com_i.columns if 'Fecha' in c and 'Cierre' not in c), None)
                
                cols_i = []
                if col_nombre_i: cols_i.append(col_nombre_i)
                if col_fecha_i: cols_i.append(col_fecha_i)
                if "Marca" in df_com_i.columns: cols_i.append("Marca")
                cols_i.append("CONCATENADO")
                
                ci_view = df_com_i[cols_i].dropna(subset=["CONCATENADO"])
                if len(ci_view) > 0: st.dataframe(ci_view, use_container_width=True, hide_index=True)
                else: st.info("Sin comentarios para este segmento.")

# ------------------------------------------------------------------------------
# 2. TABLA UNIFICADA DE ASESORES (RANKING DUAL)
# ------------------------------------------------------------------------------
with tab_tabla:
    st.markdown("### Ranking de Desempeño General de Asesores")
    
    subtab_rk_marca, subtab_rk_int = st.tabs(["🏆 Ranking Oficial (Marca)", "🎯 Ranking Interno"])
    
    # --- RANKING MARCA ---
    with subtab_rk_marca:
        col_asesor_key = next((col for col in df_filtrado.columns if 'Asesor' in col), None)
        if col_asesor_key:
            asesores = df_filtrado[col_asesor_key].dropna().unique()
            ranking_data = []
            
            for p_asesor in asesores:
                df_ase = df_filtrado[df_filtrado[col_asesor_key] == p_asesor]
                nps_q2, p_q2, n_q2, d_q2 = calcular_metricas_nps(df_ase, "Q2 - Recomendación - taller")
                nps_q7, _, _, _ = calcular_metricas_nps(df_ase, "Q7 - Cortesía y Amabilidad")
                nps_q8, _, _, _ = calcular_metricas_nps(df_ase, "Q8 - Competencia Asesor de Servicio")
                nps_q10, _, _, _ = calcular_metricas_nps(df_ase, "Q10 - Explicación presupuesto")
                nps_q11, _, _, _ = calcular_metricas_nps(df_ase, "Q11 - Explicación trabajo - costo")
                
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
                    "Muestra": len(df_ase),
                    "NPS Q2 (Recomendación)": nps_q2,
                    "NPS Q7 (Cortesía)": nps_q7,
                    "NPS Q8 (Competencia)": nps_q8,
                    "NPS Q10 (Presupuesto)": nps_q10,
                    "NPS Q11 (Trabajo/Costo)": nps_q11,
                    "Meta 94%": meta_str
                })
                
            df_ranking = pd.DataFrame(ranking_data).sort_values(by="NPS Q2 (Recomendación)", ascending=False)
            st.dataframe(df_ranking, use_container_width=True, hide_index=True)
        else:
            st.warning("Columna de Asesor no encontrada en la base de la Marca.")
            
    # --- RANKING INTERNO ---
    with subtab_rk_int:
        col_asesor_int = "Asesor" if "Asesor" in df_interna_filtrado.columns else None
        
        if col_asesor_int:
            asesores_int = df_interna_filtrado[col_asesor_int].dropna().unique()
            ranking_data_int = []
            
            for p_asesor in asesores_int:
                df_ase_i = df_interna_filtrado[df_interna_filtrado[col_asesor_int] == p_asesor]
                
                nps_rec_i, _, _, _ = calcular_metricas_nps(df_ase_i, "1-NPS")
                prom_i = calcular_promedio(df_ase_i, "Promedio")
                nps_turno, _, _, _ = calcular_metricas_nps(df_ase_i, "2-Obtener turno")
                nps_atencion, _, _, _ = calcular_metricas_nps(df_ase_i, "4-Atención de necesidades")
                nps_calidad, _, _, _ = calcular_metricas_nps(df_ase_i, "6-Calidad de trabajo")
                nps_limpieza, _, _, _ = calcular_metricas_nps(df_ase_i, "7-Limpieza del vehículo")
                
                ranking_data_int.append({
                    "Asesor de Servicio": p_asesor,
                    "Muestra": len(df_ase_i),
                    "Recomendación (1-NPS)": nps_rec_i,
                    "Satisfacción (Promedio)": prom_i,
                    "Turno (NPS)": nps_turno,
                    "Atención (NPS)": nps_atencion,
                    "Calidad Trabajo (NPS)": nps_calidad,
                    "Limpieza (NPS)": nps_limpieza
                })
                
            df_ranking_int = pd.DataFrame(ranking_data_int).sort_values(by="Recomendación (1-NPS)", ascending=False)
            st.dataframe(df_ranking_int, use_container_width=True, hide_index=True)
        else:
            st.warning("La columna 'Asesor' no se encontró en la base de datos Interna.")

# ------------------------------------------------------------------------------
# 3. FICHA HISTÓRICA POR ASESOR
# ------------------------------------------------------------------------------
with tab_ficha:
    st.markdown("### Evolución Histórica de Calidad (Cruce Marca vs Interna)")
    st.markdown("<p style='font-size: 14px; color: #64748B; margin-top:-10px;'>Esta sección analiza el historial completo de cada asesor. Cruza el rendimiento oficial de la Marca frente a la evaluación Interna del concesionario.</p>", unsafe_allow_html=True)
    
    asesores_m = set(df_marca_raw[col_asesor_key].dropna().unique()) if col_asesor_key else set()
    asesores_i = set(df_int_raw["Asesor"].dropna().unique()) if "Asesor" in df_int_raw.columns else set()
    lista_asesores_hist = sorted(list(asesores_m.union(asesores_i)))
    
    if lista_asesores_hist:
        asesor_seleccionado_hist = st.selectbox("Seleccione el Asesor de Servicio para ver su historial:", options=lista_asesores_hist)
        
        df_hist_ase_m = df_marca_raw[df_marca_raw[col_asesor_key] == asesor_seleccionado_hist] if col_asesor_key else pd.DataFrame()
        df_hist_ase_i = df_int_raw[df_int_raw["Asesor"] == asesor_seleccionado_hist] if "Asesor" in df_int_raw.columns else pd.DataFrame()
        
        col_kpi_m, col_kpi_i = st.columns(2)
        
        with col_kpi_m:
            with st.container(border=True):
                st.markdown("<h4 style='text-align:center; color:#2563EB; margin-top: 10px;'>Acumulado Marca</h4>", unsafe_allow_html=True)
                k1, k2, k3 = st.columns(3)
                with k1: st.markdown(f"<div class='kpi-card' style='padding:10px;'><div class='kpi-label'>RECOMENDACIÓN</div><div class='kpi-value' style='font-size:32px;'>{calcular_metricas_nps(df_hist_ase_m, 'Q2 - Recomendación - taller')[0]}%</div></div>", unsafe_allow_html=True)
                with k2: st.markdown(f"<div class='kpi-card' style='padding:10px;'><div class='kpi-label'>SATISFACCIÓN</div><div class='kpi-value' style='font-size:32px;'>{calcular_metricas_nps(df_hist_ase_m, 'Q1 - Satisfacción general')[0]}%</div></div>", unsafe_allow_html=True)
                with k3: st.markdown(f"<div class='kpi-card' style='padding:10px;'><div class='kpi-label'>MUESTRA</div><div class='kpi-value' style='font-size:32px;'>{len(df_hist_ase_m)}</div></div>", unsafe_allow_html=True)

        with col_kpi_i:
            with st.container(border=True):
                st.markdown("<h4 style='text-align:center; color:#10B981; margin-top: 10px;'>Acumulado Interno</h4>", unsafe_allow_html=True)
                k4, k5, k6 = st.columns(3)
                with k4: st.markdown(f"<div class='kpi-card' style='padding:10px;'><div class='kpi-label'>RECOMENDACIÓN</div><div class='kpi-value' style='font-size:32px;'>{calcular_metricas_nps(df_hist_ase_i, '1-NPS')[0]}%</div></div>", unsafe_allow_html=True)
                with k5: st.markdown(f"<div class='kpi-card' style='padding:10px;'><div class='kpi-label'>SATISFACCIÓN</div><div class='kpi-value' style='font-size:32px;'>{calcular_promedio(df_hist_ase_i, 'Promedio')}%</div></div>", unsafe_allow_html=True)
                with k6: st.markdown(f"<div class='kpi-card' style='padding:10px;'><div class='kpi-label'>MUESTRA</div><div class='kpi-value' style='font-size:32px;'>{len(df_hist_ase_i)}</div></div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.container(border=True):
            hist_data_m = {}
            if 'Mes_Num' in df_hist_ase_m.columns:
                for (año, mes_num), group in df_hist_ase_m.groupby(['Año', 'Mes_Num']):
                    hist_data_m[(año, mes_num)] = calcular_metricas_nps(group, "Q2 - Recomendación - taller")[0]
                    
            hist_data_i = {}
            if 'Mes_Num' in df_hist_ase_i.columns:
                for (año, mes_num), group in df_hist_ase_i.groupby(['Año', 'Mes_Num']):
                    hist_data_i[(año, mes_num)] = calcular_metricas_nps(group, "1-NPS")[0]
                    
            global_nps = {}
            if 'Mes_Num' in df_marca_raw.columns:
                for (año, mes), group in df_marca_raw.groupby(['Año', 'Mes_Num']):
                    global_nps[(año, mes)] = calcular_metricas_nps(group, "Q2 - Recomendación - taller")[0]

            periodos_unicos = set(hist_data_m.keys()).union(set(hist_data_i.keys()))
            
            chart_data = []
            for (año, mes_num) in periodos_unicos:
                mes_nombre = MESES_ES.get(mes_num, "Desc")
                chart_data.append({
                    "Periodo": f"{mes_nombre} {año}",
                    "Orden": año * 100 + mes_num, 
                    "NPS_Marca": hist_data_m.get((año, mes_num), None),
                    "NPS_Interna": hist_data_i.get((año, mes_num), None),
                    "NPS_Global": global_nps.get((año, mes_num), None)
                })
                
            if chart_data:
                df_grafico = pd.DataFrame(chart_data).sort_values("Orden")
                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(x=df_grafico['Periodo'], y=df_grafico['NPS_Global'], mode='lines', name='Promedio Taller (Marca)', line=dict(color='#CBD5E1', width=3), hoverinfo='skip'))
                fig_line.add_trace(go.Scatter(x=df_grafico['Periodo'], y=df_grafico['NPS_Marca'], mode='lines+markers+text', name=f'NPS Marca', line=dict(color='#1E293B', width=3), marker=dict(size=10, color='#1E293B'), text=df_grafico['NPS_Marca'].apply(lambda x: f"{x}%" if pd.notnull(x) else ""), textposition='top center', hovertemplate='<b>%{x}</b><br>Marca: %{y}%<extra></extra>'))
                fig_line.add_trace(go.Scatter(x=[df_grafico['Periodo'].iloc[0], df_grafico['Periodo'].iloc[-1]], y=[94, 94], mode='lines', name='Objetivo (94%)', line=dict(color='#22C55E', width=2, dash='dash'), hoverinfo='skip'))
                fig_line.update_layout(title={'text': "Cruce Evolutivo de NPS: Evaluación Oficial vs. Evaluación Interna", 'font': {'size': 16, 'color': '#1E293B'}}, yaxis=dict(title='NPS (%)', range=[0, 105], showgrid=True, gridcolor='#E2E8F0'), xaxis=dict(showgrid=False), margin=dict(l=40, r=40, t=60, b=40), height=450, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("No hay suficientes datos históricos para generar el gráfico.")
    else:
        st.info("No se encontraron asesores en las bases oficales para analizar.")

# ------------------------------------------------------------------------------
# 4. ANÁLISIS DE CARGA OPERATIVA Y CAUSA RAÍZ (PANTALLA DIVIDIDA)
# ------------------------------------------------------------------------------
with tab_carga:
    st.markdown("### 📊 Análisis de Carga Operativa y Calidad")
    
    col_carga_m, col_carga_i = st.columns(2)
    
    # === LADO IZQUIERDO: MARCA ===
    with col_carga_m:
        with st.container(border=True):
            st.markdown("<h4 style='color:#2563EB;'>🏢 Causa Raíz - Marca</h4>", unsafe_allow_html=True)
            
            if col_q4:
                st.markdown("<p style='font-size: 14px; color: #64748B;'>Cruza el volumen de cada servicio con su puntaje de Recomendación (Q2).</p>", unsafe_allow_html=True)
                motivos_data = []
                for motivo in df_filtrado[col_q4].dropna().unique():
                    df_motivo = df_filtrado[df_filtrado[col_q4] == motivo]
                    nps_q2, _, _, _ = calcular_metricas_nps(df_motivo, "Q2 - Recomendación - taller")
                    motivos_data.append({"Motivo": motivo, "Volumen": len(df_motivo), "NPS_Q2": nps_q2})
                    
                if motifs_data := motivos_data:
                    df_m = pd.DataFrame(motifs_data).sort_values(by="Volumen", ascending=True)
                    
                    fig_q4 = go.Figure()
                    fig_q4.add_trace(go.Bar(y=df_m["Motivo"], x=df_m["Volumen"], orientation='h', marker=dict(color=df_m["NPS_Q2"], colorscale=[[0, '#EF4444'], [0.7, '#EAB308'], [1, '#22C55E']], cmin=0, cmax=100, colorbar=dict(title="NPS Q2")), text=df_m["Volumen"], textposition='auto', hovertemplate="<b>Motivo:</b> %{y}<br><b>Autos:</b> %{x}<br><b>NPS Recomendación:</b> %{marker.color:.1f}%<extra></extra>"))
                    fig_q4.update_layout(title="Volumen vs. NPS Recommendation", height=350 if len(df_m) > 3 else 250, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_q4, use_container_width=True)
                    
                    if col_q13 in df_filtrado.columns:
                        st.markdown("<br>", unsafe_allow_html=True)
                        respuestas_q13 = df_filtrado[col_q13].dropna().unique()
                        colores_stack = ['#22C55E', '#EF4444', '#EAB308', '#64748B', '#3B82F6']
                        
                        fig_fir = go.Figure()
                        y_orden = df_m["Motivo"]
                        for i, resp in enumerate(respuestas_q13):
                            conteos = df_filtrado[df_filtrado[col_q13] == resp][col_q4].value_counts()
                            x_vals = [conteos.get(m, 0) for m in y_orden]
                            fig_fir.add_trace(go.Bar(y=y_orden, x=x_vals, name=str(resp), orientation='h', marker_color=colores_stack[i % len(colores_stack)]))
                        
                        fig_fir.update_layout(barmode='stack', title="Motivo vs. Reparado en 1ra Visita (FIR)", height=350 if len(df_m) > 3 else 250, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                        st.plotly_chart(fig_fir, use_container_width=True)
                        
                if "Q3 - Verbalización" in df_filtrado.columns:
                    st.markdown("---")
                    st.markdown("#### 💬 Lupa Cualitativa")
                    motivo_sel = st.selectbox("Filtrar comentarios por Motivo:", options=["Ver Todos"] + sorted(df_filtrado[col_q4].dropna().unique()), key="sel_m")
                    df_com_q4 = df_filtrado.copy()
                    if motivo_sel != "Ver Todos": df_com_q4 = df_com_q4[df_com_q4[col_q4] == motivo_sel]
                    df_mostrar_q4 = df_com_q4[["Fecha de la Encuesta", "Marca", col_q4, "Q1 - Satisfacción general", "Q3 - Verbalización"]].dropna(subset=["Q3 - Verbalización"])
                    if len(df_mostrar_q4) > 0: st.dataframe(df_mostrar_q4, use_container_width=True, hide_index=True)
                    else: st.info("No hay comentarios registrados para el motivo seleccionado.")
            else:
                st.info("Columna de motivos de visita (Q4) no encontrada.")

    # === LADO DERECHO: INTERNA ===
    with col_carga_i:
        with st.container(border=True):
            st.markdown("<h4 style='text-align:center; color:#10B981;'>🎯 Causa Raíz - Interna</h4>", unsafe_allow_html=True)
            st.markdown("<p style='font-size: 14px; color: #64748B;'>Análisis basado en las verbalizaciones operativas. Ingresá una palabra clave para buscar fallas recurrentes.</p>", unsafe_allow_html=True)
            
            if "CONCATENADO" in df_interna_filtrado.columns:
                palabra_clave = st.text_input("🔍 Buscar en verbalizaciones (ej. 'lavado', 'ruido', 'demora'):", key="search_int")
                
                df_carga_int = df_interna_filtrado.copy()
                if palabra_clave:
                    df_carga_int = df_carga_int[df_carga_int["CONCATENADO"].str.contains(palabra_clave, case=False, na=False)]
                
                col_nombre_i = 'Cliente' if 'Cliente' in df_carga_int.columns else next((c for c in df_carga_int.columns if 'Nombre' in c), None)
                
                if 'Fecha de la Encuesta' in df_carga_int.columns:
                    col_fecha_i = 'Fecha de la Encuesta'
                elif 'Marca temporal' in df_carga_int.columns:
                    col_fecha_i = 'Marca temporal'
                else:
                    col_fecha_i = next((c for c in df_carga_int.columns if 'Fecha' in c and 'Cierre' not in c), None)
                
                cols_i_show = []
                if col_nombre_i: cols_i_show.append(col_nombre_i)
                if col_fecha_i: cols_i_show.append(col_fecha_i)
                if "1-NPS" in df_carga_int.columns: cols_i_show.append("1-NPS")
                if "6-Calidad de trabajo" in df_carga_int.columns: cols_i_show.append("6-Calidad de trabajo")
                cols_i_show.append("CONCATENADO")
                
                view_int_carga = df_carga_int[cols_i_show].dropna(subset=["CONCATENADO"])
                
                st.markdown(f"**Resultados encontrados: {len(view_int_carga)}**")
                if len(view_int_carga) > 0:
                    st.dataframe(view_int_carga, use_container_width=True, hide_index=True)
                else:
                    st.info("No se encontraron comentarios con esa palabra clave.")
            else:
                st.info("Columna 'CONCATENADO' no encontrada en la base interna.")

# ------------------------------------------------------------------------------
# 5. GESTIÓN DE QUEJAS
# ------------------------------------------------------------------------------
with tab_quejas:
    st.markdown("### Alertas de Clientes Detractores")
    st.markdown("Casos críticos detectados donde la puntuación en Satisfacción (Q1) o Recomendación (Q2) es igual o menor a 6.")
    
    with st.container(border=True):
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
                st.success("🎉 ¡Excelente! No se registraron clientes detractors para los filtros seleccionados.")
        else:
            st.info("Columnas de análisis de quejas no encontradas.")

# ------------------------------------------------------------------------------
# 6. PESTAÑA: TELEMARKETER (CON FILTROS INTERNOS DE AÑO Y MARCA AISLADOS)
# ------------------------------------------------------------------------------
with tab_telemarketer:
    st.markdown("### 📞 Control y Efectividad de Canales (Telemarketing)")
    st.markdown("Esta sección funciona de forma independiente utilizando filtros de tiempo y marca propios.")
    
    df_tele_base = df_int_raw.copy()
    col_cierre = "Fecha Cierre"
    
    if col_cierre in df_tele_base.columns:
        df_tele_base['Fecha_Cierre_Clean'] = pd.to_datetime(df_tele_base[col_cierre], dayfirst=True, errors='coerce')
        df_tele_base['Año_Cierre'] = df_tele_base['Fecha_Cierre_Clean'].dt.year
        df_tele_base['Mes_Cierre_Num'] = df_tele_base['Fecha_Cierre_Clean'].dt.month
        
        df_tele_base = df_tele_base.dropna(subset=['Año_Cierre', 'Mes_Cierre_Num'])
        df_tele_base['Año_Cierre'] = df_tele_base['Año_Cierre'].astype(int)
        df_tele_base['Mes_Cierre_Num'] = df_tele_base['Mes_Cierre_Num'].astype(int)
        df_tele_base['Mes_Cierre_Nombre'] = df_tele_base['Mes_Cierre_Num'].map(MESES_ES)
        
        # --- DESPLIEGUE DE FILTROS INTERNOS EN PARALELO ---
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            anios_cierre_disponibles = sorted(df_tele_base['Año_Cierre'].unique(), reverse=True)
            anio_tele_sel = st.selectbox("Seleccione Año de Cierre:", options=anios_cierre_disponibles, key="sb_anio_tele")
            
        with col_f2:
            if 'Marca' in df_tele_base.columns:
                marcas_tele_disponibles = sorted(df_tele_base['Marca'].dropna().unique())
            else:
                marcas_tele_disponibles = ["PEUGEOT", "CITROEN"]
                
            marcas_tele_sel = st.multiselect("Seleccione Marca(s):", options=marcas_tele_disponibles, default=marcas_tele_disponibles, key="ms_marca_tele")
            
        # APLICAR FILTRADO INTERNO EXCLUSIVO (Año + Marcas seleccionadas)
        df_tele_filtrado = df_tele_base[df_tele_base['Año_Cierre'] == anio_tele_sel]
        if marcas_tele_sel and 'Marca' in df_tele_filtrado.columns:
            df_tele_filtrado = df_tele_filtrado[df_tele_filtrado['Marca'].isin(marcas_tele_sel)]
            
        st.markdown("---")
        st.markdown(f"#### 📈 Evolución Mensual de Comunicación Efectiva")
        
        meses_con_datos = sorted(df_tele_filtrado['Mes_Cierre_Num'].unique())
        
        line_data_tele = []
        for m_num in range(1, 13):
            df_mes = df_tele_filtrado[df_tele_filtrado['Mes_Cierre_Num'] == m_num]
            
            if 'Tipo Contacto' in df_mes.columns:
                s_contacto = df_mes['Tipo Contacto'].fillna('Vacío').astype(str).str.strip()
                
                c_whatsapp = len(s_contacto[s_contacto == 'Whatsapp'])
                c_telefonico = len(s_contacto[s_contacto == 'Telefonico'])
                c_vacios = len(s_contacto[s_contacto == 'Vacío'])
                
                total_intentos_global = c_whatsapp + c_telefonico + c_vacios
                
                # 1. EFECTIVIDAD VIRTUAL (WHATSAPP): WhatsApp / (WhatsApp + Vacios)
                den_virtual = c_whatsapp + c_vacios
                pct_virtual = round((c_whatsapp / den_virtual * 100), 1) if den_virtual > 0 else None
                
                # 2. EFECTIVIDAD TELEMARKETER (TELEFONICO): Telefonico / (Telefonico + Vacios)
                den_human = c_telefonico + c_vacios
                pct_human = round((c_telefonico / den_human * 100), 1) if den_human > 0 else None
                
                # 3. EFECTIVIDAD GLOBAL DEL TALLER: (Whatsapp + Telefonico) / Total Intentos Globales
                pct_global = round(((c_whatsapp + c_telefonico) / total_intentos_global * 100), 1) if total_intentos_global > 0 else None
            else:
                c_whatsapp, c_telefonico, c_vacios = 0, 0, 0
                pct_global, pct_virtual, pct_human = None, None, None
                
            if m_num in meses_con_datos:
                line_data_tele.append({
                    "Mes_Nombre": MESES_ES[m_num],
                    "Mes_Num": m_num,
                    "Global": pct_global,
                    "Virtual": pct_virtual,
                    "Telemarketer": pct_human,
                    "Cant_WA": c_whatsapp,
                    "Cant_Tel": c_telefonico,
                    "Cant_Vac": c_vacios
                })
        
        if line_data_tele:
            df_line_chart = pd.DataFrame(line_data_tele).sort_values("Mes_Num")
            
            fig_tele = go.Figure()
            
            custom_hover = "<b>%{x}</b><br>WhatsApp: %{customdata[0]}<br>Telefónico: %{customdata[1]}<br>Vacíos: %{customdata[2]}<extra></extra>"
            matrix_counts = df_line_chart[['Cant_WA', 'Cant_Tel', 'Cant_Vac']].values
            
            # Línea Global: % en vértice
            fig_tele.add_trace(go.Scatter(
                x=df_line_chart['Mes_Nombre'], y=df_line_chart['Global'], 
                mode='lines+markers+text', name='Efectividad Global (Taller)', 
                line=dict(color='#1E293B', width=4), 
                text=df_line_chart['Global'].apply(lambda x: f"{x}%" if pd.notnull(x) else ""), 
                textposition='top center',
                customdata=matrix_counts, hovertemplate=custom_hover
            ))
            
            # Línea Virtual: % en vértice
            fig_tele.add_trace(go.Scatter(
                x=df_line_chart['Mes_Nombre'], y=df_line_chart['Virtual'], 
                mode='lines+markers+text', name='Asesor Virtual (WhatsApp)', 
                line=dict(color='#2563EB', width=2, dash='dash'),
                text=df_line_chart['Virtual'].apply(lambda x: f"{x}%" if pd.notnull(x) else ""),
                textposition='top center',
                customdata=matrix_counts, hovertemplate=custom_hover
            ))
            
            # Línea Telemarketer: % en vértice (abajo para no encimarse)
            fig_tele.add_trace(go.Scatter(
                x=df_line_chart['Mes_Nombre'], y=df_line_chart['Telemarketer'], 
                mode='lines+markers+text', name='Asesor Telemarketer (Telefónico)', 
                line=dict(color='#10B981', width=2, dash='dot'),
                text=df_line_chart['Telemarketer'].apply(lambda x: f"{x}%" if pd.notnull(x) else ""),
                textposition='bottom center',
                customdata=matrix_counts, hovertemplate=custom_hover
            ))
            
            # NUEVA LÍNEA: Objetivo de efectividad al 75% (Referencia estática discontinua)
            fig_tele.add_trace(go.Scatter(
                x=[df_line_chart['Mes_Nombre'].iloc[0], df_line_chart['Mes_Nombre'].iloc[-1]], 
                y=[75, 75], 
                mode='lines', 
                name='Objetivo (75%)', 
                line=dict(color='#EF4444', width=2, dash='dash'), 
                hoverinfo='skip'
            ))
            
            fig_tele.update_layout(
                yaxis=dict(title='Porcentaje (%)', range=[0, 105], showgrid=True, gridcolor='#E2E8F0'),
                xaxis=dict(showgrid=False),
                margin=dict(l=40, r=40, t=20, b=40),
                height=400,
                hovermode='x unified',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_tele, use_container_width=True)
        else:
            st.info("Sin registros suficientes para generar el gráfico de líneas con los filtros seleccionados.")
            
        # --- SECCIÓN GRAFICOS DE TORTA MENSUALES ---
        st.markdown("---")
        st.markdown(f"#### 🍕 Desglose Mensual del Estado de Contacto ('Contactado')")
        
        if 'Contactado' in df_tele_filtrado.columns:
            df_torta_base = df_tele_filtrado.dropna(subset=['Contactado'])
            meses_torta = sorted(df_torta_base['Mes_Cierre_Num'].unique())
            
            if meses_torta:
                cols_per_row = 3
                for i in range(0, len(meses_torta), cols_per_row):
                    chunk_meses = meses_torta[i:i+cols_per_row]
                    st_cols = st.columns(len(chunk_meses))
                    
                    for idx, m_num in enumerate(chunk_meses):
                        with st_cols[idx]:
                            df_mes_torta = df_torta_base[df_torta_base['Mes_Cierre_Num'] == m_num]
                            counts_estado = df_mes_torta['Contactado'].value_counts()
                            
                            fig_pie = go.Figure(data=[go.Pie(
                                labels=counts_estado.index,
                                values=counts_estado.values,
                                hole=.4,
                                textinfo='percent',
                                textposition='inside'
                            )])
                            
                            fig_pie.update_layout(
                                title={'text': f"<b>{MESES_ES[m_num]}</b>", 'x': 0.5, 'y': 0.95, 'xanchor': 'center', 'font': {'size': 14, 'color': '#1E293B'}},
                                margin=dict(l=10, r=10, t=40, b=10),
                                height=230,
                                showlegend=True,
                                legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5, font=dict(size=10)),
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)'
                            )
                            st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No se registran datos cargados en la columna 'Contactado' para los criterios seleccionados.")
        else:
            st.warning("La columna 'Contactado' no fue localizada en la hoja de datos.")
    else:
        st.error("No se encontró la columna 'Fecha Cierre' indispensable para la pestaña Telemarketer.")

# ------------------------------------------------------------------------------
# 7. PESTAÑA: PRIMA DE CALIDAD (TABLERO ANUAL CON AUDITORÍA + DRIVERS DE COBRO)
# ------------------------------------------------------------------------------
with tab_prima:
    st.markdown("### 📊 Tablero de Auditoría y Liquidación: Prima de Calidad Postventa")
    st.markdown("Esta sección evalúa el cumplimiento de las llaves obligatorias y los incentivos por drivers, incorporando el Bonus Trimestral del 5% y las escalas actualizadas de forma dinámica por año y mes.")
    
    # Selector de Año exclusivo interno
    anios_disponibles_prima = sorted(df_marca_raw['Año'].unique(), reverse=True)
    if anios_disponibles_prima:
        anio_prima_sel = st.selectbox("Seleccione Año para Evaluar la Prima:", options=anios_disponibles_prima, key="sb_anio_prima")
        
        # Seteo de entorno dinámico global para corregir NameError
        es_filtro_2025 = (anio_prima_sel == 2025)
        
        # Filtro de Marcas específico para acotar la auditoría de la prima
        marcas_prima_disponibles = sorted(df_marca_raw['Marca'].dropna().unique()) if 'Marca' in df_marca_raw.columns else ["PEUGEOT", "CITROEN"]
        marcas_prima_sel = st.multiselect("Filtrar por Marcas en la Prima:", options=marcas_prima_disponibles, default=marcas_prima_disponibles, key="ms_marcas_prima")
        
        # Determinar de forma dinámica las personas según la marca seleccionada
        es_peugeot_activo = any('peugeot' in m.lower() for m in marcas_prima_sel) if marcas_prima_sel else True
        es_citroen_activo = any('citroen' in m.lower() for m in marcas_prima_sel) if marcas_prima_sel else True
        
        if es_peugeot_activo and not es_citroen_activo:
            personas_declaradas = 11
        elif es_citroen_activo and not es_peugeot_activo:
            personas_declaradas = 14
        else:
            personas_declaradas = 25 # Suma consolidada
            
        # Procesar datos base filtrados por año
        df_marca_anio = df_marca_raw[df_marca_raw['Año'] == anio_prima_sel]
        
        # Estructurar la matriz de meses (1 al 12) para armar las columnas
        meses_columnas = list(range(1, 13))
        line_data_prima = []
        
        # Diccionarios internos para control acumulado de tramos de cara al Bonus del 5%
        monto_puro_liquidado = {}
        max_teorico_acumulado = {}
        
        # Procesamiento dinámico mes a mes
        for m_num in meses_columnas:
            df_mes_marca_base = df_marca_anio[df_marca_anio['Mes_Num'] == m_num]
            
            # Filtros de marca aplicados a las muestras
            df_mes_marca_filtro = df_mes_marca_base.copy()
            df_anio_marca_filtro = df_marca_anio.copy()
            if marcas_prima_sel:
                if 'Marca' in df_mes_marca_filtro.columns:
                    df_mes_marca_filtro = df_mes_marca_filtro[df_mes_marca_filtro['Marca'].isin(marcas_prima_sel)]
                if 'Marca' in df_anio_marca_filtro.columns:
                    df_anio_marca_filtro = df_anio_marca_filtro[df_anio_marca_filtro['Marca'].isin(marcas_prima_sel)]
            
            # Condicional de corte de escala temporal e históricos
            es_escala_2025_post_mayo = (anio_prima_sel == 2025 and m_num >= 5)
            es_escala_2026_post_abril = (anio_prima_sel == 2026 and m_num >= 4)
            
            meta_llave1_umbral = 80.5 if es_escala_2025_post_mayo else 77.0
            meta_llave2_umbral = 88.0 if es_escala_2025_post_mayo else 86.3
            meta_llave5_umbral = 8 if es_escala_2025_post_mayo else 10
            
            if len(df_mes_marca_base) == 0:
                monto_puro_liquidado[m_num] = 0
                max_t_unit = 630000 if es_escala_2026_post_abril else (420000 if es_escala_2025_post_mayo else 540000)
                max_teorico_acumulado[m_num] = max_t_unit * personas_declaradas
                
                line_data_prima.append({
                    "Mes_Num": m_num, "Mes_Nombre": MESES_ES[m_num], "L1_Val": "-", "L1_OK": False,
                    "L2_Val": "-", "L2_OK": False, "L3_Val": "-", "L3_OK": False, "L5_Val": "0", "L5_OK": False,
                    "V_D1": 0, "V_D2": 0, "V_D3": 0, "V_D4": 0, "Suma_D_M": 0, "Pers": personas_declaradas, "Liq_S_M": 0,
                    "Es_2025": es_escala_2025_post_mayo, "Labels": ["🔹 Driver 1", "🔹 Driver 2", "🔹 Driver 3", "🔹 Driver 4"]
                })
                continue
                
            # --- LLAVE 1: CONTACTO POSTERIOR 6MM ---
            df_6mm_marca = df_anio_marca_filtro[(df_anio_marca_filtro['Mes_Num'] > (m_num - 6)) & (df_anio_marca_filtro['Mes_Num'] <= m_num)]
            tasa_6mm = 0.0
            ok_llave1 = False
            val_l1_display = "-"
            
            if "Q18 - Contactado" in df_6mm_marca.columns:
                serie_q18 = df_6mm_marca["Q18 - Contactado"].astype(str).str.strip()
                cant_si = len(serie_q18[serie_q18.str.lower() == 'sí']) + len(serie_q18[serie_q18.str.lower() == 'si'])
                cant_no = len(serie_q18[serie_q18.str.lower() == 'no'])
                total_validos_6mm = cant_si + cant_no
                if total_validos_6mm > 0:
                    tasa_6mm = round((cant_si / total_validos_6mm) * 100, 1)
                    ok_llave1 = (tasa_6mm >= meta_llave1_umbral)
                    val_l1_display = f"{tasa_6mm}%"
            
            # --- LLAVE 2: NPS MÍNIMO GLOBAL ---
            score_nps_mes, _, _, _ = calcular_metricas_nps(df_mes_marca_filtro, "Q2 - Recomendación - taller")
            ok_llave2 = (score_nps_mes >= meta_llave2_umbral)
            
            # --- LLAVE 3: TASA DE MAIL VÁLIDO ---
            pct_mail_val = 0.0
            ok_llave3 = False
            val_l3_display = "-"
            string_mes_buscar = f"{MESES_SHORT[m_num]} {anio_prima_sel}"
            
            if not df_email_llave_raw.empty:
                col_tasa_mail = next((c for c in df_email_llave_raw.columns if 'Tasa de Email Utilizable' in c), None)
                col_mes_ext = next((c for c in df_email_llave_raw.columns if c.lower() == 'mes'), None)
                col_marca_ext = next((c for c in df_email_llave_raw.columns if c.lower() == 'marca'), None)
                
                if col_tasa_mail and col_mes_ext:
                    df_row_mail = df_email_llave_raw[df_email_llave_raw[col_mes_ext].astype(str).str.strip().str.lower() == string_mes_buscar.lower()]
                    if marcas_prima_sel and col_marca_ext:
                        marcas_en_hoja = [m.lower() for m in marcas_prima_sel]
                        df_row_mail = df_row_mail[df_row_mail[col_marca_ext].astype(str).str.strip().str.lower().isin(marcas_en_hoja)]
                        
                    if not df_row_mail.empty:
                        tasas_lista = []
                        for _, row_m in df_row_mail.iterrows():
                            val_raw = row_m[col_tasa_mail]
                            if isinstance(val_raw, str):
                                val_raw = val_raw.replace('%', '').replace(',', '.').strip()
                            num_parsed = pd.to_numeric(val_raw, errors='coerce')
                            if pd.notnull(num_parsed):
                                val_final = num_parsed if num_parsed > 1.0 else num_parsed * 100
                                tasas_lista.append(val_final)
                        if tasas_lista:
                            pct_mail_val = round(sum(tasas_lista) / len(tasas_lista), 1)
                            ok_llave3 = (pct_mail_val >= 80.0)
                            val_l3_display = f"{pct_mail_val}%"
            
            # --- LLAVE 5: MUESTRA MÍNIMA ---
            total_encuestas_mes = len(df_mes_marca_filtro)
            ok_llave5 = (total_encuestas_mes >= meta_llave5_umbral)
            
            llaves_aprobadas_mes = ok_llave1 and ok_llave2 and ok_llave3 and ok_llave5
            
            # --- CÁLCULO INDEPENDIENTE DE DRIVERS CON ESCALAS DISCRIMINADAS POR MES ---
            monto_d1 = 0
            monto_d2 = 0
            monto_d3 = 0
            monto_d4 = 0
            
            if es_escala_2025_post_mayo:
                if score_nps_mes >= 93.5: monto_d1 = 210000
                elif score_nps_mes >= 89.8: monto_d1 = 160000
                score_q11, _, _, _ = calcular_metricas_nps(df_mes_marca_filtro, "Q11 - Explicación trabajo - costo")
                if score_q11 >= 94.0: monto_d2 = 105000
                elif score_q11 >= 89.3: monto_d2 = 80000
                score_q8, _, _, _ = calcular_metricas_nps(df_mes_marca_filtro, "Q8 - Competencia Asesor de Servicio")
                if score_q8 >= 95.5: monto_d3 = 52500
                elif score_q8 >= 93.3: monto_d3 = 40000
                score_q7, _, _, _ = calcular_metricas_nps(df_mes_marca_filtro, "Q7 - Cortesía y Amabilidad")
                if score_q7 >= 95.5: monto_d4 = 52500
                elif score_q7 >= 93.3: monto_d4 = 40000
                max_teorico_unitario = 420000
                labels_drivers = ["🔹 Recomendación (Q2)", "🔹 Q11 Explicación Trab. y Costo", "🔹 Q8 Competencia Asesor", "🔹 Q7 Cortesía y Amab. Asesor"]
            else:
                if not es_escala_2026_post_abril:
                    if score_nps_mes >= 93.5: monto_d1 = 270000
                    elif score_nps_mes >= 88.3: monto_d1 = 200000
                    score_q12, _, _, _ = calcular_metricas_nps(df_mes_marca_filtro, "Q12 - Calidad del trabajo")
                    if score_q12 >= 94.0: monto_d2 = 150000
                    elif score_q12 >= 87.8: monto_d2 = 120000
                    score_q7, _, _, _ = calcular_metricas_nps(df_mes_marca_filtro, "Q7 - Cortesía y Amabilidad")
                    if score_q7 >= 95.5: monto_d3 = 60000
                    elif score_q7 >= 91.8: monto_d3 = 40000
                    score_q19, _, _, _ = calcular_metricas_nps(df_mes_marca_filtro, "Q19 - Satisfacción con el Contacto")
                    if score_q19 >= 95.5: monto_d4 = 60000
                    elif score_q19 >= 91.8: monto_d4 = 40000
                    max_teorico_unitario = 540000
                else:
                    if score_nps_mes >= 93.5: monto_d1 = 310000
                    elif score_nps_mes >= 88.3: monto_d1 = 230000
                    score_q12, _, _, _ = calcular_metricas_nps(df_mes_marca_filtro, "Q12 - Calidad del trabajo")
                    if score_q12 >= 94.0: monto_d2 = 160000
                    elif score_q12 >= 87.8: monto_d2 = 140000
                    score_q7, _, _, _ = calcular_metricas_nps(df_mes_marca_filtro, "Q7 - Cortesía y Amabilidad")
                    if score_q7 >= 95.5: monto_d3 = 80000
                    elif score_q7 >= 91.8: monto_d3 = 50000
                    score_q19, _, _, _ = calcular_metricas_nps(df_mes_marca_filtro, "Q19 - Satisfacción con el Contacto")
                    if score_q19 >= 95.5: monto_d4 = 80000
                    elif score_q19 >= 91.8: monto_d4 = 50000
                    max_teorico_unitario = 630000
                labels_drivers = ["🔹 Recomendación (Q2)", "🔹 Q12 Calidad de Trabajo", "🔹 Q7 Cortesía y Amabilidad", "🔹 Q19 Satisfacción de Contacto"]
                
            suma_drivers_mes = (monto_d1 + monto_d2 + monto_d3 + monto_d4) if llaves_aprobadas_mes else 0
            total_liq_sector_mes = suma_drivers_mes * personas_declaradas
            
            monto_puro_liquidado[m_num] = total_liq_sector_mes
            max_teorico_acumulado[m_num] = max_teorico_unitario * personas_declaradas
            
            line_data_prima.append({
                "Mes_Num": m_num, "Mes_Nombre": MESES_ES[m_num],
                "L1_Val": val_l1_display, "L1_OK": ok_llave1,
                "L2_Val": f"{score_nps_mes}%", "L2_OK": ok_llave2,
                "L3_Val": val_l3_display, "L3_OK": ok_llave3,
                "Es_2025": es_escala_2025_post_mayo,
                "L5_Val": str(total_encuestas_mes), "L5_OK": ok_llave5,
                "V_D1": monto_d1, "V_D2": monto_d2, "V_D3": monto_d3, "V_D4": monto_d4,
                "Suma_D_M": suma_drivers_mes, "Pers": personas_declaradas, "Liq_S_M": total_liq_sector_mes,
                "Labels": labels_drivers
            })

        # --- CONSOLIDACIÓN FINAL E INYECCIÓN DE ALERTAS PREDICTIVAS ---
        lista_render_completa = []
        for d in line_data_prima:
            m = d["Mes_Num"]
            monto_bonus_trimestral = 0
            str_bonus_display = "-"
            color_bonus_html = "color:#64748B;"
            aplica_fila_bonus = (m in [3, 6, 9, 12])
            
            indices_trimestre = [m - (m-1)%3 + i for i in range(3)]
            meses_acumulados_hasta_ahora = [idx for idx in indices_trimestre if idx <= m]
            
            df_trim_encuestas = df_marca_anio[df_marca_anio['Mes_Num'].isin(meses_acumulados_hasta_ahora)]
            if marcas_prima_sel and 'Marca' in df_trim_encuestas.columns:
                df_trim_encuestas = df_trim_encuestas[df_trim_encuestas['Marca'].isin(marcas_prima_sel)]
                
            if len(df_trim_encuestas) > 0:
                nps_trim_q2, _, _, _ = calcular_metricas_nps(df_trim_encuestas, "Q2 - Recomendación - taller")
                
                if d["Es_2025"]:
                    nps_trim_q11, _, _, _ = calcular_metricas_nps(df_trim_encuestas, "Q11 - Explicación trabajo - costo")
                    nps_trim_q8, _, _, _ = calcular_metricas_nps(df_trim_encuestas, "Q8 - Competencia Asesor de Servicio")
                    nps_trim_q7, _, _, _ = calcular_metricas_nps(df_trim_encuestas, "Q7 - Cortesía y Amabilidad")
                    cumple_acum_parcial = (nps_trim_q2 >= 89.8 and nps_trim_q11 >= 89.3 and nps_trim_q8 >= 93.3 and nps_trim_q7 >= 93.3)
                    indicador_falla = "Q2" if nps_trim_q2 < 89.8 else ("Q11" if nps_trim_q11 < 89.3 else ("Q8" if nps_trim_q8 < 93.3 else "Q7"))
                else:
                    nps_trim_q12, _, _, _ = calcular_metricas_nps(df_trim_encuestas, "Q12 - Calidad del trabajo")
                    nps_trim_q7, _, _, _ = calcular_metricas_nps(df_trim_encuestas, "Q7 - Cortesía y Amabilidad")
                    nps_trim_q19, _, _, _ = calcular_metricas_nps(df_trim_encuestas, "Q19 - Satisfacción con el Contacto")
                    cumple_acum_parcial = (nps_trim_q2 >= 88.3 and nps_trim_q12 >= 87.8 and nps_trim_q7 >= 91.8 and nps_trim_q19 >= 91.8)
                    indicador_falla = "Q2" if nps_trim_q2 < 88.3 else ("Q12" if nps_trim_q12 < 87.8 else ("Q7" if nps_trim_q7 < 91.8 else "Q19"))
                
                if cumple_acum_parcial:
                    if aplica_fila_bonus:
                        suma_primas_puras_trim = sum(monto_puro_liquidado.get(idx, 0) for idx in indices_trimestre)
                        monto_bonus_trimestral = round(suma_primas_puras_trim * 0.05, 0)
                        str_bonus_display = f"${monto_bonus_trimestral:,.0f}".replace(",", ".")
                        color_bonus_html = "background-color: #D4EDDA; color: #155724; font-weight: bold;"
                    else:
                        str_bonus_display = "🟢 En Camino"
                        color_bonus_html = "background-color: #E6FFFA; color: #047857; font-size: 11px; font-weight: bold;"
                else:
                    if aplica_fila_bonus:
                        str_bonus_display = "$0"
                        color_bonus_html = "background-color: #F8D7DA; color: #721C24; font-weight: bold;"
                    else:
                        str_bonus_display = f"🔴 Riesgo ({indicador_falla})"
                        color_bonus_html = "background-color: #FFF5F5; color: #E53E3E; font-size: 11px; font-weight: bold;"

            final_recalculado_mes = d["Liq_S_M"] + monto_bonus_trimestral
            perdida_mes_calc = max(0, max_teorico_acumulado[m] - final_recalculado_mes)
            pct_cumplimiento = round((d["Liq_S_M"] / max_teorico_acumulado[m] * 100), 1) if max_teorico_acumulado[m] > 0 else 0.0
            
            lista_render_completa.append({
                **d, "Bonus_Display": str_bonus_display, "Color_B_Style": color_bonus_html, 
                "Pct_Cumpl": pct_cumplimiento, "Final_M": final_recalculado_mes, "Perdida_M": perdida_mes_calc
            })

        # Renderizado de la tabla principal HTML
        if lista_render_completa:
            html_tabla = """
            <table style='width:100%; border-collapse: collapse; font-family: Arial, sans-serif; text-align: center; font-size: 13px;'>
                <thead>
                    <tr style='background-color: #1E293B; color: white;'>
                        <th style='padding: 10px; border: 1px solid #E2E8F0; text-align: left; font-size: 14px;'>Estructura de Control y Prima Anual</th>
            """
            for d in lista_render_completa:
                html_tabla += f"<th style='padding: 10px; border: 1px solid #E2E8F0;'>{d['Mes_Nombre']}</th>"
            html_tabla += "</tr></thead><tbody>"
            
            html_tabla += "<tr style='background-color: #EDF2F7;'><td colspan='" + str(len(lista_render_completa)+1) + "' style='text-align:left; padding:8px; font-weight:bold; color:#2D3748;'>🔑 UMBRALES Y LLAVES MAESTRAS (POSTVENTA)</td></tr>"
            
            lbl_l1 = "📞 Contacto Posterior 6MM (Meta &ge; 80.5%)" if es_filtro_2025 else "📞 Contacto Posterior 6MM (Meta &ge; 77%)"
            html_tabla += f"<tr><td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left;'>{lbl_l1}</td>"
            for d in lista_render_completa:
                bg = "#D4EDDA; color: #155724;" if d["L1_OK"] else "#F8D7DA; color: #721C24;"
                if d["L1_Val"] == "-": bg = "#F1F5F9; color: #64748B;"
                html_tabla += f"<td style='padding: 10px; border: 1px solid #E2E8F0; background-color: {bg} font-weight: bold;'>{d['L1_Val']}</td>"
            html_tabla += "</tr>"
            
            lbl_l2 = "🏢 NPS Mínimo Taller (Meta &ge; 88%)" if es_filtro_2025 else "🏢 NPS Mínimo Global (Meta &ge; 86.3%)"
            html_tabla += f"<tr><td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left;'>{lbl_l2}</td>"
            for d in lista_render_completa:
                bg = "#D4EDDA; color: #155724;" if d["L2_OK"] else "#F8D7DA; color: #721C24;"
                if d["L2_Val"] == "-": bg = "#F1F5F9; color: #64748B;"
                html_tabla += f"<td style='padding: 10px; border: 1px solid #E2E8F0; background-color: {bg} font-weight: bold;'>{d['L2_Val']}</td>"
            html_tabla += "</tr>"
            
            html_tabla += "<tr><td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left;'>✉️ Tasa de Mail Válido (Meta &ge; 80%)</td>"
            for d in lista_render_completa:
                bg = "#D4EDDA; color: #155724;" if d["L3_OK"] else "#F8D7DA; color: #721C24;"
                if d["L3_Val"] == "-": bg = "#F1F5F9; color: #64748B;"
                html_tabla += f"<td style='padding: 10px; border: 1px solid #E2E8F0; background-color: {bg} font-weight: bold;'>{d['L3_Val']}</td>"
            html_tabla += "</tr>"
                
            lbl_l5 = "📊 Muestra Mínima Mensual (Meta &ge; 8 Rps.)" if es_filtro_2025 else "📊 Muestra Mínima Mensual (Meta &ge; 10 Rps.)"
            html_tabla += f"<tr><td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left;'>{lbl_l5}</td>"
            for d in lista_render_completa:
                bg = "#D4EDDA; color: #155724;" if d["L5_OK"] else "#F8D7DA; color: #721C24;"
                if d["L5_Val"] == "-": bg = "#F1F5F9; color: #64748B;"
                html_tabla += f"<td style='padding: 10px; border: 1px solid #E2E8F0; background-color: {bg} font-weight: bold;'>{d['L5_Val']}</td>"
            html_tabla += "</tr>"
            
            html_tabla += "<tr style='background-color: #EDF2F7;'><td colspan='" + str(len(lista_render_completa)+1) + "' style='text-align:left; padding:8px; font-weight:bold; color:#2D3748;'>🎯 INCENTIVOS POR DRIVERS COMERCIALES (VALOR INDIVIDUAL)</td></tr>"
            
            for row_idx in range(4):
                html_tabla += f"<tr><td style='padding:10px; border:1px solid #E2E8F0; text-align:left;'>{lista_render_completa[0]['Labels'][row_idx]}</td>"
                for d in lista_render_completa:
                    m_val = d["V_D1"] if row_idx==0 else (d["V_D2"] if row_idx==1 else (d["V_D3"] if row_idx==2 else d["V_D4"]))
                    html_tabla += f"<td style='padding:10px; border:1px solid #E2E8F0; color:#475569;'>${m_val:,.0f}</td>".replace("$0", "$0")
                html_tabla += "</tr>"
            
            html_tabla += "<tr style='background-color: #F8FAFC; border-top: 2px solid #CBD5E1;'>"
            html_tabla += "<td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left; font-weight: bold; color:#0F172A;'>💰 SUMA DRIVERS (Valor Unitario)</td>"
            for d in lista_render_completa: html_tabla += f"<td style='padding: 10px; border: 1px solid #E2E8F0; font-weight: bold; color:#1E3A8A;'>${d['Suma_D_M']:,.0f}</td>".replace("$0", "$0")
            html_tabla += "</tr>"
            
            html_tabla += "<tr style='background-color: #F1F5F9; font-weight: bold;'>"
            html_tabla += "<td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left; color:#475569;'>📊 Eficiencia Comercial del Mes</td>"
            for d in lista_render_completa:
                color_pct = "#10B981" if d["Pct_Cumpl"] >= 90 else ("#F59E0B" if d["Pct_Cumpl"] >= 50 else "#EF4444")
                html_tabla += f"<td style='padding: 10px; border: 1px solid #E2E8F0; color:{color_pct};'>{d['Pct_Cumpl']:.1f}%</td>"
            html_tabla += "</tr>"
            
            html_tabla += "<tr><td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left; font-weight: bold; color:#475569;'>👥 Personal Declarado</td>"
            for d in lista_render_completa: html_tabla += f"<td style='padding: 10px; border: 1px solid #E2E8F0; color:#475569;'>{d['Pers']}</td>"
            html_tabla += "</tr>"
            
            html_tabla += "<tr><td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left; font-weight: bold; color:#475569;'>📈 Liquidación Total Sector</td>"
            for d in lista_render_completa: html_tabla += f"<td style='padding: 10px; border: 1px solid #E2E8F0; color:#475569; font-weight: 500;'>${d['Liq_S_M']:,.0f}</td>".replace("$0", "$0")
            html_tabla += "</tr>"
            
            html_tabla += "<tr style='background-color: #FDF2F8; color: #9D174D;'>"
            html_tabla += "<td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left; font-weight: bold;'>⭐ Bonus Trimestral (5%) [Predictivo]</td>"
            for d in lista_render_completa:
                html_tabla += f"<td style='padding: 10px; border: 1px solid #E2E8F0; {d['Color_B_Style']}'>{d['Bonus_Display']}</td>"
            html_tabla += "</tr>"
            
            html_tabla += "<tr style='background-color: #D1FAE5; border-top: 2px solid #10B981;'>"
            html_tabla += "<td style='padding: 12px; border: 1px solid #E2E8F0; text-align: left; font-weight: bold; color:#065F46; font-size: 14px;'>💵 LIQUIDACIÓN FINAL CON BONUS</td>"
            for d in lista_render_completa: html_tabla += f"<td style='padding: 12px; border: 1px solid #E2E8F0; font-weight: bold; color:#047857; font-size: 14px;'>${d['Final_M']:,.0f}</td>".replace("$0", "$0")
            html_tabla += "</tr>"
            
            html_tabla += "</tbody></table>"
            st.markdown(html_tabla, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # ==============================================================================
            # FILTROS Y TARJETAS KPI DE FLUJO DE CAJA INDEPENDIENTES (CON LA 4TA TARJETA ORDENADA)
            # ==============================================================================
            st.markdown("---")
            st.markdown("#### 💵 Control de Flujo de Caja y Auditoría de Pagos Recibidos")
            st.markdown("<p style='font-size: 13px; color: #64748B; margin-top:-10px;'>Considerando el desfasaje de las transferencias de la marca, utiliza estos selectores para auditar los cobros reales.</p>", unsafe_allow_html=True)
            
            # Cálculo Automático a 45 días del mes cobrado por defecto
            fecha_actual = datetime.date.today()
            fecha_cobro = fecha_actual - datetime.timedelta(days=45)
            mes_default_nombre = MESES_ES.get(fecha_cobro.month, "Enero")
            
            meses_nombres_presentes = [d["Mes_Nombre"] for d in lista_render_completa if d["L1_Val"] != "-"]
            opciones_meses = list(MESES_ES.values())
            default_val = [mes_default_nombre] if mes_default_nombre in meses_nombres_presentes else []
            
            col_sel_c1, col_sel_c2 = st.columns(2)
            with col_sel_c1:
                anio_caja_sel = st.selectbox("Año de Gestión (Flujo Caja):", options=anios_disponibles_prima, key="sb_anio_caja")
            with col_sel_c2:
                meses_caja_sel = st.multiselect("Meses cobrados:", options=opciones_meses, default=default_val, key="ms_meses_caja")
            
            monto_cobrado_efectivo = 0.0
            monto_pendiente_prevision = 0.0
            monto_perdido_acumulado = 0.0
            
            montos_grafico_alcanzado = []
            montos_grafico_maximo = []
            montos_grafico_perdida = []
            meses_grafico_nombres = []
            
            for d in lista_render_completa:
                if d["L1_Val"] != "-": 
                    final_mes = d["Final_M"]
                    max_teorico = max_teorico_acumulado.get(d["Mes_Num"], 0)
                    perdida_mes_calc = d["Perdida_M"]
                    
                    if d["Mes_Nombre"] in meses_caja_sel:
                        monto_cobrado_efectivo += final_mes
                        monto_perdido_acumulado += perdida_mes_calc
                    else:
                        monto_pendiente_prevision += final_mes
                        
                    montos_grafico_alcanzado.append(final_mes)
                    montos_grafico_maximo.append(max_teorico)
                    montos_grafico_perdida.append(perdida_mes_calc)
                    meses_grafico_nombres.append(d["Mes_Nombre"])
            
            # Calculo para la 3ra tarjeta: % de Prima Alcanzado (Solo de los meses cobrados)
            monto_maximo_seleccionados = monto_cobrado_efectivo + monto_perdido_acumulado
            pct_alcanzado_cobrados = (monto_cobrado_efectivo / monto_maximo_seleccionados * 100) if monto_maximo_seleccionados > 0 else 0.0
            
            str_cobrado = f"${monto_cobrado_efectivo:,.0f}".replace(",", ".")
            str_perdido = f"${monto_perdido_acumulado:,.0f}".replace(",", ".")
            str_pct_alcanzado = f"{pct_alcanzado_cobrados:.1f}%"
            str_pendiente = f"${monto_pendiente_prevision:,.0f}".replace(",", ".")
            
            # Generación de 4 columnas para las KPI cards en el orden solicitado
            col_c_1, col_c_2, col_c_3, col_c_4 = st.columns(4)
            
            # 1. MONTO COBRADO
            with col_c_1:
                st.markdown(f"""
                    <div class='kpi-card' style='border-left: 5px solid #10B981; padding: 15px;'>
                        <div class='kpi-label'>💰 MONTO COBRADO</div>
                        <div class='kpi-value' style='color:#065F46; font-size: 26px;'>{str_cobrado}</div>
                        <div class='kpi-sub' style='color:#10B981; font-size: 11px;'>✓ En meses seleccionados</div>
                    </div>
                """, unsafe_allow_html=True)
                
            # 2. MONTO PERDIDO
            with col_c_2:
                st.markdown(f"""
                    <div class='kpi-card' style='border-left: 5px solid #EF4444; padding: 15px;'>
                        <div class='kpi-label'>📉 MONTO PERDIDO (NO ALCANZADO)</div>
                        <div class='kpi-value' style='color:#B91C1C; font-size: 26px;'>{str_perdido}</div>
                        <div class='kpi-sub' style='color:#EF4444; font-size: 11px;'>⚠ No alcanzado en cobrados</div>
                    </div>
                """, unsafe_allow_html=True)
                
            # 3. % DE PRIMA ALCANZADO
            with col_c_3:
                st.markdown(f"""
                    <div class='kpi-card' style='border-left: 5px solid #8B5CF6; padding: 15px;'>
                        <div class='kpi-label'>📊 % DE PRIMA ALCANZADO</div>
                        <div class='kpi-value' style='color:#5B21B6; font-size: 26px;'>{str_pct_alcanzado}</div>
                        <div class='kpi-sub' style='color:#8B5CF6; font-size: 11px;'>⚖ Eficiencia de lo cobrado</div>
                    </div>
                """, unsafe_allow_html=True)
                
            # 4. PREVISIÓN PENDIENTE
            with col_c_4:
                st.markdown(f"""
                    <div class='kpi-card' style='border-left: 5px solid #3B82F6; padding: 15px;'>
                        <div class='kpi-label'>⏳ PREVISIÓN PENDIENTE</div>
                        <div class='kpi-value' style='color:#1D4ED8; font-size: 26px;'>{str_pendiente}</div>
                        <div class='kpi-sub' style='color:#3B82F6; font-size: 11px;'>ℹ Meses con datos sin cobrar</div>
                    </div>
                """, unsafe_allow_html=True)
            
            # --- RENDERIZADO DEL GRÁFICO DE LÍNEAS CON ÁREAS SOWBREADAS CONTINUAS ---
            if meses_grafico_nombres:
                st.markdown("<br>", unsafe_allow_html=True)
                fig_econ = go.Figure()
                
                # 1. Área de Ganancia ($ Alcanzado): Sombreado verde claro completo por debajo hasta el piso 0
                fig_econ.add_trace(go.Scatter(
                    x=meses_grafico_nombres, y=montos_grafico_alcanzado,
                    mode='lines+markers+text', name='$ Alcanzado a Cobrar',
                    line=dict(color='#10B981', width=4),
                    marker=dict(size=8, color='#10B981'),
                    text=[f"${v:,.0f}".replace(",", ".") for v in montos_grafico_alcanzado],
                    textposition='top center',
                    fill='tozeroy',
                    fillcolor='rgba(34, 197, 94, 0.25)', # Verde Claro traslúcido
                    hovertemplate='<b>%{x}</b><br>Alcanzado: %{y:$,.0f}<extra></extra>'
                ))
                
                # 2. Referencia de Techo Comercial ($ Monto Máximo)
                fig_econ.add_trace(go.Scatter(
                    x=meses_grafico_nombres, y=montos_grafico_maximo,
                    mode='lines', name='$ Monto Máximo',
                    line=dict(color='#94A3B8', width=2, dash='dash'),
                    hoverinfo='skip'
                ))
                
                # 3. Área de Pérdida ($ de Pérdida): Sombreado rojo claro completo por debajo hasta el piso 0
                fig_econ.add_trace(go.Scatter(
                    x=meses_grafico_nombres, y=montos_grafico_perdida,
                    mode='lines+markers', name='$ de Pérdida',
                    line=dict(color='#EF4444', width=2),
                    marker=dict(size=6, color='#EF4444'),
                    fill='tozeroy',
                    fillcolor='rgba(239, 68, 68, 0.22)', # Rojo Claro traslúcido por debajo
                    hovertemplate='<b>%{x}</b><br>Pérdida Nominal: %{y:$,.0f}<extra></extra>'
                ))
                
                fig_econ.update_layout(
                    hovermode='x unified',
                    yaxis=dict(title='Monto en Pesos ($)', showgrid=True, gridcolor='#E2E8F0'),
                    xaxis=dict(showgrid=False),
                    margin=dict(l=40, r=40, t=20, b=40),
                    height=420,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_econ, use_container_width=True)
    else:
        st.info("No se localizó un historial anual para estructurar la matriz de llaves.")
