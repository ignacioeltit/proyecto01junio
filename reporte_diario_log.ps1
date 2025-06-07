# Ruta del archivo de log
$logPath = "C:\proyecto01junio\app_errors.log"
# Carpeta para los reportes diarios
$reporteDir = "C:\proyecto01junio\reportes_diarios"

if (!(Test-Path $logPath)) {
    Write-Host "No se encontró el archivo de log en $logPath"
    exit 1
}

# Crear la carpeta de reportes si no existe
if (!(Test-Path $reporteDir)) {
    New-Item -ItemType Directory -Path $reporteDir | Out-Null
}

# Expresión regular para detectar fecha en formato [YYYY-MM-DD HH:MM:SS]
$fechaRegex = '^\[(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2}\]'

# Leer todas las líneas
$logLines = Get-Content $logPath
$totalLines = $logLines.Count

Write-Host "Procesando $totalLines líneas del log..." -ForegroundColor Yellow

# Agrupar líneas por fecha
$gruposPorFecha = @{}
$fecha = $null

# Muestra porcentaje de avance
for ($i = 0; $i -lt $totalLines; $i++) {
    $line = $logLines[$i]
    if ($line -match $fechaRegex) {
        $fecha = $matches[1]
        if (-not $gruposPorFecha.ContainsKey($fecha)) {
            $gruposPorFecha[$fecha] = @()
        }
        $gruposPorFecha[$fecha] += $line
    }
    elseif ($fecha) {
        $gruposPorFecha[$fecha] += $line
    }

    # Mostrar porcentaje cada 5% de avance
    if (($i % [math]::Max([math]::Floor($totalLines / 20),1)) -eq 0 -or $i -eq $totalLines - 1) {
        $percent = [math]::Round((($i + 1) / $totalLines) * 100, 0)
        Write-Host "Avance: $percent%" -NoNewline
        if ($percent -lt 100) { Write-Host " ..." -NoNewline }
        Write-Host ""
    }
}

Write-Host "Generando archivos de reportes diarios..." -ForegroundColor Cyan

# Ordenar por fecha descendente (más reciente arriba)
$fechasOrdenadas = $gruposPorFecha.Keys | Sort-Object -Descending

$archivosTotales = $fechasOrdenadas.Count
$contador = 0

foreach ($fecha in $fechasOrdenadas) {
    $reportePath = Join-Path $reporteDir ("reporte_$fecha.log")
    $contenido = @("=== REPORTE DEL DÍA $fecha ===") + $gruposPorFecha[$fecha]
    Set-Content -Path $reportePath -Value $contenido
    $contador++
    $porcentajeArchivos = [math]::Round(($contador / $archivosTotales) * 100, 0)
    Write-Host "[$porcentajeArchivos%] Reporte generado: $reportePath"
}

Write-Host ""
Write-Host "Todos los reportes diarios fueron generados en: $reporteDir" -ForegroundColor Green