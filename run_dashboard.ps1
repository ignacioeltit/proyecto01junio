# Script PowerShell para iniciar adquisición y dashboard web

# Preguntar al usuario si desea usar el emulador o conexión real
echo "¿Deseas usar el emulador OBD-II? (s/n): "
$resp = Read-Host
if ($resp -eq 's') {
    $modo = 'emulador'
    # Iniciar el emulador avanzado emu2 en segundo plano
    echo "Iniciando emulador avanzado emu2..."
    Start-Process -NoNewWindow -FilePath python -ArgumentList "src/obd/emu2.py"
    Start-Sleep -Seconds 2
}
else {
    $modo = ''
}

# Activar entorno virtual
.\venv\Scripts\Activate.ps1

# Iniciar adquisición de datos en segundo plano
echo "Iniciando adquisición de datos..."
Start-Process -NoNewWindow -FilePath python -ArgumentList "-m src.obd.ejemplo_lectura $modo"

# Esperar unos segundos para asegurar que la adquisición inicia
Start-Sleep -Seconds 2

echo "Iniciando dashboard web..."
python src/ui/web_dashboard.py
