#!/usr/bin/env python3
"""
SmartForm Web Application

Flask-based web interface for the SmartForm OCR system.
Provides web-based access to form processing, template management,
and processing history with full CRUD operations.
"""

import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Import database components
from database import init_db, get_db_session, create_tables
from database.models import User, Template, FormProcessing, FormData, ProcessingLog

# Import existing OCR components
from filler.ocr import OCRExtractor
from filler.preprocess import PreprocessorService
from filler.generate_pdf import PDFGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('output/logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
app.config['UPLOAD_FOLDER'] = 'input/uploads/pending'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize database
init_db()
create_tables()

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('input/uploads/processed', exist_ok=True)
os.makedirs('output/filled_forms', exist_ok=True)
os.makedirs('output/logs', exist_ok=True)


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login."""
    with get_db_session() as db_session:
        return db_session.query(User).get(int(user_id))


@app.route('/')
def index():
    """Home page."""
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        with get_db_session() as db_session:
            user = db_session.query(User).filter_by(username=username).first()
            
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                user.last_login = datetime.now()
                db_session.commit()
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        with get_db_session() as db_session:
            # Check if user already exists
            existing_user = db_session.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing_user:
                flash('Username or email already exists', 'error')
            else:
                # Create new user
                new_user = User(
                    username=username,
                    email=email,
                    password_hash=generate_password_hash(password),
                    role='user'
                )
                db_session.add(new_user)
                db_session.commit()
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard."""
    with get_db_session() as db_session:
        # Get user's processing statistics
        total_processings = db_session.query(FormProcessing).filter_by(user_id=current_user.id).count()
        completed_processings = db_session.query(FormProcessing).filter_by(
            user_id=current_user.id, 
            processing_status='completed'
        ).count()
        
        # Get recent processings
        recent_processings = db_session.query(FormProcessing).filter_by(
            user_id=current_user.id
        ).order_by(FormProcessing.created_at.desc()).limit(5).all()
        
        # Get available templates
        templates = db_session.query(Template).filter_by(is_active=True).all()
        
        return render_template('dashboard.html', 
                             total_processings=total_processings,
                             completed_processings=completed_processings,
                             recent_processings=recent_processings,
                             templates=templates)


@app.route('/templates')
@login_required
def list_templates():
    """List all templates."""
    with get_db_session() as db_session:
        templates = db_session.query(Template).filter_by(is_active=True).all()
        return render_template('templates/list.html', templates=templates)


@app.route('/templates/create', methods=['GET', 'POST'])
@login_required
def create_template():
    """Create new template."""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        form_type = request.form.get('form_type')
        
        # Handle file upload
        if 'template_file' in request.files:
            file = request.files['template_file']
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join('templates', filename)
                file.save(file_path)
            else:
                file_path = None
        else:
            file_path = None
        
        with get_db_session() as db_session:
            new_template = Template(
                name=name,
                description=description,
                form_type=form_type,
                fields={},  # Will be populated by template editor
                file_path=file_path,
                created_by=current_user.id
            )
            db_session.add(new_template)
            db_session.commit()
            flash('Template created successfully!', 'success')
            return redirect(url_for('list_templates'))
    
    return render_template('templates/create.html')


@app.route('/templates/<int:template_id>')
@login_required
def view_template(template_id):
    """View template details."""
    with get_db_session() as db_session:
        template = db_session.query(Template).get_or_404(template_id)
        return render_template('templates/view.html', template=template)


@app.route('/templates/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_template(template_id):
    """Edit template."""
    with get_db_session() as db_session:
        template = db_session.query(Template).get_or_404(template_id)
        
        if request.method == 'POST':
            template.name = request.form.get('name')
            template.description = request.form.get('description')
            template.form_type = request.form.get('form_type')
            template.updated_at = datetime.now()
            
            db_session.commit()
            flash('Template updated successfully!', 'success')
            return redirect(url_for('view_template', template_id=template.id))
        
        return render_template('templates/edit.html', template=template)


@app.route('/templates/<int:template_id>/delete', methods=['POST'])
@login_required
def delete_template(template_id):
    """Delete template."""
    with get_db_session() as db_session:
        template = db_session.query(Template).get_or_404(template_id)
        template.is_active = False
        db_session.commit()
        flash('Template deleted successfully!', 'success')
        return redirect(url_for('list_templates'))


@app.route('/processing/upload', methods=['GET', 'POST'])
@login_required
def upload_form():
    """Upload form for processing."""
    if request.method == 'POST':
        if 'form_file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['form_file']
        template_id = request.form.get('template_id')
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and template_id:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Create processing record
            with get_db_session() as db_session:
                processing = FormProcessing(
                    template_id=int(template_id),
                    user_id=current_user.id,
                    input_file_path=file_path,
                    processing_status='pending'
                )
                db_session.add(processing)
                db_session.commit()
                
                # Start processing in background (you might want to use Celery for this)
                process_form_async(processing.id)
                
                flash('Form uploaded successfully! Processing started.', 'success')
                return redirect(url_for('processing_history'))
    
    # Get available templates
    with get_db_session() as db_session:
        templates = db_session.query(Template).filter_by(is_active=True).all()
    
    return render_template('processing/upload.html', templates=templates)


@app.route('/processing/history')
@login_required
def processing_history():
    """View processing history."""
    with get_db_session() as db_session:
        processings = db_session.query(FormProcessing).filter_by(
            user_id=current_user.id
        ).order_by(FormProcessing.created_at.desc()).all()
        
        return render_template('processing/history.html', processings=processings)


@app.route('/processing/<int:processing_id>')
@login_required
def view_processing(processing_id):
    """View processing details."""
    with get_db_session() as db_session:
        processing = db_session.query(FormProcessing).filter_by(
            id=processing_id, 
            user_id=current_user.id
        ).first_or_404()
        
        form_data = db_session.query(FormData).filter_by(
            processing_id=processing_id
        ).all()
        
        return render_template('processing/result.html', 
                             processing=processing, 
                             form_data=form_data)


def process_form_async(processing_id):
    """Process form asynchronously (simplified version)."""
    try:
        with get_db_session() as db_session:
            processing = db_session.query(FormProcessing).get(processing_id)
            if not processing:
                return
            
            # Update status to processing
            processing.processing_status = 'processing'
            db_session.commit()
            
            # Load template
            template = db_session.query(Template).get(processing.template_id)
            if not template:
                processing.processing_status = 'failed'
                processing.error_message = 'Template not found'
                db_session.commit()
                return
            
            # Process the form using existing OCR components
            start_time = datetime.now()
            
            # Preprocess input file
            preprocessor = PreprocessorService()
            processed_images = preprocessor.process_input(processing.input_file_path)
            
            # Extract data using OCR
            ocr_extractor = OCRExtractor()
            extracted_data = {}
            
            for page_num, image in enumerate(processed_images, 1):
                page_data = ocr_extractor.extract_from_page(
                    image, template.fields, page_num
                )
                extracted_data.update(page_data)
            
            # Generate filled PDF
            pdf_generator = PDFGenerator()
            output_filename = f"filled_form_{processing_id}.pdf"
            output_path = os.path.join('output/filled_forms', output_filename)
            
            pdf_generator.create_filled_pdf(
                template.fields, extracted_data, output_path
            )
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update processing record
            processing.processing_status = 'completed'
            processing.output_file_path = output_path
            processing.extracted_data = extracted_data
            processing.processing_time = processing_time
            processing.completed_at = datetime.now()
            
            # Calculate average confidence score
            if extracted_data:
                confidence_scores = [data.get('confidence', 0) for data in extracted_data.values()]
                processing.confidence_score = sum(confidence_scores) / len(confidence_scores)
            
            # Store extracted data
            for field_name, data in extracted_data.items():
                form_data = FormData(
                    processing_id=processing.id,
                    field_name=field_name,
                    extracted_text=data.get('text', ''),
                    confidence_score=data.get('confidence', 0),
                    field_type='text'
                )
                db_session.add(form_data)
            
            # Add processing log
            log = ProcessingLog(
                processing_id=processing.id,
                log_level='INFO',
                message='Form processing completed successfully',
                details={'processing_time': processing_time}
            )
            db_session.add(log)
            
            db_session.commit()
            
    except Exception as e:
        logger.error(f"Error processing form {processing_id}: {e}")
        with get_db_session() as db_session:
            processing = db_session.query(FormProcessing).get(processing_id)
            if processing:
                processing.processing_status = 'failed'
                processing.error_message = str(e)
                db_session.commit()


@app.route('/api/templates')
@login_required
def api_templates():
    """API endpoint for templates."""
    with get_db_session() as db_session:
        templates = db_session.query(Template).filter_by(is_active=True).all()
        return jsonify([{
            'id': t.id,
            'name': t.name,
            'description': t.description,
            'form_type': t.form_type
        } for t in templates])


@app.route('/api/processing/<int:processing_id>')
@login_required
def api_processing_status(processing_id):
    """API endpoint for processing status."""
    with get_db_session() as db_session:
        processing = db_session.query(FormProcessing).filter_by(
            id=processing_id, 
            user_id=current_user.id
        ).first_or_404()
        
        return jsonify({
            'id': processing.id,
            'status': processing.processing_status,
            'progress': 100 if processing.processing_status == 'completed' else 50,
            'created_at': processing.created_at.isoformat(),
            'completed_at': processing.completed_at.isoformat() if processing.completed_at else None
        })


if __name__ == '__main__':
    # Create default admin user if not exists
    with get_db_session() as db_session:
        admin_user = db_session.query(User).filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@smartform.com',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db_session.add(admin_user)
            db_session.commit()
            print("✅ Default admin user created (username: admin, password: admin123)")
    
    print("🚀 Starting SmartForm Web Application...")
    print("📊 Database initialized and tables created")
    print("🌐 Web interface available at: http://localhost:5000")
    print("👤 Default admin login: admin / admin123")
    
    app.run(debug=True, host='0.0.0.0', port=8000)
