"""Frontend routes - serves HTML pages using Jinja2 templates."""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

frontend_bp = Blueprint(
    'frontend',
    __name__,
    template_folder='../templates',
    static_folder='../static',
)


@frontend_bp.route('/')
def index():
    """Redirect to dashboard if logged in, otherwise to login."""
    if current_user.is_authenticated:
        return redirect(url_for('frontend.dashboard'))
    return redirect(url_for('frontend.login'))


@frontend_bp.route('/login')
def login():
    """Login page."""
    if current_user.is_authenticated:
        return redirect(url_for('frontend.dashboard'))
    return render_template('login.html')


@frontend_bp.route('/register')
def register():
    """Registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('frontend.dashboard'))
    return render_template('register.html')


@frontend_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')


@frontend_bp.route('/income')
@login_required
def income():
    """Income entry page."""
    return render_template('income.html')


@frontend_bp.route('/expenses')
@login_required
def expenses():
    """Expenses management page."""
    return render_template('expenses.html')


@frontend_bp.route('/heatmap')
@login_required
def heatmap():
    """Heatmap visualization page."""
    return render_template('heatmap.html')


@frontend_bp.route('/reports')
@login_required
def reports():
    """Reports page."""
    return render_template('reports.html')
