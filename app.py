import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
import math
from datetime import datetime

# ============================================================================
# КОНФИГУРАЦИЯ СТРАНИЦЫ
# ============================================================================
st.set_page_config(
    page_title="🏗️ Metal Constructor PRO",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# БАЗЫ ДАННЫХ
# ============================================================================

@st.cache_data
def get_steel_profiles():
    """Профили труб по ГОСТ 30245-2003"""
    return {
        'Квадратные': {
            '60×60×3': {'area': 6.69, 'weight': 5.25, 'ix': 2.29},
            '80×80×3': {'area': 9.09, 'weight': 7.14, 'ix': 3.10},
            '80×80×4': {'area': 11.89, 'weight': 9.33, 'ix': 3.05},
            '100×100×4': {'area': 15.29, 'weight': 12.00, 'ix': 3.95},
            '100×100×5': {'area': 18.84, 'weight': 14.79, 'ix': 3.91},
            '120×120×5': {'area': 22.84, 'weight': 17.93, 'ix': 4.71},
            '120×120×6': {'area': 27.09, 'weight': 21.26, 'ix': 4.67},
            '140×140×6': {'area': 31.89, 'weight': 25.03, 'ix': 5.54},
            '150×150×6': {'area': 34.09, 'weight': 26.76, 'ix': 5.98},
        },
        'Прямоугольные': {
            '80×40×3': {'area': 6.69, 'weight': 5.25, 'ix': 2.82},
            '100×50×4': {'area': 11.89, 'weight': 9.33, 'ix': 3.67},
            '120×60×4': {'area': 14.29, 'weight': 11.22, 'ix': 4.35},
            '140×80×4': {'area': 18.09, 'weight': 14.20, 'ix': 5.24},
        }
    }

@st.cache_data
def get_steel_grades():
    """Марки стали по ГОСТ 27772-2015"""
    return {
        'С245': {'Ry': 240, 'price': 1.0, 'description': 'Базовая'},
        'С255': {'Ry': 250, 'price': 1.05, 'description': 'Улучшенная'},
        'С345': {'Ry': 320, 'price': 1.25, 'description': 'Низколегированная'},
        'С355': {'Ry': 335, 'price': 1.30, 'description': 'Повышенной прочности'},
        'С390': {'Ry': 370, 'price': 1.45, 'description': 'Высокопрочная'},
    }

# ============================================================================
# БОКОВАЯ ПАНЕЛЬ - ПАРАМЕТРЫ
# ============================================================================

with st.sidebar:
    st.title("⚙️ ПАРАМЕТРЫ КОНСТРУКЦИИ")
    
    st.subheader("📐 Геометрия здания")
    length = st.number_input("Длина здания (м)", min_value=6.0, max_value=120.0, value=30.0, step=1.0)
    width = st.number_input("Ширина/Пролёт (м)", min_value=4.0, max_value=40.0, value=12.0, step=1.0)
    height = st.number_input("Высота до карниза (м)", min_value=2.5, max_value=12.0, value=4.0, step=0.5)
    roof_pitch_deg = st.slider("Уклон крыши (градусы)", 5, 45, 15, 1)
    
    st.subheader("🏗️ Конструкция ферм")
    truss_type = st.radio("Тип фермы", 
                          ["Треугольная", "Трапециевидная", "С параллельными поясами"], 
                          index=0)
    truss_spacing = st.slider("Шаг ферм (м)", 2.0, 8.0, 4.0, 0.5)
    num_panels = st.slider("Количество панелей фермы", 6, 16, 8, 1)
    
    st.subheader("🔩 Выбор профилей")
    profiles = get_steel_profiles()
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Стойки (колонны)**")
        columns_profile = st.selectbox("Профиль стоек", 
                                       list(profiles['Квадратные'].keys()), 
                                       index=4, key='cols')
        columns_steel = st.selectbox("Сталь стоек", 
                                     list(get_steel_grades().keys()), 
                                     index=2, key='cols_steel')
    
    with col2:
        st.markdown("**Фермы (пояса)**")
        trusses_profile = st.selectbox("Профиль ферм", 
                                       list(profiles['Квадратные'].keys()), 
                                       index=4, key='truss')
        trusses_steel = st.selectbox("Сталь ферм", 
                                     list(get_steel_grades().keys()), 
                                     index=2, key='truss_steel')
    
    st.markdown("**Прогоны кровли**")
    purlins_profile = st.selectbox("Профиль прогонов", 
                                   list(profiles['Прямоугольные'].keys()), 
                                   index=2, key='purl')
    purlins_steel = st.selectbox("Сталь прогонов", 
                                 list(get_steel_grades().keys()), 
                                 index=2, key='purl_steel')
    
    st.subheader("🌨️ Нагрузки")
    snow_district = st.selectbox("Снеговой район (СП 20.13330)", 
                                 ["I (0.5)", "II (0.7)", "III (1.0)", "IV (1.5)", "V (2.0)"], 
                                 index=3)
    wind_district = st.selectbox("Ветровой район", 
                                 ["Ia", "I", "II", "III", "IV"], 
                                 index=2)

# ============================================================================
# РАСЧЁТНЫЕ ФУНКЦИИ
# ============================================================================

def calculate_loads_and_stresses(length, width, height, roof_pitch_deg, truss_spacing, 
                                  truss_type, num_panels, columns_profile, trusses_profile, 
                                  purlins_profile, columns_steel, trusses_steel, 
                                  purlins_steel, snow_district, wind_district):
    """Расчёт нагрузок и напряжений"""
    
    profiles = get_steel_profiles()
    steel_grades = get_steel_grades()
    
    # Геометрия
    truss_height = width / 6
    roof_height = height + truss_height
    panel_length = width / num_panels
    num_trusses = int(length / truss_spacing) + 1
    
    # Снеговая нагрузка
    snow_map = {"I (0.5)": 0.5, "II (0.7)": 0.7, "III (1.0)": 1.0, "IV (1.5)": 1.5, "V (2.0)": 2.0}
    Sg = snow_map.get(snow_district, 1.5)
    mu = 1.0 if roof_pitch_deg <= 25 else 0.7 if roof_pitch_deg <= 60 else 0.0
    S0 = 0.7 * mu * Sg * 1.4
    
    # Ветровая нагрузка
    wind_map = {"Ia": 0.17, "I": 0.23, "II": 0.30, "III": 0.38, "IV": 0.48}
    w0 = wind_map.get(wind_district, 0.30)
    k = 1.0 if height < 10 else 1.25
    W0 = w0 * k * 0.8 * 1.4
    
    # Постоянная нагрузка
    permanent_load = 0.15
    
    # Общая нагрузка
    total_load = S0 + permanent_load
    q = total_load * truss_spacing
    
    # Усилия в элементах
    M_max = q * width**2 / 8
    N_chord = M_max / truss_height if truss_height > 0 else 0
    V_max = q * width / 2
    N_web = V_max / math.sin(math.radians(45))
    N_post = q * truss_spacing
    
    # Свойства профилей
    columns_props = profiles['Квадратные'][columns_profile]
    trusses_props = profiles['Квадратные'][trusses_profile]
    purlins_props = profiles['Прямоугольные'][purlins_profile]
    
    columns_Ry = steel_grades[columns_steel]['Ry']
    trusses_Ry = steel_grades[trusses_steel]['Ry']
    
    # Напряжения
    stress_columns = N_post * 10 / columns_props['area']
    stress_chord = N_chord * 10 / trusses_props['area']
    stress_web = N_web * 10 / trusses_props['area']
    
    # Утилизация
    util_columns = stress_columns / (columns_Ry * 0.9 / 1.05) * 100
    util_chord = stress_chord / (trusses_Ry * 0.9 / 1.05) * 100
    util_web = stress_web / (trusses_Ry * 0.9 / 1.05) * 100
    
    # Расчёт нагрузок на узлы
    node_loads = []
    for i in range(num_trusses):
        for j in range(num_panels + 1):
            y_pos = j * panel_length
            if y_pos <= width/2:
                z_pos = height + (y_pos / (width/2)) * truss_height
            else:
                z_pos = roof_height - ((y_pos - width/2) / (width/2)) * truss_height
            
            tributary_area = panel_length * truss_spacing if 0 < j < num_panels else (panel_length * truss_spacing) / 2
            load = total_load * tributary_area
            
            node_loads.append({
                'x': i * truss_spacing,
                'y': y_pos,
                'z': z_pos,
                'load': load,
                'node_id': f'N{i+1}-{j+1}'
            })
    
    return {
        'truss_height': truss_height,
        'roof_height': roof_height,
        'num_panels': num_panels,
        'panel_length': panel_length,
        'num_trusses': num_trusses,
        'snow_load': S0,
        'wind_load': W0,
        'total_load': total_load,
        'q': q,
        'M_max': M_max,
        'N_chord': N_chord,
        'N_web': N_web,
        'N_post': N_post,
        'stress_columns': stress_columns,
        'stress_chord': stress_chord,
        'stress_web': stress_web,
        'util_columns': util_columns,
        'util_chord': util_chord,
        'util_web': util_web,
        'node_loads': node_loads,
        'columns_props': columns_props,
        'trusses_props': trusses_props,
        'purlins_props': purlins_props
    }

# ============================================================================
# 3D ВИЗУАЛИЗАЦИЯ
# ============================================================================

def create_frame_3d(length, width, height, roof_pitch_deg, truss_spacing, calc, 
                    show_loads=False, load_mode='frame'):
    """Создание 3D модели каркаса с цветовой индикацией нагрузок"""
    
    fig = go.Figure()
    
    num_trusses = calc['num_trusses']
    num_panels = calc['num_panels']
    panel_length = calc['panel_length']
    truss_height = calc['truss_height']
    roof_height = calc['roof_height']
    
    # Цветовая схема для нагрузок
    def get_load_color(load, max_load, min_load):
        """Градиент от синего (мин) до красного (макс) через зеленый и желтый"""
        if max_load == min_load:
            return 'rgb(0, 100, 255)'
        
        ratio = (load - min_load) / (max_load - min_load)
        
        if ratio < 0.33:
            # Синий -> Зеленый
            r = int(0 + (0 - 0) * (ratio / 0.33))
            g = int(100 + (255 - 100) * (ratio / 0.33))
            b = int(255 + (0 - 255) * (ratio / 0.33))
        elif ratio < 0.66:
            # Зеленый -> Желтый
            r = int(0 + (255 - 0) * ((ratio - 0.33) / 0.33))
            g = 255
            b = int(0 + (0 - 0) * ((ratio - 0.33) / 0.33))
        else:
            # Желтый -> Красный
            r = 255
            g = int(255 + (0 - 255) * ((ratio - 0.66) / 0.34))
            b = 0
        
        return f'rgb({r}, {g}, {b})'
    
    if show_loads and calc['node_loads']:
        loads = [n['load'] for n in calc['node_loads']]
        max_load = max(loads)
        min_load = min(loads)
    
    # 1. СТОЙКИ (КОЛОННЫ)
    for i in range(num_trusses):
        x = i * truss_spacing
        
        # Левая колонна
        if show_loads:
            # Находим нагрузку для этой колонны
            col_load = max([n['load'] for n in calc['node_loads'] 
                           if abs(n['x'] - x) < 0.1 and abs(n['z'] - height) < 0.1], default=0)
            color = get_load_color(col_load, max_load, min_load)
        else:
            color = '#FF4444'
        
        fig.add_trace(go.Scatter3d(
            x=[x, x], y=[0, 0], z=[0, height],
            mode='lines',
            line=dict(color=color, width=12),
            name='Колонны' if i == 0 else '',
            showlegend=(i==0 and not show_loads)
        ))
        
        # Правая колонна
        fig.add_trace(go.Scatter3d(
            x=[x, x], y=[width, width], z=[0, height],
            mode='lines',
            line=dict(color=color, width=12),
            showlegend=False
        ))
    
    # 2. ФЕРМЫ
    for i in range(num_trusses):
        x = i * truss_spacing
        
        # Нижний пояс
        if show_loads:
            chord_load = max([n['load'] for n in calc['node_loads'] 
                             if abs(n['x'] - x) < 0.1 and abs(n['z'] - height) < 0.1], default=0)
            chord_color = get_load_color(chord_load, max_load, min_load)
        else:
            chord_color = '#00FF88'
        
        fig.add_trace(go.Scatter3d(
            x=[x, x], y=[0, width], z=[height, height],
            mode='lines',
            line=dict(color=chord_color, width=10),
            name='Нижний пояс' if i == 0 else '',
            showlegend=(i==0 and not show_loads)
        ))
        
        # Верхний пояс (левая половина)
        y_left = np.linspace(0, width/2, num_panels//2 + 1)
        z_left = height + (y_left / (width/2)) * truss_height
        
        fig.add_trace(go.Scatter3d(
            x=[x]*len(y_left), y=y_left, z=z_left,
            mode='lines',
            line=dict(color=chord_color, width=10),
            showlegend=False
        ))
        
        # Верхний пояс (правая половина)
        y_right = np.linspace(width/2, width, num_panels//2 + 1)
        z_right = roof_height - ((y_right - width/2) / (width/2)) * truss_height
        
        fig.add_trace(go.Scatter3d(
            x=[x]*len(y_right), y=y_right, z=z_right,
            mode='lines',
            line=dict(color=chord_color, width=10),
            showlegend=False
        ))
        
        # Вертикальные стойки фермы
        for j in range(num_panels + 1):
            y_pos = j * panel_length
            if y_pos <= width/2:
                z_top = height + (y_pos / (width/2)) * truss_height
            else:
                z_top = roof_height - ((y_pos - width/2) / (width/2)) * truss_height
            
            if show_loads:
                web_load = max([n['load'] for n in calc['node_loads'] 
                               if abs(n['x'] - x) < 0.1 and abs(n['y'] - y_pos) < 0.1], default=0)
                web_color = get_load_color(web_load, max_load, min_load)
            else:
                web_color = '#FFAA00'
            
            fig.add_trace(go.Scatter3d(
                x=[x, x], y=[y_pos, y_pos], z=[height, z_top],
                mode='lines',
                line=dict(color=web_color, width=6),
                showlegend=False
            ))
        
        # Диагональные раскосы
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
            
            if j % 2 == 0:
                fig.add_trace(go.Scatter3d(
                    x=[x, x], y=[y1, y2], z=[z1, height],
                    mode='lines',
                    line=dict(color=web_color, width=5),
                    showlegend=False
                ))
            else:
                fig.add_trace(go.Scatter3d(
                    x=[x, x], y=[y1, y2], z=[height, z2],
                    mode='lines',
                    line=dict(color=web_color, width=5),
                    showlegend=False
                ))
    
    # 3. ПРОГОНЫ
    num_purlins = 5
    for j in range(num_purlins):
        y_pos = (j + 1) * width / (num_purlins + 1)
        
        if y_pos <= width/2:
            z_pos = height + (y_pos / (width/2)) * truss_height
        else:
            z_pos = roof_height - ((y_pos - width/2) / (width/2)) * truss_height
        
        purlin_color = '#00D9FF' if not show_loads else '#FF6600'
        
        fig.add_trace(go.Scatter3d(
            x=[0, length], y=[y_pos, y_pos], z=[z_pos, z_pos],
            mode='lines',
            line=dict(color=purlin_color, width=11),
            name='Прогоны' if j == 0 else '',
            showlegend=(j==0 and not show_loads)
        ))
    
    # 4. УЗЛЫ (если показываем нагрузки)
    if show_loads and calc['node_loads']:
        node_x = [n['x'] for n in calc['node_loads']]
        node_y = [n['y'] for n in calc['node_loads']]
        node_z = [n['z'] for n in calc['node_loads']]
        node_loads = [n['load'] for n in calc['node_loads']]
        node_colors = [get_load_color(l, max_load, min_load) for l in node_loads]
        node_sizes = [8 + (l / max_load) * 12 for l in node_loads]
        
        fig.add_trace(go.Scatter3d(
            x=node_x, y=node_y, z=node_z,
            mode='markers',
            marker=dict(
                size=node_sizes,
                color=node_colors,
                opacity=0.9,
                line=dict(color='black', width=1)
            ),
            text=[f"Узел: {n['node_id']}<br>Нагрузка: {n['load']:.2f} кН" 
                  for n in calc['node_loads']],
            hoverinfo='text',
            name='Нагрузки на узлы'
        ))
    
    # Настройка layout
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='Длина (м)', range=[0, length]),
            yaxis=dict(title='Ширина (м)', range=[0, width]),
            zaxis=dict(title='Высота (м)', range=[0, roof_height + 2]),
            aspectmode='manual',
            aspectratio=dict(x=2.5, y=1, z=0.8),
            camera=dict(eye=dict(x=2.0, y=1.8, z=1.5))
        ),
        height=700,
        showlegend=True,
        margin=dict(l=0, r=0, t=80, b=0),
        title=dict(
            text="🏗️ 3D Модель каркаса с цветовой индикацией нагрузок" if show_loads else "🏗️ 3D Модель каркаса",
            x=0.5,
            font=dict(size=22, family="Arial Black")
        )
    )
    
    return fig

