from app.model.base import BareBaseModel, Base
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship


class Vbpl(BareBaseModel):
    __tablename__ = 'vbpl'

    file_link = Column(String(100), nullable=True)
    title = Column(String(100), nullable=False)
    doc_type = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=False)
    issuance_date = Column(DateTime, nullable=False)
    effective_date = Column(DateTime, nullable=False)
    expiration_date = Column(DateTime, nullable=True)
    gazette_date = Column(DateTime, nullable=False)
    state = Column(String(100), nullable=True)
    issuing_authority = Column(String(100), nullable=True)
    applicable_information = Column(String(100), nullable=True)
    html = Column(Text, nullable=True)

    # relationship
    toan_van = relationship("VbplToanVan", foreign_keys='VbplToanVan.vbpl_id',
                            primaryjoin='VbplToanVan.vbpl_id == Vbpl.id',
                            back_populates="vbpl_toan_van",
                            lazy='select')

    related_document_source = relationship("VbplRelatedDocument", foreign_keys='VbplRelatedDocument.source_id',
                                           primaryjoin='VbplRelatedDocument.source_id == Vbpl.id',
                                           back_populates="vbpl_related_document",
                                           lazy='select')

    related_document_dest = relationship("VbplRelatedDocument", foreign_keys='VbplRelatedDocument.related_id',
                                         primaryjoin='VbplRelatedDocument.related_id == Vbpl.id',
                                         back_populates="vbpl_related_document",
                                         lazy='select')

    doc_map_source = relationship("VbplDocMap", foreign_keys='VbplDocMap.source_id',
                                  primaryjoin='VbplDocMap.source_id == Vbpl.id',
                                  back_populates="vbpl_doc_map",
                                  lazy='select')

    doc_map_dest = relationship("VbplDocMap", foreign_keys='VbplDocMap.doc_map_id',
                                primaryjoin='VbplDocMap.doc_map_id == Vbpl.id',
                                back_populates="vbpl_doc_map",
                                lazy='select')


class VbplToanVan(Base):
    __tablename__ = 'vbpl_toan_van'

    vbpl_id = Column(Integer, ForeignKey('vbpl.id'), primary_key=True, nullable=False)
    section_number = Column(Integer, primary_key=True, nullable=False)
    section_name = Column(String(100), nullable=False)
    section_ref = Column(String(100), nullable=False)

    # relationship
    vbpl = relationship("Vbpl", foreign_keys='VbplToanVan.vbpl_id',
                        primaryjoin='and_(VbplToanVan.vbpl_id == Vbpl.id, Vbpl.deleted_at.is_(None))',
                        back_populates="vbpl",
                        lazy='select')


class VbplRelatedDocument(Base):
    __tablename__ = 'vbpl_related_document'

    source_id = Column(Integer, ForeignKey('vbpl.id'), primary_key=True, nullable=False)
    related_id = Column(Integer, ForeignKey('vbpl.id'), primary_key=True, nullable=False)

    # relationship
    source = relationship("Vbpl", foreign_keys='VbplRelatedDocument.source_id',
                          primaryjoin='and_(VbplRelatedDocument.source_id == Vbpl.id, Vbpl.deleted_at.is_(None))',
                          back_populates="vbpl",
                          lazy='select')

    related = relationship("Vbpl", foreign_keys='VbplRelatedDocument.related_id',
                           primaryjoin='and_(VbplRelatedDocument.related_id == Vbpl.id, Vbpl.deleted_at.is_(None))',
                           back_populates="vbpl",
                           lazy='select')


class VbplDocMap(Base):
    __tablename__ = 'vbpl_doc_map'

    source_id = Column(Integer, ForeignKey('vbpl.id'), primary_key=True, nullable=False)
    doc_map_id = Column(Integer, ForeignKey('vbpl.id'), primary_key=True, nullable=False)
    doc_map_type = Column(String(100), nullable=True)

    # relationship
    source = relationship("Vbpl", foreign_keys='VbplDocMap.source_id',
                          primaryjoin='and_(VbplDocMap.source_id == Vbpl.id, Vbpl.deleted_at.is_(None))',
                          back_populates="vbpl",
                          lazy='select')

    related = relationship("Vbpl", foreign_keys='VbplDocMap.doc_map_id',
                           primaryjoin='and_(VbplDocMap.doc_map_id == Vbpl.id, Vbpl.deleted_at.is_(None))',
                           back_populates="vbpl",
                           lazy='select')
