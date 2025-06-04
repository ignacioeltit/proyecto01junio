# ======================================
# Script PowerShell para consulta básica ELM327 WiFi (llaves corregidas)
# ======================================

$ip = "192.168.0.10"
$port = 35000

function Enviar-Comando {
    param(
        [System.Net.Sockets.NetworkStream]$stream,
        [string]$comando
    )
    try {
        $cmdBytes = [System.Text.Encoding]::ASCII.GetBytes("$comando`r")
        $stream.Write($cmdBytes, 0, $cmdBytes.Length)
        Start-Sleep -Milliseconds 250
        $buffer = New-Object byte[] 1024
        $totalRead = $stream.Read($buffer, 0, $buffer.Length)
        $respuesta = [System.Text.Encoding]::ASCII.GetString($buffer, 0, $totalRead)
        Write-Host ("Enviado: " + $comando + " | Respuesta: " + $respuesta)
        return $respuesta
    }
    catch {
        Write-Host ("Error enviando comando " + $comando + ": " + $_)
        return $null
    }
}

try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $tcpClient.Connect($ip, $port)
    $stream = $tcpClient.GetStream()
    Write-Host ("Conectado a " + $ip + ":" + $port)

    # Inicialización básica ELM327
    Enviar-Comando $stream "ATZ"
    Enviar-Comando $stream "ATE0"
    Enviar-Comando $stream "ATL0"
    Enviar-Comando $stream "ATH0"
    Enviar-Comando $stream "ATS0"
    Enviar-Comando $stream "ATI"

    # Consulta PIDs soportados
    $resp0100 = Enviar-Comando $stream "0100"
    if ($resp0100 -match "[0-9A-Fa-f]{8}") {
        Write-Host ("Respuesta de 0100 (PIDs soportados): " + $matches[0])
    } else {
        Write-Host "No se recibió respuesta válida de la ECU al consultar 0100. ¿El auto está en contacto (ON)?"
    }

    # Puedes agregar más comandos OBD-II aquí:
    # $respRPM = Enviar-Comando $stream "010C"    # RPM
    # $respVSS = Enviar-Comando $stream "010D"    # Velocidad

    $stream.Close()
    $tcpClient.Close()
    Write-Host "Conexión cerrada."
}
catch {
    Write-Host ("No se pudo conectar al ELM327 en " + $ip + ":" + $port + " - " + $_)
}