def create_single_truss_3d(width, truss_height, num_panels):
    """3D модель отдельной фермы"""
    
    fig = go.Figure()
    
    panel_length = width / num_panels
    
    # Нижний пояс
    fig.add_trace(go.Scatter3d(
        x=[0, width], y=[0, 0], z=[0, 0],
        mode='lines',
        line=dict(color='#FF4444', width=12),
        name='Нижний пояс'
    ))
    
    # Верхний пояс
    y_left = np.linspace(0, width/2, num_panels//2 + 1)
    z_left = (y_left / (width/2)) * truss_height
    
    fig.add_trace(go.Scatter3d(
        x=y_left, y=[0]*len(y_left), z=z_left,
        mode='lines',
        line=dict(color='#00FF88', width=10),
        name='Верхний пояс'
    ))
    
    y_right = np.linspace(width/2, width, num_panels//2 + 1)
    z_right = truss_height - ((y_right - width/2) / (width/2)) * truss_height
    
    fig.add_trace(go.Scatter3d(
        x=y_right, y=[0]*len(y_right), z=z_right,
        mode='lines',
        line=dict(color='#00FF88', width=10),
        showlegend=False
    ))
    
    # Вертикальные стойки
    for i in range(num_panels + 1):
        x_pos = i * panel_length
        if x_pos <= width/2:
            z_top = (x_pos / (width/2)) * truss_height
        else:
            z_top = truss_height - ((x_pos - width/2) / (width/2)) * truss_height
        
        fig.add_trace(go.Scatter3d(
            x=[x_pos, x_pos], y=[0, 0], z=[0, z_top],
            mode='lines',
            line=dict(color='#FFAA00', width=6),
            name='Стойки' if i == 0 else '',
            showlegend=(i==0)
        ))
    
    # Диагональные раскосы
    for i in range(num_panels):
        x1 = i * panel_length
        x2 = (i + 1) * panel_length
        
        if x1 <= width/2:
            z1 = (x1 / (width/2)) * truss_height
        else:
            z1 = truss_height - ((x1 - width/2) / (width/2)) * truss_height
        
        if x2 <= width/2:
            z2 = (x2 / (width/2)) * truss_height
        else:
            z2 = truss_height - ((x2 - width/2) / (width/2)) * truss_height
        
        if i % 2 == 0:
            fig.add_trace(go.Scatter3d(
                x=[x1, x2], y=[0, 0], z=[z1, 0],
                mode='lines',
                line=dict(color='#FF00FF', width=5),
                name='Раскосы' if i == 0 else '',
                showlegend=(i==0)
            ))
        else:
            fig.add_trace(go.Scatter3d(
                x=[x1, x2], y=[0, 0], z=[0, z2],
                mode='lines',
                line=dict(color='#FF00FF', width=5),
                showlegend=False
            ))
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='Ширина (м)', range=[-0.5, width + 0.5]),
            yaxis=dict(title='Глубина (м)', range=[-1, 1]),
            zaxis=dict(title='Высота фермы (м)', range=[-0.5, truss_height + 0.5]),
            aspectmode='manual',
            aspectratio=dict(x=2, y=0.3, z=1)
        ),
        height=500,
        showlegend=True,
        margin=dict(l=0, r=0, t=60, b=0),
        title=dict(text="🔧 Отдельная ферма", x=0.5, font=dict(size=18))
    )
    
    return fig

