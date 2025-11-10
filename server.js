// --- server.js ---
const net = require('net');
const { WebSocketServer } = require('ws');

const TCP_PORT = 9090;
const WS_PORT = 8080;

const clients = new Map();
let adminWs = null;

// --- 1. Servidor TCP para los Clientes (Actualizado) ---
const tcpServer = net.createServer((socket) => {
    const addr = `${socket.remoteAddress}:${socket.remotePort}`;
    console.log(`[TCP] Nuevo cliente conectado: ${addr}`);
    clients.set(addr, socket);
    broadcastClientList();

    // --- ACTUALIZADO: Manejador de datos ---
    socket.on('data', (data) => {
        const message = data.toString().trim();
        console.log(`[TCP] Datos de ${addr}: ${message}`);

        // Si es un mensaje de chat DEL CLIENTE (ej. "CHAT:Hola admin")
        if (message.startsWith('CHAT:')) {
            // Lo reenviamos a la GUI (si está conectada)
            if (adminWs && adminWs.readyState === adminWs.OPEN) {
                adminWs.send(JSON.stringify({
                    type: 'chat-message',
                    from: addr, // De qué cliente vino
                    message: message.substring(5) // Quitamos el prefijo 'CHAT:'
                }));
            }
        }
        // Aquí irían otros datos que el cliente pueda enviar (ej. capturas)
    });
    // --- FIN ACTUALIZACIÓN ---

    socket.on('close', () => {
        console.log(`[TCP] Cliente desconectado: ${addr}`);
        clients.delete(addr);
        broadcastClientList();
    });

    socket.on('error', (err) => {
        console.log(`[TCP] Error de socket ${addr}: ${err.message}`);
        clients.delete(addr);
        broadcastClientList();
    });
});

// --- 2. Servidor WebSocket para la GUI (Sin cambios) ---
const wss = new WebSocketServer({ port: WS_PORT });

wss.on('connection', (ws) => {
    console.log('[WS] Panel de Admin conectado.');
    adminWs = ws;
    broadcastClientList(); // Enviamos la lista al conectar

    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);
            console.log('[WS] Comando recibido de la GUI:', data);

            // Esta lógica ya maneja el envío de 'CHAT:...' al cliente
            if (data.action === 'send-command' && data.target) {
                const targetSocket = clients.get(data.target);
                
                if (targetSocket) {
                    console.log(`Enviando comando '${data.command}' a ${data.target}`);
                    targetSocket.write(data.command); // Envía (ej. 'SHUTDOWN' o 'CHAT:Hola')
                } else {
                    console.log(`[WS] Error: Cliente ${data.target} no encontrado.`);
                }
            }
        } catch (e) {
            console.log('[WS] Error al procesar mensaje:', e.message);
        }
    });

    ws.on('close', () => {
        console.log('[WS] Panel de Admin desconectado.');
        adminWs = null;
    });
});

// --- 3. Función de Ayuda (Sin cambios) ---
function broadcastClientList() {
    if (adminWs && adminWs.readyState === adminWs.OPEN) {
        const clientList = Array.from(clients.keys());
        adminWs.send(JSON.stringify({
            type: 'client-list',
            clients: clientList
        }));
    }
}

// --- Iniciar todo (Sin cambios) ---
tcpServer.listen(TCP_PORT, '0.0.0.0', () => {
    console.log(`Servidor TCP (Clientes) escuchando en puerto ${TCP_PORT}`);
});
console.log(`Servidor WebSocket (Admin) escuchando en puerto ${WS_PORT}`);