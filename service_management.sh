#!/bin/bash

# Script para gerenciar o serviço voucher-app
echo "🛠️  Gerenciamento do Serviço Voucher Management System"
echo "======================================================="

# Função para mostrar status
show_status() {
    echo "📊 Status dos Serviços:"
    echo "----------------------"
    echo "🔹 Voucher App:"
    systemctl is-active voucher-app && echo "✅ Rodando" || echo "❌ Parado"
    
    echo "🔹 Nginx:"
    systemctl is-active nginx && echo "✅ Rodando" || echo "❌ Parado"
    
    echo "🔹 MySQL:"
    systemctl is-active mysql && echo "✅ Rodando" || echo "❌ Parado"
    
    echo ""
    echo "🔍 Detalhes do Voucher App:"
    systemctl status voucher-app --no-pager -l
}

# Função para mostrar logs
show_logs() {
    echo "📋 Logs do Sistema:"
    echo "------------------"
    echo "🔹 Últimas 50 linhas do voucher-app:"
    journalctl -u voucher-app -n 50 --no-pager
    
    echo ""
    echo "🔹 Últimas 20 linhas do Nginx:"
    tail -n 20 /var/log/nginx/voucher-app.access.log 2>/dev/null || echo "Arquivo de log não encontrado"
    
    echo ""
    echo "🔹 Erros do Nginx:"
    tail -n 10 /var/log/nginx/voucher-app.error.log 2>/dev/null || echo "Sem erros recentes"
}

# Função para reiniciar serviços
restart_services() {
    echo "🔄 Reiniciando serviços..."
    
    echo "🔹 Reiniciando voucher-app..."
    systemctl restart voucher-app
    
    echo "🔹 Reiniciando nginx..."
    systemctl restart nginx
    
    sleep 3
    
    echo "✅ Serviços reiniciados"
    show_status
}

# Função para testar conectividade
test_connectivity() {
    echo "🔍 Testando conectividade:"
    echo "-------------------------"
    
    # Teste local
    echo "🔹 Teste local (porta 5000):"
    curl -I http://localhost:5000 2>/dev/null && echo "✅ OK" || echo "❌ Falha"
    
    # Teste Nginx
    echo "🔹 Teste Nginx (porta 80):"
    curl -I http://localhost 2>/dev/null && echo "✅ OK" || echo "❌ Falha"
    
    # Teste banco de dados
    echo "🔹 Teste MySQL:"
    systemctl is-active mysql && echo "✅ MySQL rodando" || echo "❌ MySQL parado"
}

# Função para monitoramento em tempo real
monitor_realtime() {
    echo "📊 Monitoramento em tempo real (Ctrl+C para sair):"
    echo "==================================================="
    
    # Monitorar logs em tempo real
    tail -f /var/log/nginx/voucher-app.access.log &
    journalctl -u voucher-app -f
}

# Função para backup
backup_config() {
    echo "💾 Criando backup das configurações..."
    
    BACKUP_DIR="/opt/voucher-app/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup arquivos principais
    cp -r /opt/voucher-app/.env "$BACKUP_DIR/" 2>/dev/null
    cp -r /opt/voucher-app/static "$BACKUP_DIR/" 2>/dev/null
    cp /etc/systemd/system/voucher-app.service "$BACKUP_DIR/" 2>/dev/null
    cp /etc/nginx/sites-available/voucher-app "$BACKUP_DIR/" 2>/dev/null
    
    echo "✅ Backup criado em: $BACKUP_DIR"
}

# Menu principal
case "$1" in
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "restart")
        restart_services
        ;;
    "test")
        test_connectivity
        ;;
    "monitor")
        monitor_realtime
        ;;
    "backup")
        backup_config
        ;;
    *)
        echo "Uso: $0 {status|logs|restart|test|monitor|backup}"
        echo ""
        echo "Comandos disponíveis:"
        echo "  status   - Mostrar status dos serviços"
        echo "  logs     - Mostrar logs do sistema"
        echo "  restart  - Reiniciar todos os serviços"
        echo "  test     - Testar conectividade"
        echo "  monitor  - Monitoramento em tempo real"
        echo "  backup   - Fazer backup das configurações"
        echo ""
        echo "Exemplos:"
        echo "  sudo $0 status"
        echo "  sudo $0 logs"
        echo "  sudo $0 restart"
        ;;
esac