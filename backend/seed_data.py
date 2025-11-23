"""
Seed script to populate database with initial data
"""
from app.database import SessionLocal, init_db
from app.models import Interest, AIPromptTemplate


def seed_interests():
    """Seed interests"""
    db = SessionLocal()

    interests_data = [
        # Sports & Fitness
        {"name": "Yoga", "category": "sports"},
        {"name": "Running", "category": "sports"},
        {"name": "Gym", "category": "sports"},
        {"name": "Hiking", "category": "sports"},
        {"name": "Swimming", "category": "sports"},
        {"name": "Cycling", "category": "sports"},
        {"name": "Rock Climbing", "category": "sports"},

        # Arts & Culture
        {"name": "Painting", "category": "arts"},
        {"name": "Photography", "category": "arts"},
        {"name": "Museums", "category": "arts"},
        {"name": "Theater", "category": "arts"},
        {"name": "Dance", "category": "arts"},
        {"name": "Writing", "category": "arts"},

        # Music
        {"name": "Live Music", "category": "music"},
        {"name": "Playing Instrument", "category": "music"},
        {"name": "Concerts", "category": "music"},
        {"name": "DJing", "category": "music"},

        # Food & Drink
        {"name": "Cooking", "category": "food"},
        {"name": "Fine Dining", "category": "food"},
        {"name": "Wine Tasting", "category": "food"},
        {"name": "Coffee", "category": "food"},
        {"name": "Baking", "category": "food"},

        # Outdoor & Adventure
        {"name": "Camping", "category": "outdoor"},
        {"name": "Travel", "category": "outdoor"},
        {"name": "Surfing", "category": "outdoor"},
        {"name": "Skiing", "category": "outdoor"},
        {"name": "Beach", "category": "outdoor"},

        # Entertainment
        {"name": "Movies", "category": "entertainment"},
        {"name": "TV Shows", "category": "entertainment"},
        {"name": "Gaming", "category": "entertainment"},
        {"name": "Board Games", "category": "entertainment"},
        {"name": "Stand-up Comedy", "category": "entertainment"},

        # Intellectual
        {"name": "Reading", "category": "intellectual"},
        {"name": "Podcasts", "category": "intellectual"},
        {"name": "Philosophy", "category": "intellectual"},
        {"name": "Science", "category": "intellectual"},
        {"name": "Learning Languages", "category": "intellectual"},

        # Social
        {"name": "Volunteering", "category": "social"},
        {"name": "Networking", "category": "social"},
        {"name": "Social Activism", "category": "social"},

        # Lifestyle
        {"name": "Fashion", "category": "lifestyle"},
        {"name": "Meditation", "category": "lifestyle"},
        {"name": "Sustainability", "category": "lifestyle"},
        {"name": "Pets", "category": "lifestyle"},
    ]

    for interest_data in interests_data:
        existing = db.query(Interest).filter(Interest.name == interest_data["name"]).first()
        if not existing:
            interest = Interest(**interest_data)
            db.add(interest)

    db.commit()
    print(f"✅ Seeded {len(interests_data)} interests")
    db.close()


def seed_prompt_templates():
    """Seed AI prompt templates"""
    db = SessionLocal()

    templates = [
        {
            "name": "initial_conversation_question",
            "category": "mediation",
            "template": "Generate a thoughtful question to help understand {user_name}'s values and personality.",
            "variables": ["user_name"]
        },
        {
            "name": "compatibility_analysis",
            "category": "analysis",
            "template": "Analyze compatibility between two users based on their profiles and responses.",
            "variables": ["user1_data", "user2_data"]
        }
    ]

    for template_data in templates:
        existing = db.query(AIPromptTemplate).filter(
            AIPromptTemplate.name == template_data["name"]
        ).first()
        if not existing:
            template = AIPromptTemplate(**template_data)
            db.add(template)

    db.commit()
    print(f"✅ Seeded {len(templates)} AI prompt templates")
    db.close()


if __name__ == "__main__":
    print("🌱 Seeding database...")
    init_db()
    seed_interests()
    seed_prompt_templates()
    print("✅ Database seeding complete!")
