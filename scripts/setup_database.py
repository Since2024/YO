#!/usr/bin/env python3
"""
Database Setup Script for SmartForm

This script initializes the SmartForm database with:
- Database tables creation
- Default admin user
- Sample templates
- Initial configuration
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, create_tables, get_db_session
from database.models import User, Template, SystemConfig
from werkzeug.security import generate_password_hash


def create_default_admin():
    """Create default admin user."""
    with get_db_session() as session:
        # Check if admin user already exists
        admin_user = session.query(User).filter_by(username='admin').first()
        
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@smartform.com',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                is_active=True
            )
            session.add(admin_user)
            session.commit()
            print("✅ Default admin user created")
            print("   Username: admin")
            print("   Password: admin123")
        else:
            print("ℹ️  Admin user already exists")


def create_sample_templates():
    """Create sample templates from existing JSON files."""
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    
    if not os.path.exists(templates_dir):
        print("⚠️  Templates directory not found")
        return
    
    with get_db_session() as session:
        # Get admin user for template creation
        admin_user = session.query(User).filter_by(username='admin').first()
        if not admin_user:
            print("❌ Admin user not found. Please create admin user first.")
            return
        
        # Load existing JSON templates
        template_files = [
            'business_tax.json',
            'land_tax.json',
            'high_contrast_business_tax.json'
        ]
        
        for template_file in template_files:
            template_path = os.path.join(templates_dir, template_file)
            
            if os.path.exists(template_path):
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    
                    # Check if template already exists
                    existing_template = session.query(Template).filter_by(
                        name=template_data.get('name', template_file)
                    ).first()
                    
                    if not existing_template:
                        template = Template(
                            name=template_data.get('name', template_file.replace('.json', '')),
                            description=template_data.get('description', f'Sample {template_file} template'),
                            form_type=template_data.get('form_type', 'business_tax'),
                            fields=template_data.get('fields', []),
                            file_path=template_path,
                            created_by=admin_user.id,
                            is_active=True
                        )
                        session.add(template)
                        print(f"✅ Created template: {template.name}")
                    else:
                        print(f"ℹ️  Template already exists: {existing_template.name}")
                        
                except Exception as e:
                    print(f"❌ Error loading template {template_file}: {e}")
        
        session.commit()


def create_system_config():
    """Create initial system configuration."""
    with get_db_session() as session:
        configs = [
            {
                'config_key': 'system_name',
                'config_value': 'SmartForm OCR System',
                'description': 'System display name'
            },
            {
                'config_key': 'max_file_size',
                'config_value': '16777216',  # 16MB in bytes
                'description': 'Maximum file upload size in bytes'
            },
            {
                'config_key': 'allowed_file_types',
                'config_value': 'pdf,jpg,jpeg,png,tiff,bmp',
                'description': 'Comma-separated list of allowed file extensions'
            },
            {
                'config_key': 'ocr_language',
                'config_value': 'eng',
                'description': 'Default OCR language'
            },
            {
                'config_key': 'processing_timeout',
                'config_value': '300',  # 5 minutes
                'description': 'Processing timeout in seconds'
            }
        ]
        
        for config_data in configs:
            existing_config = session.query(SystemConfig).filter_by(
                config_key=config_data['config_key']
            ).first()
            
            if not existing_config:
                config = SystemConfig(**config_data)
                session.add(config)
                print(f"✅ Created config: {config_data['config_key']}")
            else:
                print(f"ℹ️  Config already exists: {config_data['config_key']}")
        
        session.commit()


def check_database_connection():
    """Check if database connection is working."""
    try:
        db_manager = init_db()
        if db_manager.check_connection():
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False


def main():
    """Main setup function."""
    print("🚀 SmartForm Database Setup")
    print("=" * 40)
    
    # Check database connection
    if not check_database_connection():
        print("❌ Cannot proceed without database connection")
        return
    
    # Create tables
    print("\n📊 Creating database tables...")
    create_tables()
    
    # Create default admin user
    print("\n👤 Creating default admin user...")
    create_default_admin()
    
    # Create sample templates
    print("\n📋 Creating sample templates...")
    create_sample_templates()
    
    # Create system configuration
    print("\n⚙️  Creating system configuration...")
    create_system_config()
    
    print("\n🎉 Database setup completed successfully!")
    print("\n📝 Next steps:")
    print("1. Run the web application: python web_app.py")
    print("2. Access the web interface at: http://localhost:5000")
    print("3. Login with admin/admin123")
    print("4. Start processing forms!")


if __name__ == '__main__':
    main()
