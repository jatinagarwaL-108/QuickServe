from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from ..extensions import db
from ..models import User, Service, Booking, Complaint

bp = Blueprint('admin', __name__)


@bp.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        flash('Admin access only.', 'danger')
        return redirect(url_for('main.index'))

    providers = User.query.filter_by(role="provider").all()
    customers = User.query.filter_by(role="customer").all()
    active_services = Service.query.filter_by(is_available=True).all()
    bookings = Booking.query.all()
    complaints = Complaint.query.order_by(Complaint.timestamp.desc()).all()

    return render_template(
        'admin_dashboard.html',
        providers=providers,
        customers=customers,
        active_services=active_services,
        bookings=bookings,
        complaints=complaints
    )


# TODO (Step F): the four routes below change data through plain links (GET).
# Make them POST forms with CSRF tokens, and return 403 for non-admins.

@bp.route('/admin/delete_provider/<int:provider_id>')
@login_required
def delete_provider(provider_id):
    if current_user.role == "admin":
        provider = User.query.get_or_404(provider_id)
        db.session.delete(provider)
        db.session.commit()
        flash("Provider account deleted!", "success")
    return redirect(url_for('admin.admin'))


@bp.route('/admin/delete_customer/<int:customer_id>')
@login_required
def delete_customer(customer_id):
    if current_user.role == "admin":
        customer = User.query.get_or_404(customer_id)
        db.session.delete(customer)
        db.session.commit()
        flash("Customer account deleted!", "success")
    return redirect(url_for('admin.admin'))


@bp.route('/admin/delete_service/<int:service_id>')
@login_required
def delete_service(service_id):
    if current_user.role == "admin":
        service = Service.query.get_or_404(service_id)
        db.session.delete(service)
        db.session.commit()
        flash("Service deleted successfully!", "success")
    return redirect(url_for('admin.admin'))


@bp.route('/admin/resolve_complaint/<int:complaint_id>')
@login_required
def resolve_complaint(complaint_id):
    if current_user.role == "admin":
        complaint = Complaint.query.get_or_404(complaint_id)
        complaint.status = "Resolved"
        db.session.commit()
        flash("Complaint marked as resolved!", "success")
    return redirect(url_for('admin.admin'))