def create_node_detail_3d(node_type='ridge'):
    """Детальная 3D модель узла крепления"""
    
    fig = go.Figure()
    
    if node_type == 'ridge':
        # Коньковый узел
        fig.add_trace(go.Scatter3d(
            x=[-1, 0], y=[0, 0], z=[0, 0.8],
            mode='lines', line=dict(color='#00FF88', width=8),
            name='Левая ферма'
        ))
        fig.add_trace(go.Scatter3d(
            x=[0, 1], y=[0, 0], z=[0.8, 0],
            mode='lines', line=dict(color='#00FF88', width=8),
            name='Правая ферма'
        ))
        fig.add_trace(go.Scatter3d(
            x=[0, 0], y=[-0.5, 0.5], z=[0.8, 0.8],
            mode='lines', line=dict(color='#00D9FF', width=10),
            name='Коньковый прогон'
        ))
        # Накладка
        fig.add_trace(go.Scatter3d(
            x=[-0.1, -0.1, -0.1, -0.1],
            y=[-0.15, -0.15, 0.15, 0.15],
            z=[0.7, 0.85, 0.85, 0.7],
            mode='lines', line=dict(color='#FFCC00', width=5),
            name='Накладка'
        ))
    
    elif node_type == 'eave':
        # Карнизный узел
        fig.add_trace(go.Scatter3d(
            x=[0, 0], y=[0, 0], z=[0, 1.2],
            mode='lines', line=dict(color='#FF4444', width=10),
            name='Колонна'
        ))
        fig.add_trace(go.Scatter3d(
            x=[0, 1], y=[0, 0], z=[1.2, 1.2],
            mode='lines', line=dict(color='#00FF88', width=8),
            name='Ферма'
        ))
        fig.add_trace(go.Scatter3d(
            x=[0, 0.6], y=[0, 0], z=[1.2, 1.6],
            mode='lines', line=dict(color='#00FF88', width=8),
            name='Стропило'
        ))
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='X (м)'),
            yaxis=dict(title='Y (м)'),
            zaxis=dict(title='Z (м)'),
            aspectmode='cube'
        ),
        height=400,
        showlegend=True,
        margin=dict(l=0, r=0, t=60, b=0),
        title=dict(text=f"🔩 Узел: {node_type}", x=0.5, font=dict(size=16))
    )
    
    return fig

