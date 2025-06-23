# =============================================================================
# utilities/email_service.py
# =============================================================================
# 📧 Purpose:
# This file defines the EmailService class that handles email operations
# including sending emails via SMTP and receiving emails via IMAP. The service
# integrates with the session database to track email communications and
# manage follow-up conversations.
#
# ✅ Features:
# - SMTP email sending with authentication
# - IMAP email receiving and parsing
# - Reply detection and session tracking
# - Contact-based email operations
# - Error handling and logging
# - Email content extraction and processing
#
# 🔧 Dependencies:
# - smtplib for SMTP operations
# - imaplib for IMAP operations
# - email module for message parsing
# - Session database for tracking
# =============================================================================

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

# Load environment variables
load_dotenv()

# Set up logging for this module
logger = logging.getLogger(__name__)


class EmailService:
    """
    📧 EmailService: Handles email sending and receiving operations.
    
    This service provides functionality for:
    - Sending meeting request emails via SMTP
    - Checking for email replies via IMAP
    - Tracking email sessions in the database
    - Extracting and processing email content
    - Managing follow-up communications
    
    The service integrates with the session database to maintain conversation
    history and enable follow-up communications based on email interactions.
    
    Attributes:
        smtp_server (str): SMTP server address
        smtp_port (int): SMTP server port
        imap_server (str): IMAP server address
        imap_port (int): IMAP server port
        service_email (str): Email account for sending/receiving
        service_password (str): Password for email authentication
        user (str): User name for session tracking
        session_db: Session database for tracking communications
    """

    def __init__(self, user: str, session_db):
        """
        Initialize the EmailService with configuration and session database.
        
        Args:
            user (str): User name for session tracking
            session_db: Session database instance for tracking communications
            
        Raises:
            ValueError: If required environment variables are not set
        """
        # Load email configuration from environment variables
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.imap_server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
        self.imap_port = int(os.getenv('IMAP_PORT', '993'))
        self.service_email = os.getenv('SERVICE_EMAIL')
        self.service_password = os.getenv('SERVICE_PASSWORD')
        self.user = user
        
        # Validate required configuration
        if not self.service_email or not self.service_password:
            raise ValueError(
                "SERVICE_EMAIL and SERVICE_PASSWORD must be set in environment variables. "
                "These are required for email authentication."
            )
        
        # Initialize session database for tracking
        self.session_db = session_db
        
    def send_meeting_request(self, contact: Contact, meeting_request: str) -> bool:
        """
        Send a meeting request email to a contact.
        
        This method creates and sends a formatted meeting request email
        to the specified contact. The email includes a personalized greeting
        and the meeting request content.
        
        Args:
            contact (Contact): Contact to send the email to
            meeting_request (str): Meeting request message content
            
        Returns:
            bool: True if email was sent successfully, False otherwise
            
        Example:
            >>> contact = Contact("John", "Doe", "john@example.com")
            >>> success = email_service.send_meeting_request(
            ...     contact, "I'd like to schedule a meeting to discuss our project."
            ... )
        """
        try:
            # Create email subject
            subject = f"Meeting Request from {self.user}"
            
            # Create email body with personalized greeting
            body = f"""
                Hello {contact.first_name} {contact.last_name},

                {meeting_request}

                Best regards,
                {self.user}'s Assistant
            """

            # Send email using SMTP
            return self._send_email_smtp(contact.email, subject, body)
            
        except Exception as e:
            logger.error(f"Error sending meeting request email: {e}")
            return False

    def _send_email_smtp(self, to_email: str, subject: str, body: str) -> bool:
        """
        Send email using SMTP with TLS authentication.
        
        This method handles the low-level SMTP communication including:
        - TLS encryption setup
        - Authentication with service account
        - Message formatting and sending
        - Error handling and logging
        
        Args:
            to_email (str): Recipient email address
            subject (str): Email subject line
            body (str): Email body content
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.service_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable TLS encryption
                server.login(self.service_email, self.service_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email via SMTP: {e}")
            return False

    def check_for_replies(self) -> List[Dict]:
        """
        Check for new email replies and process them.
        
        This method connects to the IMAP server, searches for unread emails,
        and processes any replies that match existing sessions. It updates
        the session database with new messages and returns information about
        processed replies.
        
        Returns:
            List[Dict]: List of processed reply information including:
                - session_id: Session identifier
                - contact_name: Name of the contact
                - contact_email: Email address of the contact
                - content: Email content
                - from_email: Sender email address
                - timestamp: Processing timestamp
                
        Example:
            >>> replies = email_service.check_for_replies()
            >>> for reply in replies:
            ...     print(f"Reply from {reply['contact_name']}: {reply['content']}")
        """
        replies = []
        
        try:
            # Check for replies using IMAP
            replies = self._check_replies_imap()
            
        except Exception as e:
            logger.error(f"Error checking for replies: {e}")
        
        return replies

    def _check_replies_imap(self) -> List[Dict]:
        """
        Check for email replies using IMAP protocol.
        
        This method performs the actual IMAP operations:
        - Connects to IMAP server with SSL
        - Searches for unread emails
        - Processes each email for session matching
        - Updates session database with new messages
        - Marks emails as read after processing
        
        Returns:
            List[Dict]: List of processed reply information
        """
        replies = []
        try:
            # Connect to IMAP server with SSL
            with imaplib.IMAP4_SSL(self.imap_server, self.imap_port) as server:
                server.login(self.service_email, self.service_password)
                server.select('INBOX')
                
                # Search for unread emails
                _, message_numbers = server.search(None, 'UNSEEN')
                
                # Process each unread email
                if message_numbers[0]:
                    message_list = message_numbers[0].decode().split()
                    
                    for num in message_list:
                        try:
                            # Fetch email content
                            _, msg_data = server.fetch(num, '(RFC822)')
                            email_body = msg_data[0][1]
                            email_message = email.message_from_bytes(email_body)
                            
                            # Extract sender email address
                            from_email = email_message.get('From', '')
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
                                        # Get session details for reply information
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
        """
        Extract clean email address from various email string formats.
        
        This method handles different email formats including:
        - Plain email addresses: "user@example.com"
        - Named formats: "John Doe <user@example.com>"
        - Quoted formats: '"John Doe" <user@example.com>'
        
        Args:
            email_string (str): Email string that may contain formatting
            
        Returns:
            str: Clean email address in lowercase, or empty string if not found
        """
        if not email_string:
            return ""
        
        # Use regex to extract email address
        import re
        
        # Pattern to match email addresses
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(email_pattern, email_string)
        
        if match:
            return match.group(0).lower()
        
        return email_string.lower()

    def _extract_email_content(self, email_message) -> str:
        """
        Extract text content from email message.
        
        This method handles both plain text and multipart email messages,
        extracting the text content for processing and storage.
        
        Args:
            email_message: Email message object from email module
            
        Returns:
            str: Extracted text content from the email
        """
        content = ""
        
        if email_message.is_multipart():
            # Handle multipart messages (HTML + text, attachments, etc.)
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    content = part.get_payload(decode=True).decode()
                    break
        else:
            # Handle plain text messages
            content = email_message.get_payload(decode=True).decode()
        
        return content

    def send_follow_up(self, session_id: str, message: str) -> bool:
        """
        Send a follow-up message to an existing email session.
        
        This method sends a follow-up email to a contact based on an existing
        session. It retrieves the session details and sends the message to
        the appropriate contact.
        
        Args:
            session_id (str): Session identifier to send follow-up to
            message (str): Follow-up message content
            
        Returns:
            bool: True if follow-up was sent successfully, False otherwise
        """
        try:
            # Get session details
            session = self.session_db.get_session_by_id(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return False
            
            # Create contact object from session
            contact = Contact(
                first_name=session.contact_name.split()[0] if session.contact_name else "",
                last_name=" ".join(session.contact_name.split()[1:]) if session.contact_name else "",
                email=session.contact_email
            )
            
            # Send follow-up email
            return self.send_meeting_request(contact, message)
            
        except Exception as e:
            logger.error(f"Error sending follow-up for session {session_id}: {e}")
            return False
