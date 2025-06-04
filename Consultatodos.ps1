$ip = "192.168.0.10"
$port = 35000

$pid_names = @{
    "01" = "Monitor status since DTCs cleared";
    "02" = "Freeze DTC";
    "03" = "Fuel system status";
    "04" = "Calculated engine load";
    "05" = "Engine coolant temperature";
    "06" = "Short term fuel % trim-Bank 1";
    "07" = "Long term fuel % trim-Bank 1";
    "08" = "Short term fuel % trim-Bank 2";
    "09" = "Long term fuel % trim-Bank 2";
    "0A" = "Fuel pressure";
    "0B" = "Intake manifold absolute pressure";
    "0C" = "Engine RPM";
    "0D" = "Vehicle speed";
    "0E" = "Timing advance";
    "0F" = "Intake air temperature";
    "10" = "MAF air flow rate";
    "11" = "Throttle position";
    "12" = "Commanded secondary air status";
    "13" = "Oxygen sensors present";
    "14" = "Oxygen Sensor 1 - Voltage";
    "15" = "Oxygen Sensor 2 - Voltage";
    "16" = "Oxygen Sensor 3 - Voltage";
    "17" = "Oxygen Sensor 4 - Voltage";
    "18" = "Oxygen Sensor 5 - Voltage";
    "19" = "Oxygen Sensor 6 - Voltage";
    "1A" = "Oxygen Sensor 7 - Voltage";
    "1B" = "Oxygen Sensor 8 - Voltage";
    "1C" = "OBD standards this vehicle conforms to";
    "1D" = "Oxygen sensors present (alt)";
    "1E" = "Auxiliary input status";
    "1F" = "Run time since engine start";
    "20" = "PIDs supported [21-40]";
}

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

function Obtener-PIDs-Soportados {
    param(
        [System.Net.Sockets.NetworkStream]$stream
    )
    $all_supported = @()
    $ranges = @("0100","0120","0140","0160")
    foreach ($range in $ranges) {
        $resp = Enviar-Comando $stream $range
        if ($resp -match "41\s*..?\s*([0-9A-Fa-f]{8})") {
            $bits = $matches[1]
        } elseif ($resp -match "([0-9A-Fa-f]{8})") {
            $bits = $matches[1]
        } else {
            Write-Host "No se encontró mapa de bits válido para $range"
            continue
        }
        $bits_bin = [Convert]::ToString([Convert]::ToUInt32($bits,16),2).PadLeft(32,"0")
        for ($i=0; $i -lt 32; $i++) {
            if ($bits_bin[$i] -eq "1") {
                $pid_dec = ($ranges.IndexOf($range) * 32) + $i + 1
                $pid_hex = "{0:X2}" -f $pid_dec
                $all_supported += $pid_hex
            }
        }
    }
    return $all_supported
}

try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $tcpClient.Connect($ip, $port)
    $stream = $tcpClient.GetStream()
    Write-Host ("Conectado a " + $ip + ":" + $port)
    Enviar-Comando $stream "ATZ"
    Enviar-Comando $stream "ATE0"
    Enviar-Comando $stream "ATL0"
    Enviar-Comando $stream "ATH0"
    Enviar-Comando $stream "ATS0"
    Enviar-Comando $stream "ATI"

    $pids_supported = Obtener-PIDs-Soportados $stream

    Write-Host ""
    Write-Host "=============================="
    Write-Host "PIDs soportados por tu auto:"
    Write-Host "=============================="
    $exportar = @()
    foreach ($pid_val in $pids_supported) {
        $nombre = if ($pid_names.ContainsKey($pid_val)) { $pid_names[$pid_val] } else { "[Definición estándar/extendida]" }
        Write-Host ("PID " + $pid_val + " : " + $nombre)
        $exportar += [PSCustomObject]@{
            PID = $pid_val
            Nombre = $nombre
        }
    }
    Write-Host ""
    Write-Host ("Total de PIDs soportados: " + $pids_supported.Count)

    # Exportar a CSV
    $csv_path = "pids_soportados.csv"
    $exportar | Export-Csv -Path $csv_path -Encoding UTF8 -NoTypeInformation
    Write-Host "Exportado a $csv_path"

    $stream.Close()
    $tcpClient.Close()
    Write-Host "Conexión cerrada."
} catch {
    Write-Host ("No se pudo conectar al ELM327 en " + $ip + ":" + $port + " - " + $_)
}