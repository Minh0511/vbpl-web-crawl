from app.model.base import BareBaseModel, Base
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import relationship


class Vbpl(BareBaseModel):
    __tablename__ = 'vbpl'

    file_link = Column(Text, nullable=True)
    title = Column(String(455), nullable=False)
    sub_title = Column(Text, nullable=True)
    doc_type = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=False)
    issuance_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    gazette_date = Column(DateTime, nullable=True)
    state = Column(String(100), nullable=True)
    issuing_authority = Column(String(100), nullable=True)
    applicable_information = Column(String(100), nullable=True)
    sector = Column(String(100), nullable=True)
    html = Column(LONGTEXT, nullable=True)
    org_pdf_link = Column(Text, nullable=True)

    # relationship
    toan_van = relationship("VbplToanVan", foreign_keys='VbplToanVan.vbpl_id',
                            primaryjoin='VbplToanVan.vbpl_id == Vbpl.id',
                            back_populates="vbpl",
                            lazy='select')

    related_document_source = relationship("VbplRelatedDocument", foreign_keys='VbplRelatedDocument.source_id',
                                           primaryjoin='VbplRelatedDocument.source_id == Vbpl.id',
                                           back_populates="source",
                                           lazy='select')

    related_document_dest = relationship("VbplRelatedDocument", foreign_keys='VbplRelatedDocument.related_id',
                                         primaryjoin='VbplRelatedDocument.related_id == Vbpl.id',
                                         back_populates="related",
                                         lazy='select')

    doc_map_source = relationship("VbplDocMap", foreign_keys='VbplDocMap.source_id',
                                  primaryjoin='VbplDocMap.source_id == Vbpl.id',
                                  back_populates="source",
                                  lazy='select')

    doc_map_dest = relationship("VbplDocMap", foreign_keys='VbplDocMap.doc_map_id',
                                primaryjoin='VbplDocMap.doc_map_id == Vbpl.id',
                                back_populates="related",
                                lazy='select')

    sub_part = relationship("VbplSubPart", foreign_keys='VbplSubPart.vbpl_id',
                            primaryjoin='VbplSubPart.vbpl_id == Vbpl.id',
                            back_populates="vbpl",
                            lazy='select')

    def __str__(self):
        return (f'########################\n'
                f'id: {self.id},\n'
                f'file link: {self.file_link},\n'
                f'title: {self.title},\n'
                f'sub title: {self.sub_title},\n'
                f'doc type: {self.doc_type},\n'
                f'serial number: {self.serial_number},\n'
                f'issuance date: {self.issuance_date},\n'
                f'effective date: {self.effective_date},\n'
                f'expiration date: {self.expiration_date},\n'
                f'gazette date: {self.gazette_date},\n'
                f'state: {self.state},\n'
                f'issuing authority: {self.issuing_authority},\n'
                f'html: {self.html},\n'
                f'org_pdf_link: {self.org_pdf_link},\n'
                f'sector: {self.sector}\n'
                f'########################')


class VbplToanVan(Base):
    __tablename__ = 'vbpl_toan_van'

    vbpl_id = Column(Integer, ForeignKey('vbpl.id'), primary_key=True, nullable=False)
    section_number = Column(Integer, primary_key=True, nullable=False)
    section_name = Column(String(400), nullable=True)
    section_content = Column(LONGTEXT, nullable=True)
    chapter_number = Column(String(400), nullable=True)
    chapter_name = Column(Text, nullable=True)
    big_part_number = Column(String(25), nullable=True)
    big_part_name = Column(String(200), nullable=True)
    part_number = Column(String(400), nullable=True)
    part_name = Column(String(1000), nullable=True)
    mini_part_number = Column(String(25), nullable=True)
    mini_part_name = Column(String(200), nullable=True)

    # relationship
    vbpl = relationship("Vbpl", foreign_keys='VbplToanVan.vbpl_id',
                        primaryjoin='and_(VbplToanVan.vbpl_id == Vbpl.id, Vbpl.deleted_at.is_(None))',
                        back_populates="toan_van",
                        lazy='select')


class VbplRelatedDocument(Base):
    __tablename__ = 'vbpl_related_document'

    source_id = Column(Integer, ForeignKey('vbpl.id'), primary_key=True, nullable=False)
    related_id = Column(Integer, ForeignKey('vbpl.id'), primary_key=True, nullable=False)
    doc_type = Column(String(100), nullable=True)

    # relationship
    source = relationship("Vbpl", foreign_keys='VbplRelatedDocument.source_id',
                          primaryjoin='and_(VbplRelatedDocument.source_id == Vbpl.id, Vbpl.deleted_at.is_(None))',
                          back_populates="related_document_source",
                          lazy='select')

    related = relationship("Vbpl", foreign_keys='VbplRelatedDocument.related_id',
                           primaryjoin='and_(VbplRelatedDocument.related_id == Vbpl.id, Vbpl.deleted_at.is_(None))',
                           back_populates="related_document_dest",
                           lazy='select')

    def __str__(self):
        return (f'Source: {self.source_id},\n'
                f'Dest: {self.related_id},\n'
                f'Doc type: {self.doc_type}')


class VbplDocMap(Base):
    __tablename__ = 'vbpl_doc_map'

    source_id = Column(Integer, ForeignKey('vbpl.id'), primary_key=True, nullable=False)
    doc_map_id = Column(Integer, ForeignKey('vbpl.id'), primary_key=True, nullable=False)
    doc_map_type = Column(String(100), nullable=True)

    # relationship
    source = relationship("Vbpl", foreign_keys='VbplDocMap.source_id',
                          primaryjoin='and_(VbplDocMap.source_id == Vbpl.id, Vbpl.deleted_at.is_(None))',
                          back_populates="doc_map_source",
                          lazy='select')

    related = relationship("Vbpl", foreign_keys='VbplDocMap.doc_map_id',
                           primaryjoin='and_(VbplDocMap.doc_map_id == Vbpl.id, Vbpl.deleted_at.is_(None))',
                           back_populates="doc_map_dest",
                           lazy='select')

    def __str__(self):
        return (f'Source: {self.source_id},\n'
                f'Doc map: {self.doc_map_id},\n'
                f'Doc type: {self.doc_map_type}')


class VbplSubPart(Base):
    __tablename__ = 'vbpl_sub_part'

    vbpl_id = Column(Integer, ForeignKey('vbpl.id'), primary_key=True, nullable=False)
    sub_parts = Column(String(100), nullable=False)

    # relationship
    vbpl = relationship("Vbpl", foreign_keys='VbplSubPart.vbpl_id',
                        primaryjoin='and_(VbplSubPart.vbpl_id == Vbpl.id, Vbpl.deleted_at.is_(None))',
                        back_populates="sub_part",
                        lazy='select')

    def __str__(self):
        return (f'Vbpl: {self.vbpl_id},\n'
                f'Sub parts: {self.sub_parts}')
