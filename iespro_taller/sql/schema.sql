DROP DATABASE IF EXISTS iespro_taller_app;
CREATE DATABASE IF NOT EXISTS iespro_taller_app
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE iespro_taller_app;

CREATE TABLE IF NOT EXISTS sucursales (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  direccion VARCHAR(255),
  activo TINYINT(1) NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS roles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(60) NOT NULL UNIQUE,
  descripcion VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS puestos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  password VARCHAR(120) NOT NULL,
  id_rol INT NOT NULL,
  id_sucursal INT,
  es_cliente TINYINT(1) NOT NULL DEFAULT 0,
  es_trabajador TINYINT(1) NOT NULL DEFAULT 0,
  id_puesto INT,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  FOREIGN KEY (id_rol) REFERENCES roles(id),
  FOREIGN KEY (id_sucursal) REFERENCES sucursales(id),
  FOREIGN KEY (id_puesto) REFERENCES puestos(id)
);

CREATE TABLE IF NOT EXISTS clientes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  telefono VARCHAR(30),
  email VARCHAR(120),
  id_usuario INT,
  FOREIGN KEY (id_usuario) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS marcas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS tipos_combustible (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(60) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS tipos_unidad (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS vehiculos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  numero_economico VARCHAR(40) NOT NULL,
  placa VARCHAR(20) NOT NULL,
  serie VARCHAR(60) NOT NULL,
  id_marca INT NOT NULL,
  modelo VARCHAR(80) NOT NULL,
  id_tipo_combustible INT NOT NULL,
  id_tipo_unidad INT NOT NULL,
  kilometraje INT NOT NULL DEFAULT 0,
  dias_mantenimiento INT NOT NULL DEFAULT 90,
  observaciones TEXT,
  id_cliente INT NOT NULL,
  id_usuario INT NOT NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  FOREIGN KEY (id_marca) REFERENCES marcas(id),
  FOREIGN KEY (id_tipo_combustible) REFERENCES tipos_combustible(id),
  FOREIGN KEY (id_tipo_unidad) REFERENCES tipos_unidad(id),
  FOREIGN KEY (id_cliente) REFERENCES clientes(id),
  FOREIGN KEY (id_usuario) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS tipos_mantenimiento (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  descripcion TEXT,
  precio DECIMAL(10,2) NOT NULL DEFAULT 0,
  id_sucursal INT NOT NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  FOREIGN KEY (id_sucursal) REFERENCES sucursales(id)
);

CREATE TABLE IF NOT EXISTS horarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  fecha DATE NOT NULL,
  hora TIME NOT NULL,
  disponible TINYINT(1) NOT NULL DEFAULT 1,
  id_sucursal INT NOT NULL,
  UNIQUE KEY uk_horario (fecha, hora, id_sucursal),
  FOREIGN KEY (id_sucursal) REFERENCES sucursales(id)
);

CREATE TABLE IF NOT EXISTS mi_taller (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  id_sucursal INT NOT NULL UNIQUE,
  FOREIGN KEY (id_sucursal) REFERENCES sucursales(id)
);

CREATE TABLE IF NOT EXISTS islas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(80) NOT NULL,
  id_mi_taller INT NOT NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  FOREIGN KEY (id_mi_taller) REFERENCES mi_taller(id)
);

CREATE TABLE IF NOT EXISTS isla_mecanicos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  id_isla INT NOT NULL,
  id_usuario INT NOT NULL,
  es_responsable TINYINT(1) NOT NULL DEFAULT 0,
  UNIQUE KEY uk_isla_usuario (id_isla, id_usuario),
  FOREIGN KEY (id_isla) REFERENCES islas(id),
  FOREIGN KEY (id_usuario) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS citas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  id_cliente INT NOT NULL,
  id_vehiculo INT NOT NULL,
  id_sucursal INT NOT NULL,
  fecha_cita DATETIME NOT NULL,
  id_horario INT,
  id_mecanico INT NOT NULL,
  id_isla INT NOT NULL,
  descripcion_fallo TEXT NOT NULL,
  fecha_compromiso DATE NOT NULL,
  hora_compromiso TIME NOT NULL,
  estado ENUM('PENDIENTE','EN_PROCESO','COMPLETADA','CANCELADA') NOT NULL DEFAULT 'PENDIENTE',
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_cliente) REFERENCES clientes(id),
  FOREIGN KEY (id_vehiculo) REFERENCES vehiculos(id),
  FOREIGN KEY (id_sucursal) REFERENCES sucursales(id),
  FOREIGN KEY (id_horario) REFERENCES horarios(id),
  FOREIGN KEY (id_mecanico) REFERENCES usuarios(id),
  FOREIGN KEY (id_isla) REFERENCES islas(id)
);

