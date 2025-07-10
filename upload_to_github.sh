#!/bin/bash

# Script para fazer upload dos arquivos para o GitHub
# Execute este script para enviar todos os arquivos para o repositório

echo "🚀 Upload dos arquivos para o GitHub"
echo "===================================="
echo ""

# Verificar se o git está instalado
if ! command -v git &> /dev/null; then
    echo "Git não está instalado. Instalando..."
    sudo apt update
    sudo apt install -y git
fi

# Verificar se estamos em um repositório git
if [ ! -d ".git" ]; then
    echo "Inicializando repositório git..."
    git init
fi

# Configurar git (se necessário)
echo "Configurando git..."
read -p "Digite seu nome para o git: " GIT_NAME
read -p "Digite seu email para o git: " GIT_EMAIL

git config user.name "$GIT_NAME"
git config user.email "$GIT_EMAIL"

# Adicionar origem remota
echo "Adicionando repositório remoto..."
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/Joelferreira98/OmadaVoucherController.git

# Adicionar todos os arquivos
echo "Adicionando arquivos..."
git add .

# Fazer commit
echo "Fazendo commit..."
git commit -m "Initial commit - Complete voucher management system with Omada Controller integration"

# Fazer push para o GitHub
echo "Enviando para o GitHub..."
echo ""
echo "IMPORTANTE: Você precisará fornecer suas credenciais do GitHub"
echo "Username: Joelferreira98"
echo "Password: Use um Personal Access Token (não sua senha normal)"
echo ""
echo "Para criar um token:"
echo "1. Vá para: https://github.com/settings/tokens"
echo "2. Clique em 'Generate new token (classic)'"
echo "3. Selecione 'repo' permissions"
echo "4. Copie o token gerado"
echo ""
read -p "Pressione Enter para continuar..."

git push -u origin main

echo ""
echo "✅ Upload concluído!"
echo "Acesse: https://github.com/Joelferreira98/OmadaVoucherController"