import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
import io
from datetime import datetime
import math
import json

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
    wind_district = st.selectbox("Ветровой район", ["Ia", "I", "II", "III", "IV"], index=2)
    
    st.subheader("🎯 Оптимизация")
    optimization = st.radio("Режим", ["💰 Экономия", "⚖️ Баланс", "💪 Прочность"], index=1)

# ============================================================================
# РАСЧЁТНЫЕ ФУНКЦИИ
# ============================================================================

def calculate_node_loads(length, width, height, roof_pitch_deg, truss_spacing, snow_district):
    """Расчёт нагрузок на каждый узел фермы"""
    
    num_trusses = int(length / truss_spacing) + 1
    num_panels = max(8, int(width / 1.5))
    panel_length = width / num_panels
    truss_height = width / 6
    roof_height = height + truss_height
    
    # Снеговая нагрузка
    snow_map = {"I (0.5)": 0.5, "II (0.7)": 0.7, "III (1.0)": 1.0, "IV (1.5)": 1.5, "V (2.0)": 2.0}
    Sg = snow_map.get(snow_district, 1.5)
    S0 = 0.7 * 1.0 * Sg * 1.4
    
    permanent_load = 0.15
    wind_load = 0.23
    total_load = S0 + permanent_load + wind_load
    
    node_loads = []
    
    for truss_num in range(num_trusses):
        truss_x = truss_num * truss_spacing
        
        for panel_num in range(num_panels + 1):
            y_pos = panel_num * panel_length
            
            if y_pos <= width/2:
                z_pos = height + (y_pos / (width/2)) * truss_height
            else:
                z_pos = roof_height - ((y_pos - width/2) / (width/2)) * truss_height
            
            if panel_num == 0 or panel_num == num_panels:
                tributary_area = (panel_length / 2) * truss_spacing
            else:
                tributary_area = panel_length * truss_spacing
            
            vertical_load = total_load * tributary_area
            
            node_loads.append({
                'node_id': f'N{truss_num+1}-{panel_num+1}',
                'x': truss_x,
                'y': y_pos,
                'z': z_pos,
                'vertical_load_kN': vertical_load,
                'snow_load_kN': S0 * tributary_area,
                'permanent_load_kN': permanent_load * tributary_area,
                'wind_load_kN': wind_load * tributary_area,
                'tributary_area_m2': tributary_area
            })
    
    return node_loads, {
        'snow_load_kPa': S0,
        'permanent_load_kPa': permanent_load,
        'wind_load_kPa': wind_load,
        'total_load_kPa': total_load
    }

def calculate_structure(width, height, roof_pitch_deg, truss_spacing, snow_district, optimization):
    """Расчёт по СП 20.13330 и СП 16.13330"""
    
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
        sections = {'top_chord': '75×6', 'bottom_chord': '75×6', 'web': '50×5', 'posts': '75×6', 'purlins': '60×40×3'}
    elif optimization == "💪 Прочность":
        sections = {'top_chord': '100×8', 'bottom_chord': '100×8', 'web': '75×6', 'posts': '100×8', 'purlins': '80×40×4'}
    else:
        sections = {'top_chord': '90×7', 'bottom_chord': '90×7', 'web': '60×6', 'posts': '90×7', 'purlins': '70×40×3'}
    
    Ry = 320
    stress_chord = N_chord * 10 / 15.29
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
# 3D ВИЗУАЛИЗАЦИЯ
# ============================================================================

