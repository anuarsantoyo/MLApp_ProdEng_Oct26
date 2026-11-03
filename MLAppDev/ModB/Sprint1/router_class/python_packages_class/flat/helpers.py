# A module is a file. Its name is the file name without .py, so this one is "helpers".
print(f"helpers.py is running, and its __name__ is {__name__}")


def greet(name):
    return f"hola {name}"


if __name__ == "__main__":
    # This block runs only when you run `python helpers.py` yourself.
    # When another file imports this one, it is skipped.
    print(greet("ana"))
