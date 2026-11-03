
from sqlalchemy import func
from ..extensions import db
from ..models import Service, Review


def search_services(category_id, area_id=None, max_price=None):

    # Only category and availability are filters
    services = Service.query.filter(
        Service.category_id == category_id,
        Service.is_available.is_(True)
    ).all()

    if not services:
        return []

    # Get price range of all candidate services
    prices = [service.price for service in services]

    min_price = min(prices)
    max_service_price = max(prices)

    # Get review statistics for these services
    service_ids = [service.id for service in services]

    review_data = db.session.query(
        Review.service_id,
        func.avg(Review.rating),
        func.count(Review.id)
    ).filter(
        Review.service_id.in_(service_ids)
    ).group_by(Review.service_id).all()

    review_stats = {}

    for service_id, avg_rating, count in review_data:
        review_stats[service_id] = (float(avg_rating), count)

    # Global average rating of candidate services' reviews
    total_reviews = sum(count for avg, count in review_stats.values())

    if total_reviews > 0:
        global_avg = sum(
            avg * count for avg, count in review_stats.values()
        ) / total_reviews
    else:
        global_avg = None

    # Data-derived smoothing factor
    if review_stats:
        smoothing = sum(
            count for avg, count in review_stats.values()
        ) / len(services)
    else:
        smoothing = 0

    results = []

    for service in services:

        # 1. Area score
        area_score = None

        if area_id is not None:
            area_score = 1 if service.area_id == area_id else 0

        # 2. Price score
        if max_service_price == min_price:
            price_score = 0.5
        else:
            price_score = (
                max_service_price - service.price
            ) / (max_service_price - min_price)

        # If customer gave a budget, also consider budget compatibility
        if max_price is not None and service.price > max_price:
            budget_fit = max_price / service.price
            price_score *= budget_fit

        # 3. Bayesian rating score
        rating_score = None

        if global_avg is not None:
            avg_rating, review_count = review_stats.get(
                service.id, (global_avg, 0)
            )

            if review_count + smoothing > 0:
                adjusted_rating = (
                    review_count * avg_rating
                    + smoothing * global_avg
                ) / (review_count + smoothing)

                rating_score = adjusted_rating / 5

        # Combine available factors
        weighted_score = 0
        total_weight = 0

        if area_score is not None:
            weighted_score += 0.50 * area_score
            total_weight += 0.50

        weighted_score += 0.25 * price_score
        total_weight += 0.25

        if rating_score is not None:
            weighted_score += 0.25 * rating_score
            total_weight += 0.25

        final_score = weighted_score / total_weight

        reasons = []

        if area_score == 1:
            reasons.append("Available in your selected area")

        if area_score == 0:
            reasons.append("Available outside your selected area")

        if max_price is not None and service.price <= max_price:
            reasons.append("Within your specified budget")

        if rating_score is not None:
            reasons.append(
                f"Customer rating: {service.avg_rating}/5"
            )

        results.append({
            "service": service,
            "score": final_score,
            "reasons": reasons
        })

    # Highest recommendation score first
    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return results
