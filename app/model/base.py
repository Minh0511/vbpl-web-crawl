from __future__ import annotations

from datetime import datetime, date
from typing import TypeVar

from sqlalchemy import Column, Integer, DateTime, inspect, String, func
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Session

from app.helper.custom_exception import ObjectNotFound
from app.helper.enum import ObjectNotFoundType


@as_declarative()
class Base:
    __abstract__ = True
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    def as_dict(self) -> dict:
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}

    def to_dict(self, datetime_to_timestamp=False):
        result = {col.name: getattr(self, col.name) for col in self.__table__.columns}
        if datetime_to_timestamp:
            for key, value in result.items():
                if isinstance(value, datetime):
                    result[key] = round(datetime.timestamp(value))
                elif isinstance(value, date):
                    result[key] = round(datetime.timestamp(datetime(value.year, value.month, value.day)))
        return result


class BareBaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True)

    @classmethod
    def max(cls, db: Session, field):
        """
        Sample: User.max(User.id)
        :param db:
        :param field:
        :return: int, None if no records
        """
        return cls.scalar(db, 'max', field)

    @classmethod
    def scalar(cls, db: Session, _func, field):
        """
        Sample: User.scalar('max', User.id)
        :param _func:
        :param db:
        :param field:
        :return: int, None if no records
        """
        func_to_call = getattr(func, _func)
        return db.query(cls, func_to_call(field)).scalar()

    @classmethod
    def q(cls, db: Session, *criterion):
        """
        Filter by criterion, ex: User.q(User.name=='Thuc', User.status==1)
        :param db:
        :param criterion:
        :return:
        """
        query = db.query(cls).filter(cls.deleted_at.is_(None))
        if criterion:
            return query.filter(*criterion)
        return query

    @classmethod
    def q_by(cls, db: Session, **kwargs):
        """
        Filter by named params, ex: User.q(name='Thuc', status=1)
        :param db:
        :param kwargs:
        :return:
        """
        return db.query(cls).filter_by(**kwargs).filter(cls.deleted_at.is_(None))

    @classmethod
    def first(cls, db: Session, *criterion):
        """
        Get first by list of criterion, ex: user1 = User.first(User.name=='Thuc1')
        :param db:
        :param criterion:
        :return:
        """
        res = cls.q(db, *criterion).first()
        return res

    @classmethod
    def first_or_error(cls, db: Session, *criterion):
        res = cls.first(db, *criterion)
        if not res:
            raise ObjectNotFound(ObjectNotFoundType(cls.__name__))
        return res

    @classmethod
    def first_by(cls, db: Session, **kwargs):
        """
        Get first by named params, ex: user1 = User.first_by(name='Thuc1')
        :return:
        """
        res = cls.q_by(db, **kwargs).first()
        return res

    @classmethod
    def first_by_or_error(cls, db: Session, **kwargs):
        res = cls.first_by(db, **kwargs)
        if not res:
            raise ObjectNotFound(ObjectNotFoundType(cls.__name__))
        return res

    @classmethod
    def get(cls, db: Session, _id, error_out=False):
        """
        Find model object by id
        :param db:
        :param int _id:
        :param error_out:
        :return:
        :rtype: cls
        """
        obj = db.query(cls).filter(cls.id == _id).filter(cls.deleted_at.is_(None)).first()
        if not obj and error_out:
            raise ObjectNotFound(ObjectNotFoundType(cls.__name__))
        return obj

    @classmethod
    def get_or_error(cls, db: Session, _id):
        return cls.get(db, _id, True)

    @classmethod
    def create(cls, db: Session, data, commit=False):
        """
        Create new model object with given dict `data`
        :param db:
        :param dict data:
        :param commit:
        :return:
        """
        new_obj = cls(**data)
        db.add(new_obj)
        if commit:
            db.commit()
        else:
            db.flush()
        return new_obj

    def update(self, db: Session, data, commit=False, exclude=None):
        """
        Update current model object with given dict `data`
        :param db:
        :param data: dict
        :param commit:
        :param exclude: list of key to exclude from `data` dict
        :return:
        """
        for key, value in data.items():
            if not exclude or key not in exclude:
                setattr(self, key, value)

        if commit:
            db.commit()
        else:
            db.flush()

        return self

    def delete(self, db: Session, commit=False):
        db.delete(self)
        if commit:
            db.commit()
        else:
            db.flush()
