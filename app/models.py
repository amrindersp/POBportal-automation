from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class AutomationRun(Base):
    __tablename__ = "automation_runs"

    id = Column(Integer, primary_key=True, index=True)

    user = Column(String(100), nullable=False)
    vessel = Column(String(100), nullable=False)

    step = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    progress = Column(Integer, default=0)

    error = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    files = relationship(
        "AutomationFile",
        back_populates="run",
        cascade="all, delete-orphan"
    )


class AutomationFile(Base):
    __tablename__ = "automation_files"

    id = Column(Integer, primary_key=True, index=True)

    run_id = Column(
        Integer,
        ForeignKey("automation_runs.id", ondelete="CASCADE"),
        nullable=False
    )

    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)

    run = relationship("AutomationRun", back_populates="files")
