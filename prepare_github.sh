#!/bin/bash

# Script para preparar arquivos para upload no GitHub
echo "🔧 Preparando arquivos para o GitHub..."

# Limpar arquivos desnecessários
echo "Limpando arquivos desnecessários..."
rm -f *.pyc
rm -rf __pycache__
rm -rf .pytest_cache
rm -f *.log
rm -f *.tmp
rm -f *.bak

# Verificar arquivos essenciais
echo "Verificando arquivos essenciais..."
required_files=(
    "app.py"
    "main.py" 
    "models.py"
    "routes.py"
    "forms.py"
    "utils.py"
    "omada_api.py"
    "app_requirements.txt"
    "github_install.sh"
    "quick_install.sh"
    "README.md"
    "GITHUB_INSTALL.md"
    ".gitignore"
)

missing_files=()
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    echo "❌ Arquivos faltando:"
    for file in "${missing_files[@]}"; do
        echo "  - $file"
    done
    echo "Verifique se todos os arquivos estão presentes antes de continuar."
    exit 1
fi

# Verificar se existe diretório templates
if [ ! -d "templates" ]; then
    echo "❌ Diretório templates não encontrado!"
    exit 1
fi

# Verificar se existe diretório static
if [ ! -d "static" ]; then
    echo "❌ Diretório static não encontrado!"
    exit 1
fi

# Tornar scripts executáveis
echo "Configurando permissões..."
chmod +x github_install.sh
chmod +x quick_install.sh
chmod +x upload_to_github.sh

# Verificar se git está configurado
if ! command -v git &> /dev/null; then
    echo "⚠️  Git não está instalado. Instalando..."
    sudo apt update
    sudo apt install -y git
fi

# Mostrar resumo dos arquivos
echo ""
echo "✅ Arquivos preparados para upload:"
echo "├── Aplicação Principal:"
echo "│   ├── app.py"
echo "│   ├── main.py"
echo "│   ├── models.py"
echo "│   ├── routes.py"
echo "│   ├── forms.py"
echo "│   ├── utils.py"
echo "│   └── omada_api.py"
echo "├── Templates e Estáticos:"
echo "│   ├── templates/"
echo "│   └── static/"
echo "├── Instalação:"
echo "│   ├── github_install.sh"
echo "│   ├── quick_install.sh"
echo "│   └── app_requirements.txt"
echo "├── Documentação:"
echo "│   ├── README.md"
echo "│   └── GITHUB_INSTALL.md"
echo "└── Configuração:"
echo "    └── .gitignore"
echo ""

# Contar arquivos totais
total_files=$(find . -type f -not -path "./.git/*" | wc -l)
echo "📊 Total de arquivos: $total_files"

echo ""
echo "🚀 Pronto para upload!"
echo ""
echo "Execute um dos comandos abaixo para fazer upload:"
echo ""
echo "Opção 1 (automático):"
echo "  ./upload_to_github.sh"
echo ""
echo "Opção 2 (manual):"
echo "  git init"
echo "  git add ."
echo "  git commit -m 'Initial commit'"
echo "  git remote add origin https://github.com/Joelferreira98/OmadaVoucherController.git"
echo "  git push -u origin main"
echo ""
echo "Depois do upload, a instalação funcionará com:"
echo "  curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/quick_install.sh | sudo bash"