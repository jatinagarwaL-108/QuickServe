from flask import render_template,request,redirect,url_for,Blueprint,flash
from flask_login import login_required,current_user

from ..extensions import db
from ..models import Service,Booking,Complaint

bp = Blueprint('customer',__name__)

@bp.route('/book/<int:service_id>',methods = ['GET','POST'])
@login_required
def book(service_id):
    service = Service.query.get_or_404(service_id)
    provider_id = service.provider_id

    if request.method == 'POST':
        age_text = request.form.get('age','').strip()
        age = int(age_text) if age_text.isdigit() else None
        booking = Booking(
            customer_id=current_user.id,
            provider_id=provider_id,
            service_id=service.id,
            customer_name=request.form['customer_name'],
            age=age,
            gender=request.form['gender'],
            address=request.form['address'],
            date=request.form['date'],
            time=request.form['time'],
            payment_method=request.form['payment_method'],
            status="Pending"
        )

        db.session.add(booking)
        db.session.commit()
        flash("Booking request sent to provider!", "success")
        return redirect(url_for('customer.customer_notifications'))
    return render_template('booking_form.html',service=service)

@bp.route('/hire/<int:service_id>')
@login_required
def hire(service_id):
    service = Service.query.get_or_404(service_id)
    new_booking = Booking(customer_id=current_user.id, provider_id=service.provider_id,
                          service_id=service.id, status="Hired")
    db.session.add(new_booking)
    db.session.commit()
    return redirect(url_for('customer.rate_service', booking_id=new_booking.id))

@bp.route('/rate/<int:booking_id>',methods = ['GET','POST'])
@login_required
def rate_service(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.customer_id != current_user.id:
        flash("You can only rate your own bookings.", "danger")
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        rating = int(request.form['rating'])

        if 1 <= rating <= 5:
            booking.rating = rating
            db.session.commit()
            flash("Thank you for rating!", "success")
            return redirect(url_for('main.index'))
        else:
            flash("Invalid rating.", "danger")

    return render_template('rate_service.html', booking=booking)

@bp.route('/complaint',methods = ['GET','POST'])
@login_required
def complaint():
    if request.method == 'POST':
        complaint_text = request.form['complaint_text']
        if complaint_text.strip():
            new_complaint = Complaint(user_id=current_user.id, complaint_text=complaint_text)
            db.session.add(new_complaint)
            db.session.commit()
            flash("Your complaint has been submitted successfully.", "success")
        else:
            flash("Complaint cannot be empty.", "danger")

    my_complaints = Complaint.query.filter_by(user_id=current_user.id).order_by(Complaint.timestamp.desc()).all()
    return render_template('complaint.html', my_complaints=my_complaints)

@bp.route('/submit_complaint', methods=['POST'])
@login_required
def submit_complaint():
    message = request.form['message']
    new_complaint = Complaint(user_id=current_user.id, complaint_text=message)
    db.session.add(new_complaint)
    db.session.commit()
    flash("Your complaint has been submitted successfully!", "success")
    return redirect(request.referrer or url_for('main.index'))

@bp.route('/customer/notifications')
@login_required
def customer_notifications():
    if current_user.role != 'customer':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('main.index'))

    notifications = Booking.query.filter_by(customer_id=current_user.id).order_by(Booking.timestamp.desc()).all()
    return render_template('customer_notifications.html', notifications=notifications)