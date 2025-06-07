<#
.SYNOPSIS
Conexión OBD-II ultra estable para Toyota Hilux 2.4D
#>

# Configura mejorada para ELM327
$OBD_IP = "192.168.0.10"
$OBD_PORT = 35000
$global:socket = $null

function Connect-OBD {
    try {
        $global:socket = New-Object System.Net.Sockets.TcpClient
        $connectionTask = $global:socket.ConnectAsync($OBD_IP, $OBD_PORT)
        $connectionTask.Wait(3000) # Timeout de 3 segundos
        
        if (-not $global:socket.Connected) {
            throw "Timeout al conectar"
        }
        return $true
    }
    catch {
        Write-Host "[ERROR] Fallo de conexión: $_" -ForegroundColor Red
        return $false
    }
}

function Send-OBDCommand {
    param([string]$cmd)
    try {
        if (-not $global:socket.Connected) {
            if (-not (Connect-OBD)) { return $null }
        }

        $stream = $global:socket.GetStream()
        $writer = New-Object System.IO.StreamWriter($stream)
        $reader = New-Object System.IO.StreamReader($stream)
        
        $writer.WriteLine($cmd)
        $writer.Flush()
        Start-Sleep -Milliseconds 500
        return ($reader.ReadToEnd() -replace ">","").Trim()
    }
    catch {
        Write-Host "[ERROR] En comando '$cmd': $_" -ForegroundColor Yellow
        $global:socket.Close()
        return $null
    }
}

# --- Main Execution ---
Write-Host "`n=== DIAGNÓSTICO OBD-II AVANZADO ===" -ForegroundColor Cyan
Write-Host "Conectando a $OBD_IP`:$OBD_PORT..."

# 1. Conexión inicial
if (-not (Connect-OBD)) {
    Write-Host "`nSOLUCIONES:" -ForegroundColor Red
    Write-Host "1. Verifica que estás conectado a la red WiFi del adaptador"
    Write-Host "2. Prueba reiniciar el adaptador OBD2"
    Write-Host "3. Cambia la IP en el script si es necesario"
    exit
}

# 2. Comandos básicos de prueba
Write-Host "`nProbando comunicación básica..."
$atResponse = Send-OBDCommand "ATZ"
$atiResponse = Send-OBDCommand "ATI"
$protocolResponse = Send-OBDCommand "ATSP0"

Write-Host "Respuestas:`nATZ: $atResponse`nATI: $atiResponse`nProtocolo: $protocolResponse"

# 3. Obtener VIN
$vin = Send-OBDCommand "0902"
if ($vin) {
    $decodedVIN = ($vin -split '\s+' | Where-Object { $_ -match '^[0-9A-F]{2}' } | ForEach-Object {
        [char][Convert]::ToInt32($_, 16)
    }) -join ""
    Write-Host "`nVIN detectado: $($decodedVIN.Trim())" -ForegroundColor Green
}

# 4. Cerrar conexión
if ($global:socket) { $global:socket.Close() }
Write-Host "`nDiagnóstico completado. Revise los resultados." -ForegroundColor Cyan