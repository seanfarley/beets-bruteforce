import widget


def test_no_name():
    w = widget.Widget()
    assert w.hello() == "Hello, World!"


def test_name():
    w = widget.Widget("Leeroy Jenkins")
    assert w.hello() == "Hello, Leeroy Jenkins!"
