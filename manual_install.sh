#!/bin/bash

# Script de instalação manual interativa
# Execute este script para fazer instalação passo a passo com controle total

set -e

echo "🔧 Instalação Manual - Omada Voucher Controller"
echo "=============================================="
echo ""
echo "Este script guia você através de uma instalação manual completa"
echo "com controle total sobre cada etapa do processo."
echo ""

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo "❌ Execute como root: sudo bash manual_install.sh"
    exit 1
fi

# Função para pausar e aguardar confirmação
pause_and_confirm() {
    echo ""
    read -p "Pressione Enter para continuar ou Ctrl+C para cancelar..."
}

# Função para input
read_input() {
    local prompt="$1"
    local default="$2"
    local input
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
        echo "${input:-$default}"
    else
        read -p "$prompt: " input
        echo "$input"
    fi
}

# Função para senha
read_password() {
    local prompt="$1"
    local password
    
    read -s -p "$prompt: " password
    echo ""
    echo "$password"
}

echo "📋 ETAPA 1: Preparação do Sistema"
echo "================================"
echo ""
echo "Vamos começar preparando o sistema com as dependências necessárias:"
echo "- Python 3 e pip"
echo "- Nginx e Supervisor"
echo "- Git e ferramentas básicas"
echo "- Cliente MySQL"
pause_and_confirm

echo "📦 Atualizando sistema..."
apt update -y
apt upgrade -y

echo "📦 Instalando dependências básicas..."
apt install -y python3 python3-pip python3-venv git curl wget
apt install -y nginx supervisor mysql-client
apt install -y build-essential python3-dev

echo "✅ Dependências instaladas"

echo ""
echo "👤 ETAPA 2: Criação do Usuário"
echo "=============================="
echo ""
echo "Criando usuário 'voucher' para executar a aplicação:"
pause_and_confirm

if ! id "voucher" &>/dev/null; then
    useradd -m -s /bin/bash voucher
    echo "✅ Usuário 'voucher' criado"
else
    echo "ℹ️  Usuário 'voucher' já existe"
fi

echo ""
echo "📥 ETAPA 3: Download do Código"
echo "============================="
echo ""
echo "Baixando código fonte do GitHub:"
pause_and_confirm

cd /tmp
rm -rf OmadaVoucherController
git clone https://github.com/Joelferreira98/OmadaVoucherController.git
echo "✅ Código baixado"

echo ""
echo "📁 ETAPA 4: Instalação dos Arquivos"
echo "==================================="
echo ""
echo "Copiando arquivos para /opt/voucher-app:"
pause_and_confirm

