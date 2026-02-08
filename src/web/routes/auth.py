"""
Authentication Routes
Handles login, logout, registration, password reset
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from src.auth.auth_manager import AuthManager
from src.auth.user_model import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
auth_manager = AuthManager()

# ============================================================================
# LOGIN / LOGOUT
# ============================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""

    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('app.dashboard'))

    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        if not username_or_email or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('auth/login.html')

        ip_address = request.remote_addr

        # Authenticate
        user_dict = auth_manager.authenticate_user(username_or_email, password, ip_address)

        if user_dict:
            user = User(user_dict)
            login_user(user, remember=remember)

            flash(f'Welcome back, {user.full_name}!', 'success')

            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('app.dashboard'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout"""

    auth_manager.log_audit(
        current_user.id,
        'logout',
        'user',
        current_user.id,
        f'User {current_user.username} logged out',
        request.remote_addr
    )

    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


# ============================================================================
# REGISTRATION
# ============================================================================

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""

    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('app.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()

        # Validation
        errors = []

        if not email:
            errors.append('Email is required.')
        if not username:
            errors.append('Username is required.')
        if not password:
            errors.append('Password is required.')
        if not full_name:
            errors.append('Full name is required.')

        if password != confirm_password:
            errors.append('Passwords do not match.')

        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')

        if len(username) < 3:
            errors.append('Username must be at least 3 characters.')

        if '@' not in email:
            errors.append('Please enter a valid email address.')

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html')

        # Create user
        user_id = auth_manager.create_user(
            email=email,
            username=username,
            password=password,
            full_name=full_name,
            role='sales',  # Default role for new users
            company_id=1   # Demo company (in production, handle this differently)
        )

        if user_id:
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Username or email already exists. Please try different credentials.', 'error')

    return render_template('auth/register.html')


# ============================================================================
# PASSWORD RESET
# ============================================================================

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page"""

    if request.method == 'POST':
        email = request.form.get('email', '').strip()

        if not email:
            flash('Please enter your email address.', 'error')
            return render_template('auth/forgot_password.html')

        # Generate reset token
        token = auth_manager.generate_reset_token(email)

        if token:
            # TODO: Send email with reset link in production
            # For development, we'll show the token
            reset_url = url_for('auth.reset_password', token=token, _external=True)

            flash(f'Password reset link: {reset_url}', 'info')
            flash('(In production, this would be sent via email)', 'warning')
        else:
            # Don't reveal if email exists for security
            flash('If that email exists in our system, a reset link has been sent.', 'info')

        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/reset_password.html', token=token)

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('auth/reset_password.html', token=token)

        # Reset password
        success = auth_manager.reset_password(token, password)

        if success:
            flash('Password reset successfully! Please log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid or expired reset token. Please request a new one.', 'error')
            return redirect(url_for('auth.forgot_password'))

    return render_template('auth/reset_password.html', token=token)


# ============================================================================
# USER PROFILE
# ============================================================================

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""

    user_dict = auth_manager.get_user_by_id(current_user.id)
    permissions = auth_manager.get_user_permissions(current_user.id)
    audit_log = auth_manager.get_audit_log(current_user.id, limit=20)

    return render_template('auth/profile.html',
                         user=user_dict,
                         permissions=permissions,
                         audit_log=audit_log)


@auth_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""

    full_name = request.form.get('full_name', '').strip()
    phone = request.form.get('phone', '').strip()

    if not full_name:
        flash('Full name is required.', 'error')
        return redirect(url_for('auth.profile'))

    auth_manager.update_user(current_user.id, full_name=full_name, phone=phone)

    flash('Profile updated successfully.', 'success')
    return redirect(url_for('auth.profile'))


@auth_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Change password"""

    old_password = request.form.get('old_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    # Validation
    if not old_password or not new_password:
        flash('Please fill in all password fields.', 'error')
        return redirect(url_for('auth.profile'))

    if new_password != confirm_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('auth.profile'))

    if len(new_password) < 8:
        flash('Password must be at least 8 characters.', 'error')
        return redirect(url_for('auth.profile'))

    # Change password
    success = auth_manager.change_password(current_user.id, old_password, new_password)

    if success:
        flash('Password changed successfully.', 'success')
    else:
        flash('Current password is incorrect.', 'error')

    return redirect(url_for('auth.profile'))


# ============================================================================
# API ENDPOINTS
# ============================================================================

@auth_bp.route('/api/check-username', methods=['POST'])
def check_username():
    """Check if username is available (for registration form)"""

    username = request.json.get('username', '').strip()

    if not username:
        return {'available': False, 'message': 'Username is required'}

    conn = auth_manager.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    exists = cursor.fetchone() is not None
    conn.close()

    return {
        'available': not exists,
        'message': 'Username already taken' if exists else 'Username available'
    }


@auth_bp.route('/api/check-email', methods=['POST'])
def check_email():
    """Check if email is available (for registration form)"""

    email = request.json.get('email', '').strip()

    if not email:
        return {'available': False, 'message': 'Email is required'}

    conn = auth_manager.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    exists = cursor.fetchone() is not None
    conn.close()

    return {
        'available': not exists,
        'message': 'Email already registered' if exists else 'Email available'
    }


# ============================================================================
# LEGAL PAGES
# ============================================================================

@auth_bp.route('/terms')
def terms():
    """Terms of Service page"""
    return render_template('legal/terms.html')


@auth_bp.route('/privacy')
def privacy():
    """Privacy Policy page"""
    return render_template('legal/privacy.html')
