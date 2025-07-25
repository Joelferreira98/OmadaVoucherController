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
from typing import List, Dict, Optional

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

def get_sold_vouchers_from_omada(site_id: str, start_date=None, end_date=None):
    """Get individual sold vouchers (status 1: in-use, 2: expired) from Omada Controller"""
    from omada_api import OmadaAPI
    from models import Site, VoucherPlan
    
    omada_api = OmadaAPI()
    sold_vouchers = []
    
    try:
        # First, get all voucher groups from Omada Controller
        groups_response = omada_api.get_voucher_group_list(site_id)
        
        if not groups_response or groups_response.get('errorCode') != 0:
            logging.error(f"Failed to get voucher groups from Omada Controller for site {site_id}")
            return []
        
        voucher_groups = groups_response.get('result', {}).get('data', [])
        logging.info(f"Found {len(voucher_groups)} voucher groups in Omada Controller")
        
        for group in voucher_groups:
            group_id = group.get('id')
            group_name = group.get('name', '')
            unit_price = float(group.get('unitPrice', '0')) / 100  # Convert from cents
            created_time = group.get('createdTime', 0)
            
            # Skip if outside date range
            if start_date or end_date:
                group_date = datetime.fromtimestamp(created_time / 1000) if created_time else datetime.now()
                if start_date and group_date.date() < start_date:
                    continue
                if end_date and group_date.date() > end_date:
                    continue
            
            # Get individual vouchers from this group
            # First get in-use vouchers (status 1)
            in_use_response = omada_api.get_individual_vouchers_from_group(site_id, group_id, status_filter=1)
            if in_use_response and in_use_response.get('errorCode') == 0:
                in_use_vouchers = in_use_response.get('result', {}).get('data', [])
                for voucher in in_use_vouchers:
                    sold_vouchers.append({
                        'id': voucher.get('id'),
                        'code': voucher.get('code'),
                        'status': 1,  # In use
                        'status_text': 'Em Uso',
                        'status_class': 'warning',
                        'group_id': group_id,
                        'group_name': group_name,
                        'unit_price': unit_price,
                        'plan_name': _extract_plan_name_from_group(group_name),
                        'created_at': datetime.fromtimestamp(created_time / 1000) if created_time else datetime.now()
                    })
            
            # Then get expired vouchers (status 2)
            expired_response = omada_api.get_individual_vouchers_from_group(site_id, group_id, status_filter=2)
            if expired_response and expired_response.get('errorCode') == 0:
                expired_vouchers = expired_response.get('result', {}).get('data', [])
                for voucher in expired_vouchers:
                    sold_vouchers.append({
                        'id': voucher.get('id'),
                        'code': voucher.get('code'),
                        'status': 2,  # Expired
                        'status_text': 'Expirado',
                        'status_class': 'danger',
                        'group_id': group_id,
                        'group_name': group_name,
                        'unit_price': unit_price,
                        'plan_name': _extract_plan_name_from_group(group_name),
                        'created_at': datetime.fromtimestamp(created_time / 1000) if created_time else datetime.now()
                    })
        
        logging.info(f"Found {len(sold_vouchers)} sold vouchers for site {site_id}")
        return sold_vouchers
        
    except Exception as e:
        logging.error(f"Error getting sold vouchers from Omada Controller: {str(e)}")
        return []

def _extract_plan_name_from_group(group_name: str) -> str:
    """Extract plan name from group name (removes ID prefix and timestamp)"""
    # Group name format: XXX-plan-name_YYYYMMDD_HHMMSS
    try:
        # Remove timestamp part
        if '_' in group_name:
            parts = group_name.split('_')
            name_part = parts[0]  # Everything before first underscore
        else:
            name_part = group_name
        
        # Remove ID prefix (XXX-)
        if '-' in name_part and name_part[:3].isdigit():
            return name_part[4:]  # Remove "XXX-" prefix
        
        return name_part
    except:
        return group_name

