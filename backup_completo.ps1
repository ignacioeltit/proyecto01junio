# backup_completo.ps1
# Script automatizado para respaldo completo del proyecto OBD-II

$fecha = Get-Date -Format "yyyyMMdd_HHmm"
$backupName = "velreptemtempfuncioando_$fecha"
$backupDir = "$env:USERPROFILE\Desktop\$backupName"
$proyectoDir = "C:\proyecto01junio"
$zipFile = "$env:USERPROFILE\Desktop\$backupName.zip"

# 1. Crear carpeta de respaldo
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

# 2. Copiar todo el proyecto
Copy-Item -Path "$proyectoDir\*" -Destination $backupDir -Recurse -Force

# 3. Actualizar o crear bitácora y README
$bitacora = "$backupDir\bitacora.txt"
Add-Content -Path $bitacora -Value "`n---`n[$fecha] Backup de funcionamiento completo realizado con éxito. Nombre: $backupName`nUsuario: $env:USERNAME`n"

$readme = "$backupDir\README.md"
if (Test-Path $readme) {
    Add-Content -Path $readme -Value "`n### [$fecha] - Hito de backup: $backupName`n"
} else {
    Set-Content -Path $readme -Value "# Respaldo de Funcionamiento Completo`n`nFecha: $fecha`nNombre backup: $backupName`n"
}

# 4. Comprimir el respaldo
Compress-Archive -Path $backupDir\* -DestinationPath $zipFile -Force

Write-Host "✅ Backup completo creado en: $zipFile"
Write-Host "🕒 Fecha y hora en nombre del respaldo: $backupName"
Write-Host "📄 Bitácora y README actualizados."
