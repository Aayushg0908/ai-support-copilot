# security.py - Learning Notes

## What This File Does
All security-related utilities in one place. Password hashing, JWT creation/verification, validation.

## Key Concepts

### bcrypt Password Hashing
```python
# Password "mypassword123"
# Becomes: $2b$12$LJ3m4ys3GZkYOURANDOMSALTk8GZkYO...
#                     ^^^^^^^^^^^^^^^^^^^^
#                     This is the salt (auto-generated)