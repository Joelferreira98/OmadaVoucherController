"""
Permission management utilities for user access control
"""
from functools import wraps
from flask import abort
from flask_login import current_user


def has_permission(required_role):
    """
    Check if current user has the required permission level
    
    Permission hierarchy:
    - master: can access all features (master, admin, vendor)
    - admin: can access admin and vendor features  
    - vendor: can access only vendor features
    """
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
    if manager_user_type is None:
        manager_user_type = current_user.user_type
    
    # Master can manage admin and vendor
    if manager_user_type == 'master' and target_user_type in ['admin', 'vendor']:
        return True
    
    # Admin can manage vendor
    if manager_user_type == 'admin' and target_user_type == 'vendor':
        return True
    
    return False


def get_user_dashboard_url():
    """
    Get the appropriate dashboard URL for the current user
    """
    user_type = current_user.user_type
    
    if user_type == 'master':
        return '/master'
    elif user_type == 'admin':
        return '/admin'
    elif user_type == 'vendor':
        return '/vendor'
    else:
        return '/'


def get_allowed_routes_for_user(user_type=None):
    """
    Get list of routes that a user type can access
    
    This helps with navigation and access control
    """
    if user_type is None:
        user_type = current_user.user_type
    
    routes = {
        'master': [
            # Master-specific routes
            'master_dashboard', 'master_config', 'manage_admins', 'manage_sites',
            'create_admin', 'edit_admin', 'delete_admin', 'change_admin_password',
            'sync_sites',
            
            # Admin routes (inherited)
            'admin_dashboard', 'manage_plans', 'manage_vendors', 'admin_sales_reports',
            'admin_create_vouchers', 'admin_voucher_history', 'cash_register',
            'create_vendor', 'edit_vendor', 'delete_vendor', 'change_vendor_password',
            
            # Vendor routes (inherited)
            'vendor_dashboard', 'create_vouchers', 'voucher_history', 'sales_reports',
            'print_vouchers', 'export_vouchers',
            
            # Common routes
            'profile', 'change_password', 'logout'
        ],
        
        'admin': [
            # Admin-specific routes
            'admin_dashboard', 'manage_plans', 'manage_vendors', 'admin_sales_reports',
            'admin_create_vouchers', 'admin_voucher_history', 'cash_register',
            'create_vendor', 'edit_vendor', 'delete_vendor', 'change_vendor_password',
            
            # Vendor routes (inherited)
            'vendor_dashboard', 'create_vouchers', 'voucher_history', 'sales_reports',
            'print_vouchers', 'export_vouchers',
            
            # Common routes
            'profile', 'change_password', 'logout'
        ],
        
        'vendor': [
            # Vendor-specific routes
            'vendor_dashboard', 'create_vouchers', 'voucher_history', 'sales_reports',
            'print_vouchers', 'export_vouchers',
            
            # Common routes
            'profile', 'change_password', 'logout'
        ]
    }
    
    return routes.get(user_type, ['profile', 'logout'])


def filter_navigation_items(navigation_items, user_type=None):
    """
    Filter navigation items based on user permissions
    
    Takes a list of navigation items and returns only those
    the user has permission to access
    """
    if user_type is None:
        user_type = current_user.user_type
    
    allowed_routes = get_allowed_routes_for_user(user_type)
    
    filtered_items = []
    for item in navigation_items:
        if item.get('route') in allowed_routes:
            filtered_items.append(item)
    
    return filtered_items