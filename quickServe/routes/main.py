from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Service, Chat, User

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    services = Service.query.filter_by(is_available=True).order_by(Service.id).all()

    nearby_services = []
    if current_user.is_authenticated and current_user.location:
        nearby_services = Service.query.filter(
            Service.location.ilike(f"%{current_user.location}%"),
            Service.is_available == True
        ).order_by(Service.id).all()

    return render_template(
        'index.html',
        services=services,
        nearby_services=nearby_services
    )


@bp.route('/services')
def services():
    query = request.args.get('q', '')
    location = request.args.get('location', '')

    services = Service.query.filter(Service.is_available == True)

    if query:
        services = services.filter(Service.name.ilike(f"%{query}%"))
    if location:
        services = services.filter(Service.location.ilike(f"%{location}%"))

    services = services.order_by(Service.id).all()
    return render_template('services.html', services=services)


@bp.route('/chat/<int:provider_id>', methods=['GET', 'POST'])
@login_required
def chat(provider_id):
    if request.method == 'POST':
        msg = request.form['message']
        chat_msg = Chat(customer_id=current_user.id, provider_id=provider_id,
                        message=msg, sender_role=current_user.role)
        db.session.add(chat_msg)
        db.session.commit()

    chats = Chat.query.filter_by(provider_id=provider_id).order_by(Chat.timestamp.asc()).all()
    provider = db.session.get(User, provider_id)
    return render_template('chat.html', chats=chats, provider=provider)