import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from utilities.supabase_client import supabase_client
from utilities.phonebook import Contact

logger = logging.getLogger(__name__)

@dataclass
class EmailSession:
    session_id: str
    contact_email: str
    contact_name: str
    subject: str
    sent_at: str
    last_reply_at: Optional[str] = None
    conversation_history: List[Dict] = None

    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []

class Session:
    def __init__(self):
        self.email_sessions_table = 'email_sessions'
        self.conversation_messages_table = 'conversation_messages'

    def create_email_session(self, session_id: str, contact: Contact, 
                           subject: str, initial_message: str) -> bool:
        """Create a new email session"""
        try:
            # Insert email session
            session_data = {
                'session_id': session_id,
                'contact_email': contact.email,
                'contact_name': f"{contact.first_name} {contact.last_name}",
                'subject': subject,
                'sent_at': datetime.now(timezone.utc).isoformat()
            }
            
            session_result = supabase_client.insert(self.email_sessions_table, session_data)
            if not session_result:
                logger.error(f"Failed to create email session: {session_id}")
                return False
            
            # Insert initial message
            message_data = {
                'session_id': session_id,
                'message_type': 'sent',
                'content': initial_message,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            message_result = supabase_client.insert(self.conversation_messages_table, message_data)
            if not message_result:
                # Clean up the session if message creation failed
                self.delete_session(session_id)
                return False
            
            return True
            
        except Exception as e:
            # Clean up any partial session if it was created
            try:
                self.delete_session(session_id)
            except:
                pass
            return False

    def add_message_to_session(self, session_id: str, message_type: str, content: str, 
                              from_email: str = None) -> bool:
        """Add a message to an existing email session"""
        try:
            # First check if the session exists
            session_exists = self.get_session_by_id(session_id)
            if not session_exists:
                logger.error(f"This conversation session has been removed, cannot add message")
                return False
            
            # Add message
            message_data = {
                'session_id': session_id,
                'message_type': message_type,
                'content': content,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'from_email': from_email
            }
            
            message_result = supabase_client.insert(self.conversation_messages_table, message_data)
            if not message_result:
                logger.error(f"Failed to add message to session: {session_id}")
                return False
            
            # Update last_reply_at if it's a received message
            if message_type == 'received':
                update_data = {
                    'last_reply_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                supabase_client.update(self.email_sessions_table, update_data, {'session_id': session_id})
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding message to session: {e}")
            return False

    def get_session_history(self, session_id: str) -> Optional[EmailSession]:
        """Get complete session history including all messages"""
        try:
            # Get session info
            session_result = supabase_client.select(
                self.email_sessions_table,
                columns="session_id, contact_email, contact_name, subject, sent_at, last_reply_at",
                filters={'session_id': session_id}
            )
            
            if not session_result:
                return None
            
            session_row = session_result[0]
            
            # Get conversation history
            messages_result = supabase_client.select(
                self.conversation_messages_table,
                columns="message_type, content, timestamp, from_email",
                filters={'session_id': session_id}
            )
            
            conversation_history = []
            for msg_row in messages_result:
                conversation_history.append({
                    'type': msg_row['message_type'],
                    'content': msg_row['content'],
                    'timestamp': msg_row['timestamp'],
                    'from_email': msg_row['from_email']
                })
            
            # Sort by timestamp
            conversation_history.sort(key=lambda x: x['timestamp'])
            
            return EmailSession(
                session_id=session_row['session_id'],
                contact_email=session_row['contact_email'],
                contact_name=session_row['contact_name'],
                subject=session_row['subject'],
                sent_at=session_row['sent_at'],
                last_reply_at=session_row['last_reply_at'],
                conversation_history=conversation_history
            )
            
        except Exception as e:
            logger.error(f"Error getting session history: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages"""
        try:
            # Delete messages first (due to foreign key constraint)
            supabase_client.delete(self.conversation_messages_table, {'session_id': session_id})
            
            # Delete session
            result = supabase_client.delete(self.email_sessions_table, {'session_id': session_id})
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False

    def get_session_by_id(self, session_id: str) -> dict:
        """Get session information by ID"""
        try:
            result = supabase_client.select(
                self.email_sessions_table,
                columns="*",
                filters={'session_id': session_id}
            )
            
            if result:
                return result[0]
            return {}
            
        except Exception as e:
            logger.error(f"Error getting session by ID: {e}")
            return {}

    def get_session_by_email(self, email: str) -> Optional[str]:
        """Find an active session by contact email"""
        try:
            result = supabase_client.select(
                self.email_sessions_table,
                columns="session_id",
                filters={'contact_email': email, 'status': 'active'}
            )
            
            if result:
                return result[0]['session_id']
            return None
            
        except Exception as e:
            logger.error(f"Error finding active session by email: {e}")
            return None

    def start_fresh_session(self, session_id: str, contact: Contact, 
                           subject: str, initial_message: str) -> bool:
        """Start a fresh session for a user, deleting any existing active session"""
        try:
            # Check if there's an existing active session for this contact
            existing_session = self.get_session_by_email(contact.email)
            if existing_session:
                # Delete the old session and all its messages
                self.delete_session(existing_session)
            # Create the new session
            return self.create_email_session(session_id, contact, subject, initial_message)
            
        except Exception as e:
            logger.error(f"Error starting fresh session: {e}")
            return False 