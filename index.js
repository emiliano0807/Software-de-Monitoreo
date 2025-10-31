const net = require('net');
const {WebSocketServer} = require('ws');
const os = require('os');

const TCP_PORT = 9090;
const WS_PORT = 8080;

const clientes = new Map();
let adminWs = null;

const tcpServer = net.createServer((socket)=>{
    const addr = `${socket.remoteAddress}:${socket.remotePort}`;
    console.log(`[TCP] Nuevo cliente conectado: ${addr}`);
    
    clientes.set(addr, socket);

    broadcastClientList();

    socket.on('data', (data)=>{
        console.log(`[TCP] Datos de ${addr}: ${data.toString}`);
    });

    socket.on('close', ()=>{
        console.log(`[TCP] Cliente desconectado: ${addr}`);
        clientes.delete(addr);
        broadcastClientList();
    });

    socket.on('error', (err)=>{
        console.log(`[TCP] Error con el cliente ${addr}: ${err.message}`);
        clientes.delete(addr);
        broadcastClientList();
    });
});

const wss = new WebSocketServer({port: WS_PORT});

wss.on('connection', (ws)=>{
    console.log('[WS] Panel de administración conectado');
    adminWs = ws;
    broadcastClientList();

    ws.on('message', (msg)=>{
        try{
            const data = JSON.parse(msg);
            console.log('[WS] Mensaje recibido del panel de administración:', data);
            
            if(data.action === 'sendCommand' && data.target){
                targetSocket.write(data.command);
            }else{
                console.log('[WS] Acción desconocida o falta de objetivo');
            }
        }catch(err){
            console.log('[WS] Error al procesar el mensaje:', err.message);
        }
    });

    ws.on('close', ()=>{
        console.log('[WS] Panel de administración desconectado');
        adminWs = null;
    });
});

function broadcastClientList(){
    if(adminWs && adminWs.readyState === adminWs.OPEN){
        const clientList = Array.from(clientes.keys());

        adminWs.send(JSON.stringify({
            type: 'client-List',
            clients: clientList
        }));
    }
}
tcpServer.listen(TCP_PORT, '0.0.0.0', ()=>{
    console.log(`[TCP] Servidor escuchando en el puerto ${TCP_PORT}`);
})
console.log(`[WS] Servidor WebSocket escuchando en el puerto ${WS_PORT}`);