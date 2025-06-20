# MiPecuarioWeb Backend

Backend API para el sistema de gestión pecuaria MiPecuarioWeb.

## Requisitos

- Python 3.8+
- MySQL/MariaDB
- XAMPP (recomendado para desarrollo local)

## Configuración

1. Clonar el repositorio:
```bash
git clone https://github.com/tu-usuario/MiPecuarioWeb_BE.git
cd MiPecuarioWeb_BE
```

2. Crear y activar entorno virtual:
```bash
python -m venv venv
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
Crear un archivo `.env` en la raíz del proyecto con las siguientes variables:
```
DB_USER=root
DB_PASSWORD=tu_contraseña
DB_HOST=localhost
DB_NAME=MiPecuarioWed
```

5. Iniciar la base de datos:
- Asegúrate de que XAMPP esté instalado y corriendo
- Inicia los servicios de Apache y MySQL desde el panel de control de XAMPP
- La base de datos se creará automáticamente al ejecutar la aplicación

## Ejecutar la aplicación

```bash
python Aqui_empece.py
```

La API estará disponible en `http://localhost:5000`

## Endpoints disponibles

- `GET /api/test` - Prueba de conexión
- `POST /api/usuarionuevo` - Crear nuevo usuario
- `POST /api/auth/login` - Iniciar sesión
- `POST /api/auth/refresh` - Renovar token
- `GET /api/ruta-protegida` - Ruta protegida (requiere autenticación)

## Estructura del proyecto

```
MiPecuarioWeb_BE/
├── Aqui_empece.py      # Punto de entrada de la aplicación
├── Base_De_Datos_cam.py # Configuración de la base de datos
├── forms_DB_CAM.py     # Modelos de la base de datos
├── routes.py           # Rutas de la API
├── esquemas.py         # Esquemas de validación
└── requirements.txt    # Dependencias del proyecto
```

## Licencia

Este proyecto está bajo la Licencia MIT. #   M i P e c u a r i o W e b _ B E 
 
 