# ============================================================================
# ОСНОВНОЙ ИНТЕРФЕЙС
# ============================================================================

st.title("🏗️ Metal Constructor PRO")
st.markdown("**Профессиональный расчёт металлоконструкций с реалистичной 3D визуализацией** 📐")

# Расчёт
calc = calculate_loads_and_stresses(
    length, width, height, roof_pitch_deg, truss_spacing,
    truss_type, num_panels, columns_profile, trusses_profile,
    purlins_profile, columns_steel, trusses_steel,
    purlins_steel, snow_district, wind_district
)

# Вкладки
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏗️ Каркас здания",
    "🔧 Отдельная ферма", 
    "🔩 Узлы крепления",
    "📊 Расчёт нагрузок",
    "📋 Спецификация"
])

with tab1:
    st.subheader("🏗️ 3D Модель каркаса здания")
    
    show_loads = st.checkbox("📊 Показать распределение нагрузок", value=False)
    
    if show_loads:
        st.info("""
        **Цветовая индикация нагрузок:**
        - 🔵 **Синий** - минимальная нагрузка
        - 🟢 **Зелёный** - низкая нагрузка
        - 🟡 **Жёлтый** - средняя нагрузка
        - 🔴 **Красный** - максимальная нагрузка
        """)
    
    fig_frame = create_frame_3d(
        length, width, height, roof_pitch_deg, truss_spacing,
        calc, show_loads=show_loads
    )
    st.plotly_chart(fig_frame, use_container_width=True)

