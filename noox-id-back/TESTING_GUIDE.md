# 📋 Guía de Testing - NooxID API con Postman

## 🚀 Configuración Inicial

### 1. Importar archivos en Postman:
1. **Colección**: `NooxID_API_Tests.postman_collection.json`
2. **Ambiente**: `NooxID_Development.postman_environment.json`

### 2. Configurar el ambiente:
- Asegúrate de seleccionar el ambiente "NooxID Development Environment"
- Verifica que `base_url` esté configurada como `http://localhost:5000`

### 3. Iniciar el servidor:
```bash
cd noox-id-back
python main.py
```

## 🧪 Orden de Ejecución de Tests

### ✅ **Flujo Completo Automatizado**
Los tests están diseñados para ejecutarse en orden y crear/limpiar datos automáticamente:

1. **🏥 Health Check** - Verificar que la API esté funcionando
2. **🔐 Authentication** - Registro, login y verificación de tokens
3. **👤 Users** - Gestión de usuarios y perfiles
4. **📱 Applications** - Crear y gestionar aplicaciones
5. **🔗 User-App Relations** - Relaciones usuario-aplicación
6. **🎟️ Access Tokens** - Tokens de acceso
7. **👁️ Face Recognition** - Reconocimiento facial
8. **🗑️ Cleanup Tests** - Limpieza de datos de prueba

## 🎯 Tests Principales

### 🔐 **Autenticación**
- ✅ Registro de usuario nuevo
- ✅ Login tradicional
- ✅ Verificación de token JWT
- ✅ Autenticación con Google

### 👤 **Gestión de Usuarios**
- ✅ Obtener perfil actual
- ✅ Actualizar perfil
- ✅ Listar todos los usuarios (paginado)
- ✅ Buscar usuario por email

### 📱 **Aplicaciones**
- ✅ Crear nueva aplicación
- ✅ Listar aplicaciones del usuario
- ✅ Actualizar aplicación
- ✅ Regenerar API key

### 👁️ **Reconocimiento Facial**
- ✅ Extraer encoding facial (con API key)
- ✅ Comparar dos rostros
- ✅ Verificar usuario por rostro
- ✅ Procesar imagen de perfil
- ✅ Configurar tolerancia

## 🔍 Validaciones Automáticas

Cada test incluye validaciones automáticas:

### ✅ **Status Codes**
- 200: Operaciones exitosas
- 201: Recursos creados
- 400: Errores de validación
- 401: No autorizado
- 403: Sin permisos
- 404: No encontrado

### ✅ **Estructura de Respuesta**
- Campo `success`: true/false
- Datos requeridos según endpoint
- Mensajes descriptivos de error

### ✅ **Funcionalidad**
- Tokens JWT válidos
- API keys generadas automáticamente
- Encodings faciales extraídos correctamente
- Relaciones entre entidades

## 🛠️ Variables Automáticas

Los tests generan y usan estas variables automáticamente:

```json
{
  "auth_token": "JWT generado automáticamente",
  "test_user_id": "ID del usuario de prueba",
  "test_user_email": "Email del usuario de prueba", 
  "test_app_id": "ID de la aplicación de prueba",
  "test_api_key": "API key generada",
  "test_access_token_id": "ID del token de acceso"
}
```

## 🎨 Ejemplos de Uso

### 1. **Registro de Usuario con Imagen Facial**
```json
{
  "firstname": "Juan",
  "lastname": "Pérez",
  "email": "juan@test.com",
  "password": "password123",
  "base64imageprofile": "data:image/jpeg;base64,..."
}
```

### 2. **Comparación de Rostros**
```json
{
  "face1": "data:image/jpeg;base64,imagen1...",
  "face2": "data:image/jpeg;base64,imagen2..."
}
```

### 3. **Headers para API Key**
```
X-API-Key: noox_tu_api_key_aqui
X-App-ID: 1
```

## 🚨 Manejo de Errores

### **Errores Comunes y Soluciones:**

1. **500 - Error del servidor**
   - Verificar que la base de datos esté funcionando
   - Revisar logs del servidor

2. **401 - No autorizado**
   - Token JWT expirado o inválido
   - API key incorrecta

3. **400 - Error de validación**
   - Campos requeridos faltantes
   - Formato de datos incorrecto

## 📊 Métricas de Performance

Los tests verifican automáticamente:
- ⏱️ Tiempo de respuesta < 5000ms
- 📝 Respuestas JSON válidas
- 🔒 Autenticación correcta
- 💾 Persistencia de datos

## 🔄 Ejecución en Lote

### **Ejecutar toda la colección:**
1. Click en "NooxID API Tests"
2. Click en "Run collection"
3. Seleccionar todos los tests
4. Click en "Run NooxID API Tests"

### **Ejecutar por carpetas:**
- Ejecutar solo "Authentication" para tests de login
- Ejecutar solo "Face Recognition" para tests faciales
- Usar "Cleanup Tests" para limpiar datos

## 📝 Logs y Debugging

Los tests incluyen logs automáticos:
```javascript
console.log('🚀 Ejecutando: ' + pm.request.name);
console.log('✅ Completado: ' + pm.request.name + ' - Status: ' + pm.response.code);
```

## 🎯 Tests de Reconocimiento Facial

### **Casos cubiertos:**
- ✅ Extracción de encodings faciales
- ✅ Comparación de rostros idénticos
- ✅ Comparación de rostros diferentes  
- ✅ Verificación de usuarios registrados
- ✅ Manejo de imágenes sin rostros
- ✅ Configuración de tolerancia

---

**💡 Tip:** Ejecuta primero el "Health Check" para verificar que el servidor esté funcionando antes de correr los demás tests.

**🔧 Personalización:** Puedes modificar las variables de ambiente para apuntar a diferentes servidores (desarrollo, staging, producción).
