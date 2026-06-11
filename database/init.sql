-- database/init.sql
-- Script de inicialización para la base de datos en PostgreSQL
-- Objetivo: Crear la estructura vulnerable y poblarla con datos de prueba

-- Eliminar la tabla si ya existe (útil para reiniciar el entorno)
DROP TABLE IF EXISTS patients;

-- Crear la tabla de pacientes
CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    document_id VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    birth_date DATE
);

-- Insertar datos médicos ficticios para la prueba de concepto
INSERT INTO patients (full_name, document_id, email, phone, birth_date) VALUES
('Carlos Mendoza', 'V-12345678', 'cmendoza@email.com', '0414-1234567', '1985-04-12'),
('María Fernández', 'V-87654321', 'mfernandez@email.com', '0412-9876543', '1990-11-25'),
('José Pérez', 'V-11223344', 'jperez@email.com', '0416-1122334', '1978-02-05'),
('Ana Gómez', 'V-44332211', 'agomez@email.com', '0424-4433221', '2001-08-19'),
('Luis Rodríguez', 'V-55667788', 'lrodriguez@email.com', '0414-5566778', '1995-12-30');

-- ---------------------------------------------------------------
-- Tabla de usuarios del sistema (autenticación)
-- ADVERTENCIA EDUCATIVA: contraseñas en texto plano — solo pruebas
-- ---------------------------------------------------------------
DROP TABLE IF EXISTS usuarios;

CREATE TABLE usuarios (
    id       SERIAL PRIMARY KEY,
    username VARCHAR(80)  UNIQUE NOT NULL,
    password VARCHAR(120) NOT NULL,                -- texto plano (solo entorno de prueba)
    rol      VARCHAR(20)  NOT NULL                 -- 'medico', 'administrador' o 'paciente'
              CHECK (rol IN ('medico', 'administrador', 'paciente'))
);

-- Usuarios de prueba para validar los tres roles disponibles
INSERT INTO usuarios (username, password, rol) VALUES
('admin',   'admin123',   'administrador'),
('dr_lopez', 'medico123', 'medico'),
('paciente1', 'pac123',   'paciente');