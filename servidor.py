import asyncio
import websockets
import json
import socket
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from PIL import ImageGrab, Image
import io
import base64
import time

class ServidorWebSocket:
    def __init__(self):
        self.clientes_python = {}
        self.clientes_web = set()
        self.puerto_python = 5555
        self.puerto_websocket = 8080
        self.servidor_python = None
        self.servidor_activo = False
        self.loop = None
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        self.transmitiendo_pantalla = False
        self.cliente_destino_stream = None
        
    def log(self, mensaje):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {mensaje}"
        print(log_msg)
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.broadcast_web({'type': 'log', 'message': log_msg}),
                self.loop
            )
    
    async def broadcast_web(self, mensaje):
        if self.clientes_web:
            mensaje_json = json.dumps(mensaje)
            clientes_activos = self.clientes_web.copy()
            if clientes_activos:
                await asyncio.gather(
                    *[cliente.send(mensaje_json) for cliente in clientes_activos],
                    return_exceptions=True
                )
    
    def actualizar_lista_clientes_sync(self):
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.actualizar_lista_clientes(), self.loop)
    
    async def actualizar_lista_clientes(self):
        lista_clientes = []
        for info in self.clientes_python.values():
            ip_port = f"{info['direccion'][0]}:{info['direccion'][1]}"
            nombre = info.get('nombre', 'PC Desconocida')
            lista_clientes.append({'id': ip_port, 'name': nombre})
        await self.broadcast_web({'type': 'client-list', 'clients': lista_clientes})
    
    async def manejar_dashboard(self, websocket):
        self.clientes_web.add(websocket)
        self.log(f"Dashboard conectado.")
        try:
            await self.actualizar_lista_clientes()
            async for mensaje in websocket:
                try:
                    data = json.loads(mensaje)
                    await self.procesar_comando_dashboard(data)
                except: pass
        except websockets.exceptions.ConnectionClosed: pass
        finally:
            self.clientes_web.discard(websocket)
    
    async def procesar_comando_dashboard(self, data):
        action = data.get('action')
        
        if action == 'start-server-stream':
            target = data.get('target')
            cliente_id = self.encontrar_cliente_por_direccion(target)
            if cliente_id:
                self.cliente_destino_stream = cliente_id
                if not self.transmitiendo_pantalla:
                    self.transmitiendo_pantalla = True
                    threading.Thread(target=self.bucle_transmision_servidor, daemon=True).start()
                self.log(f"Iniciando transmisión de ADMIN hacia {target}")
            else:
                self.log("Error: Cliente no encontrado para transmitir")

        elif action == 'stop-server-stream':
            self.detener_transmision_admin("Detenida por el Administrador")

        elif action == 'send-file':
            target = data.get('target')
            filename = data.get('filename')
            filedata = data.get('data')
            cliente_id = self.encontrar_cliente_por_direccion(target)
            if cliente_id:
                self.log(f"Reenviando archivo '{filename}'...")
                await self.loop.run_in_executor(self.executor, self.enviar_archivo_cliente, cliente_id, filename, filedata)
                
        elif action == 'send-command':
            target = data.get('target')
            command = data.get('command')
            cliente_id = self.encontrar_cliente_por_direccion(target)
            if cliente_id:
                await self.loop.run_in_executor(self.executor, self.enviar_comando_cliente, cliente_id, command)
                if "STREAM" not in command:
                    self.log(f"Comando '{command}' enviado a {target}")
    
    def bucle_transmision_servidor(self):
        while self.transmitiendo_pantalla and self.cliente_destino_stream:
            try:
                img = ImageGrab.grab()
                img = img.resize((800, 600))
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=40)
                data_b64 = base64.b64encode(buf.getvalue()).decode()
                
                cliente = self.clientes_python.get(self.cliente_destino_stream)
                if cliente:
                    mensaje = {'comando': 'ver_pantalla_admin', 'datos': {'imagen': data_b64}}
                    msg_str = json.dumps(mensaje) + "\n"
                    cliente['socket'].sendall(msg_str.encode())
                else:
                    self.transmitiendo_pantalla = False
                time.sleep(0.05)
            except:
                self.transmitiendo_pantalla = False
                break
        
        if self.cliente_destino_stream:
            cliente = self.clientes_python.get(self.cliente_destino_stream)
            if cliente:
                try:
                    aviso = {'comando': 'admin_stream_stopped', 'datos': {}}
                    cliente['socket'].sendall((json.dumps(aviso) + "\n").encode())
                except: pass
        
        self.detener_transmision_admin("Transmisión finalizada")

    def detener_transmision_admin(self, razon=""):
        if not self.transmitiendo_pantalla: return
        self.transmitiendo_pantalla = False
        self.cliente_destino_stream = None
        self.log(f"Transmisión de ADMIN finalizada. {razon}")
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast_web({'type': 'server-stream-stopped'}), self.loop)

    def encontrar_cliente_por_direccion(self, direccion_str):
        for cliente_id, info in self.clientes_python.items():
            if f"{info['direccion'][0]}:{info['direccion'][1]}" == direccion_str:
                return cliente_id
        return None
    
    def enviar_archivo_cliente(self, cliente_id, filename, filedata):
        cliente = self.clientes_python.get(cliente_id)
        if not cliente: return
        mensaje = {'comando': 'recibir_archivo', 'datos': {'nombre': filename, 'contenido': filedata}}
        try:
            msg_str = json.dumps(mensaje) + "\n"
            cliente['socket'].sendall(msg_str.encode('utf-8')) 
            self.log(f"Archivo '{filename}' enviado.")
        except Exception as e:
            self.log(f"Error enviando archivo: {str(e)}")

    def enviar_comando_cliente(self, cliente_id, comando):
        cliente = self.clientes_python.get(cliente_id)
        if not cliente: return
        mensaje = self.parsear_comando(comando)
        if not mensaje: return
        try:
            msg = json.dumps(mensaje) + "\n"
            cliente['socket'].send(msg.encode())
        except Exception as e:
            self.log(f"Error enviando comando: {str(e)}")
    
    def parsear_comando(self, comando_str):
        mensaje = {}
        if comando_str == 'START_STREAM': mensaje = {'comando': 'START_STREAM', 'datos': {}}
        elif comando_str == 'STOP_STREAM': mensaje = {'comando': 'STOP_STREAM', 'datos': {}}
        elif comando_str.startswith('CHAT:'): mensaje = {'comando': 'chat', 'datos': {'mensaje': comando_str[5:]}}
        elif comando_str == 'SHUTDOWN': mensaje = {'comando': 'apagar_pc', 'datos': {}}
        elif comando_str.startswith('BLOCK_WEBSITE:'): mensaje = {'comando': 'bloquear_sitios', 'datos': {'sitios': [comando_str[14:]]}}
        elif comando_str.startswith('UNBLOCK_WEBSITE:'): mensaje = {'comando': 'desbloquear_sitios', 'datos': {'sitios': [comando_str[16:]]}}
        elif comando_str == 'BLOCK_PING': mensaje = {'comando': 'denegar_ping', 'datos': {}}
        elif comando_str == 'ALLOW_PING': mensaje = {'comando': 'permitir_ping', 'datos': {}}
        elif comando_str == 'BLOCK_INPUT': mensaje = {'comando': 'bloquear_entrada', 'datos': {}}
        elif comando_str == 'UNBLOCK_INPUT': mensaje = {'comando': 'desbloquear_entrada', 'datos': {}}
        elif comando_str == 'CAPTURE_SCREEN': mensaje = {'comando': 'capturar_pantalla', 'datos': {}}
        return mensaje
    
    def iniciar_servidor_python(self):
        try:
            self.servidor_python = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.servidor_python.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.servidor_python.bind(('0.0.0.0', self.puerto_python))
            self.servidor_python.listen(5)
            self.servidor_activo = True
            self.log(f"Servidor Python iniciado en puerto {self.puerto_python}")
            threading.Thread(target=self.aceptar_clientes_python, daemon=True).start()
        except Exception as e:
            self.log(f"Error al iniciar servidor Python: {str(e)}")
    
    def aceptar_clientes_python(self):
        while self.servidor_activo:
            try:
                cliente_socket, direccion = self.servidor_python.accept()
                cliente_id = len(self.clientes_python) + 1
                self.clientes_python[cliente_id] = {
                    'socket': cliente_socket,
                    'direccion': direccion,
                    'hora_conexion': datetime.now().strftime("%H:%M:%S"),
                    'estado': 'Conectado',
                    'nombre': 'Esperando datos...'
                }
                self.log(f"Cliente Python {cliente_id} conectado")
                self.actualizar_lista_clientes_sync()
                threading.Thread(target=self.manejar_cliente_python, args=(cliente_id,), daemon=True).start()
            except: break
    
    def manejar_cliente_python(self, cliente_id):
        cliente = self.clientes_python.get(cliente_id)
        if not cliente: return
        buffer = ""
        try:
            while self.servidor_activo:
                data = cliente['socket'].recv(1024 * 1024 * 5) 
                if not data: break
                buffer += data.decode('utf-8')
                while "\n" in buffer:
                    mensaje_str, buffer = buffer.split("\n", 1)
                    if mensaje_str.strip():
                        try: self.procesar_mensaje_cliente_sync(cliente_id, json.loads(mensaje_str))
                        except: pass
        except: pass
        finally: self.desconectar_cliente_python(cliente_id)
    
    def procesar_mensaje_cliente_sync(self, cliente_id, mensaje):
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.procesar_mensaje_cliente(cliente_id, mensaje), self.loop)
    
    async def procesar_mensaje_cliente(self, cliente_id, mensaje):
        tipo = mensaje.get('tipo')
        dir_cliente = self.clientes_python[cliente_id]['direccion']
        dir_str = f"{dir_cliente[0]}:{dir_cliente[1]}"
        info = self.clientes_python[cliente_id]
        identificador = f"{info.get('nombre','')} ({dir_str})" if info.get('nombre') else dir_str
        
        if tipo == 'info_sistema':
            self.clientes_python[cliente_id]['nombre'] = mensaje.get('hostname', 'PC')
            self.log(f"Cliente identificado: {mensaje.get('hostname')}")
            await self.actualizar_lista_clientes()
        elif tipo == 'archivo':
            self.log(f"Archivo recibido de {identificador}")
            await self.broadcast_web({'type': 'client-file', 'client': identificador, 'name': mensaje.get('nombre'), 'data': mensaje.get('contenido')})
        
        elif tipo == 'solicitar_ver_admin':
            self.log(f"Solicitud de ver pantalla admin de {identificador}")
            await self.broadcast_web({
                'type': 'admin-view-request',
                'client': dir_str, 
                'name': identificador
            })
        
        elif tipo == 'detener_ver_admin':
            self.detener_transmision_admin(f"Solicitado por cliente {identificador}")
        
        # NUEVO: MANEJO DE PERMISO DENEGADO
        elif tipo == 'permission_denied':
            self.log(f"Permiso denegado en {identificador}: {mensaje.get('action')}")
            await self.broadcast_web({
                'type': 'client-permission-denied',
                'client': dir_str,
                'name': identificador,
                'action': mensaje.get('action')
            })

        elif tipo == 'screenshot':
            await self.broadcast_web({'type': 'screenshot-data', 'client': dir_str, 'image': mensaje.get('data')})
        elif tipo == 'chat':
            await self.broadcast_web({'type': 'chat-message', 'from': identificador, 'message': mensaje.get('mensaje', '')})
        elif tipo == 'respuesta_autorizacion':
            await self.broadcast_web({'type': 'authorization-response', 'client': identificador, 'action': mensaje.get('accion'), 'authorized': mensaje.get('autorizado'), 'message': mensaje.get('mensaje', '')})
            
    def desconectar_cliente_python(self, cliente_id):
        if cliente_id in self.clientes_python:
            dir_str = f"{self.clientes_python[cliente_id]['direccion'][0]}:{self.clientes_python[cliente_id]['direccion'][1]}"
            try: self.clientes_python[cliente_id]['socket'].close()
            except: pass
            del self.clientes_python[cliente_id]
            self.log(f"Cliente desconectado: {dir_str}")
            if self.cliente_destino_stream == cliente_id:
                self.detener_transmision_admin("Cliente desconectado")
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast_web({'type': 'client-disconnected', 'client': dir_str}), self.loop)
            self.actualizar_lista_clientes_sync()
    
    async def iniciar_servidor_websocket(self):
        async with websockets.serve(self.manejar_dashboard, "0.0.0.0", self.puerto_websocket, max_size=None):
            self.log(f"Servidor WebSocket: {self.puerto_websocket} (Sin límite)")
            await asyncio.Future()

    async def iniciar_async(self):
        self.loop = asyncio.get_running_loop()
        await self.loop.run_in_executor(self.executor, self.iniciar_servidor_python)
        await self.iniciar_servidor_websocket()
    
    def iniciar(self):
        try: asyncio.run(self.iniciar_async())
        except KeyboardInterrupt: self.servidor_activo = False

if __name__ == "__main__":
    print("Servidor Iniciado...")
    servidor = ServidorWebSocket()
    servidor.iniciar()