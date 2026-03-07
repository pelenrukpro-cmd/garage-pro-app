import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from datetime import datetime
import math

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================
st.set_page_config(
    page_title="🏗️ Metal Constructor PRO",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# БОКОВАЯ ПАНЕЛЬ
# ============================================================================
with st.sidebar:
    st.title("⚙️ ПАРАМЕТРЫ ЗДАНИЯ")
    
    st.subheader("📐 Геометрия")
    length = st.number_input("Длина здания L (м)", min_value=6.0, max_value=120.0, value=30.0, step=1.0)
    width = st.number_input("Ширина/Пролёт B (м)", min_value=4.0, max_value=40.0, value=12.0, step=1.0)
    height = st.number_input("Высота до карниза H (м)", min_value=2.5, max_value=12.0, value=4.0, step=0.5)
    roof_pitch_deg = st.slider("Уклон крыши (градусы)", 5, 45, 15, 1)
    
    st.subheader("🔩 Конструкция")
    truss_spacing = st.slider("Шаг ферм (м)", 2.0, 8.0, 4.0, 0.5)
    truss_type = st.radio("Тип фермы", ["Треугольная", "Трапециевидная"], index=0)
    
    st.subheader("🌨️ Нагрузки")
    snow_district = st.selectbox("Снеговой район", ["I (0.5)", "II (0.7)", "III (1.0)", "IV (1.5)", "V (2.0)"], index=3)
    
    st.subheader("🎯 Оптимизация")
    optimization = st.radio("Режим", ["💰 Экономия", "⚖️ Баланс", "💪 Прочность"], index=1)

# ============================================================================
# РАСЧЁТЫ
# ============================================================================

snow_map = {"I (0.5)": 0.5, "II (0.7)": 0.7, "III (1.0)": 1.0, "IV (1.5)": 1.5, "V (2.0)": 2.0}
Sg = snow_map.get(snow_district, 1.5)

if roof_pitch_deg <= 25:
    mu = 1.0
elif roof_pitch_deg <= 60:
    mu = 0.7
else:
    mu = 0.0

S0 = 0.7 * mu * Sg * 1.4

truss_height = width / 6
roof_height = height + truss_height
num_panels = max(8, int(width / 1.5))
panel_length = width / num_panels

permanent_load = 0.15
total_load = S0 + permanent_load
q = total_load * truss_spacing

M_max = q * width**2 / 8
N_chord = M_max / truss_height if truss_height > 0 else 0

safety_factors = {"💰 Экономия": 1.0, "⚖️ Баланс": 1.2, "💪 Прочность": 1.5}
sf = safety_factors.get(optimization, 1.2)

N_chord *= sf
N_web = N_chord * 0.4
N_post = q * truss_spacing * sf

if optimization == "💰 Экономия":
    sections = {'top_chord': '75×6', 'bottom_chord': '75×6', 'web': '50×5', 'posts': '75×6', 'purlins': '60×40×3', 'area_chord': 9.09, 'area_web': 6.69, 'area_post': 9.09}
elif optimization == "💪 Прочность":
    sections = {'top_chord': '100×8', 'bottom_chord': '100×8', 'web': '75×6', 'posts': '100×8', 'purlins': '80×40×4', 'area_chord': 18.84, 'area_web': 11.89, 'area_post': 18.84}
else:
    sections = {'top_chord': '90×7', 'bottom_chord': '90×7', 'web': '60×6', 'posts': '90×7', 'purlins': '70×40×3', 'area_chord': 14.0, 'area_web': 8.73, 'area_post': 14.0}

Ry = 320
stress_chord = N_chord * 10 / sections['area_chord']
stress_util = stress_chord / Ry * 100

num_trusses = int(length / truss_spacing) + 1

# ============================================================================
# 3D МОДЕЛЬ
# ============================================================================

def create_3d_model():
    fig = go.Figure()
    
    colors = {
        'columns': '#FFFFFF',
        'trusses': '#27AE60',
        'purlins': '#00CED1',
        'bracing': '#FF8C00',
        'nodes': '#FF0000'
    }
    
    # Стойки
    for i in range(num_trusses):
        x = i * truss_spacing
        fig.add_trace(go.Scatter3d(x=[x, x], y=[0, 0], z=[0, height], mode='lines', line=dict(color=colors['columns'], width=10), name='Колонны' if i == 0 else '', showlegend=(i==0)))
        fig.add_trace(go.Scatter3d(x=[x, x], y=[width, width], z=[0, height], mode='lines', line=dict(color=colors['columns'], width=10), showlegend=False))
    
    # Фермы
    for i in range(num_trusses):
        x = i * truss_spacing
        
        fig.add_trace(go.Scatter3d(x=[x, x], y=[0, width], z=[height, height], mode='lines', line=dict(color=colors['trusses'], width=8), name='Фермы' if i == 0 else '', showlegend=(i==0)))
        
        y_left = np.linspace(0, width/2, num_panels//2 + 1)
        z_left = height + (y_left / (width/2)) * truss_height
        fig.add_trace(go.Scatter3d(x=[x]*len(y_left), y=y_left, z=z_left, mode='lines', line=dict(color=colors['trusses'], width=8), showlegend=False))
        
        y_right = np.linspace(width/2, width, num_panels//2 + 1)
        z_right = roof_height - ((y_right - width/2) / (width/2)) * truss_height
        fig.add_trace(go.Scatter3d(x=[x]*len(y_right), y=y_right, z=z_right, mode='lines', line=dict(color=colors['trusses'], width=8), showlegend=False))
        
        for j in range(num_panels + 1):
            y_pos = j * panel_length
            if y_pos <= width/2:
                z_top = height + (y_pos / (width/2)) * truss_height
            else:
                z_top = roof_height - ((y_pos - width/2) / (width/2)) * truss_height
            fig.add_trace(go.Scatter3d(x=[x, x], y=[y_pos, y_pos], z=[height, z_top], mode='lines', line=dict(color=colors['trusses'], width=5), showlegend=False))
    
    # Прогоны
    for j in range(5):
        y_pos = (j + 1) * width / 6
        if y_pos <= width/2:
            z_pos = height + (y_pos / (width/2)) * truss_height
        else:
            z_pos = roof_height - ((y_pos - width/2) / (width/2)) * truss_height
        fig.add_trace(go.Scatter3d(x=[0, length], y=[y_pos, y_pos], z=[z_pos, z_pos], mode='lines', line=dict(color=colors['purlins'], width=9), name='Прогоны' if j == 0 else '', showlegend=(j==0)))
    
    # Узлы
    node_positions = []
    for i in range(num_trusses):
        x = i * truss_spacing
        node_positions.append([x, 0, height])
        node_positions.append([x, width, height])
        node_positions.append([x, width/2, roof_height])
    
    if node_positions:
        node_array = np.array(node_positions)
        fig.add_trace(go.Scatter3d(x=node_array[:, 0], y=node_array[:, 1], z=node_array[:, 2], mode='markers', marker=dict(size=8, color=colors['nodes'], opacity=0.9), name='Узлы'))
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='Длина (м)', range=[0, length]),
            yaxis=dict(title='Ширина (м)', range=[0, width]),
            zaxis=dict(title='Высота (м)', range=[0, roof_height + 2]),
            aspectmode='manual',
            aspectratio=dict(x=2.5, y=1, z=0.8)
        ),
        height=700,
        showlegend=True,
        margin=dict(l=0, r=0, t=80, b=0),
        title=dict(text="🏗️ 3D Модель каркаса", x=0.5, font=dict(size=22))
    )
    
    return fig

