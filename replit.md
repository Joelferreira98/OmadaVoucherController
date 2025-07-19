# Voucher Management System

## Overview

This is a comprehensive voucher management system built with Flask that integrates with Omada Controller for WiFi hotspot management. The system supports a hierarchical user structure with masters, administrators, and vendors, allowing for multi-site voucher creation and sales management.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes (July 2025)

### Revenue Calculation Bug Fix (July 10, 2025)
- **Critical Problem**: Application was calculating revenue based on total vouchers generated instead of vouchers actually sold/used
- **Impact**: Revenue reports showed inflated values (e.g., showing R$ 100 when only 1 of 10 vouchers was used)
- **Root Cause**: System was using total quantity multiplied by price instead of tracking actual usage from Omada Controller
- **Solution Implemented**:
  - Updated all revenue calculations to use only sold vouchers (expired_count + used_count)
  - Modified generate_sales_report_data() to calculate based on actual sales
  - Updated voucher history and sales report templates to show both generated and sold quantities
  - Added conversion rate tracking (sold/generated percentage)
  - Enhanced Omada API integration to properly sync voucher status counts
  - Updated templates to clearly distinguish between "Vouchers Gerados" and "Vouchers Vendidos"
  - Added detailed status display showing unused, used, in-use, and expired counts

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

### Real Voucher Code Retrieval Enhancement (July 10, 2025)
- **Problem**: Users received PDF with placeholder codes (e.g., "OMADA-686fd6d0adf92811290d0fac-001") instead of real codes ("33537248")
- **Solution Implemented**:
  - Added automatic real code retrieval after voucher group creation
  - Implemented 2-second delay to allow Omada Controller to generate codes
  - Enhanced sync_voucher_statuses_from_omada() to update placeholder codes with real codes
  - Added intelligent PDF generation that detects real vs placeholder codes
  - Updated PDF warnings to be more specific about code type
  - Added fallback mechanism for when real codes cannot be retrieved

### Ticket Layout Redesign (July 10, 2025)
- **Problem**: User requested ticket format for customer delivery instead of table format
- **Solution Implemented**:
  - Redesigned PDF layouts for both A4 and 50x80mm formats as individual tickets
  - A4 format: 32 tickets per page in 4x8 grid layout for easy cutting
  - 50x80mm format: One ticket per page for thermal printers
  - Each ticket includes: Site name, voucher code, plan name, and price
  - Removed generic elements: "Voucher Internet" header, duration display, usage instructions
  - Added cut lines (✂) for easy separation
  - Professional ticket format suitable for customer delivery
  - Fixed ticket dimensions ensure consistent sizing regardless of voucher quantity

### Admin Voucher Management & Cash Register System (July 10, 2025)
- **Enhancement**: Extended vendor functionality to administrators
- **Admin Voucher Functions**:
  - Complete voucher creation system identical to vendor interface
  - Voucher history management with PDF downloads and printing
  - Real-time synchronization with Omada Controller
  - Multi-format support (A4 and thermal printer formats)
- **Cash Register System**:
  - Period-based cash register closing with automated calculations
  - Revenue tracking based on actual voucher sales (used + expired)
  - Optional removal of expired vouchers from Omada Controller via API
  - Complete audit trail with voucher group snapshots
  - Historical reporting of all cash register closings
  - Database persistence of all financial records even after voucher removal
- **New Database Model**: CashRegister for comprehensive financial tracking
- **New API Integration**: delete_expired_vouchers endpoint for cleanup operations

### Individual Voucher Sales Reporting (July 10, 2025)
- **Major Change**: Sales reports now show individual vouchers instead of voucher groups
- **Implementation**:
  - Both admin and vendor sales reports fetch individual voucher data from Omada Controller
  - Only vouchers with status "expired" or "in-use" are considered "sold"
  - Reports display actual voucher codes, individual status, and precise revenue calculation
  - Real-time data integration directly from Omada Controller API
  - Detailed voucher-level tracking replaces group-based reporting
- **Benefits**:
  - Accurate revenue tracking based on actual voucher usage
  - Individual voucher code visibility for customer support
  - Real-time status monitoring (Em Uso vs Expirado)
  - Precise audit trail for financial reporting
  - Enhanced CSV export with individual voucher details

### Admin Voucher Deletion System (July 10, 2025)
- **Feature**: Complete voucher deletion system for administrators
- **Implementation**:
  - Added delete_voucher() and delete_voucher_groups() functions to Omada API
  - Individual voucher deletion by voucher ID from Omada Controller
  - Bulk voucher group deletion with checkbox selection interface
  - Form-based selection with "Select All" functionality
  - Confirmation dialogs to prevent accidental deletions
  - Database synchronization - groups removed from local DB after successful Omada deletion
