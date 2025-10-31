// --- client.js ---
const net = require('net');
const { exec } = require('child_process'); // Para ejecutar comandos (como 'shutdown')
const os = require('os');

// ¡¡CAMBIA ESTO!! por la IP de tu PC Servidor
const SERVER_HOST = '127.0.0.1'; 
const SERVER_PORT = 9090;

function connectToServer() {
    const client = new net.Socket();

    client.connect(SERVER_PORT, SERVER_HOST, () => {
        console.log(`Conectado al servidor en ${SERVER_HOST}:${SERVER_PORT}`);
    });

    // Esta es la función CLAVE: maneja los comandos del servidor
    client.on('data', (data) => {
        const command = data.toString().trim();
        console.log(`Comando recibido: ${command}`);

        // --- AQUÍ AÑADES TUS FUNCIONES ---
        
        if (command === 'TEST_COMMAND') {
            console.log('¡El servidor envió un comando de prueba!');
        
        } else if (command === 'SHUTDOWN') {
            console.log('Recibido comando de apagado. Apagando...');
            
            // Detectamos el OS para el comando correcto
            // ¡¡ESTO NECESITA PERMISOS DE ADMINISTRADOR!!
            try {
                if (os.platform() === 'win32') {
                    exec('shutdown /s /t 0', (err) => { if(err) console.log(err); });
                } else { // Linux o macOS
                    exec('shutdown now', (err) => { if(err) console.log(err); });
                }
            } catch (e) {
                console.log("Error al ejecutar apagado:", e.message);
            }
        }
    });

    client.on('close', () => {
        console.log('Conexión cerrada. Reintentando en 5 segundos...');
        // Lógica de reconexión
        setTimeout(connectToServer, 5000);
    });

    client.on('error', (err) => {
        // No imprimimos error de conexión, 'close' lo manejará
        if (err.code !== 'ECONNREFUSED') {
            console.log(`Error de conexión: ${err.message}`);
        }
    });
}

// Iniciar la primera conexión
connectToServer();