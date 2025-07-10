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

@app.route('/admin/vendors')
@login_required
def manage_vendors():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    # Get current site
    current_site = Site.query.get(current_site_id)
    if not current_site:
        flash('Site não encontrado.', 'error')
        return redirect(url_for('admin_site_selection'))
    
    # Get vendors for current site with statistics
    vendors = db.session.query(
        User,
        db.func.sum(VoucherGroup.quantity).label('total_vouchers'),
        db.func.sum(VoucherGroup.total_value).label('total_revenue')
    ).outerjoin(VendorSite, User.id == VendorSite.vendor_id)\
     .outerjoin(VoucherGroup, User.id == VoucherGroup.created_by_id)\
     .filter(VendorSite.site_id == current_site_id)\
     .filter(User.user_type == 'vendor')\
     .group_by(User.id)\
     .all()
    
    return render_template('admin/manage_vendors.html', 
                         vendors=vendors, 
                         current_site=current_site)

@app.route('/admin/create_vendor', methods=['POST'])
@login_required
def create_vendor():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        site_id = request.form.get('site_id')
        
        # Validate required fields
        if not username or not email or not password or not site_id:
            flash('Todos os campos são obrigatórios.', 'error')
            return redirect(url_for('manage_vendors'))
        
        # Verify admin has access to this site
        admin_site = AdminSite.query.filter_by(admin_id=current_user.id, site_id=site_id).first()
        if not admin_site:
            flash('Acesso negado ao site.', 'error')
            return redirect(url_for('manage_vendors'))
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Usuário já existe.', 'error')
            return redirect(url_for('manage_vendors'))
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email já existe.', 'error')
            return redirect(url_for('manage_vendors'))
        
        # Create vendor user
        vendor = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            user_type='vendor',
            is_active=True
        )
        db.session.add(vendor)
        db.session.flush()  # Get the vendor ID
        
        # Assign vendor to site
        vendor_site = VendorSite(vendor_id=vendor.id, site_id=site_id)
        db.session.add(vendor_site)
        
        db.session.commit()
        
        flash(f'Vendedor {username} criado com sucesso.', 'success')
        logging.info(f"New vendor {username} created by admin {current_user.username} for site {admin_site.site.name}")
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating vendor: {str(e)}")
        flash('Erro ao criar vendedor.', 'error')
    
    return redirect(url_for('manage_vendors'))

@app.route('/admin/toggle_vendor_status', methods=['POST'])
@login_required
def toggle_vendor_status():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        vendor_id = request.form.get('vendor_id')
        status = request.form.get('status') == 'true'
        
        vendor = User.query.get(vendor_id)
        if not vendor or vendor.user_type != 'vendor':
            flash('Vendedor não encontrado.', 'error')
            return redirect(url_for('manage_vendors'))
        
        vendor.is_active = status
        db.session.commit()
        
        action = 'ativado' if status else 'desativado'
        flash(f'Vendedor {vendor.username} {action} com sucesso.', 'success')
        logging.info(f"Vendor {vendor.username} {action} by admin {current_user.username}")
        
    except Exception as e:
        logging.error(f"Error toggling vendor status: {str(e)}")
        flash('Erro ao alterar status do vendedor.', 'error')
    
    return redirect(url_for('manage_vendors'))

@app.route('/admin/plans')
@login_required
def manage_plans():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    # Get current site
    current_site = Site.query.get(current_site_id)
    if not current_site:
        flash('Site não encontrado.', 'error')
        return redirect(url_for('admin_site_selection'))
    
    # Get plans for current site with statistics
    plans = db.session.query(
        VoucherPlan,
        db.func.sum(VoucherGroup.quantity).label('total_vouchers'),
        db.func.sum(VoucherGroup.total_value).label('total_revenue')
    ).outerjoin(VoucherGroup, VoucherPlan.id == VoucherGroup.plan_id)\
     .filter(VoucherPlan.site_id == current_site_id)\
     .group_by(VoucherPlan.id)\
     .order_by(VoucherPlan.created_at.desc())\
     .all()
    
    return render_template('admin/manage_plans.html', 
                         plans=plans, 
                         current_site=current_site)