- **Admin Interface Location**:
  - Access: Admin Dashboard → Histórico de Vouchers
  - Individual deletion: Available per voucher (future implementation)
  - Bulk deletion: Checkbox selection + "Excluir Selecionados" button in voucher history
  - Safety: Confirmation dialog before deletion, only affects Omada Controller and local database

### UI Visibility Improvements (July 10, 2025)
- **Problem**: Form fields had white text on white background making them invisible
- **Solution**: Switched from dark Bootstrap theme to standard Bootstrap for better form visibility
- **Login Page Cleanup**: Removed default test credentials display for production use

### Complete Theme System Implementation (July 10, 2025)
- **Feature**: Dual theme system with light and dark modes
- **Implementation**:
  - Created themes.css with comprehensive CSS custom properties for both themes
  - Added theme-switcher.js with persistent localStorage theme preference
  - Floating theme toggle button with smooth transitions
  - Theme-aware chart colors and grid lines
  - Complete compatibility with existing Bootstrap components
- **Mobile Optimizations**:
  - Responsive table layouts with hidden columns on small screens
  - Mobile-specific status displays and button layouts
  - Touch-friendly form controls (44px minimum height)
  - Optimized font sizes and spacing for mobile devices
  - Stack layout for action buttons on small screens
- **Performance**:
  - CSS custom properties for instant theme switching
  - Minimal JavaScript footprint for theme management
  - Smooth transitions without layout shifts
  - Chart theme updates integrated with theme switching
- **Contrast Issues Resolved**:
  - Fixed text visibility problems in light theme
  - Corrected table background and text colors for both themes
  - Enhanced specificity with theme-specific CSS rules
  - Ensured proper contrast ratios for accessibility

### Complete User Management CRUD System (July 19, 2025)
- **Master User Management**: Full CRUD operations for administrators
  - Create, edit, delete administrators with proper validation
  - Change password functionality for administrators
  - Site assignment management with modal interface
  - Comprehensive user information display and management
- **Admin User Management**: Full CRUD operations for vendors
  - Create, edit, delete vendors within assigned sites
  - Change vendor passwords with admin privileges
  - User status management (activate/deactivate)
  - Performance tracking and statistics display
- **Personal Profile Management**: Self-service password changes
  - Secure password change with current password verification
  - Universal profile page for all user types
  - User information display and management
- **Enhanced Template System**: 
  - New templates: profile.html, edit_admin.html, change_admin_password.html
  - Updated manage_admins.html and manage_vendors.html with action buttons
  - Admin templates: edit_vendor.html, change_vendor_password.html
  - Responsive button groups and confirmation dialogs
- **Security Improvements**:
  - Password validation and confirmation requirements
  - Username and email uniqueness validation
  - User type verification and authorization checks
  - Site-based access control for vendor management
- **User Interface Enhancements**:
  - Action button groups with edit, password, and delete options
  - Confirmation dialogs for destructive operations
  - Form validation with error display
  - Consistent styling with theme system integration

### Admin Voucher Printing Permissions (July 19, 2025)
- **Issue Resolution**: Corrected administrator permissions for voucher printing
- **Full Admin Functionality**: Administrators now have complete voucher management access
  - Voucher creation identical to vendor interface
  - PDF generation and printing capabilities
  - Multi-format support (A4 and thermal printer formats)
  - Real-time synchronization with Omada Controller
- **Enhanced Admin Interface**: All vendor functions available to administrators
  - Complete voucher history management
  - Sales reporting and analytics
  - Cash register management system
  - Voucher deletion and cleanup operations

### PWA Implementation and Enhanced Responsiveness (July 19, 2025)
- **Progressive Web App Features**: Complete PWA transformation
  - Service Worker for offline functionality and caching
  - Web App Manifest with app icons and shortcuts
  - Install prompt for native app-like experience
  - Push notification support and offline detection
  - Auto-update mechanism with user notification
- **Enhanced Mobile Responsiveness**: 
  - Touch-friendly interface with 44px minimum button sizes
  - iOS zoom prevention with proper input font sizes
  - Responsive sidebar that collapses on mobile
  - Mobile-optimized table layouts with hidden columns
  - Tablet and large screen optimizations
- **Accessibility Improvements**:
  - High contrast mode support
  - Reduced motion support for users with vestibular disorders
  - Improved focus management with visible outlines
  - Touch-friendly animations and hover states
- **Offline Capabilities**:
  - Cached resources for offline browsing
  - Offline page with connection retry functionality
  - Visual offline indicator with automatic reconnection
  - Service Worker manages cache updates and versioning
