from sqlalchemy import Column, Integer, Text, Date, DateTime, Index
from datetime import datetime
from .database import Base


class Standard(Base):
    __tablename__ = "standards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hcno = Column(Text, unique=True, nullable=False, index=True)
    standard_number = Column(Text, nullable=False)
    cn_name = Column(Text, nullable=False)
    en_name = Column(Text, default="")
    status = Column(Text, default="")  # 现行 / 即将实施 / 废止
    standard_type = Column(Text, default="")  # 强制 / 推荐 / 指导
    ics_code = Column(Text, default="")
    ccs_code = Column(Text, default="")
    publish_date = Column(Date, nullable=True)
    implement_date = Column(Date, nullable=True)
    abolish_date = Column(Date, nullable=True)
    replaced_by = Column(Text, default="")
    category = Column(Text, default="")
    pdf_path = Column(Text, default="")       # PDF 文件本地存储路径
    pdf_size = Column(Integer, default=0)      # PDF 文件大小(bytes)
    pdf_downloaded_at = Column(DateTime, nullable=True)  # PDF 下载时间
    scraped_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_implement_date", "implement_date"),
        Index("idx_abolish_date", "abolish_date"),
        Index("idx_status", "status"),
    )
