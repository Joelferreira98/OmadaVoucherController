#!/bin/bash

# Script de instalação via GitHub
# Execute este comando na sua VPS:
# curl -fsSL https://raw.githubusercontent.com/seu-usuario/voucher-system/main/github_install.sh | bash

set -e

# Configuração
REPO_URL="https://github.com/joel-0/voucher-system"
INSTALL_DIR="/tmp/voucher-system"
APP_NAME="voucher-system"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log colorido
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Função para ler entrada do usuário
read_input() {
    local prompt="$1"
    local default="$2"
    local value
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " value
        echo "${value:-$default}"
    else
        read -p "$prompt: " value
        echo "$value"
    fi
}

# Função para ler senha
read_password() {
    local prompt="$1"
    local password
    
    while true; do
        echo -n "$prompt: "
        read -s password
        echo
        if [ -n "$password" ]; then
            echo "$password"
            break
        else
            log_error "Senha não pode estar vazia!"
        fi
    done
}

# Verificar se é root
if [ "$EUID" -ne 0 ]; then
    log_error "Este script deve ser executado como root (use sudo)"
    exit 1
fi

# Banner
clear
echo ""
echo "========================================================="
echo "           🚀 INSTALAÇÃO VIA GITHUB - VOUCHER SYSTEM"
echo "========================================================="
echo ""
echo "Este script irá:"
echo "  • Baixar a aplicação do GitHub"
echo "  • Configurar o ambiente automaticamente"
echo "  • Instalar todas as dependências"
echo "  • Configurar nginx, supervisor e firewall"
echo "  • Deixar a aplicação pronta para usar"
echo ""
echo "========================================================="
echo ""

# Confirmar instalação
read -p "Deseja continuar com a instalação? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    log_info "Instalação cancelada."
    exit 0
fi

# Atualizar sistema
log_info "Atualizando sistema..."
apt update && apt upgrade -y

# Instalar dependências básicas
log_info "Instalando dependências básicas..."
apt install -y \
    curl \
    wget \
    git \
    unzip \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    supervisor \
    ufw \
    openssl \
    mysql-client \
    postgresql-client

# Criar usuário da aplicação
log_info "Criando usuário da aplicação..."
if ! id "voucher" &>/dev/null; then
    useradd -r -s /bin/false voucher
    log_success "Usuário 'voucher' criado"
else
    log_info "Usuário 'voucher' já existe"
fi

# Baixar aplicação do GitHub
log_info "Baixando aplicação do GitHub..."
rm -rf "$INSTALL_DIR"
git clone "$REPO_URL" "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Verificar se os arquivos foram baixados
if [ ! -f "app.py" ] || [ ! -f "main.py" ]; then
    log_error "Arquivos da aplicação não foram encontrados no repositório!"
    log_error "Verifique se o repositório está correto e contém os arquivos necessários."
    exit 1
fi

log_success "Aplicação baixada com sucesso!"

# Configurar banco de dados
echo ""
echo "=== CONFIGURAÇÃO DO BANCO DE DADOS ==="
echo "Escolha o tipo de banco de dados:"
echo "1) MySQL Local (será instalado e configurado automaticamente)"
echo "2) MySQL/MariaDB Remoto (você fornece as credenciais)"
echo "3) PostgreSQL Remoto (você fornece as credenciais)"
echo ""

while true; do
    read -p "Escolha uma opção [1-3]: " DB_CHOICE
    case $DB_CHOICE in
        1|2|3)
            break
            ;;
        *)
            log_error "Opção inválida! Escolha 1, 2 ou 3."
            ;;
    esac
done

# Configurar banco baseado na escolha
if [ "$DB_CHOICE" = "1" ]; then
    # MySQL Local
    log_info "Instalando MySQL local..."
    apt install -y mysql-server
    systemctl start mysql
    systemctl enable mysql
    
    log_info "Configurando MySQL local..."
    DB_HOST="localhost"
    DB_PORT="3306"
    DB_ROOT_PASSWORD=$(read_password "Digite a senha para o usuário root do MySQL")
    DB_NAME=$(read_input "Nome do banco de dados" "voucher_db")
    DB_USER=$(read_input "Usuário do banco de dados" "voucher")
    DB_PASSWORD=$(read_password "Senha do usuário do banco de dados")
    
    # Configurar MySQL
    mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '$DB_ROOT_PASSWORD';"
    mysql -u root -p$DB_ROOT_PASSWORD -e "FLUSH PRIVILEGES;"
    mysql -u root -p$DB_ROOT_PASSWORD -e "CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    mysql -u root -p$DB_ROOT_PASSWORD -e "CREATE USER '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD';"
    mysql -u root -p$DB_ROOT_PASSWORD -e "GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';"
    mysql -u root -p$DB_ROOT_PASSWORD -e "FLUSH PRIVILEGES;"
    
    DATABASE_URL="mysql+pymysql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
    
