import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog, Label
from PIL import Image, ImageTk, ImageGrab, ImageDraw
import json
import os
import sys
import subprocess
import platform
from datetime import datetime
import base64
import io
import time
import ctypes

class ClienteAgente:
    def __init__(self, root):
        self.root = root
        self.root.title("Cliente - Agente de Administración Remota")
        self.root.geometry("850x650")
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_aplicacion)

        self.socket_cliente = None
        self.conectado = False
        self.streaming = False
        self.servidor_ip = ""
        self.servidor_puerto = 5555

        self.entrada_bloqueada = False
        self.ping_bloqueado = False
        self.sitios_bloqueados = []
        self.ventana_bloqueo = None

        # Variables para ver pantalla del admin
        self.ventana_ver_admin = None
        self.lbl_imagen_admin = None

        if platform.system() == "Windows":
            self.hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        else:
            self.hosts_path = "/etc/hosts"

        self.configurar_interfaz()

    def configurar_interfaz(self):
        frame_header = tk.Frame(self.root, bg="#34495e", pady=15)
        frame_header.pack(fill=tk.X)

        tk.Label(frame_header, text="Cliente de Administración Remota", bg="#34495e", fg="white",
                 font=("Arial", 16, "bold")).pack(pady=(0, 10))

        frame_inputs = tk.Frame(frame_header, bg="#34495e")
        frame_inputs.pack()

        tk.Label(frame_inputs, text="IP:", bg="#34495e", fg="white").grid(row=0, column=0, padx=5)
        self.entry_ip = tk.Entry(frame_inputs, width=20)
        self.entry_ip.insert(0, "192.168.137.1")
        self.entry_ip.grid(row=0, column=1, padx=5)

        tk.Label(frame_inputs, text="Puerto:", bg="#34495e", fg="white").grid(row=1, column=0, padx=5)
        self.entry_puerto = tk.Entry(frame_inputs, width=20)
        self.entry_puerto.insert(0, "5555")
        self.entry_puerto.grid(row=1, column=1, padx=5)

        frame_btns = tk.Frame(frame_header, bg="#34495e")
        frame_btns.pack(pady=10)

        self.btn_conectar = tk.Button(frame_btns, text="Conectar", command=self.conectar_servidor,
                                      bg="#27ae60", fg="white", width=15)
        self.btn_conectar.pack(side=tk.LEFT, padx=10)

        self.btn_desconectar = tk.Button(frame_btns, text="Desconectar", command=self.desconectar_servidor,
                                         bg="#e74c3c", fg="white", width=15, state=tk.DISABLED)
        self.btn_desconectar.pack(side=tk.LEFT, padx=10)

        self.lbl_estado_conexion = tk.Label(frame_header, text="● Desconectado", bg="#34495e",
                                            fg="#e74c3c", font=("Arial", 11, "bold"))
        self.lbl_estado_conexion.pack(pady=(5, 0))

        frame_body = tk.Frame(self.root, padx=15, pady=15)
        frame_body.pack(fill=tk.BOTH, expand=True)

        frame_left = tk.Frame(frame_body)
        frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        frame_right = tk.Frame(frame_body)
        frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Estado
        frame_estado = tk.LabelFrame(frame_left, text="Estado y Acciones",
                                     font=("Arial", 11, "bold"), padx=10, pady=10)
        frame_estado.pack(fill=tk.X, pady=(0, 15))

        info_grid = tk.Frame(frame_estado)
        info_grid.pack(fill=tk.X)

        tk.Label(info_grid, text="Sistema:").grid(row=0, column=0, sticky="w")
        tk.Label(info_grid, text=f"{platform.system()}").grid(row=0, column=1, sticky="w", padx=10)

        tk.Label(info_grid, text="Entrada:").grid(row=1, column=0, sticky="w")
        self.lbl_estado_entrada = tk.Label(info_grid, text="Desbloqueada", fg="#27ae60")
        self.lbl_estado_entrada.grid(row=1, column=1, sticky="w", padx=10)

        tk.Label(info_grid, text="Ping:").grid(row=2, column=0, sticky="w")
        self.lbl_estado_ping = tk.Label(info_grid, text="Permitido", fg="#27ae60")
        self.lbl_estado_ping.grid(row=2, column=1, sticky="w", padx=10)

        self.btn_solicitar = tk.Button(
            frame_estado,
            text="📡 Solicitar que me vean",
            command=self.solicitar_transmision_al_admin,
            bg="#d35400",
            fg="white",
            pady=5
        )
        self.btn_solicitar.pack(fill=tk.X, pady=(10, 5))  # ← CORRECCIÓN AQUÍ

        # Chat
        frame_chat = tk.LabelFrame(frame_left, text="Chat", font=("Arial", 11, "bold"), padx=10, pady=10)
        frame_chat.pack(fill=tk.BOTH, expand=True)

        self.txt_chat = scrolledtext.ScrolledText(frame_chat, height=10, state=tk.DISABLED)
        self.txt_chat.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        frame_env = tk.Frame(frame_chat)
        frame_env.pack(fill=tk.X)

        self.btn_adj = tk.Button(frame_env, text="📎", command=self.seleccionar_archivo,
                                 bg="#95a5a6", fg="white", width=3)
        self.btn_adj.pack(side=tk.LEFT, padx=(0, 5))

        self.entry_mensaje = tk.Entry(frame_env)
        self.entry_mensaje.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entry_mensaje.bind("<Return>", lambda e: self.enviar_mensaje())

        tk.Button(frame_env, text="Enviar", command=self.enviar_mensaje,
                  bg="#3498db", fg="white", padx=15).pack(side=tk.RIGHT)

        # Logs
        frame_logs = tk.LabelFrame(frame_right, text="Logs", font=("Arial", 11, "bold"), padx=10, pady=10)
        frame_logs.pack(fill=tk.BOTH, expand=True)

        self.txt_logs = scrolledtext.ScrolledText(frame_logs, height=20,
                                                  state=tk.DISABLED, font=("Consolas", 8))
        self.txt_logs.pack(fill=tk.BOTH, expand=True)

    def conectar_servidor(self):
        try:
            ip = self.entry_ip.get()
            port = int(self.entry_puerto.get())
            self.socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_cliente.connect((ip, port))
            self.conectado = True

            self.btn_conectar.config(state=tk.DISABLED)
            self.btn_desconectar.config(state=tk.NORMAL)
            self.lbl_estado_conexion.config(text="● Conectado", fg="#27ae60")

            self.agregar_log(f"Conectado a {ip}:{port}")

            threading.Thread(target=self.escuchar_servidor, daemon=True).start()

            try:
                self.enviar_respuesta(
                    'info_sistema',
                    {'hostname': platform.node(),
                     'os': f"{platform.system()} {platform.release()}"}
                )
            except:
                pass

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def desconectar_servidor(self):
        if self.entrada_bloqueada:
            self.desbloquear_entrada()

        if self.ventana_ver_admin:
            self.ventana_ver_admin.destroy()
            self.ventana_ver_admin = None

        self.conectado = False
        self.streaming = False

        if self.socket_cliente:
            try:
                self.socket_cliente.close()
            except:
                pass

        self.btn_conectar.config(state=tk.NORMAL)
        self.btn_desconectar.config(state=tk.DISABLED)
        self.lbl_estado_conexion.config(text="● Desconectado", fg="#e74c3c")

    def escuchar_servidor(self):
        buffer = ""
        while self.conectado:
            try:
                data = self.socket_cliente.recv(5 * 1024 * 1024)
                if not data:
                    break

                buffer += data.decode("utf-8")

                while "\n" in buffer:
                    mensaje_str, buffer = buffer.split("\n", 1)
                    if mensaje_str.strip():
                        try:
                            self.procesar_comando(json.loads(mensaje_str))
                        except:
                            pass

            except:
                break

        self.desconectar_servidor()

    def procesar_comando(self, mensaje):
        comando = mensaje.get("comando")
        datos = mensaje.get("datos", {})

        # Ver pantalla del admin
        if comando == "ver_pantalla_admin":
            self.mostrar_pantalla_admin(datos.get("imagen"))
            return

        if comando == "START_STREAM":
            if not self.streaming:
                self.iniciar_transmision()
            return

        elif comando == "STOP_STREAM":
            self.streaming = False
            return

        elif comando == "recibir_archivo":
            self.guardar_archivo_recibido(datos.get("nombre"), datos.get("contenido"))
            return

        self.agregar_log(f"CMD: {comando}")

        if not self.solicitar_autorizacion(comando, datos):
            self.enviar_respuesta("respuesta_autorizacion",
                                  {'autorizado': False, 'accion': comando, 'mensaje': 'Denegado'})
            return

        if comando == "chat":
            self.agregar_mensaje_chat("Servidor", datos.get("mensaje", ""))

        elif comando == "bloquear_entrada":
            self.bloquear_entrada()

        elif comando == "desbloquear_entrada":
            self.desbloquear_entrada()

        elif comando == "apagar_pc":
            self.apagar_pc()

        elif comando == "bloquear_sitios":
            self.bloquear_sitios(datos.get("sitios", []))

        elif comando == "desbloquear_sitios":
            self.desbloquear_sitios(datos.get("sitios", []))

        elif comando == "denegar_ping":
            self.denegar_ping()

        elif comando == "permitir_ping":
            self.permitir_ping()

        self.enviar_respuesta("respuesta_autorizacion",
                              {'autorizado': True, 'accion': comando, 'mensaje': 'Ejecutado'})

    # Mostrar ventana con pantalla del admin
    def mostrar_pantalla_admin(self, base64_data):
        try:
            img_data = base64.b64decode(base64_data)
            img = Image.open(io.BytesIO(img_data))
            tk_img = ImageTk.PhotoImage(img)

            if self.ventana_ver_admin is None or not self.ventana_ver_admin.winfo_exists():
                self.ventana_ver_admin = tk.Toplevel(self.root)
                self.ventana_ver_admin.title("🔴 PANTALLA DEL ADMINISTRADOR")
                self.ventana_ver_admin.geometry("800x600")

                self.lbl_imagen_admin = tk.Label(self.ventana_ver_admin)
                self.lbl_imagen_admin.pack(fill=tk.BOTH, expand=True)

                def on_close():
                    self.ventana_ver_admin.destroy()
                    self.ventana_ver_admin = None

                self.ventana_ver_admin.protocol("WM_DELETE_WINDOW", on_close)

            self.lbl_imagen_admin.config(image=tk_img)
            self.lbl_imagen_admin.image = tk_img

        except Exception as e:
            print(f"Error mostrando pantalla admin: {e}")

    def solicitar_transmision_al_admin(self):
        if not self.conectado:
            return
        self.enviar_respuesta("solicitar_stream", {})
        self.agregar_log("Solicitud enviada al Admin.")
        messagebox.showinfo("Info", "Solicitud enviada. Espera confirmación.")

    def seleccionar_archivo(self):
        if not self.conectado:
            return

        ruta = filedialog.askopenfilename()
        if ruta:
            try:
                with open(ruta, "rb") as f:
                    content = f.read()

                b64 = base64.b64encode(content).decode("utf-8")

                self.enviar_respuesta("archivo",
                                      {"nombre": os.path.basename(ruta), "contenido": b64})

                self.agregar_log(f"Enviado: {os.path.basename(ruta)}")

            except Exception as e:
                self.agregar_log(f"Error: {e}")

    def guardar_archivo_recibido(self, nombre, contenido_base64):
        try:
            path = os.path.join(os.path.expanduser("~"), "Downloads", nombre)
            with open(path, "wb") as f:
                f.write(base64.b64decode(contenido_base64))

            self.agregar_log(f"Recibido: {path}")
            messagebox.showinfo("Archivo", f"Recibido: {nombre}\nGuardado en Descargas.")

        except Exception as e:
            self.agregar_log(f"Error guardar: {e}")

    def iniciar_transmision(self):
        self.streaming = True
        self.agregar_log(">>> STREAM START <<<")

        threading.Thread(target=self.bucle_transmision, daemon=True).start()

    def bucle_transmision(self):
        while self.streaming and self.conectado:
            try:
                img = ImageGrab.grab()
                img = img.resize((800, 600))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=40)

                data = base64.b64encode(buf.getvalue()).decode()
                self.enviar_respuesta("screenshot", {"data": data})

                time.sleep(0.05)

            except:
                self.streaming = False
                break

    def enviar_respuesta(self, tipo, datos):
        if self.conectado:
            try:
                self.socket_cliente.sendall(
                    (json.dumps({'tipo': tipo, **datos}) + "\n").encode()
                )
            except:
                pass

    def solicitar_autorizacion(self, accion, datos):
        return True

    def apagar_pc(self):
        pass

    def bloquear_entrada(self):
        self.entrada_bloqueada = True
        self.lbl_estado_entrada.config(text="Bloqueada", fg="red")
        self.agregar_log("Input Bloqueado")

        threading.Thread(target=self.ciclo_bloqueo, daemon=True).start()

        if platform.system() == "Windows":
            try:
                ctypes.windll.user32.BlockInput(True)
            except:
                pass

    def desbloquear_entrada(self):
        self.entrada_bloqueada = False
        self.lbl_estado_entrada.config(text="Desbloqueada", fg="green")
        self.agregar_log("Input Desbloqueado")

        if platform.system() == "Windows":
            try:
                ctypes.windll.user32.BlockInput(False)
            except:
                pass

    def ciclo_bloqueo(self):
        while self.entrada_bloqueada and self.conectado:
            if platform.system() == "Windows":
                ctypes.windll.user32.SetCursorPos(0, 0)
            time.sleep(0.01)

    def denegar_ping(self):
        self.ping_bloqueado = True
        self.lbl_estado_ping.config(text="Denegado", fg="red")
        self.agregar_log("Ping Bloqueado")

    def permitir_ping(self):
        self.ping_bloqueado = False
        self.lbl_estado_ping.config(text="Permitido", fg="green")
        self.agregar_log("Ping Permitido")

    def bloquear_sitios(self, s):
        self.agregar_log(f"Webs bloqueadas: {s}")

    def desbloquear_sitios(self, s):
        self.agregar_log(f"Webs liberadas: {s}")

    def agregar_log(self, msg):
        t = datetime.now().strftime("%H:%M:%S")
        self.txt_logs.config(state=tk.NORMAL)
        self.txt_logs.insert(tk.END, f"[{t}] {msg}\n")
        self.txt_logs.see(tk.END)
        self.txt_logs.config(state=tk.DISABLED)

    def agregar_mensaje_chat(self, user, msg):
        self.txt_chat.config(state=tk.NORMAL)
        self.txt_chat.insert(tk.END, f"{user}: {msg}\n")
        self.txt_chat.see(tk.END)
        self.txt_chat.config(state=tk.DISABLED)

    def enviar_mensaje(self):
        msg = self.entry_mensaje.get()
        if msg:
            self.enviar_respuesta("chat", {"mensaje": msg})
            self.agregar_mensaje_chat("Yo", msg)
            self.entry_mensaje.delete(0, tk.END)

    def cerrar_aplicacion(self):
        self.desconectar_servidor()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ClienteAgente(root)
    root.mainloop()
