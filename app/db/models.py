from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user") # user, admin

    searches = relationship("SearchHistory", back_populates="user")

class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    origin = Column(String)
    destinations = Column(String) # Comma separated
    start_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="searches")
    itineraries = relationship("Itinerary", back_populates="search")

class Itinerary(Base):
    __tablename__ = "itineraries"

    id = Column(Integer, primary_key=True, index=True)
    search_id = Column(Integer, ForeignKey("search_history.id"))
    total_cost = Column(Float)
    total_duration = Column(Integer) # Minutes
    details_json = Column(Text) # JSON string of the full result
    alternatives_json = Column(Text, nullable=True) # JSON string of alternatives
    cost_breakdown_json = Column(Text, nullable=True) # JSON string of cost breakdown
    hotels_json = Column(Text, nullable=True) # JSON string of hotels found
    created_at = Column(DateTime, default=datetime.utcnow)

    search = relationship("SearchHistory", back_populates="itineraries")

class FlightOption(Base):
    __tablename__ = "flight_options"

    id = Column(Integer, primary_key=True, index=True)
    search_id = Column(Integer, ForeignKey("search_history.id"))
    origin = Column(String)
    destination = Column(String)
    airline = Column(String)
    price = Column(Float)
    duration = Column(Integer)
    stops = Column(Integer)
    flight_number = Column(String, default="N/A")
    departure_time = Column(DateTime)
    arrival_time = Column(DateTime)
    
    search = relationship("SearchHistory", back_populates="flights")

# Add the relationship to SearchHistory as well
# Add the relationship to SearchHistory as well
SearchHistory.flights = relationship("FlightOption", back_populates="search")

class HotelOption(Base):
    __tablename__ = "hotel_options"

    id = Column(Integer, primary_key=True, index=True)
    search_id = Column(Integer, ForeignKey("search_history.id"))
    city = Column(String)
    name = Column(String)
    price = Column(Float)
    rating = Column(Float)
    
    search = relationship("SearchHistory", back_populates="hotels")

SearchHistory.hotels = relationship("HotelOption", back_populates="search")
