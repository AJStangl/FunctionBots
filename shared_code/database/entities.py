from sqlalchemy import Column, ForeignKey, Integer, Table, Text, TIMESTAMP
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

association_table = Table(
    "association",
    Base.metadata,
    Column("TrackingSubmission_id", ForeignKey("TrackingSubmission.Id"), primary_key=True),
    Column("TrackingComment_id", ForeignKey("TrackingComment.Id"), primary_key=True),
)


class TrackingSubmission(Base):
	__tablename__ = "TrackingSubmission"
	Id = Column(Text, primary_key=True)
	Author = Column(Text)
	Subreddit = Column(Text)
	SubmissionTimeStamp = Column(Integer)
	Text = Column(Text)
	DateCreated = Column(Integer)
	DateUpdated = Column(Integer)
	children = relationship("TrackingComment", secondary=association_table)


class TrackingComment(Base):
	__tablename__ = "TrackingComment"
	Id = Column(Text, primary_key=True)
	SubmissionId = (Text, ForeignKey("TrackingSubmission.Id"))
	Submission = relationship("TrackingSubmission", back_populates="children")
	Author = Column(Text)
	Text = Column(Text)
	CreatedAt = Column(Integer)
	DateCreated = Column(Integer)
	DateUpdated = Column(Integer)


class BotConfiguration(Base):
	__tablename__ = "BotConfiguration"
	Id = Column(Integer, primary_key=True)
	Name = Column(Text)
	ModelPath = Column(Text)
	DateCreated = Column(Integer)
	DateUpdated = Column(Integer)


class TrackResponse(Base):
	__tablename__ = "TrackResponse"
	Id = Column(Text, primary_key=True)
	BotName = Column(Text)
	ResponseId = Column(Text)
	Text = Column(Text)
	DateCreated = Column(Integer)
	DateUpdated = Column(Integer)