CREATE TABLE IF NOT EXISTS cita_servicios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  id_cita INT NOT NULL,
  id_tipo_mantenimiento INT NOT NULL,
  FOREIGN KEY (id_cita) REFERENCES citas(id) ON DELETE CASCADE,
  FOREIGN KEY (id_tipo_mantenimiento) REFERENCES tipos_mantenimiento(id)
);

CREATE TABLE IF NOT EXISTS fallas_registradas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  id_cita INT,
  id_vehiculo INT NOT NULL,
  descripcion TEXT NOT NULL,
  diagnostico TEXT,
  resuelto TINYINT(1) NOT NULL DEFAULT 0,
  registrado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_cita) REFERENCES citas(id) ON DELETE SET NULL,
  FOREIGN KEY (id_vehiculo) REFERENCES vehiculos(id)
);

CREATE TABLE IF NOT EXISTS conversaciones (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_usuario INT NOT NULL,
  id_sucursal INT NOT NULL,
  titulo VARCHAR(255),
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (id_usuario) REFERENCES usuarios(id),
  FOREIGN KEY (id_sucursal) REFERENCES sucursales(id)
);

CREATE TABLE IF NOT EXISTS mensajes_chat (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_conversacion BIGINT NOT NULL,
  role ENUM('user','assistant','system') NOT NULL,
  contenido TEXT NOT NULL,
  route VARCHAR(32),
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_conversacion) REFERENCES conversaciones(id) ON DELETE CASCADE,
  INDEX idx_mensajes_conversacion (id_conversacion, creado_en)
);


USE iespro_taller_app;

INSERT IGNORE INTO sucursales (id, nombre, direccion) VALUES
(1, 'Sucursal Centro', 'Av. Principal 100'),
(2, 'Sucursal Norte', 'Blvd. Norte 250');

INSERT IGNORE INTO roles (id, nombre, descripcion) VALUES
(1, 'ADMIN', 'Administrador del sistema'),
(2, 'JEFE_TALLER', 'Jefe de taller'),
(3, 'MECANICO', 'Mecánico'),
(4, 'CLIENTE', 'Cliente del taller');

INSERT IGNORE INTO puestos (id, nombre) VALUES
(1, 'Gerente'),
(2, 'Jefe de Taller'),
(3, 'Mecánico Senior'),
(4, 'Mecánico');

INSERT IGNORE INTO usuarios (id, nombre, email, password, id_rol, id_sucursal, es_cliente, es_trabajador, id_puesto) VALUES
(1, 'Admin Sistema', 'admin@iespro.mx', 'admin123', 1, 1, 0, 1, 1),
(2, 'Jefe Taller Centro', 'jefe@iespro.mx', 'jefe123', 2, 1, 0, 1, 2),
(3, 'Carlos Mecánico', 'carlos@iespro.mx', 'mec123', 3, 1, 0, 1, 4),
(4, 'Ana Mecánica', 'ana@iespro.mx', 'mec123', 3, 1, 0, 1, 4),
(5, 'Roberto García', 'roberto@cliente.mx', 'cli123', 4, 1, 1, 0, NULL),
(6, 'María López', 'maria@cliente.mx', 'cli123', 4, 1, 1, 0, NULL);

INSERT IGNORE INTO clientes (id, nombre, telefono, email, id_usuario) VALUES
(1, 'Roberto García', '555-1001', 'roberto@cliente.mx', 5),
(2, 'María López', '555-1002', 'maria@cliente.mx', 6);

INSERT IGNORE INTO marcas (id, nombre) VALUES
(1, 'Nissan'), (2, 'Toyota'), (3, 'Ford'), (4, 'Chevrolet');

INSERT IGNORE INTO tipos_combustible (id, nombre) VALUES
(1, 'Gasolina'), (2, 'Diésel'), (3, 'Híbrido'), (4, 'Eléctrico');

INSERT IGNORE INTO tipos_unidad (id, nombre) VALUES
(1, 'Sedán'), (2, 'Pickup'), (3, 'SUV'), (4, 'Camioneta');

