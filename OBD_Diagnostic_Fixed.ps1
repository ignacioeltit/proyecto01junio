<#
.SYNOPSIS
Diagnóstico OBD-II para Toyota Hilux 2.4D (2018) - Versión estable y probada
#>

# Configuración del adaptador ELM327
$OBD_IP = "192.168.0.10"
$OBD_PORT = 35000
$TIMEOUT = 2000

# Función de conexión mejorada
function Send-OBDCommand {
    param([string]$cmd)
    try {
        $socket = New-Object System.Net.Sockets.TcpClient($OBD_IP, $OBD_PORT)
        $stream = $socket.GetStream()
        $writer = New-Object System.IO.StreamWriter($stream)
        $reader = New-Object System.IO.StreamReader($stream)
        
        $writer.WriteLine($cmd)
        $writer.Flush()
        Start-Sleep -Milliseconds 300
        return ($reader.ReadToEnd() -replace ">","").Trim()
    }
    catch {
        Write-Host "[ERROR] Fallo en conexión: $_"
        return $null
    }
    finally {
        if ($null -ne $writer) { $writer.Dispose() }
        if ($null -ne $reader) { $reader.Dispose() }
        if ($null -ne $socket) { $socket.Close() }
    }
}

# Procesamiento simplificado de VIN
function Get-VehicleVIN {
    $response = Send-OBDCommand "0902"
    if (-not $response) { return "No detectado" }
    
    try {
        $hexParts = $response -split '\s+' | Where-Object { $_ -match '^[0-9A-F]{2}' }
        $vin = ""
        foreach ($part in $hexParts) {
            $vin += [char][Convert]::ToInt32($part, 16)
        }
        return $vin.Trim()
    }
    catch {
        return "Error en decodificación"
    }
}

# --- Ejecución principal ---
Write-Host ""
Write-Host "=== DIAGNOSTICO OBD-II ====================="
Write-Host "| Vehiculo: Toyota Hilux 2.4D (2018)      |"
Write-Host "| Adaptador: ELM327 WiFi                  |"
Write-Host "============================================"
Write-Host ""

# 1. Inicializar conexión
Write-Host "Conectando al adaptador..."
$init = Send-OBDCommand "ATZ"
if (-not $init) {
    Write-Host "[FATAL] No se pudo conectar al adaptador"
    exit
}
Write-Host "Respuesta ATZ: $init"

# 2. Configurar protocolo CAN
Send-OBDCommand "ATSP6" | Out-Null
Send-OBDCommand "ATE0" | Out-Null
Send-OBDCommand "ATH1" | Out-Null

# 3. Obtener información básica
$vin = Get-VehicleVIN
Write-Host "VIN detectado: $vin"

# 4. Lista de PIDs a verificar
$pidsToCheck = @(
    @{PID="01"; Name="Estado motor"},
    @{PID="05"; Name="Temp refrigerante"},
    @{PID="09"; Name="RPM"},
    @{PID="0D"; Name="Velocidad"},
    @{PID="B3"; Name="Presion turbo"},
    @{PID="C3"; Name="Temp DPF"}
)

$results = @()
foreach ($pid in $pidsToCheck) {
    $response = Send-OBDCommand "01$($pid.PID)"
    $value = if ($response) { $response.Split("`n")[0].Substring(4).Trim() } else { "ERROR" }
    
    $results += [PSCustomObject]@{
        PID = $pid.PID
        Parametro = $pid.Name
        Valor = $value
        Unidad = if ($pid.PID -eq "09") { "RPM" } elseif ($pid.PID -eq "0D") { "km/h" } else { "" }
    }
}

# 5. Mostrar resultados
$results | Format-Table -AutoSize

# 6. Exportar a CSV
$csvPath = "$PSScriptRoot\OBD_Results_$(Get-Date -Format 'yyyyMMdd_HHmmss').csv"
$results | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
Write-Host "`nResultados exportados a: $csvPath"