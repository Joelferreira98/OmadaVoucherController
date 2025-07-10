# Voucher Management System

## Overview

This is a comprehensive voucher management system built with Flask that integrates with Omada Controller for WiFi hotspot management. The system supports a hierarchical user structure with masters, administrators, and vendors, allowing for multi-site voucher creation and sales management.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes (July 2025)

### Voucher Status Management System
- **Problem Identified**: Vouchers were incorrectly marked as "sold" when generated, not when actually used
- **Solution Implemented**: 
  - Vouchers now start with status "generated" when created
  - Only become "sold" when expired/used in Omada Controller
  - Added real-time status synchronization from Omada Controller
  - Added database fields: unused_count, used_count, in_use_count, expired_count, last_sync
  - Created sync_voucher_statuses_from_omada() function for status updates
  - Added /sync-voucher-status/<site_id> route for manual synchronization

### Code Generation Improvements
- **Voucher Codes**: Always numeric-only (no letters/symbols)
- **Plan-Level Configuration**: Code length and limit type configured at voucher plan creation
- **Simplified Generation**: Removed advanced options from voucher generation form

### Voucher Code Synchronization Issue Resolution
- **Problem**: PDF voucher codes don't match actual Omada Controller generated codes
- **Root Cause**: Omada API limitation - voucher code retrieval endpoints are not functional
- **Solution**: Updated system to generate reference codes and guide users to access real codes from Omada Controller web interface
- **Implementation**: 
  - PDF now shows clear instructions to access real codes from Omada Controller
  - Added Omada Group ID tracking for easy reference
  - Updated templates to warn users about accessing real codes
  - Created fallback system with proper user guidance

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with PostgreSQL support
- **Authentication**: Flask-Login for session management
- **Forms**: Flask-WTF for form handling and validation
- **PDF Generation**: ReportLab for voucher PDF creation

### Frontend Architecture
- **Template Engine**: Jinja2 (Flask's default)
- **CSS Framework**: Bootstrap 5 with custom dashboard styling
- **JavaScript**: Vanilla JavaScript with Chart.js for data visualization
- **Icons**: Font Awesome and Feather icons

### Database Schema
The system uses a relational database with the following key entities:
- **Users**: Hierarchical user system (master, admin, vendor)
- **Sites**: Physical locations managed through Omada Controller
- **VoucherPlans**: Configurable internet access plans
- **VoucherGroups**: Batch voucher generations
- **AdminSite/VendorSite**: Many-to-many relationships for site assignments

## Key Components

### User Management System
- **Master Users**: System-wide administration, can create admins and manage all sites
- **Admin Users**: Site-specific management, can create vendors and manage voucher plans
- **Vendor Users**: Site-specific voucher creation and sales reporting

### Voucher System
- **Plan Creation**: Admins can create voucher plans with duration, pricing, and bandwidth limits
- **Voucher Generation**: Vendors can generate vouchers in batches with PDF output
- **Sales Tracking**: Comprehensive reporting system for voucher sales

### Omada Controller Integration
- **API Integration**: Connects to TP-Link Omada Controller for hotspot management
- **Configuration Interface**: Master user interface for API credentials setup
- **Site Synchronization**: Paginated site synchronization from Omada Controller with full API compliance
- **Token Management**: OAuth2-style authentication with token refresh
- **Connection Testing**: Built-in API connection testing functionality
- **Admin Management**: Complete system for creating administrators and assigning sites

## Data Flow

1. **User Authentication**: Users log in based on their role (master/admin/vendor)
2. **Site Selection**: Multi-site users select their working site
3. **Plan Management**: Admins create and manage voucher plans for their sites
4. **Voucher Generation**: Vendors select plans and generate voucher batches
5. **PDF Creation**: System generates printable voucher PDFs with codes
6. **Sales Reporting**: System tracks and reports voucher sales by vendor/site

## External Dependencies

### Core Dependencies
- Flask and its extensions (SQLAlchemy, Login, WTF)
- PostgreSQL database
- ReportLab for PDF generation
- Requests for HTTP API calls

### Frontend Dependencies
- Bootstrap 5 (CSS framework)
- Chart.js (data visualization)
- Font Awesome (icons)
- Feather Icons (additional icons)

### Third-party Integrations
- **Omada Controller**: TP-Link's network management system
- **OAuth2 Authentication**: For secure API access to Omada Controller

## Deployment Strategy

### Environment Configuration
The application relies on environment variables for configuration:
- `SESSION_SECRET`: Flask session security
- `DATABASE_URL`: PostgreSQL connection string
- `OMADA_CONTROLLER_URL`: Omada Controller endpoint
- `OMADA_CLIENT_ID`: OAuth2 client credentials
- `OMADA_CLIENT_SECRET`: OAuth2 client credentials
- `OMADA_OMADAC_ID`: Omada Controller instance ID

### Database Initialization
- Automatic table creation on startup
- Default master user creation with credentials (username: master, password: admin123)
- Omada API configuration storage in database
- Site synchronization from Omada Controller

### Security Considerations
- Password hashing using Werkzeug security utilities
- Session-based authentication with Flask-Login
- Role-based access control for different user types
- CSRF protection through Flask-WTF

### File Structure
- `app.py`: Main application configuration and initialization
- `models.py`: Database models and relationships
- `routes.py`: URL routing and view functions
- `forms.py`: Form definitions and validation
- `utils.py`: Utility functions (PDF generation, formatting)
- `omada_api.py`: Omada Controller API integration
- `templates/`: Jinja2 templates organized by user role
- `static/`: CSS, JavaScript, and asset files

The system is designed to be easily deployable on cloud platforms with support for containerization and can scale horizontally by adding more sites and users through the Omada Controller integration.