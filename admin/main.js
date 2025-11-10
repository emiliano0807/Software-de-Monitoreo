// --- main.js (Este es JavaScript del NAVEGADOR) ---

// Conectamos al servidor WebSocket (el puerto 8080)
const ws = new WebSocket('ws://localhost:8080');

// Referencias a los elementos HTML
const clientList = document.getElementById('client-list');
const btnTest = document.getElementById('btn-test');
const btnShutdown = document.getElementById('btn-shutdown');

// --- NUEVO ---
const chatBox = document.getElementById('chat-box');
const chatInput = document.getElementById('chat-input');
const btnChatSend = document.getElementById('chat-send');
// --- FIN NUEVO ---

ws.onopen = () => {
    console.log('Conectado al servidor WebSocket (Admin)');
};

// Esta es la función CLAVE: escucha mensajes del servidor
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    // Si el servidor nos envía la lista de clientes
    if (data.type === 'client-list') {
        console.log('Lista de clientes actualizada:', data.clients);
        updateClientList(data.clients);
    
    // --- NUEVO ---
    // Si el servidor nos reenvía un mensaje de chat DE UN CLIENTE
    } else if (data.type === 'chat-message') {
        appendChatMessage(`[${data.from}]: ${data.message}`);
    }
    // --- FIN NUEVO ---
};

ws.onclose = () => {
    console.log('Desconectado del servidor WebSocket. Recarga la página.');
    appendChatMessage("[Sistema]: Desconectado del servidor.");
};

function updateClientList(clients) {
    // Guardamos el cliente que estaba seleccionado
    const selectedClient = clientList.value; 
    
    clientList.innerHTML = ''; // Limpiamos la lista
    
    clients.forEach(clientAddr => {
        const option = document.createElement('option');
        option.value = clientAddr;
        option.textContent = clientAddr;
        clientList.appendChild(option);
    });

    // Intentamos volver a seleccionar el cliente que estaba
    if (clients.includes(selectedClient)) {
        clientList.value = selectedClient;
    }
}

// --- NUEVO ---
function appendChatMessage(message) {
    chatBox.innerHTML += `<div>${message}</div>`;
    // Auto-scroll al fondo
    chatBox.scrollTop = chatBox.scrollHeight;
}
// --- FIN NUEVO ---

// --- Lógica de los Botones ---

function getSelectedClient() {
    const selectedClient = clientList.value;
    if (!selectedClient) {
        alert('Por favor, selecciona un cliente de la lista.');
        return null;
    }
    return selectedClient;
}

function sendCommand(command) {
    const targetClient = getSelectedClient();
    if (!targetClient) return;

    if (command === 'SHUTDOWN') {
        if (!confirm(`¿Seguro que quieres apagar la PC ${targetClient}?`)) {
            return;
        }
    }
    
    ws.send(JSON.stringify({
        action: 'send-command',
        target: targetClient,
        command: command
    }));
}

// Asignamos las funciones a los botones
btnTest.onclick = () => sendCommand('TEST_COMMAND');
btnShutdown.onclick = () => sendCommand('SHUTDOWN');

// --- NUEVO ---
// Lógica para enviar un mensaje de chat
btnChatSend.onclick = () => {
    const targetClient = getSelectedClient();
    if (!targetClient) return;

    const message = chatInput.value;
    if (message.trim() === '') return;

    // 1. Enviar el mensaje al servidor (para que lo reenvíe al cliente)
    ws.send(JSON.stringify({
        action: 'send-command',
        target: targetClient,
        // Usamos un prefijo 'CHAT:' para que el cliente sepa qué es
        command: `CHAT:${message}` 
    }));

    // 2. Mostrar nuestro propio mensaje en la GUI
    appendChatMessage(`[Admin]: ${message}`);
    chatInput.value = ''; // Limpiar el input
};
// --- FIN NUEVO ---