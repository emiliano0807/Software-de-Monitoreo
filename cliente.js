const net = require('net');
const { exec } = require('child_process');
const fs = require('fs');
const os = require('os');
const readline = require('readline');

// ¡¡CAMBIA ESTO!! por la IP de tu PC Servidor
const SERVER_HOST = '127.0.0.1'; 
const SERVER_PORT = 9090;

function connectToServer() {
    const client = new net.Socket();
    let rl; 

    client.connect(SERVER_PORT, SERVER_HOST, () => {
        console.log(`[CLIENTE] Conectado al servidor en ${SERVER_HOST}:${SERVER_PORT}`);
        // ... (resto del código de readline sin cambios)
        rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });
        rl.setPrompt('> ');
        rl.prompt();
        rl.on('line', (line) => {
            const message = line.trim();
            if (message) {
                client.write(`CHAT:${message}`);
            }
            rl.prompt();
        });
    });

    client.on('data', (data) => {
        const command = data.toString().trim();
        
        if (command.startsWith('CHAT:')) {
            const message = command.substring(5);
            process.stdout.write('\r' + ' '.repeat(process.stdout.columns) + '\r'); 
            console.log(`[Admin]: ${message}`);
            rl.prompt(true); 

        } else if (command === 'SHUTDOWN') {
            console.log('\n[CLIENTE] Recibido comando de apagado...');
            client.write('CHAT:Comando de apagado recibido. Apagando...');
            let shutdownCommand = '';
            const platform = os.platform();
            
            if (platform === 'win32') {
                shutdownCommand = 'shutdown /s /t 1'; // Windows
            } else if (platform === 'linux' || platform === 'darwin') {
                shutdownCommand = 'shutdown -h now'; // Linux o macOS
            } else {
                client.write('CHAT:Error. SO no compatible.');
                return;
            }
            
            // exec(shutdownCommand); // Descomentar para apagar
            client.end(); 
            
        // --- SECCIÓN DE SITIOS WEB (SIN CAMBIOS) ---
        } else if (command.startsWith('BLOCK_WEBSITE:')) {
            const website = command.substring(14).trim();
            blockWebsite(website, (err, msg) => {
                if (err) console.error(err);
                console.log(msg);
                client.write(`CHAT:${msg}`);
            });

        } else if (command.startsWith('UNBLOCK_WEBSITE:')) {
            const website = command.substring(16).trim();
            unblockWebsite(website, (err, msg) => {
                if (err) console.error(err);
                console.log(msg);
                client.write(`CHAT:${msg}`);
            });
        
        // --- ¡NUEVA LÓGICA DE PING! ---
        
        // 3.10.- Denegar Ping (Firewall)
        } else if (command === 'BLOCK_PING') {
            const ruleCommand = getFirewallRule('block_ping');
            exec(ruleCommand, (err, stdout, stderr) => {
                if(err) {
                    console.error(stderr);
                    client.write('CHAT:Error al bloquear ping. ¿Permisos?');
                } else {
                    console.log('Ping bloqueado.');
                    client.write('CHAT:Ping bloqueado exitosamente.');
                }
            });
            
        // 3.10.- Permitir Ping (Firewall)
        } else if (command === 'ALLOW_PING') {
            const ruleCommand = getFirewallRule('allow_ping');
            exec(ruleCommand, (err, stdout, stderr) => {
                if(err) {
                    console.error(stderr);
                    client.write('CHAT:Error al permitir ping. ¿Permisos?');
                } else {
                    console.log('Ping permitido.');
                    client.write('CHAT:Ping permitido exitosamente.');
                }
            });
        }
    });

    client.on('close', () => {
        console.log('\n--- Fin del Chat ---');
        console.log('Conexión cerrada. Reintentando en 5 segundos...');
        if (rl) rl.close(); 
        setTimeout(connectToServer, 5000);
    });

    client.on('error', (err) => {
        if (err.code !== 'ECONNREFUSED') {
            console.log(`\nError de conexión: ${err.message}`);
        }
    });
}

// --- Funciones de Ayuda de Sitios Web (SIN CAMBIOS) ---

function getHostsFilePath() {
    return os.platform() === 'win32'
        ? 'C:\\Windows\\System32\\drivers\\etc\\hosts'
        : '/etc/hosts';
}

function blockWebsite(website, callback) {
    const hostsFile = getHostsFilePath();
    const www = `www.${website}`;
    const entry = `\n127.0.0.1 ${website}\t#Bloqueado_por_Admin\n127.0.0.1 ${www}\t#Bloqueado_por_Admin`;
    
    fs.appendFile(hostsFile, entry, (err) => {
        if (err) {
            callback(err, `Error al bloquear ${website}. ¿Permisos?`);
        } else {
            if (os.platform() === 'win32') {
                exec('ipconfig /flushdns', (flushErr, stdout, stderr) => {
                    callback(null, `Sitio bloqueado ${website} (DNS cache flushed).`);
                });
            } else {
                callback(null, `Sitio bloqueado: ${website}`);
            }
        }
    });
}

function unblockWebsite(website, callback) {
    const hostsFile = getHostsFilePath();
    
    fs.readFile(hostsFile, 'utf8', (err, data) => {
        if (err) {
             return callback(err, `Error al leer hosts. ¿Permisos?`);
        }
        
        const www = `www.${website}`;
        const lines = data.split('\n');
        const newData = lines.filter(line => 
            !line.includes(website) && !line.includes(www)
        ).join('\n');

        fs.writeFile(hostsFile, newData, (err) => {
            if (err) {
                callback(err, `Error al desbloquear ${website}. ¿Permisos?`);
            } else {
                if (os.platform() === 'win32') {
                    exec('ipconfig /flushdns', (flushErr, stdout, stderr) => {
                        callback(null, `Sitio desbloqueado ${website} (DNS cache flushed).`);
                    });
                } else {
                    callback(null, `Sitio desbloqueado: ${website}`);
                }
            }
        });
    });
}


// --- ¡NUEVA FUNCIÓN DE FIREWALL! ---
// 3.10.- Denegar/Permitir Ping (Firewall)
function getFirewallRule(action) {
    const platform = os.platform();
    
    // Esta es la forma moderna e independiente del idioma para controlar el grupo
    // de reglas "Uso compartido de archivos e impresoras"
    const ruleGroup = '@firewallapi.dll,-28502';

    if (platform === 'win32') {
        if (action === 'block_ping') {
            // Desactiva el grupo de reglas que permite el ping
            // --- ¡ACTUALIZADO! Se añade profile=any ---
            return `netsh advfirewall firewall set rule group="${ruleGroup}" new enable=No profile=any`;
        } else { // 'allow_ping'
            // Activa el grupo de reglas que permite el ping
            // --- ¡ACTUALIZADO! Se añade profile=any ---
            return `netsh advfirewall firewall set rule group="${ruleGroup}" new enable=Yes profile=any`;
        }
    } else { // Linux (usando iptables - esta lógica no ha cambiado)
         if (action === 'block_ping') {
            return 'iptables -A INPUT -p icmp --icmp-type echo-request -j DROP';
        } else {
            return 'iptables -D INPUT -p icmp --icmp-type echo-request -j DROP';
        }
    }
}


// Iniciar la primera conexión
connectToServer();