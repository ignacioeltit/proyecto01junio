<#
.SYNOPSIS
Diagnóstico OBD-II para Toyota Hilux 2.4 Diesel (2018) - Identificación de PIDs
.DESCRIPTION
Script para mapear PIDs disponibles en vehículos diesel con adaptador ELM327 vía WiFi
#>

# Configuración (ajustar según tu adaptador)
$OBD_IP = "192.168.0.10"  # IP del adaptador ELM327 WiFi
$OBD_PORT = 35000          # Puerto típico de ELM327
$TIMEOUT = 2000            # Timeout en ms

# PIDs específicos para Diesel (Turbo/DPF/EGR)
$DIESEL_PIDS = @(
    "01", "02", "03", "04", "05", "06", "07", "08", "09", "0A", "0B", "0C", "0D",
    "0E", "0F", "10", "11", "12", "13", "14", "15", "1C", "1F", "21", "22",
    "23", "24", "2E", "2F", "30", "31", "32", "33", "34", "3C", "42", "43",
    "44", "45", "46", "47", "49", "4A", "4B", "4C", "4D", "4E", "4F", "52",
    "5C", "5D", "5E", "61", "62", "63", "64", "7E", "A6", "B0", "B1", "B2",
    "B3", "B4", "B5", "B6", "B7", "B8", "B9", "BA", "BB", "BC", "BD", "BE",
    "BF", "C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "CA",
    "CB", "CC", "CD", "CE", "CF"
)

# Diccionario de nombres de PIDs
$PID_NAMES = @{
    "01" = "Monitor Status"; "02" = "Freeze DTC"; "03" = "Fuel System Status"
    "04" = "Engine Load"; "05" = "Coolant Temp"; "06" = "Short Term Fuel Trim"
    "07" = "Long Term Fuel Trim"; "08" = "Intake Pressure"; "09" = "RPM"
    "0A" = "Spark Advance"; "0B" = "Intake Temp"; "0C" = "MAF Rate"
    "0D" = "Vehicle Speed"; "0E" = "Timing Advance"; "0F" = "Intake Air Temp"
    "10" = "MAF Air Flow"; "11" = "Throttle Position"; "1C" = "OBD Standard"
    "21" = "Distance Traveled"; "22" = "Fuel Rail Pressure"; "23" = "Fuel Rail Gauge Pressure"
    "24" = "O2 Sensor 1"; "2F" = "Fuel Level"; "31" = "Distance since DTC clear"
    "33" = "Barometric Pressure"; "42" = "Control Module Voltage"
    "43" = "Absolute Load"; "44" = "Commanded Equiv Ratio"; "45" = "Relative Throttle Pos"
    "46" = "Ambient Air Temp"; "47" = "Absolute Throttle Pos B"; "49" = "Accel Pedal Pos D"
    "4A" = "Accel Pedal Pos E"; "4B" = "Commanded Throttle Actuator"
    "5C" = "Engine Oil Temp"; "61" = "Driver Demand Torque"; "62" = "Actual Torque"
    "63" = "Engine Ref Torque"; "A6" = "O2 Sensor 3"; "B0" = "EGR Error"
    "B1" = "EGR Commanded"; "B2" = "Exhaust Pressure"; "B3" = "Turbo Boost Pressure"
    "B4" = "Intake Manifold Pressure"; "C3" = "DPF Temp"; "C4" = "DPF Differential Pressure"
}

# Función para enviar comandos al ELM327
function Send-OBDCommand {
    param([string]$cmd)
    try {
        $socket = New-Object System.Net.Sockets.TcpClient($OBD_IP, $OBD_PORT)
        $stream = $socket.GetStream()
        $writer = New-Object System.IO.StreamWriter($stream)
        $reader = New-Object System.IO.StreamReader($stream)
        
        $writer.WriteLine($cmd)
        $writer.Flush()
        Start-Sleep -Milliseconds ($TIMEOUT/1000)
        $response = $reader.ReadToEnd() -replace ">", "" -replace "\r", "" -split "\n" | Where-Object { $_ -ne "" }
        
        return $response
    }
    finally {
        if ($null -ne $writer) { $writer.Dispose() }
        if ($null -ne $reader) { $reader.Dispose() }
        if ($null -ne $socket) { $socket.Close() }
    }
}

