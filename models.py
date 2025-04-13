from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class CustomDomain(db.Model):
    """Custom domain model for popular email providers"""
    __tablename__ = 'custom_domains'
    
    id = Column(Integer, primary_key=True)
    domain = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    is_popular = Column(Boolean, default=False)
    mail_server = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'domain': self.domain,
            'display_name': self.display_name,
            'is_popular': self.is_popular
        }

class TempEmail(db.Model):
    """Temporary email account model"""
    __tablename__ = 'temp_emails'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    account_id = Column(String(100), nullable=False)
    token = Column(Text, nullable=False)
    password = Column(String(100), nullable=False)
    domain_type = Column(String(20), default="mail_tm")  # mail_tm, custom, etc.
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)
    
    # Relationship with emails
    emails = relationship('Email', back_populates='temp_email', cascade='all, delete-orphan')
    
    @property
    def is_expired(self):
        """Check if the email is expired (older than 24 hours)"""
        return datetime.now() - self.created_at > timedelta(hours=24)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'email': self.email,
            'account_id': self.account_id,
            'token': self.token,
            'password': self.password,
            'domain_type': self.domain_type,
            'created_at': self.created_at,
            'is_active': self.is_active
        }


class Email(db.Model):
    """Email model for storing received emails"""
    __tablename__ = 'emails'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(String(100), nullable=False, index=True)
    temp_email_id = Column(Integer, ForeignKey('temp_emails.id', ondelete='CASCADE'), nullable=False)
    sender = Column(String(100), nullable=False)
    recipient = Column(String(100), nullable=False)
    subject = Column(String(255))
    intro = Column(Text)
    html_content = Column(Text)
    text_content = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationship with temp_email
    temp_email = relationship('TempEmail', back_populates='emails')
    
    def to_dict(self, include_content=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.message_id,
            'from': self.sender,
            'subject': self.subject,
            'intro': self.intro,
            'isRead': self.is_read,
            'createdAt': self.created_at
        }
        
        if include_content:
            data.update({
                'to': self.recipient,
                'text': self.text_content,
                'html': self.html_content
            })
            
        return data