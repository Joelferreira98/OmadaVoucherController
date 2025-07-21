#!/bin/bash

# Script para criar serviço systemd para a aplicação
echo "🚀 Criando serviço systemd para aplicação voucher..."

# Criar arquivo de serviço systemd
sudo tee /etc/systemd/system/voucher-app.service > /dev/null << 'EOF'
[Unit]
Description=Voucher Management System
After=network.target mysql.service
Requires=mysql.service

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=/opt/voucher-app
Environment=PATH=/opt/voucher-app/venv/bin
ExecStart=/opt/voucher-app/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 30 --keep-alive 2 --max-requests 1000 --preload main:app
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

[Install]
WantedBy=multi-user.target
EOF

# Recarregar daemon systemd
sudo systemctl daemon-reload

# Habilitar serviço para iniciar no boot
sudo systemctl enable voucher-app

# Iniciar serviço
sudo systemctl start voucher-app

# Verificar status
echo "📊 Status do serviço:"
sudo systemctl status voucher-app --no-pager

echo ""
echo "✅ Serviço criado com sucesso!"
echo ""
echo "📋 Comandos úteis:"
echo "# Ver status do serviço"
echo "sudo systemctl status voucher-app"
echo ""
echo "# Iniciar serviço"
echo "sudo systemctl start voucher-app"
echo ""
echo "# Parar serviço"
echo "sudo systemctl stop voucher-app"
echo ""
echo "# Reiniciar serviço"
echo "sudo systemctl restart voucher-app"
echo ""
echo "# Ver logs do serviço"
echo "sudo journalctl -u voucher-app -f"
echo ""
echo "# Desabilitar serviço do boot"
echo "sudo systemctl disable voucher-app"
echo ""
echo "🌐 Aplicação disponível em:"
echo "http://localhost:5000"
echo "http://SEU-IP:5000"