INSERT IGNORE INTO vehiculos (id, numero_economico, placa, serie, id_marca, modelo, id_tipo_combustible, id_tipo_unidad, kilometraje, dias_mantenimiento, observaciones, id_cliente, id_usuario) VALUES
(1, 'VEH-001', 'ABC-123', 'SN001', 1, 'Versa 2020', 1, 1, 45000, 90, 'Cliente frecuente', 1, 5),
(2, 'VEH-002', 'XYZ-789', 'SN002', 2, 'Hilux 2019', 2, 2, 82000, 60, NULL, 1, 5),
(3, 'VEH-003', 'LMN-456', 'SN003', 3, 'Ranger 2021', 2, 2, 31000, 90, NULL, 2, 6);

INSERT IGNORE INTO tipos_mantenimiento (id, nombre, descripcion, precio, id_sucursal) VALUES
(1, 'Cambio de aceite', 'Aceite sintético y filtro', 850.00, 1),
(2, 'Afinación mayor', 'Bujías, filtros, limpieza', 3200.00, 1),
(3, 'Frenos delanteros', 'Balatas y rectificado de discos', 2800.00, 1),
(4, 'Diagnóstico general', 'Escaneo y revisión', 500.00, 1),
(5, 'Suspensión', 'Revisión de amortiguadores', 1500.00, 1);

INSERT IGNORE INTO horarios (fecha, hora, disponible, id_sucursal) VALUES
('2026-06-09', '09:00:00', 1, 1),
('2026-06-09', '10:00:00', 1, 1),
('2026-06-09', '11:00:00', 1, 1),
('2026-06-09', '15:00:00', 1, 1),
('2026-06-10', '09:00:00', 1, 1),
('2026-06-10', '10:00:00', 1, 1),
('2026-06-10', '14:00:00', 1, 1),
('2026-06-11', '09:00:00', 1, 1),
('2026-06-11', '11:00:00', 1, 1);

INSERT IGNORE INTO mi_taller (id, nombre, id_sucursal) VALUES
(1, 'Taller Centro', 1);

INSERT IGNORE INTO islas (id, nombre, id_mi_taller) VALUES
(1, 'Isla 1 - Diagnóstico', 1),
(2, 'Isla 2 - Mecánica', 1),
(3, 'Isla 3 - Frenos', 1);

INSERT IGNORE INTO isla_mecanicos (id_isla, id_usuario, es_responsable) VALUES
(1, 3, 1),
(2, 3, 0),
(2, 4, 1),
(3, 4, 0);

INSERT IGNORE INTO citas (id, id_cliente, id_vehiculo, id_sucursal, fecha_cita, id_horario, id_mecanico, id_isla, descripcion_fallo, fecha_compromiso, hora_compromiso, estado) VALUES
(1, 1, 1, 1, '2026-06-09 09:00:00', 1, 3, 1, 'Ruido metálico al frenar en ciudad, posible desgaste de balatas', '2026-06-09', '18:00:00', 'PENDIENTE'),
(2, 1, 2, 1, '2026-06-09 10:00:00', 2, 4, 3, 'Pedal de freno esponjoso, posible aire en líneas o fuga de líquido', '2026-06-10', '17:00:00', 'EN_PROCESO'),
(3, 2, 3, 1, '2026-06-10 09:00:00', 5, 3, 2, 'Vibración en volante a alta velocidad, posible balanceo o suspensión', '2026-06-10', '16:00:00', 'PENDIENTE');

INSERT IGNORE INTO cita_servicios (id_cita, id_tipo_mantenimiento) VALUES
(1, 3), (1, 4),
(2, 3), (2, 4),
(3, 5), (3, 4);

INSERT IGNORE INTO fallas_registradas (id_cita, id_vehiculo, descripcion, diagnostico, resuelto) VALUES
(1, 1, 'Ruido metálico al frenar en ciudad, posible desgaste de balatas', 'Balatas delanteras al 15%, discos rayados', 0),
(2, 2, 'Pedal de freno esponjoso, posible aire en líneas o fuga de líquido', 'Aire en circuito, manguera con microfuga', 0),
(3, 3, 'Vibración en volante a alta velocidad, posible balanceo o suspensión', NULL, 0),
(NULL, 1, 'Chirrido al frenar en bajada, similar a balatas gastadas', 'Se cambiaron balatas hace 6 meses', 1);

-- ---------------------------------------------------------------------------
-- Datos ampliados para demo (UI + agente + RAG)
-- ---------------------------------------------------------------------------