with tab2:
    st.subheader("🔧 Детальная модель фермы")
    
    fig_truss = create_single_truss_3d(width, calc['truss_height'], calc['num_panels'])
    st.plotly_chart(fig_truss, use_container_width=True)
    
    st.info(f"""
    **Параметры фермы:**
    • Пролёт: {width} м
    • Высота: {calc['truss_height']:.2f} м
    • Количество панелей: {calc['num_panels']} шт.
    • Длина панели: {calc['panel_length']:.2f} м
    """)

with tab3:
    st.subheader("🔩 Узлы крепления")
    
    node_type = st.selectbox("Выберите тип узла", 
                             ["Коньковый узел", "Карнизный узел", "Опорный узел"])
    
    node_map = {"Коньковый узел": "ridge", "Карнизный узел": "eave", "Опорный узел": "base"}
    fig_node = create_node_detail_3d(node_map[node_type])
    st.plotly_chart(fig_node, use_container_width=True)

with tab4:
    st.subheader("📊 Расчёт нагрузок и напряжений")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("❄️ Снеговая нагрузка", f"{calc['snow_load']:.2f} кПа")
        st.metric("💨 Ветровая нагрузка", f"{calc['wind_load']:.2f} кПа")
        st.metric("📦 Постоянная нагрузка", f"0.15 кПа")
    
    with col2:
        st.metric("🏗️ Нагрузка на ферму", f"{calc['q']:.2f} кН/м")
        st.metric("📐 Изгибающий момент", f"{calc['M_max']:.2f} кН·м")
        st.metric("⚡ Перерезывающая сила", f"{calc['V_max']:.2f} кН")
    
    with col3:
        st.metric("🔩 Усилие в поясе", f"{calc['N_chord']:.2f} кН")
        st.metric("🔩 Усилие в раскосе", f"{calc['N_web']:.2f} кН")
        st.metric("🔩 Усилие в стойке", f"{calc['N_post']:.2f} кН")
    
    st.markdown("---")
    st.subheader("🔍 Напряжения в элементах")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        util = calc['util_columns']
        status = "🔴 ПЕРЕГРУЗ" if util > 100 else "🟡 Повышенное" if util > 80 else "🟢 Норма"
        st.metric(f"Колонны ({columns_profile})", f"{util:.1f}%", delta=status)
        st.write(f"Напряжение: {calc['stress_columns']:.1f} МПа")
    
    with col2:
        util = calc['util_chord']
        status = "🔴 ПЕРЕГРУЗ" if util > 100 else "🟡 Повышенное" if util > 80 else "🟢 Норма"
        st.metric(f"Пояса ферм ({trusses_profile})", f"{util:.1f}%", delta=status)
        st.write(f"Напряжение: {calc['stress_chord']:.1f} МПа")
    
    with col3:
        util = calc['util_web']
        status = "🔴 ПЕРЕГРУЗ" if util > 100 else "🟡 Повышенное" if util > 80 else "🟢 Норма"
        st.metric(f"Раскосы ({trusses_profile})", f"{util:.1f}%", delta=status)
        st.write(f"Напряжение: {calc['stress_web']:.1f} МПа")

