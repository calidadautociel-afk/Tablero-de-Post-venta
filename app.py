import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import datetime
from fpdf import FPDF
import io

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
    
    .vertical-divider {
        border-left: 2px solid #E2E8F0;
        height: 100%;
        margin-left: 10px;
        margin-right: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# URLs públicas de Google Sheets
SHEET_URL_MARCA = "https://docs.google.com/spreadsheets/d/1kMzEHI4uuEWdIG7NfjgVkVVqOSw8ga9p_4-1i5ZN5wo/export?format=csv&gid=754740343"
SHEET_URL_INTERNA = "https://docs.google.com/spreadsheets/d/1kMzEHI4uuEWdIG7NfjgVkVVqOSw8ga9p_4-1i5ZN5wo/export?format=csv&gid=1128023355"
SHEET_URL_EMAIL_LLAVE = "https://docs.google.com/spreadsheets/d/1kMzEHI4uuEWdIG7NfjgVkVVqOSw8ga9p_4-1i5ZN5wo/export?format=csv&gid=1727842086"
SHEET_URL_RECLAMOS = "https://docs.google.com/spreadsheets/d/1kMzEHI4uuEWdIG7NfjgVkVVqOSw8ga9p_4-1i5ZN5wo/export?format=csv&gid=1460120243"

# Mapeo de meses en español
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}
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
def load_simple_sheet(url):
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    return df

try:
    df_marca_raw = load_data(SHEET_URL_MARCA)
    df_int_raw = load_data(SHEET_URL_INTERNA)
    df_email_llave_raw = load_simple_sheet(SHEET_URL_EMAIL_LLAVE)
    df_reclamos_raw = load_simple_sheet(SHEET_URL_RECLAMOS)
except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")
    st.stop()

# --- BÚSQUEDA DINÁMICA DE COLUMNAS Q4 Y Q13 (Base Marca) ---
col_q4 = next((col for col in df_marca_raw.columns if 'Q4' in col and 'Motivo' in col), None)
col_q13 = next((col for col in df_marca_raw.columns if 'Q13' in col), "Q13 - Trabajo realizado en primera visita")

# --- FUNCIÓN DE FILTRADO LOCAL POR PESTAÑA ---
def render_filtros_pestaña(df_m_raw, df_i_raw, key_prefix):
    hoy = datetime.date.today()
    mes_actual_nombre = MESES_ES.get(hoy.month, "Enero")
    año_actual = hoy.year

    # Listas disponibles extraídas de los datos
    anios_disp = sorted(df_m_raw['Año'].unique(), reverse=True) if 'Año' in df_m_raw.columns else [año_actual]
    meses_disp = list(MESES_ES.values())
    marcas_disp = sorted(df_m_raw['Marca'].dropna().unique()) if 'Marca' in df_m_raw.columns else []

    # --- LÓGICA DE VALORES POR DEFECTO ---
    default_anio = [año_actual] if año_actual in anios_disp else (anios_disp[:1] if anios_disp else [2026])
    
    meses_existentes = df_m_raw[df_m_raw['Año'] == default_anio[0]]['Mes'].unique() if default_anio else []
    default_mes = [mes_actual_nombre] if mes_actual_nombre in meses_existentes else (meses_existentes[:1].tolist() if len(meses_existentes)>0 else [mes_actual_nombre])
    
    default_marca = [m for m in marcas_disp if "peugeot" in str(m).lower()]
    if not default_marca and marcas_disp:
        default_marca = marcas_disp[:1]

    if f'{key_prefix}_anio' not in st.session_state:
        st.session_state[f'{key_prefix}_anio'] = default_anio
    if f'{key_prefix}_mes' not in st.session_state:
        st.session_state[f'{key_prefix}_mes'] = default_mes
    if f'{key_prefix}_marca' not in st.session_state:
        st.session_state[f'{key_prefix}_marca'] = default_marca

    titulo_unico = f"⚙️ Filtros de visualización ({key_prefix.replace('_', ' ').title()})"

    with st.expander(titulo_unico, expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_años = st.multiselect("Seleccione Año", anios_disp, key=f'{key_prefix}_anio')
        with c2:
            sel_meses = st.multiselect("Seleccione Mes(es)", meses_disp, key=f'{key_prefix}_mes')
        with c3:
            sel_marcas = st.multiselect("Seleccione Marca", marcas_disp, key=f'{key_prefix}_marca')

    df_m_filt = df_m_raw[df_m_raw['Año'].isin(sel_años) & df_m_raw['Mes'].isin(sel_meses)]
    df_i_filt = df_i_raw[df_i_raw['Año'].isin(sel_años) & df_i_raw['Mes'].isin(sel_meses)]

    if sel_marcas:
        if 'Marca' in df_m_filt.columns: df_m_filt = df_m_filt[df_m_filt['Marca'].isin(sel_marcas)]
        if 'Marca' in df_i_filt.columns: df_i_filt = df_i_filt[df_i_filt['Marca'].isin(sel_marcas)]

    return df_m_filt, df_i_filt, sel_meses

# --- CÁLCULOS MÉTRICAS ---
def calcular_metricas_nps(df, columna):
    if columna not in df.columns: return 0.0, 0, 0, 0
    
    mapeo_textos = {
        'muy satisfecho': 10, 'satisfecho': 8, 'insatisfecho': 1, 'muy insatisfecho': 1,
        'sí': 10, 'si': 10, 'no': 1,
        'superó mis expectativas': 10, 'cumplió mis expectativas': 8, 'no cumplió mis expectativas': 1
    }
    
    if df[columna].dtype == object:
        valores_procesados = df[columna].astype(str).str.strip().str.lower().map(mapeo_textos).fillna(pd.to_numeric(df[columna], errors='coerce'))
    else:
        valores_procesados = pd.to_numeric(df[columna], errors='coerce')
        
    valores = valores_procesados.dropna()
    total = len(valores)
    if total == 0: return 0.0, 0, 0, 0
    
    promotores = len(valores[valores >= 9])
    detractores = len(valores[valores <= 6])
    neutros = len(valores[(valores >= 7) & (valores <= 8)])
    
    pct_promotores = (promotores / total) * 100
    pct_detractores = (detractores / total) * 100
    nps_score = max(0.0, round(pct_promotores - pct_detractores, 1))
    
    return nps_score, promotores, neutros, detractores

def calcular_promedio(df, columna):
    if columna not in df.columns: return 0.0
    s_limpia = df[columna].astype(str).str.replace(',', '.') if df[columna].dtype == object else df[columna]
    valores = pd.to_numeric(s_limpia, errors='coerce').dropna()
    valores = valores[(valores > 0) & (valores <= 10)]
    if len(valores) == 0: return 0.0
    return round(valores.mean() * 10, 1)

# --- VELOCÍMETROS (ACTUALIZADO AL FORMATO VENTAS) ---
def crear_velocimetro(score, titulo, mini=False, is_promedio=False):
    color_bar = '#22C55E' if score >= 90 else ('#EAB308' if score >= (80 if is_promedio else 70) else '#EF4444')
    font_size = 20 if mini else 42
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score, 
        number={'suffix': "%", 'font': {'size': font_size, 'color': '#1E293B'}}, 
        gauge={
            'axis': {
                'range': [0, 100], 
                'showticklabels': False,
                'tickvals': [0, 25, 50, 75, 100],
                'tickwidth': 2,
                'tickcolor': '#555555',
                'ticklen': 5
            }, 
            'bar': {'color': color_bar, 'thickness': 0.25}, 
            'bgcolor': "#E6E9EC", 
            'borderwidth': 0
        }
    ))
    height_chart = 130 if mini else 240
    margin_bottom = 0 if mini else 10
    fig.update_layout(
        title={'text': f"<b>{titulo}</b>", 'y': 0.85, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top', 'font': {'size': 12 if mini else 14, 'color': '#475569'}},
        margin=dict(l=20, r=20, t=40, b=margin_bottom), height=height_chart, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# --- GRÁFICOS DE TORTA ---
def crear_torta(df, columna, titulo):
    if columna not in df.columns or df[columna].dropna().empty:
        fig = go.Figure()
        fig.update_layout(
            title={'text': f"<b>{titulo}</b><br><span style='font-size:11px;color:#94A3B8;font-weight:normal;'>Sin datos en este período</span>", 'x': 0.5, 'y': 0.5, 'xanchor': 'center', 'yanchor': 'middle', 'font': {'size': 12, 'color': '#475569'}}, 
            height=260, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig
        
    datos = df[columna].value_counts()
    
    fig = go.Figure(data=[go.Pie(
        labels=datos.index, 
        values=datos.values, 
        hole=.35, 
        textinfo='value+percent', 
        textposition='inside', 
        insidetextorientation='radial'
    )])
    
    fig.update_layout(
        title={'text': f"<b>{titulo}</b>", 'x': 0.5, 'y': 0.95, 'xanchor': 'center', 'yanchor': 'top', 'font': {'size': 13, 'color': '#475569'}}, 
        margin=dict(l=10, r=10, t=50, b=30), 
        height=280, 
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5, font=dict(size=10)),
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# --- FUNCIÓN GENERADORA DE REPORTE PDF ---
def generar_reporte_pdf_bytes(df_m, df_i, meses_seleccionados):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, "REPORTE CONSOLIDADO DE CALIDAD POSVENTA", ln=True, align="C")
    
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(100, 116, 139)
    meses_str = ", ".join(meses_seleccionados) if meses_seleccionados else "Todos"
    pdf.cell(0, 6, f"Periodo: {meses_str} | Empresa: Autociel", ln=True, align="C")
    pdf.ln(5)
    pdf.set_draw_color(226, 232, 240)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)
    
    # SECCIÓN 1
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 8, "1. Monitor Global Comparativo", ln=True)
    pdf.ln(2)
    
    score_q1, p_q1, n_q1, d_q1 = calcular_metricas_nps(df_m, "Q1 - Satisfacción general")
    score_q2, p_q2, n_q2, d_q2 = calcular_metricas_nps(df_m, "Q2 - Recomendación - taller")
    prom_int = calcular_promedio(df_i, "Promedio")
    score_int_nps, p_i, n_i, d_i = calcular_metricas_nps(df_i, "1-NPS")
    
    fig_q1 = crear_velocimetro(score_q1, "SATISFACCION MARCA")
    fig_q2 = crear_velocimetro(score_q2, "RECOMENDACION MARCA")
    fig_int_prom = crear_velocimetro(prom_int, "SATISFACCION INTERNA", is_promedio=True)
    fig_int_nps = crear_velocimetro(score_int_nps, "RECOMENDACION INTERNA")
    
    img_q1 = io.BytesIO(fig_q1.to_image(format="png", width=400, height=250))
    img_q2 = io.BytesIO(fig_q2.to_image(format="png", width=400, height=250))
    img_int_prom = io.BytesIO(fig_int_prom.to_image(format="png", width=400, height=250))
    img_int_nps = io.BytesIO(fig_int_nps.to_image(format="png", width=400, height=250))
    
    y_actual = pdf.get_y()
    pdf.image(img_q1, x=15, y=y_actual, w=85)
    pdf.image(img_q2, x=105, y=y_actual, w=85)
    pdf.ln(50)
    
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(90, 5, f"Muestra: {p_q1+n_q1+d_q1} | Prom: {p_q1} | Neu: {n_q1} | Det: {d_q1}", align="C")
    pdf.cell(90, 5, f"Muestra: {p_q2+n_q2+d_q2} | Prom: {p_q2} | Neu: {n_q2} | Det: {d_q2}", align="C", ln=True)
    pdf.ln(5)

    y_actual = pdf.get_y()
    pdf.image(img_int_prom, x=15, y=y_actual, w=85)
    pdf.image(img_int_nps, x=105, y=y_actual, w=85)
    pdf.ln(50)
    
    pdf.cell(90, 5, "Promedio s/ encuestas", align="C")
    pdf.cell(90, 5, f"Muestra: {p_i+n_i+d_i} | Prom: {p_i} | Neu: {n_i} | Det: {d_i}", align="C", ln=True)
    pdf.ln(10)
    
    # SECCIÓN 2
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, "2. Ranking Oficial de Asesores (Base Marca)", ln=True)
    pdf.ln(2)
    
    col_asesor_key = next((col for col in df_m.columns if 'Asesor' in col), None)
    if col_asesor_key:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(55, 7, "Asesor de Servicio", border=1, fill=True)
        pdf.cell(18, 7, "Muestra", border=1, fill=True, align="C")
        pdf.cell(28, 7, "NPS Q2 (Rec.)", border=1, fill=True, align="C")
        pdf.cell(28, 7, "NPS Q7 (Cort.)", border=1, fill=True, align="C")
        pdf.cell(61, 7, "Estado Meta 94%", border=1, fill=True, align="C", ln=True)
        
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(15, 23, 42)
        
        for p_asesor in df_m[col_asesor_key].dropna().unique():
            df_ase = df_m[df_m[col_asesor_key] == p_asesor]
            nps_q2, p_q2, n_q2, d_q2 = calcular_metricas_nps(df_ase, "Q2 - Recomendación - taller")
            nps_q7, _, _, _ = calcular_metricas_nps(df_ase, "Q7 - Cortesía y Amabilidad")
            
            t_validos = p_q2 + n_q2 + d_q2
            if nps_q2 >= 94.0:
                meta_str = "Alcanzado"
            elif t_validos > 0:
                faltantes = math.ceil((94 * t_validos - 100 * (p_q2 - d_q2)) / 6.0)
                meta_str = f"Faltan {max(0, faltantes)} Prom."
            else:
                meta_str = "Sin datos"
                
            pdf.cell(55, 7, str(p_asesor)[:28], border=1)
            pdf.cell(18, 7, str(len(df_ase)), border=1, align="C")
            pdf.cell(28, 7, f"{nps_q2}%", border=1, align="C")
            pdf.cell(28, 7, f"{nps_q7}%", border=1, align="C")
            pdf.cell(61, 7, meta_str, border=1, align="C", ln=True)
    pdf.ln(6)
    
    # SECCIÓN 3
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(219, 68, 68)
    pdf.cell(0, 8, "3. Alertas Detractoras Recientes (<= 6)", ln=True)
    pdf.ln(2)
    
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(15, 23, 42)
    
    if "Q1 - Satisfacción general" in df_m.columns and "Q2 - Recomendación - taller" in df_m.columns:
        q1_num = pd.to_numeric(df_m["Q1 - Satisfacción general"], errors='coerce')
        q2_num = pd.to_numeric(df_m["Q2 - Recomendación - taller"], errors='coerce')
        df_detractores = df_m[(q1_num <= 6) | (q2_num <= 6)]
        
        if len(df_detractores) > 0:
            contador = 0
            for idx, row in df_detractores.iterrows():
                if contador >= 6:
                    pdf.cell(0, 6, "... Existen mas alertas en la plataforma web ...", ln=True, align="C")
                    break
                verb = str(row.get("Q3 - Verbalización", "Sin comentarios")).replace("\n", " ").strip()
                if verb == "nan" or verb == "": verb = "Sin comentarios registrados."
                ase_name = str(row.get(col_asesor_key, "N/A"))
                pdf.multi_cell(0, 5, f"- Asesor: {ase_name} | Q1: {row.get('Q1 - Satisfacción general')} | Q2: {row.get('Q2 - Recomendación - taller')}\n  Comentario: {verb[:150]}", border='B')
                pdf.ln(1)
                contador += 1
        else:
            pdf.set_text_color(34, 197, 94)
            pdf.cell(0, 7, "Excelente: No se detectan clientes detractores.", ln=True)
            
    return bytes(pdf.output())   
