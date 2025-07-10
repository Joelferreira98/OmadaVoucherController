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

def generate_voucher_pdf(voucher_group, voucher_codes: List[str], format_type: str = "a4") -> bytes:
    """Generate PDF with voucher codes in A4 or 50x80mm format"""
    buffer = io.BytesIO()
    
    if format_type == "50x80mm":
        # Small voucher format (50x80mm)
        from reportlab.lib.units import mm
        page_size = (50*mm, 80*mm)
        doc = SimpleDocTemplate(buffer, pagesize=page_size, rightMargin=2*mm, leftMargin=2*mm, topMargin=3*mm, bottomMargin=3*mm)
        return generate_small_voucher_pdf(voucher_group, voucher_codes, buffer, doc)
    else:
        # Standard A4 format
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        return generate_standard_voucher_pdf(voucher_group, voucher_codes, buffer, doc)

def generate_small_voucher_pdf(voucher_group, voucher_codes: List[str], buffer, doc) -> bytes:
    """Generate small format vouchers (50x80mm) - Individual tickets"""
    from reportlab.lib.units import mm
    from reportlab.platypus import PageBreak
    
    # Create ticket-style compact styles for small format
    styles = getSampleStyleSheet()
    
    # Header style for business name
    header_style = ParagraphStyle(
        'TicketHeader',
        parent=styles['Normal'],
        fontSize=8,
        spaceAfter=1*mm,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    # Site name style
    site_style = ParagraphStyle(
        'SiteName',
        parent=styles['Normal'],
        fontSize=7,
        spaceAfter=2*mm,
        alignment=TA_CENTER,
        textColor=colors.black
    )
    
    # Code style with border effect
    code_style = ParagraphStyle(
        'VoucherCode',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=2*mm,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Courier-Bold'
    )
    
    # Plan name style
    plan_style = ParagraphStyle(
        'PlanName',
        parent=styles['Normal'],
        fontSize=8,
        spaceAfter=1*mm,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    # Price style
    price_style = ParagraphStyle(
        'PriceStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=2*mm,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    # Info style for small details
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=5,
        spaceAfter=0.5*mm,
        alignment=TA_CENTER,
        textColor=colors.black
    )
    
    # Check if we have real codes or placeholder codes
    has_real_codes = voucher_codes and not any('OMADA-' in str(code) for code in voucher_codes)
    
    # Generate responsive vouchers for thermal printer (50x80mm)
    story = []
    for i, code in enumerate(voucher_codes):
        if i > 0:
            story.append(PageBreak())
        
        # Create compact ticket content
        ticket_lines = []
        
        # Site name
        ticket_lines.append(f"<b>{voucher_group.site.name}</b>")
        ticket_lines.append("- - - - - - - - - - - -")
        
        # Voucher code
        if has_real_codes:
            ticket_lines.append(f"<font name='Courier-Bold' size='14'>{code}</font>")
        else:
            ticket_lines.append("<font name='Courier-Bold' size='10'>VER OMADA</font>")
            ticket_lines.append(f"<font size='6'>ID: {voucher_group.omada_group_id[:10]}...</font>")
        
        # Plan name
        ticket_lines.append(f"<b>{voucher_group.plan.name}</b>")
        
        # Price
        ticket_lines.append(f"<font size='12'><b>{format_currency(voucher_group.plan.price)}</b></font>")
        
        # Cut line
        ticket_lines.append("✂ - - - - - - - - - - - - ✂")
        
        # Create single compact paragraph
        ticket_content = "<br/>".join(ticket_lines)
        
        # Responsive paragraph style that adjusts to content
        compact_style = ParagraphStyle(
            'CompactThermal',
            parent=styles['Normal'],
            fontSize=7,
            alignment=TA_CENTER,
            textColor=colors.black,
            leading=8,
            spaceAfter=1*mm
        )
        
        story.append(Paragraph(ticket_content, compact_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.read()

def generate_standard_voucher_pdf(voucher_group, voucher_codes: List[str], buffer, doc) -> bytes:
    """Generate standard A4 format vouchers - Individual tickets arranged in grid"""
    from reportlab.platypus import PageBreak, Frame, KeepTogether
    from reportlab.lib.units import mm
    
    # Styles for ticket format on A4
    styles = getSampleStyleSheet()
    
    # Header style for each ticket
    ticket_header_style = ParagraphStyle(
        'TicketHeader',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=2*mm,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    # Site name style
    site_style = ParagraphStyle(
        'SiteName',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=3*mm,
        alignment=TA_CENTER,
        textColor=colors.black
    )
    
    # Code style
    code_style = ParagraphStyle(
        'VoucherCode',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=3*mm,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Courier-Bold'
    )
    
    # Plan name style
    plan_style = ParagraphStyle(
        'PlanName',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=2*mm,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    # Price style
    price_style = ParagraphStyle(
        'PriceStyle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=3*mm,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    # Info style
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=7,
        spaceAfter=1*mm,
        alignment=TA_CENTER,
        textColor=colors.black
    )
    
    # Cut line style
    cut_style = ParagraphStyle(
        'CutLine',
        parent=styles['Normal'],
        fontSize=8,
        spaceAfter=2*mm,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    
    # Check if we have real codes or placeholder codes
    has_real_codes = voucher_codes and not any('OMADA-' in str(code) for code in voucher_codes)
    
    # Create tickets in responsive grid format (4x8 = 32 tickets per page)
    story = []
    tickets_per_row = 4
    rows_per_page = 8
    
    # Create table data for tickets
    table_data = []
    current_row = []
    
    for i, code in enumerate(voucher_codes):
        # Create compact ticket content
        ticket_lines = []
        
        # Site name
        ticket_lines.append(f"<b>{voucher_group.site.name}</b>")
        ticket_lines.append("- - - - - - - - - -")
        
        # Voucher code
        if has_real_codes:
            ticket_lines.append(f"<font name='Courier-Bold' size='11'>{code}</font>")
        else:
            ticket_lines.append("<font name='Courier-Bold' size='9'>VER OMADA</font>")
            ticket_lines.append(f"<font size='6'>ID: {voucher_group.omada_group_id[:6]}...</font>")
        
        # Plan name and price
        ticket_lines.append(f"<b>{voucher_group.plan.name}</b>")
        ticket_lines.append(f"<font size='10'><b>{format_currency(voucher_group.plan.price)}</b></font>")
        ticket_lines.append("✂ - - - - - - ✂")
        
        # Join all content into a single paragraph
        ticket_content = "<br/>".join(ticket_lines)
        ticket_paragraph = Paragraph(ticket_content, ParagraphStyle(
            'CompactTicket',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.black,
            leading=9
        ))
        
        current_row.append(ticket_paragraph)
        
        # If row is complete or it's the last voucher, add to table
        if len(current_row) == tickets_per_row or i == len(voucher_codes) - 1:
            # Fill remaining cells if needed
            while len(current_row) < tickets_per_row:
                current_row.append("")
            
            table_data.append(current_row)
            current_row = []
            
            # If we have enough rows for a page, create the table
            if len(table_data) == rows_per_page or i == len(voucher_codes) - 1:
                # Calculate fixed dimensions based on full grid (4x8)
                available_width = 7.5 * inch  # A4 width minus margins
                available_height = 10 * inch  # A4 height minus margins
                
                col_width = available_width / tickets_per_row
                row_height = available_height / rows_per_page  # Always use full grid height
                
                # Fill remaining rows with empty cells if needed to maintain consistent sizing
                while len(table_data) < rows_per_page:
                    empty_row = [""] * tickets_per_row
                    table_data.append(empty_row)
                
                # Create table with fixed ticket dimensions
                table = Table(table_data, 
                            colWidths=[col_width] * tickets_per_row, 
                            rowHeights=[row_height] * rows_per_page)
                table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                
                story.append(table)
                
                # Add page break if not the last batch
                if i < len(voucher_codes) - 1:
                    story.append(PageBreak())
                
                # Reset table data for next page
                table_data = []
    
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
                    
                    # Try to sync real voucher codes if we don't have them or have placeholders
                    if (not voucher_group.voucher_codes or 
                        any('OMADA-' in str(code) for code in voucher_group.voucher_codes)):
                        try:
                            group_details = omada_api.get_voucher_group_detail(site.site_id, omada_group_id)
                            if group_details and group_details.get('errorCode') == 0:
                                voucher_data_list = group_details.get('result', {}).get('data', [])
                                real_codes = [voucher['code'] for voucher in voucher_data_list if 'code' in voucher]
                                if real_codes:
                                    voucher_group.voucher_codes = real_codes
                                    logging.info(f"Updated voucher group {voucher_group.id} with {len(real_codes)} real codes")
                        except Exception as e:
                            logging.error(f"Error syncing codes for group {voucher_group.id}: {str(e)}")
                    
                    # Update overall status based on counts
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
