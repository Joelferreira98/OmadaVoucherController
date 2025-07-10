from datetime import datetime
from app import db
from flask_login import UserMixin
from sqlalchemy import Text, JSON

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # master, admin, vendor
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    admin_sites = db.relationship('AdminSite', back_populates='admin', cascade='all, delete-orphan')
    vendor_site = db.relationship('VendorSite', back_populates='vendor', uselist=False, cascade='all, delete-orphan')
    created_vouchers = db.relationship('VoucherGroup', back_populates='created_by', cascade='all, delete-orphan')

class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.String(100), unique=True, nullable=False)  # Omada site ID
    name = db.Column(db.String(200), nullable=False)
    region = db.Column(db.String(100))
    timezone = db.Column(db.String(50))
    scenario = db.Column(db.String(50))
    site_type = db.Column(db.Integer)
    last_sync = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    admin_sites = db.relationship('AdminSite', back_populates='site', cascade='all, delete-orphan')
    vendor_sites = db.relationship('VendorSite', back_populates='site', cascade='all, delete-orphan')
    voucher_plans = db.relationship('VoucherPlan', back_populates='site', cascade='all, delete-orphan')
    voucher_groups = db.relationship('VoucherGroup', back_populates='site', cascade='all, delete-orphan')

class AdminSite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    admin = db.relationship('User', back_populates='admin_sites')
    site = db.relationship('Site', back_populates='admin_sites')

class VendorSite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    vendor = db.relationship('User', back_populates='vendor_site')
    site = db.relationship('Site', back_populates='vendor_sites')

class VoucherPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    duration_unit = db.Column(db.String(20), default='minutes')  # minutes, hours, days
    price = db.Column(db.Float, nullable=False)
    data_quota = db.Column(db.Integer)  # in MB, optional
    download_speed = db.Column(db.Integer)  # in Mbps, optional
    upload_speed = db.Column(db.Integer)  # in Mbps, optional
    code_length = db.Column(db.Integer, default=8)  # voucher code length
    limit_type = db.Column(db.Integer, default=2)  # 0=Limited Usage, 1=Limited Users, 2=Unlimited
    limit_num = db.Column(db.Integer)  # limit number if limit_type != 2
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    site = db.relationship('Site', back_populates='voucher_plans')
    voucher_groups = db.relationship('VoucherGroup', back_populates='plan', cascade='all, delete-orphan')

class VoucherGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('voucher_plan.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    omada_group_id = db.Column(db.String(100))  # ID from Omada Controller
    voucher_codes = db.Column(JSON)  # List of voucher codes
    total_value = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, used, expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    site = db.relationship('Site', back_populates='voucher_groups')
    plan = db.relationship('VoucherPlan', back_populates='voucher_groups')
    created_by = db.relationship('User', back_populates='created_vouchers')

class OmadaConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    controller_url = db.Column(db.String(500), nullable=False)
    client_id = db.Column(db.String(100), nullable=False)
    client_secret = db.Column(db.String(100), nullable=False)
    omadac_id = db.Column(db.String(100), nullable=False)
    access_token = db.Column(Text)
    refresh_token = db.Column(Text)
    token_expires_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
