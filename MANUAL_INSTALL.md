# Instalação Manual - Omada Voucher Controller

## 📋 Pré-requisitos

Antes de começar, certifique-se de ter:
- Ubuntu 18.04+ ou Debian 9+
- Acesso root ao servidor
- Banco de dados MySQL configurado (local ou remoto)
- Porta 80 e 5000 disponíveis

## 🚀 Instalação Rápida (Recomendada)

### Opção 1: Clonar e configurar manualmente

```bash
# 1. Clonar repositório
git clone https://github.com/Joelferreira98/OmadaVoucherController.git
cd OmadaVoucherController

# 2. Copiar para diretório final
sudo mkdir -p /opt/voucher-app
sudo cp -r * /opt/voucher-app/
sudo chown -R $USER:$USER /opt/voucher-app

# 3. Configurar ambiente
cd /opt/voucher-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configurar .env (veja seção abaixo)
nano .env

# 5. Testar aplicação
python main.py
```

### Opção 2: Instalação em /opt como root

```bash
# 1. Preparar sistema
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git nginx supervisor mysql-client

# 2. Criar usuário do sistema
sudo useradd -m -s /bin/bash voucher

# 3. Clonar e instalar
cd /tmp
git clone https://github.com/Joelferreira98/OmadaVoucherController.git
sudo mkdir -p /opt/voucher-app
sudo cp -r OmadaVoucherController/* /opt/voucher-app/
sudo chown -R voucher:voucher /opt/voucher-app

# 4. Configurar Python
cd /opt/voucher-app
sudo -u voucher python3 -m venv venv
sudo -u voucher ./venv/bin/pip install --upgrade pip
sudo -u voucher ./venv/bin/pip install -r requirements.txt

# 5. Configurar .env
sudo -u voucher nano .env
```

## ⚙️ Configuração do Arquivo .env

Crie o arquivo `.env` na raiz do projeto (`/opt/voucher-app/.env` ou `./OmadaVoucherController/.env`):

### Exemplo de configuração para MySQL local:
```env
# Banco de dados MySQL local
DATABASE_URL=mysql+pymysql://JOEL:SUA_SENHA@localhost:3306/omada_voucher_system

# Chave de segurança (gere uma nova com: openssl rand -hex 32)
SESSION_SECRET=f7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8

# Omada Controller (configurar depois na aplicação)
OMADA_CONTROLLER_URL=https://controller.local:8043
OMADA_CLIENT_ID=
OMADA_CLIENT_SECRET=
OMADA_OMADAC_ID=
```

### Exemplo de configuração para MySQL remoto:
```env
# Banco de dados MySQL remoto
DATABASE_URL=mysql+pymysql://JOEL:SUA_SENHA@194.163.133.179:3306/omada_voucher_system

# Chave de segurança (gere uma nova com: openssl rand -hex 32)
SESSION_SECRET=f7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8

# Omada Controller (configurar depois na aplicação)
OMADA_CONTROLLER_URL=https://controller.local:8043
OMADA_CLIENT_ID=
OMADA_CLIENT_SECRET=
OMADA_OMADAC_ID=
```

### Como gerar uma chave secreta:
```bash
# Gerar chave aleatória
openssl rand -hex 32
# Exemplo de resultado: f7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8
```

### Parâmetros importantes:
- **DATABASE_URL**: Substitua `SUA_SENHA` pela senha real do MySQL
- **SESSION_SECRET**: Use uma chave única gerada com openssl
- **OMADA_CONTROLLER_URL**: Configure depois através da aplicação web
- **OMADA_CLIENT_ID/SECRET**: Deixe vazio, configure na aplicação

## 🧪 Teste de Conexão com Banco

Antes de continuar, teste a conexão com o banco:

```bash
# Para MySQL local
mysql -h localhost -P 3306 -u JOEL -p -e "SELECT 1;" omada_voucher_system

# Para MySQL remoto
mysql -h 194.163.133.179 -P 3306 -u JOEL -p -e "SELECT 1;" omada_voucher_system
```

## 📦 Instalação de Dependências Python

Crie um arquivo `requirements.txt` ou instale diretamente:

```bash
# Ativar ambiente virtual
cd /opt/voucher-app
source venv/bin/activate

# Instalar dependências
pip install Flask==3.0.0
pip install Flask-SQLAlchemy==3.1.1
pip install Flask-Login==0.6.3
pip install Flask-WTF==1.2.1
pip install WTForms==3.1.0
pip install email-validator==2.1.0
pip install Werkzeug==3.0.1
pip install gunicorn==21.2.0
pip install SQLAlchemy==2.0.23
pip install PyMySQL==1.1.0
pip install reportlab==4.0.7
pip install requests==2.31.0
pip install PyJWT==2.8.0
pip install oauthlib==3.2.2
```

## 🔧 Teste da Aplicação

Após configurar o `.env`, teste se a aplicação funciona:

```bash
cd /opt/voucher-app
python main.py
```

Se tudo estiver correto, você verá:
```
 * Running on http://0.0.0.0:5000
```

Acesse `http://SEU-IP:5000` para testar.

## 📋 Configuração de Produção

Para produção, configure Nginx e Supervisor:

## 🐍 Passo 3: Configurar Ambiente Python

### 3.1 Criar ambiente virtual
```bash
sudo -u voucher python3 -m venv /opt/voucher-app/venv
```

### 3.2 Ativar ambiente virtual
```bash
sudo -u voucher /opt/voucher-app/venv/bin/pip install --upgrade pip
```

### 3.3 Instalar dependências Python
```bash
cd /opt/voucher-app
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
```

## 🔧 Passo 4: Configurar Variáveis de Ambiente

### 4.1 Criar arquivo de configuração
```bash
sudo -u voucher nano /opt/voucher-app/.env
```

