from app.database.db import Base, engine
from app.models.notification import Notification  # noqa: F401


def migrate():
    Base.metadata.create_all(bind=engine)
    print("[OK] Notifications table is ready.")


if __name__ == "__main__":
    migrate()
