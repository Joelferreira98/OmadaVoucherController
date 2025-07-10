#!/bin/bash

# Script completo para configurar aplicação como serviço
echo "🚀 Configuração completa de serviço - Voucher Management System"
echo "======================================================="

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Este script deve ser executado como root (sudo)"
    exit 1
fi

# Verificar se diretório da aplicação existe
if [ ! -d "/opt/voucher-app" ]; then
    echo "❌ Diretório /opt/voucher-app não encontrado"
    echo "Execute primeiro a instalação da aplicação"
    exit 1
fi

echo "📋 Etapa 1: Criando serviço systemd..."

# Criar arquivo de serviço systemd
cat > /etc/systemd/system/voucher-app.service << 'EOF'
[Unit]
Description=Voucher Management System - Omada Controller Integration
Documentation=https://github.com/Joelferreira98/OmadaVoucherController
After=network.target mysql.service
Requires=mysql.service

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=/opt/voucher-app
Environment=PATH=/opt/voucher-app/venv/bin
EnvironmentFile=/opt/voucher-app/.env
ExecStart=/opt/voucher-app/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 30 --keep-alive 2 --max-requests 1000 --preload main:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=voucher-app

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/voucher-app

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Serviço systemd criado"

echo "📋 Etapa 2: Configurando Nginx..."

# Instalar Nginx se necessário
if ! command -v nginx &> /dev/null; then
    echo "📦 Instalando Nginx..."
    apt update
    apt install nginx -y
fi

# Backup da configuração padrão
cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup 2>/dev/null || true

# Criar configuração Nginx
cat > /etc/nginx/sites-available/voucher-app << 'EOF'
server {
    listen 80;
    server_name _;
    
    # Configurações de segurança
    client_max_body_size 20M;
    server_tokens off;
    
    # Logs
    access_log /var/log/nginx/voucher-app.access.log;
    error_log /var/log/nginx/voucher-app.error.log;
    
    # Arquivos estáticos
    location /static/ {
        alias /opt/voucher-app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff;
        add_header X-Frame-Options DENY;
        add_header X-XSS-Protection "1; mode=block";
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
        
        # Headers de segurança
        proxy_set_header X-Content-Type-Options nosniff;
        proxy_set_header X-Frame-Options DENY;
        proxy_set_header X-XSS-Protection "1; mode=block";
        
        # WebSocket support
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
mkdir -p /opt/voucher-app/static
cat > /opt/voucher-app/static/maintenance.html << 'EOF'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema em Manutenção - Voucher Management</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container { 
            background: white;
            padding: 60px 40px;
            border-radius: 20px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            text-align: center;
            max-width: 500px;
            margin: 20px;
        }
        .icon { 
            font-size: 64px;
            margin-bottom: 30px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        h1 { 
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 28px;
            font-weight: 600;
        }
        p { 
            color: #7f8c8d;
            line-height: 1.6;
            margin-bottom: 15px;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            color: #95a5a6;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">🔧</div>
        <h1>Sistema em Manutenção</h1>
        <p>O sistema de gerenciamento de vouchers está temporariamente indisponível para manutenção.</p>
        <p>Estamos atualizando o sistema para melhor atendê-lo.</p>
        <p><strong>Tente novamente em alguns minutos.</strong></p>
        <div class="footer">
            Voucher Management System<br>
            Integração com Omada Controller
        </div>
    </div>
</body>
</html>
EOF

# Configurar sites Nginx
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/voucher-app /etc/nginx/sites-enabled/

echo "✅ Nginx configurado"

echo "📋 Etapa 3: Configurando firewall..."

# Configurar UFW se disponível
if command -v ufw &> /dev/null; then
    ufw --force enable
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    echo "✅ Firewall configurado"
else
    echo "⚠️  UFW não disponível, configure o firewall manualmente"
fi

echo "📋 Etapa 4: Iniciando serviços..."

# Testar configuração Nginx
nginx -t
if [ $? -ne 0 ]; then
    echo "❌ Erro na configuração Nginx"
    exit 1
fi

# Recarregar daemon systemd
systemctl daemon-reload

# Habilitar e iniciar serviços
systemctl enable voucher-app
systemctl enable nginx

systemctl restart nginx
systemctl restart voucher-app

# Aguardar inicialização
sleep 5

echo "📋 Etapa 5: Verificando status..."

# Verificar status dos serviços
echo "📊 Status Nginx:"
systemctl status nginx --no-pager -l

echo ""
echo "📊 Status Voucher App:"
systemctl status voucher-app --no-pager -l

echo ""
echo "🔍 Testando conectividade:"
curl -I http://localhost 2>/dev/null || echo "❌ Aplicação não responde"

echo ""
echo "======================================================="
echo "✅ CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!"
echo "======================================================="
echo ""
echo "🌐 Acesso à aplicação:"
echo "   http://SEU-IP-SERVIDOR"
echo "   http://localhost (no próprio servidor)"
echo ""
echo "👤 Login padrão:"
echo "   Usuário: master"
echo "   Senha: admin123"
echo ""
echo "📋 Comandos úteis:"
echo "   # Status dos serviços"
echo "   sudo systemctl status voucher-app"
echo "   sudo systemctl status nginx"
echo ""
echo "   # Logs dos serviços"
echo "   sudo journalctl -u voucher-app -f"
echo "   sudo tail -f /var/log/nginx/voucher-app.access.log"
echo ""
echo "   # Reiniciar serviços"
echo "   sudo systemctl restart voucher-app"
echo "   sudo systemctl restart nginx"
echo ""
echo "🔧 Próximos passos:"
echo "1. Acessar aplicação via navegador"
echo "2. Fazer login com usuário master"
echo "3. Configurar Omada Controller"
echo "4. Sincronizar sites"
echo "5. Criar administradores e vendedores"
echo ""
echo "📚 Documentação completa disponível em:"
echo "   /opt/voucher-app/README.md"
echo "   /opt/voucher-app/VPS_CSRF_FIX.md"