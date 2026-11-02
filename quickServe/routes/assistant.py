import uuid

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from flask_login import login_required, current_user
from langchain_core.messages import HumanMessage

from ..services.chat_graph import chatbot

bp = Blueprint('assistant', __name__)


def _thread_config():
    """One conversation per logged-in user, held in the signed session cookie."""
    if 'chat_thread' not in session:
        session['chat_thread'] = uuid.uuid4().hex
    return {'configurable': {'thread_id': f"{current_user.id}-{session['chat_thread']}"}}


@bp.route('/assistant/chat', methods=['GET', 'POST'])
@login_required          # stops anonymous visitors from using up your API quota
def chat():
    if request.args.get('reset'):
        session.pop('chat_thread', None)
        return redirect(url_for('assistant.chat'))

    config = _thread_config()

    if request.method == 'POST':
        message = request.form.get('message', '').strip()[:500]
        if not message:
            flash('Please type a message.', 'danger')
        else:
            try:
                chatbot.invoke({'messages': [HumanMessage(content=message)]}, config=config)
            except Exception:
                current_app.logger.exception('Chat graph failed')
                flash('Sorry, something went wrong. Please try again.', 'danger')
        return redirect(url_for('assistant.chat'))     # avoids re-sending the message on refresh

    values = chatbot.get_state(config).values          # empty dict for a new chat
    return render_template('assistant_chat.html',
                           messages=values.get('messages', []),
                           results=values.get('results'))