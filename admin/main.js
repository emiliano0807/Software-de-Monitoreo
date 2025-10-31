// --- main.js (Este es JavaScript del NAVEGADOR) ---

// Conectamos al servidor WebSocket (el puerto 8080)
const ws = new WebSocket('ws://localhost:8080');

// Referencias a los elementos HTML
const clientList = document.getElementById('client-list');
const btnTest = document.getElementById('btn-test');
const btnShutdown = document.getElementById('btn-shutdown');

ws.onopen = () => {
    console.log('Conectado al servidor WebSocket (Admin)');
};

// Esta es la función CLAVE: escucha mensajes del servidor
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    // Si el servidor nos envía la lista de clientes
    if (data.type === 'client-list') {
        console.log('Lista de clientes actualizada:', data.clients);
        
        // Limpiamos la lista actual
        clientList.innerHTML = '';
        
        // Volvemos a llenar la lista
        data.clients.forEach(clientAddr => {
            const option = document.createElement('option');
            option.value = clientAddr;
            option.textContent = clientAddr;
            clientList.appendChild(option);
        });
    }
};

ws.onclose = () => {
    console.log('Desconectado del servidor WebSocket. Recarga la página.');
};

// --- Lógica de los Botones ---

function sendCommand(command) {
    const selectedClient = clientList.value; // Obtiene el cliente seleccionado
    if (!selectedClient) {
        alert('Por favor, selecciona un cliente de la lista.');
        return;
    }

    if (command === 'SHUTDOWN') {
        if (!confirm(`¿Seguro que quieres apagar la PC ${selectedClient}?`)) {
            return;
        }
    }
    
    // Construimos el mensaje JSON para el servidor
    const message = {
        action: 'send-command',
        target: selectedClient, // A quién va dirigido
        command: command        // Qué comando enviar
    };

    // Enviamos el mensaje (como string) al servidor
    ws.send(JSON.stringify(message));
}

// Asignamos las funciones a los botones
btnTest.onclick = () => sendCommand('TEST_COMMAND');
btnShutdown.onclick = () => sendCommand('SHUTDOWN');