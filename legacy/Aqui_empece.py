"""
[ARCHIVO OBSOLETO]
Este archivo servía como punto de entrada principal para la aplicación Flask, gestionando la configuración de CORS, el registro de rutas y la integración con ngrok para exponer la API públicamente.

Motivos de inutilización:
- La lógica de inicialización y configuración se migró a `app.py` en la raíz del proyecto para una estructura más clara y modular.
- El registro de rutas ahora se realiza mediante blueprints separados en la carpeta `routes/`, facilitando el mantenimiento y escalabilidad.

Comparativa con la versión actual (`app.py`):
- Antes: Toda la configuración y registro de rutas estaban centralizados aquí, dificultando la modularidad.
- Ahora: Uso de blueprints para separar la lógica de autenticación, usuarios, lotes y animales.
- Antes: La gestión de ngrok y CORS era menos flexible.
- Ahora: Variables de entorno y configuración más robusta y segura.
- Antes: No seguía buenas prácticas de organización de proyectos Flask.
- Ahora: Estructura modular, fácil de mantener y escalar.
"""

# from flask import Flask
# from flask_cors import CORS
# from routes import api
# from pyngrok import ngrok, conf
# import os
# from dotenv import load_dotenv
# import time
# import subprocess
# import sys

# # Cargar variables de entorno
# load_dotenv()

# app = Flask(__name__)
# # Configurar CORS para permitir las credenciales y headers necesarios para JWT
# CORS(app, resources={
#     r"/api/*": {
#         "origins": "*",
#         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
#         "allow_headers": ["Content-Type", "Authorization"]
#     }
# })
# app.register_blueprint(api, url_prefix='/api')

# def kill_ngrok_processes():
#     try:
#         # Comando específico para PowerShell
#         subprocess.run(['powershell', '-Command', 'Stop-Process -Name "ngrok" -Force -ErrorAction SilentlyContinue'], capture_output=True)
#         time.sleep(2)
#     except:
#         pass

# if __name__ == '__main__':
#     try:
#         # Configurar ngrok
#         port = "5000"
        
#         # Matar cualquier proceso de ngrok existente
#         kill_ngrok_processes()
        
#         # Configurar ngrok con tu token de autenticación
#         ngrok.set_auth_token("2yIuyRMapqamMEwjFjIlK6s1T4o_4eXFEJyumwiVidi7EVcVQ")
        
#         # Abrir el túnel de ngrok
#         public_url = ngrok.connect(port).public_url
#         print(f' * URL de Ngrok: {public_url}')
#         print(f' * Endpoint de la API: {public_url}/api')
#         print(f' * Servidor iniciado en el puerto {port}')
        
#         # Iniciar la aplicación Flask
#         app.run(host='0.0.0.0', port=int(port), debug=True)
#     except Exception as e:
#         print(f"Error al iniciar ngrok: {str(e)}")
#         print("\nPor favor, sigue estos pasos:")
#         print("1. Abre PowerShell como administrador")
#         print("2. Ejecuta: Get-Process ngrok | Stop-Process -Force")
#         print("3. Ve a https://dashboard.ngrok.com/agents")
#         print("4. Cierra manualmente cualquier sesión activa")
#         print("5. Intenta ejecutar la aplicación nuevamente")



