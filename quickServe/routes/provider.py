from flask import Blueprint,request,render_template,url_for,flash,redirect
from flask_login import login_required,current_user

from ..extensions import db
from ..models import Service,Booking

bp = Blueprint('provider',__name__)

@bp.route('/create_service',methods=['GET','POST'])
@login_required
def create_service():
    if current_user.role != 'provider':
        flash('Only service providers can create services.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        location = request.form['location']

        new_service = Service(provider_id = current_user.id,name = name,description = description , price = price,
                              location = location)

        db.session.add(new_service)
        db.session.commit()
        flash('Service created successfully!', 'success')
        return redirect(url_for('main.services'))

    return render_template('create_service.html')

@bp.route('/provider/notifications')
@login_required
def provider_notifications():
    if current_user.role != 'provider':
        flash("Access Denied", "danger")
        return redirect(url_for('main.index'))

    bookings = Booking.query.filter_by(provider_id=current_user.id).order_by(Booking.timestamp.desc()).all()
    return render_template('provider_notifications.html',bookings = bookings)

@bp.route('/booking/<int:booking_id>/<action>')
@login_required
def update_booking_status(booking_id, action):
    booking = Booking.query.get_or_404(booking_id)
    if current_user.id != booking.provider_id:
        flash("Unauthorized!", "danger")
        return redirect(url_for('main.index'))

    if action == "accept":
        booking.status = "Accepted"
    elif action == "reject":
        booking.status = "Rejected"
    db.session.commit()
    flash("Booking status updated!", "success")
    return redirect(url_for('provider.provider_notifications'))