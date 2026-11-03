# Run me from this folder:  python main.py
#
# `from helpers import greet` works because the folder this file sits in is the
# first place Python looks for modules. Nothing else is magic.
import MLAppDev.ModB.Sprint1.router_class.python_packages_class.flat.helpers as helpers
from MLAppDev.ModB.Sprint1.router_class.python_packages_class.flat.helpers import greet

print(f"main.py is running, and its __name__ is {__name__}")
print("the module itself:  ", helpers.greet("ana"))
print("just the function:  ", greet("ana"))
# helpers.py printed once even though we imported it twice: a file runs once,
# then Python keeps it in sys.modules and hands you the same copy.
