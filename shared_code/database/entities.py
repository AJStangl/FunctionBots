from sqlalchemy import Column, ForeignKey, Table, Text, TIMESTAMP, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

association_table = Table(
    "association",
    Base.metadata,
    Column("Id", ForeignKey("TrackingSubmission.Id"), primary_key=True),
    Column("Id", ForeignKey("TrackingComment.Id"), primary_key=True),
)


class TrackingSubmission(Base):
	__tablename__ = "TrackingSubmission"
	Id = Column(Text, primary_key=True)
	Author = Column(Text)
	SubmissionTimestamp = Column(TIMESTAMP)
	Subreddit = Column(Text)
	DateCreated = Column(TIMESTAMP)
	DateUpdated = Column(TIMESTAMP)
	Text = Column(Text)
	Comments = relationship("TrackingComment")


class TrackingComment(Base):
	__tablename__ = "TrackingComment"
	Id = Column(Text, primary_key=True)
	SubmissionId = Column(Text, ForeignKey("TrackingSubmission.Id"))
	ParentId = Column(Text)
	Author = Column(Text)
	Text = Column(Text)
	CommentTimestamp = Column(TIMESTAMP)
	DateCreated = Column(TIMESTAMP)
	DateUpdated = Column(TIMESTAMP)

class TrackingResponse(Base):
	__tablename__ = "TrackingResponse"
	Id = Column(Text, primary_key=True)
	SubmissionId = Column(Text)
	CommentId = Column(Text, ForeignKey("TrackingComment.Id"))
	HasResponded = Column(Boolean)
	DateCreated = Column(TIMESTAMP)
	DateUpdated = Column(TIMESTAMP)
	BotName = Column(Text)
	Text = Column(Text)

