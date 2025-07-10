#!/bin/bash

# Script de instalação para VPS com MySQL local
# Execute na mesma VPS onde está o banco de dados

set -e

echo "🚀 Instalação VPS - Omada Voucher Controller"
echo "==========================================="
echo ""
echo "Este script instalará a aplicação na mesma VPS onde está o MySQL"
echo ""

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo "❌ Execute como root: sudo bash install_vps.sh"
    exit 1
fi

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

echo "📋 ETAPA 1: Configuração do Banco de Dados"
echo "========================================="
echo ""
echo "Como você está instalando na mesma VPS do MySQL,"
echo "vamos usar 'localhost' como host do banco."
echo ""

# Configurações do banco
DB_HOST="localhost"
DB_PORT="3306"
DB_NAME=$(read_input "Nome do banco de dados" "omada_voucher_system")
DB_USER=$(read_input "Usuário do MySQL" "JOEL")
DB_PASSWORD=$(read_password "Senha do MySQL")

# Testar conexão local
echo ""
echo "🔍 Testando conexão local com MySQL..."

if mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1;" "$DB_NAME" 2>/dev/null; then
    echo "✅ Conexão MySQL local OK"
else
    echo "❌ Erro na conexão MySQL local"
    echo ""
    echo "Vamos tentar criar o banco de dados..."
    
    # Tentar conectar sem especificar banco
    if mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS $DB_NAME;" 2>/dev/null; then
        echo "✅ Banco de dados '$DB_NAME' criado/verificado"
    else
        echo "❌ Não foi possível criar o banco de dados"
        echo "Verifique as credenciais e tente novamente"
        exit 1
    fi
fi

DATABASE_URL="mysql+pymysql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"

echo ""
echo "📦 ETAPA 2: Instalação de Dependências"
echo "====================================="

# Atualizar sistema
echo "🔄 Atualizando sistema..."
apt update -y >/dev/null 2>&1
apt upgrade -y >/dev/null 2>&1

# Instalar dependências
echo "📦 Instalando dependências..."
apt install -y python3 python3-pip python3-venv git curl wget >/dev/null 2>&1
apt install -y nginx supervisor >/dev/null 2>&1
apt install -y build-essential python3-dev >/dev/null 2>&1

echo "✅ Dependências instaladas"

echo ""
echo "👤 ETAPA 3: Configuração do Usuário"
echo "=================================="

# Criar usuário
if ! id "voucher" &>/dev/null; then
    useradd -m -s /bin/bash voucher
    echo "✅ Usuário 'voucher' criado"
else
    echo "ℹ️  Usuário 'voucher' já existe"
fi

echo ""
echo "📥 ETAPA 4: Download da Aplicação"
echo "==============================="

# Baixar código
cd /tmp
rm -rf OmadaVoucherController
git clone https://github.com/Joelferreira98/OmadaVoucherController.git
echo "✅ Código baixado"

