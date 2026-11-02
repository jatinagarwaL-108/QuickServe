from sqlalchemy import func
from ..extensions import db
from ..models import Service,Review

WEIGHTS = {'rating': 0.60, 'area': 0.25, 'price': 0.15}

PRIOR_WEIGHT = 5

def search_services(category_id,area_id=None,max_price=None,limit=10):

    query = Service.query.filter(
        Service.is_available == True,
        Service.category_id == category_id
    )

    if max_price is not None:
        query = query.filter(Service.price <= max_price)

    services = query.all()

    # means there is no service present in the database
    if not services:
        return []

    rows = db.session.query(Review.service_id,func.count(Review.id),func.avg(Review.rating)).filter(Review.service_id.in_([s.id for s in services])).group_by(Review.service_id).all()


    stats = {service_id: (count,float(avg)) for service_id,count,avg in rows}

    overall = db.session.query(func.avg(Review.rating)).scalar()
    overall = float(overall) if overall else 4.0

    results=[]
    for s in services:
        count,avg = stats.get(s.id,(0,0.0))

        adjusted = (PRIOR_WEIGHT * overall + count * avg) / (PRIOR_WEIGHT + count)
        rating_part = adjusted / 5

        area_part = 1.0 if (area_id is None or s.area_id == area_id) else 0.0
        price_part = 1.0 if not max_price else 1 - 0.5 * (s.price / max_price)

        score = (WEIGHTS['rating'] * rating_part
                 + WEIGHTS['area'] * area_part
                 + WEIGHTS['price'] * price_part)

        reasons = [f"{avg:.1f} stars from {count} reviews" if count else "No reviews yet"]
        if area_id is not None:
            reasons.append("In your area" if s.area_id == area_id else f"Outside your area ({s.location})")
        if max_price:
            reasons.append(f"₹{s.price:.0f} is within your budget of ₹{max_price:.0f}")

        results.append({'service': s, 'score': score, 'review_count': count, 'reasons': reasons})

    results.sort(key=lambda r: (r['score'], r['review_count']), reverse=True)
    return results[:limit]


    