with tab5:
    st.subheader("📋 Спецификация материалов")
    
    steel_grades = get_steel_grades()
    
    data = {
        'Элемент': ['Колонны', 'Фермы (пояса)', 'Фермы (раскосы)', 'Прогоны'],
        'Профиль': [columns_profile, trusses_profile, trusses_profile, purlins_profile],
        'Сталь': [columns_steel, trusses_steel, trusses_steel, purlins_steel],
        'Ry, МПа': [steel_grades[columns_steel]['Ry'], 
                    steel_grades[trusses_steel]['Ry'],
                    steel_grades[trusses_steel]['Ry'],
                    steel_grades[purlins_steel]['Ry']],
        'Вес, кг/м': [calc['columns_props']['weight'],
                      calc['trusses_props']['weight'],
                      calc['trusses_props']['weight'],
                      calc['purlins_props']['weight']]
    }
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

# Footer
st.markdown("---")
st.warning("⚠️ **ВАЖНО:** Расчёт предварительный. Для строительства нужен полный проект по СП.")

st.markdown(f"""
<div style='text-align: center; color: gray; margin-top: 50px;'>
<strong>🏗️ Metal Constructor PRO v3.0</strong><br>
{datetime.now().strftime('%d.%m.%Y %H:%M')} | 
{length}м × {width}м × {height}м
</div>
""", unsafe_allow_html=True)
