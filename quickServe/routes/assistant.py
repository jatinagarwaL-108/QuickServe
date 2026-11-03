from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app
)

from flask_login import login_required, current_user

from langchain_core.messages import (
    HumanMessage,
    AIMessage
)

from ..extensions import db
from ..models import chatbotSession, ChatbotMessage
from ..services.chat_graph import chatbot


bp = Blueprint('assistant', __name__)


# --------------------------------
# Get or create chatbot session
# --------------------------------

def get_chat_session():

    chat_session_id = session.get('chatbot_session_id')

    chat_session = None

    if chat_session_id:

        chat_session = chatbotSession.query.filter_by(
            id=chat_session_id,
            user_id=current_user.id
        ).first()

    if not chat_session:

        chat_session = chatbotSession(
            user_id=current_user.id
        )

        db.session.add(chat_session)
        db.session.commit()

        session['chatbot_session_id'] = chat_session.id

    return chat_session


# --------------------------------
# Load conversation history
# --------------------------------

def get_graph_messages(chat_session):

    history = []

    messages = ChatbotMessage.query.filter_by(
        session_id=chat_session.id
    ).order_by(
        ChatbotMessage.created_at,
        ChatbotMessage.id
    ).all()

    for msg in messages:

        if msg.sender == 'user':

            history.append(
                HumanMessage(content=msg.message)
            )

        elif msg.sender == 'assistant':

            history.append(
                AIMessage(content=msg.message)
            )

    return history


# --------------------------------
# Chat route
# --------------------------------

@bp.route('/assistant/chat', methods=['GET', 'POST'])
@login_required
def chat():

    # Start a new conversation
    if request.args.get('reset'):

        session.pop('chatbot_session_id', None)

        return redirect(url_for('assistant.chat'))

    chat_session = get_chat_session()

    # --------------------------------
    # Handle customer message
    # --------------------------------

    if request.method == 'POST':

        message = request.form.get(
            'message', ''
        ).strip()[:500]

        if not message:

            flash(
                'Please type a message.',
                'danger'
            )

        else:

            try:

                # Save user message
                user_message = ChatbotMessage(
                    session_id=chat_session.id,
                    sender='user',
                    message=message
                )

                db.session.add(user_message)
                db.session.commit()

                # Load complete conversation history
                history = get_graph_messages(chat_session)

                # Load previously collected information
                collected = chat_session.collected_data or {}

                # Prepare LangGraph input
                initial_state = {

                    'messages': history,

                    'category': collected.get('category'),

                    'area': collected.get('area'),

                    'unknown_area': collected.get('unknown_area'),

                    'any_area': collected.get(
                        'any_area', False
                    ),

                    'max_price': collected.get('max_price'),

                    'problem_description': collected.get(
                        'problem_description'
                    )
                }

                # Run chatbot
                response = chatbot.invoke(initial_state)

                # Get assistant response
                assistant_message = response['messages'][-1]

                # Save assistant message
                db.session.add(
                    ChatbotMessage(
                        session_id=chat_session.id,
                        sender='assistant',
                        message=str(assistant_message.content)
                    )
                )

                # --------------------------------
                # Save extracted customer details
                # --------------------------------

                chat_session.collected_data = {

                    'category': (
                        response.get('category')
                        or collected.get('category')
                    ),

                    'area': (
                        response.get('area')
                        or collected.get('area')
                    ),

                    'unknown_area': response.get(
                        'unknown_area'
                    ),

                    'any_area': response.get(
                        'any_area',
                        collected.get('any_area', False)
                    ),

                    'max_price': (
                        response.get('max_price')
                        or collected.get('max_price')
                    ),

                    'problem_description': (
                        response.get('problem_description')
                        or collected.get('problem_description')
                    ),

                    'results': response.get('results')
                }

                db.session.commit()

            except Exception:

                db.session.rollback()

                current_app.logger.exception(
                    'Chat graph failed'
                )

                flash(
                    'Sorry, something went wrong. Please try again.',
                    'danger'
                )

        return redirect(
            url_for('assistant.chat')
        )

    # --------------------------------
    # Display conversation
    # --------------------------------

    messages = ChatbotMessage.query.filter_by(
        session_id=chat_session.id
    ).order_by(
        ChatbotMessage.created_at,
        ChatbotMessage.id
    ).all()

    collected = chat_session.collected_data or {}

    return render_template(
        'assistant_chat.html',
        messages=messages,
        results=collected.get('results')
    )