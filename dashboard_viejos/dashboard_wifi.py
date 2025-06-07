import streamlit as st
import socket
import time
import pandas as pd
from datetime import datetime
import os

# Configuración
st.set_page_config(page_title="🚗 ELM327 WiFi Dashboard", layout="wide")

# Variables de estado
if 'elm_socket' not in st.session_state:
    st.session_state.elm_socket = None
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'data_buffer' not in st.session_state:
    st.session_state.data_buffer = []

def connect_elm327():
    """Conectar al ELM327 WiFi"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("192.168.0.10", 35000))
        
        # Inicializar
        init_commands = ["ATZ\r\n", "ATE0\r\n", "ATL0\r\n", "ATS0\r\n"]
        for cmd in init_commands:
            sock.send(cmd.encode())
            time.sleep(0.3)
            sock.recv(1024)
        
        return sock
    except:
        return None

def read_obd_data(sock):
    """Leer datos OBD del ELM327"""
    try:
        # RPM
        sock.send(b"010C\r\n")
        time.sleep(0.2)
        rpm_response = sock.recv(1024).decode('utf-8', errors='ignore')
        
        # Velocidad  
        sock.send(b"010D\r\n")
        time.sleep(0.2)
        speed_response = sock.recv(1024).decode('utf-8', errors='ignore')
        
        # Temperatura
        sock.send(b"0105\r\n")
        time.sleep(0.2)
        temp_response = sock.recv(1024).decode('utf-8', errors='ignore')
        
        # Procesar respuestas
        rpm = parse_rpm(rpm_response)
        speed = parse_speed(speed_response)
        temp = parse_temp(temp_response)
        
        return {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'rpm': rpm,
            'velocidad': speed,
            'temp_motor': temp
        }
    except:
        return None

def parse_rpm(response):
    try:
        hex_data = response.replace(' ', '').replace('\r', '').replace('\n', '')
        if '41' in hex_data and '0C' in hex_data:
            data_part = hex_data[hex_data.find('410C')+4:hex_data.find('410C')+8]
            rpm = int(data_part, 16) / 4
            return int(rpm)
    except:
        pass
    return 0

def parse_speed(response):
    try:
        hex_data = response.replace(' ', '').replace('\r', '').replace('\n', '')
        if '41' in hex_data and '0D' in hex_data:
            data_part = hex_data[hex_data.find('410D')+4:hex_data.find('410D')+6]
            speed = int(data_part, 16)
            return speed
    except:
        pass
    return 0

def parse_temp(response):
    try:
        hex_data = response.replace(' ', '').replace('\r', '').replace('\n', '')
        if '41' in hex_data and '05' in hex_data:
            data_part = hex_data[hex_data.find('4105')+4:hex_data.find('4105')+6]
            temp = int(data_part, 16) - 40
            return temp
    except:
        pass
    return 0

# INTERFAZ
st.title("🚗💨 ELM327 WiFi Dashboard")

col1, col2 = st.columns(2)

with col1:
    if st.button("🔌 Conectar ELM327 WiFi"):
        with st.spinner("Conectando..."):
            sock = connect_elm327()
            if sock:
                st.session_state.elm_socket = sock
                st.session_state.connected = True
                st.success("✅ Conectado a ELM327 WiFi!")
            else:
                st.error("❌ No se pudo conectar")

with col2:
    if st.session_state.connected and st.button("📊 Leer Datos"):
        data = read_obd_data(st.session_state.elm_socket)
        if data:
            st.session_state.data_buffer.append(data)
            st.success("✅ Datos leídos")
            
            # Mostrar datos
            col3, col4, col5 = st.columns(3)
            with col3:
                st.metric("🔄 RPM", f"{data['rpm']}")
            with col4:
                st.metric("🏎️ Velocidad", f"{data['velocidad']} km/h")
            with col5:
                st.metric("🌡️ Temperatura", f"{data['temp_motor']}°C")

# Mostrar historial
if st.session_state.data_buffer:
    st.subheader("📈 Historial")
    df = pd.DataFrame(st.session_state.data_buffer)
    st.dataframe(df)

# Estado
st.write(f"**Estado:** {'🟢 Conectado' if st.session_state.connected else '🔴 Desconectado'}")