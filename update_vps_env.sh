#!/bin/bash

# Script para atualizar o arquivo .env no VPS
echo "🔧 Atualizando configuração do VPS..."

# Cria arquivo .env para VPS com MySQL
cat > /tmp/vps_env << 'EOF'
# Database Configuration - MySQL Local
DATABASE_URL=mysql+pymysql://JOEL:admin123@localhost:3306/omada_voucher_system

# Flask Security Configuration
SESSION_SECRET=f7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8

# Omada Controller Configuration
OMADA_CONTROLLER_URL=
OMADA_CLIENT_ID=
OMADA_CLIENT_SECRET=
OMADA_OMADAC_ID=
EOF

# Instrução para o usuário
echo "📋 Para corrigir no VPS, execute no servidor:"
echo ""
echo "# Copie o arquivo .env para o VPS"
echo "sudo cp /tmp/vps_env /opt/voucher-app/.env"
echo ""
echo "# Ou crie manualmente:"
echo "sudo nano /opt/voucher-app/.env"
echo ""
echo "# E cole o conteúdo:"
cat /tmp/vps_env
echo ""
echo "# Depois reinicie o serviço:"
echo "sudo systemctl restart voucher-app"
echo ""
echo "# Ou execute manualmente:"
echo "cd /opt/voucher-app && python main.py"
echo ""
echo "✅ Configuração preparada para VPS"