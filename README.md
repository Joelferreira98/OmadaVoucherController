# 🎯 Omada Voucher Controller

Sistema completo de gerenciamento de vouchers para hotspot WiFi com integração ao TP-Link Omada Controller.

## ✨ Características

- **Sistema Hierárquico**: Master, Admins e Vendedores
- **Integração Omada**: Conexão direta com TP-Link Omada Controller
- **Gerenciamento Completo**: Criação, venda e relatórios de vouchers
- **PDF Automático**: Geração de vouchers em formato A4 e 50x80mm
- **Sistema de Caixa**: Controle financeiro com fechamento de caixa
- **Relatórios Avançados**: Vendas por voucher individual
- **Tema Duplo**: Modo claro e escuro com otimização mobile
- **Multi-Banco**: Suporte MySQL e PostgreSQL

## 🚀 Instalação Rápida

### Método 1: Uma Linha (Recomendado)

```bash
curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/quick_install.sh | sudo bash
```

### Método 2: Manual

```bash
# Baixar o script
curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/github_install.sh -o install.sh

# Executar
chmod +x install.sh
sudo ./install.sh
```

## 📋 Requisitos

- **Sistema**: Ubuntu 18.04+ ou Debian 9+
- **Banco de Dados**: MySQL 5.7+ ou PostgreSQL 10+
- **Omada Controller**: TP-Link Omada Controller v5.0+
- **Porta**: 80 (HTTP) e 443 (HTTPS opcional)

## 🔧 Configuração

Durante a instalação você configurará:

### Banco de Dados
- MySQL Local (instalado automaticamente)
- MySQL Remoto (suas credenciais)
- PostgreSQL Remoto (suas credenciais)

### Omada Controller
- URL do Controller
- Client ID
- Client Secret
- Omadac ID

## 🎭 Tipos de Usuário

### Master
- Cria administradores
- Gerencia sites
- Configurações globais

### Admin
- Gerencia vendedores
- Cria planos de voucher
- Relatórios de vendas
- Fechamento de caixa
- Pode fazer tudo que o vendedor faz

### Vendedor
- Gera vouchers
- Imprime PDFs
- Visualiza relatórios de vendas

## 📊 Funcionalidades

### Gerenciamento de Vouchers
- ✅ Criação de planos personalizados
- ✅ Geração em lote
- ✅ Códigos numéricos únicos
- ✅ Status em tempo real
- ✅ Sincronização com Omada

### Relatórios
- ✅ Vendas por voucher individual
- ✅ Receita baseada em uso real
- ✅ Estatísticas detalhadas
- ✅ Exportação CSV

### Sistema de Caixa
- ✅ Fechamento automático
- ✅ Remoção de vouchers expirados
- ✅ Histórico completo
- ✅ Auditoria financeira

### PDFs
- ✅ Formato A4 (32 vouchers/página)
- ✅ Formato 50x80mm (impressora térmica)
- ✅ Códigos reais do Omada
- ✅ Design profissional

## 🔐 Credenciais Padrão

- **Usuário**: master
- **Senha**: admin123

## 🛠️ Comandos Úteis

```bash
# Status da aplicação
sudo supervisorctl status voucher-app

# Ver logs
sudo tail -f /var/log/voucher-app/supervisor.log

# Reiniciar
sudo supervisorctl restart voucher-app

# Status nginx
sudo systemctl status nginx
```

## 📁 Estrutura de Arquivos

```
/opt/voucher-app/           # Aplicação principal
├── app.py                  # Configuração Flask
├── models.py               # Modelos de banco
├── routes.py               # Rotas da aplicação
├── omada_api.py           # Integração Omada
├── utils.py               # Funções auxiliares
├── forms.py               # Formulários WTF
├── templates/             # Templates HTML
├── static/                # CSS, JS, imagens
└── .env                   # Configurações

/var/log/voucher-app/      # Logs
├── supervisor.log         # Log principal
├── access.log            # Log de acesso
└── error.log             # Log de erros
```

## 🔧 Configuração Avançada

### SSL com Let's Encrypt
```bash
sudo certbot --nginx -d seudominio.com
```

### Backup do Banco
```bash
# MySQL
mysqldump -h HOST -u USER -p DATABASE > backup.sql

# PostgreSQL
pg_dump -h HOST -U USER DATABASE > backup.sql
```

### Atualização
```bash
# Parar aplicação
sudo supervisorctl stop voucher-app

# Baixar nova versão
cd /tmp
git clone https://github.com/Joelferreira98/OmadaVoucherController update
sudo cp -r update/* /opt/voucher-app/
sudo chown -R voucher:voucher /opt/voucher-app/

# Reiniciar
sudo supervisorctl start voucher-app
```

## 🔍 Resolução de Problemas

### Aplicação não inicia
```bash
# Verificar logs
sudo tail -50 /var/log/voucher-app/supervisor.log

# Testar conexão com banco
cd /opt/voucher-app
sudo -u voucher ./venv/bin/python -c "from app import db; print('DB OK')"
```

### Erro de conexão Omada
- Verifique URL do Controller
- Confirme credenciais OAuth
- Teste conexão de rede

### Problemas de permissão
```bash
# Corrigir permissões
sudo chown -R voucher:voucher /opt/voucher-app/
sudo chmod -R 755 /opt/voucher-app/
```

## 🎨 Personalização

### Tema
- Modo claro/escuro automático
- Personalizável via CSS
- Otimizado para mobile

### Logos
- Substitua arquivos em `static/images/`
- Formatos: PNG, SVG, JPG

### Cores
- Edite `static/css/themes.css`
- Variáveis CSS personalizáveis

## 📱 Compatibilidade

- ✅ Desktop (Chrome, Firefox, Safari, Edge)
- ✅ Mobile (iOS Safari, Chrome Mobile)
- ✅ Tablet (iPad, Android)
- ✅ Impressoras térmicas (58mm, 80mm)

## 🔒 Segurança

- Hash de senhas com Werkzeug
- Sessões seguras
- Firewall automático
- Usuário dedicado sem shell
- Proxy reverso nginx
- HTTPS opcional

## 🤝 Suporte

Para suporte:
1. Verifique logs da aplicação
2. Teste conexão com banco
3. Verifique credenciais Omada
4. Confirme portas abertas

## 📄 Licença

Este projeto é de código aberto. Use livremente para fins comerciais e pessoais.

## 🚀 Versão

- **Versão Atual**: 2.0
- **Data**: Julho 2025
- **Compatibilidade**: Omada Controller v5.0+

---

**Desenvolvido para máxima eficiência e facilidade de uso!** 🎯