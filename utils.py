import os
import io
import logging
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from flask import current_app
from typing import List, Dict

def generate_voucher_pdf(voucher_group, voucher_codes: List[str]) -> bytes:
    """Generate PDF with voucher codes"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.darkblue,
        alignment=TA_CENTER,
        spaceAfter=0.3*inch
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.black,
        alignment=TA_LEFT,
        spaceAfter=0.2*inch
    )
    
    # Build content
    story = []
    
    # Title
    title = Paragraph("Vouchers de Internet", title_style)
    story.append(title)
    
    # Plan information
    plan_info = f"""
    <b>Plano:</b> {voucher_group.plan.name}<br/>
    <b>Duração:</b> {voucher_group.plan.duration} {voucher_group.plan.duration_unit}<br/>
    <b>Preço:</b> R$ {voucher_group.plan.price:.2f}<br/>
    <b>Quantidade:</b> {voucher_group.quantity}<br/>
    <b>Valor Total:</b> R$ {voucher_group.total_value:.2f}<br/>
    <b>Data de Criação:</b> {voucher_group.created_at.strftime('%d/%m/%Y %H:%M')}<br/>
    <b>Site:</b> {voucher_group.site.name}
    """
    
    info_para = Paragraph(plan_info, header_style)
    story.append(info_para)
    story.append(Spacer(1, 0.3*inch))
    
    # Voucher codes table
    voucher_data = [['Código do Voucher', 'Status']]
    for code in voucher_codes:
        voucher_data.append([code, 'Ativo'])
    
    # Create table with voucher codes (2 columns per row for better space usage)
    table_data = []
    for i in range(0, len(voucher_codes), 2):
        row = []
        row.append(voucher_codes[i])
        if i + 1 < len(voucher_codes):
            row.append(voucher_codes[i + 1])
        else:
            row.append('')
        table_data.append(row)
    
    # Add header
    table_data.insert(0, ['Código do Voucher', 'Código do Voucher'])
    
    table = Table(table_data, colWidths=[2.5*inch, 2.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    story.append(table)
    
    # Instructions
    instructions = f"""
    <b>IMPORTANTE - CÓDIGOS DE VOUCHER:</b><br/>
    Os códigos reais dos vouchers estão disponíveis no Omada Controller.<br/>
    Acesse: Painel do Omada Controller → Sites → Hotspot → Grupos de Vouchers<br/>
    ID do Grupo: {voucher_group.omada_group_id}<br/><br/>
    
    <b>Instruções de Uso:</b><br/>
    1. Conecte-se à rede Wi-Fi do local<br/>
    2. Abra o navegador e acesse qualquer site<br/>
    3. Será redirecionado para a página de autenticação<br/>
    4. Digite o código do voucher real (do Omada Controller) e clique em "Conectar"<br/>
    5. Aguarde a confirmação da conexão<br/><br/>
    <b>Importante:</b> Cada voucher pode ser usado apenas uma vez e tem validade conforme o plano escolhido.
    """
    
    story.append(Spacer(1, 0.3*inch))
    instructions_para = Paragraph(instructions, header_style)
    story.append(instructions_para)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.read()

def format_currency(value: float) -> str:
    """Format currency in Brazilian Real"""
    if value is None:
        value = 0
    return f"{value:.2f}".replace('.', ',')

def format_duration(duration: int, unit: str) -> str:
    """Format duration with proper unit"""
    if unit == 'minutes':
        if duration >= 60:
            hours = duration // 60
            minutes = duration % 60
            if minutes == 0:
                return f"{hours}h"
            return f"{hours}h {minutes}min"
        return f"{duration}min"
    elif unit == 'hours':
        if duration >= 24:
            days = duration // 24
            hours = duration % 24
            if hours == 0:
                return f"{days}d"
            return f"{days}d {hours}h"
        return f"{duration}h"
    elif unit == 'days':
        return f"{duration}d"
    return f"{duration} {unit}"

def generate_sales_report_data(site_id: int, start_date: datetime = None, end_date: datetime = None) -> Dict:
    """Generate sales report data for a specific site based on actual voucher usage"""
    from models import VoucherGroup, VoucherPlan
    
    query = VoucherGroup.query.filter_by(site_id=site_id)
    
    if start_date:
        query = query.filter(VoucherGroup.created_at >= start_date)
    if end_date:
        query = query.filter(VoucherGroup.created_at <= end_date)
    
    voucher_groups = query.all()
    
    # Calculate totals based on actually sold vouchers (expired + used)
    total_vouchers_generated = sum(vg.quantity for vg in voucher_groups)
    total_vouchers_sold = sum((vg.expired_count or 0) + (vg.used_count or 0) for vg in voucher_groups)
    total_revenue = sum(((vg.expired_count or 0) + (vg.used_count or 0)) * vg.plan.price for vg in voucher_groups)
    
    # Group by plan - only count sold vouchers
    plan_sales = {}
    for vg in voucher_groups:
        plan_name = vg.plan.name
        sold_vouchers = (vg.expired_count or 0) + (vg.used_count or 0)
        
        if plan_name not in plan_sales:
            plan_sales[plan_name] = {
                'quantity_generated': 0,
                'quantity_sold': 0,
                'revenue': 0,
                'plan_price': vg.plan.price
            }
        
        plan_sales[plan_name]['quantity_generated'] += vg.quantity
        plan_sales[plan_name]['quantity_sold'] += sold_vouchers
        plan_sales[plan_name]['revenue'] += sold_vouchers * vg.plan.price
    
    # Group by vendor - only count sold vouchers
    vendor_sales = {}
    for vg in voucher_groups:
        vendor_name = vg.created_by.username
        sold_vouchers = (vg.expired_count or 0) + (vg.used_count or 0)
        
        if vendor_name not in vendor_sales:
            vendor_sales[vendor_name] = {
                'quantity_generated': 0,
                'quantity_sold': 0,
                'revenue': 0
            }
        
        vendor_sales[vendor_name]['quantity_generated'] += vg.quantity
        vendor_sales[vendor_name]['quantity_sold'] += sold_vouchers
        vendor_sales[vendor_name]['revenue'] += sold_vouchers * vg.plan.price
    
    return {
        'total_vouchers_generated': total_vouchers_generated,
        'total_vouchers_sold': total_vouchers_sold,
        'total_revenue': total_revenue,
        'plan_sales': plan_sales,
        'vendor_sales': vendor_sales,
        'voucher_groups': voucher_groups
    }

def sync_sites_from_omada():
    """Sync sites from Omada Controller"""
    from omada_api import omada_api
    from models import Site
    from app import db
    
    try:
        # Get all sites from Omada Controller (paginated)
        all_sites = []
        page = 1
        page_size = 100
        
        while True:
            sites_data = omada_api.get_sites(page=page, page_size=page_size)
            if not sites_data:
                break
            
            all_sites.extend(sites_data)
            
            # If we got less than page_size results, we've reached the end
            if len(sites_data) < page_size:
                break
                
            page += 1
        
        if not all_sites:
            return False, "Nenhum site encontrado no Omada Controller. Verifique a configuração da API."
        
        synced_count = 0
        updated_count = 0
        
        for site_data in all_sites:
            site = Site.query.filter_by(site_id=site_data['siteId']).first()
            if not site:
                # Create new site
                site = Site(
                    site_id=site_data['siteId'],
                    name=site_data['name'],
                    region=site_data.get('region', ''),
                    timezone=site_data.get('timeZone', ''),
                    scenario=site_data.get('scenario', ''),
                    site_type=site_data.get('type', 0),
                    last_sync=datetime.utcnow()
                )
                db.session.add(site)
                synced_count += 1
                logging.info(f"New site added: {site_data['name']} (ID: {site_data['siteId']})")
            else:
                # Update existing site
                site.name = site_data['name']
                site.region = site_data.get('region', '')
                site.timezone = site_data.get('timeZone', '')
                site.scenario = site_data.get('scenario', '')
                site.site_type = site_data.get('type', 0)
                site.last_sync = datetime.utcnow()
                updated_count += 1
                logging.info(f"Site updated: {site_data['name']} (ID: {site_data['siteId']})")
        
        db.session.commit()
        
        total_sites = Site.query.count()
        message = f"Sincronização concluída! {synced_count} novos sites, {updated_count} atualizados. Total: {total_sites} sites."
        logging.info(message)
        return True, message
        
    except Exception as e:
        logging.error(f"Error syncing sites: {str(e)}")
        return False, f"Erro na sincronização: {str(e)}"

def sync_voucher_statuses_from_omada(site_id: int):
    """Sync voucher statuses from Omada Controller for a specific site"""
    from omada_api import omada_api
    from models import Site, VoucherGroup
    from app import db
    import logging
    
    # Get the site from database
    site = Site.query.get(site_id)
    if not site:
        logging.error(f"Site with id {site_id} not found")
        return False
    
    # Get voucher groups for this site from Omada Controller
    response = omada_api.get_voucher_groups(site.site_id)
    
    if response and response.get('errorCode') == 0:
        voucher_groups_data = response.get('result', {}).get('data', [])
        
        for group_data in voucher_groups_data:
            omada_group_id = group_data.get('id')
            if omada_group_id:
                # Find the corresponding voucher group in our database
                voucher_group = VoucherGroup.query.filter_by(omada_group_id=omada_group_id).first()
                
                if voucher_group:
                    # Update status counts from Omada Controller
                    voucher_group.unused_count = group_data.get('unusedCount', 0)
                    voucher_group.used_count = group_data.get('usedCount', 0)
                    voucher_group.in_use_count = group_data.get('inUseCount', 0)
                    voucher_group.expired_count = group_data.get('expiredCount', 0)
                    voucher_group.last_sync = datetime.utcnow()
                    
                    # Update overall status based on counts
                    # Expired vouchers are considered "sold" (used)
                    if voucher_group.expired_count > 0 or voucher_group.used_count > 0 or voucher_group.in_use_count > 0:
                        voucher_group.status = 'sold'
                    else:
                        voucher_group.status = 'generated'
                    
                    logging.info(f"Updated voucher group {voucher_group.id}: unused={voucher_group.unused_count}, "
                               f"used={voucher_group.used_count}, in_use={voucher_group.in_use_count}, "
                               f"expired={voucher_group.expired_count}, status={voucher_group.status}")
        
        db.session.commit()
        return True
    
    return False