def generate_sales_report_data(site_id: int, start_date=None, end_date=None) -> Dict:
    """Generate sales report data for a specific site based on actual voucher usage"""
    from models import VoucherGroup, VoucherPlan
    
    query = VoucherGroup.query.filter_by(site_id=site_id)
    
    if start_date:
        query = query.filter(VoucherGroup.created_at >= start_date)
    if end_date:
        query = query.filter(VoucherGroup.created_at <= end_date)
    
    voucher_groups = query.all()
    
    # Calculate totals based on actually sold vouchers (expired + used + in_use)
    total_vouchers_generated = sum(vg.quantity for vg in voucher_groups)
    total_vouchers_sold = sum((vg.expired_count or 0) + (vg.used_count or 0) + (vg.in_use_count or 0) for vg in voucher_groups)
    total_revenue = sum(((vg.expired_count or 0) + (vg.used_count or 0) + (vg.in_use_count or 0)) * vg.plan.price for vg in voucher_groups)
    
    # Group by plan - only count sold vouchers
    plan_sales = {}
    for vg in voucher_groups:
        plan_name = vg.plan.name
        sold_vouchers = (vg.expired_count or 0) + (vg.used_count or 0) + (vg.in_use_count or 0)
        
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
        sold_vouchers = (vg.expired_count or 0) + (vg.used_count or 0) + (vg.in_use_count or 0)
        
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
            logging.warning("Nenhum site encontrado no Omada Controller")
            return 0
        
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
        
        total_count = synced_count + updated_count
        logging.info(f"Sites synced: {synced_count} new, {updated_count} updated, {total_count} total")
        return total_count
        
    except Exception as e:
        logging.error(f"Error syncing sites: {str(e)}")
        raise e