# Escaneo de PIDs soportados
function Get-SupportedPIDs {
    $supportedPIDs = @{}
    $mode = "01"  # Modo de datos actuales
    
    foreach ($pidGroup in 0..3) {
        $pid = $pidGroup * 0x20
        $hexPID = "{0:X2}" -f $pid
        $response = Send-OBDCommand "$mode$hexPID"
        
        if ($response -match "^[0-9A-F]{3}") {
            $data = $response[0].Substring(4) -replace "\s", ""
            $bits = [Convert]::ToString([Convert]::ToInt32($data, 16), 2).PadLeft(32, '0')
            
            for ($i=0; $i -lt $bits.Length; $i++) {
                if ($bits[$i] -eq '1') {
                    $calculatedPID = $pid + $i + 1
                    $hexPID = "{0:X2}" -f $calculatedPID
                    $supportedPIDs[$hexPID] = $true
                }
            }
        }
    }
    
    return $supportedPIDs.Keys | Sort-Object
}

# Proceso principal
Write-Host "=== INICIANDO DIAGNÓSTICO OBD-II PARA TOYOTA HILUX 2.4 DIESEL (2018) ==="
Write-Host "Conectando al adaptador ELM327 en $OBD_IP`:$OBD_PORT..."

# 1. Verificar conexión
$response = Send-OBDCommand "ATZ"
if (-not $response) {
    Write-Host "Error: No se pudo conectar al adaptador ELM327"
    exit
}
Write-Host "Conexión establecida. Respuesta del adaptador:`n$($response -join "`n")"

# 2. Configurar adaptador para diesel
Send-OBDCommand "ATSP6" | Out-Null  # Protocolo CAN 500Kbps
Send-OBDCommand "ATE0" | Out-Null   # Deshabilitar eco
Send-OBDCommand "ATH1" | Out-Null   # Mostrar headers

# 3. Obtener información básica del vehículo
$vin = Send-OBDCommand "0902" -join "" -replace "\s", ""
$vin = [System.Text.Encoding]::ASCII.GetString(([byte[]]($vin -split '(..)' -ne '' | % { [Convert]::ToByte($_, 16) }))
Write-Host "VIN detectado: $vin"

# 4. Escanear PIDs soportados
Write-Host "`nEscaneando PIDs soportados (modo 01)..."
$supportedPIDs = Get-SupportedPIDs
$supportedDieselPIDs = $DIESEL_PIDS | Where-Object { $_ -in $supportedPIDs }

# 5. Generar reporte
$report = @()
foreach ($pid in $supportedDieselPIDs) {
    $name = if ($PID_NAMES.ContainsKey($pid)) { $PID_NAMES[$pid] } else { "PID Desconocido" }
    $report += [PSCustomObject]@{
        PID = $pid
        Nombre = $name
        Modo = "01"
        Soporte = "Soportado"
        Descripción = if ($name -eq "PID Desconocido") { "Revisar documentación del fabricante" } else { "" }
    }
}

# 6. Exportar resultados
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$csvPath = "OBD_Report_$timestamp.csv"
$report | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8

Write-Host "`n=== RESULTADOS ==="
Write-Host "PIDs soportados detectados: $($supportedDieselPIDs.Count)"
Write-Host "Reporte generado: $csvPath`n"

# Mostrar PIDs críticos para diesel
Write-Host "PIDs clave para motor diesel:"
$report | Where-Object { 
    $_.Nombre -match "Turbo|DPF|EGR|Pressure|Temp" 
} | Format-Table PID, Nombre -AutoSize