#!/bin/bash

# Script de instalação rápida via URL
# Execute este comando em uma linha na sua VPS:
# curl -fsSL https://raw.githubusercontent.com/joel-0/voucher-system/main/quick_install.sh | sudo bash

echo "🚀 Instalação Rápida do Voucher System"
echo "======================================"
echo ""

# Baixar o script principal
echo "Baixando script de instalação..."
curl -fsSL https://raw.githubusercontent.com/joel-0/voucher-system/main/github_install.sh -o /tmp/github_install.sh

# Dar permissão de execução
chmod +x /tmp/github_install.sh

# Executar instalação
echo "Iniciando instalação..."
bash /tmp/github_install.sh

# Limpar arquivo temporário
rm -f /tmp/github_install.sh

echo "Instalação concluída!"