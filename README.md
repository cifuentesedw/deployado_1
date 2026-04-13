# 📬 Blacklist Microservice

Microservicio REST en Python/Flask para la **gestión de la lista negra global de emails** de una compañía multinacional.  
Desplegado manualmente sobre **AWS Elastic Beanstalk** con base de datos **AWS RDS PostgreSQL**.

---

## 📐 Arquitectura

```
┌──────────────────────────────────────────────────────────────────┐
│                         Cliente (Postman)                         │
└──────────────────────────┬───────────────────────────────────────┘
                           │  HTTPS  (Bearer Token)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│              AWS Elastic Beanstalk (PaaS)                        │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  EC2  –  Gunicorn  →  Flask Application                  │    │
│  │                                                           │    │
│  │   POST  /blacklists          ← BlacklistResource         │    │
│  │   GET   /blacklists/<email>  ← BlacklistCheckResource    │    │
│  │   GET   /health                                          │    │
│  └──────────────────────┬────────────────────────────────────┘    │
│                         │  SQLAlchemy ORM                        │
└─────────────────────────┼────────────────────────────────────────┘
                          │  TCP 5432
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│          AWS RDS  –  PostgreSQL                                  │
│          Tabla: blacklist_entries                                │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🛠 Stack Tecnológico

| Componente        | Versión  | Rol                                     |
|-------------------|----------|-----------------------------------------|
| Python            | 3.14     | Lenguaje base                           |
| Flask             | 2.3.3    | Micro-framework web                     |
| Flask-RESTful     | 0.3.10   | API REST orientada a objetos            |
| Flask-SQLAlchemy  | 3.1.1    | ORM – integración con SQLAlchemy        |
| SQLAlchemy        | 2.0.23   | Mapper relacional de objetos            |
| Flask-Marshmallow | 0.15.0   | Serialización / validación de esquemas  |
| Flask-JWT-Extended| 4.5.3    | Soporte JWT (Bearer Token)              |
| Werkzeug          | 2.3.7    | Capa WSGI subyacente de Flask           |
| PostgreSQL        | 17       | Motor de base de datos relacional       |
| Gunicorn          | 21.2.0   | Servidor WSGI para producción           |
| AWS Elastic Beanstalk | —    | PaaS para despliegue manual             |
| AWS RDS           | —        | Servicio de base de datos administrado  |

---

## 📁 Estructura del Proyecto

```
blacklist-microservice/
├── application.py              # Punto de entrada (EB busca 'application')
├── requirements.txt
├── .env.example
├── .gitignore
│
├── app/
│   ├── __init__.py             # Application factory
│   ├── models/
│   │   └── blacklist.py        # Modelo BlacklistEntry (SQLAlchemy)
│   ├── schemas/
│   │   └── blacklist.py        # Esquemas Marshmallow (validación/serialización)
│   ├── resources/
│   │   └── blacklist.py        # Recursos Flask-RESTful (endpoints)
│   └── utils/
│       └── auth.py             # Decorador token_required
│
├── tests/
│   └── test_blacklist.py       # 13 tests con pytest
│
└── .ebextensions/
    ├── python.config           # Configuración WSGI para Elastic Beanstalk
    └── environment.config      # Variables de entorno para EB
```

---

## 🗄 Modelo de Datos

### Tabla `blacklist_entries`

| Columna          | Tipo          | Restricciones              | Descripción                            |
|------------------|---------------|----------------------------|----------------------------------------|
| `id`             | INTEGER       | PK, AUTOINCREMENT          | Identificador único                    |
| `email`          | VARCHAR(255)  | NOT NULL, UNIQUE, INDEX    | Email en lista negra                   |
| `app_uuid`       | VARCHAR(36)   | NOT NULL                   | UUID de la app que realizó la solicitud|
| `blocked_reason` | VARCHAR(255)  | NULLABLE                   | Motivo del bloqueo (máx. 255 chars)    |
| `request_ip`     | VARCHAR(45)   | NOT NULL                   | IP desde la que se realizó la solicitud|
| `created_at`     | DATETIME      | NOT NULL, DEFAULT=now()    | Fecha/hora de registro                 |

---

## 🔑 Autenticación

Todos los endpoints requieren un **Bearer Token estático** en el header `Authorization`:

```
Authorization: Bearer xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> El token se configura mediante la variable de entorno `STATIC_TOKEN`.

---

## 🚀 API Endpoints

