import streamlit as st
import pandas as pd
import math
import plotly.express as px
import requests
import time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestor de Pokédex TCG", layout="wide", page_icon="📕")

st.divider()

st.title("📕 Dashboard del Binder: Pokédex Nacional")

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Leemos la base de datos (ttl=0 asegura que siempre leamos la versión más reciente)
try:
    df = conn.read(worksheet="Datos", ttl=0, usecols=[0, 1, 2, 3, 4])
    df = df.dropna(how="all") # Limpiamos filas vacías
    if not df.empty:
        df['Dex'] = df['Dex'].astype(int) # Aseguramos que el número Dex sea entero
        df['Pagina'] = df['Pagina'].astype(int)
        df['Slot'] = df['Slot'].astype(int)
except:
    df = pd.DataFrame(columns=["Dex", "Nombre", "Pagina", "Slot", "Idioma/Nota"])

# --- LÓGICA DEL BINDER Y GENERACIONES ---
def calcular_posicion(dex_num):
    if dex_num > 1024: return None, None 
    pagina = math.ceil(dex_num / 16)
    slot_en_pagina = ((dex_num - 1) % 16) + 1
    return pagina, slot_en_pagina

def obtener_numero_dex(nombre_pokemon):
    url = f"https://pokeapi.co/api/v2/pokemon/{nombre_pokemon.lower().strip()}"
    try:
        res = requests.get(url)
        if res.status_code == 200: return res.json()['id']
    except:
        pass
    return None

def obtener_region(dex_num):
    if dex_num <= 151: return "Gen 1 (Kanto)"
    elif dex_num <= 251: return "Gen 2 (Johto)"
    elif dex_num <= 386: return "Gen 3 (Hoenn)"
    elif dex_num <= 493: return "Gen 4 (Sinnoh)"
    elif dex_num <= 649: return "Gen 5 (Unova)"
    elif dex_num <= 721: return "Gen 6 (Kalos)"
    elif dex_num <= 809: return "Gen 7 (Alola)"
    elif dex_num <= 905: return "Gen 8 (Galar)"
    else: return "Gen 9 (Paldea)"

totales_por_gen = {
    "Gen 1 (Kanto)": 151, "Gen 2 (Johto)": 100, "Gen 3 (Hoenn)": 135,
    "Gen 4 (Sinnoh)": 107, "Gen 5 (Unova)": 156, "Gen 6 (Kalos)": 72,
    "Gen 7 (Alola)": 88, "Gen 8 (Galar)": 96, "Gen 9 (Paldea)": 120
}

# --- SECCIÓN 1: ESTADÍSTICAS GENERALES ---
st.header("📈 Estadísticas Generales")
if not df.empty:
    total_cartas = len(df)
    progreso_pct = (total_cartas / 1024) * 100
    
    conteo_paginas = df['Pagina'].value_counts().reset_index()
    conteo_paginas.columns = ['Pagina', 'Cantidad']
    todas_paginas = pd.DataFrame({'Pagina': range(1, 65)})
    datos_completos_paginas = pd.merge(todas_paginas, conteo_paginas, on='Pagina', how='left').fillna(0)
    
    promedio_pag = datos_completos_paginas['Cantidad'].mean()
    mediana_pag = datos_completos_paginas['Cantidad'].median()
    pagina_max = datos_completos_paginas.loc[datos_completos_paginas['Cantidad'].idxmax()]
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Cartas", f"{total_cartas} / 1024")
    col2.metric("Progreso Total", f"{progreso_pct:.2f}%")
    col3.metric("Promedio por Pág", f"{promedio_pag:.1f}")
    col4.metric("Mediana por Pág", f"{int(mediana_pag)}")
    col5.metric("Pág más llena", f"Pág {int(pagina_max['Pagina'])}", f"{int(pagina_max['Cantidad'])} cartas")
else:
    st.info("Añade cartas para ver tus estadísticas.")

st.divider()

# --- SECCIÓN 2: REGISTRO DE CARTAS ---
st.header("➕ Registrar nueva carta")
col_reg1, col_reg2 = st.columns(2)
with col_reg1: nuevo_nombre = st.text_input("Nombre del Pokémon (en inglés)")
with col_reg2: nota_idioma = st.selectbox("Versión / Idioma", ["Japonés", "Inglés", "Chino Simplificado", "Otro"], key="add_idioma")

