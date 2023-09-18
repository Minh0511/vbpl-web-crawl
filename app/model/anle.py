from app.model.base import BareBaseModel, Base
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship


class Anle(BareBaseModel):
    __tablename__ = 'anle'

    doc_id = Column(String(25), nullable=False)
    file_link = Column(String(200), nullable=True)
    title = Column(String(100), nullable=False)
    serial_number = Column(String(100), nullable=False)
    adoption_date = Column(DateTime, nullable=False)
    application_date = Column(DateTime, nullable=False)
    expiration_date = Column(DateTime, nullable=True)
    publication_date = Column(DateTime, nullable=False)
    state = Column(String(100), nullable=True)
    sector = Column(String(100), nullable=True)
    publication_decision = Column(String(255), nullable=True)
    org_pdf_link = Column(String(100), nullable=True)

    # relationship
    section = relationship("AnleSection", foreign_keys='AnleSection.anle_id',
                           primaryjoin='AnleSection.anle_id == Anle.id',
                           back_populates="anle_source",
                           lazy='select')

    def __str__(self):
        return (f'########################\n'
                f'id: {self.id},\n'
                f'doc_id: {self.doc_id},\n'
                f'file link: {self.file_link},\n'
                f'title: {self.title},\n'
                f'serial number: {self.serial_number},\n'
                f'adoption date: {self.adoption_date},\n'
                f'application date: {self.application_date},\n'
                f'expiration date: {self.expiration_date},\n'
                f'publication date: {self.publication_date},\n'
                f'state: {self.state},\n'
                f'sector: {self.sector},\n'
                f'publication decision: {self.publication_decision},\n'
                f'org_pdf_link: {self.org_pdf_link},\n'
                f'########################')


class AnleSection(BareBaseModel):
    __tablename__ = 'anle_section'

    anle_id = Column(Integer, ForeignKey('anle.id'), nullable=False)
    context = Column(Text, nullable=True)
    solution = Column(Text, nullable=True)
    content = Column(Text, nullable=True)

    # relationship
    anle_source = relationship("Anle", foreign_keys='AnleSection.anle_id',
                               primaryjoin='and_(AnleSection.anle_id == Anle.id, Anle.deleted_at.is_(None))',
                               back_populates="section",
                               lazy='select')
