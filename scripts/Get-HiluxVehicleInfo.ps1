param(
    [string]$ElmIP = "192.168.0.10",
    [int]$ElmPort = 35000
)

Write-Host "🚗 DETECCIÓN AUTOMÁTICA TOYOTA HILUX 2018 DIESEL" -ForegroundColor Green

function Send-OBDCommand {
    param([string]$Command)
    try {
        $client = New-Object System.Net.Sockets.TcpClient($ElmIP, $ElmPort)
        $stream = $client.GetStream()
        $writer = New-Object System.IO.StreamWriter($stream)
        $reader = New-Object System.IO.StreamReader($stream)
        $writer.WriteLine($Command)
        $writer.Flush()
        Start-Sleep -Milliseconds 500
        $response = $reader.ReadLine()
        $client.Close()
        return $response
    } catch {
        Write-Error "Error: $_"
        return $null
    }
}

$hiluxPIDs = @{
    "0902" = "VIN (debe contener MR0FB8CD3H0320802)"
    "0904" = "Calibration ID Toyota 2GD"
    "010C" = "RPM Motor"
    "010D" = "Velocidad"
    "0105" = "Temperatura Refrigerante"
    "0123" = "Presión Riel Combustible"
    "0170" = "Presión Boost Turbo"
    "0174" = "RPM Turbocompresor"
    "017C" = "Temperatura DPF"
}

$results = @{}
foreach ($pid in $hiluxPIDs.Keys) {
    $desc = $hiluxPIDs[$pid]
    Write-Host "🔍 Probando PID $pid - $desc" -ForegroundColor Yellow
    $response = Send-OBDCommand $pid
    $results[$pid] = @{
        "description" = $desc
        "response" = $response
        "available" = ($response -ne $null -and $response -ne "NO DATA")
    }
    if ($results[$pid].available) {
        Write-Host "   ✅ Disponible: $response" -ForegroundColor Green
    } else {
        Write-Host "   ❌ No disponible" -ForegroundColor Red
    }
}

$report = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    vehicle = "Toyota Hilux 2018 Diesel"
    chassis = "MR0FB8CD3H0320802"
    pids_tested = $results
}

$outputFile = "hilux_detection_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$report | ConvertTo-Json -Depth 10 | Out-File $outputFile -Encoding UTF8

Write-Host "💾 Reporte guardado: $outputFile" -ForegroundColor Green
