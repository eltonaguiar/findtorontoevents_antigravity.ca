from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class Experiment(Base):
    __tablename__ = 'experiments'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default='draft')  # draft, running, completed, stopped
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Experiment parameters
    variants = Column(Text)  # JSON: [{'name': 'A', 'traffic_percentage': 50}, {'name': 'B', 'traffic_percentage': 50}]
    metrics = Column(Text)  # JSON: ['conversion_rate', 'revenue', 'engagement']
    target_metric = Column(String(100))
    significance_level = Column(Float, default=0.05)
    minimum_sample_size = Column(Integer)

    # Results
    winner = Column(String(50))
    confidence_level = Column(Float)
    effect_size = Column(Float)

    # Relationships
    observations = relationship("Observation", back_populates="experiment")

class Observation(Base):
    __tablename__ = 'observations'

    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey('experiments.id'))
    variant = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Metrics
    metrics_data = Column(Text)  # JSON: {'conversion_rate': 0.15, 'revenue': 25.50}

    # Relationships
    experiment = relationship("Experiment", back_populates="observations")

class Deployment(Base):
    __tablename__ = 'deployments'

    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey('experiments.id'))
    variant = Column(String(50), nullable=False)
    traffic_percentage = Column(Float, nullable=False)
    status = Column(String(50), default='pending')  # pending, deploying, deployed, rolled_back
    deployed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    experiment = relationship("Experiment")

def init_db(database_url):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()