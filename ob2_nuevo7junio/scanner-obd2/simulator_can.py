"""
simulator_can.py - Simulación de mensajes CAN a partir de un DBC
"""
import random
import threading
import time

def simulate_can_messages(database, message_name, callback, interval_ms=500, stop_event=None):
    """
    Simula mensajes CAN generando valores aleatorios válidos para cada señal del mensaje.
    Args:
        database: Objeto cantools.database.Database
        message_name (str): Nombre del mensaje CAN a simular
        callback (callable): Función a la que se le pasa el diccionario de señales
        interval_ms (int): Intervalo entre mensajes en ms
        stop_event (threading.Event): Permite detener la simulación
    """
    msg = database.get_message_by_name(message_name)
    if not msg:
        raise ValueError(f"Mensaje CAN '{message_name}' no encontrado en el DBC.")
    def _simulate():
        while not (stop_event and stop_event.is_set()):
            data = {}
            for sig in msg.signals:
                minv = sig.minimum if sig.minimum is not None else 0
                maxv = sig.maximum if sig.maximum is not None else 255
                value = random.uniform(minv, maxv) if sig.is_float else random.randint(int(minv), int(maxv))
                data[sig.name] = {'value': round(value, 2), 'unit': sig.unit or ''}
            callback(data)
            time.sleep(interval_ms / 1000.0)
    thread = threading.Thread(target=_simulate, daemon=True)
    thread.start()
    return thread