INSERT IGNORE INTO usuarios (id, nombre, email, password, id_rol, id_sucursal, es_cliente, es_trabajador, id_puesto) VALUES
(7, 'Jorge Medina', 'jorge@cliente.mx', 'cli123', 4, 1, 1, 0, NULL),
(8, 'Patricia Ruiz', 'patricia@cliente.mx', 'cli123', 4, 1, 1, 0, NULL),
(9, 'Luis Hernández', 'luis@cliente.mx', 'cli123', 4, 1, 1, 0, NULL),
(10, 'Carmen Vega', 'carmen@cliente.mx', 'cli123', 4, 1, 1, 0, NULL),
(11, 'Diego Morales', 'diego@cliente.mx', 'cli123', 4, 1, 1, 0, NULL),
(12, 'Miguel Torre', 'miguel@iespro.mx', 'mec123', 3, 1, 0, 1, 3),
(13, 'Laura Recepción', 'laura@iespro.mx', 'rec123', 2, 1, 0, 1, 2);

INSERT IGNORE INTO clientes (id, nombre, telefono, email, id_usuario) VALUES
(3, 'Jorge Medina', '555-1003', 'jorge@cliente.mx', 7),
(4, 'Patricia Ruiz', '555-1004', 'patricia@cliente.mx', 8),
(5, 'Luis Hernández', '555-1005', 'luis@cliente.mx', 9),
(6, 'Carmen Vega', '555-1006', 'carmen@cliente.mx', 10),
(7, 'Diego Morales', '555-1007', 'diego@cliente.mx', 11);

INSERT IGNORE INTO marcas (id, nombre) VALUES
(5, 'Honda'), (6, 'Mazda'), (7, 'Volkswagen');

INSERT IGNORE INTO vehiculos (id, numero_economico, placa, serie, id_marca, modelo, id_tipo_combustible, id_tipo_unidad, kilometraje, dias_mantenimiento, observaciones, id_cliente, id_usuario) VALUES
(4, 'VEH-004', 'QWE-456', 'SN004', 4, 'Aveo 2018', 1, 1, 67000, 90, 'Flota taxi', 3, 7),
(5, 'VEH-005', 'RTY-789', 'SN005', 2, 'Corolla 2022', 3, 1, 22000, 120, NULL, 4, 8),
(6, 'VEH-006', 'UIO-321', 'SN006', 1, 'NP300 2020', 2, 2, 95000, 60, 'Uso comercial', 5, 9),
(7, 'VEH-007', 'PAS-654', 'SN007', 5, 'CR-V 2021', 1, 3, 38000, 90, NULL, 6, 10),
(8, 'VEH-008', 'DFG-987', 'SN008', 3, 'Escape 2019', 1, 3, 54000, 90, NULL, 7, 11),
(9, 'VEH-009', 'HJK-111', 'SN009', 6, 'CX-5 2023', 1, 3, 15000, 120, 'Garantía vigente', 2, 6),
(10, 'VEH-010', 'ZXC-222', 'SN010', 7, 'Jetta 2017', 1, 1, 112000, 60, 'Revisión frecuente', 1, 5);

INSERT IGNORE INTO tipos_mantenimiento (id, nombre, descripcion, precio, id_sucursal) VALUES
(6, 'Alineación y balanceo', 'Ajuste de geometría y balanceo de 4 ruedas', 950.00, 1),
(7, 'Cambio de bandas', 'Banda de accesorios y tensor', 1800.00, 1),
(8, 'Servicio de transmisión', 'Cambio de aceite ATF y filtro', 2400.00, 1),
(9, 'Climatización', 'Recarga y revisión de A/C', 1200.00, 1),
(10, 'Lavado express', 'Lavado exterior e interior básico', 250.00, 1);

INSERT IGNORE INTO horarios (fecha, hora, disponible, id_sucursal) VALUES
('2026-06-11', '10:00:00', 1, 1),
('2026-06-11', '14:00:00', 1, 1),
('2026-06-11', '15:00:00', 1, 1),
('2026-06-11', '16:00:00', 1, 1),
('2026-06-12', '09:00:00', 1, 1),
('2026-06-12', '10:00:00', 1, 1),
('2026-06-12', '11:00:00', 1, 1),
('2026-06-12', '14:00:00', 1, 1),
('2026-06-12', '15:00:00', 1, 1),
('2026-06-13', '09:00:00', 1, 1),
('2026-06-13', '11:00:00', 1, 1),
('2026-06-13', '16:00:00', 1, 1);

