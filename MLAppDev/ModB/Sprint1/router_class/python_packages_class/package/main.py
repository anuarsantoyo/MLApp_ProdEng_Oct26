# Run me from this folder:  python main.py
#
# Same function as ../flat/helpers.py, but now it lives inside a package.
# The import got shorter, not longer. That is the whole point of __init__.py.
from MLAppDev.ModB.Sprint1.router_class.python_packages_class.package.shop import greet

print(greet("ana"))
