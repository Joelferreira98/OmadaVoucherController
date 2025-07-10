from flask import render_template, request, redirect, url_for, flash, jsonify, make_response, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import logging

from app import app, db, login_manager
from models import User, Site, AdminSite, VendorSite, VoucherPlan, VoucherGroup, OmadaConfig
from forms import LoginForm, UserForm, VoucherPlanForm, VoucherGenerationForm, OmadaConfigForm
from utils import generate_voucher_pdf, format_currency, format_duration, generate_sales_report_data, sync_sites_from_omada
from omada_api import omada_api

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data) and user.is_active:
            login_user(user)
            next_page = request.args.get('next')
            
            # Redirect based on user type
            if user.user_type == 'master':
                return redirect(next_page or url_for('master_dashboard'))
            elif user.user_type == 'admin':
                # Check if admin has multiple sites
                admin_sites = AdminSite.query.filter_by(admin_id=user.id).all()
                if len(admin_sites) > 1:
                    return redirect(url_for('admin_site_selection'))
                elif len(admin_sites) == 1:
                    session['current_site_id'] = admin_sites[0].site_id
                    return redirect(next_page or url_for('admin_dashboard'))
                else:
                    flash('Nenhum site atribuído. Contate o administrador.', 'warning')
                    logout_user()
                    return redirect(url_for('login'))
            elif user.user_type == 'vendor':
                return redirect(next_page or url_for('vendor_dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'error')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Logout realizado com sucesso.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.user_type == 'master':
        return redirect(url_for('master_dashboard'))
    elif current_user.user_type == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.user_type == 'vendor':
        return redirect(url_for('vendor_dashboard'))
    else:
        flash('Tipo de usuário inválido.', 'error')
        return redirect(url_for('login'))

# Master Routes
@app.route('/master')
@login_required
def master_dashboard():
    if current_user.user_type != 'master':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get statistics
    total_admins = User.query.filter_by(user_type='admin').count()
    total_vendors = User.query.filter_by(user_type='vendor').count()
    total_sites = Site.query.count()
    
    # Recent activity
    recent_vouchers = VoucherGroup.query.order_by(VoucherGroup.created_at.desc()).limit(10).all()
    
    return render_template('master/dashboard.html', 
                         total_admins=total_admins,
                         total_vendors=total_vendors,
                         total_sites=total_sites,
                         recent_vouchers=recent_vouchers)

@app.route('/master/admins')
@login_required
def manage_admins():
    if current_user.user_type != 'master':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    admins = User.query.filter_by(user_type='admin').all()
    sites = Site.query.all()
    
    return render_template('master/manage_admins.html', admins=admins, sites=sites)

@app.route('/master/create_admin', methods=['POST'])
@login_required
def create_admin():
    if current_user.user_type != 'master':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate required fields
        if not username or not email or not password:
            flash('Todos os campos são obrigatórios.', 'error')
            return redirect(url_for('manage_admins'))
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Usuário já existe.', 'error')
            return redirect(url_for('manage_admins'))
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email já existe.', 'error')
            return redirect(url_for('manage_admins'))
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            user_type='admin',
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        
        flash(f'Administrador {username} criado com sucesso.', 'success')
        logging.info(f"New admin created: {username} by {current_user.username}")
        
    except Exception as e:
        logging.error(f"Error creating admin: {str(e)}")
        flash('Erro ao criar administrador.', 'error')
    
    return redirect(url_for('manage_admins'))

@app.route('/master/assign_sites', methods=['POST'])
@login_required
def assign_sites():
    if current_user.user_type != 'master':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        admin_id = request.form.get('admin_id')
        site_ids = request.form.getlist('site_ids')
        
        # Validate admin exists
        admin = User.query.get(admin_id)
        if not admin or admin.user_type != 'admin':
            flash('Administrador não encontrado.', 'error')
            return redirect(url_for('manage_admins'))
        
        # Remove existing assignments
        AdminSite.query.filter_by(admin_id=admin_id).delete()
        
        # Add new assignments
        assigned_count = 0
        for site_id in site_ids:
            site = Site.query.get(site_id)
            if site:
                admin_site = AdminSite(admin_id=admin_id, site_id=site_id)
                db.session.add(admin_site)
                assigned_count += 1
        
        db.session.commit()
        
        if assigned_count > 0:
            flash(f'{assigned_count} sites atribuídos ao administrador {admin.username}.', 'success')
            logging.info(f"Sites assigned to admin {admin.username}: {assigned_count} sites")
        else:
            flash('Nenhum site válido selecionado.', 'warning')
            
    except Exception as e:
        logging.error(f"Error assigning sites: {str(e)}")
        flash('Erro ao atribuir sites.', 'error')
    
    return redirect(url_for('manage_admins'))

@app.route('/master/sync_sites', methods=['POST'])
@login_required
def sync_sites():
    if current_user.user_type != 'master':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        logging.info(f"Site synchronization started by {current_user.username}")
        success, message = sync_sites_from_omada()
        if success:
            flash(message, 'success')
            logging.info(f"Site synchronization completed successfully by {current_user.username}")
        else:
            flash(message, 'error')
            logging.error(f"Site synchronization failed: {message}")
    except Exception as e:
        error_msg = f"Erro durante a sincronização: {str(e)}"
        flash(error_msg, 'error')
        logging.error(f"Site synchronization error: {str(e)}")
    
    return redirect(url_for('master_dashboard'))

@app.route('/master/config', methods=['GET', 'POST'])
@login_required
def omada_config():
    if current_user.user_type != 'master':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    form = OmadaConfigForm()
    config = OmadaConfig.query.filter_by(is_active=True).first()
    
    if form.validate_on_submit():
        if config:
            # Update existing config
            config.controller_url = form.controller_url.data
            config.client_id = form.client_id.data
            config.client_secret = form.client_secret.data
            config.omadac_id = form.omadac_id.data
            config.updated_at = datetime.utcnow()
            # Clear existing tokens when config changes
            config.access_token = None
            config.refresh_token = None
            config.token_expires_at = None
        else:
            # Create new config
            config = OmadaConfig(
                controller_url=form.controller_url.data,
                client_id=form.client_id.data,
                client_secret=form.client_secret.data,
                omadac_id=form.omadac_id.data,
                is_active=True
            )
            db.session.add(config)
        
        db.session.commit()
        flash('Configuração do Omada Controller salva com sucesso.', 'success')
        return redirect(url_for('omada_config'))
    
    # Pre-populate form with existing config
    if config:
        form.controller_url.data = config.controller_url
        form.client_id.data = config.client_id
        form.client_secret.data = config.client_secret
        form.omadac_id.data = config.omadac_id
    
    return render_template('master/omada_config.html', form=form, config=config)

@app.route('/master/test_connection', methods=['POST'])
@login_required
def test_connection():
    if current_user.user_type != 'master':
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        # Get current configuration
        config = OmadaConfig.query.filter_by(is_active=True).first()
        if not config:
            return jsonify({'success': False, 'message': 'Configuração não encontrada. Salve a configuração primeiro.'})
        
        # Test connection using the Omada API
        token = omada_api.get_access_token()
        if token:
            # If successful, try to get sites to verify full API access
            sites = omada_api.get_sites(page=1, page_size=1)
            if sites is not None:
                return jsonify({'success': True, 'message': f'Conexão estabelecida com sucesso! Token obtido e API funcionando.'})
            else:
                return jsonify({'success': True, 'message': 'Token obtido, mas houve problema ao acessar os sites.'})
        else:
            return jsonify({'success': False, 'message': 'Falha na autenticação. Verifique suas credenciais.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro na conexão: {str(e)}'})

# Admin Routes
@app.route('/admin/site_selection')
@login_required
def admin_site_selection():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    admin_sites = AdminSite.query.filter_by(admin_id=current_user.id).all()
    
    # If admin has no sites, redirect to dashboard with message
    if not admin_sites:
        flash('Nenhum site foi atribuído a você. Entre em contato com o administrador master.', 'warning')
        return redirect(url_for('login'))
    
    # If admin has only one site, redirect directly to that site's dashboard
    if len(admin_sites) == 1:
        session['selected_site_id'] = admin_sites[0].site.id
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/site_selection.html', admin_sites=admin_sites)

@app.route('/admin/select_site/<int:site_id>')
@login_required
def select_site(site_id):
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    # Verify admin has access to this site
    admin_site = AdminSite.query.filter_by(admin_id=current_user.id, site_id=site_id).first()
    if not admin_site:
        flash('Acesso negado ao site.', 'error')
        return redirect(url_for('admin_site_selection'))
    
    # Store selected site in session
    session['selected_site_id'] = site_id
    flash(f'Site {admin_site.site.name} selecionado com sucesso.', 'success')
    logging.info(f"Admin {current_user.username} selected site {admin_site.site.name}")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    # Verify admin has access to this site
    admin_site = AdminSite.query.filter_by(admin_id=current_user.id, site_id=current_site_id).first()
    if not admin_site:
        flash('Acesso negado ao site.', 'error')
        return redirect(url_for('admin_site_selection'))
    
    # Get site information
    current_site = admin_site.site
    
    # Get all admin sites for potential site switching
    admin_sites = AdminSite.query.filter_by(admin_id=current_user.id).all()
    
    # Get statistics for current site
    total_vendors = User.query.join(VendorSite).filter(
        VendorSite.site_id == current_site_id,
        User.user_type == 'vendor'
    ).count()
    
    total_plans = VoucherPlan.query.filter_by(site_id=current_site_id, is_active=True).count()
    
    total_vouchers = db.session.query(db.func.sum(VoucherGroup.quantity)).filter(
        VoucherGroup.site_id == current_site_id
    ).scalar() or 0
    
    total_revenue = db.session.query(db.func.sum(VoucherGroup.total_value)).filter(
        VoucherGroup.site_id == current_site_id
    ).scalar() or 0
    
    # Recent voucher activity
    recent_vouchers = VoucherGroup.query.filter_by(site_id=current_site_id).order_by(
        VoucherGroup.created_at.desc()
    ).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         current_site=current_site,
                         admin_sites=admin_sites,
                         total_vendors=total_vendors,
                         total_plans=total_plans,
                         total_vouchers=total_vouchers,
                         total_revenue=total_revenue,
                         recent_vouchers=recent_vouchers)
    total_vendors = VendorSite.query.filter_by(site_id=current_site_id).count()
    total_plans = VoucherPlan.query.filter_by(site_id=current_site_id).count()
    total_vouchers = VoucherGroup.query.filter_by(site_id=current_site_id).count()
    
    # Sales data for current month
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_sales = generate_sales_report_data(current_site_id, start_of_month)
    
    return render_template('admin/dashboard.html', 
                         site=site,
                         total_vendors=total_vendors,
                         total_plans=total_plans,
                         total_vouchers=total_vouchers,
                         monthly_sales=monthly_sales)

@app.route('/admin/vendors')
@login_required
def manage_vendors():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('current_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    # Get vendors for current site
    vendor_sites = VendorSite.query.filter_by(site_id=current_site_id).all()
    vendors = [vs.vendor for vs in vendor_sites]
    
    return render_template('admin/manage_vendors.html', vendors=vendors, current_site_id=current_site_id)

@app.route('/admin/create_vendor', methods=['POST'])
@login_required
def create_vendor():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('current_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    form = UserForm()
    if form.validate_on_submit():
        # Check if username already exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Usuário já existe.', 'error')
            return redirect(url_for('manage_vendors'))
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            user_type='vendor',
            is_active=True
        )
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Assign vendor to current site
        vendor_site = VendorSite(vendor_id=user.id, site_id=current_site_id)
        db.session.add(vendor_site)
        db.session.commit()
        
        flash('Vendedor criado com sucesso.', 'success')
    else:
        flash('Erro ao criar vendedor.', 'error')
    
    return redirect(url_for('manage_vendors'))

@app.route('/admin/plans')
@login_required
def manage_plans():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('current_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    plans = VoucherPlan.query.filter_by(site_id=current_site_id).all()
    return render_template('admin/manage_plans.html', plans=plans)

@app.route('/admin/create_plan', methods=['POST'])
@login_required
def create_plan():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('current_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    form = VoucherPlanForm()
    if form.validate_on_submit():
        plan = VoucherPlan(
            site_id=current_site_id,
            name=form.name.data,
            duration=form.duration.data,
            duration_unit=form.duration_unit.data,
            price=form.price.data,
            data_quota=form.data_quota.data,
            download_speed=form.download_speed.data,
            upload_speed=form.upload_speed.data,
            is_active=form.is_active.data
        )
        db.session.add(plan)
        db.session.commit()
        
        flash('Plano criado com sucesso.', 'success')
    else:
        flash('Erro ao criar plano.', 'error')
    
    return redirect(url_for('manage_plans'))

@app.route('/admin/sales_reports')
@login_required
def admin_sales_reports():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('current_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    # Get date range from request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    sales_data = generate_sales_report_data(current_site_id, start_date, end_date)
    
    return render_template('admin/sales_reports.html', 
                         sales_data=sales_data,
                         start_date=start_date,
                         end_date=end_date)

# Vendor Routes
@app.route('/vendor')
@login_required
def vendor_dashboard():
    if current_user.user_type != 'vendor':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get vendor's site
    vendor_site = VendorSite.query.filter_by(vendor_id=current_user.id).first()
    if not vendor_site:
        flash('Nenhum site atribuído. Contate o administrador.', 'error')
        return redirect(url_for('login'))
    
    # Get statistics
    total_vouchers = VoucherGroup.query.filter_by(
        site_id=vendor_site.site_id,
        created_by_id=current_user.id
    ).count()
    
    # Sales data for current month
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_sales = generate_sales_report_data(vendor_site.site_id, start_of_month)
    
    # Filter only current vendor's sales
    vendor_monthly_sales = 0
    for vg in monthly_sales['voucher_groups']:
        if vg.created_by_id == current_user.id:
            vendor_monthly_sales += vg.total_value
    
    return render_template('vendor/dashboard.html', 
                         site=vendor_site.site,
                         total_vouchers=total_vouchers,
                         monthly_sales=vendor_monthly_sales)

@app.route('/vendor/create_vouchers')
@login_required
def create_vouchers():
    if current_user.user_type != 'vendor':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get vendor's site
    vendor_site = VendorSite.query.filter_by(vendor_id=current_user.id).first()
    if not vendor_site:
        flash('Nenhum site atribuído. Contate o administrador.', 'error')
        return redirect(url_for('login'))
    
    # Get available plans
    plans = VoucherPlan.query.filter_by(site_id=vendor_site.site_id, is_active=True).all()
    
    return render_template('vendor/create_vouchers.html', plans=plans, site=vendor_site.site)

@app.route('/vendor/generate_vouchers', methods=['POST'])
@login_required
def generate_vouchers():
    if current_user.user_type != 'vendor':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get vendor's site
    vendor_site = VendorSite.query.filter_by(vendor_id=current_user.id).first()
    if not vendor_site:
        flash('Nenhum site atribuído. Contate o administrador.', 'error')
        return redirect(url_for('login'))
    
    form = VoucherGenerationForm()
    if form.validate_on_submit():
        plan = VoucherPlan.query.get(form.plan_id.data)
        if not plan or plan.site_id != vendor_site.site_id:
            flash('Plano inválido.', 'error')
            return redirect(url_for('create_vouchers'))
        
        # Generate voucher codes (simple implementation)
        import random
        import string
        
        voucher_codes = []
        for _ in range(form.quantity.data):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            voucher_codes.append(code)
        
        # Create voucher group
        voucher_group = VoucherGroup(
            site_id=vendor_site.site_id,
            plan_id=plan.id,
            created_by_id=current_user.id,
            quantity=form.quantity.data,
            voucher_codes=voucher_codes,
            total_value=plan.price * form.quantity.data
        )
        
        db.session.add(voucher_group)
        db.session.commit()
        
        flash(f'{form.quantity.data} vouchers gerados com sucesso.', 'success')
        return redirect(url_for('voucher_history'))
    
    flash('Erro ao gerar vouchers.', 'error')
    return redirect(url_for('create_vouchers'))

@app.route('/vendor/voucher_history')
@login_required
def voucher_history():
    if current_user.user_type != 'vendor':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    voucher_groups = VoucherGroup.query.filter_by(created_by_id=current_user.id).order_by(VoucherGroup.created_at.desc()).all()
    
    return render_template('vendor/voucher_history.html', voucher_groups=voucher_groups)

@app.route('/vendor/download_vouchers/<int:voucher_group_id>')
@login_required
def download_vouchers(voucher_group_id):
    if current_user.user_type != 'vendor':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    voucher_group = VoucherGroup.query.get_or_404(voucher_group_id)
    
    # Verify ownership
    if voucher_group.created_by_id != current_user.id:
        flash('Acesso negado.', 'error')
        return redirect(url_for('voucher_history'))
    
    # Generate PDF
    pdf_data = generate_voucher_pdf(voucher_group, voucher_group.voucher_codes)
    
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=vouchers_{voucher_group_id}.pdf'
    
    return response

@app.route('/vendor/sales_reports')
@login_required
def vendor_sales_reports():
    if current_user.user_type != 'vendor':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get vendor's site
    vendor_site = VendorSite.query.filter_by(vendor_id=current_user.id).first()
    if not vendor_site:
        flash('Nenhum site atribuído. Contate o administrador.', 'error')
        return redirect(url_for('login'))
    
    # Get date range from request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Get vendor's voucher groups
    query = VoucherGroup.query.filter_by(
        site_id=vendor_site.site_id,
        created_by_id=current_user.id
    )
    
    if start_date:
        query = query.filter(VoucherGroup.created_at >= start_date)
    if end_date:
        query = query.filter(VoucherGroup.created_at <= end_date)
    
    voucher_groups = query.order_by(VoucherGroup.created_at.desc()).all()
    
    total_vouchers = sum(vg.quantity for vg in voucher_groups)
    total_revenue = sum(vg.total_value for vg in voucher_groups)
    
    return render_template('vendor/sales_reports.html', 
                         voucher_groups=voucher_groups,
                         total_vouchers=total_vouchers,
                         total_revenue=total_revenue,
                         start_date=start_date,
                         end_date=end_date)

# API endpoints for charts and data
@app.route('/api/sales_chart_data')
@login_required
def sales_chart_data():
    site_id = None
    
    if current_user.user_type == 'admin':
        site_id = session.get('current_site_id')
    elif current_user.user_type == 'vendor':
        vendor_site = VendorSite.query.filter_by(vendor_id=current_user.id).first()
        if vendor_site:
            site_id = vendor_site.site_id
    
    if not site_id:
        return jsonify({'error': 'Site não encontrado'}), 400
    
    # Get last 30 days data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Get daily sales
    daily_sales = {}
    voucher_groups = VoucherGroup.query.filter(
        VoucherGroup.site_id == site_id,
        VoucherGroup.created_at >= start_date
    ).all()
    
    for vg in voucher_groups:
        # Filter by vendor if user is vendor
        if current_user.user_type == 'vendor' and vg.created_by_id != current_user.id:
            continue
            
        date_key = vg.created_at.date().isoformat()
        if date_key not in daily_sales:
            daily_sales[date_key] = 0
        daily_sales[date_key] += vg.total_value
    
    # Fill missing dates with 0
    current_date = start_date.date()
    while current_date <= end_date.date():
        date_key = current_date.isoformat()
        if date_key not in daily_sales:
            daily_sales[date_key] = 0
        current_date += timedelta(days=1)
    
    # Sort by date
    sorted_sales = sorted(daily_sales.items())
    
    return jsonify({
        'labels': [item[0] for item in sorted_sales],
        'data': [item[1] for item in sorted_sales]
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('base.html', error_message='Página não encontrada'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('base.html', error_message='Erro interno do servidor'), 500

# Template filters
@app.template_filter('currency')
def currency_filter(value):
    return format_currency(value)

@app.template_filter('duration')
def duration_filter(value, unit):
    return format_duration(value, unit)