### `POST /blacklists`
Agrega un email a la lista negra global.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "email": "usuario@ejemplo.com",
  "app_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "blocked_reason": "Envío masivo de spam"
}
```

**Respuesta exitosa (201):**
```json
{
  "msg": "El email 'usuario@ejemplo.com' fue agregado exitosamente a la lista negra global.",
  "data": {
    "id": 1,
    "email": "usuario@ejemplo.com",
    "app_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "blocked_reason": "Envío masivo de spam",
    "request_ip": "190.57.12.34",
    "created_at": "2024-01-15T10:30:00"
  }
}
```

**Códigos de respuesta:**

| Código | Situación                                  |
|--------|--------------------------------------------|
| 201    | Email agregado exitosamente                |
| 400    | Datos inválidos (email mal formado, UUID inválido, motivo > 255 chars) |
| 401    | Token faltante o mal formado               |
| 403    | Token inválido                             |
| 409    | El email ya existe en la lista negra       |
| 500    | Error interno del servidor                 |

---

### `GET /blacklists/<email>`
Consulta si un email está en la lista negra global.

**Headers:**
```
Authorization: Bearer <token>
```

**Respuesta – email EN lista negra (200):**
```json
{
  "is_blacklisted": true,
  "email": "usuario@ejemplo.com",
  "blocked_reason": "Spam",
  "app_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-01-15T10:30:00"
}
```

**Respuesta – email NO en lista negra (200):**
```json
{
  "is_blacklisted": false,
  "email": "limpio@ejemplo.com",
  "blocked_reason": null
}
```

**Códigos de respuesta:**

| Código | Situación                    |
|--------|------------------------------|
| 200    | Consulta exitosa             |
| 401    | Token faltante o mal formado |
| 403    | Token inválido               |

---

### `GET /health`
Verificación de estado del servicio (sin autenticación).

**Respuesta (200):**
```json
{
  "status": "healthy",
  "service": "blacklist-microservice"
}
```

---

## ⚙️ Instalación Local

### 1. Pre-requisitos
- Python 3.14
- PostgreSQL 15+
- Git

### 2. Clonar y configurar

```bash
git clone https://github.com/<tu-usuario>/deployado_1.git
cd deployado_1

# Crear entorno virtual
python -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Variables de entorno

```bash
# Conector a base de datos
DATABASE_URL=postgresql+psycopg://postgres:PASSWORD_VALIDO@direccion_a_base_de_datos_en_aws_rds:5432/blacklist_db
                                                       
# Token Bearer estático
STATIC_TOKEN=aqui_debe_ir_el_token_estatico

# JWT Secret
JWT_SECRET_KEY=aqui_la_llave_secreta_jwt

# Editar .env con los valores reales para DA
```

### 4. Crear base de datos PostgreSQL

```sql
CREATE DATABASE blacklist_db;
```

### 5. Ejecutar la aplicación

```bash
python application.py
```

El servicio estará disponible en `http://localhost:5000`.

### 6. Ejecutar tests

```bash
pytest tests/ -v
```

---

## ☁️ Despliegue Manual en AWS Elastic Beanstalk

### Pre-requisitos AWS
- Cuenta AWS activa
- AWS CLI instalado y configurado (`aws configure`)
- EB CLI instalado (`pip install awsebcli`)

### Paso 1 – Crear instancia RDS PostgreSQL

1. Ir a **AWS RDS → Create database**
2. Engine: **PostgreSQL 17**
3. Template: **Free tier** (desarrollo) o **Production**
4. DB identifier: `blacklist-db`
5. Master username: `postgres`
6. Contraseña: contraseña segura
7. Misma VPC que usará EB
8. **Publicly accessible**: No (acceso solo desde EB)
9. Crear la instancia y copiar el **Endpoint**

### Paso 2 – Configurar variables de entorno

Editar `.ebextensions/environment.config`:

```yaml
option_settings:
  aws:elasticbeanstalk:application:environment:
    DATABASE_URL: "postgresql://postgres:<PASSWORD>@<RDS_ENDPOINT>:5432/blacklist_db"
    STATIC_TOKEN: "el-token-super-secreto-produccion"
    JWT_SECRET_KEY: "mi-jwt-secreto-produccion"
```

### Paso 3 – Inicializar EB CLI

```bash
eb init blacklist-microservice \
  --platform python-3.14 \
  --region us-east-1
```

### Paso 4 – Crear el entorno Elastic Beanstalk

```bash
eb create blacklist-prod \
  --instance-type t3.micro \
  --single
```

### Paso 5 – Desplegar la aplicación

```bash
eb deploy
```

### Paso 6 – Verificar el despliegue

```bash
eb open          # Abre el navegador con la URL del entorno
eb logs          # Ver logs en tiempo real
```

La URL del entorno tendrá la forma:
```
http://blacklist-prod.eba-xxxxxxxx.us-east-1.elasticbeanstalk.com
```

### Paso 7 – Crear la base de datos en RDS

Conectarse a RDS y ejecutar:
```sql
CREATE DATABASE blacklist_db;
```

> Las tablas se crean automáticamente al iniciar la aplicación (`db.create_all()`).

---

## 📄 Licencia

MIT License — Proyecto académico de microservicios en la nube.
