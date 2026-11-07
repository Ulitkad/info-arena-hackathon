"""Serialization helpers shared by API use-cases."""


def row(obj, *excluded):
    if obj is None:
        return None
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns if column.name not in excluded}


def public_user(user):
    return row(user, "phone")
