CREATE DATABASE IF NOT EXISTS iespro_taller_app
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Instalación limpia (opcional): descomenta la siguiente línea y vuelve a ejecutar este script.
-- DROP DATABASE IF EXISTS iespro_taller_app;
-- CREATE DATABASE iespro_taller_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

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

CREATE TABLE IF NOT EXISTS codigos_invitacion (
  id INT AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(32) NOT NULL UNIQUE,
  id_sucursal INT NOT NULL,
  usos_maximos INT NOT NULL DEFAULT 1,
  usos_actuales INT NOT NULL DEFAULT 0,
  expira_en DATETIME NULL,
  creado_por INT NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  permite_admin_sucursal TINYINT(1) NOT NULL DEFAULT 0,
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_sucursal) REFERENCES sucursales(id),
  FOREIGN KEY (creado_por) REFERENCES usuarios(id)
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

CREATE TABLE IF NOT EXISTS usuario_sucursales (
  id INT AUTO_INCREMENT PRIMARY KEY,
  id_usuario INT NOT NULL,
  id_sucursal INT NOT NULL,
  UNIQUE KEY uk_usuario_sucursal (id_usuario, id_sucursal),
  FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE CASCADE,
  FOREIGN KEY (id_sucursal) REFERENCES sucursales(id) ON DELETE CASCADE
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
  id_sucursal INT NOT NULL,
  id_mecanico_asignado INT NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  FOREIGN KEY (id_marca) REFERENCES marcas(id),
  FOREIGN KEY (id_tipo_combustible) REFERENCES tipos_combustible(id),
  FOREIGN KEY (id_tipo_unidad) REFERENCES tipos_unidad(id),
  FOREIGN KEY (id_cliente) REFERENCES clientes(id),
  FOREIGN KEY (id_usuario) REFERENCES usuarios(id),
  FOREIGN KEY (id_sucursal) REFERENCES sucursales(id),
  FOREIGN KEY (id_mecanico_asignado) REFERENCES usuarios(id)
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
  estado ENUM(
    'PENDIENTE','RECIBIDO','DIAGNOSTICO','EN_PROCESO','EN_REPARACION',
    'ESPERANDO_REFACCIONES','COMPLETADA','FINALIZADO','CANCELADA'
  ) NOT NULL DEFAULT 'PENDIENTE',
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
  observaciones TEXT,
  solucion TEXT,
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

CREATE TABLE IF NOT EXISTS llm_observability_logs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  session_id VARCHAR(120) NOT NULL,
  timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_prompt TEXT NOT NULL,
  system_response LONGTEXT,
  ttft_ms INT,
  total_latency_ms INT NOT NULL,
  tokens_per_second DECIMAL(10,2),
  was_blocked TINYINT(1) NOT NULL DEFAULT 0,
  tools_executed JSON,
  INDEX idx_obs_session (session_id),
  INDEX idx_obs_timestamp (timestamp)
);


CREATE TABLE IF NOT EXISTS app_meta (
  meta_key VARCHAR(64) PRIMARY KEY,
  meta_value VARCHAR(255) NOT NULL
);


-- Catálogo mínimo (referencia para formularios). El resto se crea desde la app.
INSERT IGNORE INTO roles (id, nombre, descripcion) VALUES
(1, 'ADMIN', 'Administrador del sistema'),
(2, 'MECANICO', 'Mecánico de taller'),
(3, 'PENDIENTE', 'Registro con código, pendiente de activación'),
(4, 'CLIENTE', 'Cliente con acceso a la app'),
(5, 'SUPER_ADMIN', 'Alias legacy de administrador');

INSERT IGNORE INTO puestos (id, nombre) VALUES
(1, 'Admin'),
(2, 'Mecánico');

INSERT IGNORE INTO usuarios (id, nombre, email, password, id_rol, id_sucursal, es_cliente, es_trabajador, id_puesto) VALUES
(1, 'Admin Sistema', 'admin@iespro.mx', 'admin1234', 1, NULL, 0, 1, 1);

INSERT IGNORE INTO marcas (id, nombre) VALUES
(1, 'Nissan'), (2, 'Toyota'), (3, 'Ford'), (4, 'Chevrolet');

INSERT IGNORE INTO tipos_combustible (id, nombre) VALUES
(1, 'Gasolina'), (2, 'Diésel'), (3, 'Híbrido'), (4, 'Eléctrico');

INSERT IGNORE INTO tipos_unidad (id, nombre) VALUES
(1, 'Sedán'), (2, 'Pickup'), (3, 'SUV'), (4, 'Camioneta');
