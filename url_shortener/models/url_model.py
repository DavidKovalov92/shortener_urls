from sqlalchemy import Column, Integer, String, DateTime, Table, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

url_tag_association = Table(
    "url_tag_association",
    Base.metadata,
    Column("url_id", Integer, ForeignKey("urls.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

class URL(Base):
    __tablename__ = "urls"
    
    id = Column(Integer, unique=True, primary_key=True, index=True)
    original_url = Column(String, nullable=False, index=True)
    short_code = Column(String, unique=True, nullable=False, index=True)
    click_count = Column(Integer, default=0)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    tags = relationship("Tags", secondary=url_tag_association, back_populates="urls")
    owner = relationship("User", back_populates="urls")


class Tags(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, unique=True, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    urls = relationship("URL", secondary=url_tag_association, back_populates="tags")

