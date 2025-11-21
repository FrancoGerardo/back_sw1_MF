# Variables de Entorno Requeridas

Este archivo documenta todas las variables de entorno necesarias para el proyecto.

## Variables Obligatorias

### Django Settings
```bash
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost,your-domain.railway.app
```

### Database Configuration (PostgreSQL)
```bash
DB_NAME=traductordb
DB_USER=postgres
DB_PASSWORD=your-database-password
DB_HOST=localhost
DB_PORT=5432
```

### Gemini API Key (para funcionalidades de IA)
```bash
GEMINI_API_KEY=your-gemini-api-key-here
```

## Variables Opcionales (pero recomendadas para producción)

### Redis Configuration (para WebSockets/Channels)
```bash
# En Railway, esto se configura automáticamente cuando agregas el servicio Redis
REDIS_URL=redis://localhost:6379/0
```

### CORS Configuration
```bash
# URLs del frontend separadas por comas (sin espacios después de las comas)
CORS_ALLOWED_ORIGINS=https://tu-frontend.railway.app,https://otro-dominio.com
```

### Frontend URL (para redirecciones)
```bash
FRONTEND_URL=https://tu-frontend.railway.app
```

### Email Configuration (obligatorio para producción)
```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=grupito.si.5@gmail.com
EMAIL_HOST_PASSWORD=auueuwlqectlifms
```

**Nota:** Si estas variables NO están configuradas, el sistema usará consola (solo para desarrollo).

## Notas

- En desarrollo local, crea un archivo `.env` en la raíz del proyecto con estas variables
- En Railway, configura estas variables en el panel de configuración del proyecto
- Las variables con valores por defecto funcionarán en desarrollo, pero deben configurarse para producción

