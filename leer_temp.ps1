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
        return $respuesta
    } catch {
        Write-Host ("Error enviando comando " + $comando + ": " + $_)
        return $null
    }
}

function Decodificar-Temperatura {
    param([string]$respuesta)
    # Buscar respuesta tipo "41 05 XX"
    if ($respuesta -match "41\s*05\s*([0-9A-Fa-f]{2})") {
        $hex = $matches[1]
        $valor = [Convert]::ToInt32($hex,16)
        $celsius = $valor - 40
        Write-Host ("Temperatura de refrigerante: $celsius °C")
        return $celsius
    } else {
        Write-Host "No se pudo decodificar la respuesta del PID 05."
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

    # Consulta PID 05 (temperatura de refrigerante)
    $resp05 = Enviar-Comando $stream "0105"
    Write-Host ("Respuesta cruda de 0105: " + $resp05)
    Decodificar-Temperatura $resp05

    $stream.Close()
    $tcpClient.Close()
    Write-Host "Conexión cerrada."
} catch {
    Write-Host ("No se pudo conectar al ELM327 en " + $ip + ":" + $port + " - " + $_)
}