def create_professional_3d(length, width, height, roof_pitch_deg, truss_spacing, calc, node_loads=None):
    """Профессиональная 3D модель с узлами и нагрузками"""
    
    fig = go.Figure()
    
    num_trusses = int(length / truss_spacing) + 1
    num_panels = calc['num_panels']
    panel_length = calc['panel_length']
    truss_height = calc['truss_height']
    roof_height = calc['roof_height']
    
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
        fig.add_trace(go.Scatter3d(
            x=[x, x], y=[0, 0], z=[0, height],
            mode='lines',
            line=dict(color=colors['columns'], width=10),
            name='Колонны' if i == 0 else '',
            showlegend=(i==0)
        ))
        fig.add_trace(go.Scatter3d(
            x=[x, x], y=[width, width], z=[0, height],
            mode='lines',
            line=dict(color=colors['columns'], width=10),
            showlegend=False
        ))
    
    # Фермы
    for i in range(num_trusses):
        x = i * truss_spacing
        
        fig.add_trace(go.Scatter3d(
            x=[x, x], y=[0, width], z=[height, height],
            mode='lines',
            line=dict(color=colors['trusses'], width=8),
            name='Фермы' if i == 0 else '',
            showlegend=(i==0)
        ))
        
        y_left = np.linspace(0, width/2, num_panels//2 + 1)
        z_left = height + (y_left / (width/2)) * truss_height
        
        fig.add_trace(go.Scatter3d(
            x=[x] * len(y_left),
            y=y_left,
            z=z_left,
            mode='lines',
            line=dict(color=colors['trusses'], width=8),
            showlegend=False
        ))
        
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
                showlegend=False
            ))
    
    # Прогоны
    num_purlins = 5
    for j in range(num_purlins):
        y_pos = (j + 1) * width / (num_purlins + 1)
        
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
    
    # Узлы с размерами по нагрузке
    if node_loads:
        node_x = [node['x'] for node in node_loads]
        node_y = [node['y'] for node in node_loads]
        node_z = [node['z'] for node in node_loads]
        node_sizes = [5 + min(node['vertical_load_kN'] / 5, 15) for node in node_loads]
        node_texts = [f"Узел: {node['node_id']}<br>Нагрузка: {node['vertical_load_kN']:.2f} кН" for node in node_loads]
        
        fig.add_trace(go.Scatter3d(
            x=node_x,
            y=node_y,
            z=node_z,
            mode='markers',
            marker=dict(
                size=node_sizes,
                color=colors['nodes'],
                opacity=0.8,
                line=dict(color='darkred', width=1)
            ),
            text=node_texts,
            hoverinfo='text',
            name='Нагрузки на узлы'
        ))
    else:
        node_positions = []
        for i in range(num_trusses):
            x = i * truss_spacing
            node_positions.append([x, 0, height])
            node_positions.append([x, width, height])
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
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='Длина здания (м)', range=[0, length]),
            yaxis=dict(title='Ширина (м)', range=[0, width]),
            zaxis=dict(title='Высота (м)', range=[0, roof_height + 2]),
            aspectmode='manual',
            aspectratio=dict(x=2.5, y=1, z=0.8)
        ),
        height=700,
        showlegend=True,
        margin=dict(l=0, r=0, t=80, b=0),
        title=dict(
            text="🏗️ 3D Модель каркаса с нагрузками на узлы",
            x=0.5,
            font=dict(size=22, family="Arial Black")
        )
    )
    
    return fig

# ============================================================================
# ГЕНЕРАЦИЯ ЧЕРТЕЖЕЙ И ЭКСПОРТ
# ============================================================================

def generate_dxf_data(length, width, height, calc):
    """Генерация данных для DXF чертежа"""
    dxf_content = f"""0
SECTION
2
HEADER
9
$ACADVER
1
AC1015
0
ENDSEC
0
SECTION
2
TABLES
0
TABLE
2
LAYER
0
LAYER
2
COLUMNS
70
0
62
1
6
CONTINUOUS
0
LAYER
2
TRUSSES
70
0
62
3
6
CONTINUOUS
0
LAYER
2
PURLINS
70
0
62
4
6
CONTINUOUS
0
ENDTAB
0
ENDSEC
0
SECTION
2
ENTITIES
0
LINE
8
COLUMNS
10
0.0
20
0.0
30
0.0
11
0.0
21
0.0
31
{height}
0
LINE
8
COLUMNS
10
{length}
20
0.0
30
0.0
11
{length}
21
0.0
31
{height}
0
LINE
8
TRUSSES
10
0.0
20
0.0
30
{height}
11
0.0
21
{width/2}
31
{calc['roof_height']}
0
LINE
8
TRUSSES
10
0.0
21
{width/2}
30
{calc['roof_height']}
11
0.0
21
{width}
31
{height}
0
LINE
8
TRUSSES
10
0.0
20
0.0
30
{height}
11
0.0
21
{width}
31
{height}
0
ENDSEC
0
EOF
"""
    return dxf_content

