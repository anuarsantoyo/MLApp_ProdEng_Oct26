# The front door of the package. Whatever you export here is what
# `from shop import ...` can see. Nothing else in this folder is visible from outside.
print("shop/__init__.py ran: the front door opened")

# The dot means "inside this package". Without it, `from helpers import greet`
# would search sys.path (the outside world) and fail.
from .helpers import greet
