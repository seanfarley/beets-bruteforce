class Widget:
    def __init__(self, name=None):
        self.name = name
        if name is None:
            self.name = "World"

    def hello(self):
        return f"Hello, {self.name}!"
