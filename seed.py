"""Seed the database from CSV files."""

import csv
import sys

from dotenv import load_dotenv
from peewee import chunked

load_dotenv()

from app.database import db, init_db_standalone
from app.models import Event, Url, User


def load_csv(filepath):
    with open(filepath, newline="") as f:
        return list(csv.DictReader(f))


def seed():
    init_db_standalone()
    db.create_tables([User, Url, Event])

    users = load_csv("seed_data/users.csv")
    urls = load_csv("seed_data/urls.csv")
    events = load_csv("seed_data/events.csv")

    with db.atomic():
        for batch in chunked(users, 100):
            User.insert_many(batch).execute()
    print(f"Loaded {len(users)} users")

    with db.atomic():
        for batch in chunked(urls, 100):
            # Convert is_active from string to boolean
            for row in batch:
                row["is_active"] = row["is_active"] == "True"
            Url.insert_many(batch).execute()
    print(f"Loaded {len(urls)} urls")

    with db.atomic():
        for batch in chunked(events, 100):
            Event.insert_many(batch).execute()
    print(f"Loaded {len(events)} events")

    # Reset PostgreSQL sequences after bulk insert with explicit IDs
    for table in ["users", "urls", "events"]:
        db.execute_sql(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
            f"(SELECT MAX(id) FROM {table}))"
        )
    print("Sequences reset.")

    print("Seeding complete!")


if __name__ == "__main__":
    seed()
