
import difflib
import os

from typing import Annotated, Optional, TypedDict

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage
)

from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from pydantic import BaseModel

from ..models import Category, Area
from .search_service import search_services


# --------------------------------
# Customer details extracted by LLM
# --------------------------------

class CustomerDetails(BaseModel):
    category: Optional[str] = None
    area: Optional[str] = None
    any_area: bool = False
    max_price: Optional[float] = None
    problem_description: Optional[str] = None


# --------------------------------
# LangGraph state
# --------------------------------

class ChatState(TypedDict, total=False):

    messages: Annotated[list, add_messages]

    category: Optional[str]
    area: Optional[str]

    unknown_area: Optional[str]

    any_area: bool

    max_price: Optional[float]

    problem_description: Optional[str]

    results: Optional[list]


# --------------------------------
# LLM configuration
# --------------------------------

llm = ChatGoogleGenerativeAI(
    model=os.environ.get(
        'LLM_MODEL',
        'gemini-3.5-flash-lite'
    ),
    max_retries=2,
    timeout=15
)

extractor = llm.with_structured_output(CustomerDetails)


# --------------------------------
# Match extracted names with DB
# --------------------------------

def real_name(value, names):

    if not value:
        return None

    by_lower = {
        name.lower(): name
        for name in names
    }

    close = difflib.get_close_matches(
        value.strip().lower(),
        list(by_lower),
        n=1,
        cutoff=0.8
    )

    return by_lower[close[0]] if close else None


# --------------------------------
# Extract customer details
# --------------------------------

def extract_details(state: ChatState):

    categories = [
        c.name for c in Category.query.all()
    ]

    areas = [
        a.name for a in Area.query.all()
    ]

    # Get only customer messages, not assistant messages.
    customer_messages = [
        str(msg.content)[:500]
        for msg in state['messages']
        if isinstance(msg, HumanMessage)
    ]

    conversation = "\n".join(
        customer_messages[-12:]
    )

    prompt = (
        "Extract customer requirements for a home services marketplace.\n\n"

        f"Available categories: {categories}\n"
        f"Supported areas: {areas}\n\n"

        "Use all customer messages to understand the complete request.\n"

        "category: Select the matching category from available categories. "
        "Infer it from the problem where possible. Otherwise null.\n"

        "area: Extract the location mentioned by the customer, even if "
        "it is not supported. Otherwise null.\n"

        "any_area: True only if the customer explicitly requests "
        "any area or anywhere.\n"

        "max_price: Extract the maximum budget in INR. "
        "Convert 1k to 1000. Otherwise null.\n"

        "problem_description: Summarize the actual problem in one short "
        "sentence. Exclude location, budget and category. "
        "Otherwise null.\n\n"

        "If the customer corrects an earlier detail, use the latest "
        "correction. Do not treat an assistant question as a customer "
        "requirement. Never invent information."
    )

    result = extractor.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=conversation)
    ])

    if result is None:
        return {
            'results': None,
            'unknown_area': None
        }

    # Match category with database
    new_category = real_name(
        result.category,
        categories
    )

    # Match area with database
    new_area = real_name(
        result.area,
        areas
    )

    unknown_area = (
        result.area
        if result.area and not new_area
        else None
    )

    # Preserve existing area
    area = state.get('area')
    any_area = state.get('any_area', False)

    if new_area:
        area = new_area
        any_area = False

    elif unknown_area:
        area = None
        any_area = False

    elif result.any_area:
        area = None
        any_area = True

    # Preserve existing budget if not provided again
    max_price = (
        result.max_price
        if result.max_price is not None and result.max_price > 0
        else state.get('max_price')
    )

    # Preserve previously extracted problem
    problem_description = (
        result.problem_description
        if result.problem_description
        else state.get('problem_description')
    )

    return {

        'category': (
            new_category
            or state.get('category')
        ),

        'area': area,

        'unknown_area': unknown_area,

        'any_area': any_area,

        'max_price': max_price,

        'problem_description': problem_description,

        'results': None
    }


# --------------------------------
# Check required details
# --------------------------------

def check_details(state: ChatState):

    if not state.get('category') or not (
        state.get('area') or state.get('any_area')
    ):
        return 'ask'

    return 'search'


# --------------------------------
# Ask for missing information
# --------------------------------

def ask_missing_details(state: ChatState):

    prefix = ''

    if state.get('unknown_area'):
        prefix = (
            f"Sorry, I don't cover "
            f"'{state['unknown_area']}' yet. "
        )

    if not state.get('category'):

        text = (
            prefix
            + "Which service do you need? "
            + ', '.join(
                c.name for c in Category.query.all()
            )
            + "."
        )

    else:

        text = (
            prefix
            + "Which area are you in? "
            + ', '.join(
                a.name for a in Area.query.all()
            )
            + ". You can also say 'any area' or mention your budget."
        )

    return {
        'messages': [
            AIMessage(content=text)
        ]
    }


# --------------------------------
# Search matching services
# --------------------------------

def search(state: ChatState):

    category = Category.query.filter_by(
        name=state['category']
    ).first()

    area = (
        Area.query.filter_by(
            name=state['area']
        ).first()
        if state.get('area')
        else None
    )

    found = search_services(
        category.id,
        area.id if area else None,
        state.get('max_price')
    )

    results = [
        {
            'service_id': item['service'].id,
            'name': item['service'].name,
            'price': float(item['service'].price),
            'provider': item['service'].provider.username,
            'location': item['service'].location,

            # Combined recommendation score
            'score': round(item['score'], 3),

            'reasons': item['reasons']
        }
        for item in found
    ]

    text = (
        f"Here are the top {len(results)} "
        f"{category.name} services for you."
        if results
        else
        "I could not find any matching services. "
        "Try a higher budget or say 'any area'."
    )

    return {
        'results': results,
        'messages': [
            AIMessage(content=text)
        ]
    }


# --------------------------------
# Build LangGraph workflow
# --------------------------------

graph = StateGraph(ChatState)

graph.add_node(
    'extract_details',
    extract_details
)

graph.add_node(
    'ask_missing_details',
    ask_missing_details
)

graph.add_node(
    'search',
    search
)

graph.add_edge(
    START,
    'extract_details'
)

graph.add_conditional_edges(
    'extract_details',
    check_details,
    {
        'ask': 'ask_missing_details',
        'search': 'search'
    }
)

graph.add_edge(
    'ask_missing_details',
    END
)

graph.add_edge(
    'search',
    END
)


# --------------------------------
# Compile graph
# --------------------------------

# Conversation history is loaded from database.
chatbot = graph.compile()