mkdir -p /opt/voucher-app
cp -r /tmp/OmadaVoucherController/* /opt/voucher-app/
chown -R voucher:voucher /opt/voucher-app
echo "✅ Arquivos instalados"

echo ""
echo "🐍 ETAPA 5: Ambiente Python"
echo "=========================="
echo ""
echo "Configurando ambiente virtual Python:"
pause_and_confirm

cd /opt/voucher-app
sudo -u voucher python3 -m venv venv
sudo -u voucher ./venv/bin/pip install --upgrade pip
echo "✅ Ambiente virtual criado"

echo ""
echo "📚 Instalando dependências Python (isso pode demorar um pouco)..."
sudo -u voucher ./venv/bin/pip install Flask==3.0.0
sudo -u voucher ./venv/bin/pip install Flask-SQLAlchemy==3.1.1
sudo -u voucher ./venv/bin/pip install Flask-Login==0.6.3
sudo -u voucher ./venv/bin/pip install Flask-WTF==1.2.1
sudo -u voucher ./venv/bin/pip install WTForms==3.1.0
sudo -u voucher ./venv/bin/pip install email-validator==2.1.0
sudo -u voucher ./venv/bin/pip install Werkzeug==3.0.1
sudo -u voucher ./venv/bin/pip install gunicorn==21.2.0
sudo -u voucher ./venv/bin/pip install SQLAlchemy==2.0.23
sudo -u voucher ./venv/bin/pip install PyMySQL==1.1.0
sudo -u voucher ./venv/bin/pip install reportlab==4.0.7
sudo -u voucher ./venv/bin/pip install requests==2.31.0
sudo -u voucher ./venv/bin/pip install PyJWT==2.8.0
sudo -u voucher ./venv/bin/pip install oauthlib==3.2.2
echo "✅ Dependências Python instaladas"

echo ""
echo "🔧 ETAPA 6: Configuração do Banco de Dados"
echo "========================================="
echo ""
echo "Agora vamos configurar a conexão com o banco de dados MySQL:"
pause_and_confirm

# Configurar banco de dados
DB_HOST=$(read_input "Host do MySQL" "localhost")
DB_PORT=$(read_input "Porta do MySQL" "3306")
DB_NAME=$(read_input "Nome do banco de dados" "voucher_db")
DB_USER=$(read_input "Usuário do MySQL" "root")
DB_PASSWORD=$(read_password "Senha do MySQL")

# Testar conexão
echo ""
echo "🔍 Testando conexão com banco de dados..."
if mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1;" "$DB_NAME" > /dev/null 2>&1; then
    echo "✅ Conexão com banco de dados OK"
else
    echo "❌ Erro na conexão com banco de dados!"
    echo "Verifique as credenciais e tente novamente."
    exit 1
fi

DATABASE_URL="mysql+pymysql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"

echo ""
echo "⚙️ ETAPA 7: Configuração da Aplicação"
echo "==================================="
echo ""
echo "Configurando variáveis de ambiente:"
pause_and_confirm

# Gerar chave secreta
SESSION_SECRET=$(openssl rand -hex 32)
echo "✅ Chave secreta gerada"

# Configurar Omada Controller
echo ""
echo "📡 Configuração do Omada Controller (pode ser alterada depois):"
OMADA_URL=$(read_input "URL do Omada Controller" "https://controller.local:8043")
OMADA_CLIENT_ID=$(read_input "Client ID do Omada (opcional)" "")
OMADA_CLIENT_SECRET=$(read_input "Client Secret do Omada (opcional)" "")
OMADA_OMADAC_ID=$(read_input "Omadac ID (opcional)" "")

# Criar arquivo de configuração
cat > /opt/voucher-app/.env << EOF
DATABASE_URL=$DATABASE_URL
SESSION_SECRET=$SESSION_SECRET
OMADA_CONTROLLER_URL=$OMADA_URL
OMADA_CLIENT_ID=$OMADA_CLIENT_ID
OMADA_CLIENT_SECRET=$OMADA_CLIENT_SECRET
OMADA_OMADAC_ID=$OMADA_OMADAC_ID
EOF

chown voucher:voucher /opt/voucher-app/.env
echo "✅ Arquivo de configuração criado"

echo ""
echo "🧪 ETAPA 8: Teste da Aplicação"
echo "============================="
echo ""
echo "Testando se a aplicação funciona corretamente:"
pause_and_confirm

# Testar aplicação
cd /opt/voucher-app
if sudo -u voucher ./venv/bin/python -c "
import os
os.environ['DATABASE_URL'] = '$DATABASE_URL'
os.environ['SESSION_SECRET'] = '$SESSION_SECRET'
os.environ['OMADA_CONTROLLER_URL'] = '$OMADA_URL'
os.environ['OMADA_CLIENT_ID'] = '$OMADA_CLIENT_ID'
os.environ['OMADA_CLIENT_SECRET'] = '$OMADA_CLIENT_SECRET'
os.environ['OMADA_OMADAC_ID'] = '$OMADA_OMADAC_ID'
from app import app, db
with app.app_context():
    db.create_all()
print('✅ Aplicação funcionando!')
" > /dev/null 2>&1; then
    echo "✅ Aplicação testada com sucesso"
else
    echo "❌ Erro no teste da aplicação!"
    exit 1
fi

echo ""
echo "📋 ETAPA 9: Configuração do Supervisor"
echo "====================================="
echo ""
echo "Configurando Supervisor para gerenciar a aplicação:"
pause_and_confirm

# Configurar Supervisor
cat > /etc/supervisor/conf.d/voucher-app.conf << EOF
[program:voucher-app]
command=/opt/voucher-app/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 30 --keep-alive 2 --max-requests 1000 --preload main:app
directory=/opt/voucher-app
user=voucher
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/voucher-app.log
environment=DATABASE_URL="$DATABASE_URL",SESSION_SECRET="$SESSION_SECRET",OMADA_CONTROLLER_URL="$OMADA_URL",OMADA_CLIENT_ID="$OMADA_CLIENT_ID",OMADA_CLIENT_SECRET="$OMADA_CLIENT_SECRET",OMADA_OMADAC_ID="$OMADA_OMADAC_ID"
EOF

supervisorctl reread
supervisorctl update
supervisorctl start voucher-app
echo "✅ Supervisor configurado"

echo ""
echo "🌐 ETAPA 10: Configuração do Nginx"
echo "=================================="
echo ""
echo "Configurando Nginx como proxy reverso:"
pause_and_confirm

# Configurar Nginx
cat > /etc/nginx/sites-available/voucher-app << 'EOF'
server {
    listen 80;
    server_name _;
    
    client_max_body_size 50M;
    
    location /static/ {
        alias /opt/voucher-app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
EOF

ln -s /etc/nginx/sites-available/voucher-app /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Testar configuração
if nginx -t > /dev/null 2>&1; then
    systemctl restart nginx
    echo "✅ Nginx configurado"
else
    echo "❌ Erro na configuração do Nginx!"
    exit 1
fi

echo ""
echo "🔒 ETAPA 11: Configuração do Firewall"
echo "===================================="
echo ""
echo "Configurando firewall para permitir acesso web:"
pause_and_confirm

ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
echo "✅ Firewall configurado"

echo ""
echo "🎯 ETAPA 12: Verificação Final"
echo "============================="
echo ""
echo "Verificando se todos os serviços estão funcionando:"
pause_and_confirm

# Verificar serviços
echo "🔍 Verificando status dos serviços..."
sleep 5

# Status do supervisor
if supervisorctl status voucher-app | grep -q "RUNNING"; then
    echo "✅ Aplicação está rodando no Supervisor"
else
    echo "❌ Aplicação não está rodando no Supervisor"
    supervisorctl status voucher-app
fi

# Status do nginx
if systemctl is-active --quiet nginx; then
    echo "✅ Nginx está rodando"
else
    echo "❌ Nginx não está rodando"
fi

# Testar resposta HTTP
if curl -s http://localhost:5000 > /dev/null; then
    echo "✅ Aplicação responde na porta 5000"
else
    echo "❌ Aplicação não responde na porta 5000"
fi

echo ""
echo "========================================="
echo "🎉 INSTALAÇÃO MANUAL CONCLUÍDA!"
echo "========================================="
echo ""
echo "📊 Resumo da instalação:"
echo "   • Aplicação: /opt/voucher-app"
echo "   • Usuário: voucher"
echo "   • Banco: $DB_HOST:$DB_PORT/$DB_NAME"
echo "   • Logs: /var/log/voucher-app.log"
echo ""
echo "🌐 Acesso à aplicação:"
echo "   • URL: http://$(curl -s ifconfig.me 2>/dev/null || echo 'SEU-IP')"
echo "   • Usuário: master"
echo "   • Senha: admin123"
echo ""
echo "📋 Comandos úteis:"
echo "   • Status: sudo supervisorctl status voucher-app"
echo "   • Logs: sudo tail -f /var/log/voucher-app.log"
echo "   • Reiniciar: sudo supervisorctl restart voucher-app"
echo ""
echo "⚙️ Próximos passos:"
echo "   1. Acesse a aplicação no navegador"
echo "   2. Faça login com as credenciais padrão"
echo "   3. Configure o Omada Controller no menu Master"
echo "   4. Sincronize os sites do Omada Controller"
echo "   5. Crie administradores e vendedores"
echo ""
echo "📖 Para mais informações, consulte o arquivo MANUAL_INSTALL.md"
echo ""

# Limpar arquivos temporários
rm -rf /tmp/OmadaVoucherController