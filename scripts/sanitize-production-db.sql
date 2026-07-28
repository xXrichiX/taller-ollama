-- Limpieza de datos basura en producción (nombres inválidos, usuarios de prueba).
-- Uso:
--   cd ~/taller-ollama && set -a && source .env && set +a
--   docker compose -f docker-compose.prod.yml exec -T database \
--     mysql -uroot -p"$MYSQL_ROOT_PASSWORD" iespro_taller_app \
--     < scripts/sanitize-production-db.sql

USE iespro_taller_app;

START TRANSACTION;

-- Sucursales con nombres sospechosos → desactivar
UPDATE sucursales
SET nombre = 'Sucursal desactivada', direccion = '', activo = 0
WHERE activo = 1
  AND (
    nombre REGEXP '(?i)(hack|injected|evil|exploit)'
    OR direccion REGEXP '(?i)(hacker|evil)'
  );

-- Conversaciones huérfanas de sucursales desactivadas
DELETE mc FROM mensajes_chat mc
INNER JOIN conversaciones cv ON cv.id = mc.id_conversacion
INNER JOIN sucursales s ON s.id = cv.id_sucursal
WHERE s.activo = 0;

DELETE cv FROM conversaciones cv
INNER JOIN sucursales s ON s.id = cv.id_sucursal
WHERE s.activo = 0;

-- Mensajes con payloads de inyección obvios
DELETE FROM mensajes_chat
WHERE contenido LIKE '%<!ENTITY%'
   OR contenido LIKE '%{{config}}%'
   OR contenido LIKE '%file:///etc/passwd%'
   OR contenido LIKE '%$(whoami)%';

-- Clientes de prueba / inyección en nombre
DELETE cs FROM cita_servicios cs
INNER JOIN citas c ON c.id = cs.id_cita
INNER JOIN clientes cl ON cl.id = c.id_cliente
WHERE cl.email LIKE '%@test.com'
   OR cl.nombre LIKE '%{{%'
   OR cl.nombre LIKE '%<%';

DELETE f FROM fallas_registradas f
INNER JOIN citas c ON c.id = f.id_cita
INNER JOIN clientes cl ON cl.id = c.id_cliente
WHERE cl.email LIKE '%@test.com'
   OR cl.nombre LIKE '%{{%'
   OR cl.nombre LIKE '%<%';

DELETE c FROM citas c
INNER JOIN clientes cl ON cl.id = c.id_cliente
WHERE cl.email LIKE '%@test.com'
   OR cl.nombre LIKE '%{{%'
   OR cl.nombre LIKE '%<%';

DELETE f FROM fallas_registradas f
INNER JOIN vehiculos v ON v.id = f.id_vehiculo
INNER JOIN clientes cl ON cl.id = v.id_cliente
WHERE cl.email LIKE '%@test.com'
   OR cl.nombre LIKE '%{{%'
   OR cl.nombre LIKE '%<%';

DELETE v FROM vehiculos v
INNER JOIN clientes cl ON cl.id = v.id_cliente
WHERE cl.email LIKE '%@test.com'
   OR cl.nombre LIKE '%{{%'
   OR cl.nombre LIKE '%<%';

DELETE FROM clientes
WHERE email LIKE '%@test.com'
   OR email LIKE '%inject%'
   OR nombre LIKE '%{{%'
   OR nombre LIKE '%<%'
   OR nombre LIKE '%;id;%'
   OR nombre LIKE '%$(whoami)%';

-- Inventario con precios absurdos
UPDATE inventario
SET precio_unitario = 0, stock_minimo = 0
WHERE nombre REGEXP '(?i)(exploit|mass_assign)'
   OR precio_unitario >= 999999;

COMMIT;

SELECT COUNT(*) AS sucursales_sospechosas_activas
FROM sucursales
WHERE activo = 1
  AND (
    nombre REGEXP '(?i)(hack|injected|evil|exploit)'
    OR direccion REGEXP '(?i)(hacker|evil)'
  );
