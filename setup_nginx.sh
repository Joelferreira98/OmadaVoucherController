#!/bin/bash

# Script para configurar Nginx como proxy reverso
echo "🌐 Configurando Nginx para aplicação voucher..."

# Instalar Nginx se não estiver instalado
if ! command -v nginx &> /dev/null; then
    echo "📦 Instalando Nginx..."
    sudo apt update
    sudo apt install nginx -y
fi

# Backup da configuração padrão
sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup

# Criar configuração para aplicação voucher
sudo tee /etc/nginx/sites-available/voucher-app > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;
    
    # Configurações de segurança
    client_max_body_size 20M;
    
    # Logs
    access_log /var/log/nginx/voucher-app.access.log;
    error_log /var/log/nginx/voucher-app.error.log;
    
    # Arquivos estáticos
    location /static/ {
        alias /opt/voucher-app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Proxy para aplicação Flask
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # WebSocket support (se necessário)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Página de erro personalizada
    error_page 502 503 504 /maintenance.html;
    location = /maintenance.html {
        root /opt/voucher-app/static;
        internal;
    }
}
EOF

# Criar página de manutenção
sudo mkdir -p /opt/voucher-app/static
sudo tee /opt/voucher-app/static/maintenance.html > /dev/null << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Sistema em Manutenção</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
        .container { max-width: 500px; margin: 0 auto; }
        .icon { font-size: 48px; margin-bottom: 20px; }
        h1 { color: #e74c3c; }
        p { color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">🔧</div>
        <h1>Sistema em Manutenção</h1>
        <p>O sistema está temporariamente indisponível para manutenção.</p>
        <p>Tente novamente em alguns minutos.</p>
    </div>
</body>
</html>
EOF

# Desabilitar site padrão e habilitar voucher-app
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/voucher-app /etc/nginx/sites-enabled/

# Testar configuração Nginx
echo "🔍 Testando configuração Nginx..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Configuração Nginx válida"
    
    # Reiniciar e habilitar Nginx
    sudo systemctl restart nginx
    sudo systemctl enable nginx
    
    echo "🌐 Nginx configurado com sucesso!"
    echo ""
    echo "📋 Acesso à aplicação:"
    echo "http://SEU-IP (porta 80)"
    echo "http://localhost (porta 80)"
    echo ""
    echo "📊 Status dos serviços:"
    sudo systemctl status nginx --no-pager -l
    echo ""
    echo "📝 Logs úteis:"
    echo "# Logs Nginx"
    echo "sudo tail -f /var/log/nginx/voucher-app.access.log"
    echo "sudo tail -f /var/log/nginx/voucher-app.error.log"
    echo ""
    echo "# Logs aplicação"
    echo "sudo journalctl -u voucher-app -f"
else
    echo "❌ Erro na configuração Nginx"
    echo "Verifique os logs: sudo nginx -t"
fi