# ==============================================================================
# TÍTULO PRINCIPAL Y REPORTE CONSOLIDADO
# ==============================================================================
st.markdown("<h1 style='font-size: 36px; color: #1E293B; display: flex; align-items: center;'><span style='font-size: 40px; margin-right: 15px;'>📊</span> INDICADORES Y SEGUIMIENTO DE CALIDAD POSTVENTA AUTOCIEL</h1>", unsafe_allow_html=True)

with st.expander("📦 Generar y Descargar Reporte Consolidado PDF", expanded=False):
    st.caption("El reporte tomará los filtros configurados en la pestaña 'Monitor Global'.")
    if st.button("⚙️ Pre-renderizar Informe PDF"):
        try:
            # Reconstruimos los filtros globales en base al estado del Monitor
            sel_años_pdf = st.session_state.get('monitor_anio', [datetime.date.today().year])
            sel_meses_pdf = st.session_state.get('monitor_mes', [MESES_ES.get(datetime.date.today().month, "Enero")])
            sel_marcas_pdf = st.session_state.get('monitor_marca', [])
            
            df_pdf_m = df_marca_raw[df_marca_raw['Año'].isin(sel_años_pdf) & df_marca_raw['Mes'].isin(sel_meses_pdf)]
            df_pdf_i = df_int_raw[df_int_raw['Año'].isin(sel_años_pdf) & df_int_raw['Mes'].isin(sel_meses_pdf)]
            
            if sel_marcas_pdf:
                if 'Marca' in df_pdf_m.columns: df_pdf_m = df_pdf_m[df_pdf_m['Marca'].isin(sel_marcas_pdf)]
                if 'Marca' in df_pdf_i.columns: df_pdf_i = df_pdf_i[df_pdf_i['Marca'].isin(sel_marcas_pdf)]

            with st.spinner("Compilando datos de todas las areas..."):
                data_pdf = generar_reporte_pdf_bytes(df_pdf_m, df_pdf_i, sel_meses_pdf)
                
            st.success("¡Reporte listo!")
            st.download_button(
                label="📥 Descargar Reporte PDF", data=data_pdf,
                file_name=f"Reporte_Calidad_Autociel_{'_'.join(sel_meses_pdf)}.pdf", mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Error al estructurar el PDF: {e}")

st.markdown("<br>", unsafe_allow_html=True)
# ==============================================================================
# PESTAÑAS PRINCIPALES
# ==============================================================================
tab_monitor, tab_tabla, tab_ficha, tab_carga, tab_quejas, tab_telemarketer, tab_prima, tab_reclamos = st.tabs([
    "🏠 Monitor Global Comparativo", 
    "👥 Tabla Unificada de Asesores", 
    "👤 Ficha Histórica Asesor", 
    "📊 Análisis de Carga Operativa",
    "⚠️ Gestión de Quejas",
    "📞 Telemarketer",
    "💰 Prima de Calidad",
    "📋 Análisis de Reclamos"
])

# ------------------------------------------------------------------------------
# 1. MONITOR GLOBAL COMPARATIVO
# ------------------------------------------------------------------------------
with tab_monitor:
    df_m1, df_i1, meses_sel_t1 = render_filtros_pestaña(df_marca_raw, df_int_raw, "monitor")
    
    # ==============================================================================
    # TENDENCIA ANUAL DE NPS (NUEVO DESPLEGABLE)
    # ==============================================================================
    with st.expander("📈 Ver anualmente el NPS (Evolución Mensual)", expanded=False):
        # Tomamos los años seleccionados en el filtro de arriba
        años_seleccionados = st.session_state.get('monitor_anio', [datetime.date.today().year])
        
        # Filtramos la base cruda SOLO por el año para asegurar traer todos los meses
        df_m_anio_completo = df_marca_raw[df_marca_raw['Año'].isin(años_seleccionados)]
        df_i_anio_completo = df_int_raw[df_int_raw['Año'].isin(años_seleccionados)]
        
        # Si hay marcas seleccionadas, las respetamos en la tendencia anual
        marcas_seleccionadas = st.session_state.get('monitor_marca', [])
        if marcas_seleccionadas:
            if 'Marca' in df_m_anio_completo.columns:
                df_m_anio_completo = df_m_anio_completo[df_m_anio_completo['Marca'].isin(marcas_seleccionadas)]
            if 'Marca' in df_i_anio_completo.columns:
                df_i_anio_completo = df_i_anio_completo[df_i_anio_completo['Marca'].isin(marcas_seleccionadas)]

        meses_eje_x = []
        nps_marca_y = []
        nps_interna_y = []
        
        # Recorremos los meses del 1 al 12 para calcular los resultados
        for m_num in sorted(df_m_anio_completo['Mes_Num'].unique()):
            df_mes_m = df_m_anio_completo[df_m_anio_completo['Mes_Num'] == m_num]
            df_mes_i = df_i_anio_completo[df_i_anio_completo['Mes_Num'] == m_num]
            
            # Calculamos el NPS correspondiente a ese mes
            score_m = calcular_metricas_nps(df_mes_m, "Q2 - Recomendación - taller")[0] if not df_mes_m.empty else None
            score_i = calcular_metricas_nps(df_mes_i, "1-NPS")[0] if not df_mes_i.empty else None
            
            if score_m is not None or score_i is not None:
                meses_eje_x.append(MESES_ES[m_num])
                nps_marca_y.append(score_m if score_m is not None else 0.0)
                nps_interna_y.append(score_i if score_i is not None else 0.0)
        
        if meses_eje_x:
            fig_tendencia = go.Figure()
            
            # Barra Vertical - Marca
            fig_tendencia.add_trace(go.Bar(
                x=meses_eje_x, y=nps_marca_y,
                name="NPS Oficial Marca",
                marker_color="#2563EB",
                text=[f"{v}%" for v in nps_marca_y],
                textposition='auto'
            ))
            
            # Barra Vertical - Interna
            fig_tendencia.add_trace(go.Bar(
                x=meses_eje_x, y=nps_interna_y,
                name="NPS Encuesta Interna",
                marker_color="#10B981",
                text=[f"{v}%" for v in nps_interna_y],
                textposition='auto'
            ))
            
            # Línea de Objetivo del 95%
            fig_tendencia.add_trace(go.Scatter(
                x=meses_eje_x, y=[95] * len(meses_eje_x),
                mode='lines',
                name='Objetivo Calidad (95%)',
                line=dict(color='#EF4444', width=3, dash='dash'),
                hoverinfo='skip'
            ))
            
            fig_tendencia.update_layout(
                barmode='group',
                xaxis=dict(title="Meses"),
                yaxis=dict(title="NPS (%)", range=[0, 105]),
                height=400,
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig_tendencia, use_container_width=True)
        else:
            st.info("No se registran datos suficientes en el año seleccionado para calcular la tendencia.")
            
    st.markdown("<br>", unsafe_allow_html=True)
    # ==============================================================================

    st.markdown(f"<div class='sub-title'>Resultados en Paralelo: {', '.join(meses_sel_t1)}</div>", unsafe_allow_html=True)
    
    col_izq, col_der = st.columns(2)
    
    # === LADO IZQUIERDO: MARCA ===
    with col_izq:
        st.markdown("### 🏢 Datos de Origen: Encuestas de Marca")
        with st.container(border=True):
            cm_q1, cm_q2, cm_tot = st.columns([2.2, 2.2, 0.8])
            
            with cm_q1:
                score_q1, p_q1, n_q1, d_q1 = calcular_metricas_nps(df_m1, "Q1 - Satisfacción general")
                st.plotly_chart(crear_velocimetro(score_q1, "Q1 - SATISFACCIÓN (NPS)"), use_container_width=True)
                sub_c1, sub_c2, sub_c3 = st.columns(3)
                with sub_c1: st.button(f"🟢 {p_q1} Prom", key="btn_m_p1", on_click=set_filtro_marca, args=('Promotor',))
                with sub_c2: st.button(f"🟡 {n_q1} Neu", key="btn_m_n1", on_click=set_filtro_marca, args=('Neutro',))
                with sub_c3: st.button(f"🔴 {d_q1} Det", key="btn_m_d1", on_click=set_filtro_marca, args=('Detractor',))

            with cm_q2:
                score_q2, p_q2, n_q2, d_q2 = calcular_metricas_nps(df_m1, "Q2 - Recomendación - taller")
                st.plotly_chart(crear_velocimetro(score_q2, "Q2 - RECOMENDACIÓN (NPS)"), use_container_width=True)
                sub_c4, sub_c5, sub_c6 = st.columns(3)
                with sub_c4: st.button(f"🟢 {p_q2} Prom", key="btn_m_p2", on_click=set_filtro_marca, args=('Promotor',))
                with sub_c5: st.button(f"🟡 {n_q2} Neu", key="btn_m_n2", on_click=set_filtro_marca, args=('Neutro',))
                with sub_c6: st.button(f"🔴 {d_q2} Det", key="btn_m_d2", on_click=set_filtro_marca, args=('Detractor',))
                
            with cm_tot:
                st.markdown("<br><br>", unsafe_allow_html=True)
                t_m_q1 = p_q1 + n_q1 + d_q1
                st.metric("Muestra", t_m_q1)
                st.button("🔄 Todos", key="btn_clear_m", on_click=set_filtro_marca, args=('Todos',))

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"**Segmentación actual Marca:** `{st.session_state.filtro_comentarios_marca}`")
        
        subtab_agendamiento, subtab_asesor, subtab_taller, subtab_contacto = st.tabs(["📅 Agend.", "👔 Asesor", "⚙️ Taller", "📞 Cont. "])
        
        with subtab_agendamiento:
            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_m1, "Q5 - Facilidad de agendamiento")[0], "Q5 - Agendamiento", mini=True), use_container_width=True)
            with c2: st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_m1, "Q6 - Satisfacción instalaciones")[0], "Q6 - Instalaciones", mini=True), use_container_width=True)
        
        with subtab_asesor:
            c1, c2, c3 = st.columns(3)
            with c1: st.plotly_chart(crear_torta(df_m1, "Q7 - Cortesía y Amabilidad", "Q7 - Cortesía"), use_container_width=True)
            with c2: st.plotly_chart(crear_torta(df_m1, "Q8 - Competencia Asesor de Servicio", "Q8 - Competencia"), use_container_width=True)
            with c3: st.plotly_chart(crear_torta(df_m1, "Q11 - Explicación trabajo - costo", "Q11 - Expl. Trabajo"), use_container_width=True)
            
            if 'Q10 - Explicación presupuesto' in df_m1.columns and not df_m1['Q10 - Explicación presupuesto'].dropna().empty:
                with st.expander("📊 Ver KPI Histórico Descontinuado (Q10 - Presupuesto)"):
                    st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_m1, "Q10 - Explicación presupuesto")[0], "Q10 - Presupuesto (Ene-Jun)", mini=True), use_container_width=True)

        with subtab_taller:
            c1, c2, c3 = st.columns(3)
            with c1: st.plotly_chart(crear_torta(df_m1, "Q12 - Calidad del trabajo", "Q12 - Calidad"), use_container_width=True)
            with c2: st.plotly_chart(crear_torta(df_m1, col_q13, "Q13 - FIR"), use_container_width=True)
            with c3: st.plotly_chart(crear_torta(df_m1, "Q15 - Entrega según momento acordado", "Q15 - Entrega"), use_container_width=True)
        
        with subtab_contacto:
            st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_m1, "Q19 - Satisfacción con el Contacto")[0], "Q19 - Satisfacción Contacto", mini=True), use_container_width=True)

    # === LADO DERECHO: INTERNA ===
    with col_der:
        st.markdown("### 🎯 Datos de Origen: Encuestas Internas")
        with st.container(border=True):
            ci_q1, ci_q2, ci_tot = st.columns([2.2, 2.2, 0.8])
            
            with ci_q1:
                score_i1 = calcular_promedio(df_i1, "Promedio")
                st.plotly_chart(crear_velocimetro(score_i1, "SATISFACCIÓN (Promedio)", is_promedio=True), use_container_width=True)
                
            with ci_q2:
                score_i2, p_i2, n_i2, d_i2 = calcular_metricas_nps(df_i1, "1-NPS")
                st.plotly_chart(crear_velocimetro(score_i2, "RECOMENDACIÓN (NPS)"), use_container_width=True)
                sub_i4, sub_i5, sub_i6 = st.columns(3)
                with sub_i4: st.button(f"🟢 {p_i2} Prom", key="btn_i_p2", on_click=set_filtro_int, args=('Promotor',))
                with sub_i5: st.button(f"🟡 {n_i2} Neu", key="btn_i_n2", on_click=set_filtro_int, args=('Neutro',))
                with sub_i6: st.button(f"🔴 {d_i2} Det", key="btn_i_d2", on_click=set_filtro_int, args=('Detractor',))
                
            with ci_tot:
                st.markdown("<br><br>", unsafe_allow_html=True)
                t_i_q2 = p_i2 + n_i2 + d_i2
                st.metric("Muestra", t_i_q2)
                st.button("🔄 Todos", key="btn_clear_i", on_click=set_filtro_int, args=('Todos',))
                
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"**Segmentación actual Interna:** `{st.session_state.filtro_comentarios_int}`")
        
        subtab_agend_int, subtab_asesor_int, subtab_taller_int, subtab_contacto_int = st.tabs(["📅 Agend.", "👔 Asesor", "⚙️ Taller", "📞 Cont. "])
        
        with subtab_agend_int:
            st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_i1, "2-Obtener turno")[0], "2-Obtener turno", mini=True), use_container_width=True)
        
        with subtab_asesor_int:
            st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_i1, "4-Atención de necesidades")[0], "4-Atención necesidades", mini=True), use_container_width=True)
        
        with subtab_taller_int:
            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_i1, "6-Calidad de trabajo")[0], "6-Calidad trabajo", mini=True), use_container_width=True)
            with c2: st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_i1, "7-Limpieza del vehículo")[0], "7-Limpieza", mini=True), use_container_width=True)
        
        with subtab_contacto_int:
            st.plotly_chart(crear_velocimetro(calcular_metricas_nps(df_i1, "11-Contacto Servicio Oficial")[0], "11-Contacto Oficial", mini=True), use_container_width=True)

    # === TABLA GLOBAL DE COMENTARIOS DOBLE ===
    st.markdown("---")
    st.markdown("### 💬 Comentarios de Clientes")
    col_com_m, col_com_i = st.columns(2)
    
    with col_com_m:
        with st.container(border=True):
            st.markdown(f"**🏢 Marca (Filtro: {st.session_state.filtro_comentarios_marca})**")
            if st.session_state.filtro_comentarios_marca != 'Todos': st.button("🔄 Ver Todos (Marca)", on_click=set_filtro_marca, args=('Todos',))
            
            # Incorporación de "Verbalización Final" si existe
            cols_verb = [c for c in ["Q3 - Verbalización", "Verbalización Final"] if c in df_m1.columns]
            
            if cols_verb:
                df_com_m = df_m1.copy()
                if st.session_state.filtro_comentarios_marca != 'Todos':
                    q_base = pd.to_numeric(df_com_m["Q1 - Satisfacción general"], errors='coerce')
                    if st.session_state.filtro_comentarios_marca == 'Promotor': df_com_m = df_com_m[q_base >= 9]
                    elif st.session_state.filtro_comentarios_marca == 'Neutro': df_com_m = df_com_m[(q_base >= 7) & (q_base <= 8)]
                    elif st.session_state.filtro_comentarios_marca == 'Detractor': df_com_m = df_com_m[q_base <= 6]
                    
                col_nombre_m = 'Nombre de cliente' if 'Nombre de cliente' in df_com_m.columns else ('Cliente' if 'Cliente' in df_com_m.columns else next((c for c in df_com_m.columns if 'Nombre' in c and 'Principal' not in c), None))
                col_fecha_m = 'Fecha de la Encuesta' if 'Fecha de la Encuesta' in df_com_m.columns else next((c for c in df_com_m.columns if 'Fecha' in c), None)
                
                cols_m = [c for c in [col_nombre_m, col_fecha_m, "Marca"] if c and c in df_com_m.columns] + cols_verb
                
                cm_view = df_com_m[cols_m].dropna(subset=cols_verb, how='all')
                if len(cm_view) > 0: st.dataframe(cm_view, use_container_width=True, hide_index=True)
                else: st.info("Sin comentarios para este segmento.")
            
    with col_com_i:
        with st.container(border=True):
            st.markdown(f"**🎯 Interna (Filtro: {st.session_state.filtro_comentarios_int})**")
            if st.session_state.filtro_comentarios_int != 'Todos': st.button("🔄 Ver Todos (Interna)", on_click=set_filtro_int, args=('Todos',))
            if "CONCATENADO" in df_i1.columns:
                df_com_i = df_i1.copy()
                if st.session_state.filtro_comentarios_int != 'Todos':
                    qi_base = pd.to_numeric(df_com_i["1-NPS"], errors='coerce')
                    if st.session_state.filtro_comentarios_int == 'Promotor': df_com_i = df_com_i[qi_base >= 9]
                    elif st.session_state.filtro_comentarios_int == 'Neutro': df_com_i = df_com_i[(qi_base >= 7) & (qi_base <= 8)]
                    elif st.session_state.filtro_comentarios_int == 'Detractor': df_com_i = df_com_i[qi_base <= 6]
                
                col_nombre_i = 'Cliente' if 'Cliente' in df_com_i.columns else next((c for c in df_com_i.columns if 'Nombre' in c), None)
                col_fecha_i = 'Fecha de la Encuesta' if 'Fecha de la Encuesta' in df_com_i.columns else next((c for c in df_com_i.columns if 'Fecha' in c), None)
                
                cols_i = [c for c in [col_nombre_i, col_fecha_i, "Marca"] if c and c in df_com_i.columns] + ["CONCATENADO"]
                ci_view = df_com_i[cols_i].dropna(subset=["CONCATENADO"])
                if len(ci_view) > 0: st.dataframe(ci_view, use_container_width=True, hide_index=True)
                else: st.info("Sin comentarios para este segmento.")

