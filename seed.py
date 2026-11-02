"""Fill the database with fake test data.

Run from the project root:
    python scripts/seed.py            # add data
    python scripts/seed.py --reset    # remove old fake data, then add new
"""
import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import or_
from sqlalchemy.engine import make_url
from werkzeug.security import generate_password_hash

from quickServe import create_app
from quickServe.extensions import db
from quickServe.models import User, Service, Booking, Review, Category, Area

random.seed(42)  # same data every run

SERVICES_PER_CATEGORY = 12
FIRST = ['Amit', 'Ravi', 'Suresh', 'Mohan', 'Vikram', 'Rahul', 'Sunil', 'Deepak',
         'Manoj', 'Anil', 'Pooja', 'Neha', 'Sita', 'Kavita', 'Rekha', 'Imran',
         'Salman', 'Arjun', 'Karan', 'Vijay']
LAST = ['Sharma', 'Verma', 'Gupta', 'Singh', 'Meena', 'Yadav', 'Khan', 'Joshi',
        'Saini', 'Jain']

MIXED = ["Work was good but arrived an hour late",
         "Did the job well, a little expensive",
         "Fixed it, but the place was left untidy"]
NEGATIVE = ["Problem came back after two days",
            "Charged more than the quoted price",
            "Arrived very late and rushed the work"]

# Category names must match the rows in your category table.
CATEGORY_DATA = {
    'AC Repair': {
        'price': (400, 1800),
        'services': ['AC gas refill', 'AC service and deep cleaning', 'AC installation', 'AC not cooling repair'],
        'positive': ["Fixed my AC that was not cooling in one visit",
                     "Gas leak found and refilled, room cools fast now",
                     "AC was dripping water inside, sorted quickly",
                     "Deep cleaning made the AC much quieter"]},
    'Plumbing': {
        'price': (200, 1200),
        'services': ['Leaking tap repair', 'Pipe leakage fix', 'Bathroom fitting', 'Drain unblocking'],
        'positive': ["Fixed the leaking pipe under my kitchen sink quickly",
                     "Blocked drain cleared and no smell afterwards",
                     "Replaced the bathroom tap neatly",
                     "Water pressure problem solved in one visit"]},
    'Electrician': {
        'price': (200, 1000),
        'services': ['Switchboard repair', 'Fan installation', 'Wiring check', 'MCB and fuse repair'],
        'positive': ["Found the fault tripping my MCB and fixed it",
                     "Fan installed neatly and works silently",
                     "Replaced old wiring safely",
                     "Sparking switchboard repaired in minutes"]},
    'Carpenter': {
        'price': (300, 2000),
        'services': ['Furniture repair', 'Door and lock fitting', 'Wardrobe assembly', 'Bed repair'],
        'positive': ["Repaired my broken wardrobe door well",
                     "Door lock fitted perfectly",
                     "Assembled the bed quickly and neatly",
                     "Squeaky drawer fixed properly"]},
    'Home Cleaning': {
        'price': (500, 3500),
        'services': ['Full home deep cleaning', 'Kitchen cleaning', 'Bathroom cleaning', 'Sofa cleaning'],
        'positive': ["Kitchen grease removed completely",
                     "Bathroom looks brand new after cleaning",
                     "Sofa stains came out well",
                     "Team was punctual and thorough"]},
    'Painting': {
        'price': (1500, 12000),
        'services': ['Interior wall painting', 'Single room painting', 'Waterproof coating', 'Texture painting'],
        'positive': ["Room painted neatly with no mess on the floor",
                     "Damp patch fixed and painted over properly",
                     "Colour matched what I wanted",
                     "Finished a day earlier than promised"]},
    'Appliance Repair': {
        'price': (300, 1500),
        'services': ['Washing machine repair', 'Refrigerator repair', 'Microwave repair', 'TV repair'],
        'positive': ["Washing machine stopped draining, now working again",
                     "Fridge was not cooling, fixed on the spot",
                     "Microwave repaired at a fair price",
                     "Explained the fault clearly before fixing"]},
    'Pest Control': {
        'price': (600, 3500),
        'services': ['Cockroach treatment', 'Termite treatment', 'Bed bug treatment', 'General pest control'],
        'positive': ["No cockroaches in the kitchen since the treatment",
                     "Termite problem handled with a clear plan",
                     "Safe for kids and pets as promised",
                     "Bed bugs gone after the follow-up visit"]},
    'Geyser Repair': {
        'price': (300, 1500),
        'services': ['Geyser not heating repair', 'Geyser installation', 'Geyser leakage repair', 'Geyser service'],
        'positive': ["Geyser was tripping the MCB, fixed in one visit",
                     "Replaced the heating element and it heats fast now",
                     "Leak from the geyser stopped completely",
                     "Installed the new geyser safely"]},
    'Salon at Home': {
        'price': (300, 6000),
        'services': ['Haircut at home', 'Facial and cleanup', 'Bridal makeup', 'Waxing and threading'],
        'positive': ["Haircut was exactly what I asked for",
                     "Clean tools and very hygienic",
                     "Facial gave a great glow",
                     "Arrived on time and set up quickly"]},
}


