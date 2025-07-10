#!/bin/bash

# Script para limpar resquícios e preparar para nova instalação
# Execute este script se ainda houver problemas após a remoção

echo "🧹 Limpeza Completa do Sistema"
echo "============================="

# Verificar se é root
if [[ $EUID -ne 0 ]]; then
    echo "❌ Execute como root: sudo bash cleanup.sh"
    exit 1
fi

echo "🔍 Verificando resquícios da instalação anterior..."

# Matar processos relacionados
echo "⏹️  Matando processos relacionados..."
pkill -f "voucher-app" 2>/dev/null || true
pkill -f "gunicorn.*main:app" 2>/dev/null || true
pkill -f "/opt/voucher-app" 2>/dev/null || true

# Limpar supervisor completamente
echo "🗑️  Limpando supervisor..."
supervisorctl stop all 2>/dev/null || true
rm -f /etc/supervisor/conf.d/voucher*
rm -f /etc/supervisor/supervisord.conf.backup*
supervisorctl reread 2>/dev/null || true
supervisorctl update 2>/dev/null || true

# Limpar nginx completamente
echo "🗑️  Limpando nginx..."
rm -f /etc/nginx/sites-available/voucher*
rm -f /etc/nginx/sites-enabled/voucher*
nginx -t 2>/dev/null || true

# Limpar todos os diretórios relacionados
echo "🗑️  Removendo diretórios..."
rm -rf /opt/voucher*
rm -rf /var/log/voucher*
rm -rf /tmp/voucher*
rm -rf /tmp/OmadaVoucherController*

# Limpar usuários relacionados
echo "🗑️  Removendo usuários..."
for user in voucher voucher-app omada-app; do
    if id "$user" &>/dev/null; then
        userdel -r "$user" 2>/dev/null || true
    fi
done

# Limpar processos em segundo plano
echo "🗑️  Limpando processos em segundo plano..."
jobs -p | xargs -r kill 2>/dev/null || true

# Limpar arquivos de lock
echo "🗑️  Removendo arquivos de lock..."
rm -f /var/lock/voucher*
rm -f /var/run/voucher*

# Limpar cache Python
echo "🗑️  Limpando cache Python..."
find /tmp -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find /tmp -name "*.pyc" -type f -delete 2>/dev/null || true

# Limpar logs antigos
echo "🗑️  Limpando logs antigos..."
find /var/log -name "*voucher*" -type f -delete 2>/dev/null || true
find /var/log -name "*omada*" -type f -delete 2>/dev/null || true

# Verificar portas em uso
echo "🔍 Verificando porta 5000..."
PORT_5000=$(netstat -tlnp 2>/dev/null | grep ":5000 " | wc -l)
if [ $PORT_5000 -gt 0 ]; then
    echo "⚠️  Porta 5000 ainda está em uso:"
    netstat -tlnp | grep ":5000 "
    echo "   Matando processos na porta 5000..."
    fuser -k 5000/tcp 2>/dev/null || true
fi

# Reiniciar serviços
echo "🔄 Reiniciando serviços..."
systemctl restart nginx 2>/dev/null || true
systemctl restart supervisor 2>/dev/null || true

# Verificar se limpeza foi bem-sucedida
echo "🔍 Verificando limpeza..."
REMAINING_FILES=$(find /opt -name "*voucher*" -type d 2>/dev/null | wc -l)
REMAINING_CONFIGS=$(find /etc -name "*voucher*" -type f 2>/dev/null | wc -l)
REMAINING_LOGS=$(find /var/log -name "*voucher*" -type f 2>/dev/null | wc -l)

echo ""
echo "========================================="
echo "✅ LIMPEZA CONCLUÍDA!"
echo "========================================="
echo ""
echo "📊 Resumo da limpeza:"
echo "   - Processos: Terminados"
echo "   - Arquivos restantes: $REMAINING_FILES"
echo "   - Configurações restantes: $REMAINING_CONFIGS"
echo "   - Logs restantes: $REMAINING_LOGS"
echo "   - Porta 5000: Liberada"
echo ""

if [ $REMAINING_FILES -eq 0 ] && [ $REMAINING_CONFIGS -eq 0 ] && [ $REMAINING_LOGS -eq 0 ]; then
    echo "✅ Sistema completamente limpo!"
else
    echo "⚠️  Alguns arquivos podem ter restado, mas não devem interferir na nova instalação"
fi

echo ""
echo "🚀 Sistema pronto para nova instalação:"
echo "   curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/quick_install.sh | sudo bash"
echo ""
echo "💡 Dica: Aguarde alguns segundos antes de fazer a nova instalação"
echo "   para garantir que todos os serviços foram reiniciados corretamente"
echo ""