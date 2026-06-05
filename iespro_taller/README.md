# IESPRO-Taller — Sistema de citas + IA local

Proyecto académico que simula un **taller mecánico**: guarda clientes, vehículos, citas e islas de trabajo en una base de datos, y tiene un **asistente con inteligencia artificial** que corre **100% en tu computadora** (sin pagar APIs de OpenAI ni internet obligatorio para la IA).

Incluye tres piezas que Joel pide en las actividades:

| Semana | Tema | Qué hace este proyecto |
|--------|------|------------------------|
| 1 | Ollama local | Modelo de chat `llama3.2:3b` en tu PC |
| 2 | RAG | Busca fallas parecidas con ChromaDB + embeddings |
| 3 | Function calling | El agente ejecuta acciones reales (crear citas, listar, etc.) |

---

## Guía rápida — ¿Qué es cada cosa? (para el usuario)

Si no eres programador, esta sección resume **todo lo que usa el proyecto** y **para qué sirve**, antes de entrar en detalle técnico.

### El sistema en una frase

**IESPRO-Taller** es como el programa de un taller mecánico: guarda quién es cada cliente, qué auto trae, qué cita tiene y en qué isla trabaja el mecánico. Además tiene un **chat con inteligencia artificial** que responde preguntas y puede **hacer cosas de verdad** (por ejemplo crear una cita), no solo hablar.

---

### Programas que debes tener instalados

| Lo que instalas | Qué es en palabras simples | Qué pasa si no está |
|-----------------|----------------------------|---------------------|
| **Python** | El “motor” que ejecuta nuestro programa | No arranca nada |
| **MySQL** | Archivero digital en tablas (como Excel organizado) | No hay clientes ni citas guardadas |
| **Ollama** | Programa que corre la IA en tu computadora | El chat no responde |
| **llama3.2:3b** | El “cerebro” que entiende español y decide qué hacer | Error “model not found” |
| **nomic-embed-text** | Ayudante que convierte textos en números para comparar fallas | El RAG (casos similares) no funciona |

No necesitas pagar ChatGPT ni internet constante: la IA corre **en tu PC**.

---

### Partes de la aplicación que tú ves

| Parte | Qué es | Para qué la usas |
|-------|--------|------------------|
| **Login** | Pantalla de usuario y contraseña | Entrar al sistema |
| **Pestaña Inicio** | Resumen con números y citas recientes | Ver cómo va el taller de un vistazo |
| **Clientes** | Lista de personas | Dar de alta o ver quién viene al taller |
| **Vehículos** | Autos con placa, modelo, dueño | Registrar qué carro pertenece a quién |
| **Citas** | Agenda de trabajos | Programar una reparación (fecha, mecánico, isla, fallo) |
| **Mi Taller** | Islas / bahías de trabajo | Ver dónde se repara y qué mecánico está en cada lugar |
| **Usuarios** | Cuentas del personal | Admin, mecánicos, etc. |
| **Abrir asistente IA** | Chat flotante | Preguntar en español normal; el sistema responde solo |
| **Terminal (`agent_cli`)** | Pantalla negra con `>` | Modo técnico para demo de “tools”; misma IA, sin ventanas |

---

### Palabras del taller (dominio del negocio)

| Término | Significado |
|---------|-------------|
| **Cliente** | Persona que lleva su auto al taller |
| **Vehículo** | Auto identificado por placa (ej. ABC-123) |
| **Cita** | Una visita programada: qué falla tiene, cuándo, quién la atiende |
| **Isla** | Lugar físico del taller (Diagnóstico, Mecánica, Frenos…) |
| **Mecánico** | Trabajador asignado a la cita o a una isla |
| **Falla** | Descripción del problema del auto (“ruido al frenar”, etc.) |
| **Estado de cita** | PENDIENTE → EN_PROCESO → COMPLETADA (o CANCELADA) |
| **Tipo de mantenimiento** | Servicio con precio (aceite, frenos, diagnóstico…) |
| **Sucursal** | Sede del taller (por defecto “Sucursal Centro”) |

---

### Las 3 formas en que la IA te responde (Actividad 3)

El chat **no siempre funciona igual**. Según tu pregunta, usa uno de estos caminos:

#### 1. SQL — datos exactos

- **Qué es:** Preguntar directo a la base de datos, como un conteo en Excel.
- **Cuándo:** «¿Cuántas citas hay?», «¿Cuántos clientes?»
- **Ventaja:** Números reales, sin inventar.
- **Ejemplo:** *«¿Cuántas citas hay registradas?»*

#### 2. RAG — buscar por significado