elif [ "$DB_CHOICE" = "2" ]; then
    # MySQL Remoto
    log_info "Configurando MySQL/MariaDB remoto..."
    DB_HOST=$(read_input "Host do banco de dados" "")
    DB_PORT=$(read_input "Porta do banco de dados" "3306")
    DB_NAME=$(read_input "Nome do banco de dados" "voucher_db")
    DB_USER=$(read_input "Usuário do banco de dados" "")
    DB_PASSWORD=$(read_password "Senha do banco de dados")
    
    if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
        log_error "Host, usuário e senha são obrigatórios!"
        exit 1
    fi
    
    DATABASE_URL="mysql+pymysql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
    
elif [ "$DB_CHOICE" = "3" ]; then
    # PostgreSQL Remoto
    log_info "Configurando PostgreSQL remoto..."
    DB_HOST=$(read_input "Host do banco de dados" "")
    DB_PORT=$(read_input "Porta do banco de dados" "5432")
    DB_NAME=$(read_input "Nome do banco de dados" "voucher_db")
    DB_USER=$(read_input "Usuário do banco de dados" "")
    DB_PASSWORD=$(read_password "Senha do banco de dados")
    
    if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
        log_error "Host, usuário e senha são obrigatórios!"
        exit 1
    fi
    
    DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
fi

# Configurações da aplicação
echo ""
echo "=== CONFIGURAÇÃO DA APLICAÇÃO ==="
SESSION_SECRET=$(read_input "Chave secreta da aplicação (deixe vazio para gerar automaticamente)" "")
if [ -z "$SESSION_SECRET" ]; then
    SESSION_SECRET=$(openssl rand -hex 32)
    log_success "Chave secreta gerada automaticamente"
fi

echo ""
echo "=== CONFIGURAÇÃO DO OMADA CONTROLLER ==="
OMADA_URL=$(read_input "URL do Omada Controller" "https://controller.local:8043")
OMADA_CLIENT_ID=$(read_input "Client ID do Omada" "")
OMADA_CLIENT_SECRET=$(read_input "Client Secret do Omada" "")
OMADA_OMADAC_ID=$(read_input "Omadac ID" "")

echo ""
echo "=== CONFIGURAÇÃO DO DOMÍNIO ==="
DOMAIN_NAME=$(read_input "Nome do domínio (deixe vazio para usar IP)" "")