# ------------------------------------------------------------------------------
# 2. TABLA UNIFICADA DE ASESORES (RANKING DUAL)
# ------------------------------------------------------------------------------
with tab_tabla:
    st.markdown("### Ranking de Desempeño General de Asesores")
    df_t2_m, df_t2_i, _ = render_filtros_pestaña(df_marca_raw, df_int_raw, "tabla_asesores")
    subtab_rk_marca, subtab_rk_int = st.tabs(["🏆 Ranking Oficial (Marca)", "🎯 Ranking Interno"])
    
    with subtab_rk_marca:
        col_asesor_key = next((col for col in df_t2_m.columns if 'Asesor' in col), None)
        if col_asesor_key:
            asesores = df_t2_m[col_asesor_key].dropna().unique()
            ranking_data = []
            for p_asesor in asesores:
                df_ase = df_t2_m[df_t2_m[col_asesor_key] == p_asesor]
                nps_q2, p_q2, n_q2, d_q2 = calcular_metricas_nps(df_ase, "Q2 - Recomendación - taller")
                nps_q7, _, _, _ = calcular_metricas_nps(df_ase, "Q7 - Cortesía y Amabilidad")
                nps_q8, _, _, _ = calcular_metricas_nps(df_ase, "Q8 - Competencia Asesor de Servicio")
                nps_q10, _, _, _ = calcular_metricas_nps(df_ase, "Q10 - Explicación presupuesto")
                nps_q11, _, _, _ = calcular_metricas_nps(df_ase, "Q11 - Explicación trabajo - costo")
                
                t_validos = p_q2 + n_q2 + d_q2
                if nps_q2 >= 94.0: meta_str = "✅ Alcanzado"
                elif t_validos > 0: meta_str = f"Faltan {max(0, math.ceil((94 * t_validos - 100 * (p_q2 - d_q2)) / 6.0))} Prom."
                else: meta_str = "Sin datos"
                
                ranking_data.append({
                    "Asesor de Servicio": p_asesor, "Muestra": len(df_ase), "NPS Q2 (Recomendación)": nps_q2,
                    "NPS Q7 (Cortesía)": nps_q7, "NPS Q8 (Competencia)": nps_q8, "NPS Q10 (Presupuesto)": nps_q10,
                    "NPS Q11 (Trabajo/Costo)": nps_q11, "Meta 94%": meta_str
                })
                
            if ranking_data: st.dataframe(pd.DataFrame(ranking_data).sort_values("NPS Q2 (Recomendación)", ascending=False), use_container_width=True, hide_index=True)
            else: st.info("📊 Aún no se registran encuestas oficiales para el período seleccionado.")
        else:
            st.warning("Columna de Asesor no encontrada en la base de la Marca.")
            
    with subtab_rk_int:
        col_asesor_int = "Asesor" if "Asesor" in df_t2_i.columns else None
        if col_asesor_int:
            ranking_data_int = []
            for p_asesor in df_t2_i[col_asesor_int].dropna().unique():
                df_ase_i = df_t2_i[df_t2_i[col_asesor_int] == p_asesor]
                ranking_data_int.append({
                    "Asesor de Servicio": p_asesor, "Muestra": len(df_ase_i),
                    "Recomendación (1-NPS)": calcular_metricas_nps(df_ase_i, "1-NPS")[0],
                    "Satisfacción (Promedio)": calcular_promedio(df_ase_i, "Promedio"),
                    "Turno (NPS)": calcular_metricas_nps(df_ase_i, "2-Obtener turno")[0],
                    "Atención (NPS)": calcular_metricas_nps(df_ase_i, "4-Atención de necesidades")[0],
                    "Calidad Trabajo (NPS)": calcular_metricas_nps(df_ase_i, "6-Calidad de trabajo")[0],
                    "Limpieza (NPS)": calcular_metricas_nps(df_ase_i, "7-Limpieza del vehículo")[0]
                })
                
            if ranking_data_int: st.dataframe(pd.DataFrame(ranking_data_int).sort_values("Recomendación (1-NPS)", ascending=False), use_container_width=True, hide_index=True)
            else: st.info("🎯 Aún no se registran encuestas internas para el período seleccionado.")
        else:
            st.warning("La columna 'Asesor' no se encontró en la base Interna.")

