// --- client.js ---
const net = require('net');
const { exec } = require('child_process');
const os = require('os');
const readline = require('readline'); // <-- NUEVO: Para leer de la terminal

// ¡¡CAMBIA ESTO!! por la IP de tu PC Servidor
const SERVER_HOST = '127.0.0.1'; 
const SERVER_PORT = 9090;

function connectToServer() {
    const client = new net.Socket();

    client.connect(SERVER_PORT, SERVER_HOST, () => {
        console.log(`Conectado al servidor en ${SERVER_HOST}:${SERVER_PORT}`);
        console.log('--- Chat con Admin ---');
        console.log('Escribe un mensaje y presiona Enter para chatear.');
    });

    // Esta es la función CLAVE: maneja los comandos del servidor
    client.on('data', (data) => {
        const command = data.toString().trim();
        
        // --- ACTUALIZADO ---
        if (command.startsWith('CHAT:')) {
            // Si es un mensaje de chat DEL ADMIN
            const message = command.substring(5);
            console.log(`\n[Admin]: ${message}`);
            // Volvemos a mostrar el prompt de chat
            rl.prompt(true); 

        } else if (command === 'LS') {
            console.log('\n¡El servidor envió un comando de prueba!');
            rl.prompt(true);

        } else if (command === 'shutdown /s /t 0') {
            console.log('\nRecibido comando de apagado. Apagando...');
            // ... (código de apagado) ...
        }
        // --- FIN ACTUALIZACIÓN ---
    });

    client.on('close', () => {
        console.log('\n--- Fin del Chat ---');
        console.log('Conexión cerrada. Reintentando en 5 segundos...');
        rl.close(); // Cerramos el lector de terminal
        setTimeout(connectToServer, 5000);
    });

    client.on('error', (err) => {
        if (err.code !== 'ECONNREFUSED') {
            console.log(`\nError de conexión: ${err.message}`);
        }
    });

    // --- NUEVO: Lógica para leer de la terminal ---
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });

    // Ponemos un "prompt" (>)
    rl.setPrompt('> ');
    rl.prompt();

    // Cuando el usuario escribe una línea (presiona Enter)
    rl.on('line', (line) => {
        const message = line.trim();
        if (message) {
            // Enviamos el mensaje al servidor con el prefijo 'CHAT:'
            client.write(`CHAT:${message}`);
        }
        // Volvemos a mostrar el prompt
        rl.prompt();
    });
    // --- FIN NUEVO ---
}

// Iniciar la primera conexión
connectToServer();