# ============================================================================
# ОСНОВНОЙ ИНТЕРФЕЙС
# ============================================================================

st.title("🏗️ Metal Constructor PRO")
st.markdown("**Профессиональный расчёт металлоконструкций** 📐")

# Метрики
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("❄️ Снег", f"{S0:.2f} кПа")
with col2:
    st.metric("🏗️ Нагрузка", f"{q:.2f} кН/м")
with col3:
    st.metric("📐 Высота", f"{roof_height:.2f} м")
with col4:
    st.metric("🔩 Ферм", f"{num_trusses} шт.")

st.markdown("---")

# 3D модель
st.subheader("🏗️ 3D Модель")
fig_3d = create_3d_model()
st.plotly_chart(fig_3d, use_container_width=True)

# Анализ
st.markdown("---")
st.subheader("🔍 Анализ напряжений")

if stress_util > 100:
    st.error(f"🔴 **ПЕРЕГРУЗ!** {stress_util:.1f}%")
elif stress_util > 80:
    st.warning(f"🟡 **Повышенное** {stress_util:.1f}%")
else:
    st.success(f"🟢 **Норма** {stress_util:.1f}%")

st.markdown("---")
st.subheader("🔩 Рекомендуемые сечения")
st.markdown(f"""
**Верхний пояс:** {sections['top_chord']} мм  
**Нижний пояс:** {sections['bottom_chord']} мм  
**Стойки:** {sections['posts']} мм  
**Раскосы:** {sections['web']} мм  
**Прогоны:** {sections['purlins']} мм
""")

# Экспорт
report = f"""
ПРОЕКТ КАРКАСА
Metal Constructor PRO
Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}

Размеры: {length}м × {width}м × {height}м
Уклон: {roof_pitch_deg}°

Нагрузки:
Снег: {S0:.2f} кПа
Нагрузка: {q:.2f} кН/м

Сечения:
Верхний пояс: {sections['top_chord']}
Нижний пояс: {sections['bottom_chord']}
Раскосы: {sections['web']}
Стойки: {sections['posts']}
"""

st.download_button("📥 Скачать отчёт", report, f"project_{length}x{width}m.txt", "text/plain")

st.markdown("---")
st.warning("⚠️ **ВАЖНО:** Расчёт предварительный. Для строительства нужен проект по СП.")

st.markdown(f"""
<div style='text-align: center; color: gray; margin-top: 50px;'>
<strong>🏗️ Metal Constructor PRO</strong><br>
{datetime.now().strftime('%d.%m.%Y %H:%M')} | {length}м × {width}м × {height}м
</div>
""", unsafe_allow_html=True)