- **Performance Optimizations**:
  - Print-friendly styles for reports and vouchers
  - Loading states with visual feedback
  - Optimized CSS for different screen sizes
  - Reduced motion preferences respected

### VPS Deployment Preparation (July 10, 2025)
- **Production Ready**: Application tested and optimized for deployment
- **Theme System**: Fully functional light/dark mode with proper contrast
- **Mobile Responsive**: Complete mobile optimization implemented
- **Performance**: Optimized for production use with proper caching and minification
- **Database Migration**: Updated deployment scripts from PostgreSQL to MySQL
- **Interactive Installation**: Created interactive install_vps.sh script that prompts for configurations
- **Automated Deployment**: Script automatically moves files, configures services, and starts application
- **Download Script**: Added download_and_install.sh for complete automation from repository
- **SSL Support**: Optional Let's Encrypt SSL installation during setup
- **Backup System**: Automatic backup script creation and configuration
- **Remote Database Support**: Added support for remote MySQL/MariaDB and PostgreSQL databases
- **Database Choice Menu**: Interactive selection between local MySQL, remote MySQL, or remote PostgreSQL
- **Connection Testing**: Automatic database connection validation during installation
- **Driver Management**: Automatic installation of appropriate database drivers (PyMySQL/psycopg2)

### GitHub Installation Method (July 10, 2025)
- **One-Line Installation**: Created quick_install.sh for single-command deployment
- **GitHub Integration**: Complete installation script that downloads from GitHub repository
- **Automated Setup**: Downloads, configures, and deploys application automatically
- **Error Template Fix**: Added missing error templates (404.html, 500.html, 403.html) to prevent template errors
- **Comprehensive Guide**: Created GITHUB_INSTALL.md with detailed instructions
- **Multi-Database Support**: GitHub installer supports MySQL local, MySQL remote, and PostgreSQL remote
- **Production Ready**: Includes nginx, supervisor, firewall, and SSL configuration
- **Import Error Resolution**: Fixed Gunicorn import issues with environment variable configuration
- **Testing Integration**: Added automated testing of application import and database connection
- **Enhanced Debugging**: Improved error logging and troubleshooting in installation script
- **GitHub Repository**: https://github.com/Joelferreira98/OmadaVoucherController
- **Simple Commands**: 
  - Quick: `curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/quick_install.sh | sudo bash`
  - Manual: Download github_install.sh and execute
- **Upload Scripts**: Created prepare_github.sh and upload_to_github.sh for easy repository management

### Manual Installation System (July 10, 2025)
- **Complete Manual Installation Guide**: Created comprehensive MANUAL_INSTALL.md and SIMPLE_MANUAL_INSTALL.md
- **Git Clone Method**: Direct cloning from GitHub with manual configuration
- **Environment Configuration**: Detailed .env file setup for MySQL local and remote connections
- **Step-by-Step Process**: 
  1. System preparation with dependencies
  2. Git clone and file copying
  3. Python virtual environment setup
  4. Database configuration and testing
  5. Application testing and production setup
- **Multiple Installation Options**:
  - Development setup (direct Python execution)
  - Production setup (Nginx + Supervisor)
  - VPS-specific installation (install_vps.sh)
  - Complete removal system (uninstall.sh, cleanup.sh)
- **Troubleshooting Tools**: Database connection testing scripts and diagnostic tools
- **Simplified Configuration**: app_requirements.txt with all necessary dependencies

### Gunicorn Import Error Resolution (July 10, 2025)
- **Critical Issue**: VPS installations failing with Gunicorn import errors due to main.py structure
- **Root Cause**: Gunicorn unable to find Flask app object in main.py module
- **Solution Implemented**:
  - Completely rewrote main.py to expose Flask app correctly for Gunicorn
  - Added proper logging and error handling for production environment
  - Created both 'app' and 'application' objects for compatibility
  - Enhanced error reporting with traceback for debugging
  - Added environment detection for development vs production modes
- **Script Corrections**:
  - Updated all installation scripts (github_install.sh, simple_install.sh, debug_install.sh)
  - Fixed Gunicorn command line arguments to use proper binding and workers
  - Removed gunicorn.conf.py dependency in favor of inline configuration
  - Added fix_gunicorn.sh script for existing installations
- **Production Deployment**: 
  - All scripts now use: `gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 30 --keep-alive 2 --max-requests 1000 --preload main:app`
  - Proper environment variable handling through supervisor
  - Enhanced error logging to /var/log/voucher-app.log
  - Automated testing of app import before service start

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