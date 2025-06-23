import smtplib
import imaplib
import email
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import List, Dict
from dotenv import load_dotenv

from utilities.phonebook import Contact

load_dotenv()

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self, user: str, session_db):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.imap_server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
        self.imap_port = int(os.getenv('IMAP_PORT', '993'))
        self.service_email = os.getenv('SERVICE_EMAIL')
        self.service_password = os.getenv('SERVICE_PASSWORD')
        self.user = user
        if not self.service_email or not self.service_password:
            raise ValueError("SERVICE_EMAIL and SERVICE_PASSWORD must be set in environment variables")
        
        # Initialize session database
        self.session_db = session_db
        
    def send_meeting_request(self, contact: Contact, meeting_request: str) -> bool:
        """Send a meeting request email to a contact without an agent"""
        try:
            subject = f"Meeting Request from {self.user}"
            
            # Create email body
            body = f"""
                Hello {contact.first_name} {contact.last_name},

                {meeting_request}

                Best regards,
                {self.user}'s Assistant
            """

            # Send email using appropriate method
            self._send_email_smtp(contact.email, subject, body) 
            return True
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    def _send_email_smtp(self, to_email: str, subject: str, body: str) -> bool:
        """Send email using SMTP (App Password method)"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.service_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.service_email, self.service_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending email via SMTP: {e}")
            return False

    def check_for_replies(self) -> List[Dict]:
        """Check for new email replies and return them with session IDs"""
        replies = []
        
        try:
            replies = self._check_replies_imap()
            
        except Exception as e:
            logger.error(f"Error checking for replies: {e}")
        
        return replies

    def _check_replies_imap(self) -> List[Dict]:
        """Check for replies using IMAP (App Password method)"""
        replies = []
        try:
            # Connect to IMAP server
            with imaplib.IMAP4_SSL(self.imap_server, self.imap_port) as server:
                server.login(self.service_email, self.service_password)
                server.select('INBOX')
                
                # Search for unread emails
                _, message_numbers = server.search(None, 'UNSEEN')
                # Convert bytes to string and split into individual message numbers

                if message_numbers[0]:
                    message_list = message_numbers[0].decode().split()
                    
                    for num in message_list:
                        try:
                            _, msg_data = server.fetch(num, '(RFC822)')
                            email_body = msg_data[0][1]
                            email_message = email.message_from_bytes(email_body)
                            
                            # Check if this is a reply to one of our sessions
                            from_email = email_message.get('From', '')
                            
                            # Extract email address from various formats
                            clean_email = self._extract_email_address(from_email)
                            
                            if clean_email:
                                # Find matching session by email
                                session_id = self.session_db.get_session_by_email(clean_email)
                                if session_id:
                                    
                                    # Extract email content
                                    content = self._extract_email_content(email_message)
                                    
                                    # Add message to session in database
                                    success = self.session_db.add_message_to_session(
                                        session_id=session_id,
                                        message_type='received',
                                        content=content,
                                        from_email=from_email
                                    )
                                    
                                    if success:
                                        # Get session details for reply
                                        session = self.session_db.get_session_history(session_id)
                                        if session:
                                            replies.append({
                                                'session_id': session_id,
                                                'contact_name': session.contact_name,
                                                'contact_email': session.contact_email,
                                                'content': content,
                                                'from_email': from_email,
                                                'timestamp': datetime.now(timezone.utc).isoformat()
                                            })
                                            
                                            logger.info(f"Found reply for session {session_id}")
                                else:
                                    logger.info(f"No matching session found for email {clean_email}")
                            
                            # Mark this specific email as read
                            try:
                                server.store(num, '+FLAGS', '\\Seen')
                            except Exception as e:
                                logger.warning(f"Could not mark email {num} as read: {e}")
                        
                        except Exception as e:
                            logger.error(f"Error processing email {num}: {e}")
                            continue
            
        except Exception as e:
            logger.error(f"Error checking replies via IMAP: {e}")
        
        return replies

    def _extract_email_address(self, email_string: str) -> str:
        """Extract clean email address from various formats"""
        if not email_string:
            return ""
        
        # Remove common email formats like "John Doe <john@example.com>"
        import re
        
        # Pattern to match email addresses
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(email_pattern, email_string)
        
        if match:
            return match.group(0).lower()
        
        return email_string.lower()

    def _extract_email_content(self, email_message) -> str:
        """Extract text content from email message"""
        content = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    content = part.get_payload(decode=True).decode()
                    break
        else:
            content = email_message.get_payload(decode=True).decode()
        
        return content

    def send_follow_up(self, session_id: str, message: str) -> bool:
        """Send a follow-up message to an existing email session"""
        try:
            session = self.session_db.get_session_by_id(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return False
            
            subject = f"Re: {session['subject']}"
            
            # Send email using appropriate method
            success = self._send_email_smtp(session["contact_email"], subject, message)
            
            if success:
                # Add message to session in database
                success = self.session_db.add_message_to_session(
                    session_id=session_id,
                    message_type='sent',
                    content=message,
                    from_email='agent'
                )
                
                if success:
                    logger.info(f"Follow-up email sent for session {session_id}")
                    return True
                else:
                    logger.error(f"Failed to store follow-up message for session {session_id}")
                    return False
            else:
                logger.error(f"Failed to send follow-up email for session {session_id}")
                return False
            
        except Exception as e:
            logger.error(f"Error sending follow-up: {e}")
            return False