- **Qué es:** RAG = buscar en el **historial de fallas** casos parecidos a lo que describes, aunque no uses las mismas palabras.
- **Cuándo:** «¿Hay algo similar a…?», «casos parecidos», síntomas, ruidos, vibraciones.
- **Ventaja:** Aprende de lo que ya pasó en el taller (placas, diagnósticos viejos).
- **Ejemplo:** *«Ruido al frenar, ¿hubo casos parecidos?»*
- **Dónde vive la memoria:** carpeta `db_vectorial/` (ChromaDB), alimentada desde MySQL.

#### 3. Function Calling (FC) — la IA **hace** cosas

- **Qué es:** La IA elige una **acción** de una lista permitida (tools): listar, buscar, crear cita, cambiar estado.
- **Cuándo:** Listados, búsquedas por nombre/placa, **crear o modificar** citas.
- **Ventaja:** No solo te dice: **ejecuta** y guarda en MySQL.
- **Ejemplo:** *«Crea cita para Roberto García, placa ABC-123, Carlos, isla 1, falla: ruido en frenos»*
- **En terminal** verás `[tool]` y `[result]` = prueba de que sí se ejecutó.

---

### Otras palabras técnicas (explicadas fácil)

| Palabra | Explicación simple |
|---------|-------------------|
| **Backend** | La “cocina”: lógica y base de datos; no la ves, pero hace el trabajo |
| **Frontend** | Lo que ves: ventanas, botones, tablas, chat |
| **Base de datos (MySQL)** | Donde se guarda todo permanentemente |
| **ChromaDB** | Memoria especial para comparar fallas por similitud (RAG) |
| **Embedding** | Convertir un texto en números para saber si dos fallas se parecen |
| **Tool / herramienta** | Acción que la IA puede ejecutar (listar citas, crear cita, etc.) |
| **Ollama** | Servicio local que corre los modelos de IA |
| **Modelo (llama3.2:3b)** | Archivo grande entrenado para entender y responder texto |
| **Terminal / consola** | Ventana de texto donde escribes comandos (`python agent_cli.py`) |
| **Tkinter** | Librería que dibuja las ventanas del programa |
| **Python** | Lenguaje en el que está escrito todo el proyecto |
| **`.venv`** | Carpeta con las librerías Python del proyecto (se activa con `source .venv/bin/activate`) |

---

### ¿Qué uso yo según lo que necesite?

| Necesito… | Usa esto |
|-----------|----------|
| Ver tablas y capturar datos a mano | `python main.py --ui` → pestañas |
| Preguntar al asistente (SQL + RAG + acciones) | UI → **Abrir asistente IA** |
| Demo de tools para la escuela | `python agent_cli.py` en terminal |
| Solo contar citas rápido en chat | «¿Cuántas citas hay?» |
| Buscar fallas parecidas | «¿Casos similares a [síntoma]?» |
| Agendar por voz/texto natural | «Crea cita para [nombre], placa [X]…» |

---

### Flujo mental (de punta a punta)

```
Tú (usuario)
    ↓ escribes en chat o usas pestañas
Ventanas del programa (frontend)
    ↓
Programa Python (backend)
    ↓                    ↓                    ↓
  MySQL              ChromaDB              Tools (FC)
  (datos exactos)    (fallas similares)    (acciones)
    ↓                    ↓                    ↓
              Ollama (IA local en tu PC)
    ↓
Respuesta en español (o cita creada en la BD)
```