def generate_report(length, width, height, calc, node_loads, load_params):
    """Генерация полного отчёта"""
    num_trusses = int(length / calc['q'] / truss_spacing) + 1 if calc['q'] > 0 else 1
    
    report = f"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                    ПРОЕКТ КАРКАСА ЗДАНИЯ                                       ║
║                    Metal Constructor PRO v2.0                                  ║
╠════════════════════════════════════════════════════════════════════════════════╣
║  ДАТА РАСЧЁТА: {datetime.now().strftime('%d.%m.%Y %H:%M')}                                    ║
╠════════════════════════════════════════════════════════════════════════════════╣
║  1. ГЕОМЕТРИЯ ЗДАНИЯ                                                           ║
║  ──────────────────────                                                        ║
║  • Длина: {length:.1f} м                                                           ║
║  • Ширина: {width:.1f} м                                                          ║
║  • Высота: {height:.1f} м                                                         ║
║  • Уклон крыши: {roof_pitch_deg}°                                                       ║
║  • Количество ферм: {num_trusses} шт.                                                  ║
║  • Площадь застройки: {length*width:.1f} м²                                             ║
╠════════════════════════════════════════════════════════════════════════════════╣
║  2. НАГРУЗКИ                                                                   ║
║  ──────────────                                                                ║
║  • Снеговая (норм.): {load_params['snow_load_kPa']:.2f} кПа                                                    ║
║  • Постоянная: {load_params['permanent_load_kPa']:.2f} кПа                                                     ║
║  • Ветровая: {load_params['wind_load_kPa']:.2f} кПа                                                          ║
║  • Итого: {load_params['total_load_kPa']:.2f} кН/м²                                                          ║
╠════════════════════════════════════════════════════════════════════════════════╣
║  3. СЕЧЕНИЯ ЭЛЕМЕНТОВ                                                          ║
║  ──────────────────────                                                        ║
║  • Верхний пояс: {calc['sections']['top_chord']} мм                                              ║
║  • Нижний пояс: {calc['sections']['bottom_chord']} мм                                              ║
║  • Раскосы: {calc['sections']['web']} мм                                                           ║
║  • Стойки: {calc['sections']['posts']} мм                                                          ║
║  • Прогоны: {calc['sections']['purlins']} мм                                                         ║
╠════════════════════════════════════════════════════════════════════════════════╣
║  4. УЗЛЫ КРЕПЛЕНИЯ                                                             ║
║  ──────────────────                                                            ║
║  • Болты: M16-M20 (класс 5.8)                                                 ║
║  • Сварка: электроды Э42А                                                       ║
║  • Антикоррозия: грунтовка ГФ-021                                               ║
╚════════════════════════════════════════════════════════════════════════════════╝

⚠️ ВАЖНО: Данный расчёт является предварительным и не заменяет проектную документацию.
Для строительства необходим полный проект по СП 16.13330 и СП 20.13330 с экспертизой.