def sync_voucher_statuses_from_omada(site_id: int):
    """
    Sync voucher statuses from Omada Controller for a specific site
    Also discovers and imports voucher groups that exist in Omada but not locally
    """
    from omada_api import omada_api
    from models import Site, VoucherGroup, VoucherPlan, User, AdminSite
    from app import db
    import logging
    
    try:
        # Get site from database
        site = Site.query.get(site_id)
        if not site:
            logging.error(f"Site with ID {site_id} not found in database")
            return False
        
        logging.info(f"Syncing voucher statuses for site: {site.name} (ID: {site_id})")
        
        # Get ALL voucher groups from Omada Controller (paginated)
        all_voucher_groups = []
        page = 1
        page_size = 100
        
        while True:
            response = omada_api.get_voucher_groups(site.site_id, page=page, page_size=page_size)
            
            if not response or response.get('errorCode') != 0:
                if page == 1:
                    logging.error(f"Failed to get voucher groups from Omada Controller")
                    return False
                else:
                    break
            
            result = response.get('result', {})
            data = result.get('data', [])
            
            if not data:
                break
                
            all_voucher_groups.extend(data)
            
            # Check if there are more pages
            total_rows = result.get('totalRows', 0)
            if len(all_voucher_groups) >= total_rows:
                break
                
            page += 1
        
        logging.info(f"Found {len(all_voucher_groups)} voucher groups in Omada Controller")
        
        total_synced = 0
        new_groups_imported = 0
        
        for group_data in all_voucher_groups:
            omada_group_id = group_data.get('id')
            if not omada_group_id:
                continue
            
            # Find the corresponding voucher group in our database
            voucher_group = VoucherGroup.query.filter_by(omada_group_id=omada_group_id).first()
            
            if not voucher_group:
                # This voucher group exists in Omada but not locally - import it
                logging.info(f"Importing missing voucher group {omada_group_id}")
                
                # Get detailed information about this group
                group_details = omada_api.get_voucher_group_detail(site.site_id, omada_group_id)
                
                if group_details and group_details.get('errorCode') == 0:
                    result_data = group_details.get('result', {})
                    group_info = result_data.get('groupInfo', {})
                    voucher_data_list = result_data.get('data', [])
                    
                    if voucher_data_list:
                        # Create or find a suitable plan
                        plan_name = f"Importado - {group_info.get('name', 'Sem Nome')}"[:50]
                        duration_limit = group_info.get('durationLimit', 60)
                        data_limit = group_info.get('dataLimit', 0)
                        
                        # Try to find existing plan with similar characteristics
                        existing_plan = VoucherPlan.query.filter_by(
                            site_id=site_id,
                            duration=duration_limit
                        ).first()
                        
                        if not existing_plan:
                            # Create new plan for imported vouchers
                            existing_plan = VoucherPlan(
                                name=plan_name,
                                duration=duration_limit,
                                price=0.00,  # Unknown price for imported vouchers
                                site_id=site_id,
                                is_active=True,
                                data_quota=data_limit,  # Correct field name
                                code_length=8,
                                limit_type=2  # Unlimited type
                            )
                            db.session.add(existing_plan)
                            db.session.flush()  # Get the ID
                        
                        # Find appropriate user to attribute import to
                        import_user = None
                        
                        # Prefer admin users for this site
                        admin_sites = AdminSite.query.filter_by(site_id=site_id).all()
                        if admin_sites:
                            import_user = User.query.get(admin_sites[0].admin_id)
                        
                        # Fallback to master or any user
                        if not import_user:
                            import_user = (User.query.filter_by(user_type='master').first() or
                                         User.query.filter_by(user_type='admin').first() or
                                         User.query.first())
                        
                        if import_user:
                            # Extract voucher codes
                            voucher_codes = [v.get('code', f'CODE-{i}') for i, v in enumerate(voucher_data_list)]
                            
                            # Count statuses
                            unused_count = sum(1 for v in voucher_data_list if v.get('status') == 0)
                            used_count = sum(1 for v in voucher_data_list if v.get('status') == 1)
                            in_use_count = sum(1 for v in voucher_data_list if v.get('status') == 2)
                            expired_count = sum(1 for v in voucher_data_list if v.get('status') == 3)
                            
                            # Calculate total value based on quantity and plan price
                            total_value = len(voucher_data_list) * existing_plan.price
                            
                            # Create voucher group
                            voucher_group = VoucherGroup(
                                plan_id=existing_plan.id,
                                site_id=site_id,
                                quantity=len(voucher_data_list),
                                omada_group_id=omada_group_id,
                                created_by_id=import_user.id,
                                voucher_codes=voucher_codes,
                                total_value=total_value,
                                created_at=datetime.now(),
                                unused_count=unused_count,
                                used_count=used_count,
                                in_use_count=in_use_count,
                                expired_count=expired_count,
                                last_sync=datetime.now(),
                                status='sold' if (expired_count + used_count + in_use_count) > 0 else 'generated'
                            )
                            db.session.add(voucher_group)
                            new_groups_imported += 1
                            
                            logging.info(f"Imported voucher group {omada_group_id} with {len(voucher_data_list)} vouchers")
            
            if voucher_group:
                # Update existing voucher group with fresh data from Omada
                try:
                    group_details = omada_api.get_voucher_group_detail(site.site_id, omada_group_id)
                    if group_details and group_details.get('errorCode') == 0:
                        voucher_data_list = group_details.get('result', {}).get('data', [])
                        
                        # Count vouchers by status
                        unused_count = sum(1 for v in voucher_data_list if v.get('status') == 0)
                        used_count = sum(1 for v in voucher_data_list if v.get('status') == 1)
                        in_use_count = sum(1 for v in voucher_data_list if v.get('status') == 2)
                        expired_count = sum(1 for v in voucher_data_list if v.get('status') == 3)
                        
                        # Update counts
                        voucher_group.unused_count = unused_count
                        voucher_group.used_count = used_count
                        voucher_group.in_use_count = in_use_count
                        voucher_group.expired_count = expired_count
                        voucher_group.last_sync = datetime.now()
                        
                        # Update voucher codes if we have real ones
                        real_codes = [v.get('code') for v in voucher_data_list if v.get('code') and not v.get('code', '').startswith('OMADA-')]
                        if real_codes and len(real_codes) == len(voucher_data_list):
                            voucher_group.voucher_codes = real_codes
                        
                        # Update status
                        voucher_group.status = 'sold' if (expired_count + used_count + in_use_count) > 0 else 'generated'
                        
                        total_synced += 1
                        
                except Exception as e:
                    logging.error(f"Error updating voucher group {omada_group_id}: {str(e)}")
        
        # Commit all changes
        db.session.commit()
        
        if new_groups_imported > 0:
            logging.info(f"Imported {new_groups_imported} new voucher groups from Omada Controller")
        
        logging.info(f"Successfully synced {total_synced} voucher groups for site {site_id}")
        return True
        
    except Exception as e:
        logging.error(f"Error syncing voucher statuses from Omada: {str(e)}")
        db.session.rollback()
        return False