@app.route('/admin/create_plan', methods=['GET', 'POST'])
@login_required
def create_plan():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    # Get current site
    current_site = Site.query.get(current_site_id)
    if not current_site:
        flash('Site não encontrado.', 'error')
        return redirect(url_for('admin_site_selection'))
    
    form = VoucherPlanForm()
    
    if form.validate_on_submit():
        try:
            plan = VoucherPlan(
                site_id=current_site_id,
                name=form.name.data,
                duration=form.duration.data,
                duration_unit=form.duration_unit.data,
                price=form.price.data,
                data_quota=form.data_quota.data if form.data_quota.data else None,
                download_speed=form.download_speed.data if form.download_speed.data else None,
                upload_speed=form.upload_speed.data if form.upload_speed.data else None,
                is_active=form.is_active.data
            )
            
            db.session.add(plan)
            db.session.commit()
            
            flash(f'Plano {plan.name} criado com sucesso.', 'success')
            logging.info(f"New plan {plan.name} created by admin {current_user.username} for site {current_site.name}")
            return redirect(url_for('manage_plans'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating plan: {str(e)}")
            flash('Erro ao criar plano.', 'error')
    
    return render_template('admin/create_plan.html', 
                         form=form, 
                         current_site=current_site,
                         plan=None)

@app.route('/admin/edit_plan/<int:plan_id>', methods=['GET', 'POST'])
@login_required
def edit_plan(plan_id):
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    # Get current site
    current_site = Site.query.get(current_site_id)
    if not current_site:
        flash('Site não encontrado.', 'error')
        return redirect(url_for('admin_site_selection'))
    
    # Get plan and verify it belongs to current site
    plan = VoucherPlan.query.filter_by(id=plan_id, site_id=current_site_id).first()
    if not plan:
        flash('Plano não encontrado.', 'error')
        return redirect(url_for('manage_plans'))
    
    form = VoucherPlanForm(obj=plan)
    
    if form.validate_on_submit():
        try:
            plan.name = form.name.data
            plan.duration = form.duration.data
            plan.duration_unit = form.duration_unit.data
            plan.price = form.price.data
            plan.data_quota = form.data_quota.data if form.data_quota.data else None
            plan.download_speed = form.download_speed.data if form.download_speed.data else None
            plan.upload_speed = form.upload_speed.data if form.upload_speed.data else None
            plan.is_active = form.is_active.data
            
            db.session.commit()
            
            flash(f'Plano {plan.name} atualizado com sucesso.', 'success')
            logging.info(f"Plan {plan.name} updated by admin {current_user.username}")
            return redirect(url_for('manage_plans'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating plan: {str(e)}")
            flash('Erro ao atualizar plano.', 'error')
    
    # Get plan statistics
    plan.total_vouchers = db.session.query(db.func.sum(VoucherGroup.quantity)).filter(
        VoucherGroup.plan_id == plan.id
    ).scalar() or 0
    
    plan.total_revenue = db.session.query(db.func.sum(VoucherGroup.total_value)).filter(
        VoucherGroup.plan_id == plan.id
    ).scalar() or 0
    
    return render_template('admin/create_plan.html', 
                         form=form, 
                         current_site=current_site,
                         plan=plan)

@app.route('/admin/toggle_plan_status', methods=['POST'])
@login_required
def toggle_plan_status():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        plan_id = request.form.get('plan_id')
        status = request.form.get('status') == 'true'
        current_site_id = session.get('selected_site_id')
        
        plan = VoucherPlan.query.filter_by(id=plan_id, site_id=current_site_id).first()
        if not plan:
            flash('Plano não encontrado.', 'error')
            return redirect(url_for('manage_plans'))
        
        plan.is_active = status
        db.session.commit()
        
        action = 'ativado' if status else 'desativado'
        flash(f'Plano {plan.name} {action} com sucesso.', 'success')
        logging.info(f"Plan {plan.name} {action} by admin {current_user.username}")
        
    except Exception as e:
        logging.error(f"Error toggling plan status: {str(e)}")
        flash('Erro ao alterar status do plano.', 'error')
    
    return redirect(url_for('manage_plans'))

# Sales Reports
@app.route('/admin/sales_reports')
@login_required
def admin_sales_reports():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    # Get current site
    current_site = Site.query.get(current_site_id)
    if not current_site:
        flash('Site não encontrado.', 'error')
        return redirect(url_for('admin_site_selection'))
    
    # Get date range from request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Get sales data
    query = VoucherGroup.query.filter_by(site_id=current_site_id)
    
    if start_date:
        query = query.filter(VoucherGroup.created_at >= start_date)
    if end_date:
        query = query.filter(VoucherGroup.created_at <= end_date)
    
    voucher_groups = query.order_by(VoucherGroup.created_at.desc()).all()
    
    # Calculate totals
    total_vouchers = sum(vg.quantity for vg in voucher_groups)
    total_revenue = sum(vg.total_value for vg in voucher_groups)
    
    # Group by vendor
    vendor_stats = {}
    for vg in voucher_groups:
        vendor_id = vg.created_by_id
        if vendor_id not in vendor_stats:
            vendor_stats[vendor_id] = {
                'vendor': vg.created_by,
                'vouchers': 0,
                'revenue': 0
            }
        vendor_stats[vendor_id]['vouchers'] += vg.quantity
        vendor_stats[vendor_id]['revenue'] += vg.total_value
    
    return render_template('admin/sales_reports.html',
                         current_site=current_site,
                         voucher_groups=voucher_groups,
                         vendor_stats=vendor_stats,
                         total_vouchers=total_vouchers,
                         total_revenue=total_revenue,
                         start_date=start_date,
                         end_date=end_date)

# Vendor Routes
@app.route('/vendor')
@login_required
def vendor_dashboard():
    if current_user.user_type != 'vendor':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    vendor_site = VendorSite.query.filter_by(vendor_id=current_user.id).first()
    if not vendor_site:
        flash('Nenhum site atribuído.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get available plans for this site
    plans = VoucherPlan.query.filter_by(site_id=vendor_site.site_id, is_active=True).all()
    
    # Get vendor statistics
    total_vouchers = db.session.query(db.func.sum(VoucherGroup.quantity)).filter(
        VoucherGroup.created_by_id == current_user.id
    ).scalar() or 0
    
    total_revenue = db.session.query(db.func.sum(VoucherGroup.total_value)).filter(
        VoucherGroup.created_by_id == current_user.id
    ).scalar() or 0
    
    recent_vouchers = VoucherGroup.query.filter_by(created_by_id=current_user.id).order_by(
        VoucherGroup.created_at.desc()
    ).limit(10).all()
    
    return render_template('vendor/dashboard.html',
                         site=vendor_site.site,
                         plans=plans,
                         total_vouchers=total_vouchers,
                         total_revenue=total_revenue,
                         recent_vouchers=recent_vouchers)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# Template filters
@app.template_filter('currency')
def currency_filter(value):
    return format_currency(value or 0)

@app.template_filter('duration')
def duration_filter(value, unit):
    return format_duration(value, unit)
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