# ------------------------------------------------------------------------------
# 3. FICHA HISTÓRICA POR ASESOR
# ------------------------------------------------------------------------------
with tab_ficha:
    st.markdown("### Evolución Histórica de Calidad (Cruce Marca vs Interna)")
    st.markdown("<p style='font-size: 14px; color: #64748B; margin-top:-10px;'>Filtra el rango de datos para los KPI superiores. El gráfico evolutivo muestra el historial completo.</p>", unsafe_allow_html=True)
    df_t3_m, df_t3_i, _ = render_filtros_pestaña(df_marca_raw, df_int_raw, "ficha_asesor")
    
    asesores_m = set(df_marca_raw[col_asesor_key].dropna().unique()) if col_asesor_key else set()
    asesores_i = set(df_int_raw["Asesor"].dropna().unique()) if "Asesor" in df_int_raw.columns else set()
    lista_asesores_hist = sorted(list(asesores_m.union(asesores_i)))
    
    if lista_asesores_hist:
        asesor_seleccionado_hist = st.selectbox("Seleccione el Asesor de Servicio para ver su historial:", options=lista_asesores_hist)
        
        # Filtrado para KPI Acumulado (Usando el df filtrado de la pestaña)
        df_kpi_m = df_t3_m[df_t3_m[col_asesor_key] == asesor_seleccionado_hist] if col_asesor_key else pd.DataFrame()
        df_kpi_i = df_t3_i[df_t3_i["Asesor"] == asesor_seleccionado_hist] if "Asesor" in df_t3_i.columns else pd.DataFrame()
        
        col_kpi_m, col_kpi_i = st.columns(2)
        with col_kpi_m:
            with st.container(border=True):
                st.markdown("<h4 style='text-align:center; color:#2563EB; margin-top: 10px;'>Acumulado Marca (Meses Sel.)</h4>", unsafe_allow_html=True)
                k1, k2, k3 = st.columns(3)
                with k1: st.markdown(f"<div class='kpi-card' style='padding:10px;'><div class='kpi-label'>RECOMENDACIÓN</div><div class='kpi-value' style='font-size:32px;'>{calcular_metricas_nps(df_kpi_m, 'Q2 - Recomendación - taller')[0]}%</div></div>", unsafe_allow_html=True)
                with k2: st.markdown(f"<div class='kpi-card' style='padding:10px;'><div class='kpi-label'>SATISFACCIÓN</div><div class='kpi-value' style='font-size:32px;'>{calcular_metricas_nps(df_kpi_m, 'Q1 - Satisfacción general')[0]}%</div></div>", unsafe_allow_html=True)
                with k3: st.markdown(f"<div class='kpi-card' style='padding:10px;'><div class='kpi-label'>MUESTRA</div><div class='kpi-value' style='font-size:32px;'>{len(df_kpi_m)}</div></div>", unsafe_allow_html=True)

        with col_kpi_i:
            with st.container(border=True):
                st.markdown("<h4 style='text-align:center; color:#10B981; margin-top: 10px;'>Acumulado Interno (Meses Sel.)</h4>", unsafe_allow_html=True)
                k4, k5, k6 = st.columns(3)
                with k4: st.markdown(f"<div class='kpi-card' style='padding:10px;'><div class='kpi-label'>RECOMENDACIÓN</div><div class='kpi-value' style='font-size:32px;'>{calcular_metricas_nps(df_kpi_i, '1-NPS')[0]}%</div></div>", unsafe_allow_html=True)
                with k5: st.markdown(f"<div class='kpi-card' style='padding:10px;'><div class='kpi-label'>SATISFACCIÓN</div><div class='kpi-value' style='font-size:32px;'>{calcular_promedio(df_kpi_i, 'Promedio')}%</div></div>", unsafe_allow_html=True)
                with k6: st.markdown(f"<div class='kpi-card' style='padding:10px;'><div class='kpi-label'>MUESTRA</div><div class='kpi-value' style='font-size:32px;'>{len(df_kpi_i)}</div></div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Filtrado histórico para el gráfico de líneas (usamos todo el raw)
        with st.container(border=True):
            df_hist_ase_m = df_marca_raw[df_marca_raw[col_asesor_key] == asesor_seleccionado_hist] if col_asesor_key else pd.DataFrame()
            df_hist_ase_i = df_int_raw[df_int_raw["Asesor"] == asesor_seleccionado_hist] if "Asesor" in df_int_raw.columns else pd.DataFrame()
            
            hist_data_m = { (año, m): calcular_metricas_nps(g, "Q2 - Recomendación - taller")[0] for (año, m), g in df_hist_ase_m.groupby(['Año', 'Mes_Num']) } if 'Mes_Num' in df_hist_ase_m.columns else {}
            hist_data_i = { (año, m): calcular_metricas_nps(g, "1-NPS")[0] for (año, m), g in df_hist_ase_i.groupby(['Año', 'Mes_Num']) } if 'Mes_Num' in df_hist_ase_i.columns else {}
            global_nps = { (año, m): calcular_metricas_nps(g, "Q2 - Recomendación - taller")[0] for (año, m), g in df_marca_raw.groupby(['Año', 'Mes_Num']) } if 'Mes_Num' in df_marca_raw.columns else {}

            periodos_unicos = set(hist_data_m.keys()).union(set(hist_data_i.keys()))
            chart_data = [{"Periodo": f"{MESES_ES.get(m, 'Desc')} {a}", "Orden": a*100+m, "NPS_Marca": hist_data_m.get((a,m)), "NPS_Interna": hist_data_i.get((a,m)), "NPS_Global": global_nps.get((a,m))} for (a,m) in periodos_unicos]
                
            if chart_data:
                df_grafico = pd.DataFrame(chart_data).sort_values("Orden")
                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(x=df_grafico['Periodo'], y=df_grafico['NPS_Global'], mode='lines', name='Promedio Taller (Marca)', line=dict(color='#CBD5E1', width=3), hoverinfo='skip'))
                fig_line.add_trace(go.Scatter(x=df_grafico['Periodo'], y=df_grafico['NPS_Marca'], mode='lines+markers+text', name='NPS Marca', line=dict(color='#1E293B', width=3), marker=dict(size=10, color='#1E293B'), text=df_grafico['NPS_Marca'].apply(lambda x: f"{x}%" if pd.notnull(x) else ""), textposition='top center'))
                fig_line.add_trace(go.Scatter(x=[df_grafico['Periodo'].iloc[0], df_grafico['Periodo'].iloc[-1]], y=[94, 94], mode='lines', name='Objetivo (94%)', line=dict(color='#22C55E', width=2, dash='dash'), hoverinfo='skip'))
                fig_line.update_layout(title="Cruce Evolutivo de NPS: Evaluación Oficial vs. Evaluación Interna", yaxis=dict(title='NPS (%)', range=[0, 105]), height=450, showlegend=True, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("No hay suficientes datos históricos para generar el gráfico.")
    else:
        st.info("No se encontraron asesores en las bases oficiales para analizar.")

# ------------------------------------------------------------------------------
# 4. ANÁLISIS DE CARGA OPERATIVA Y CAUSA RAÍZ
# ------------------------------------------------------------------------------
with tab_carga:
    st.markdown("### 📊 Análisis de Carga Operativa y Calidad")
    df_t4_m, df_t4_i, _ = render_filtros_pestaña(df_marca_raw, df_int_raw, "carga_operativa")
    col_carga_m, col_carga_i = st.columns(2)
    
    with col_carga_m:
        with st.container(border=True):
            st.markdown("<h4 style='color:#2563EB;'>🏢 Causa Raíz - Marca</h4>", unsafe_allow_html=True)
            if col_q4:
                motivos_data = [{"Motivo": m, "Volumen": len(df_t4_m[df_t4_m[col_q4]==m]), "NPS_Q2": calcular_metricas_nps(df_t4_m[df_t4_m[col_q4]==m], "Q2 - Recomendación - taller")[0]} for m in df_t4_m[col_q4].dropna().unique()]
                if motivos_data:
                    df_m_bar = pd.DataFrame(motivos_data).sort_values(by="Volumen", ascending=True)
                    fig_q4 = go.Figure(go.Bar(y=df_m_bar["Motivo"], x=df_m_bar["Volumen"], orientation='h', marker=dict(color=df_m_bar["NPS_Q2"], colorscale=[[0, '#EF4444'], [0.7, '#EAB308'], [1, '#22C55E']], cmin=0, cmax=100, colorbar=dict(title="NPS Q2")), text=df_m_bar["Volumen"], textposition='auto'))
                    fig_q4.update_layout(title="Volumen vs. NPS", height=350 if len(df_m_bar)>3 else 250, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_q4, use_container_width=True)
                    
                    if col_q13 in df_t4_m.columns:
                        fig_fir = go.Figure()
                        colores_stack = ['#22C55E', '#EF4444', '#EAB308', '#64748B', '#3B82F6']
                        for i, resp in enumerate(df_t4_m[col_q13].dropna().unique()):
                            conteos = df_t4_m[df_t4_m[col_q13] == resp][col_q4].value_counts()
                            fig_fir.add_trace(go.Bar(y=df_m_bar["Motivo"], x=[conteos.get(m, 0) for m in df_m_bar["Motivo"]], name=str(resp), orientation='h', marker_color=colores_stack[i % len(colores_stack)]))
                        fig_fir.update_layout(barmode='stack', title="Motivo vs. Reparado en 1ra Visita", height=350 if len(df_m_bar)>3 else 250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                        st.plotly_chart(fig_fir, use_container_width=True)
                        
                cols_verb = [c for c in ["Q3 - Verbalización", "Verbalización Final"] if c in df_t4_m.columns]
                if cols_verb:
                    st.markdown("#### 💬 Lupa Cualitativa")
                    motivo_sel = st.selectbox("Filtrar comentarios:", options=["Ver Todos"] + sorted(df_t4_m[col_q4].dropna().unique()), key="sel_m")
                    df_mostrar_q4 = df_t4_m[df_t4_m[col_q4] == motivo_sel] if motivo_sel != "Ver Todos" else df_t4_m
                    
                    cols_mostrar = ["Fecha de la Encuesta", "Marca", col_q4, "Q1 - Satisfacción general"] + cols_verb
                    df_mostrar_q4 = df_mostrar_q4[cols_mostrar].dropna(subset=cols_verb, how='all')
                    
                    if len(df_mostrar_q4) > 0: st.dataframe(df_mostrar_q4, use_container_width=True, hide_index=True)
                    else: st.info("No hay comentarios.")
            else: st.info("Columna de motivos (Q4) no encontrada.")

    with col_carga_i:
        with st.container(border=True):
            st.markdown("<h4 style='text-align:center; color:#10B981;'>🎯 Causa Raíz - Interna</h4>", unsafe_allow_html=True)
            if "CONCATENADO" in df_t4_i.columns:
                palabra = st.text_input("🔍 Buscar en verbalizaciones:", key="search_int")
                df_carga_i = df_t4_i[df_t4_i["CONCATENADO"].str.contains(palabra, case=False, na=False)] if palabra else df_t4_i
                
                col_n = 'Cliente' if 'Cliente' in df_carga_i.columns else next((c for c in df_carga_i.columns if 'Nombre' in c), None)
                col_f = 'Fecha de la Encuesta' if 'Fecha de la Encuesta' in df_carga_i.columns else next((c for c in df_carga_i.columns if 'Fecha' in c or 'temporal' in c), None)
                
                cols_s = [c for c in [col_n, col_f, "1-NPS", "6-Calidad de trabajo"] if c and c in df_carga_i.columns] + ["CONCATENADO"]
                view_i = df_carga_i[cols_s].dropna(subset=["CONCATENADO"])
                
                st.markdown(f"**Resultados encontrados: {len(view_i)}**")
                if len(view_i) > 0: st.dataframe(view_i, use_container_width=True, hide_index=True)
                else: st.info("No se encontraron comentarios.")
            else: st.info("Columna 'CONCATENADO' no encontrada.")

# ------------------------------------------------------------------------------
# 5. GESTIÓN DE QUEJAS
# ------------------------------------------------------------------------------
with tab_quejas:
    st.markdown("### Alertas de Clientes Detractores")
    df_t5_m, _, _ = render_filtros_pestaña(df_marca_raw, df_int_raw, "quejas")
    
    with st.container(border=True):
        if "Q1 - Satisfacción general" in df_t5_m.columns and "Q2 - Recomendación - taller" in df_t5_m.columns:
            df_det = df_t5_m[(pd.to_numeric(df_t5_m["Q1 - Satisfacción general"], errors='coerce') <= 6) | (pd.to_numeric(df_t5_m["Q2 - Recomendación - taller"], errors='coerce') <= 6)]
            if len(df_det) > 0:
                cols_q = ["Fecha de la Encuesta", "Marca", "Q1 - Satisfacción general", "Q2 - Recomendación - taller"]
                if col_asesor_key: cols_q.append(col_asesor_key)
                if "Q3 - Verbalización" in df_t5_m.columns: cols_q.append("Q3 - Verbalización")
                if "Verbalización Final" in df_t5_m.columns: cols_q.append("Verbalización Final")
                st.dataframe(df_det[cols_q], use_container_width=True, hide_index=True)
            else: st.success("🎉 ¡Excelente! No se registraron detractores en este segmento.")
        else: st.info("Columnas de análisis no encontradas.")

# ------------------------------------------------------------------------------
# 6. PESTAÑA: TELEMARKETER
# ------------------------------------------------------------------------------
with tab_telemarketer:
    st.markdown("### 📞 Control y Efectividad de Canales (Telemarketing)")
    df_tele_base = df_int_raw.copy()
    if "Fecha Cierre" in df_tele_base.columns:
        df_tele_base['Fecha_Cierre_Clean'] = pd.to_datetime(df_tele_base["Fecha Cierre"], dayfirst=True, errors='coerce')
        df_tele_base['Año_Cierre'] = df_tele_base['Fecha_Cierre_Clean'].dt.year
        df_tele_base['Mes_Cierre_Num'] = df_tele_base['Fecha_Cierre_Clean'].dt.month
        df_tele_base = df_tele_base.dropna(subset=['Año_Cierre', 'Mes_Cierre_Num'])
        df_tele_base['Año_Cierre'] = df_tele_base['Año_Cierre'].astype(int)
        df_tele_base['Mes_Cierre_Num'] = df_tele_base['Mes_Cierre_Num'].astype(int)
        
        with st.expander("⚙️ Filtros Telemarketing", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                anios_cierre = sorted(df_tele_base['Año_Cierre'].unique(), reverse=True)
                anio_tele_sel = st.selectbox("Año:", options=anios_cierre, key="sb_anio_tele")
            with c2:
                marcas_tele = sorted(df_tele_base['Marca'].dropna().unique()) if 'Marca' in df_tele_base.columns else []
                marcas_tele_sel = st.multiselect("Marca(s):", options=marcas_tele, default=marcas_tele, key="ms_marca_tele")
                
        df_tele_filtrado = df_tele_base[df_tele_base['Año_Cierre'] == anio_tele_sel]
        if marcas_tele_sel and 'Marca' in df_tele_filtrado.columns: df_tele_filtrado = df_tele_filtrado[df_tele_filtrado['Marca'].isin(marcas_tele_sel)]
        
        st.markdown("---")
        st.markdown(f"#### 📈 Evolución Mensual de Comunicación Efectiva")
        line_data_tele = []
        for m_num in range(1, 13):
            df_mes = df_tele_filtrado[df_tele_filtrado['Mes_Cierre_Num'] == m_num]
            
            if 'Tipo Contacto' in df_mes.columns and 'Contactado' in df_mes.columns:
                
                # 1. Numeradores (Filtro por Tipo de Contacto)
                s_c = df_mes['Tipo Contacto'].fillna('Vacío').astype(str).str.strip()
                c_wa = len(s_c[s_c == 'Whatsapp'])
                c_tel = len(s_c[s_c == 'Telefonico'])
                c_vac = len(s_c[s_c == 'Vacío']) # Se conserva para los tooltips (customdata) del gráfico
                
                # 2. Denominador Común (Filtro por Estado de Contacto)
                estados_validos = ['Cerrado sin respuesta', 'Contactado', 'Buzón de voz', 'No Contactado']
                denominador_comun = df_mes['Contactado'].astype(str).str.strip().isin(estados_validos).sum()
                
                # 3. Cálculos de Efectividad (Los 3 comparten el mismo denominador)
                p_virt = round((c_wa / denominador_comun * 100), 1) if denominador_comun > 0 else None
                p_hum = round((c_tel / denominador_comun * 100), 1) if denominador_comun > 0 else None
                p_glob = round(((c_wa + c_tel) / denominador_comun * 100), 1) if denominador_comun > 0 else None
                
                if m_num in df_tele_filtrado['Mes_Cierre_Num'].unique():
                    line_data_tele.append({
                        "Mes_Nombre": MESES_ES[m_num], 
                        "Mes_Num": m_num, 
                        "Global": p_glob, 
                        "Virtual": p_virt, 
                        "Telemarketer": p_hum, 
                        "Cant_WA": c_wa, 
                        "Cant_Tel": c_tel, 
                        "Cant_Vac": c_vac
                    })
        if line_data_tele:
            df_l = pd.DataFrame(line_data_tele).sort_values("Mes_Num")
            fig_tele = go.Figure()
            m_counts = df_l[['Cant_WA', 'Cant_Tel', 'Cant_Vac']].values
            c_hov = "<b>%{x}</b><br>WhatsApp: %{customdata[0]}<br>Telefónico: %{customdata[1]}<br>Vacíos: %{customdata[2]}<extra></extra>"
            fig_tele.add_trace(go.Scatter(x=df_l['Mes_Nombre'], y=df_l['Global'], mode='lines+markers+text', name='Efectividad Global', line=dict(color='#1E293B', width=4), text=df_l['Global'].apply(lambda x: f"{x}%" if pd.notnull(x) else ""), textposition='top center', customdata=m_counts, hovertemplate=c_hov))
            fig_tele.add_trace(go.Scatter(x=df_l['Mes_Nombre'], y=df_l['Virtual'], mode='lines+markers+text', name='Virtual (WhatsApp)', line=dict(color='#2563EB', width=2, dash='dash'), text=df_l['Virtual'].apply(lambda x: f"{x}%" if pd.notnull(x) else ""), textposition='top center', customdata=m_counts, hovertemplate=c_hov))
            fig_tele.add_trace(go.Scatter(x=df_l['Mes_Nombre'], y=df_l['Telemarketer'], mode='lines+markers+text', name='Telemarketer (Tel)', line=dict(color='#10B981', width=2, dash='dot'), text=df_l['Telemarketer'].apply(lambda x: f"{x}%" if pd.notnull(x) else ""), textposition='bottom center', customdata=m_counts, hovertemplate=c_hov))
            fig_tele.add_trace(go.Scatter(x=[df_l['Mes_Nombre'].iloc[0], df_l['Mes_Nombre'].iloc[-1]], y=[75, 75], mode='lines', name='Objetivo (75%)', line=dict(color='#EF4444', width=2, dash='dash'), hoverinfo='skip'))
            fig_tele.update_layout(yaxis=dict(title='%', range=[0, 105]), height=400, hovermode='x unified', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_tele, use_container_width=True)
            
            st.markdown("---")
            if 'Contactado' in df_tele_filtrado.columns:
                df_torta = df_tele_filtrado.dropna(subset=['Contactado'])
                meses_torta = sorted(df_torta['Mes_Cierre_Num'].unique())
                for i in range(0, len(meses_torta), 3):
                    chunk = meses_torta[i:i+3]
                    cols = st.columns(len(chunk))
                    for idx, m_n in enumerate(chunk):
                        counts = df_torta[df_torta['Mes_Cierre_Num']==m_n]['Contactado'].value_counts()
                        fig_p = go.Figure(data=[go.Pie(labels=counts.index, values=counts.values, hole=.4, textinfo='percent', textposition='inside')])
                        fig_p.update_layout(title={'text': f"<b>{MESES_ES[m_n]}</b>", 'x': 0.5}, height=230, margin=dict(t=40,b=10,l=10,r=10), legend=dict(orientation="h", y=-0.05, xanchor="center", x=0.5, font=dict(size=10)), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                        with cols[idx]: st.plotly_chart(fig_p, use_container_width=True)
        else: st.info("Sin registros suficientes para este filtro.")
    else: st.error("Columna 'Fecha Cierre' no encontrada.")

# ------------------------------------------------------------------------------
# 7. PESTAÑA: PRIMA DE CALIDAD
# ------------------------------------------------------------------------------
with tab_prima:
    st.markdown("### 📊 Tablero de Auditoría y Liquidación: Prima de Calidad Postventa")
    anios_prima = sorted(df_marca_raw['Año'].unique(), reverse=True)
    if anios_prima:
        with st.expander("⚙️ Filtros de Prima", expanded=False):
            c1, c2 = st.columns(2)
            with c1: anio_prima_sel = st.selectbox("Año:", options=anios_prima, key="sb_anio_prima")
            with c2: marcas_prima_sel = st.multiselect("Marcas:", options=sorted(df_marca_raw['Marca'].dropna().unique()) if 'Marca' in df_marca_raw.columns else ["PEUGEOT", "CITROEN"], default=["PEUGEOT", "CITROEN"] if 'Marca' not in df_marca_raw.columns else sorted(df_marca_raw['Marca'].dropna().unique()), key="ms_marcas_prima")
        
        es_filtro_2025 = (anio_prima_sel == 2025)
        p_peugeot = any('peugeot' in m.lower() for m in marcas_prima_sel) if marcas_prima_sel else True
        p_citroen = any('citroen' in m.lower() for m in marcas_prima_sel) if marcas_prima_sel else True
        personas_declaradas = 11 if (p_peugeot and not p_citroen) else (14 if (p_citroen and not p_peugeot) else 25)
        
        df_marca_anio = df_marca_raw[df_marca_raw['Año'] == anio_prima_sel]
        line_data_prima, monto_puro_liquidado, max_teorico_acumulado = [], {}, {}
        
        for m_num in range(1, 13):
            df_mes_marca_filtro = df_marca_anio[df_marca_anio['Mes_Num'] == m_num]
            df_anio_marca_filtro = df_marca_anio.copy()
            if marcas_prima_sel:
                if 'Marca' in df_mes_marca_filtro.columns: df_mes_marca_filtro = df_mes_marca_filtro[df_mes_marca_filtro['Marca'].isin(marcas_prima_sel)]
                if 'Marca' in df_anio_marca_filtro.columns: df_anio_marca_filtro = df_anio_marca_filtro[df_anio_marca_filtro['Marca'].isin(marcas_prima_sel)]
            
            es_2025_post = (anio_prima_sel == 2025 and m_num >= 5)
            es_2026_post = (anio_prima_sel == 2026 and m_num >= 4)
            es_nuevo_esquema = (anio_prima_sel >= 2026 and m_num >= 7) # NUEVA REGLA DESDE JULIO
            
            m_l1, m_l2, m_l5 = (80.5 if es_2025_post else 77.0), (88.0 if es_2025_post else 86.3), (8 if es_2025_post else 10)
            
            if len(df_mes_marca_filtro) == 0:
                monto_puro_liquidado[m_num] = 0
                
                # Ajuste del máximo teórico para meses vacíos
                if es_nuevo_esquema: max_t = 800000
                else: max_t = 630000 if es_2026_post else (420000 if es_2025_post else 540000)
                
                max_teorico_acumulado[m_num] = max_t * personas_declaradas
                lbls_zero = ["🔹 Recomendación (Q2)", "🔹 Q12 Cal. Trab. (Inactivo)", "🔹 Q7 Cortesía (Inactivo)", "🔹 Q19 Cont. (Inactivo)"] if es_nuevo_esquema else ["🔹 Recomendación (Q2)", "🔹 Driver 2", "🔹 Driver 3", "🔹 Driver 4"]
                
                line_data_prima.append({"Mes_Num": m_num, "Mes_Nombre": MESES_ES[m_num], "L1_Val": "-", "L1_OK": False, "L2_Val": "-", "L2_OK": False, "L3_Val": "-", "L3_OK": False, "L5_Val": "0", "L5_OK": False, "V_D1": 0, "V_D2": 0, "V_D3": 0, "V_D4": 0, "Suma_D_M": 0, "Pers": personas_declaradas, "Liq_S_M": 0, "Es_2025": es_2025_post, "Labels": lbls_zero})
                continue
                
            df_6mm = df_anio_marca_filtro[(df_anio_marca_filtro['Mes_Num'] > (m_num - 6)) & (df_anio_marca_filtro['Mes_Num'] <= m_num)]
            tasa_6mm, ok_llave1, val_l1_display = 0.0, False, "-"
            if "Q18 - Contactado" in df_6mm.columns:
                s_q18 = df_6mm["Q18 - Contactado"].astype(str).str.strip().str.lower()
                c_si, c_no = len(s_q18[s_q18.isin(['sí', 'si'])]), len(s_q18[s_q18=='no'])
                if (c_si + c_no) > 0:
                    tasa_6mm = round((c_si / (c_si + c_no)) * 100, 1)
                    ok_llave1, val_l1_display = (tasa_6mm >= m_l1), f"{tasa_6mm}%"
            
            score_nps_mes = calcular_metricas_nps(df_mes_marca_filtro, "Q2 - Recomendación - taller")[0]
            ok_llave2 = (score_nps_mes >= m_l2)
            
            # 3. Mail Válido
            pct_mail_val, ok_llave3, val_l3_display = 0.0, False, "-"
            if not df_email_llave_raw.empty:
                col_fecha_llave = next((c for c in df_email_llave_raw.columns if 'importaci' in c.lower()), None)
                col_estado = next((c for c in df_email_llave_raw.columns if 'estado de limpieza' in c.lower()), None)
                col_rechazo = next((c for c in df_email_llave_raw.columns if 'razón de rechazo' in c.lower() or 'razon de rechazo' in c.lower()), None)
                col_mar = next((c for c in df_email_llave_raw.columns if 'marca' in c.lower()), None)

                if col_fecha_llave and col_estado:
                    df_email_llave_raw['Fecha_Temp'] = pd.to_datetime(df_email_llave_raw[col_fecha_llave], dayfirst=True, errors='coerce')
                    mascara_mes_base = (df_email_llave_raw['Fecha_Temp'].dt.year == anio_prima_sel) & (df_email_llave_raw['Fecha_Temp'].dt.month == m_num)
                    df_rm = df_email_llave_raw[mascara_mes_base].copy()
                    
                    if marcas_prima_sel and col_mar:
                        marcas_upper = [m.upper() for m in marcas_prima_sel]
                        df_rm = df_rm[df_rm[col_mar].astype(str).str.strip().str.upper().isin(marcas_upper)]

                    if not df_rm.empty:
                        estado_serie = df_rm[col_estado].astype(str).str.strip().str.upper().str.replace('Á', 'A')
                        cant_validos = (estado_serie == "VALIDO").sum()

                        cant_rechazos = 0
                        if col_rechazo:
                            razones_validas_penalizables = [
                                "NoContactProvided",
                                "Correo electronico/telefono ausente;Correo electronico/telefono Inválido",
                                "Correo electrónico/teléfono Inválido",
                                "Email /phone missing",
                                "Email /phone missing;Invalid email / phone",
                                "Invalid Email",
                                "Invalid email / phone",
                                "Mandatory field missing - Email;Invalid Email",
                                "No se proporciono ningun contacto valido"
                            ]
                            razon_serie = df_rm[col_rechazo].astype(str).str.strip()
                            mascara_rechazos = (estado_serie.str.contains("NO VALID", na=False)) & (razon_serie.isin(razones_validas_penalizables))
                            cant_rechazos = mascara_rechazos.sum()

                        total_divisor = cant_validos + cant_rechazos
                        if total_divisor > 0:
                            pct_mail_val = round((cant_validos / total_divisor) * 100, 1)
                            ok_llave3, val_l3_display = (pct_mail_val >= 80.0), f"{pct_mail_val}%"

            ok_llave5 = (len(df_mes_marca_filtro) >= m_l5)
            llaves_ok = ok_llave1 and ok_llave2 and ok_llave3 and ok_llave5
            
            m1, m2, m3, m4 = 0, 0, 0, 0
            
            # --- EVALUACIÓN DE DRIVERS ---
            if es_nuevo_esquema:
                # NUEVA LÓGICA (A partir de Julio 2026)
                if score_nps_mes >= 93.5: m1 = 800000
                elif score_nps_mes >= 88.3: m1 = 600000
                
                max_u = 800000
                lbls = ["🔹 Recomendación (Q2)", "🔹 Q12 Calidad Trabajo (Inactivo)", "🔹 Q7 Cortesía Asesor (Inactivo)", "🔹 Q19 Sat. Contacto (Inactivo)"]
            
            elif es_2025_post:
                # LÓGICA HISTÓRICA 2025
                if score_nps_mes>=93.5: m1=210000
                elif score_nps_mes>=89.8: m1=160000
                sq11 = calcular_metricas_nps(df_mes_marca_filtro, "Q11 - Explicación trabajo - costo")[0]
                if sq11>=94.0: m2=105000
                elif sq11>=89.3: m2=80000
                sq8 = calcular_metricas_nps(df_mes_marca_filtro, "Q8 - Competencia Asesor de Servicio")[0]
                if sq8>=95.5: m3=52500
                elif sq8>=93.3: m3=40000
                sq7 = calcular_metricas_nps(df_mes_marca_filtro, "Q7 - Cortesía y Amabilidad")[0]
                if sq7>=95.5: m4=52500
                elif sq7>=93.3: m4=40000
                max_u, lbls = 420000, ["🔹 Recomendación (Q2)", "🔹 Q11 Explicación Trab.", "🔹 Q8 Competencia Asesor", "🔹 Q7 Cortesía Asesor"]
            
            else:
                if not es_2026_post:
                    # LÓGICA HISTÓRICA ENE-MAR 2026
                    if score_nps_mes>=93.5: m1=270000
                    elif score_nps_mes>=88.3: m1=200000
                    sq12 = calcular_metricas_nps(df_mes_marca_filtro, "Q12 - Calidad del trabajo")[0]
                    if sq12>=94.0: m2=150000
                    elif sq12>=87.8: m2=120000
                    sq7 = calcular_metricas_nps(df_mes_marca_filtro, "Q7 - Cortesía y Amabilidad")[0]
                    if sq7>=95.5: m3=60000
                    elif sq7>=91.8: m3=40000
                    sq19 = calcular_metricas_nps(df_mes_marca_filtro, "Q19 - Satisfacción con el Contacto")[0]
                    if sq19>=95.5: m4=60000
                    elif sq19>=91.8: m4=40000
                    max_u, lbls = 540000, ["🔹 Recomendación (Q2)", "🔹 Q12 Calidad Trabajo", "🔹 Q7 Cortesía Asesor", "🔹 Q19 Satisfacción Contacto"]
                else:
                    # LÓGICA HISTÓRICA ABR-JUN 2026
                    if score_nps_mes>=93.5: m1=310000
                    elif score_nps_mes>=88.3: m1=230000
                    sq12 = calcular_metricas_nps(df_mes_marca_filtro, "Q12 - Calidad del trabajo")[0]
                    if sq12>=94.0: m2=160000
                    elif sq12>=87.8: m2=140000
                    sq7 = calcular_metricas_nps(df_mes_marca_filtro, "Q7 - Cortesía y Amabilidad")[0]
                    if sq7>=95.5: m3=80000
                    elif sq7>=91.8: m3=50000
                    sq19 = calcular_metricas_nps(df_mes_marca_filtro, "Q19 - Satisfacción con el Contacto")[0]
                    if sq19>=95.5: m4=80000
                    elif sq19>=91.8: m4=50000
                    max_u, lbls = 630000, ["🔹 Recomendación (Q2)", "🔹 Q12 Calidad Trabajo", "🔹 Q7 Cortesía Asesor", "🔹 Q19 Satisfacción Contacto"]
            
            sum_d = (m1+m2+m3+m4) if llaves_ok else 0
            tot_l = sum_d * personas_declaradas
            monto_puro_liquidado[m_num] = tot_l
            max_teorico_acumulado[m_num] = max_u * personas_declaradas
            line_data_prima.append({"Mes_Num": m_num, "Mes_Nombre": MESES_ES[m_num], "L1_Val": val_l1_display, "L1_OK": ok_llave1, "L2_Val": f"{score_nps_mes}%", "L2_OK": ok_llave2, "L3_Val": val_l3_display, "L3_OK": ok_llave3, "Es_2025": es_2025_post, "L5_Val": str(len(df_mes_marca_filtro)), "L5_OK": ok_llave5, "V_D1": m1, "V_D2": m2, "V_D3": m3, "V_D4": m4, "Suma_D_M": sum_d, "Pers": personas_declaradas, "Liq_S_M": tot_l, "Labels": lbls})

        lista_render = []
        for d in line_data_prima:
            m = d["Mes_Num"]
            m_bonus, s_bonus, c_bonus = 0, "-", "color:#64748B;"
            
            if m in [3, 6, 9, 12]:
                idx_trim = [m-2, m-1, m]
                df_trim = df_marca_anio[df_marca_anio['Mes_Num'].isin(idx_trim)]
                if marcas_prima_sel and 'Marca' in df_trim.columns: df_trim = df_trim[df_trim['Marca'].isin(marcas_prima_sel)]
                if len(df_trim) > 0:
                    nq2 = calcular_metricas_nps(df_trim, "Q2 - Recomendación - taller")[0]
                    if d["Es_2025"]:
                        nq11, nq8, nq7 = calcular_metricas_nps(df_trim, "Q11 - Explicación trabajo - costo")[0], calcular_metricas_nps(df_trim, "Q8 - Competencia Asesor de Servicio")[0], calcular_metricas_nps(df_trim, "Q7 - Cortesía y Amabilidad")[0]
                        ok_trim = (nq2>=89.8 and nq11>=89.3 and nq8>=93.3 and nq7>=93.3)
                    else:
                        nq12, nq7, nq19 = calcular_metricas_nps(df_trim, "Q12 - Calidad del trabajo")[0], calcular_metricas_nps(df_trim, "Q7 - Cortesía y Amabilidad")[0], calcular_metricas_nps(df_trim, "Q19 - Satisfacción con el Contacto")[0]
                        ok_trim = (nq2>=88.3 and nq12>=87.8 and nq7>=91.8 and nq19>=91.8)
                    
                    if ok_trim:
                        m_bonus = round(sum(monto_puro_liquidado.get(i, 0) for i in idx_trim) * 0.05, 0)
                        s_bonus, c_bonus = f"${m_bonus:,.0f}".replace(",", "."), "background-color: #D4EDDA; color: #155724; font-weight: bold;"
                    else: s_bonus, c_bonus = "$0", "background-color: #F8D7DA; color: #721C24; font-weight: bold;"
                    
            f_calc = d["Liq_S_M"] + m_bonus
            lista_render.append({**d, "Bonus_Display": s_bonus, "Color_B_Style": c_bonus, "Pct_Cumpl": round((d["Liq_S_M"]/max_teorico_acumulado[m]*100),1) if max_teorico_acumulado[m]>0 else 0.0, "Final_M": f_calc, "Perdida_M": max(0, max_teorico_acumulado[m]-f_calc)})

        # ==========================================================
        # RENDERIZADO HTML (DIVIDIDO PARA EL DESPLEGABLE)
        # ==========================================================
        if lista_render:
            # Estilo maestro para fijar el ancho y evitar desalineaciones
            t_style = "width:100%; table-layout:fixed; border-collapse: collapse; text-align: center; font-size: 13px;"
            
            # --- PARTE 1: TABLA PRINCIPAL Y RECOMENDACIÓN ---
            html_top = f"<table style='{t_style}'><thead><tr style='background-color: #1E293B; color: white;'><th style='padding: 10px; border: 1px solid #E2E8F0; text-align: left;'>Mes</th>"
            for d in lista_render: html_top += f"<th style='padding: 10px; border: 1px solid #E2E8F0;'>{d['Mes_Nombre']}</th>"
            html_top += "</tr></thead><tbody>"
            
            html_top += f"<tr style='background-color: #EDF2F7;'><td colspan='{len(lista_render)+1}' style='text-align:left; padding:8px; font-weight:bold;'>🔑 UMBRALES (POSTVENTA)</td></tr>"
            lbl_l1 = "📞 Contacto Posterior 6MM (Meta &ge; 80.5%)" if es_filtro_2025 else "📞 Contacto Posterior 6MM (Meta &ge; 77%)"
            html_top += f"<tr><td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left; overflow:hidden;'>{lbl_l1}</td>"
            for d in lista_render: html_top += f"<td style='padding: 10px; border: 1px solid #E2E8F0; background-color: {'#D4EDDA' if d['L1_OK'] else ('#F1F5F9' if d['L1_Val']=='-' else '#F8D7DA')}; font-weight: bold;'>{d['L1_Val']}</td>"
            html_top += "</tr>"
            
            lbl_l2 = "🏢 NPS Mínimo Taller (Meta &ge; 88%)" if es_filtro_2025 else "🏢 NPS Mínimo Global (Meta &ge; 86.3%)"
            html_top += f"<tr><td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left; overflow:hidden;'>{lbl_l2}</td>"
            for d in lista_render: html_top += f"<td style='padding: 10px; border: 1px solid #E2E8F0; background-color: {'#D4EDDA' if d['L2_OK'] else ('#F1F5F9' if d['L2_Val']=='-' else '#F8D7DA')}; font-weight: bold;'>{d['L2_Val']}</td>"
            html_top += "</tr>"
            
            html_top += "<tr><td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left; overflow:hidden;'>✉️ Tasa Mail Válido (&ge; 80%)</td>"
            for d in lista_render: html_top += f"<td style='padding: 10px; border: 1px solid #E2E8F0; background-color: {'#D4EDDA' if d['L3_OK'] else ('#F1F5F9' if d['L3_Val']=='-' else '#F8D7DA')}; font-weight: bold;'>{d['L3_Val']}</td>"
            html_top += "</tr>"
            
            lbl_l5 = "📊 Muestra Mínima (Meta &ge; 8 Rps.)" if es_filtro_2025 else "📊 Muestra Mínima (Meta &ge; 10 Rps.)"
            html_top += f"<tr><td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left; overflow:hidden;'>{lbl_l5}</td>"
            for d in lista_render: html_top += f"<td style='padding: 10px; border: 1px solid #E2E8F0; background-color: {'#D4EDDA' if d['L5_OK'] else ('#F1F5F9' if d['L5_Val']=='-' else '#F8D7DA')}; font-weight: bold;'>{d['L5_Val']}</td>"
            html_top += "</tr>"
            
            html_top += f"<tr style='background-color: #EDF2F7;'><td colspan='{len(lista_render)+1}' style='text-align:left; padding:8px; font-weight:bold;'>🎯 INCENTIVOS COMERCIALES</td></tr>"
            
            # Fila estática de Recomendación (Siempre visible)
            html_top += f"<tr><td style='padding:10px; border:1px solid #E2E8F0; text-align:left; overflow:hidden;'>{lista_render[0]['Labels'][0]}</td>"
            for d in lista_render: html_top += f"<td style='padding:10px; border:1px solid #E2E8F0;'>${d['V_D1']:,.0f}</td>".replace("$0", "$0")
            html_top += "</tr></tbody></table>"
            
            st.markdown(html_top, unsafe_allow_html=True)
            
            # --- PARTE 2: DESPLEGABLE DRIVERS DESCONTINUADOS ---
            with st.expander("🔽 Ver Drivers Complementarios (Historial y Descontinuados)", expanded=False):
                html_mid = f"<table style='{t_style}'><tbody>"
                for i in range(1, 4):
                    html_mid += f"<tr><td style='padding:10px; border:1px solid #E2E8F0; text-align:left; overflow:hidden; color:#64748B;'>{lista_render[0]['Labels'][i]}</td>"
                    for d in lista_render:
                        val = d["V_D2"] if i==1 else (d["V_D3"] if i==2 else d["V_D4"])
                        html_mid += f"<td style='padding:10px; border:1px solid #E2E8F0; color:#64748B;'>${val:,.0f}</td>".replace("$0", "$0")
                    html_mid += "</tr>"
                html_mid += "</tbody></table>"
                st.markdown(html_mid, unsafe_allow_html=True)
                
            # --- PARTE 3: TOTALES INFERIORES ---
            html_bot = f"<table style='{t_style}'><tbody>"
            html_bot += "<tr style='background-color: #F8FAFC;'><td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left; font-weight: bold; overflow:hidden;'>💰 SUMA DRIVERS (Unitario)</td>"
            for d in lista_render: html_bot += f"<td style='padding: 10px; border: 1px solid #E2E8F0; font-weight: bold; color:#1E3A8A;'>${d['Suma_D_M']:,.0f}</td>".replace("$0", "$0")
            html_bot += "</tr>"
            
            html_bot += "<tr style='background-color: #F1F5F9; font-weight: bold;'><td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left; overflow:hidden;'>📊 Eficiencia del Mes</td>"
            for d in lista_render: html_bot += f"<td style='padding: 10px; border: 1px solid #E2E8F0; color:{'#10B981' if d['Pct_Cumpl']>=90 else ('#F59E0B' if d['Pct_Cumpl']>=50 else '#EF4444')};'>{d['Pct_Cumpl']:.1f}%</td>"
            html_bot += "</tr>"
            
            html_bot += "<tr><td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left; font-weight: bold; overflow:hidden;'>👥 Personal Declarado</td>"
            for d in lista_render: html_bot += f"<td style='padding: 10px; border: 1px solid #E2E8F0;'>{d['Pers']}</td>"
            html_bot += "</tr>"
            
            html_bot += "<tr><td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left; font-weight: bold; overflow:hidden;'>📈 Liq. Total Sector</td>"
            for d in lista_render: html_bot += f"<td style='padding: 10px; border: 1px solid #E2E8F0;'>${d['Liq_S_M']:,.0f}</td>".replace("$0", "$0")
            html_bot += "</tr>"
            
            html_bot += "<tr style='background-color: #FDF2F8;'><td style='padding: 10px; border: 1px solid #E2E8F0; text-align: left; font-weight: bold; color: #9D174D; overflow:hidden;'>⭐ Bonus Trimestral (5%)</td>"
            for d in lista_render: html_bot += f"<td style='padding: 10px; border: 1px solid #E2E8F0; {d['Color_B_Style']}'>{d['Bonus_Display']}</td>"
            html_bot += "</tr>"
            
            html_bot += "<tr style='background-color: #D1FAE5;'><td style='padding: 12px; border: 1px solid #E2E8F0; text-align: left; font-weight: bold; color:#065F46; overflow:hidden;'>💵 LIQUIDACIÓN FINAL</td>"
            for d in lista_render: html_bot += f"<td style='padding: 12px; border: 1px solid #E2E8F0; font-weight: bold; color:#047857;'>${d['Final_M']:,.0f}</td>".replace("$0", "$0")
            html_bot += "</tr></tbody></table>"
            
            st.markdown(html_bot, unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("#### 💵 Control de Flujo de Caja")
            c_sel1, c_sel2 = st.columns(2)
            
            # --- NUEVA LÓGICA: AUTO-COMPLETAR MESES COBRADOS (+45 DÍAS) ---
            meses_cobrados_default = []
            hoy = datetime.date.today()
            
            for m_num in range(1, 13):
                if m_num == 12:
                    primer_dia_siguiente = datetime.date(anio_prima_sel + 1, 1, 1)
                else:
                    primer_dia_siguiente = datetime.date(anio_prima_sel, m_num + 1, 1)
                    
                fecha_cierre_mes = primer_dia_siguiente - datetime.timedelta(days=1)
                fecha_cobro = fecha_cierre_mes + datetime.timedelta(days=45)
                
                if hoy >= fecha_cobro:
                    mes_nombre = MESES_ES.get(m_num)
                    if any(x['Mes_Nombre'] == mes_nombre and x['L1_Val'] != '-' for x in lista_render):
                        meses_cobrados_default.append(mes_nombre)
            # --------------------------------------------------------------

            with c_sel1: a_caja = st.selectbox("Año:", options=anios_prima, key="sb_anio_caja")
            with c_sel2: m_caja = st.multiselect("Meses cobrados:", options=list(MESES_ES.values()), default=meses_cobrados_default, key="ms_meses_caja")
            
            m_cob, m_pend, m_perd = 0.0, 0.0, 0.0
            x_m, y_alc, y_max, y_per = [], [], [], []
            for d in lista_render:
                if d["L1_Val"] != "-":
                    if d["Mes_Nombre"] in m_caja: m_cob += d["Final_M"]; m_perd += d["Perdida_M"]
                    else: m_pend += d["Final_M"]
                    x_m.append(d["Mes_Nombre"]); y_alc.append(d["Final_M"]); y_max.append(max_teorico_acumulado.get(d["Mes_Num"], 0)); y_per.append(d["Perdida_M"])
            
            pct_alc = (m_cob / (m_cob + m_perd) * 100) if (m_cob + m_perd) > 0 else 0.0
            
            c_k1, c_k2, c_k3, c_k4 = st.columns(4)
            c_k1.markdown(f"<div class='kpi-card' style='border-left: 5px solid #10B981;'><div class='kpi-label'>💰 COBRADO</div><div class='kpi-value' style='color:#065F46; font-size: 26px;'>${m_cob:,.0f}</div></div>".replace(",", "."), unsafe_allow_html=True)
            c_k2.markdown(f"<div class='kpi-card' style='border-left: 5px solid #EF4444;'><div class='kpi-label'>📉 PERDIDO</div><div class='kpi-value' style='color:#B91C1C; font-size: 26px;'>${m_perd:,.0f}</div></div>".replace(",", "."), unsafe_allow_html=True)
            c_k3.markdown(f"<div class='kpi-card' style='border-left: 5px solid #8B5CF6;'><div class='kpi-label'>📊 % ALCANZADO</div><div class='kpi-value' style='color:#5B21B6; font-size: 26px;'>{pct_alc:.1f}%</div></div>", unsafe_allow_html=True)
            c_k4.markdown(f"<div class='kpi-card' style='border-left: 5px solid #3B82F6;'><div class='kpi-label'>⏳ PENDIENTE</div><div class='kpi-value' style='color:#1D4ED8; font-size: 26px;'>${m_pend:,.0f}</div></div>".replace(",", "."), unsafe_allow_html=True)
            
            if x_m:
                fig_ec = go.Figure()
                fig_ec.add_trace(go.Scatter(x=x_m, y=y_alc, mode='lines+markers+text', name='$ Alcanzado', line=dict(color='#10B981', width=4), text=[f"${v:,.0f}".replace(",", ".") for v in y_alc], textposition='top center', fill='tozeroy', fillcolor='rgba(34, 197, 94, 0.25)'))
                fig_ec.add_trace(go.Scatter(x=x_m, y=y_max, mode='lines', name='$ Máximo', line=dict(color='#94A3B8', width=2, dash='dash')))
                fig_ec.add_trace(go.Scatter(x=x_m, y=y_per, mode='lines+markers', name='$ Pérdida', line=dict(color='#EF4444', width=2), fill='tozeroy', fillcolor='rgba(239, 68, 68, 0.22)'))
                fig_ec.update_layout(hovermode='x unified', height=420, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_ec, use_container_width=True)

# ------------------------------------------------------------------------------
        # 8. PESTAÑA: ANÁLISIS DE RECLAMOS
        # ------------------------------------------------------------------------------
        with tab_reclamos:
            st.markdown("### 📋 Análisis de Reclamos")
            df_rec_base = df_reclamos_raw.copy()
            if 'Fecha Cierre' in df_rec_base.columns:
                df_rec_base['Fecha_Cierre_Clean'] = pd.to_datetime(df_rec_base['Fecha Cierre'], dayfirst=True, errors='coerce')
                df_rec_base['Año_Cierre'] = df_rec_base['Fecha_Cierre_Clean'].dt.year
                df_rec_base['Mes_Cierre_Num'] = df_rec_base['Fecha_Cierre_Clean'].dt.month
                df_rec_base = df_rec_base.dropna(subset=['Año_Cierre', 'Mes_Cierre_Num'])
                df_rec_base['Año_Cierre'] = df_rec_base['Año_Cierre'].astype(int)
                df_rec_base['Mes_Cierre_Num'] = df_rec_base['Mes_Cierre_Num'].astype(int)
                
                with st.expander("⚙️ Filtros de Reclamos", expanded=False):
                    col_r1, col_r2 = st.columns(2)
                    with col_r1: anio_rec_sel = st.selectbox("Año:", options=sorted(df_rec_base['Año_Cierre'].unique(), reverse=True), key="sb_anio_rec")
                    with col_r2: 
                        df_rec_a = df_rec_base[df_rec_base['Año_Cierre'] == anio_rec_sel]
                        m_disp = sorted(df_rec_a['Mes_Cierre_Num'].unique())
                        meses_rec_sel = multiselect_meses = st.multiselect("Mes(es):", options=m_disp, format_func=lambda x: MESES_ES[x], default=m_disp, key="ms_mes_rec")
                
                df_rec_filtrado = df_rec_a[df_rec_a['Mes_Cierre_Num'].isin(meses_rec_sel)]
                
                st.markdown("---")
                
                # --- CONTENEDOR DE 2 COLUMNAS PARA LOS GRÁFICOS ---
                col_graf_1, col_graf_2 = st.columns(2)
                
                # 1. Gráfico de Línea (Columna Izquierda)
                with col_graf_1:
                    st.markdown("#### 📈 Evolución Mensual de Reclamos")
                    line_data_rec = []
                    for m_num in m_disp:
                        df_m = df_rec_a[df_rec_a['Mes_Cierre_Num'] == m_num]
                        cr, cc, cv = df_m['Reclamo'].notna().sum() if 'Reclamo' in df_m.columns else 0, df_m['Contactado'].notna().sum() if 'Contactado' in df_m.columns else 0, df_m['Estado'].isna().sum() if 'Estado' in df_m.columns else 0
                        pct = round((cr / (cc + cr) * 100), 1) if (cc + cr) > 0 else 0.0
                        line_data_rec.append({"Mes_Nombre": MESES_ES[m_num], "Mes_Num": m_num, "Pct_Reclamo": pct, "Cant_Reclamo": cr, "Cant_Contactado": cc, "Cant_Vacios": cv})
                        
                    if line_data_rec:
                        df_lr = pd.DataFrame(line_data_rec).sort_values("Mes_Num")
                        fig_l_rec = go.Figure(go.Scatter(x=df_lr['Mes_Nombre'], y=df_lr['Pct_Reclamo'], mode='lines+markers+text', line=dict(color='#EF4444', width=3), text=df_lr['Pct_Reclamo'].apply(lambda x: f"{x}%"), textposition='top center', customdata=df_lr[['Cant_Reclamo', 'Cant_Contactado', 'Cant_Vacios']].values, hovertemplate="<b>%{x}</b><br>% Reclamos: %{y}%<br>Reclamos: %{customdata[0]}<br>Contactados: %{customdata[1]}<br>Vacíos: %{customdata[2]}<extra></extra>"))
                        fig_l_rec.update_layout(yaxis=dict(title='%', range=[0, max(df_lr['Pct_Reclamo'])+10 if not df_lr.empty else 100]), height=380, margin=dict(l=10, r=10, t=30, b=10), hovermode='x unified', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig_l_rec, use_container_width=True)

                # 2. Gráfico de Embudo (Columna Derecha)
                with col_graf_2:
                    st.markdown("#### 🔄 Embudo por Categoría de Reclamo")
                    if 'Reclamo' in df_rec_filtrado.columns:
                        df_rc = df_rec_filtrado.dropna(subset=['Reclamo'])
                        if not df_rc.empty:
                            c_rec = df_rc['Reclamo'].value_counts().reset_index()
                            c_rec.columns = ['Categoria', 'Cantidad']
                            fig_f = go.Figure(go.Funnel(y=c_rec['Categoria'], x=c_rec['Cantidad'], textinfo="value+percent initial", marker={"color": ["#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE", "#DBEAFE"] * 10}))
                            fig_f.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                            st.plotly_chart(fig_f, use_container_width=True)
                        else:
                            st.info("Sin datos para el embudo en este segmento.")
                    else:
                        st.info("Columna 'Reclamo' no encontrada.")
                
                st.markdown("---")
                
                # --- SECCIÓN DE BARRAS POR ÁREA Y TABLA DE DETALLE ---
                areas_cols = ['Cita', 'Servicio', 'Taller', 'Repuesto', 'Lavadero', 'Garantia', 'Gestion', 'Taller Cenoa']
                cc_tot = df_rec_filtrado['Contactado'].notna().sum() if 'Contactado' in df_rec_filtrado.columns else 0
                a_stats = {a: {'total': df_rec_filtrado[a].notna().sum(), 'pct': round((df_rec_filtrado[a].notna().sum() / (cc_tot + df_rec_filtrado[a].notna().sum()) * 100), 1) if (cc_tot + df_rec_filtrado[a].notna().sum()) > 0 else 0.0} for a in areas_cols if a in df_rec_filtrado.columns and df_rec_filtrado[a].notna().sum() > 0}
                
                f_area, f_cat = None, None
                if a_stats:
                    s_areas = sorted(list(a_stats.keys()), key=lambda x: a_stats[x]['total'])
                    c_per_a = {a: df_rec_filtrado[a].value_counts() for a in s_areas}
                    all_cats = set()
                    for counts in c_per_a.values(): all_cats.update(counts.index)
                    l_cats = sorted(list(all_cats))
                    
                    fig_ba = go.Figure()
                    for cat in l_cats:
                        x_v, cd_p = [c_per_a[a].get(cat, 0) for a in s_areas], [a_stats[a]['pct'] for a in s_areas]
                        if sum(x_v) > 0:
                            fig_ba.add_trace(go.Bar(
                                y=s_areas, x=x_v, name=str(cat), orientation='h', 
                                text=[f"{v}" if v>0 else "" for v in x_v], textposition='inside', 
                                customdata=cd_p, hovertemplate="<b>Área:</b> %{y}<br><b>Falla:</b> " + str(cat) + "<br><b>Cant:</b> %{x}<br><b>% Reclamo:</b> %{customdata}%<extra></extra>"
                            ))
                    fig_ba.update_layout(barmode='stack', height=400 if len(s_areas)>3 else 280, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                    st.info("💡 Haz clic en cualquier bloque de color del gráfico para filtrar la tabla de abajo. (Doble clic para borrar el filtro).")
                    
                    try:
                        event = st.plotly_chart(fig_ba, use_container_width=True, on_select="rerun", selection_mode="points", key="gr_rec")
                        puntos = []
                        
                        if hasattr(event, "selection") and hasattr(event.selection, "points"):
                            puntos = event.selection.points
                        elif isinstance(event, dict) and "selection" in event:
                            puntos = event["selection"].get("points", [])
                            
                        if puntos:
                            pto = puntos[0]
                            f_area = pto.get("y") if isinstance(pto, dict) else getattr(pto, "y", None)
                            
                            c_idx = pto.get("curve_number") if isinstance(pto, dict) else getattr(pto, "curve_number", None)
                            if c_idx is None and isinstance(pto, dict): c_idx = pto.get("curveNumber")
                            if c_idx is None: c_idx = getattr(pto, "curveNumber", None)
                            
                            if c_idx is not None and int(c_idx) < len(fig_ba.data):
                                f_cat = fig_ba.data[int(c_idx)].name
                    except Exception: 
                        pass
                
                st.markdown("---")
                st.markdown(f"#### 📋 Detalle de Reclamos Operativos ({f'Filtrado: {f_area} ➔ {f_cat}' if f_area and f_cat else 'Visualizando Todos'})")
                cols_req = ["Fecha Cierre", "cliente", "Teléfono", "Asesor", "N° Orden", "Motivo", "Tipo Orden", "CONCATENADO"]
                cols_enc = [next((c for c in df_rec_filtrado.columns if str(c).strip().lower()==str(col).lower()), None) for col in cols_req]
                cols_enc = [c for c in cols_enc if c]
                
            if cols_enc:
                    col_cc = next((c for c in cols_enc if 'concat' in str(c).lower()), None)
                    
                    if f_area and f_cat and f_area in df_rec_filtrado.columns:
                        df_t = df_rec_filtrado[df_rec_filtrado[f_area].astype(str).str.strip() == str(f_cat).strip()]
                    else:
                        df_t = df_rec_filtrado
                        
                    df_t = df_t[cols_enc]
                    if col_cc: df_t = df_t.dropna(subset=[col_cc])
                    
                    if len(df_t) > 0: 
                        st.dataframe(df_t, use_container_width=True, hide_index=True)
                    else: 
                        st.info("No hay detalles registrados para este cruce.")
            else: 
            st.error("Columna 'Fecha Cierre' no encontrada.")

