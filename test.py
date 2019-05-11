from argus.models import Base


x = list(Base._decl_class_registry.values())[2]

print([column for column in x.__table__.columns])


class Test(object):

    @declared_attribute
    def __column_list__(cls)
        return (column.name for column in cls.__table__.columns)

    @declared_attribute
