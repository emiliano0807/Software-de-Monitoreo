const net = require('net');
const { exec } = require('child_process');
const os = require('os'); // <-- AHORA SÍ LA VAMOS A USAR
const readline = require('readline');

// ¡¡CAMBIA ESTO!! por la IP de tu PC Servidor
// 127.0.0.1 (localhost) si pruebas todo en la misma PC.
const SERVER_HOST = '127.0.0.1'; 
const SERVER_PORT = 9090;

function connectToServer() {
    const client = new net.Socket();
    let rl; // Definir rl aquí para que sea accesible en 'close'

    client.connect(SERVER_PORT, SERVER_HOST, () => {
        console.log(`[CLIENTE] Conectado al servidor en ${SERVER_HOST}:${SERVER_PORT}`);
        console.log('--- Chat con Admin ---');
        console.log('Escribe un mensaje y presiona Enter para chatear.');
        
        // Iniciar el lector de línea solo después de conectar
        rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });

        rl.setPrompt('> ');
        rl.prompt();

        rl.on('line', (line) => {
            const message = line.trim();
            if (message) {
                // Enviamos el mensaje al servidor con el prefijo 'CHAT:'
                client.write(`CHAT:${message}`);
            }
            rl.prompt();
        });
    });

    // Esta es la función CLAVE: maneja los comandos del servidor
    client.on('data', (data) => {
        const command = data.toString().trim();
        
        // Si es un mensaje de chat DEL ADMIN
        if (command.startsWith('CHAT:')) {
            const message = command.substring(5);
            process.stdout.write('\r' + ' '.repeat(process.stdout.columns) + '\r'); // Borra la línea actual
            console.log(`[Admin]: ${message}`);
            rl.prompt(true); // Vuelve a mostrar el prompt (>)

        // *** ¡ESTA ES LA CORRECCIÓN! ***
        } else if (command === 'SHUTDOWN') {
            console.log('\n[CLIENTE] Recibido comando de apagado...');
            client.write('CHAT:Comando de apagado recibido. Apagando...');

            let shutdownCommand = '';

            // 1. Usamos 'os' para detectar la plataforma
            const platform = os.platform();

            // 2. Elegimos el comando correcto
            if (platform === 'win32') {
                shutdownCommand = 'shutdown /s /t 1'; // Windows
            } else if (platform === 'linux' || platform === 'darwin') {
                shutdownCommand = 'shutdown -h now'; // Linux o macOS
            } else {
                console.log('[CLIENTE] Sistema operativo no compatible para apagado.');
                client.write('CHAT:Error. SO no compatible.');
                return;
            }

            // 3. ¡EJECUTAMOS EL COMANDO!
            console.log(`[CLIENTE] Ejecutando: ${shutdownCommand}`);
            
            // --- ¡¡PELIGRO!! ---
            // Descomenta la siguiente línea para permitir el apagado real.
            exec(shutdownCommand);
            // --- ---

            client.end(); // Cerramos la conexión después de ejecutar
        }
    });

    client.on('close', () => {
        console.log('\n--- Fin del Chat ---');
        console.log('Conexión cerrada. Reintentando en 5 segundos...');
        if (rl) rl.close(); // Cerramos el lector de terminal
        setTimeout(connectToServer, 5000);
    });

    client.on('error', (err) => {
        if (err.code !== 'ECONNREFUSED') {
            console.log(`\nError de conexión: ${err.message}`);
        }
    });
}

// Iniciar la primera conexión
connectToServer();