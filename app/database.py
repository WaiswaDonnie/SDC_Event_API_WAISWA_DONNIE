from sqlmodel import SQLModel, create_engine, Session
DATABASE_URL = "sqlite:///./sport_events.db"
engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})

def get_db():
    with Session(engine) as session:
        yield session

def init_db():
    SQLModel.metadata.create_all(engine)
