# requirements.txt - Learning Notes

## What This File Does
Declares all Python packages our project needs with specific versions.

## Key Packages Explained

### fastapi
Modern async Python web framework. Chosen over Django/Flask for:
- Built-in async support (important for AI calls)
- Automatic OpenAPI documentation
- Type hints enforced at runtime
- 2-3x faster than Flask

### sqlalchemy
Database ORM (Object-Relational Mapping). Instead of writing raw SQL:
```python
# Without ORM
cursor.execute("SELECT * FROM users WHERE email = %s", [email])

# With SQLAlchemy
user = db.query(User).filter(User.email == email).first()