# Instalar arquivos
mkdir -p /opt/voucher-app
cp -r /tmp/OmadaVoucherController/* /opt/voucher-app/
chown -R voucher:voucher /opt/voucher-app
echo "✅ Arquivos instalados"

echo ""
echo "🐍 ETAPA 5: Configuração Python"
echo "============================="

# Criar ambiente virtual
cd /opt/voucher-app
sudo -u voucher python3 -m venv venv
sudo -u voucher ./venv/bin/pip install --upgrade pip >/dev/null 2>&1
echo "✅ Ambiente virtual criado"

# Instalar dependências Python
echo "📚 Instalando dependências Python..."
sudo -u voucher ./venv/bin/pip install Flask==3.0.0 >/dev/null 2>&1
sudo -u voucher ./venv/bin/pip install Flask-SQLAlchemy==3.1.1 >/dev/null 2>&1
sudo -u voucher ./venv/bin/pip install Flask-Login==0.6.3 >/dev/null 2>&1
sudo -u voucher ./venv/bin/pip install Flask-WTF==1.2.1 >/dev/null 2>&1
sudo -u voucher ./venv/bin/pip install WTForms==3.1.0 >/dev/null 2>&1
sudo -u voucher ./venv/bin/pip install email-validator==2.1.0 >/dev/null 2>&1
sudo -u voucher ./venv/bin/pip install Werkzeug==3.0.1 >/dev/null 2>&1
sudo -u voucher ./venv/bin/pip install gunicorn==21.2.0 >/dev/null 2>&1
sudo -u voucher ./venv/bin/pip install SQLAlchemy==2.0.23 >/dev/null 2>&1
sudo -u voucher ./venv/bin/pip install PyMySQL==1.1.0 >/dev/null 2>&1
sudo -u voucher ./venv/bin/pip install reportlab==4.0.7 >/dev/null 2>&1
sudo -u voucher ./venv/bin/pip install requests==2.31.0 >/dev/null 2>&1
sudo -u voucher ./venv/bin/pip install PyJWT==2.8.0 >/dev/null 2>&1
sudo -u voucher ./venv/bin/pip install oauthlib==3.2.2 >/dev/null 2>&1
echo "✅ Dependências Python instaladas"

echo ""
echo "⚙️ ETAPA 6: Configuração da Aplicação"
echo "=================================="

# Gerar chave secreta
SESSION_SECRET=$(openssl rand -hex 32)
echo "✅ Chave secreta gerada"

# Configurar Omada (opcional)
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
echo "✅ Configuração criada"

echo ""
echo "🧪 ETAPA 7: Teste da Aplicação"
echo "============================"

# Testar aplicação
echo "🔍 Testando aplicação..."
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
" 2>/dev/null; then
    echo "✅ Teste da aplicação bem-sucedido"
else
    echo "❌ Erro no teste da aplicação"
    echo "Verificando logs..."
    sudo -u voucher ./venv/bin/python -c "
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
print('Aplicação funcionando!')
" 2>&1 | head -10
    exit 1
fi

echo ""
echo "📋 ETAPA 8: Configuração do Supervisor"
echo "===================================="

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

supervisorctl reread >/dev/null 2>&1
supervisorctl update >/dev/null 2>&1
supervisorctl start voucher-app >/dev/null 2>&1
echo "✅ Supervisor configurado"

echo ""
echo "🌐 ETAPA 9: Configuração do Nginx"
echo "==============================="

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

# Testar e reiniciar nginx
if nginx -t >/dev/null 2>&1; then
    systemctl restart nginx
    echo "✅ Nginx configurado"
else
    echo "❌ Erro na configuração do Nginx"
    exit 1
fi

echo ""
echo "🔒 ETAPA 10: Configuração do Firewall"
echo "==================================="

# Configurar firewall
ufw allow OpenSSH >/dev/null 2>&1
ufw allow 'Nginx Full' >/dev/null 2>&1
ufw --force enable >/dev/null 2>&1
echo "✅ Firewall configurado"

echo ""
echo "🔍 ETAPA 11: Verificação Final"
echo "============================"

# Verificar serviços
echo "🔄 Aguardando serviços iniciarem..."
sleep 5

# Verificar aplicação
if supervisorctl status voucher-app | grep -q "RUNNING"; then
    echo "✅ Aplicação rodando"
else
    echo "❌ Aplicação não está rodando"
    supervisorctl status voucher-app
fi

# Verificar nginx
if systemctl is-active --quiet nginx; then
    echo "✅ Nginx rodando"
else
    echo "❌ Nginx não está rodando"
fi

# Testar resposta
if curl -s http://localhost:5000 >/dev/null 2>&1; then
    echo "✅ Aplicação respondendo"
else
    echo "❌ Aplicação não responde"
fi

echo ""
echo "========================================="
echo "🎉 INSTALAÇÃO CONCLUÍDA!"
echo "========================================="
echo ""
echo "📊 Informações da instalação:"
echo "   • Aplicação: http://$(curl -s ifconfig.me 2>/dev/null || echo 'SEU-IP')"
echo "   • Usuário: master"
echo "   • Senha: admin123"
echo "   • Banco: $DB_HOST:$DB_PORT/$DB_NAME"
echo "   • Logs: /var/log/voucher-app.log"
echo ""
echo "📋 Comandos úteis:"
echo "   • Status: sudo supervisorctl status voucher-app"
echo "   • Logs: sudo tail -f /var/log/voucher-app.log"
echo "   • Reiniciar: sudo supervisorctl restart voucher-app"
echo ""
echo "⚙️ Próximos passos:"
echo "   1. Acesse a aplicação no navegador"
echo "   2. Faça login com master/admin123"
echo "   3. Configure o Omada Controller"
echo "   4. Sincronize os sites"
echo "   5. Crie administradores e vendedores"
echo ""

# Limpar arquivos temporários
rm -rf /tmp/OmadaVoucherController

echo "✅ Instalação VPS concluída com sucesso!"