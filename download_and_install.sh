#!/bin/bash

# Script simplificado para download e instalação
# Este script baixa os arquivos da aplicação e executa a instalação

set -e

echo "========================================================="
echo "       Download e Instalação - Sistema de Vouchers"
echo "========================================================="
echo ""

# Verificar se curl está instalado
if ! command -v curl &> /dev/null; then
    echo "Instalando curl..."
    sudo apt update
    sudo apt install -y curl
fi

# Solicitar URL do repositório ou arquivo ZIP
echo "Para instalar o sistema, você precisa fornecer:"
echo "1. URL de um repositório Git, ou"
echo "2. URL de um arquivo ZIP com os arquivos da aplicação"
echo ""

read -p "Digite a URL do repositório ou arquivo ZIP: " REPO_URL

if [ -z "$REPO_URL" ]; then
    echo "❌ URL não informada!"
    exit 1
fi

# Criar diretório temporário
TEMP_DIR="/tmp/voucher-app-$(date +%s)"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

echo "📥 Fazendo download dos arquivos..."

# Verificar se é Git ou ZIP
if [[ "$REPO_URL" == *.git ]] || [[ "$REPO_URL" == *github.com* ]] || [[ "$REPO_URL" == *gitlab.com* ]]; then
    # É um repositório Git
    if ! command -v git &> /dev/null; then
        echo "Instalando git..."
        sudo apt update
        sudo apt install -y git
    fi
    
    git clone "$REPO_URL" app
    cd app
    
elif [[ "$REPO_URL" == *.zip ]]; then
    # É um arquivo ZIP
    if ! command -v unzip &> /dev/null; then
        echo "Instalando unzip..."
        sudo apt update
        sudo apt install -y unzip
    fi
    
    curl -L -o app.zip "$REPO_URL"
    unzip app.zip
    
    # Encontrar a pasta da aplicação
    if [ -f "app.py" ] && [ -f "main.py" ]; then
        # Arquivos estão na raiz
        echo "✓ Arquivos encontrados na raiz"
    else
        # Procurar em subpastas
        APP_DIR=$(find . -name "app.py" -type f | head -1 | xargs dirname)
        if [ -n "$APP_DIR" ]; then
            cd "$APP_DIR"
            echo "✓ Arquivos encontrados em: $APP_DIR"
        else
            echo "❌ Arquivos da aplicação não encontrados no ZIP!"
            exit 1
        fi
    fi
    
else
    echo "❌ URL não reconhecida! Use um repositório Git (.git) ou arquivo ZIP (.zip)"
    exit 1
fi

# Verificar se os arquivos necessários estão presentes
if [ ! -f "app.py" ] || [ ! -f "main.py" ]; then
    echo "❌ Arquivos obrigatórios não encontrados!"
    echo "Procurando por: app.py, main.py"
    echo "Conteúdo do diretório:"
    ls -la
    exit 1
fi

echo "✓ Arquivos da aplicação baixados com sucesso!"

# Verificar se o script de instalação está presente
if [ ! -f "install_vps.sh" ]; then
    echo "❌ Script de instalação (install_vps.sh) não encontrado!"
    echo "Criando script de instalação..."
    
    # Baixar script de instalação do repositório (caso não esteja incluído)
    curl -s -o install_vps.sh "https://raw.githubusercontent.com/exemplo/voucher-app/main/install_vps.sh" || {
        echo "❌ Não foi possível baixar o script de instalação!"
        echo "Certifique-se de que o arquivo install_vps.sh está incluído no repositório."
        exit 1
    }
fi

chmod +x install_vps.sh

echo ""
echo "🚀 Iniciando instalação automática..."
echo ""

# Executar script de instalação
bash install_vps.sh

echo ""
echo "✅ Instalação concluída!"