INSERT IGNORE INTO isla_mecanicos (id_isla, id_usuario, es_responsable) VALUES
(1, 12, 0),
(3, 12, 1),
(2, 2, 0);

INSERT IGNORE INTO citas (id, id_cliente, id_vehiculo, id_sucursal, fecha_cita, id_horario, id_mecanico, id_isla, descripcion_fallo, fecha_compromiso, hora_compromiso, estado) VALUES
(4, 3, 4, 1, '2026-06-11 09:00:00', NULL, 3, 2, 'Pérdida de potencia en subidas, check engine encendido', '2026-06-11', '18:00:00', 'PENDIENTE'),
(5, 4, 5, 1, '2026-06-11 11:00:00', NULL, 4, 1, 'A/C no enfría, posible fuga de refrigerante', '2026-06-11', '17:00:00', 'PENDIENTE'),
(6, 5, 6, 1, '2026-06-12 09:00:00', NULL, 12, 2, 'Ruido en cardán al acelerar en pickup cargada', '2026-06-12', '18:00:00', 'PENDIENTE'),
(7, 6, 7, 1, '2026-06-10 14:00:00', NULL, 4, 3, 'Luces de ABS intermitentes al frenar', '2026-06-10', '16:00:00', 'EN_PROCESO'),
(8, 7, 8, 1, '2026-06-08 10:00:00', NULL, 3, 1, 'Chequeo general antes de viaje largo', '2026-06-08', '15:00:00', 'COMPLETADA'),
(9, 2, 9, 1, '2026-06-07 11:00:00', NULL, 12, 2, 'Servicio de 15,000 km programado', '2026-06-07', '14:00:00', 'COMPLETADA'),
(10, 1, 10, 1, '2026-06-06 09:00:00', NULL, 4, 3, 'Temblor en volante entre 80 y 100 km/h', '2026-06-06', '13:00:00', 'COMPLETADA'),
(11, 3, 4, 1, '2026-06-05 15:00:00', NULL, 3, 1, 'Cliente canceló por falta de refacción', '2026-06-05', '18:00:00', 'CANCELADA'),
(12, 4, 5, 1, '2026-06-13 09:00:00', NULL, 12, 1, 'Olor a gasolina en arranque en frío', '2026-06-13', '17:00:00', 'PENDIENTE');

INSERT IGNORE INTO cita_servicios (id_cita, id_tipo_mantenimiento) VALUES
(4, 4), (4, 2),
(5, 9), (5, 4),
(6, 5), (6, 8),
(7, 3), (7, 4),
(8, 4), (8, 1),
(9, 1), (9, 6),
(10, 6), (10, 3),
(11, 4),
(12, 4), (12, 2);

INSERT IGNORE INTO fallas_registradas (id_cita, id_vehiculo, descripcion, diagnostico, resuelto) VALUES
(4, 4, 'Pérdida de potencia en subidas, check engine encendido', 'Sensor MAP con lectura errática', 0),
(5, 5, 'A/C no enfría, posible fuga de refrigerante', 'Fuga en válvula Schrader del compresor', 0),
(6, 6, 'Ruido en cardán al acelerar en pickup cargada', 'Cruzeta con juego, requiere reemplazo', 0),
(7, 7, 'Luces de ABS intermitentes al frenar', 'Sensor de velocidad trasero sucio', 0),
(8, 8, 'Chequeo general antes de viaje largo', 'Unidad apta, niveles OK', 1),
(9, 9, 'Servicio de 15,000 km programado', 'Aceite y filtros cambiados', 1),
(10, 10, 'Temblor en volante entre 80 y 100 km/h', 'Balanceo y rotación de llantas', 1),
(12, 5, 'Olor a gasolina en arranque en frío', NULL, 0),
(NULL, 6, 'Humo negro en aceleración fuerte en diesel', 'Filtro de aire obstruido', 1),
(NULL, 7, 'Ventilador del A/C hace ruido al encender', 'Rodamiento de blower desgastado', 0),
(NULL, 8, 'Fuga de aceite en tapa de balancines', 'Empaque endurecido', 1),
(NULL, 9, 'Parabrisas con rajadura pequeña lado conductor', 'Reparación con resina', 1),
(NULL, 10, 'Batería descargada tras 3 días sin uso', 'Prueba de carga: alternador OK, batería al 40%', 1);