# Instalar aplicação
log_info "Instalando aplicação..."
mkdir -p /opt/voucher-app
cp -r "$INSTALL_DIR"/* /opt/voucher-app/
chown -R voucher:voucher /opt/voucher-app/
cd /opt/voucher-app

# Criar ambiente virtual
log_info "Criando ambiente virtual..."
sudo -u voucher python3 -m venv venv
sudo -u voucher ./venv/bin/pip install --upgrade pip

# Instalar dependências
log_info "Instalando dependências Python..."
sudo -u voucher ./venv/bin/pip install Flask==3.0.0
sudo -u voucher ./venv/bin/pip install Flask-SQLAlchemy==3.1.1
sudo -u voucher ./venv/bin/pip install Flask-Login==0.6.3
sudo -u voucher ./venv/bin/pip install Flask-WTF==1.2.1
sudo -u voucher ./venv/bin/pip install WTForms==3.1.0
sudo -u voucher ./venv/bin/pip install email-validator==2.1.0
sudo -u voucher ./venv/bin/pip install Werkzeug==3.0.1
sudo -u voucher ./venv/bin/pip install gunicorn==21.2.0
sudo -u voucher ./venv/bin/pip install SQLAlchemy==2.0.23
sudo -u voucher ./venv/bin/pip install reportlab==4.0.7
sudo -u voucher ./venv/bin/pip install requests==2.31.0
sudo -u voucher ./venv/bin/pip install PyJWT==2.8.0
sudo -u voucher ./venv/bin/pip install oauthlib==3.2.2

# Instalar driver específico do banco
if [ "$DB_CHOICE" = "1" ] || [ "$DB_CHOICE" = "2" ]; then
    log_info "Instalando driver MySQL..."
    sudo -u voucher ./venv/bin/pip install PyMySQL==1.1.0
elif [ "$DB_CHOICE" = "3" ]; then
    log_info "Instalando driver PostgreSQL..."
    sudo -u voucher ./venv/bin/pip install psycopg2-binary==2.9.7
fi

# Criar arquivo de configuração
log_info "Criando arquivo de configuração..."
sudo -u voucher cat > /opt/voucher-app/.env << EOF
# Configurações da aplicação
SESSION_SECRET=$SESSION_SECRET
DATABASE_URL=$DATABASE_URL

# Configurações do Omada Controller
OMADA_CONTROLLER_URL=$OMADA_URL
OMADA_CLIENT_ID=$OMADA_CLIENT_ID
OMADA_CLIENT_SECRET=$OMADA_CLIENT_SECRET
OMADA_OMADAC_ID=$OMADA_OMADAC_ID
EOF

# Configurar Gunicorn
log_info "Configurando Gunicorn..."
sudo -u voucher cat > /opt/voucher-app/gunicorn.conf.py << 'EOF'
import multiprocessing

bind = "127.0.0.1:5000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 30
keepalive = 2
max_requests = 1000
preload_app = True
reload = False

# Logging
accesslog = "/var/log/voucher-app/access.log"
errorlog = "/var/log/voucher-app/error.log"
loglevel = "info"
EOF

# Criar diretório de logs
mkdir -p /var/log/voucher-app
chown voucher:voucher /var/log/voucher-app

# Configurar Supervisor
log_info "Configurando Supervisor..."
cat > /etc/supervisor/conf.d/voucher-app.conf << 'EOF'
[program:voucher-app]
command=/opt/voucher-app/venv/bin/gunicorn --config /opt/voucher-app/gunicorn.conf.py main:app
directory=/opt/voucher-app
user=voucher
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/voucher-app/supervisor.log
environment=PATH="/opt/voucher-app/venv/bin"
EOF

# Configurar Nginx
log_info "Configurando Nginx..."
if [ -n "$DOMAIN_NAME" ]; then
    SERVER_NAME="$DOMAIN_NAME www.$DOMAIN_NAME"
else
    SERVER_NAME="_"
fi

cat > /etc/nginx/sites-available/voucher-app << EOF
server {
    listen 80;
    server_name $SERVER_NAME;
    
    client_max_body_size 50M;
    
    location /static/ {
        alias /opt/voucher-app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
    }
}
EOF

# Ativar site no Nginx
ln -s /etc/nginx/sites-available/voucher-app /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Configurar firewall
log_info "Configurando firewall..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# Reiniciar serviços
log_info "Reiniciando serviços..."
systemctl restart nginx
systemctl enable nginx
systemctl restart supervisor
systemctl enable supervisor

# Inicializar aplicação
log_info "Inicializando aplicação..."
supervisorctl reread
supervisorctl update
supervisorctl start voucher-app

# Verificar status
sleep 3
if supervisorctl status voucher-app | grep -q "RUNNING"; then
    log_success "Aplicação iniciada com sucesso!"
else
    log_error "Erro ao iniciar aplicação!"
    supervisorctl status voucher-app
fi

# Configurar SSL se necessário
if [ -n "$DOMAIN_NAME" ]; then
    echo ""
    log_info "Configuração SSL disponível"
    read -p "Deseja instalar certificado SSL com Let's Encrypt? (y/n): " INSTALL_SSL
    
    if [ "$INSTALL_SSL" = "y" ] || [ "$INSTALL_SSL" = "Y" ]; then
        log_info "Instalando Certbot..."
        apt install -y certbot python3-certbot-nginx
        
        log_info "Obtendo certificado SSL..."
        certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME
        
        log_success "SSL configurado com sucesso!"
    fi
fi

# Limpar arquivos temporários
log_info "Limpando arquivos temporários..."
rm -rf "$INSTALL_DIR"

# Resultado final
echo ""
echo "========================================================="
echo "            🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO!"
echo "========================================================="
echo ""
echo "📋 RESUMO:"
if [ "$DB_CHOICE" = "1" ]; then
    echo "  • Banco: MySQL Local ($DB_NAME)"
elif [ "$DB_CHOICE" = "2" ]; then
    echo "  • Banco: MySQL Remoto ($DB_HOST:$DB_PORT/$DB_NAME)"
elif [ "$DB_CHOICE" = "3" ]; then
    echo "  • Banco: PostgreSQL Remoto ($DB_HOST:$DB_PORT/$DB_NAME)"
fi

if [ -n "$DOMAIN_NAME" ]; then
    echo "  • Acesso: http://$DOMAIN_NAME"
else
    echo "  • Acesso: http://$(curl -s ifconfig.me || hostname -I | awk '{print $1}')"
fi

echo ""
echo "🔐 CREDENCIAIS PADRÃO:"
echo "  • Usuário: master"
echo "  • Senha: admin123"
echo ""
echo "⚙️  COMANDOS ÚTEIS:"
echo "  • Status: sudo supervisorctl status voucher-app"
echo "  • Logs: sudo tail -f /var/log/voucher-app/supervisor.log"
echo "  • Reiniciar: sudo supervisorctl restart voucher-app"
echo ""
echo "A aplicação está pronta para uso!"