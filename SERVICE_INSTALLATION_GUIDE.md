# Guia de Instalação como Serviço

## Transformando a Aplicação em Serviço Systemd

### 🚀 Instalação Automática Completa

Execute o script principal para configurar tudo automaticamente:

```bash
# Baixar e executar configuração completa
sudo ./complete_service_setup.sh
```

### 📋 Instalação Manual Passo a Passo

#### 1. Criar Serviço Systemd

```bash
# Criar arquivo de serviço
sudo ./create_service.sh
```

#### 2. Configurar Nginx (Opcional)

```bash
# Configurar proxy reverso
sudo ./setup_nginx.sh
```

#### 3. Gerenciar Serviço

```bash
# Comandos básicos
sudo systemctl start voucher-app     # Iniciar
sudo systemctl stop voucher-app      # Parar
sudo systemctl restart voucher-app   # Reiniciar
sudo systemctl status voucher-app    # Ver status
sudo systemctl enable voucher-app    # Habilitar no boot
sudo systemctl disable voucher-app   # Desabilitar no boot
```

## 📊 Monitoramento e Logs

### Script de Gerenciamento

```bash
# Usar script de gerenciamento
sudo ./service_management.sh status    # Status dos serviços
sudo ./service_management.sh logs      # Ver logs
sudo ./service_management.sh restart   # Reiniciar serviços
sudo ./service_management.sh test      # Testar conectividade
sudo ./service_management.sh monitor   # Monitoramento em tempo real
sudo ./service_management.sh backup    # Backup configurações
```

### Logs Manuais

```bash
# Logs do serviço voucher-app
sudo journalctl -u voucher-app -f

# Logs do Nginx
sudo tail -f /var/log/nginx/voucher-app.access.log
sudo tail -f /var/log/nginx/voucher-app.error.log

# Logs do sistema
sudo journalctl -f
```

## 🔧 Configuração de Arquivos

### 1. Arquivo de Serviço Systemd
**Local:** `/etc/systemd/system/voucher-app.service`

```ini
[Unit]
Description=Voucher Management System
After=network.target mysql.service
Requires=mysql.service

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=/opt/voucher-app
Environment=PATH=/opt/voucher-app/venv/bin
EnvironmentFile=/opt/voucher-app/.env
ExecStart=/opt/voucher-app/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 30 --preload main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Configuração Nginx
**Local:** `/etc/nginx/sites-available/voucher-app`

```nginx
server {
    listen 80;
    server_name _;
    
    location /static/ {
        alias /opt/voucher-app/static/;
        expires 30d;
    }
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Arquivo de Ambiente
**Local:** `/opt/voucher-app/.env`

```env
# Database Configuration
DATABASE_URL=mysql+pymysql://JOEL:admin123@localhost:3306/omada_voucher_system

# Flask Security Configuration
SESSION_SECRET=f7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8

# Omada Controller Configuration
OMADA_CONTROLLER_URL=https://seu-controller.local:8043
OMADA_CLIENT_ID=seu-client-id
OMADA_CLIENT_SECRET=seu-client-secret
OMADA_OMADAC_ID=seu-omadac-id
```

## 🌐 Acesso à Aplicação

### Com Nginx (Recomendado)
- **URL:** `http://SEU-IP-SERVIDOR`
- **Porta:** 80 (padrão HTTP)

### Direto (Sem Nginx)
- **URL:** `http://SEU-IP-SERVIDOR:5000`
- **Porta:** 5000

### Login Padrão
- **Usuário:** `master`
- **Senha:** `admin123`

## 🔐 Segurança

### Firewall
```bash
# Configurar UFW
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
```

### SSL/HTTPS (Opcional)
```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Obter certificado SSL
sudo certbot --nginx -d seu-dominio.com
```

## 🛠️ Solução de Problemas

### Serviço não inicia
```bash
# Verificar logs
sudo journalctl -u voucher-app -n 50

# Verificar configuração
sudo systemctl status voucher-app

# Recarregar configuração
sudo systemctl daemon-reload
sudo systemctl restart voucher-app
```

### Nginx não responde
```bash
# Testar configuração
sudo nginx -t

# Reiniciar Nginx
sudo systemctl restart nginx

# Verificar logs
sudo tail -f /var/log/nginx/error.log
```

### Banco de dados
```bash
# Verificar MySQL
sudo systemctl status mysql

# Testar conexão
mysql -u JOEL -p -h localhost omada_voucher_system

# Reiniciar MySQL
sudo systemctl restart mysql
```

## 📈 Monitoramento Avançado

### Configurar Monitoramento
```bash
# Instalar htop para monitoramento
sudo apt install htop

# Monitorar recursos
htop

# Monitorar processos Python
ps aux | grep python

# Verificar portas
netstat -tlnp | grep :5000
```

### Alertas por Email (Opcional)
```bash
# Configurar alertas systemd
sudo systemctl edit voucher-app
```

## 📋 Checklist de Verificação

- [ ] Serviço voucher-app rodando
- [ ] Nginx configurado e rodando
- [ ] MySQL conectado
- [ ] Firewall configurado
- [ ] Arquivo .env com todas as variáveis
- [ ] Logs sendo gerados corretamente
- [ ] Aplicação acessível via navegador
- [ ] Login funcionando
- [ ] Backup das configurações criado

## 🔄 Atualizações

### Atualizar Aplicação
```bash
# Parar serviço
sudo systemctl stop voucher-app

# Atualizar código (se necessário)
cd /opt/voucher-app
git pull origin main

# Atualizar dependências
source venv/bin/activate
pip install -r requirements.txt

# Reiniciar serviço
sudo systemctl start voucher-app
```

### Backup Automático
```bash
# Criar script de backup automático
sudo ./service_management.sh backup

# Agendar backup diário (crontab)
sudo crontab -e
# Adicionar linha:
# 0 2 * * * /opt/voucher-app/service_management.sh backup
```

## 📞 Suporte

Se encontrar problemas:

1. Verifique os logs com `sudo ./service_management.sh logs`
2. Teste a conectividade com `sudo ./service_management.sh test`
3. Consulte a documentação completa
4. Verifique as configurações do Omada Controller
5. Confirme as credenciais do banco de dados

---

**Aplicação configurada como serviço com sucesso!**