from django.apps import apps


def test_django_is_ready() -> None:
    assert apps.ready
