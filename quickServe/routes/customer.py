from flask import render_template,request,redirect,url_for,Blueprint,flash,abort
from flask_login import login_required,current_user

from ..extensions import db
from ..models import Service,Booking,Complaint,Review

bp = Blueprint('customer',__name__)

@bp.route('/book/<int:service_id>',methods = ['GET','POST'])
@login_required
def book(service_id):
    if current_user.role != 'customer':
        flash("Unauthorized access for this",'danger')
        return redirect(url_for('main.index'))
    
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

@bp.route('/rate/<int:booking_id>', methods=['POST'])
@login_required
def rate_service(booking_id):
    booking = db.session.get(Booking, booking_id)
    if booking is None or booking.customer_id != current_user.id:
        abort(404)                       # not your booking, so it does not exist for you

    back = redirect(url_for('customer.customer_notifications'))

    if booking.status != 'Completed':
        flash('You can review a service only after it is completed.', 'danger')
        return back
    if booking.review:
        flash('You have already reviewed this booking.', 'warning')
        return back

    rating = request.form.get('rating', type=int)
    if rating is None or not 1 <= rating <= 5:
        flash('Please choose a rating from 1 to 5.', 'danger')
        return back

    text = request.form.get('text', '').strip()[:1000] or None

    db.session.add(Review(
        booking_id=booking.id,
        customer_id=current_user.id,
        provider_id=booking.provider_id,
        service_id=booking.service_id,
        rating=rating,
        text=text,
    ))
    booking.rating = rating              # keep the old column in step, so old pages still work

    try:
        db.session.commit()
    except IntegrityError:               # two clicks at once: the unique rule on booking_id wins
        db.session.rollback()
        flash('You have already reviewed this booking.', 'warning')
        return back

    flash('Thank you for your review!', 'success')
    return back

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