if st.button("Añadir al Binder"):
    if not nuevo_nombre: st.warning("Por favor, escribe un nombre.")
    else:
        with st.spinner("Buscando en la Pokédex..."):
            nuevo_dex = obtener_numero_dex(nuevo_nombre)
            
        if nuevo_dex is None: st.error("❌ No se encontró el Pokémon.")
        elif nuevo_dex == 1025: st.warning("⚠️ Pecharunt (#1025) excede los 1024 espacios.")
        elif nuevo_dex in df['Dex'].values: st.error(f"¡Ya tienes a {nuevo_nombre.capitalize()}!")
        else:
            pag, slot = calcular_posicion(nuevo_dex)
            nueva_fila = pd.DataFrame([{"Dex": nuevo_dex, "Nombre": nuevo_nombre.capitalize(), "Pagina": pag, "Slot": slot, "Idioma/Nota": nota_idioma}])
            df = pd.concat([df, nueva_fila], ignore_index=True).sort_values(by="Dex")
            
            # --- GUARDADO EN GOOGLE SHEETS ---
            conn.update(worksheet="Datos", data=df)
            st.cache_data.clear() # Limpia la caché para obligar a descargar los datos frescos
            
            st.success(f"✅ ¡{nuevo_nombre.capitalize()} añadido en Página {pag}, espacio {slot}!")
            time.sleep(1)
            st.rerun()

st.divider()

# --- SECCIÓN 3: GRÁFICOS Y GENERACIONES ---
col_graf1, col_graf2 = st.columns([2, 1])

with col_graf1:
    st.subheader("📊 Densidad del Binder")
    if not df.empty:
        fig = px.bar(datos_completos_paginas, x='Pagina', y='Cantidad', labels={'Cantidad': 'Cartas', 'Pagina': 'Página'}, range_y=[0, 16])
        fig.update_traces(marker_color='#ef5350')
        st.plotly_chart(fig, use_container_width=True)

with col_graf2:
    st.subheader("🌍 Progreso por Región")
    if not df.empty:
        df['Region'] = df['Dex'].apply(obtener_region)
        conteo_regiones = df['Region'].value_counts().reset_index()
        conteo_regiones.columns = ['Region', 'Cartas']
        
        tabla_gen = []
        for reg, max_cartas in totales_por_gen.items():
            cartas_actuales = conteo_regiones[conteo_regiones['Region'] == reg]['Cartas'].values
            cartas_actuales = int(cartas_actuales[0]) if len(cartas_actuales) > 0 else 0
            porcentaje = (cartas_actuales / max_cartas) * 100
            tabla_gen.append({"Región": reg, "Progreso": f"{cartas_actuales}/{max_cartas}", "%": f"{porcentaje:.1f}%"})
        
        st.dataframe(pd.DataFrame(tabla_gen), use_container_width=True, hide_index=True)

st.divider()

# --- SECCIÓN 4: HERRAMIENTAS OCULTAS (EXPANDERS) ---
st.header("🛠️ Herramientas de Gestión")

with st.expander("✏️ Editar carta registrada"):
    if not df.empty:
        ce1, ce2, ce3 = st.columns([2, 2, 1])
        with ce1:
            opciones_editar = df['Dex'].astype(str) + " - " + df['Nombre']
            carta_seleccionada = st.selectbox("Selecciona carta", opciones_editar)
        with ce2:
            nuevo_idioma = st.selectbox("Nuevo Idioma", ["Japonés", "Inglés", "Chino Simplificado", "Otro"], key="edit_idioma")
        with ce3:
            st.write(""); st.write("")
            if st.button("Actualizar"):
                dex_edit = int(carta_seleccionada.split(" - ")[0])
                df.loc[df['Dex'] == dex_edit, 'Idioma/Nota'] = nuevo_idioma
                
                # --- ACTUALIZADO EN GOOGLE SHEETS ---
                conn.update(worksheet="Datos", data=df)
                st.cache_data.clear()
                
                st.success("✅ Carta actualizada")
                time.sleep(1)
                st.rerun()
    else:
        st.info("Aún no tienes cartas.")

with st.expander("🔍 Consultar progreso hasta cierta página"):
    max_pag = st.slider("Página límite", 1, 64, 64)
    if not df.empty:
        df_filtrado = df[df['Pagina'] <= max_pag]
        st.info(f"Hasta la página {max_pag}, tienes **{len(df_filtrado)}** cartas de {max_pag * 16} posibles.")

with st.expander("🌐 Porcentaje por Idioma"):
    if not df.empty:
        conteo_idiomas = df['Idioma/Nota'].value_counts(normalize=True) * 100
        df_idiomas = conteo_idiomas.reset_index()
        df_idiomas.columns = ['Idioma / Versión', 'Porcentaje']
        df_idiomas['Porcentaje'] = df_idiomas['Porcentaje'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(df_idiomas, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no tienes cartas para calcular porcentajes.")

with st.expander("📋 Ver inventario completo"):
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
