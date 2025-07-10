#!/bin/bash

# Script para baixar e instalar automaticamente na VPS
# Execute este comando para instalação completa em uma linha

echo "📥 Download e Instalação Automática"
echo "==================================="
echo ""
echo "Baixando e executando script de instalação para VPS..."
echo ""

# Verificar se é root
if [[ $EUID -ne 0 ]]; then
    echo "❌ Execute como root: sudo bash download_and_install.sh"
    exit 1
fi

# Baixar script de instalação
echo "🔽 Baixando script de instalação..."
curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/install_vps.sh -o /tmp/install_vps.sh

if [ $? -eq 0 ]; then
    echo "✅ Script baixado com sucesso"
    echo ""
    echo "🚀 Iniciando instalação..."
    echo ""
    
    # Executar script de instalação
    bash /tmp/install_vps.sh
    
    # Limpar arquivo temporário
    rm -f /tmp/install_vps.sh
    
else
    echo "❌ Erro ao baixar script de instalação"
    echo "Verifique sua conexão com a internet e tente novamente"
    exit 1
fi