from app.db.database import engine, Base
from app.db.models import User, SearchHistory, Itinerary

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

if __name__ == "__main__":
    init_db()
