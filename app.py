import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask
from flask_cors import CORS
from routes.auth_routes import auth_bp, register_global_legacy_routes
from routes.user_routes import user_bp
from routes.lote_routes import lote_bp
from routes.animal_routes import animal_bp

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "allow_headers": ["Content-Type", "Authorization"]}})

# Registro de blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(lote_bp)
app.register_blueprint(animal_bp)

# Registrar rutas legacy globales para compatibilidad con el frontend antiguo
register_global_legacy_routes(app)

# --- NGROK LOGIC ---
from pyngrok import ngrok
import time
import subprocess

def kill_ngrok_processes():
    try:
        subprocess.run(['powershell', '-Command', 'Stop-Process -Name "ngrok" -Force -ErrorAction SilentlyContinue'], capture_output=True)
        time.sleep(2)
    except:
        pass

if __name__ == '__main__':
    try:
        port = "5000"
        kill_ngrok_processes()
        ngrok_token = os.getenv('NGROK_AUTH_TOKEN')
        if ngrok_token:
            ngrok.set_auth_token(ngrok_token)
        public_url = ngrok.connect(port).public_url
        print(f' * URL de Ngrok: {public_url}')
        print(f' * Endpoint de la API: {public_url}/api')
        print(f' * Servidor iniciado en el puerto {port}')
        app.run(host='0.0.0.0', port=int(port), debug=True)
    except Exception as e:
        print(f"Error al iniciar ngrok: {str(e)}")
        print("\nPor favor, sigue estos pasos:")
        print("1. Abre PowerShell como administrador")
        print("2. Ejecuta: Get-Process ngrok | Stop-Process -Force")
        print("3. Ve a https://dashboard.ngrok.com/agents")
        print("4. Cierra manualmente cualquier sesión activa")
        print("5. Intenta ejecutar la aplicación nuevamente")
        print("4. Cierra manualmente cualquier sesión activa")
        print("5. Intenta ejecutar la aplicación nuevamente")