# Permission Management Functions
def get_vendor_site_for_user():
    """
    Get vendor site for current user, supporting hierarchical access
    Returns vendor_site object or None
    """
    from flask_login import current_user
    from flask import session
    from models import VendorSite, Site
    
    if current_user.user_type == 'vendor':
        # Standard vendor access
        return VendorSite.query.filter_by(vendor_id=current_user.id).first()
    elif current_user.user_type in ['admin', 'master']:
        # Admin/Master accessing vendor functions
        current_site_id = session.get('selected_site_id')
        if current_site_id:
            current_site = Site.query.get(current_site_id)
            if current_site:
                # Create mock vendor_site object for compatibility
                class MockVendorSite:
                    def __init__(self, site):
                        self.site = site
                        self.site_id = site.id
                        self.vendor_id = current_user.id
                return MockVendorSite(current_site)
    return None

def has_permission(required_role):
    """
    Check if current user has the required permission level
    
    Permission hierarchy:
    - master: can access all features (master, admin, vendor)
    - admin: can access admin and vendor features  
    - vendor: can access only vendor features
    """
    from flask_login import current_user
    
    if not current_user.is_authenticated:
        return False
    
    user_role = current_user.user_type
    
    # Master users have all permissions
    if user_role == 'master':
        return True
    
    # Admin users have admin and vendor permissions
    if user_role == 'admin' and required_role in ['admin', 'vendor']:
        return True
    
    # Vendor users only have vendor permissions
    if user_role == 'vendor' and required_role == 'vendor':
        return True
    
    return False


def require_permission(required_role):
    """
    Decorator to require specific permission level for routes
    
    Usage:
    @require_permission('vendor')  # vendor, admin, or master can access
    @require_permission('admin')   # admin or master can access  
    @require_permission('master')  # only master can access
    """
    from functools import wraps
    from flask import abort
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not has_permission(required_role):
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def check_site_access(site_id, user_type=None, user_id=None):
    """
    Check if user has access to a specific site
    
    Returns True if user can access the site, False otherwise
    """
    from flask_login import current_user
    from models import AdminSite, VendorSite
    
    if user_type is None:
        user_type = current_user.user_type
    if user_id is None:
        user_id = current_user.id
    
    # Master users have access to all sites
    if user_type == 'master':
        return True
    
    # Admin users need explicit site assignment
    if user_type == 'admin':
        admin_site = AdminSite.query.filter_by(admin_id=user_id, site_id=site_id).first()
        return admin_site is not None
    
    # Vendor users need explicit site assignment
    if user_type == 'vendor':
        vendor_site = VendorSite.query.filter_by(vendor_id=user_id, site_id=site_id).first()
        return vendor_site is not None
    
    return False


def get_accessible_sites(user_type=None, user_id=None):
    """
    Get list of sites accessible to the current user
    
    Returns list of Site objects
    """
    from flask_login import current_user
    from models import Site, AdminSite, VendorSite
    
    if user_type is None:
        user_type = current_user.user_type
    if user_id is None:
        user_id = current_user.id
    
    # Master users can access all sites
    if user_type == 'master':
        return Site.query.all()
    
    # Admin users can access their assigned sites
    if user_type == 'admin':
        admin_sites = AdminSite.query.filter_by(admin_id=user_id).all()
        site_ids = [admin_site.site_id for admin_site in admin_sites]
        return Site.query.filter(Site.id.in_(site_ids)).all()
    
    # Vendor users can access their assigned sites
    if user_type == 'vendor':
        vendor_sites = VendorSite.query.filter_by(vendor_id=user_id).all()
        site_ids = [vendor_site.site_id for vendor_site in vendor_sites]
        return Site.query.filter(Site.id.in_(site_ids)).all()
    
    return []


def can_manage_user(target_user_type, manager_user_type=None):
    """
    Check if a user can manage another user type
    
    Rules:
    - Master can manage admin and vendor users
    - Admin can manage vendor users
    - Vendor cannot manage any users
    """
    from flask_login import current_user
    
    if manager_user_type is None:
        manager_user_type = current_user.user_type
    
    # Master can manage admin and vendor
    if manager_user_type == 'master' and target_user_type in ['admin', 'vendor']:
        return True
    
    # Admin can manage vendor
    if manager_user_type == 'admin' and target_user_type == 'vendor':
        return True
    
    return False
