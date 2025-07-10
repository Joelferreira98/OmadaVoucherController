#!/bin/bash

# Script para copiar .env para o servidor VPS
echo "Copiando .env para o servidor VPS..."

# Verifica se o arquivo .env existe
if [ ! -f ".env" ]; then
    echo "Arquivo .env não encontrado. Criando..."
    cat > .env << EOF
# Database Configuration
DATABASE_URL=mysql+pymysql://JOEL:admin123@localhost:3306/omada_voucher_system

# Flask Security Configuration
SESSION_SECRET=f7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8

# Omada Controller Configuration (configure after installation)
OMADA_CONTROLLER_URL=
OMADA_CLIENT_ID=
OMADA_CLIENT_SECRET=
OMADA_OMADAC_ID=
EOF
fi

# Copia o arquivo .env para o VPS
sudo cp .env /opt/voucher-app/

# Verifica se o arquivo foi copiado
if [ -f "/opt/voucher-app/.env" ]; then
    echo "✅ Arquivo .env copiado com sucesso para /opt/voucher-app/"
    echo "🔧 Configurações aplicadas:"
    cat /opt/voucher-app/.env
    
    # Reinicia o serviço se existir
    if systemctl is-active --quiet voucher-app; then
        echo "🔄 Reiniciando serviço..."
        sudo systemctl restart voucher-app
        echo "✅ Serviço reiniciado"
    else
        echo "ℹ️  Serviço não encontrado. Execute manualmente:"
        echo "cd /opt/voucher-app && python main.py"
    fi
else
    echo "❌ Erro ao copiar arquivo .env"
    exit 1
fi