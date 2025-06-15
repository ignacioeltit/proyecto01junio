# Pendientes técnicos OBD2 Scanner

## 2025-06-14

- [ ] **Migración automática de la base vPIC (SQL Server .bak → SQLite) en macOS**
  - No es posible restaurar un .bak de SQL Server directamente en macOS, ya que requiere una instancia de SQL Server accesible (normalmente solo disponible en Windows o en una VM/servidor).
  - Solución recomendada: realizar la restauración y migración en un entorno Windows con SQL Server, y luego copiar el archivo resultante `vpic_lite.db` a la carpeta `data/` en tu Mac.
  - Alternativa: si tienes acceso a un SQL Server en red, modificar el script para apuntar a ese servidor y ejecutar la migración desde macOS.

---

Este pendiente debe resolverse antes de poder usar la decodificación VIN offline con la base local vPIC.