def review_text(rating, data):
    if rating >= 4:
        return random.choice(data['positive']) if random.random() < 0.8 else random.choice(MIXED)
    if rating == 3:
        return random.choice(MIXED)
    return random.choice(NEGATIVE)


def person_name(number):
    return f"{random.choice(FIRST)}_{random.choice(LAST)}_{number}"


def reset():
    ids = [u.id for u in User.query.filter(User.email.like('%@seed.local')).all()]
    if not ids:
        return
    Review.query.filter(or_(Review.provider_id.in_(ids), Review.customer_id.in_(ids))).delete(synchronize_session=False)
    Booking.query.filter(or_(Booking.provider_id.in_(ids), Booking.customer_id.in_(ids))).delete(synchronize_session=False)
    Service.query.filter(Service.provider_id.in_(ids)).delete(synchronize_session=False)
    User.query.filter(User.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    print(f"Removed {len(ids)} old fake users and their data.")


def main():
    app = create_app()
    with app.app_context():
        url = make_url(app.config['SQLALCHEMY_DATABASE_URI'])
        print(f"Target database: {url.drivername}  host={url.host or '(local file)'}  name={url.database}")
        print("If this is your PRODUCTION database, stop now (Ctrl+C).")
        if input("Type yes to continue: ").strip().lower() != 'yes':
            print("Cancelled.")
            return

        if '--reset' in sys.argv:
            reset()
        elif User.query.filter(User.email.like('%@seed.local')).first():
            print("Fake data already exists. Run with --reset to replace it.")
            return

        categories = {c.name: c for c in Category.query.all()}
        areas = Area.query.all()
        if not categories or not areas:
            print("Insert categories and areas first (see the starter rows).")
            return

        password_hash = generate_password_hash('Test@1234', method='pbkdf2:sha256')

        customers = []
        for i in range(1, 41):
            area = random.choice(areas)
            customer = User(username=person_name(i), email=f'customer{i}@seed.local',
                            password=password_hash, role='customer',
                            location=f"{area.name}, {area.city}", area_id=area.id)
            db.session.add(customer)
            customers.append(customer)
        db.session.flush()

        provider_no = 0
        review_count = 0
        for cat_name, data in CATEGORY_DATA.items():
            category = categories.get(cat_name)
            if not category:
                print(f"Skipping {cat_name}: not in the category table.")
                continue
            for _ in range(SERVICES_PER_CATEGORY):
                provider_no += 1
                area = random.choice(areas)
                provider = User(username=person_name(1000 + provider_no),
                                email=f'provider{provider_no}@seed.local',
                                password=password_hash, role='provider',
                                location=f"{area.name}, {area.city}", area_id=area.id)
                db.session.add(provider)
                db.session.flush()

                low, high = data['price']
                service_name = random.choice(data['services'])
                service = Service(
                    provider_id=provider.id, name=service_name,
                    description=(f"{service_name}. Experienced and verified professional covering "
                                 f"{area.name}, {area.city}. Fast response, fair pricing, and a "
                                 f"clear estimate before starting work."),
                    price=round(random.randint(low, high) / 10) * 10,
                    location=f"{area.name}, {area.city}", is_available=True,
                    category_id=category.id, area_id=area.id)
                db.session.add(service)
                db.session.flush()

                quality = random.uniform(2.8, 4.9)   # hidden "true" quality of this provider
                for _ in range(random.choice([0, 1, 2, 3, 4, 6, 8, 10, 14, 18])):
                    customer = random.choice(customers)
                    rating = min(5, max(1, round(random.gauss(quality, 0.8))))
                    when = datetime.utcnow() - timedelta(days=random.randint(5, 180))
                    booking = Booking(
                        customer_id=customer.id, provider_id=provider.id, service_id=service.id,
                        customer_name=customer.username.split('_')[0], age=random.randint(22, 60),
                        gender=random.choice(['male', 'female']),
                        address=f"{random.randint(1, 120)}, {area.name}",
                        date=when.strftime('%Y-%m-%d'), time=when.strftime('%H:%M'),
                        payment_method=random.choice(['cash', 'upi']),
                        rating=rating, status='Completed',
                        timestamp=when - timedelta(days=1), scheduled_at=when,
                        responded_at=when - timedelta(hours=random.randint(1, 24)),
                        completed_at=when + timedelta(hours=2), created_by='user')
                    db.session.add(booking)
                    db.session.flush()
                    db.session.add(Review(
                        booking_id=booking.id, customer_id=customer.id,
                        provider_id=provider.id, service_id=service.id,
                        rating=rating, text=review_text(rating, data),
                        created_at=when + timedelta(days=1)))
                    review_count += 1

        db.session.commit()
        print(f"Done: 40 customers, {provider_no} providers/services, {review_count} reviews.")
        print("All fake accounts use the password Test@1234 (never do this on a real site).")


if __name__ == '__main__':
    main()