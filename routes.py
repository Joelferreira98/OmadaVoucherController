from flask import render_template, request, redirect, url_for, flash, jsonify, make_response, session, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import logging

from app import app, db, login_manager
from models import User, Site, AdminSite, VendorSite, VoucherPlan, VoucherGroup, OmadaConfig, CashRegister
from forms import (LoginForm, UserForm, VoucherPlanForm, VoucherGenerationForm, 
                  OmadaConfigForm, CashRegisterForm, UserEditForm, 
                  ChangePasswordForm, AdminChangePasswordForm, VoucherGroupEditForm,
                  ImportVoucherGroupsForm)
from utils import generate_voucher_pdf, format_currency, format_duration, generate_sales_report_data, sync_sites_from_omada, sync_voucher_statuses_from_omada, has_permission, check_site_access, get_accessible_sites, can_manage_user, get_vendor_site_for_user
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
        if user and user.password_hash and check_password_hash(user.password_hash, form.password.data) and user.is_active:
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
                    session['selected_site_id'] = admin_sites[0].site_id
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

# Generic User Routes
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page with password change functionality"""
    from forms import ChangePasswordForm
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if not current_user.password_hash or not check_password_hash(current_user.password_hash, form.current_password.data):
            flash('Senha atual incorreta.', 'error')
            return render_template('profile.html', form=form, user=current_user)
        
        if form.new_password.data != form.confirm_password.data:
            flash('Nova senha e confirmação não coincidem.', 'error')
            return render_template('profile.html', form=form, user=current_user)
        
        try:
            current_user.password_hash = generate_password_hash(form.new_password.data) if form.new_password.data else None
            db.session.commit()
            flash('Senha alterada com sucesso.', 'success')
            logging.info(f"Password changed for user {current_user.username}")
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao alterar senha.', 'error')
            logging.error(f"Error changing password for user {current_user.id}: {str(e)}")
    
    return render_template('profile.html', form=form, user=current_user)

# Master Routes
@app.route('/master')
@login_required
def master_dashboard():
    # Only masters can access this - hierarchical permission
    if not has_permission('master'):
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
        count = sync_sites_from_omada()
        message = f"Sincronização concluída! {count} sites processados."
        flash(message, 'success')
        logging.info(f"Site synchronization completed: {count} sites by {current_user.username}")
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

# User CRUD Routes for Master
@app.route('/master/edit_admin/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_admin(user_id):
    if current_user.user_type != 'master':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.user_type != 'admin':
        flash('Usuário não é um administrador.', 'error')
        return redirect(url_for('manage_admins'))
    
    from forms import UserEditForm
    form = UserEditForm()
    
    if form.validate_on_submit():
        try:
            # Check if username exists for another user
            existing_user = User.query.filter(User.username == form.username.data, User.id != user_id).first()
            if existing_user:
                flash('Nome de usuário já existe.', 'error')
                return render_template('master/edit_admin.html', form=form, user=user)
            
            # Check if email exists for another user
            existing_email = User.query.filter(User.email == form.email.data, User.id != user_id).first()
            if existing_email:
                flash('Email já existe.', 'error')
                return render_template('master/edit_admin.html', form=form, user=user)
            
            user.username = form.username.data
            user.email = form.email.data
            user.user_type = form.user_type.data
            user.is_active = form.is_active.data
            
            db.session.commit()
            flash(f'Administrador {user.username} atualizado com sucesso.', 'success')
            return redirect(url_for('manage_admins'))
            
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar administrador.', 'error')
            logging.error(f"Error updating admin {user_id}: {str(e)}")
    
    # Pre-populate form
    form.username.data = user.username
    form.email.data = user.email
    form.user_type.data = user.user_type
    form.is_active.data = user.is_active
    
    return render_template('master/edit_admin.html', form=form, user=user)

@app.route('/master/delete_admin/<int:user_id>', methods=['POST'])
@login_required
def delete_admin(user_id):
    if current_user.user_type != 'master':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.user_type != 'admin':
        flash('Usuário não é um administrador.', 'error')
        return redirect(url_for('manage_admins'))
    
    try:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f'Administrador {username} removido com sucesso.', 'success')
        logging.info(f"Admin {username} deleted by {current_user.username}")
    except Exception as e:
        db.session.rollback()
        flash('Erro ao remover administrador.', 'error')
        logging.error(f"Error deleting admin {user_id}: {str(e)}")
    
    return redirect(url_for('manage_admins'))

@app.route('/master/change_admin_password/<int:user_id>', methods=['GET', 'POST'])
@login_required  
def change_admin_password(user_id):
    if current_user.user_type != 'master':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.user_type != 'admin':
        flash('Usuário não é um administrador.', 'error')
        return redirect(url_for('manage_admins'))
    
    from forms import AdminChangePasswordForm
    form = AdminChangePasswordForm()
    
    if form.validate_on_submit():
        if form.new_password.data != form.confirm_password.data:
            flash('Nova senha e confirmação não coincidem.', 'error')
            return render_template('master/change_admin_password.html', form=form, user=user)
        
        try:
            user.password_hash = generate_password_hash(form.new_password.data) if form.new_password.data else None
            db.session.commit()
            flash(f'Senha do administrador {user.username} alterada com sucesso.', 'success')
            logging.info(f"Password changed for admin {user.username} by {current_user.username}")
            return redirect(url_for('manage_admins'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao alterar senha.', 'error')
            logging.error(f"Error changing password for admin {user_id}: {str(e)}")
    
    return render_template('master/change_admin_password.html', form=form, user=user)

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
    # Admin or Master can access - hierarchical permission
    if not has_permission('admin'):
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
    
    # Calculate vouchers generated vs sold
    total_vouchers_generated = db.session.query(db.func.sum(VoucherGroup.quantity)).filter(
        VoucherGroup.site_id == current_site_id
    ).scalar() or 0
    
    # Calculate vouchers actually sold (used + expired)
    total_vouchers_sold = db.session.query(
        db.func.sum((VoucherGroup.used_count or 0) + (VoucherGroup.expired_count or 0))
    ).filter(VoucherGroup.site_id == current_site_id).scalar() or 0
    
    # Calculate revenue based on sold vouchers
    voucher_groups = VoucherGroup.query.filter_by(site_id=current_site_id).all()
    total_revenue = sum(
        ((vg.used_count or 0) + (vg.expired_count or 0)) * vg.plan.price 
        for vg in voucher_groups
    )
    
    # Recent voucher activity
    recent_vouchers = VoucherGroup.query.filter_by(site_id=current_site_id).order_by(
        VoucherGroup.created_at.desc()
    ).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         current_site=current_site,
                         admin_sites=admin_sites,
                         total_vendors=total_vendors,
                         total_plans=total_plans,
                         total_vouchers_generated=total_vouchers_generated,
                         total_vouchers_sold=total_vouchers_sold,
                         total_revenue=total_revenue,
                         recent_vouchers=recent_vouchers)

@app.route('/admin/vendors')
@login_required
def manage_vendors():
    # Admin or Master can manage vendors - hierarchical permission
    if not has_permission('admin'):
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
    # Admin or Master can create vendors - hierarchical permission
    if not has_permission('admin'):
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

# Vendor CRUD Routes for Admins
@app.route('/admin/edit_vendor/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_vendor(user_id):
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    user = User.query.get_or_404(user_id)
    if user.user_type != 'vendor':
        flash('Usuário não é um vendedor.', 'error')
        return redirect(url_for('manage_vendors'))
    
    # Verify vendor belongs to current site
    vendor_site = VendorSite.query.filter_by(vendor_id=user_id, site_id=current_site_id).first()
    if not vendor_site:
        flash('Vendedor não pertence ao site atual.', 'error')
        return redirect(url_for('manage_vendors'))
    
    from forms import UserEditForm
    form = UserEditForm()
    
    if form.validate_on_submit():
        try:
            # Check if username exists for another user
            existing_user = User.query.filter(User.username == form.username.data, User.id != user_id).first()
            if existing_user:
                flash('Nome de usuário já existe.', 'error')
                return render_template('admin/edit_vendor.html', form=form, user=user)
            
            # Check if email exists for another user
            existing_email = User.query.filter(User.email == form.email.data, User.id != user_id).first()
            if existing_email:
                flash('Email já existe.', 'error')
                return render_template('admin/edit_vendor.html', form=form, user=user)
            
            user.username = form.username.data
            user.email = form.email.data
            user.is_active = form.is_active.data
            
            db.session.commit()
            flash(f'Vendedor {user.username} atualizado com sucesso.', 'success')
            return redirect(url_for('manage_vendors'))
            
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar vendedor.', 'error')
            logging.error(f"Error updating vendor {user_id}: {str(e)}")
    
    # Pre-populate form
    form.username.data = user.username
    form.email.data = user.email
    form.user_type.data = user.user_type
    form.is_active.data = user.is_active
    
    return render_template('admin/edit_vendor.html', form=form, user=user)

@app.route('/admin/delete_vendor/<int:user_id>', methods=['POST'])
@login_required
def delete_vendor(user_id):
    # Admin or Master can delete vendors - hierarchical permission
    if not has_permission('admin'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    user = User.query.get_or_404(user_id)
    if user.user_type != 'vendor':
        flash('Usuário não é um vendedor.', 'error')
        return redirect(url_for('manage_vendors'))
    
    # Verify vendor belongs to current site
    vendor_site = VendorSite.query.filter_by(vendor_id=user_id, site_id=current_site_id).first()
    if not vendor_site:
        flash('Vendedor não pertence ao site atual.', 'error')
        return redirect(url_for('manage_vendors'))
    
    try:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f'Vendedor {username} removido com sucesso.', 'success')
        logging.info(f"Vendor {username} deleted by admin {current_user.username}")
    except Exception as e:
        db.session.rollback()
        flash('Erro ao remover vendedor.', 'error')
        logging.error(f"Error deleting vendor {user_id}: {str(e)}")
    
    return redirect(url_for('manage_vendors'))

@app.route('/admin/change_vendor_password/<int:user_id>', methods=['GET', 'POST'])
@login_required
def change_vendor_password(user_id):
    # Admin or Master can change vendor passwords - hierarchical permission
    if not has_permission('admin'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    user = User.query.get_or_404(user_id)
    if user.user_type != 'vendor':
        flash('Usuário não é um vendedor.', 'error')
        return redirect(url_for('manage_vendors'))
    
    # Verify vendor belongs to current site
    vendor_site = VendorSite.query.filter_by(vendor_id=user_id, site_id=current_site_id).first()
    if not vendor_site:
        flash('Vendedor não pertence ao site atual.', 'error')
        return redirect(url_for('manage_vendors'))
    
    from forms import AdminChangePasswordForm
    form = AdminChangePasswordForm()
    
    if form.validate_on_submit():
        if form.new_password.data != form.confirm_password.data:
            flash('Nova senha e confirmação não coincidem.', 'error')
            return render_template('admin/change_vendor_password.html', form=form, user=user)
        
        try:
            user.password_hash = generate_password_hash(form.new_password.data) if form.new_password.data else None
            db.session.commit()
            flash(f'Senha do vendedor {user.username} alterada com sucesso.', 'success')
            logging.info(f"Password changed for vendor {user.username} by admin {current_user.username}")
            return redirect(url_for('manage_vendors'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao alterar senha.', 'error')
            logging.error(f"Error changing password for vendor {user_id}: {str(e)}")
    
    return render_template('admin/change_vendor_password.html', form=form, user=user)

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
    
    # Get plans for current site
    plans = VoucherPlan.query.filter_by(site_id=current_site_id).order_by(VoucherPlan.created_at.desc()).all()
    
    # Add statistics to each plan
    for plan in plans:
        plan.total_vouchers = db.session.query(db.func.sum(VoucherGroup.quantity)).filter(
            VoucherGroup.plan_id == plan.id
        ).scalar() or 0
        
        plan.total_revenue = db.session.query(db.func.sum(VoucherGroup.total_value)).filter(
            VoucherGroup.plan_id == plan.id
        ).scalar() or 0
    
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
                code_length=form.code_length.data,
                limit_type=form.limit_type.data,
                limit_num=form.limit_num.data if form.limit_type.data != 2 else None,
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
            plan.code_length = form.code_length.data
            plan.limit_type = form.limit_type.data
            plan.limit_num = form.limit_num.data if form.limit_type.data != 2 else None
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

# Sales Reports - Individual Vouchers
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
    
    # Get voucher groups first
    query = VoucherGroup.query.filter_by(site_id=current_site_id)
    
    if start_date:
        query = query.filter(VoucherGroup.created_at >= start_date)
    if end_date:
        query = query.filter(VoucherGroup.created_at <= end_date)
    
    voucher_groups = query.order_by(VoucherGroup.created_at.desc()).all()
    
    # Get individual voucher data from Omada Controller
    sold_vouchers = []  # Vouchers that are expired or in-use
    from omada_api import omada_api
    
    try:
        for vg in voucher_groups:
            if vg.omada_group_id:
                # Get detailed voucher data from Omada Controller
                group_details = omada_api.get_voucher_group_detail(current_site.site_id, vg.omada_group_id)
                
                if group_details and group_details.get('errorCode') == 0:
                    voucher_data_list = group_details.get('result', {}).get('data', [])
                    
                    for voucher in voucher_data_list:
                        # Only include vouchers that are expired or in-use (sold)
                        status = voucher.get('status', 0)
                        if status in [2, 3]:  # 2 = in-use, 3 = expired
                            sold_vouchers.append({
                                'code': voucher.get('code', 'N/A'),
                                'status': 'Em Uso' if status == 2 else 'Expirado',
                                'status_class': 'warning' if status == 2 else 'danger',
                                'plan_name': vg.plan.name,
                                'plan_price': vg.plan.price,
                                'created_by': vg.created_by.username,
                                'created_at': vg.created_at,
                                'group_id': vg.id,
                                'usage_time': voucher.get('usageTime', 0) if status == 2 else voucher.get('duration', 0),
                                'start_time': voucher.get('startTime'),
                                'end_time': voucher.get('endTime')
                            })
    
    except Exception as e:
        logging.error(f"Error fetching individual voucher data: {str(e)}")
        flash('Erro ao carregar dados dos vouchers do Omada Controller.', 'warning')
    
    # Calculate totals based on sold vouchers
    total_sold_vouchers = len(sold_vouchers)
    total_revenue = sum(voucher['plan_price'] for voucher in sold_vouchers)
    
    # Group by vendor
    vendor_stats = {}
    for voucher in sold_vouchers:
        vendor_name = voucher['created_by']
        if vendor_name not in vendor_stats:
            vendor_stats[vendor_name] = {
                'vendor_name': vendor_name,
                'vouchers': 0,
                'revenue': 0.0
            }
        vendor_stats[vendor_name]['vouchers'] += 1
        vendor_stats[vendor_name]['revenue'] += voucher['plan_price']
    
    # Group by plan
    plan_stats = {}
    for voucher in sold_vouchers:
        plan_name = voucher['plan_name']
        if plan_name not in plan_stats:
            plan_stats[plan_name] = {
                'plan_name': plan_name,
                'vouchers': 0,
                'revenue': 0.0
            }
        plan_stats[plan_name]['vouchers'] += 1
        plan_stats[plan_name]['revenue'] += voucher['plan_price']
    
    return render_template('admin/sales_reports.html',
                         current_site=current_site,
                         sold_vouchers=sold_vouchers,
                         vendor_stats=vendor_stats,
                         plan_stats=plan_stats,
                         total_sold_vouchers=total_sold_vouchers,
                         total_revenue=total_revenue,
                         start_date=start_date,
                         end_date=end_date)

# Admin Voucher Management (same as vendor functions)
@app.route('/admin/create_vouchers')
@login_required
def admin_create_vouchers():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    current_site = Site.query.get(current_site_id)
    if not current_site:
        flash('Site não encontrado.', 'error')
        return redirect(url_for('admin_site_selection'))
    
    # Get available plans
    plans = VoucherPlan.query.filter_by(site_id=current_site_id, is_active=True).all()
    
    # Create form and populate plan choices
    form = VoucherGenerationForm()
    form.plan_id.choices = [(plan.id, f"{plan.name} - R$ {plan.price:.2f}".replace('.', ',')) for plan in plans]
    
    # Pre-select plan if provided in URL
    plan_id = request.args.get('plan_id')
    if plan_id:
        form.plan_id.data = int(plan_id)
    
    return render_template('admin/create_vouchers.html', 
                         form=form, 
                         plans=plans, 
                         site=current_site)

@app.route('/admin/generate_vouchers', methods=['POST'])
@login_required
def admin_generate_vouchers():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    form = VoucherGenerationForm()
    plans = VoucherPlan.query.filter_by(site_id=current_site_id, is_active=True).all()
    form.plan_id.choices = [(plan.id, f"{plan.name} - R$ {plan.price:.2f}".replace('.', ',')) for plan in plans]
    
    if form.validate_on_submit():
        try:
            plan = VoucherPlan.query.filter_by(id=form.plan_id.data, site_id=current_site_id).first()
            if not plan:
                flash('Plano não encontrado.', 'error')
                return redirect(url_for('admin_create_vouchers'))
            
            site = Site.query.get(current_site_id)
            if not site:
                flash('Site não encontrado.', 'error')
                return redirect(url_for('admin_create_vouchers'))
            
            # Convert duration to minutes for Omada API
            duration_minutes = plan.duration
            if plan.duration_unit == 'hours':
                duration_minutes = plan.duration * 60
            elif plan.duration_unit == 'days':
                duration_minutes = plan.duration * 24 * 60
            
            # Prepare voucher data for Omada API following exact vendor specification
            voucher_data = {
                "name": f"{plan.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "amount": form.quantity.data,
                "codeLength": plan.code_length,
                "codeForm": [0],  # Always use numbers only
                "limitType": plan.limit_type,
                "durationType": 0,  # Client duration
                "duration": duration_minutes,
                "timingType": 0,  # Timing by time
                "rateLimit": {
                    "mode": 0,  # Custom rate limit
                    "customRateLimit": {
                        "downLimitEnable": bool(plan.download_speed),
                        "downLimit": (plan.download_speed * 1024) if plan.download_speed else 0,  # Convert Mbps to Kbps
                        "upLimitEnable": bool(plan.upload_speed),
                        "upLimit": (plan.upload_speed * 1024) if plan.upload_speed else 0  # Convert Mbps to Kbps
                    }
                },
                "trafficLimitEnable": bool(plan.data_quota),
                "applyToAllPortals": True,
                "logout": True,
                "description": f"Vouchers gerados por {current_user.username}",
                "printComments": f"Plano: {plan.name}",
                "validityType": 0  # Can be used at any time
            }
            
            # Add optional fields only if they have values
            if plan.limit_type != 2 and plan.limit_num:
                voucher_data["limitNum"] = plan.limit_num
            
            if plan.data_quota:
                voucher_data["trafficLimit"] = plan.data_quota
                voucher_data["trafficLimitFrequency"] = 0  # Total
            
            # Create voucher group in Omada Controller
            from omada_api import omada_api
            result = omada_api.create_voucher_group(site.site_id, voucher_data)
            
            if result and result.get('errorCode') == 0:
                omada_group_id = result.get('result', {}).get('id')
                
                # Create database record
                voucher_group = VoucherGroup(
                    site_id=current_site_id,
                    plan_id=plan.id,
                    created_by_id=current_user.id,
                    quantity=form.quantity.data,
                    omada_group_id=omada_group_id,
                    total_value=form.quantity.data * plan.price,
                    unused_count=form.quantity.data,
                    used_count=0,
                    in_use_count=0,
                    expired_count=0,
                    status='generated'
                )
                db.session.add(voucher_group)
                db.session.commit()
                
                # Try to get real voucher codes after a short delay
                import time
                time.sleep(2)
                sync_voucher_statuses_from_omada(current_site_id)
                
                flash(f'{form.quantity.data} vouchers criados com sucesso!', 'success')
                logging.info(f"Admin {current_user.username} created {form.quantity.data} vouchers for plan {plan.name}")
                
                # Redirect to format selection page after successful generation
                return redirect(url_for('choose_print_format', voucher_group_id=voucher_group.id))
            else:
                error_msg = result.get('msg', 'Erro desconhecido') if result else 'Falha na comunicação'
                flash(f'Erro ao criar vouchers: {error_msg}', 'error')
                logging.error(f"Failed to create vouchers for admin {current_user.username}: {error_msg}")
        
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error generating vouchers for admin {current_user.username}: {str(e)}")
            flash('Erro ao gerar vouchers.', 'error')
    
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Erro no campo {field}: {error}', 'error')
    
    return redirect(url_for('admin_create_vouchers'))

@app.route('/admin/voucher_history')
@login_required
def admin_voucher_history():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    current_site = Site.query.get(current_site_id)
    if not current_site:
        flash('Site não encontrado.', 'error')
        return redirect(url_for('admin_site_selection'))
    
    # Get all voucher groups for the site
    voucher_groups = VoucherGroup.query.filter_by(site_id=current_site_id).order_by(
        VoucherGroup.created_at.desc()
    ).all()
    
    return render_template('admin/voucher_history.html', 
                         voucher_groups=voucher_groups, 
                         site=current_site)

# Cash Register Management
@app.route('/admin/cash_register')
@login_required
def cash_register():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    current_site = Site.query.get(current_site_id)
    if not current_site:
        flash('Site não encontrado.', 'error')
        return redirect(url_for('admin_site_selection'))
    
    # Get last cash register closing
    last_closing = CashRegister.query.filter_by(site_id=current_site_id).order_by(
        CashRegister.period_end.desc()
    ).first()
    
    # Determine period start
    period_start = last_closing.period_end if last_closing else datetime(2020, 1, 1)
    period_end = datetime.now()
    
    # Get voucher groups in this period
    voucher_groups = VoucherGroup.query.filter(
        VoucherGroup.site_id == current_site_id,
        VoucherGroup.created_at >= period_start,
        VoucherGroup.created_at <= period_end
    ).all()
    
    # Calculate statistics - vouchers sold include: used, in_use, and expired
    total_generated = sum(vg.quantity for vg in voucher_groups)
    total_sold = sum((vg.used_count or 0) + (vg.in_use_count or 0) + (vg.expired_count or 0) for vg in voucher_groups)
    total_expired = sum(vg.expired_count or 0 for vg in voucher_groups)
    total_unused = sum(vg.unused_count or 0 for vg in voucher_groups)
    total_revenue = sum(((vg.used_count or 0) + (vg.in_use_count or 0) + (vg.expired_count or 0)) * vg.plan.price for vg in voucher_groups)
    
    # Get groups with expired vouchers
    groups_with_expired = [vg for vg in voucher_groups if (vg.expired_count or 0) > 0]
    
    form = CashRegisterForm()
    
    return render_template('admin/cash_register.html',
                         current_site=current_site,
                         period_start=period_start,
                         period_end=period_end,
                         voucher_groups=voucher_groups,
                         groups_with_expired=groups_with_expired,
                         total_generated=total_generated,
                         total_sold=total_sold,
                         total_expired=total_expired,
                         total_unused=total_unused,
                         total_revenue=total_revenue,
                         last_closing=last_closing,
                         form=form)

@app.route('/admin/close_cash_register', methods=['POST'])
@login_required
def close_cash_register():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    try:
        form = CashRegisterForm()
        if not form.validate_on_submit():
            flash('Dados inválidos.', 'error')
            return redirect(url_for('cash_register'))
        
        site = Site.query.get(current_site_id)
        if not site:
            flash('Site não encontrado.', 'error')
            return redirect(url_for('cash_register'))
        
        # Get last cash register closing
        last_closing = CashRegister.query.filter_by(site_id=current_site_id).order_by(
            CashRegister.period_end.desc()
        ).first()
        
        # Determine period
        period_start = last_closing.period_end if last_closing else datetime(2020, 1, 1)
        period_end = datetime.now()
        
        # Get voucher groups in this period
        voucher_groups = VoucherGroup.query.filter(
            VoucherGroup.site_id == current_site_id,
            VoucherGroup.created_at >= period_start,
            VoucherGroup.created_at <= period_end
        ).all()
        
        # Calculate statistics - vouchers sold include: used, in_use, and expired  
        total_generated = sum(vg.quantity for vg in voucher_groups)
        total_sold = sum((vg.used_count or 0) + (vg.in_use_count or 0) + (vg.expired_count or 0) for vg in voucher_groups)
        total_expired = sum(vg.expired_count or 0 for vg in voucher_groups)
        total_unused = sum(vg.unused_count or 0 for vg in voucher_groups)
        total_revenue = sum(((vg.used_count or 0) + (vg.in_use_count or 0) + (vg.expired_count or 0)) * vg.plan.price for vg in voucher_groups)
        
        # Remove expired vouchers if requested
        expired_removed = False
        if form.remove_expired.data:
            from omada_api import omada_api
            groups_with_expired = [vg for vg in voucher_groups if (vg.expired_count or 0) > 0]
            
            for vg in groups_with_expired:
                if vg.omada_group_id:
                    result = omada_api.delete_expired_vouchers(site.site_id, vg.omada_group_id)
                    if result and result.get('errorCode') == 0:
                        logging.info(f"Deleted expired vouchers for group {vg.omada_group_id}")
                        expired_removed = True
                    else:
                        logging.warning(f"Failed to delete expired vouchers for group {vg.omada_group_id}")
        
        # Create cash register record
        cash_register = CashRegister(
            site_id=current_site_id,
            closed_by_id=current_user.id,
            period_start=period_start,
            period_end=period_end,
            vouchers_generated=total_generated,
            vouchers_sold=total_sold,
            vouchers_expired=total_expired,
            vouchers_unused=total_unused,
            total_revenue=total_revenue,
            expired_vouchers_removed=expired_removed,
            voucher_groups_data=[{
                'id': vg.id,
                'plan_name': vg.plan.name,
                'quantity': vg.quantity,
                'unused_count': vg.unused_count or 0,
                'used_count': vg.used_count or 0,
                'in_use_count': vg.in_use_count or 0,
                'expired_count': vg.expired_count or 0,
                'total_value': ((vg.used_count or 0) + (vg.in_use_count or 0) + (vg.expired_count or 0)) * vg.plan.price,
                'created_at': vg.created_at.isoformat(),
                'created_by': vg.created_by.username
            } for vg in voucher_groups],
            notes=form.notes.data
        )
        
        db.session.add(cash_register)
        db.session.commit()
        
        flash(f'Caixa fechado com sucesso! Receita: R$ {total_revenue:.2f}'.replace('.', ','), 'success')
        logging.info(f"Cash register closed by {current_user.username} for site {site.name} - Revenue: R$ {total_revenue:.2f}")
        
        return redirect(url_for('cash_register_history'))
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error closing cash register: {str(e)}")
        flash('Erro ao fechar caixa.', 'error')
        return redirect(url_for('cash_register'))

@app.route('/admin/cash_register_history')
@login_required
def cash_register_history():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    current_site = Site.query.get(current_site_id)
    if not current_site:
        flash('Site não encontrado.', 'error')
        return redirect(url_for('admin_site_selection'))
    
    # Get cash register records
    cash_registers = CashRegister.query.filter_by(site_id=current_site_id).order_by(
        CashRegister.period_end.desc()
    ).all()
    
    return render_template('admin/cash_register_history.html',
                         current_site=current_site,
                         cash_registers=cash_registers)

# Vendor Routes
@app.route('/vendor')
@app.route('/vendor/dashboard')
@login_required
def vendor_dashboard():
    # Vendor, Admin or Master can access - hierarchical permission
    if not has_permission('vendor'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get vendor site - supporting hierarchical access
    vendor_site = get_vendor_site_for_user()
    if not vendor_site:
        if current_user.user_type in ['admin', 'master']:
            flash('Selecione um site no dashboard de administrador primeiro.', 'warning')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Nenhum site atribuído. Contate o administrador.', 'error')
            return redirect(url_for('dashboard'))
    
    # Get available plans for this site
    plans = VoucherPlan.query.filter_by(site_id=vendor_site.site_id, is_active=True).all()
    
    # Get site statistics - all vouchers for the site (not just created by current user)
    total_vouchers_generated = db.session.query(db.func.sum(VoucherGroup.quantity)).filter(
        VoucherGroup.site_id == vendor_site.site_id
    ).scalar() or 0
    
    # Calculate vouchers actually sold (used + expired) for all site vouchers
    voucher_groups = VoucherGroup.query.filter_by(site_id=vendor_site.site_id).all()
    total_vouchers_sold = sum((vg.used_count or 0) + (vg.expired_count or 0) for vg in voucher_groups)
    total_revenue = sum(((vg.used_count or 0) + (vg.expired_count or 0)) * vg.plan.price for vg in voucher_groups)
    
    # Monthly sales based on sold vouchers for the site
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_voucher_groups = VoucherGroup.query.filter(
        VoucherGroup.site_id == vendor_site.site_id,
        VoucherGroup.created_at >= start_of_month
    ).all()
    monthly_sales = sum(((vg.used_count or 0) + (vg.expired_count or 0)) * vg.plan.price for vg in monthly_voucher_groups)
    
    recent_vouchers = VoucherGroup.query.filter_by(site_id=vendor_site.site_id).order_by(
        VoucherGroup.created_at.desc()
    ).limit(5).all()
    
    return render_template('vendor/dashboard.html',
                         site=vendor_site.site,
                         plans=plans,
                         total_vouchers_generated=total_vouchers_generated,
                         total_vouchers_sold=total_vouchers_sold,
                         total_revenue=total_revenue,
                         monthly_sales=monthly_sales,
                         recent_vouchers=recent_vouchers)

@app.route('/vendor/create_vouchers')
@login_required
def create_vouchers():
    # Vendor, Admin or Master can create vouchers - hierarchical permission
    if not has_permission('vendor'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    vendor_site = get_vendor_site_for_user()
    if not vendor_site:
        if current_user.user_type in ['admin', 'master']:
            flash('Selecione um site no dashboard de administrador primeiro.', 'warning')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Nenhum site atribuído. Contate o administrador.', 'error')
            return redirect(url_for('dashboard'))
    
    # Get available plans
    plans = VoucherPlan.query.filter_by(site_id=vendor_site.site_id, is_active=True).all()
    
    # Create form and populate plan choices
    form = VoucherGenerationForm()
    form.plan_id.choices = [(plan.id, f"{plan.name} - R$ {plan.price:.2f}".replace('.', ',')) for plan in plans]
    
    # Pre-select plan if provided in URL
    plan_id = request.args.get('plan_id')
    if plan_id:
        form.plan_id.data = int(plan_id)
    
    return render_template('vendor/create_vouchers.html', 
                         form=form, 
                         plans=plans, 
                         site=vendor_site.site)

@app.route('/vendor/generate_vouchers', methods=['POST'])
@login_required
def generate_vouchers():
    # Vendor, Admin or Master can generate vouchers - hierarchical permission
    if not has_permission('vendor'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    vendor_site = get_vendor_site_for_user()
    if not vendor_site:
        if current_user.user_type in ['admin', 'master']:
            flash('Selecione um site no dashboard de administrador primeiro.', 'warning')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Nenhum site atribuído. Contate o administrador.', 'error')
            return redirect(url_for('dashboard'))
    
    form = VoucherGenerationForm()
    plans = VoucherPlan.query.filter_by(site_id=vendor_site.site_id, is_active=True).all()
    form.plan_id.choices = [(plan.id, f"{plan.name} - R$ {plan.price:.2f}".replace('.', ',')) for plan in plans]
    
    if form.validate_on_submit():
        try:
            plan = VoucherPlan.query.get(form.plan_id.data)
            if not plan or plan.site_id != vendor_site.site_id:
                flash('Plano inválido.', 'error')
                return redirect(url_for('create_vouchers'))
            
            # Use plan settings for voucher generation
            code_length = plan.code_length
            code_form = [0]  # Always use numbers only
            limit_type = plan.limit_type
            limit_num = plan.limit_num if plan.limit_type != 2 else None
            description = request.form.get('description', '')
            
            # Convert plan duration to minutes for Omada API
            duration_in_minutes = plan.duration
            if plan.duration_unit == 'hours':
                duration_in_minutes = plan.duration * 60
            elif plan.duration_unit == 'days':
                duration_in_minutes = plan.duration * 24 * 60
            
            # Prepare voucher data for Omada API following exact specification
            voucher_data = {
                "name": f"{plan.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "amount": form.quantity.data,
                "codeLength": code_length,
                "codeForm": code_form,
                "limitType": limit_type,
                "durationType": 0,  # Client duration
                "duration": duration_in_minutes,
                "timingType": 0,  # Timing by time
                "rateLimit": {
                    "mode": 0,  # Custom rate limit
                    "customRateLimit": {
                        "downLimitEnable": bool(plan.download_speed),
                        "downLimit": (plan.download_speed * 1024) if plan.download_speed else 0,  # Convert Mbps to Kbps
                        "upLimitEnable": bool(plan.upload_speed),
                        "upLimit": (plan.upload_speed * 1024) if plan.upload_speed else 0  # Convert Mbps to Kbps
                    }
                },
                "trafficLimitEnable": bool(plan.data_quota),
                "applyToAllPortals": True,
                "logout": True,
                "description": description or f"Vouchers gerados por {current_user.username}",
                "printComments": f"Plano: {plan.name}",
                "validityType": 0  # Can be used at any time
            }
            
            # Add optional fields only if they have values
            if limit_type != 2 and limit_num:
                voucher_data["limitNum"] = limit_num
            
            if plan.data_quota:
                voucher_data["trafficLimit"] = plan.data_quota
                voucher_data["trafficLimitFrequency"] = 0  # Total
            
            if plan.price and plan.price > 0:
                voucher_data["unitPrice"] = int(plan.price * 100)  # Convert to cents
                voucher_data["currency"] = "BRL"
            
            # Create voucher group in Omada Controller
            from omada_api import OmadaAPI
            omada_api = OmadaAPI()
            result = omada_api.create_voucher_group(vendor_site.site.site_id, voucher_data)
            
            if result and result.get('errorCode') == 0:
                # Success - get the voucher group ID from Omada
                omada_group_id = result.get('result', {}).get('id')
                
                # Try to get the real voucher codes from Omada Controller
                real_voucher_codes = []
                try:
                    # Wait a moment for the vouchers to be created in Omada
                    import time
                    time.sleep(2)
                    
                    # Get voucher group details which should include the actual codes
                    group_details = omada_api.get_voucher_group_detail(vendor_site.site.site_id, omada_group_id)
                    
                    if group_details and group_details.get('errorCode') == 0:
                        voucher_data_list = group_details.get('result', {}).get('data', [])
                        real_voucher_codes = [voucher['code'] for voucher in voucher_data_list if 'code' in voucher]
                        logging.info(f"Retrieved {len(real_voucher_codes)} real voucher codes from Omada Controller")
                    
                    # If we couldn't get real codes, use reference codes
                    if not real_voucher_codes:
                        real_voucher_codes = [f"OMADA-{omada_group_id}-{i+1:03d}" for i in range(form.quantity.data)]
                        logging.warning(f"Could not retrieve real codes, using reference codes for group {omada_group_id}")
                    
                except Exception as e:
                    logging.error(f"Error retrieving real voucher codes: {str(e)}")
                    real_voucher_codes = [f"OMADA-{omada_group_id}-{i+1:03d}" for i in range(form.quantity.data)]
                
                # Create local voucher group record with proper initial status
                voucher_group = VoucherGroup(
                    site_id=vendor_site.site_id,
                    plan_id=plan.id,
                    created_by_id=current_user.id,
                    quantity=form.quantity.data,
                    omada_group_id=omada_group_id,
                    voucher_codes=real_voucher_codes,
                    total_value=plan.price * form.quantity.data,
                    unused_count=form.quantity.data,  # Initially all vouchers are unused
                    used_count=0,
                    in_use_count=0,
                    expired_count=0
                )
                
                db.session.add(voucher_group)
                db.session.commit()
                
                flash(f'{form.quantity.data} vouchers gerados com sucesso!', 'success')
                logging.info(f"Vouchers generated: {form.quantity.data} vouchers by {current_user.username} for plan {plan.name}")
                
                # Always redirect to format selection page after successful generation
                return redirect(url_for('choose_print_format', voucher_group_id=voucher_group.id))
            else:
                error_msg = result.get('msg', 'Erro na API do Omada Controller') if result else 'Falha na comunicação com o Controller'
                flash(f'Erro ao gerar vouchers: {error_msg}', 'error')
                logging.error(f"Omada API error: {result}")
                
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error generating vouchers: {str(e)}")
            flash('Erro interno ao gerar vouchers.', 'error')
    else:
        flash('Dados inválidos. Verifique os campos.', 'error')
    
    return redirect(url_for('create_vouchers'))

@app.route('/sync-voucher-status/<int:site_id>')
@login_required
def sync_voucher_status(site_id):
    from utils import sync_voucher_statuses_from_omada
    
    success = sync_voucher_statuses_from_omada(site_id)
    
    if success:
        flash('Status dos vouchers sincronizado com sucesso!', 'success')
        logging.info(f"Voucher statuses synced for site {site_id} by {current_user.username}")
    else:
        flash('Erro ao sincronizar status dos vouchers. Verifique a conexão com o Omada Controller.', 'error')
        logging.error(f"Failed to sync voucher statuses for site {site_id}")
    
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/vendor/voucher_history')
@login_required
def voucher_history():
    # Vendor, Admin or Master can access voucher history - hierarchical permission
    if not has_permission('vendor'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    vendor_site = get_vendor_site_for_user()
    if not vendor_site:
        if current_user.user_type in ['admin', 'master']:
            flash('Selecione um site no dashboard de administrador primeiro.', 'warning')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Nenhum site atribuído. Contate o administrador.', 'error')
            return redirect(url_for('dashboard'))
    
    # Get filter parameters
    plan_id = request.args.get('plan_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Base query - get all vouchers for the site (not just created by current user)
    query = VoucherGroup.query.filter_by(site_id=vendor_site.site_id)
    
    # Apply filters
    if plan_id:
        query = query.filter_by(plan_id=plan_id)
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(VoucherGroup.created_at >= start_dt)
        except ValueError:
            flash('Data de início inválida.', 'error')
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(VoucherGroup.created_at <= end_dt)
        except ValueError:
            flash('Data de fim inválida.', 'error')
    
    # Get voucher groups
    voucher_groups = query.order_by(VoucherGroup.created_at.desc()).all()
    
    # Calculate statistics based on actual sales (expired + used vouchers)
    total_vouchers_generated = sum(vg.quantity for vg in voucher_groups)
    total_vouchers_sold = sum((vg.expired_count or 0) + (vg.used_count or 0) for vg in voucher_groups)
    total_revenue = sum(((vg.expired_count or 0) + (vg.used_count or 0)) * vg.plan.price for vg in voucher_groups)
    total_groups = len(voucher_groups)
    
    # Calculate average per day for sold vouchers
    if voucher_groups:
        first_date = min(vg.created_at for vg in voucher_groups).date()
        last_date = max(vg.created_at for vg in voucher_groups).date()
        days_diff = (last_date - first_date).days + 1
        avg_per_day = total_vouchers_sold / days_diff if days_diff > 0 else 0
    else:
        avg_per_day = 0
    
    # Get available plans for filter
    plans = VoucherPlan.query.filter_by(site_id=vendor_site.site_id).all()
    
    return render_template('vendor/voucher_history.html',
                         voucher_groups=voucher_groups,
                         plans=plans,
                         site=vendor_site.site,
                         total_vouchers_generated=total_vouchers_generated,
                         total_vouchers_sold=total_vouchers_sold,
                         total_revenue=total_revenue,
                         total_groups=total_groups,
                         avg_per_day=avg_per_day,
                         selected_plan_id=plan_id,
                         start_date=start_date,
                         end_date=end_date)

@app.route('/vendor/download_vouchers/<int:voucher_group_id>')
@login_required
def download_vouchers(voucher_group_id):
    # Vendor, Admin or Master can download vouchers - hierarchical permission
    if not has_permission('vendor'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    voucher_group = VoucherGroup.query.get_or_404(voucher_group_id)
    
    # Check access: all users can access vouchers from their assigned sites
    if current_user.user_type == 'vendor':
        # Vendors can access vouchers from their site (not just their own)
        vendor_site = get_vendor_site_for_user()
        if not vendor_site or voucher_group.site_id != vendor_site.site_id:
            flash('Acesso negado a este grupo de vouchers.', 'error')
            return redirect(url_for('voucher_history'))
    elif current_user.user_type in ['admin', 'master']:
        # Admins and masters can access vouchers from their assigned sites
        if not check_site_access(voucher_group.site_id):
            flash('Acesso negado a este site.', 'error')
            return redirect(url_for('dashboard'))
    
    # Get format from request parameter
    format_type = request.args.get('format', 'a4')  # Default to A4
    
    try:
        # Generate PDF with specified format
        pdf_data = generate_voucher_pdf(voucher_group, voucher_group.voucher_codes, format_type)
        
        # Set filename based on format
        filename_suffix = "_50x80mm" if format_type == "50x80mm" else "_A4"
        filename = f'vouchers_{voucher_group.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}{filename_suffix}.pdf'
        
        # Create response
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        logging.info(f"PDF downloaded: voucher group {voucher_group_id} ({format_type}) by {current_user.username}")
        return response
        
    except Exception as e:
        logging.error(f"Error generating PDF: {str(e)}")
        flash('Erro ao gerar PDF dos vouchers.', 'error')
        return redirect(url_for('voucher_history'))

@app.route('/vendor/choose_print_format/<int:voucher_group_id>')
@login_required
def choose_print_format(voucher_group_id):
    """Choose print format page"""
    # Vendor, Admin or Master can choose print format - hierarchical permission
    if not has_permission('vendor'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    voucher_group = VoucherGroup.query.get_or_404(voucher_group_id)
    
    # Check access: all users can access vouchers from their assigned sites
    if current_user.user_type == 'vendor':
        # Vendors can access vouchers from their site (not just their own)
        vendor_site = get_vendor_site_for_user()
        if not vendor_site or voucher_group.site_id != vendor_site.site_id:
            flash('Acesso negado a este grupo de vouchers.', 'error')
            return redirect(url_for('voucher_history'))
    elif current_user.user_type in ['admin', 'master']:
        # Admins and masters can access vouchers from their assigned sites
        if not check_site_access(voucher_group.site_id):
            flash('Acesso negado a este site.', 'error')
            return redirect(url_for('dashboard'))
    
    return render_template('vendor/choose_print_format.html', voucher_group=voucher_group)

@app.route('/vendor/print_vouchers/<int:voucher_group_id>')
@login_required
def print_vouchers(voucher_group_id):
    # Vendor, Admin or Master can print vouchers - hierarchical permission
    if not has_permission('vendor'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    voucher_group = VoucherGroup.query.get_or_404(voucher_group_id)
    
    # Check access: all users can access vouchers from their assigned sites
    if current_user.user_type == 'vendor':
        # Vendors can access vouchers from their site (not just their own)
        vendor_site = get_vendor_site_for_user()
        if not vendor_site or voucher_group.site_id != vendor_site.site_id:
            flash('Acesso negado a este grupo de vouchers.', 'error')
            return redirect(url_for('voucher_history'))
    elif current_user.user_type in ['admin', 'master']:
        # Admins and masters can access vouchers from their assigned sites
        if not check_site_access(voucher_group.site_id):
            flash('Acesso negado a este site.', 'error')
            return redirect(url_for('dashboard'))
    
    # Get print format from URL parameter
    print_format = request.args.get('format', 'a4')
    
    logging.info(f"Print page opened for voucher group {voucher_group_id} ({print_format}) by {current_user.username}")
    
    # Render HTML page optimized for printing with selected format
    return render_template('vendor/print_vouchers_clean.html', 
                         voucher_group=voucher_group, 
                         print_format=print_format)

@app.route('/vendor/sales_reports')
@login_required  
def vendor_sales_reports():
    # Vendor, Admin or Master can access sales reports - hierarchical permission
    if not has_permission('vendor'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    vendor_site = get_vendor_site_for_user()
    if not vendor_site:
        if current_user.user_type in ['admin', 'master']:
            flash('Selecione um site no dashboard de administrador primeiro.', 'warning')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Nenhum site atribuído. Contate o administrador.', 'error')
            return redirect(url_for('dashboard'))
    
    # Get date filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Default to last 30 days if no dates provided
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Generate report data
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        
        # Get all voucher groups for the site in date range (not just created by current user)
        voucher_groups = VoucherGroup.query.filter(
            VoucherGroup.site_id == vendor_site.site_id,
            VoucherGroup.created_at >= start_dt,
            VoucherGroup.created_at <= end_dt
        ).all()
        
        # Get individual voucher data from Omada Controller
        sold_vouchers = []  # Vouchers that are expired or in-use
        from omada_api import omada_api
        
        try:
            for vg in voucher_groups:
                if vg.omada_group_id:
                    # Get detailed voucher data from Omada Controller
                    group_details = omada_api.get_voucher_group_detail(vendor_site.site.site_id, vg.omada_group_id)
                    
                    if group_details and group_details.get('errorCode') == 0:
                        voucher_data_list = group_details.get('result', {}).get('data', [])
                        
                        for voucher in voucher_data_list:
                            # Only include vouchers that are expired or in-use (sold)
                            status = voucher.get('status', 0)
                            if status in [2, 3]:  # 2 = in-use, 3 = expired
                                sold_vouchers.append({
                                    'code': voucher.get('code', 'N/A'),
                                    'status': 'Em Uso' if status == 2 else 'Expirado',
                                    'status_class': 'warning' if status == 2 else 'danger',
                                    'plan_name': vg.plan.name,
                                    'plan_price': vg.plan.price,
                                    'created_at': vg.created_at,
                                    'group_id': vg.id,
                                    'usage_time': voucher.get('usageTime', 0) if status == 2 else voucher.get('duration', 0),
                                    'start_time': voucher.get('startTime'),
                                    'end_time': voucher.get('endTime')
                                })
        
        except Exception as e:
            logging.error(f"Error fetching individual voucher data for vendor: {str(e)}")
            flash('Erro ao carregar dados dos vouchers do Omada Controller.', 'warning')
        
        # Calculate totals based on sold vouchers
        total_vouchers_generated = sum(vg.quantity for vg in voucher_groups)
        total_vouchers_sold = len(sold_vouchers)
        total_revenue = sum(voucher['plan_price'] for voucher in sold_vouchers)
        
        # Group by plan
        plan_stats = {}
        for voucher in sold_vouchers:
            plan_name = voucher['plan_name']
            if plan_name not in plan_stats:
                plan_stats[plan_name] = {
                    'plan_name': plan_name,
                    'vouchers': 0,
                    'revenue': 0.0
                }
            plan_stats[plan_name]['vouchers'] += 1
            plan_stats[plan_name]['revenue'] += voucher['plan_price']
        
        # Group by date
        date_stats = {}
        for voucher in sold_vouchers:
            date_key = voucher['created_at'].strftime('%Y-%m-%d')
            if date_key not in date_stats:
                date_stats[date_key] = {
                    'vouchers': 0,
                    'revenue': 0.0
                }
            date_stats[date_key]['vouchers'] += 1
            date_stats[date_key]['revenue'] += voucher['plan_price']
        
        return render_template('vendor/sales_reports.html',
                             site=vendor_site.site,
                             sold_vouchers=sold_vouchers,
                             total_vouchers_generated=total_vouchers_generated,
                             total_vouchers_sold=total_vouchers_sold,
                             total_revenue=total_revenue,
                             plan_stats=plan_stats,
                             date_stats=date_stats,
                             start_date=start_date,
                             end_date=end_date)
                             
    except ValueError:
        flash('Datas inválidas fornecidas.', 'error')
        return redirect(url_for('vendor_dashboard'))

# Admin Delete Vouchers Routes
@app.route('/admin/delete_voucher/<voucher_id>', methods=['POST'])
@login_required
def delete_voucher(voucher_id):
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    site = Site.query.get(current_site_id)
    if not site:
        flash('Site não encontrado.', 'error')
        return redirect(url_for('admin_site_selection'))
    
    try:
        from omada_api import omada_api
        result = omada_api.delete_voucher(site.site_id, voucher_id)
        
        if result and result.get('errorCode') == 0:
            flash('Voucher excluído com sucesso!', 'success')
            logging.info(f"Voucher {voucher_id} deleted by admin {current_user.username} for site {site.name}")
        else:
            error_msg = result.get('msg', 'Erro desconhecido') if result else 'Falha na comunicação'
            flash(f'Erro ao excluir voucher: {error_msg}', 'error')
            logging.error(f"Failed to delete voucher {voucher_id}: {error_msg}")
    
    except Exception as e:
        logging.error(f"Error deleting voucher {voucher_id}: {str(e)}")
        flash('Erro interno ao excluir voucher.', 'error')
    
    return redirect(request.referrer or url_for('admin_voucher_history'))

@app.route('/admin/delete_voucher_groups', methods=['POST'])
@login_required
def delete_voucher_groups():
    if current_user.user_type != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    current_site_id = session.get('selected_site_id')
    if not current_site_id:
        return redirect(url_for('admin_site_selection'))
    
    site = Site.query.get(current_site_id)
    if not site:
        flash('Site não encontrado.', 'error')
        return redirect(url_for('admin_site_selection'))
    
    try:
        # Get group IDs from form data
        group_ids = request.form.getlist('group_ids')
        if not group_ids:
            flash('Nenhum grupo selecionado para exclusão.', 'warning')
            return redirect(request.referrer or url_for('admin_voucher_history'))
        
        # Get voucher groups from database to get Omada group IDs
        voucher_groups = VoucherGroup.query.filter(
            VoucherGroup.id.in_(group_ids),
            VoucherGroup.site_id == current_site_id
        ).all()
        
        if not voucher_groups:
            flash('Grupos de vouchers não encontrados.', 'error')
            return redirect(request.referrer or url_for('admin_voucher_history'))
        
        # Extract Omada group IDs
        omada_group_ids = [vg.omada_group_id for vg in voucher_groups if vg.omada_group_id]
        
        if omada_group_ids:
            from omada_api import omada_api
            result = omada_api.delete_voucher_groups(site.site_id, omada_group_ids)
            
            if result and result.get('errorCode') == 0:
                # Delete from local database
                for vg in voucher_groups:
                    db.session.delete(vg)
                db.session.commit()
                
                flash(f'{len(voucher_groups)} grupos de vouchers excluídos com sucesso!', 'success')
                logging.info(f"{len(voucher_groups)} voucher groups deleted by admin {current_user.username} for site {site.name}")
            else:
                error_msg = result.get('msg', 'Erro desconhecido') if result else 'Falha na comunicação'
                flash(f'Erro ao excluir grupos de vouchers: {error_msg}', 'error')
                logging.error(f"Failed to delete voucher groups: {error_msg}")
        else:
            flash('Nenhum grupo válido encontrado no Omada Controller.', 'warning')
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting voucher groups: {str(e)}")
        flash('Erro interno ao excluir grupos de vouchers.', 'error')
    
    return redirect(request.referrer or url_for('admin_voucher_history'))

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# PWA Routes
@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')

@app.route('/offline')
def offline():
    return render_template('offline.html')

# Auto-sync API Routes  
@app.route('/api/sync-sites', methods=['POST'])
@login_required
def api_sync_sites():
    """API endpoint for syncing sites with Omada Controller"""
    try:
        # Check user authorization
        if current_user.user_type != 'master':
            return jsonify({'error': 'Unauthorized - Only master users can sync sites'}), 403
        
        # Check if Omada API is configured
        omada_config = OmadaConfig.query.first()
        if not omada_config or not omada_config.controller_url:
            return jsonify({
                'success': False,
                'error': 'Omada Controller not configured'
            }), 400
        
        # Sync sites from Omada Controller
        count = sync_sites_from_omada()
        
        logging.info(f"Sites synced successfully: {count}")
        return jsonify({
            'success': True,
            'count': count,
            'message': f'{count} sites sincronizados'
        })
    except Exception as e:
        logging.error(f"Error syncing sites: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync-vouchers/<int:site_id>', methods=['POST'])
@login_required
def api_sync_vouchers(site_id):
    """API endpoint for syncing vouchers with Omada Controller"""
    try:
        # Check if site exists
        site = Site.query.get(site_id)
        if not site:
            return jsonify({'error': 'Site not found'}), 404
        
        # Check if user has access to this site
        has_access = False
        if current_user.user_type == 'master':
            has_access = True
        elif current_user.user_type == 'admin':
            admin_site = AdminSite.query.filter_by(admin_id=current_user.id, site_id=site_id).first()
            has_access = admin_site is not None
        elif current_user.user_type == 'vendor':
            vendor_site = VendorSite.query.filter_by(vendor_id=current_user.id, site_id=site_id).first()
            has_access = vendor_site is not None
        
        if not has_access:
            return jsonify({'error': 'Site access denied'}), 403
        
        # Check if Omada API is configured
        omada_config = OmadaConfig.query.first()
        if not omada_config or not omada_config.controller_url:
            return jsonify({
                'success': False,
                'error': 'Omada Controller not configured'
            }), 400
        
        # Sync voucher statuses from Omada Controller
        count = sync_voucher_statuses_from_omada(site_id)
        
        logging.info(f"Vouchers synced for site {site_id}: {count}")
        return jsonify({
            'success': True,
            'count': count,
            'message': f'{count} vouchers sincronizados'
        })
    except Exception as e:
        logging.error(f"Error syncing vouchers for site {site_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync-status')
@login_required
def api_sync_status():
    """Get current sync status and statistics"""
    try:
        # Get last sync times from database or cache
        stats = {
            'sites_count': Site.query.count(),
            'voucher_groups_count': VoucherGroup.query.count(),
            'last_site_sync': None,  # Could be stored in a sync log table
            'last_voucher_sync': None,
            'sync_errors': 0
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logging.error(f"Error getting sync status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/admin/import-voucher-groups', methods=['GET', 'POST'])
@login_required
def import_voucher_groups():
    """Import voucher groups interface"""
    if not has_permission('admin'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    form = ImportVoucherGroupsForm()
    
    # Populate site choices based on user access
    accessible_sites = get_accessible_sites()
    form.site_id.choices = [(site.id, site.name) for site in accessible_sites]
    
    # Populate plan choices (will be updated via AJAX based on site selection)
    form.default_plan_id.choices = []
    
    if form.validate_on_submit():
        # This will be handled via AJAX, not form submission
        pass
    
    return render_template('admin/import_voucher_groups.html', form=form)

@app.route('/api/scan-missing-voucher-groups/<int:site_id>')
@login_required
def api_scan_missing_voucher_groups(site_id):
    """Scan for voucher groups that exist in Omada but not locally"""
    if not has_permission('admin'):
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    if not check_site_access(site_id):
        return jsonify({'success': False, 'error': 'Acesso negado ao site'}), 403
    
    try:
        from omada_api import omada_api
        
        site = Site.query.get_or_404(site_id)
        
        # Get all voucher groups from Omada Controller
        all_voucher_groups = []
        page = 1
        page_size = 100
        
        while True:
            response = omada_api.get_voucher_groups(site.site_id, page=page, page_size=page_size)
            
            if not response or response.get('errorCode') != 0:
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
        
        # Filter out groups that already exist locally
        missing_groups = []
        existing_omada_ids = [vg.omada_group_id for vg in VoucherGroup.query.filter_by(site_id=site_id).all()]
        
        for group_data in all_voucher_groups:
            omada_group_id = group_data.get('id')
            if omada_group_id and omada_group_id not in existing_omada_ids:
                # Get detailed information about this group
                group_details = omada_api.get_voucher_group_detail(site.site_id, omada_group_id)
                
                if group_details and group_details.get('errorCode') == 0:
                    result_data = group_details.get('result', {})
                    group_info = result_data.get('groupInfo', {})
                    voucher_data_list = result_data.get('data', [])
                    
                    if voucher_data_list:
                        missing_groups.append({
                            'omada_id': omada_group_id,
                            'name': group_info.get('name', 'Sem Nome'),
                            'voucher_count': len(voucher_data_list),
                            'duration': group_info.get('durationLimit', 60),
                            'data_limit': group_info.get('dataLimit', 0),
                            'group_info': group_info,
                            'voucher_data': voucher_data_list
                        })
        
        return jsonify({
            'success': True,
            'groups': missing_groups
        })
        
    except Exception as e:
        logging.error(f"Error scanning missing voucher groups: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/import-voucher-groups', methods=['POST'])
@login_required
def api_import_voucher_groups():
    """Import selected voucher groups with specified plans"""
    if not has_permission('admin'):
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    try:
        data = request.get_json()
        site_id = data.get('site_id')
        groups_to_import = data.get('groups', [])
        
        if not check_site_access(site_id):
            return jsonify({'success': False, 'error': 'Acesso negado ao site'}), 403
        
        imported_count = 0
        
        for group_import in groups_to_import:
            group_data = group_import.get('group')
            plan_id = group_import.get('plan_id')
            
            # Validate plan belongs to the site
            plan = VoucherPlan.query.filter_by(id=plan_id, site_id=site_id).first()
            if not plan:
                continue
            
            # Extract voucher codes
            voucher_codes = [v.get('code', f'CODE-{i}') for i, v in enumerate(group_data['voucher_data'])]
            
            # Count statuses
            unused_count = sum(1 for v in group_data['voucher_data'] if v.get('status') == 0)
            used_count = sum(1 for v in group_data['voucher_data'] if v.get('status') == 1)
            in_use_count = sum(1 for v in group_data['voucher_data'] if v.get('status') == 2)
            expired_count = sum(1 for v in group_data['voucher_data'] if v.get('status') == 3)
            
            # Calculate total value
            total_value = len(group_data['voucher_data']) * plan.price
            
            # Create voucher group
            voucher_group = VoucherGroup(
                plan_id=plan.id,
                site_id=site_id,
                quantity=len(group_data['voucher_data']),
                omada_group_id=group_data['omada_id'],
                created_by_id=current_user.id,
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
            imported_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'imported_count': imported_count
        })
        
    except Exception as e:
        logging.error(f"Error importing voucher groups: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get-site-plans/<int:site_id>')
@login_required
def api_get_site_plans(site_id):
    """Get voucher plans for a specific site"""
    if not check_site_access(site_id):
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    try:
        plans = VoucherPlan.query.filter_by(site_id=site_id, is_active=True).all()
        plans_data = [{'id': plan.id, 'name': plan.name, 'price': plan.price} for plan in plans]
        
        return jsonify({
            'success': True,
            'plans': plans_data
        })
    except Exception as e:
        logging.error(f"Error getting site plans: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# CRUD Routes for Plans  
@app.route('/admin/plans/<int:plan_id>/delete', methods=['POST'])
@login_required
def delete_plan(plan_id):
    """Delete voucher plan"""
    if not has_permission('admin'):
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    plan = VoucherPlan.query.get_or_404(plan_id)
    
    # Check if admin has access to this plan's site
    if current_user.user_type == 'admin':
        admin_site = AdminSite.query.filter_by(
            admin_id=current_user.id, 
            site_id=plan.site_id
        ).first()
        if not admin_site:
            return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    # Check if plan has associated voucher groups
    voucher_groups = VoucherGroup.query.filter_by(plan_id=plan_id).count()
    if voucher_groups > 0:
        return jsonify({
            'success': False, 
            'error': f'Não é possível excluir o plano. Existem {voucher_groups} grupos de vouchers associados.'
        }), 400
    
    try:
        plan_name = plan.name
        db.session.delete(plan)
        db.session.commit()
        logging.info(f"Plan {plan_name} deleted by {current_user.username}")
        return jsonify({'success': True, 'message': f'Plano "{plan_name}" excluído com sucesso'})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting plan {plan_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# CRUD Routes for Voucher Groups
@app.route('/admin/vouchers/<int:group_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_voucher_group(group_id):
    """Edit voucher group"""
    if not has_permission('vendor'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    voucher_group = VoucherGroup.query.get_or_404(group_id)
    
    # Check access based on user type
    if not check_site_access(voucher_group.site_id):
        flash('Acesso negado a este grupo de vouchers.', 'error')
        return redirect(url_for('voucher_history'))
    
    form = VoucherGroupEditForm(obj=voucher_group)
    
    if form.validate_on_submit():
        try:
            # Only allow editing of name and notes, not critical data
            voucher_group.name = form.name.data
            voucher_group.notes = form.notes.data
            db.session.commit()
            flash('Grupo de vouchers atualizado com sucesso!', 'success')
            logging.info(f"Voucher group {group_id} updated by {current_user.username}")
            return redirect(url_for('voucher_history'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar grupo: {str(e)}', 'error')
            logging.error(f"Error updating voucher group {group_id}: {str(e)}")
    
    return render_template('admin/edit_voucher_group.html', 
                         form=form, voucher_group=voucher_group)

@app.route('/admin/vouchers/<int:group_id>/delete', methods=['POST'])
@login_required
def delete_voucher_group(group_id):
    """Delete voucher group (and from Omada Controller)"""
    if not has_permission('admin'):
        return jsonify({'success': False, 'error': 'Apenas administradores podem excluir vouchers'}), 403
    
    voucher_group = VoucherGroup.query.get_or_404(group_id)
    
    # Check access
    if not check_site_access(voucher_group.site_id):
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    try:
        # Try to delete from Omada Controller first
        if voucher_group.omada_group_id:
            try:
                success = omada_api.delete_voucher_groups(voucher_group.site.site_id, [voucher_group.omada_group_id])
                if not success:
                    logging.warning(f"Failed to delete voucher group from Omada: {voucher_group.omada_group_id}")
            except Exception as omada_error:
                logging.error(f"Omada deletion error: {str(omada_error)}")
                # Continue with local deletion even if Omada fails
        
        # Delete from local database
        group_info = f"{voucher_group.plan.name} ({voucher_group.quantity} vouchers)"
        db.session.delete(voucher_group)
        db.session.commit()
        
        logging.info(f"Voucher group {group_id} deleted by {current_user.username}")
        return jsonify({
            'success': True, 
            'message': f'Grupo de vouchers "{group_info}" excluído com sucesso'
        })
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting voucher group {group_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Template filters
@app.template_filter('currency')
def currency_filter(value):
    return format_currency(value or 0)

@app.template_filter('duration')
def duration_filter(value, unit):
    return format_duration(value, unit)
