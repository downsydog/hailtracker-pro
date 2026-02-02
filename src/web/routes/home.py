"""
Home/landing page routes
"""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

home_bp = Blueprint('home', __name__)


@home_bp.route('/')
def index():
    """Home page"""

    # If logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('crm.dashboard'))

    # Show landing page
    return render_template('home/index.html')


@home_bp.route('/about')
def about():
    """About page"""
    return render_template('home/about.html')


@home_bp.route('/pricing')
def pricing():
    """Pricing page"""
    return render_template('home/pricing.html')
