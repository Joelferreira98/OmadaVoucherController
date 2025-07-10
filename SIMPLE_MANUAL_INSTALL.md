# Instalação Manual Simplificada - Omada Voucher Controller

## 🚀 Instalação em 5 Passos

### 1. Preparar Sistema
```bash
# Instalar dependências
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git nginx supervisor mysql-client

# Criar usuário (opcional)
sudo useradd -m -s /bin/bash voucher
```

### 2. Clonar Repositório
```bash
# Clonar código
git clone https://github.com/Joelferreira98/OmadaVoucherController.git
cd OmadaVoucherController

# Copiar para diretório final
sudo mkdir -p /opt/voucher-app
sudo cp -r * /opt/voucher-app/
sudo chown -R voucher:voucher /opt/voucher-app
```

### 3. Configurar Python
```bash
# Criar ambiente virtual
cd /opt/voucher-app
sudo -u voucher python3 -m venv venv
sudo -u voucher ./venv/bin/pip install --upgrade pip

# Instalar dependências
sudo -u voucher ./venv/bin/pip install -r app_requirements.txt
```

### 4. Configurar Banco de Dados
```bash
# Testar conexão MySQL
mysql -h localhost -P 3306 -u JOEL -p -e "SELECT 1;" omada_voucher_system

# Criar arquivo .env
sudo -u voucher nano /opt/voucher-app/.env
```

**Conteúdo do arquivo .env:**
```env
# Para MySQL local
DATABASE_URL=mysql+pymysql://JOEL:SUA_SENHA@localhost:3306/omada_voucher_system

# Para MySQL remoto
DATABASE_URL=mysql+pymysql://JOEL:SUA_SENHA@194.163.133.179:3306/omada_voucher_system

# Gerar com: openssl rand -hex 32
SESSION_SECRET=f7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8

# Configurar depois na aplicação
OMADA_CONTROLLER_URL=https://controller.local:8043
OMADA_CLIENT_ID=
OMADA_CLIENT_SECRET=
OMADA_OMADAC_ID=
```

### 5. Testar Aplicação
```bash
# Testar funcionamento
cd /opt/voucher-app
sudo -u voucher ./venv/bin/python main.py

# Deverá mostrar: Running on http://0.0.0.0:5000
# Acesse http://SEU-IP:5000 para testar
# Ctrl+C para parar
```

## 🎯 Configuração de Produção (Opcional)

### Configurar Supervisor
```bash
# Criar configuração
sudo nano /etc/supervisor/conf.d/voucher-app.conf
```

**Conteúdo do arquivo supervisor:**
```ini
[program:voucher-app]
command=/opt/voucher-app/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 30 --keep-alive 2 --max-requests 1000 --preload main:app
directory=/opt/voucher-app
user=voucher
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/voucher-app.log
environment=DATABASE_URL="mysql+pymysql://JOEL:SUA_SENHA@localhost:3306/omada_voucher_system",SESSION_SECRET="f7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8",OMADA_CONTROLLER_URL="https://controller.local:8043",OMADA_CLIENT_ID="",OMADA_CLIENT_SECRET="",OMADA_OMADAC_ID=""
```

```bash
# Ativar supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start voucher-app
```

### Configurar Nginx
```bash
# Criar configuração
sudo nano /etc/nginx/sites-available/voucher-app
```

**Conteúdo do arquivo nginx:**
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

```bash
# Ativar nginx
sudo ln -s /etc/nginx/sites-available/voucher-app /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# Configurar firewall
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

## 🔧 Comandos Úteis

### Gerenciar Aplicação
```bash
# Logs
sudo tail -f /var/log/voucher-app.log

# Status
sudo supervisorctl status voucher-app

# Reiniciar
sudo supervisorctl restart voucher-app

# Parar/Iniciar
sudo supervisorctl stop voucher-app
sudo supervisorctl start voucher-app
```

### Testar Manualmente
```bash
# Rodar em modo desenvolvimento
cd /opt/voucher-app
sudo -u voucher ./venv/bin/python main.py

# Testar conexão banco
mysql -h localhost -P 3306 -u JOEL -p omada_voucher_system

# Gerar chave secreta
openssl rand -hex 32
```

## 🐛 Resolução de Problemas

### Erro de Conexão com Banco
```bash
# Verificar se MySQL está rodando
sudo systemctl status mysql

# Testar conexão
mysql -h localhost -P 3306 -u JOEL -p -e "SELECT 1;" omada_voucher_system

# Verificar arquivo .env
cat /opt/voucher-app/.env
```

### Erro de Importação Python
```bash
# Verificar se dependências estão instaladas
cd /opt/voucher-app
sudo -u voucher ./venv/bin/pip list

# Reinstalar dependências
sudo -u voucher ./venv/bin/pip install -r app_requirements.txt
```

### Erro de Permissão
```bash
# Corrigir permissões
sudo chown -R voucher:voucher /opt/voucher-app
sudo chmod +x /opt/voucher-app/main.py
```

## 🎉 Acesso à Aplicação

- **URL**: `http://SEU-IP` (com nginx) ou `http://SEU-IP:5000` (modo desenvolvimento)
- **Login**: master
- **Senha**: admin123

## 📋 Próximos Passos

1. Faça login na aplicação
2. Vá em **Master** → **Configurar Omada**
3. Configure as credenciais do Omada Controller
4. Sincronize os sites
5. Crie administradores e vendedores

## 💡 Dicas Importantes

- **Substitua** `SUA_SENHA` pela senha real do MySQL
- **Gere** uma nova chave secreta com `openssl rand -hex 32`
- **Teste** a conexão com o banco antes de continuar
- **Use** modo desenvolvimento para testar rapidamente
- **Configure** nginx e supervisor para produção

Esse guia simplificado cobre os passos essenciais para ter a aplicação funcionando rapidamente!