Más detalle técnico en la [sección 7](#7-tecnologías-y-conceptos-rag-sql-function-calling).

---

## Tabla de contenidos

0. [Guía rápida: qué es cada cosa (para el usuario)](#guía-rápida--qué-es-cada-cosa-para-el-usuario)
1. [Qué necesitas instalar (antes de arrancar)](#1-qué-necesitas-instalar-antes-de-arrancar)
2. [Cómo ponerlo en marcha paso a paso](#2-cómo-ponerlo-en-marcha-paso-a-paso)
3. [Dos formas de usar el sistema](#3-dos-formas-de-usar-el-sistema)
4. [Pantalla gráfica: qué hace cada pestaña](#4-pantalla-gráfica-qué-hace-cada-pestaña)
5. [Asistente IA: qué preguntar y ejemplos](#5-asistente-ia-qué-preguntar-y-ejemplos)
6. [Datos de prueba incluidos](#6-datos-de-prueba-incluidos)
7. [Tecnologías y conceptos (RAG, SQL, Function Calling)](#7-tecnologías-y-conceptos-rag-sql-function-calling)
8. [Problemas frecuentes](#8-problemas-frecuentes)
9. [Anexo técnico: carpetas, flujo y piezas](#9-anexo-técnico-carpetas-flujo-y-piezas)

---

## 1. Qué necesitas instalar (antes de arrancar)

Todo esto debe estar **descargado e instalado** en tu Mac (o PC). Si falta uno, algo del proyecto no funcionará.

> **Resumen:** Python ejecuta el programa; MySQL guarda los datos; Ollama pone la IA en marcha; los dos modelos (`llama3.2:3b` y `nomic-embed-text`) son los “cerebros” descargables. La [guía rápida](#guía-rápida--qué-es-cada-cosa-para-el-usuario) explica cada uno sin tecnicismos.

### Obligatorio

| Programa | Para qué sirve | Cómo obtenerlo |
|----------|----------------|------------------|
| **Python 3.12** | Ejecuta el proyecto | [python.org](https://www.python.org/downloads/) — **no uses 3.14** (ChromaDB falla) |
| **MySQL 8** | Base de datos del taller (clientes, citas, etc.) | MySQL Community o MAMP/XAMPP con MySQL |
| **Ollama** | Motor de IA local (chat + embeddings) | [ollama.com](https://ollama.com) |

### Modelos de Ollama (descargar una vez)

Abre terminal y ejecuta:

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

| Modelo | Tamaño aprox. | Uso |
|--------|---------------|-----|
| `llama3.2:3b` | ~2 GB | Conversación y function calling |
| `nomic-embed-text` | ~274 MB | RAG: convertir texto de fallas en vectores |

Comprueba que Ollama corre:

```bash
ollama list
```

Debes ver los dos modelos en la lista.

### Librerías Python del proyecto

Dentro de la carpeta `iespro_taller`:

```bash
cd ~/Desktop/Proyecto_RAG_Local/iespro_taller
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

| Librería | Para qué |
|----------|----------|
| `pymysql` | Conectar Python con MySQL |
| `ollama` | Hablar con Ollama desde Python |
| `chromadb` | Base vectorial para RAG (memoria semántica de fallas) |

Tkinter (interfaz gráfica) viene incluido con Python en macOS; no hace falta instalarlo aparte.

### Configuración de MySQL

Por defecto el proyecto espera:

| Parámetro | Valor por defecto |
|-----------|-------------------|
| Host | `localhost` |
| Puerto | `3306` |
| Usuario | `root` |
| Contraseña | `root2919` |
| Base de datos | `iespro_taller_app` |

La base **se crea sola** al arrancar (lee `sql/schema.sql`). Solo necesitas que el servicio MySQL esté **encendido**.

Si tu contraseña de MySQL es otra, puedes exportar variables antes de ejecutar:

```bash
export MYSQL_PASSWORD="tu_contraseña"
export MYSQL_USER="root"
```

---

## 2. Cómo ponerlo en marcha paso a paso

### Checklist rápido

1. MySQL encendido  
2. Ollama encendido (`ollama serve` suele arrancar solo en Mac)  
3. Modelos descargados (`llama3.2:3b` y `nomic-embed-text`)  
4. Entorno virtual activado (`source .venv/bin/activate`)

### Modo recomendado para la entrega (Actividad 3) — Terminal

```bash
cd ~/Desktop/Proyecto_RAG_Local/iespro_taller
source .venv/bin/activate
python agent_cli.py
```

Verás un prompt `>`. Escribe preguntas y pulsa Enter. Para salir: `salir`, `exit` o `quit`.

Cuando el agente usa una herramienta verás líneas como:

```
[tool] listar_citas({...})
[result] [...]
```

Eso demuestra **function calling real**: la IA no inventa; ejecuta código que lee o modifica MySQL.

### Modo interfaz gráfica (opcional)

```bash
python main.py --ui
```

Login demo: **admin@iespro.mx** / **admin123**

---

## 3. Dos formas de usar el sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    IESPRO-Taller                            │
├──────────────────────────┬──────────────────────────────────┤
│  agent_cli.py            │  main.py --ui                    │
│  (terminal)              │  (ventanas Tkinter)              │
│                          │                                  │
│  Solo function calling   │  CRUD manual + chat flotante     │
│  Ideal demo Joel sem. 3  │  Ideal administrar datos         │
└──────────────────────────┴──────────────────────────────────┘
                              │
                              ▼
                    MySQL (iespro_taller_app)
                              │
                              ▼
              Ollama (llama3.2:3b + nomic-embed-text)
                              │
                              ▼
         ChromaDB (../db_vectorial/) — solo RAG en chat UI
```

| Modo | Comando | Cuándo usarlo |
|------|---------|---------------|
| Agente terminal | `python agent_cli.py` | Video de function calling, pruebas rápidas |
| App gráfica | `python main.py --ui` | Ver tablas, crear citas a mano, chat con RAG |
| Por defecto `main.py` | `python main.py` | Igual que agent_cli (sin UI) |

---

## 4. Pantalla gráfica: qué hace cada pestaña

Después del login aparecen **6 pestañas**. Cada una es una “vista” del taller.

### Inicio

**Qué es:** Panel de resumen del taller.

**Qué muestra:**

- Tarjetas con totales: clientes, vehículos, citas, pendientes, en proceso, completadas, islas, mecánicos  
- Estado de conexión a MySQL  
- Tabla de **citas recientes**

**Qué hacer aquí:** Solo consultar. Botón **Actualizar** refresca los números.

---

### Clientes

**Qué es:** Directorio de personas que llevan autos al taller.

**Qué puedes hacer:**

- Ver lista de clientes (nombre, teléfono, email)  
- **Nuevo cliente:** llenar nombre, teléfono, email; opcionalmente vincular a un usuario del sistema  
- **Guardar cliente**

**Cuándo usarlo:** Cuando entra un cliente nuevo y aún no está en la base.

---

### Vehículos

**Qué es:** Registro de autos por cliente.

**Qué puedes hacer:**

- Registrar placa, serie, modelo, marca, combustible, tipo de unidad, kilometraje  
- Elegir **propietario** en el desplegable (debe ser un cliente ya dado de alta)  
- Ver tabla de todos los vehículos

**Importante:** El cliente debe tener **usuario vinculado** para poder guardar vehículo (los del seed ya lo tienen).

---

### Citas

**Qué es:** Corazón operativo — agendar trabajo en el taller.

**Qué puedes hacer:**

1. Elegir **cliente** → se cargan sus vehículos  
2. Elegir **vehículo**, **fecha**, **hora** (botón *Cargar horarios*)  
3. Asignar **mecánico** e **isla**  
4. Escribir **descripción del fallo**  
5. Seleccionar uno o más **tipos de mantenimiento** (lista con precios)  
6. **Crear cita**

Abajo ves la tabla de citas existentes con estado (PENDIENTE, EN_PROCESO, COMPLETADA, CANCELADA).

---

### Mi Taller

**Qué es:** Configuración física del taller (bahías/islas).

**Qué puedes hacer:**

- Crear **islas** (ej. “Isla 4 - Transmisión”)  
- **Asignar mecánicos** a una isla (marcar si es responsable)  
- Ver islas activas

**Para qué sirve:** Saber quién trabaja en cada bahía; el agente también puede consultarlo.

---

### Usuarios

**Qué es:** Cuentas del sistema (admin, jefes, mecánicos, clientes).

**Qué puedes hacer:**

- Crear usuarios con rol, sucursal, puesto  
- Marcar si es cliente o trabajador  
- Ver listado completo

**Login demo:** `admin@iespro.mx` / `admin123`

---

### Botón “Abrir asistente IA” (esquina superior)

Abre una **ventana de chat** flotante. A diferencia del terminal:

- Usa **RAG** (buscar fallas similares)  
- Usa **function calling** y atajos SQL  
- No muestra JSON crudo al usuario

Ideal para preguntas del tipo “¿alguna vez tuvimos un caso parecido a…?”.

---

## 5. Asistente IA: qué preguntar y ejemplos

### Regla de oro

Habla **como le hablarías a un recepcionista del taller**, con nombres y placas. **No hace falta saber IDs numéricos.**

### Consultas — copia y pega

| Quieres… | Ejemplo de pregunta |
|----------|---------------------|
| Ver citas | `Lista las citas del taller` |
| Contar | `¿Cuántas citas pendientes hay?` |
| Clientes | `Muéstrame todos los clientes` |
| Vehículos | `Lista los vehículos registrados` |
| Mecánicos | `¿Quiénes son los mecánicos disponibles?` |
| Islas | `Lista las islas del taller` |
| Mecánico en isla | `¿Qué mecánicos hay en la isla 1?` |
| Vehículos de alguien | `¿Qué vehículos tiene Roberto García?` (usa listar + buscar) |

### Crear cita (lenguaje natural)

```
Crea una cita para Roberto García, placa ABC-123, mecánico Carlos, isla 1, falla: ruido metálico al frenar
```

```
Agenda a María López con placa LMN-456, mecánico Ana, isla 3, falla: vibración en frenos
```

Campos que el agente necesita (puede pedirte lo que falte):

- Nombre del cliente  
- Placa (o modelo del auto)  
- Nombre del mecánico (Carlos, Ana, Miguel…)  
- Isla (número o nombre: “1”, “Diagnóstico”, “Frenos”)  
- Descripción del fallo  

### Cambiar estado de una cita

```
Marca como completada la cita del vehículo ABC-123
```

```
Pon en proceso la cita de la placa LMN-456
```

Estados posibles: **PENDIENTE**, **EN_PROCESO**, **COMPLETADA**, **CANCELADA**.

### RAG — fallas similares (mejor en chat UI)

```
¿Hay fallas parecidas a ruido al frenar con pedal duro?
```

```
Busca casos similares a pérdida de potencia con check engine encendido
```

El sistema busca en el historial indexado en ChromaDB y devuelve placas y diagnósticos parecidos.

### Meta / ayuda

```
¿Qué puedes hacer?
```

En terminal el agente responde con sus capacidades reales (sin inventar JSON).

---

## 6. Datos de prueba incluidos

Al arrancar, `sql/schema.sql` carga datos demo si no existen (`INSERT IGNORE`).

### Acceso

| Email | Contraseña | Rol |
|-------|------------|-----|
| admin@iespro.mx | admin123 | Administrador |
| carlos@iespro.mx | mec123 | Mecánico |
| roberto@cliente.mx | cli123 | Cliente |

### Muestra de datos

| Tipo | Cantidad aprox. | Ejemplos |
|------|-----------------|----------|
| Clientes | 7 | Roberto García, María López, Jorge Medina… |
| Vehículos | 10 | ABC-123, LMN-456, QWE-456, RTY-789… |
| Citas | 12 | Varios estados y fechas |
| Islas | 3 | Diagnóstico, Mecánica, Frenos |
| Mecánicos | 3 | Carlos, Ana, Miguel |
| Tipos mantenimiento | 10 | Aceite, frenos, A/C, alineación… |
| Fallas históricas | 15+ | Para RAG |

---

## 7. Tecnologías y conceptos (RAG, SQL, Function Calling)

Esta sección explica **qué tecnologías usa el proyecto** y **qué significan RAG, SQL y Function Calling**, para que cualquier persona (sin ser programador) entienda la Actividad 3 de Joel.

### 7.1 Stack completo del proyecto

| Tecnología | Qué es | Para qué la usamos aquí |
|------------|--------|-------------------------|
| **Python 3.12** | Lenguaje de programación | Todo el sistema: base de datos, IA, ventanas |
| **MySQL 8** | Base de datos en tablas (filas y columnas) | Guardar clientes, vehículos, citas, islas, usuarios |
| **Ollama** | Programa que corre modelos de IA en tu PC | No depender de ChatGPT en la nube |
| **llama3.2:3b** | Modelo de lenguaje (~2 GB) | Entender preguntas en español y decidir qué hacer |
| **nomic-embed-text** | Modelo de embeddings (~274 MB) | Convertir texto de fallas en vectores numéricos (RAG) |
| **ChromaDB** | Base de datos vectorial (archivos en disco) | Buscar fallas **parecidas en significado**, no solo palabra exacta |
| **pymysql** | Librería Python ↔ MySQL | Ejecutar consultas y guardar datos |
| **chromadb** | Librería Python ↔ ChromaDB | Indexar y buscar fallas similares |
| **ollama** (pip) | Librería Python ↔ Ollama | Enviar mensajes al modelo local |
| **Tkinter** | Librería de ventanas (viene con Python) | Pantallas, pestañas, chat flotante |

**Todo corre local:** MySQL en tu máquina, Ollama en tu máquina, vectores en `../db_vectorial/`. No se paga API externa.

---

### 7.2 Las tres formas de responder (Actividad 3)

Joel pide que el **chat** sepa usar **tres mecanismos** y elija el adecuado según la pregunta:

| Mecanismo | Nombre corto | Cuándo se usa | Ejemplo en nuestro taller |
|-----------|--------------|---------------|---------------------------|
| **SQL tradicional** | SQL | Conteos y datos exactos en tablas | «¿Cuántas citas hay?» → cuenta en MySQL |
| **RAG** | RAG | Buscar por **significado**, casos parecidos | «¿Hay fallas similares a ruido al frenar?» |
| **Function Calling** | FC | Listar, buscar, **crear o modificar** datos | «Crea cita para Roberto, placa ABC-123…» |

En la **interfaz gráfica** (`main.py --ui` → **Abrir asistente IA**), el archivo `chat_service.py` enruta así:

```
Pregunta
   ↓
¿Es conteo directo?     → SQL
   ↓ no
¿Pide casos similares?  → RAG
   ↓ no
Ollama elige tools      → Function Calling
```

En el **terminal** (`agent_cli.py`) solo se demuestra **Function Calling** (ideal para video de tools ejecutándose).

---

### 7.3 ¿Qué es SQL (consultas tradicionales)?

**SQL** (Structured Query Language) es el lenguaje estándar para preguntar a bases de datos relacionales como **MySQL**.

- Los datos están en **tablas**: `clientes`, `vehiculos`, `citas`, etc.
- Preguntas típicas: cuántos hay, listar todos, filtrar por estado.

**En nuestro proyecto:**

- MySQL guarda toda la información real del taller.
- En el chat, algunas preguntas simples van por un **atajo SQL** (`run_sql_query` en `chat_service.py`): el sistema reconoce frases como «cuántas citas», «cuántos clientes», «cuántos vehículos» y responde **directo desde la base**, sin inventar números.
- No es que el usuario escriba `SELECT COUNT(*)...`; el backend ya tiene consultas preparadas para esos casos.

**Analogía:** como preguntarle al contador «¿cuántas facturas hay?» y que abra Excel y cuente — dato exacto, no interpretación.

**Ejemplo demo:** `¿Cuántas citas hay registradas?` → ruta **SQL** en el chat.

---

### 7.4 ¿Qué es RAG?

**RAG** = **R**etrieval-**A**ugmented **G**eneration (Generación aumentada por recuperación).

En palabras simples:

1. **Recuperar** información relevante de una base de conocimiento.
2. **Aumentar** el prompt del modelo con esa información.
3. **Generar** una respuesta basada en datos reales, no solo en lo que el modelo “recuerda” de entrenamiento.

**¿Por qué no basta con preguntarle al modelo directo?**  
Porque el modelo no conoce *tus* fallas del taller. RAG le pasa casos reales de tu historial antes de responder.

**Cómo funciona en IESPRO-Taller:**

```
MySQL (fallas_registradas)
        ↓
Texto de cada falla → modelo nomic-embed-text → vector (lista de números)
        ↓
Se guarda en ChromaDB (carpeta db_vectorial/)
        ↓
Usuario: "¿Casos parecidos a vibración en frenos?"
        ↓
Se convierte la pregunta en vector → se buscan fallas más cercanas
        ↓
Ollama redacta respuesta usando esos casos (placa, diagnóstico, similitud)
```

**Analogía:** como buscar en el archivo del taller «expedientes parecidos a este síntoma», no solo coincidencia de palabra exacta.

**Tecnologías RAG en este proyecto:**

| Pieza | Rol |
|-------|-----|
| `rag_service.py` | Sincroniza fallas MySQL → ChromaDB y busca similares |
| `nomic-embed-text` | Convierte texto → vector |
| `ChromaDB` | Almacena vectores y busca por similitud (coseno) |
| Tool `buscar_fallas_similares` | Puerta que usa el chat para invocar RAG |

**Ejemplo demo:** `Ruido al frenar, ¿hay casos parecidos?` → ruta **RAG** en el chat.

**Actividad 2 → 3:** la Actividad 2 monta RAG; la Actividad 3 lo **integra en el chat** junto con SQL y Function Calling.

---

### 7.5 ¿Qué es Function Calling (FC)?

**Function Calling** (llamada a funciones) es cuando el modelo de IA **no responde solo con texto**, sino que **elige una acción** de una lista que le definimos (las **tools** / herramientas).

Flujo:

```
Usuario: "Lista las citas del taller"
        ↓
Ollama devuelve: quiero usar tool "listar_citas"
        ↓
Python ejecuta listar_citas() → consulta MySQL
        ↓
Resultado JSON vuelve al modelo
        ↓
Modelo responde en español con los datos reales
```

**Importante:** la IA **no ejecuta código peligroso**; solo puede llamar funciones que nosotros registramos en `tools_service.py` (listar, crear cita, cambiar estado, etc.).

**Analogía:** el modelo es un recepcionista que pulsa botones en un panel («Listar citas», «Crear cita»); cada botón corre código nuestro en Python.

**Tools principales de acción (FC):**

| Tool | Qué hace en la vida real |
|------|--------------------------|
| `crear_cita_natural` | Crea cita con nombres y placa (sin pedir IDs) |
| `cambiar_estado_cita_natural` | Cambia PENDIENTE / EN_PROCESO / COMPLETADA / CANCELADA |
| `listar_citas`, `contar_citas` | Consultas estructuradas |
| `buscar_cliente`, `buscar_vehiculo` | Buscar por nombre o placa |

**Ejemplo demo:** `Crea una cita para Roberto García, placa ABC-123, mecánico Carlos, isla 1, falla: ruido en frenos` → ruta **Function Calling**; la cita aparece en MySQL y en la pestaña Citas.

**En terminal** (`agent_cli.py`) verás la prueba explícita:

```
[tool] crear_cita_natural({...})
[result] {"ok": true, "id_cita": ...}
```

Eso demuestra que la tool **sí se ejecutó**, no es texto inventado.

---

### 7.6 Comparación rápida: ¿SQL, RAG o FC?

| Pregunta | Mecanismo | Por qué |
|----------|-----------|---------|
| ¿Cuántas citas pendientes hay? | **SQL** (o FC `contar_citas`) | Número exacto en tabla |
| ¿Hay casos como chirrido al frenar? | **RAG** | Similitud de significado |
| ¿Quién es el dueño de la placa ABC-123? | **FC** `buscar_vehiculo` | Consulta estructurada con lógica |
| Crea una cita para María… | **FC** `crear_cita_natural` | **Acción** que modifica la BD |
| Lista todos los mecánicos | **FC** `listar_mecanicos` | Listado desde API interna |

---

### 7.7 Ollama y los modelos (Actividad 1)

**Ollama** es el “motor” que corre modelos open source en local.

| Modelo | Actividad | Función |
|--------|-----------|---------|
| `llama3.2:3b` | 1 y 3 | Chat, razonamiento, elegir tools |
| `nomic-embed-text` | 2 (RAG) | Embeddings para ChromaDB |

**Embedding:** transformar texto en una lista de números que captura el **sentido**. Textos parecidos → vectores parecidos → ChromaDB los encuentra juntos.

---

### 7.8 Frontend y backend en la Actividad 3

| Capa | Qué es | Archivos |
|------|--------|----------|
| **Frontend** | Lo que ves y tocas | `ui/main_app.py`, `ui/chat_window.py`, pestañas Clientes/Citas… |
| **Backend** | Lógica y datos | `services/*`, `db/*`, `sql/schema.sql` |
| **IA** | Ollama + enrutamiento | `chat_service.py`, `agent_service.py`, `rag_service.py` |

El usuario puede:

- **Manual:** crear citas en la pestaña Citas (frontend → `cita_service` → MySQL).
- **Chat:** preguntar en lenguaje natural (frontend chat → `chat_service` → SQL / RAG / FC → MySQL o ChromaDB).

---

### 7.9 Diagrama general del sistema

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (Tkinter)                                         │
│  Pestañas CRUD  +  Chat "Abrir asistente IA"                │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  BACKEND (Python services)                                  │
│  chat_service → elige: SQL | RAG | Function Calling         │
└───────┬─────────────────┬─────────────────┬─────────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
   MySQL (SQL)      ChromaDB (RAG)     tools_service (FC)
   tablas           vectores           → MySQL acciones
        │                 │                 │
        └─────────────────┴─────────────────┘
                            │
                            ▼
                      Ollama (local)
              llama3.2:3b + nomic-embed-text
```

---

### 7.10 Resumen para la entrega a Joel

| Actividad | Concepto | ¿Lo tenemos? | Dónde demostrarlo |
|-----------|----------|--------------|-------------------|
| 1 | Ollama local | Sí | `ollama list`, chat responde |
| 2 | RAG | Sí | Pregunta de fallas similares en chat UI |
| 3 | Function Calling | Sí | Crear cita / listar en chat o `agent_cli.py` |
| 3 | SQL tradicional | Sí | «¿Cuántas citas hay?» en chat UI |
| 3 | Integración 3 en 1 | Sí | `chat_service.py` enruta automáticamente |

**Video sugerido (3 preguntas, 3 rutas):** usar el chat de la UI y mostrar que cada respuesta usa un mecanismo distinto (SQL, RAG, FC).

---

## 8. Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `Unknown database 'iespro_taller_app'` | MySQL apagado o schema no corrido | Enciende MySQL; ejecuta de nuevo `python agent_cli.py` |
| Error Ollama / connection refused | Ollama no está corriendo | Abre app Ollama o `ollama serve` |
| Model not found | Falta descargar modelo | `ollama pull llama3.2:3b` |
| RAG no indexa | Falta embedding model | `ollama pull nomic-embed-text` |
| ChromaDB error en Python 3.14 | Versión incompatible | Usa **Python 3.12** en el venv |
| Agente responde sin `[tool]` | Pregunta muy vaga o meta | Sé concreto: "lista citas", "crea cita para…" |
| UI no refleja datos nuevos | Seed ya insertado antes | Los `INSERT IGNORE` no duplican; crea datos desde la UI o borra BD y reinicia |

---

## 9. Anexo técnico: carpetas, flujo y piezas

Esta sección explica **qué archivo es qué**, sin necesidad de saber programar. Piensa en el proyecto como una **oficina**: cada carpeta es un departamento.

### Mapa de carpetas (Proyecto_RAG_Local)

```
Proyecto_RAG_Local/
├── iespro_taller/          ← PROYECTO PRINCIPAL (este README)
│   ├── main.py             ← Puerta de entrada
│   ├── agent_cli.py        ← Agente en terminal
│   ├── config.py           ← Configuración (MySQL, Ollama, rutas)
│   ├── requirements.txt    ← Lista de librerías Python
│   ├── sql/
│   │   └── schema.sql      ← Estructura BD + datos demo
│   ├── db/
│   │   ├── connection.py   ← Conexión a MySQL
│   │   └── init_db.py      ← Crea tablas al arrancar
│   ├── services/           ← Lógica de negocio
│   ├── ui/                 ← Ventanas gráficas
│   └── data/               ← Documentos opcionales para RAG
│
└── db_vectorial/           ← ChromaDB guarda aquí los vectores de fallas
```

### Qué hace cada archivo importante

| Archivo | Rol (analogía) |
|---------|----------------|
| `main.py` | Interruptor general: `--ui` abre ventanas; sin flag abre terminal |
| `agent_cli.py` | Recepcionista en consola: lee `>`, llama al agente, muestra tools |
| `config.py` | Hoja de configuración: passwords, nombres de modelos, rutas |
| `sql/schema.sql` | Plano de la base + datos de ejemplo |
| `db/connection.py` | Cable entre Python y MySQL |
| `db/init_db.py` | Al arrancar, ejecuta el SQL para crear/llenar tablas |
| `services/cita_service.py` | Reglas de citas, vehículos, islas; busca por nombre/placa |
| `services/catalog_service.py` | Clientes, usuarios, login, catálogos |
| `services/tools_service.py` | **Tools** del agente: listar, crear cita, cambiar estado… |
| `services/agent_service.py` | Cerebro del terminal: Ollama + function calling |
| `services/chat_service.py` | Cerebro del chat UI: RAG + tools + atajos |
| `services/rag_service.py` | Indexa fallas en ChromaDB y busca similares |
| `ui/main_app.py` | Ventana principal con pestañas |
| `ui/chat_window.py` | Ventana flotante del asistente |
| `ui/login_window.py` | Pantalla de login |
| `ui/theme.py` | Colores y estilos |

### Las 14 “tools” (acciones que la IA puede ejecutar)

| Tool | Acción real |
|------|-------------|
| `contar_citas` | Cuenta citas (opcional por estado) |
| `listar_citas` | Lista citas con detalle |
| `listar_clientes` | Lista clientes |
| `listar_vehiculos` | Lista vehículos |
| `listar_mecanicos` | Lista mecánicos |
| `listar_islas` | Lista islas/bahías |
| `mecanicos_en_isla` | Mecánicos de una isla |
| `vehiculos_de_cliente` | Autos de un cliente |
| `buscar_cliente` | Busca cliente por nombre |
| `buscar_vehiculo` | Busca por placa o modelo |
| `crear_cita_natural` | **Crea cita con nombres** (sin IDs) |
| `cambiar_estado_cita_natural` | Cambia estado por placa |
| `cambiar_estado_cita` | Cambia estado por id_cita |
| `buscar_fallas_similares` | RAG: fallas parecidas |

### Flujo completo al iniciar la app gráfica

```
1. main.py arranca
2. init_db.py ejecuta schema.sql → MySQL listo
3. chat_service sincroniza fallas → ChromaDB (db_vectorial/)
4. LoginWindow pide usuario/contraseña
5. MainApp muestra pestañas
6. Usuario puede operar manualmente O abrir chat IA
```

### Flujo al iniciar agent_cli.py

```
1. init_db.py → MySQL listo
2. Bucle: input > → agent_service.ask()
3. Ollama puede devolver tool_calls
4. tools_service ejecuta → MySQL
5. Respuesta final impresa
```

### Qué descargar vs qué se genera solo

| Descargas tú | Se genera solo |
|--------------|----------------|
| Python, MySQL, Ollama, modelos Ollama | Base `iespro_taller_app` |
| `pip install -r requirements.txt` | Carpeta `db_vectorial/` |
| | Entorno `.venv/` |
| | Datos demo del schema |

### Variables de entorno opcionales

Puedes cambiar comportamiento sin tocar código:

```bash
export MYSQL_HOST=localhost
export MYSQL_PASSWORD=tu_clave
export OLLAMA_CHAT_MODEL=llama3.2:3b
export OLLAMA_EMBED_MODEL=nomic-embed-text
export DEFAULT_SUCURSAL_ID=1
```

---

## Créditos y contexto

Proyecto para entregables de **Joel** (Ollama + RAG + Function Calling) integrado con el caso de estudio **IESPRO-Taller** (citas automotrices).

**Recomendación para video de entrega:** grabar `python agent_cli.py` mostrando una pregunta, las líneas `[tool]` / `[result]`, y la respuesta final confirmando el cambio en MySQL o en la pestaña Citas de la UI.
