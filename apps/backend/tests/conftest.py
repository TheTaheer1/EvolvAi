import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://evolvai:evolvai@localhost:5432/evolvai_db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
