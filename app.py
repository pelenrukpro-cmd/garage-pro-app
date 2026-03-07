import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from datetime import datetime
import math

# ============================================================================
# КОНФИГУРАЦИЯ СТРАНИЦЫ
# ============================================================================
st.set_page_config(
    page_title="🏗️ PRO Калькулятор ферм",
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
    roof_pitch = math.tan(math.radians(roof_pitch_deg)) * 100
    
    st.subheader("🔩 Конструкция фермы")
    truss_spacing = st.slider("Шаг ферм (м)", 2.0, 8.0, 4.0, 0.5)
    truss_type = st.radio("Тип фермы", ["Треугольная с параллельным поясом", "Треугольная", "Трапециевидная"], index=0)
    
    st.subheader("🌨️ Нагрузки")
    snow_district = st.selectbox("Снеговой район", ["I (0.5)", "II (0.7)", "III (1.0)", "IV (1.5)", "V (2.0)", "VI (2.5)", "VII (3.0)", "VIII (3.5)"], index=3)
    
    st.subheader("🎯 Оптимизация")
    optimization = st.radio("Режим", ["💰 Экономия", "⚖️ Баланс", "💪 Прочность"], index=1)

# ============================================================================
# РАСЧЁТНЫЕ ФУНКЦИИ
# ============================================================================

def calculate_structure(width, height, roof_pitch_deg, truss_spacing, snow_district, optimization):
    """Расчёт по СП 20.13330 и СП 16.13330"""
    
    # Снеговая нагрузка
    snow_map = {"I (0.5)": 0.5, "II (0.7)": 0.7, "III (1.0)": 1.0, "IV (1.5)": 1.5, 
                "V (2.0)": 2.0, "VI (2.5)": 2.5, "VII (3.0)": 3.0, "VIII (3.5)": 3.5}
    Sg = snow_map.get(snow_district, 1.5)
    
    # Коэффициент уклона
    if roof_pitch_deg <= 25:
        mu = 1.0
    elif roof_pitch_deg <= 60:
        mu = 0.7
    else:
        mu = 0.0
    
    S0 = 0.7 * mu * Sg * 1.4  # расчётная снеговая нагрузка
    
    # Геометрия фермы (как на чертеже ФМ1)
    truss_height = width / 6  # оптимальное h/l = 1/6
    roof_height = height + truss_height
    
    # Количество панелей фермы (как на чертеже - обычно 8-12 панелей)
    num_panels = max(8, int(width / 1.5))
    panel_length = width / num_panels
    
    # Нагрузки
    permanent_load = 0.15  # собственный вес
    total_load = S0 + permanent_load
    q = total_load * truss_spacing  # кН/м
    
    # Усилия
    M_max = q * width**2 / 8
    N_chord = M_max / truss_height if truss_height > 0 else 0
    
    # Коэффициенты запаса
    safety_factors = {"💰 Экономия": 1.0, "⚖️ Баланс": 1.2, "💪 Прочность": 1.5}
    sf = safety_factors.get(optimization, 1.2)
    
    N_chord *= sf
    N_web = N_chord * 0.4
    N_post = q * truss_spacing * sf
    
    # Подбор сечений (как на чертежах)
    if optimization == "💰 Экономия":
        sections = {'top_chord': '75×6', 'bottom_chord': '75×6', 'web': '50×5', 'posts': '75×6', 'purlins': '60×40×3'}
    elif optimization == "💪 Прочность":
        sections = {'top_chord': '100×8', 'bottom_chord': '100×8', 'web': '75×6', 'posts': '100×8', 'purlins': '80×40×4'}
    else:
        sections = {'top_chord': '90×7', 'bottom_chord': '90×7', 'web': '60×6', 'posts': '90×7', 'purlins': '70×40×3'}
    
    # Напряжения
    Ry = 320  # С345
    stress_chord = N_chord * 10 / 15.29  # для 100×100×4
    stress_util = stress_chord / Ry * 100
    
    return {
        'snow_load': S0,
        'truss_height': truss_height,
        'roof_height': roof_height,
        'num_panels': num_panels,
        'panel_length': panel_length,
        'q': q,
        'M_max': M_max,
        'N_chord': N_chord,
        'N_web': N_web,
        'N_post': N_post,
        'sections': sections,
        'stress_chord': stress_chord,
        'stress_util': stress_util,
        'Ry': Ry,
        'safety_factor': sf
    }

# ============================================================================
# 3D ВИЗУАЛИЗАЦИЯ (КАК НА ВАШИХ ЧЕРТЕЖАХ)
# ============================================================================

def create_professional_3d(length, width, height, roof_pitch_deg, truss_spacing, calc):
    """Профессиональная 3D модель с цветовой кодировкой как на чертежах"""
    
    fig = go.Figure()
    
    # Параметры
    num_trusses = int(length / truss_spacing) + 1
    num_panels = calc['num_panels']
    panel_length = calc['panel_length']
    truss_height = calc['truss_height']
    roof_height = calc['roof_height']
    
    # ЦВЕТОВАЯ СХЕМА (как на 3D рендере):
    colors = {
        'columns': '#FFFFFF',        # белые - стойки/колонны
        'trusses': '#27AE60',        # зелёные - фермы
        'purlins': '#00CED1',        # бирюзовые - прогоны
        'bracing': '#FF8C00',        # оранжевые - связи
        'nodes': '#FF0000'           # красные - узлы
    }
    
    # === 1. СТОЙКИ (КОЛОННЫ) - БЕЛЫЕ ===
    for i in range(num_trusses):
        x = i * truss_spacing
        
        # Левая колонна
        fig.add_trace(go.Scatter3d(
            x=[x, x], y=[0, 0], z=[0, height],
            mode='lines',
            line=dict(color=colors['columns'], width=10),
            name='Колонны' if i == 0 else '',
            showlegend=(i==0)
        ))
        
        # Правая колонна
        fig.add_trace(go.Scatter3d(
            x=[x, x], y=[width, width], z=[0, height],
            mode='lines',
            line=dict(color=colors['columns'], width=10),
            showlegend=False
        ))
    
    # === 2. ФЕРМЫ - ЗЕЛЁНЫЕ (с правильной геометрией как на чертеже ФМ1) ===
    for i in range(num_trusses):
        x = i * truss_spacing
        
        # Нижний пояс фермы (горизонтальный)
        fig.add_trace(go.Scatter3d(
            x=[x, x], y=[0, width], z=[height, height],
            mode='lines',
            line=dict(color=colors['trusses'], width=8),
            name='Фермы (нижний пояс)' if i == 0 else '',
            showlegend=(i==0)
        ))
        
        # Верхний пояс (треугольный)
        # Левая половина
        y_left = np.linspace(0, width/2, num_panels//2 + 1)
        z_left = height + (y_left / (width/2)) * truss_height
        
        fig.add_trace(go.Scatter3d(
            x=[x] * len(y_left),
            y=y_left,
            z=z_left,
            mode='lines',
            line=dict(color=colors['trusses'], width=8),
            name='Фермы (верхний пояс)' if i == 0 else '',
            showlegend=(i==0)
        ))
        
        # Правая половина
        y_right = np.linspace(width/2, width, num_panels//2 + 1)
        z_right = roof_height - ((y_right - width/2) / (width/2)) * truss_height
        
        fig.add_trace(go.Scatter3d(
            x=[x] * len(y_right),
            y=y_right,
            z=z_right,
            mode='lines',
            line=dict(color=colors['trusses'], width=8),
            showlegend=False
        ))
        
        # === 3. ВЕРТИКАЛЬНЫЕ СТОЙКИ ФЕРМЫ ===
        for j in range(num_panels + 1):
            y_pos = j * panel_length
            if y_pos <= width/2:
                z_top = height + (y_pos / (width/2)) * truss_height
            else:
                z_top = roof_height - ((y_pos - width/2) / (width/2)) * truss_height
            
            fig.add_trace(go.Scatter3d(
                x=[x, x], y=[y_pos, y_pos], z=[height, z_top],
                mode='lines',
                line=dict(color=colors['trusses'], width=5),
                name='Стойки фермы' if (i==0 and j==0) else '',
                showlegend=(i==0 and j==0)
            ))
        
        # === 4. ДИАГОНАЛЬНЫЕ РАСКОСЫ (как на чертеже) ===
        for j in range(num_panels):
            y1 = j * panel_length
            y2 = (j + 1) * panel_length
            
            if y1 <= width/2:
                z1 = height + (y1 / (width/2)) * truss_height
            else:
                z1 = roof_height - ((y1 - width/2) / (width/2)) * truss_height
            
            if y2 <= width/2:
                z2 = height + (y2 / (width/2)) * truss_height
            else:
                z2 = roof_height - ((y2 - width/2) / (width/2)) * truss_height
            
            # Чередование направления раскосов
            if j % 2 == 0:
                fig.add_trace(go.Scatter3d(
                    x=[x, x], y=[y1, y2], z=[z1, height],
                    mode='lines',
                    line=dict(color=colors['trusses'], width=4),
                    name='Раскосы' if (i==0 and j==0) else '',
                    showlegend=(i==0 and j==0)
                ))
            else:
                fig.add_trace(go.Scatter3d(
                    x=[x, x], y=[y1, y2], z=[height, z2],
                    mode='lines',
                    line=dict(color=colors['trusses'], width=4),
                    showlegend=False
                ))
    
    # === 5. ПРОГОНЫ - БИРЮЗОВЫЕ (горизонтальные балки) ===
    num_purlins = 5
    for j in range(num_purlins):
        y_pos = (j + 1) * width / (num_purlins + 1)
        
        # Расчёт высоты в точке
        if y_pos <= width/2:
            z_pos = height + (y_pos / (width/2)) * truss_height
        else:
            z_pos = roof_height - ((y_pos - width/2) / (width/2)) * truss_height
        
        fig.add_trace(go.Scatter3d(
            x=[0, length], y=[y_pos, y_pos], z=[z_pos, z_pos],
            mode='lines',
            line=dict(color=colors['purlins'], width=9),
            name='Прогоны' if j == 0 else '',
            showlegend=(j==0)
        ))
    
    # === 6. СВЯЗИ ЖЁСТКОСТИ - ОРАНЖЕВЫЕ (кресты в торцах и по длине) ===
    # Торцевые связи
    for x_pos in [0, length]:
        # Крест в левой части
        fig.add_trace(go.Scatter3d(
            x=[x_pos, x_pos], y=[0, width/3], z=[height/2, height],
            mode='lines',
            line=dict(color=colors['bracing'], width=4, dash='dash'),
            name='Связи' if x_pos == 0 else '',
            showlegend=(x_pos==0)
        ))
        
        fig.add_trace(go.Scatter3d(
            x=[x_pos, x_pos], y=[width/3, 0], z=[height, height/2],
            mode='lines',
            line=dict(color=colors['bracing'], width=4, dash='dash'),
            showlegend=False
        ))
    
    # === 7. УЗЛЫ КРЕПЛЕНИЯ - КРАСНЫЕ ТОЧКИ ===
    node_positions = []
    
    # Узлы на колоннах
    for i in range(num_trusses):
        x = i * truss_spacing
        node_positions.append([x, 0, height])
        node_positions.append([x, width, height])
    
    # Узлы в коньке
    for i in range(num_trusses):
        x = i * truss_spacing
        node_positions.append([x, width/2, roof_height])
    
    if node_positions:
        node_array = np.array(node_positions)
        fig.add_trace(go.Scatter3d(
            x=node_array[:, 0],
            y=node_array[:, 1],
            z=node_array[:, 2],
            mode='markers',
            marker=dict(size=8, color=colors['nodes'], opacity=0.9),
            name='Узлы крепления'
        ))
    
    # === НАСТРОЙКИ ВИЗУАЛИЗАЦИИ ===
    fig.update_layout(
        scene=dict(
            xaxis=dict(
                title='Длина здания (м)',
                range=[0, length],
                gridcolor='rgba(200,200,200,0.3)',
                backgroundcolor='rgba(245,245,245,0.5)'
            ),
            yaxis=dict(
                title='Ширина (м)',
                range=[0, width],
                gridcolor='rgba(200,200,200,0.3)',
                backgroundcolor='rgba(245,245,245,0.5)'
            ),
            zaxis=dict(
                title='Высота (м)',
                range=[0, roof_height + 2],
                gridcolor='rgba(200,200,200,0.3)',
                backgroundcolor='rgba(245,245,245,0.5)'
            ),
            aspectmode='manual',
            aspectratio=dict(x=2.5, y=1, z=0.8),
            camera=dict(
                eye=dict(x=1.8, y=1.5, z=1.3),
                up=dict(x=0, y=0, z=1)
            )
        ),
        height=700,
        showlegend=True,
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='rgba(0,0,0,0.3)',
            borderwidth=1
        ),
        margin=dict(l=0, r=0, t=80, b=0),
        title=dict(
            text="🏗️ 3D Модель каркаса (цветовая схема как на чертежах)",
            x=0.5,
            font=dict(size=22, family="Arial Black")
        ),
        paper_bgcolor='rgba(255,255,255,1)',
        plot_bgcolor='rgba(255,255,255,1)'
    )
    
    return fig

# ============================================================================
# ГЕНЕРАЦИЯ ЧЕРТЕЖЕЙ
# ============================================================================

def generate_drawings(length, width, height, roof_pitch_deg, calc):
    """Генерация чертежей как на ваших примерах"""
    
    num_trusses = int(length / truss_spacing) + 1
    
    # Чертёж 1: Ферма (как ФМ1)
    truss_drawing = f"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                    ГЕОМЕТРИЧЕСКАЯ СХЕМА ФЕРМЫ ФМ1                              ║
║                    Разрез 1:{int(width)}                                        ║
╠════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║                              /\                                                ║
║                             /  \\    h = {calc['truss_height']:.2f}м                          ║
║                            /    \\                                              ║
║                           /      \\                                             ║
║                          /        \\                                            ║
║                         /          \\                                           ║
║                        /            \\                                          ║
║                       /              \\                                         ║
║                      /                \\                                        ║
║                     /__________________\\                                       ║
║                     ←     B={width:.1f}м      →                                ║
║                                                                                ║
║  ГЕОМЕТРИЯ:                                                                    ║
║  • Пролёт: {width:.1f} м                                                       ║
║  • Высота фермы: {calc['truss_height']:.2f} м                                              ║
║  • Количество панелей: {calc['num_panels']} шт.                                          ║
║  • Длина панели: {calc['panel_length']:.2f} м                                            ║
║  • Уклон крыши: {roof_pitch_deg}°                                              ║
║                                                                                ║
║  ЭЛЕМЕНТЫ (как на чертеже):                                                    ║
║  ┌────────────────────────────────────────────────────────────────────────┐   ║
║  │ № │ Элемент          │ Сечение    │ Длина, м │ Кол-во │ Масса, кг  │   ║
║  ├────────────────────────────────────────────────────────────────────────┤   
║  │ 1 │ Верхний пояс     │ {calc['sections']['top_chord']:>8} │   {width*1.1:.1f}  │      2 │        0 │   ║
║  │ 2 │ Нижний пояс      │ {calc['sections']['bottom_chord']:>8} │   {width:.1f}   │      2 │        0 │   ║
║  │ 3 │ Стойки           │ {calc['sections']['posts']:>8} │   {calc['truss_height']:.1f}   │     {calc['num_panels']+1} │        0 │   ║
║  │ 4 │ Раскосы          │ {calc['sections']['web']:>8} │   {width*0.7:.1f}  │     {calc['num_panels']} │        0 │   ║
║  └────────────────────────────────────────────────────────────────────────┘   ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

    # Чертёж 2: Общий вид
    general_view = f"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                         ОБЩИЙ ВИД КАРКАСА ЗДАНИЯ                               ║
║                         План 1:{int(length)}  |  Разрез 1:{int(width)}        ║
╠════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  ПЛАН (вид сверху):                                                            ║
║  ┌──────────────────────────────────────────────────────────────────┐         ║
║  │  ←──────────────────── L = {length:.1f}м ────────────────────→       │         ║
║  │  ┌──────────────────────────────────────────────────────────┐   │         ║
║  │  │  || ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  │   │  B      ║
║  │  │  || ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  │   │  =      ║
║  │  │  || ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  │   │ {width:.1f}м    ║
║  │  └──────────────────────────────────────────────────────────┘   │         ║
║  └──────────────────────────────────────────────────────────────────┘         ║
║     ← {truss_spacing}м →                                                       ║
║                                                                                ║
║  РАЗРЕЗ 1-1:                                                                   ║
║                    /\\   H = {calc['roof_height']:.2f}м                                ║
║                   /  \\                                                        ║
║                  /    \\                                                       ║
║                 /      \\                                                      ║
║                /        \\                                                     ║
║  ─────────────/──────────\\─────────── H = {height:.1f}м                       ║
║  │            │          │            │                                       ║
║  │            │          │            │                                       ║
║  └────────────┴──────────────────────┘                                       
║       ←  {truss_spacing:.1f}м  →                                              ║
║                                                                                ║
║  ОСНОВНЫЕ ДАННЫЕ:                                                              ║
║  • Размеры: {length:.1f}м × {width:.1f}м × {height:.1f}м (Д×Ш×В)                              ║
║  • Количество ферм: {num_trusses} шт.                                          ║
║  • Шаг ферм: {truss_spacing:.1f} м                                                      ║
║  • Площадь: {length*width:.1f} м²                                                        ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

    return truss_drawing, general_view

# ============================================================================
# ОСНОВНОЙ КОД
# ============================================================================

st.title("🏗️ PRO Калькулятор стальных ферм")
st.markdown("**Профессиональная 3D визуализация + чертёжи как на примерах** 📐")

# Расчёт
calc = calculate_structure(width, height, roof_pitch_deg, truss_spacing, snow_district, optimization)

# Метрики
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("❄️ Снег", f"{calc['snow_load']:.2f} кПа")
with col2:
    st.metric("🏗️ Нагрузка", f"{calc['q']:.2f} кН/м")
with col3:
    st.metric("📐 Высота", f"{calc['roof_height']:.2f} м")
with col4:
    st.metric("🔩 Ферм", f"{int(length/truss_spacing)+1} шт.")

st.markdown("---")

# 3D модель
st.subheader("🏗️ 3D Модель каркаса (цветовая схема)")
st.info("""
**Цветовая кодировка (как на ваших 3D рендерах):**
- ⬜ **Белый** - Колонны (стойки)
- 🟩 **Зелёный** - Фермы (пояса, стойки, раскосы)
- 🔷 **Бирюзовый** - Прогоны (горизонтальные балки)
- 🟠 **Оранжевый** - Связи жёсткости
- 🔴 **Красный** - Узлы крепления
""")

fig_3d = create_professional_3d(length, width, height, roof_pitch_deg, truss_spacing, calc)
st.plotly_chart(fig_3d, use_container_width=True)

# Анализ
st.markdown("---")
st.subheader("🔍 Анализ напряжений")

if calc['stress_util'] > 100:
    st.error(f"🔴 **ПЕРЕГРУЗ!** {calc['stress_util']:.1f}% (σ={calc['stress_chord']:.1f} МПа > R={calc['Ry']} МПа)")
elif calc['stress_util'] > 80:
    st.warning(f"🟡 **Повышенное** {calc['stress_util']:.1f}%")
else:
    st.success(f"🟢 **Норма** {calc['stress_util']:.1f}%")

# Сечения
st.markdown("---")
st.subheader("🔩 Рекомендуемые сечения (как на чертежах)")
st.markdown(f"""
**Верхний пояс:** {calc['sections']['top_chord']} мм  
**Нижний пояс:** {calc['sections']['bottom_chord']} мм  
**Стойки фермы:** {calc['sections']['posts']} мм  
**Раскосы:** {calc['sections']['web']} мм  
**Прогоны:** {calc['sections']['purlins']} мм
""")

# Чертёжи
st.markdown("---")
st.subheader("📐 Проектная документация")

truss_draw, general_draw = generate_drawings(length, width, height, roof_pitch_deg, calc)

col1, col2 = st.columns(2)
with col1:
    st.download_button("📐 Ферма ФМ1 (TXT)", truss_draw, f"01_Truss_FM1_{width}m.txt", "text/plain")
with col2:
    st.download_button("🏢 Общий вид (TXT)", general_draw, f"02_General_{length}x{width}m.txt", "text/plain")

# Footer
st.markdown("---")
st.warning("⚠️ **ВАЖНО:** Расчёт предварительный. Для строительства нужен полный проект по СП.")

st.markdown(f"""
<div style='text-align: center; color: gray; margin-top: 50px;'>
<strong>🏗️ Garage Calculator PRO v5.0</strong><br>
{datetime.now().strftime('%d.%m.%Y %H:%M')} | {length}м × {width}м × {height}м
</div>
""", unsafe_allow_html=True)