### 4.2 Adicionar configurações (edite conforme necessário)
```env
# Banco de dados
DATABASE_URL=mysql+pymysql://USUARIO:SENHA@HOST:PORTA/BANCO

# Segurança
SESSION_SECRET=sua-chave-secreta-aqui

# Omada Controller
OMADA_CONTROLLER_URL=https://seu-controller.local:8043
OMADA_CLIENT_ID=seu-client-id
OMADA_CLIENT_SECRET=seu-client-secret
OMADA_OMADAC_ID=seu-omadac-id
```

### 4.3 Gerar chave secreta
```bash
# Gerar chave aleatória
openssl rand -hex 32
# Cole o resultado no SESSION_SECRET
```

## 🧪 Passo 5: Testar Aplicação

### 5.1 Testar conexão com banco
```bash
mysql -h SEU_HOST -P PORTA -u USUARIO -p -e "SELECT 1;" BANCO
```

### 5.2 Testar importação da aplicação
```bash
cd /opt/voucher-app
sudo -u voucher ./venv/bin/python -c "
import os
os.environ['DATABASE_URL'] = 'mysql+pymysql://USUARIO:SENHA@HOST:PORTA/BANCO'
os.environ['SESSION_SECRET'] = 'sua-chave-secreta'
os.environ['OMADA_CONTROLLER_URL'] = 'https://controller.local:8043'
os.environ['OMADA_CLIENT_ID'] = ''
os.environ['OMADA_CLIENT_SECRET'] = ''
os.environ['OMADA_OMADAC_ID'] = ''
from app import app, db
with app.app_context():
    db.create_all()
print('✅ Aplicação funcionando!')
"
```

### 5.3 Testar servidor de desenvolvimento
```bash
cd /opt/voucher-app
sudo -u voucher ./venv/bin/python main.py
# Ctrl+C para parar
```

## 📋 Passo 6: Configurar Supervisor

### 6.1 Criar configuração do supervisor
```bash
sudo nano /etc/supervisor/conf.d/voucher-app.conf
```

### 6.2 Adicionar configuração
```ini
[program:voucher-app]
command=/opt/voucher-app/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 30 --keep-alive 2 --max-requests 1000 --preload main:app
directory=/opt/voucher-app
user=voucher
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/voucher-app.log
environment=DATABASE_URL="mysql+pymysql://USUARIO:SENHA@HOST:PORTA/BANCO",SESSION_SECRET="sua-chave-secreta",OMADA_CONTROLLER_URL="https://controller.local:8043",OMADA_CLIENT_ID="",OMADA_CLIENT_SECRET="",OMADA_OMADAC_ID=""
```

### 6.3 Ativar configuração
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start voucher-app
```

### 6.4 Verificar status
```bash
sudo supervisorctl status voucher-app
```

## 🌐 Passo 7: Configurar Nginx

### 7.1 Criar configuração do nginx
```bash
sudo nano /etc/nginx/sites-available/voucher-app
```

### 7.2 Adicionar configuração
```nginx
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
```

### 7.3 Ativar site
```bash
sudo ln -s /etc/nginx/sites-available/voucher-app /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
```

### 7.4 Testar configuração
```bash
sudo nginx -t
sudo systemctl restart nginx
```

## 🔒 Passo 8: Configurar Firewall

### 8.1 Configurar UFW
```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

### 8.2 Verificar status
```bash
sudo ufw status
```

## 🚀 Passo 9: Finalizar Instalação

### 9.1 Verificar se tudo está funcionando
```bash
# Status dos serviços
sudo systemctl status nginx
sudo systemctl status supervisor
sudo supervisorctl status voucher-app

# Testar resposta HTTP
curl -I http://localhost:5000
```

### 9.2 Verificar logs
```bash
sudo tail -f /var/log/voucher-app.log
```

### 9.3 Acessar aplicação
```bash
# Descobrir IP do servidor
curl -s ifconfig.me
```

Acesse: `http://SEU-IP-DO-SERVIDOR`

## 📋 Passo 10: Credenciais Padrão

- **Usuário:** master
- **Senha:** admin123

## 🔧 Comandos Úteis

### Gerenciar aplicação
```bash
# Status
sudo supervisorctl status voucher-app

# Reiniciar
sudo supervisorctl restart voucher-app

# Parar
sudo supervisorctl stop voucher-app

# Iniciar
sudo supervisorctl start voucher-app

# Logs
sudo tail -f /var/log/voucher-app.log
```

### Gerenciar serviços
```bash
# Nginx
sudo systemctl restart nginx
sudo systemctl status nginx

# Supervisor
sudo systemctl restart supervisor
sudo systemctl status supervisor
```

## 🐛 Resolução de Problemas

### Erro: Aplicação não inicia
```bash
# Verificar logs
sudo tail -20 /var/log/voucher-app.log

# Testar manualmente
cd /opt/voucher-app
sudo -u voucher ./venv/bin/python main.py
```

### Erro: Banco de dados
```bash
# Testar conexão
mysql -h HOST -P PORTA -u USUARIO -p BANCO

# Verificar variáveis
sudo -u voucher cat /opt/voucher-app/.env
```

### Erro: Nginx
```bash
# Testar configuração
sudo nginx -t

# Verificar logs
sudo tail -f /var/log/nginx/error.log
```

### Erro: Permissões
```bash
# Corrigir permissões
sudo chown -R voucher:voucher /opt/voucher-app
sudo chmod +x /opt/voucher-app/main.py
```

## 🎉 Pronto!

Sua instalação manual está completa. A aplicação deve estar rodando em:
- `http://SEU-IP-DO-SERVIDOR`

Configure o Omada Controller através do menu Master → Configurar Omada.