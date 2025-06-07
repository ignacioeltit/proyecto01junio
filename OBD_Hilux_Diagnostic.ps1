<#
.SYNOPSIS
Diagnóstico OBD-II para Toyota Hilux 2.4D (2018) - Versión Ultra Estable
#>

# Configuración del adaptador (ajustar según tu hardware)
$OBD_IP = "192.168.0.10"
$OBD_PORT = 35000
$global:obdTimeout = 5000  # Timeout de 5 segundos

# Función mejorada de conexión OBD-II
function Send-OBDCommand {
    param([string]$cmd)
    $socket = $null
    $stream = $null
    $writer = $null
    $reader = $null

    try {
        # 1. Establecer conexión
        $socket = New-Object System.Net.Sockets.TcpClient
        $connectTask = $socket.ConnectAsync($OBD_IP, $OBD_PORT)
        $connectTask.Wait($global:obdTimeout)

        if (-not $socket.Connected) {
            Write-Host "[ERROR] Timeout al conectar" -ForegroundColor Red
            return $null
        }

        # 2. Configurar stream
        $stream = $socket.GetStream()
        $writer = New-Object System.IO.StreamWriter($stream)
        $reader = New-Object System.IO.StreamReader($stream)
        
        # 3. Enviar comando (con formato correcto para ELM327)
        $writer.AutoFlush = $true
        $writer.NewLine = "`r"  # CR requerido por protocolo
        $writer.WriteLine($cmd)
        
        # 4. Esperar respuesta
        Start-Sleep -Milliseconds 800
        $response = $reader.ReadToEnd()

        return $response.Trim() -replace ">", ""
    }
    catch {
        Write-Host "[ERROR] En comando '$cmd': $_" -ForegroundColor Yellow
        return $null
    }
    finally {
        # 5. Limpieza segura
        if ($null -ne $writer) { $writer.Dispose() }
        if ($null -ne $reader) { $reader.Dispose() }
        if ($null -ne $socket) { $socket.Close() }
    }
}

# --- Ejecución principal ---
Clear-Host
Write-Host ""
Write-Host "=== DIAGNOSTICO OBD-II PARA TOYOTA HILUX 2.4D ===" -ForegroundColor Cyan
Write-Host "| IP: $OBD_IP`:$OBD_PORT" -ForegroundColor White
Write-Host "| Protocolo: CAN 500Kbps (ATSP6)" -ForegroundColor White
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Conexión inicial
Write-Host "Conectando al adaptador..." -NoNewline
$response = Send-OBDCommand "ATZ"
if (-not $response) {
    Write-Host " [FALLO]" -ForegroundColor Red
    Write-Host ""
    Write-Host "SOLUCIONES:" -ForegroundColor Yellow
    Write-Host "1. Verifica que el adaptador esté en modo WiFi"
    Write-Host "2. Confirma la IP del adaptador (prueba 'ping $OBD_IP')"
    Write-Host "3. Reinicia el adaptador OBD2"
    exit
}
Write-Host " [OK]" -ForegroundColor Green
Write-Host "Respuesta ATZ: $response"

# 2. Configurar protocolo CAN
Write-Host "Configurando protocolo..." -NoNewline
Send-OBDCommand "ATE0" | Out-Null  # Desactivar eco
Send-OBDCommand "ATH1" | Out-Null  # Mostrar headers
$protocol = Send-OBDCommand "ATSP6"  # Protocolo CAN
if ($protocol -match "OK") {
    Write-Host " [OK]" -ForegroundColor Green
} else {
    Write-Host " [FALLO]" -ForegroundColor Red
    Write-Host "Intenta con 'ATSP0' para autodetección"
}

# 3. Obtener información básica
Write-Host ""
Write-Host "=== INFORMACIÓN DEL VEHÍCULO ===" -ForegroundColor Cyan

# VIN
$vinResponse = Send-OBDCommand "0902"
if ($vinResponse) {
    $vin = ($vinResponse -split '\s+' | Where-Object { $_ -match '^[0-9A-F]{2}' } | ForEach-Object {
        [char][Convert]::ToInt32($_, 16)
    }) -join ""
    Write-Host "VIN: $($vin.Trim())" -ForegroundColor White
} else {
    Write-Host "VIN: No detectado" -ForegroundColor Yellow
}

# 4. Chequear PIDs críticos
Write-Host ""
Write-Host "=== PARÁMETROS CLAVE ===" -ForegroundColor Cyan
$pidsToCheck = @(
    @{Code="010D"; Name="Velocidad"; Unit="km/h"},
    @{Code="010C"; Name="RPM"; Unit="rpm"},
    @{Code="0105"; Name="Temp. refrigerante"; Unit="°C"},
    @{Code="0121"; Name="Distancia con DTC"; Unit="km"},
    @{Code="01B3"; Name="Presión turbo"; Unit="kPa"}
)

foreach ($pid in $pidsToCheck) {
    $response = Send-OBDCommand $pid.Code
    if ($response -match "41" + $pid.Code.Substring(2)) {
        $hexValue = $response.Split()[2]  # Ejemplo: "41 0D 2F" → 2F
        $decimalValue = [Convert]::ToInt32($hexValue, 16)
        Write-Host "$($pid.Name.PadRight(20)): $decimalValue $($pid.Unit)" -ForegroundColor White
    } else {
        Write-Host "$($pid.Name.PadRight(20)): No soportado" -ForegroundColor DarkGray
    }
}

# 5. Cierre profesional
Write-Host ""
Write-Host "Diagnóstico completado a las $(Get-Date -Format "HH:mm:ss")" -ForegroundColor Cyan
Write-Host ""