Metal Constructor PRO v2.0
"""
    
    return report

# ============================================================================
# ОСНОВНОЙ КОД
# ============================================================================

st.title("🏗️ Metal Constructor PRO")
st.markdown("**Профессиональный расчёт металлоконструкций с 3D визуализацией и экспортом** 📐")

# Расчёты
calc = calculate_structure(width, height, roof_pitch_deg, truss_spacing, snow_district, optimization)
node_loads, load_params = calculate_node_loads(length, width, height, roof_pitch_deg, truss_spacing, snow_district)

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
st.subheader("🏗️ 3D Модель каркаса")
st.info("**Цветовая схема:** ⬜ Колонны | 🟩 Фермы | 🔵 Прогоны | 🔴 Узлы (размер = нагрузка)")

fig_3d = create_professional_3d(length, width, height, roof_pitch_deg, truss_spacing, calc, node_loads)
st.plotly_chart(fig_3d, use_container_width=True)

# Вкладки с дополнительной информацией
tab1, tab2, tab3, tab4 = st.tabs(["📊 Нагрузки на узлы", "📐 Чертёж DXF", "📋 Отчёт", "📥 Экспорт"])

with tab1:
    st.subheader("🔵 Нагрузки на узлы фермы")
    
    node_loads_df = pd.DataFrame(node_loads)
    
    selected_truss = st.selectbox(
        "Выберите ферму для просмотра:",
        options=[f"Ферма {i+1}" for i in range(int(length/truss_spacing)+1)]
    )
    
    truss_num = int(selected_truss.split()[1]) - 1
    truss_nodes = node_loads_df[node_loads_df['node_id'].str.startswith(f'N{truss_num+1}-')]
    
    st.dataframe(
        truss_nodes[['node_id', 'y', 'z', 'vertical_load_kN', 'snow_load_kN', 
                      'permanent_load_kN', 'wind_load_kN', 'tributary_area_m2']].round(2),
        use_container_width=True
    )
    
    st.markdown("### 📊 Параметры нагрузок:")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Снеговая нагрузка", f"{load_params['snow_load_kPa']:.2f} кПа")
    with col2:
        st.metric("Постоянная нагрузка", f"{load_params['permanent_load_kPa']:.2f} кПа")
    with col3:
        st.metric("Ветровая нагрузка", f"{load_params['wind_load_kPa']:.2f} кПа")
    with col4:
        st.metric("Общая нагрузка", f"{load_params['total_load_kPa']:.2f} кПа")

with tab2:
    st.subheader("📐 Чертёж в формате DXF")
    dxf_data = generate_dxf_data(length, width, height, calc)
    st.download_button(
        label="📥 Скачать чертёж DXF",
        data=dxf_data,
        file_name=f"frame_{length}x{width}m.dxf",
        mime="application/dxf",
        use_container_width=True
    )
    
    st.info("📌 **DXF** — формат для AutoCAD и других CAD программ")

with tab3:
    st.subheader("📋 Полный отчёт по проекту")
    report = generate_report(length, width, height, calc, node_loads, load_params)
    st.text_area("Отчёт", report, height=600)
    
    st.download_button(
        label="📥 Скачать отчёт TXT",
        data=report,
        file_name=f"report_{length}x{width}m.txt",
        mime="text/plain",
        use_container_width=True
    )

with tab4:
    st.subheader("📥 Экспорт всех данных")
    
    # CSV с узлами
    node_loads_csv = node_loads_df.to_csv(index=False, sep=';', decimal=',')
    st.download_button(
        label="📊 Нагрузки на узлы (CSV)",
        data=node_loads_csv,
        file_name=f"node_loads_{length}x{width}m.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    # JSON с проектом
    project_json = json.dumps({
        'geometry': {
            'length': length,
            'width': width,
            'height': height,
            'roof_pitch': roof_pitch_deg
        },
        'results': {
            'snow_load': calc['snow_load'],
            'total_load': calc['q'],
            'sections': calc['sections']
        },
        'timestamp': datetime.now().isoformat()
    }, indent=2, ensure_ascii=False)
    
    st.download_button(
        label="💾 Проект (JSON)",
        data=project_json,
        file_name=f"project_{length}x{width}m.json",
        mime="application/json",
        use_container_width=True
    )

# Анализ напряжений
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

# Footer
st.markdown("---")
st.warning("⚠️ **ВАЖНО:** Расчёт предварительный. Для строительства нужен полный проект по СП.")

st.markdown(f"""
<div style='text-align: center; color: gray; margin-top: 50px;'>
<strong>🏗️ Metal Constructor PRO v2.0</strong><br>
{datetime.now().strftime('%d.%m.%Y %H:%M')} | {length}м × {width}м × {height}м
</div>
""", unsafe_allow_html=True)
