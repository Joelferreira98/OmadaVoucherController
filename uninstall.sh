#!/bin/bash

# Script para remover completamente a instalação do Omada Voucher Controller
# Execute este script antes de fazer uma nova instalação

echo "🗑️  Removendo Omada Voucher Controller..."
echo "========================================"

# Verificar se é root
if [[ $EUID -ne 0 ]]; then
    echo "❌ Execute como root: sudo bash uninstall.sh"
    exit 1
fi

# Confirmar remoção
echo "⚠️  Este script irá remover COMPLETAMENTE a instalação do Omada Voucher Controller"
echo "   Isso inclui:"
echo "   - Aplicação (/opt/voucher-app)"
echo "   - Configurações do Nginx"
echo "   - Configurações do Supervisor"
echo "   - Logs da aplicação"
echo "   - Usuário do sistema"
echo ""
read -p "Tem certeza que deseja continuar? (digite 'SIM' para confirmar): " CONFIRM

if [ "$CONFIRM" != "SIM" ]; then
    echo "❌ Operação cancelada"
    exit 1
fi

echo "🔄 Iniciando remoção..."

# Parar e remover serviços
echo "⏹️  Parando serviços..."
supervisorctl stop voucher-app 2>/dev/null || true
systemctl stop supervisor 2>/dev/null || true
systemctl stop nginx 2>/dev/null || true

# Remover configurações do supervisor
echo "🗑️  Removendo configurações do supervisor..."
rm -f /etc/supervisor/conf.d/voucher-app.conf
supervisorctl reread 2>/dev/null || true
supervisorctl update 2>/dev/null || true

# Remover configurações do nginx
echo "🗑️  Removendo configurações do nginx..."
rm -f /etc/nginx/sites-available/voucher-app
rm -f /etc/nginx/sites-enabled/voucher-app

# Restaurar site padrão do nginx se não existir
if [ ! -f /etc/nginx/sites-enabled/default ] && [ -f /etc/nginx/sites-available/default ]; then
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
fi

# Remover aplicação
echo "🗑️  Removendo aplicação..."
rm -rf /opt/voucher-app

# Remover logs
echo "🗑️  Removendo logs..."
rm -rf /var/log/voucher-app
rm -f /var/log/voucher-app.log

# Remover usuário do sistema
echo "🗑️  Removendo usuário..."
if id "voucher" &>/dev/null; then
    userdel -r voucher 2>/dev/null || true
fi

# Remover arquivos temporários
echo "🗑️  Removendo arquivos temporários..."
rm -rf /tmp/voucher-install
rm -rf /tmp/OmadaVoucherController*

# Reiniciar serviços
echo "🔄 Reiniciando serviços..."
systemctl restart nginx 2>/dev/null || true
systemctl restart supervisor 2>/dev/null || true

echo ""
echo "========================================="
echo "✅ REMOÇÃO CONCLUÍDA!"
echo "========================================="
echo ""
echo "📋 O que foi removido:"
echo "   ✅ Aplicação (/opt/voucher-app)"
echo "   ✅ Configurações do Nginx"
echo "   ✅ Configurações do Supervisor"
echo "   ✅ Logs da aplicação"
echo "   ✅ Usuário 'voucher'"
echo "   ✅ Arquivos temporários"
echo ""
echo "🚀 Agora você pode fazer uma instalação limpa:"
echo "   curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/quick_install.sh | sudo bash"
echo ""
echo "⚠️  IMPORTANTE:"
echo "   - Os dados do banco de dados NÃO foram removidos"
echo "   - Nginx e Supervisor continuam instalados"
echo "   - Uma nova instalação pode reutilizar os dados existentes"
echo ""