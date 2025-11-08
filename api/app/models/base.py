"""SQLAlchemy declarative base and common utilities."""


from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Define naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class."""

    metadata = metadata

    def __repr__(self) -> str:
        """String representation of model instance."""
        attrs = []
        for col in self.__table__.columns:
            attrs.append(f"{col.name}={getattr(self, col.name)!r}")
        return f"{self.__class__.__name__}({', '.join(attrs)})"
