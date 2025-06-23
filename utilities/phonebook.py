import os
import logging
from typing import List, Optional
from dataclasses import dataclass

from utilities.supabase_client import supabase_client

logger = logging.getLogger(__name__)

@dataclass
class Contact:
    id: str
    first_name: str
    last_name: str
    agent_name: Optional[str] = None
    agent_url: Optional[str] = None
    email: Optional[str] = None

class PhoneBook:
    def __init__(self):
        self.table_name = 'contacts'

    def lookup(self, name: str) -> Optional[Contact]:
        """
        Look up a contact by name (first name, last name, or full name)
        """
        try:
            # Use simple Supabase table query instead of raw SQL
            # Get all contacts and filter in Python for simplicity
            result = supabase_client.select(
                self.table_name,
                columns="id, first_name, last_name, agent_name, agent_url, email"
            )
            
            # Filter contacts that match the search term
            search_term = name.lower()
            for row in result:
                first_name = row['first_name'].lower() if row['first_name'] else ""
                last_name = row['last_name'].lower() if row['last_name'] else ""
                full_name = f"{first_name} {last_name}".strip()
                
                if (search_term in first_name or 
                    search_term in last_name or 
                    search_term in full_name):
                    return Contact(
                        id=row['id'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        agent_name=row['agent_name'],
                        agent_url=row['agent_url'],
                        email=row['email']
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error looking up contact: {e}")
            return None

    def get_all_contacts(self) -> List[Contact]:
        """
        Get all contacts from the database
        """
        try:
            result = supabase_client.select(
                self.table_name,
                columns="id, first_name, last_name, agent_name, agent_url, email",
                filters={}
            )
            
            contacts = []
            for row in result:
                contacts.append(Contact(
                    id=row['id'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    agent_name=row['agent_name'],
                    agent_url=row['agent_url'],
                    email=row['email']
                ))
            
            return contacts
            
        except Exception as e:
            logger.error(f"Error getting all contacts: {e}")
            return []

    def add_contact(self, first_name: str, last_name: str, agent_name: str = None, 
                   agent_url: str = None, email: str = None) -> bool:
        """
        Add a new contact to the database
        """
        try:
            contact_id = os.urandom(8).hex()
            contact_data = {
                'id': contact_id,
                'first_name': first_name,
                'last_name': last_name,
                'agent_name': agent_name,
                'agent_url': agent_url,
                'email': email
            }
            
            result = supabase_client.insert(self.table_name, contact_data)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error adding contact: {e}")
            return False

    def remove_contact(self, contact_id: str) -> bool:
        """
        Remove a contact from the database
        """
        try:
            result = supabase_client.delete(self.table_name, {'id': contact_id})
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"Error removing contact: {e}")
            return False

    def has_agent(self, contact: Contact) -> bool:
        """
        Check if a contact has an associated agent
        """
        return contact.agent_name is not None and contact.agent_url is not None

    def has_email(self, contact: Contact) -> bool:
        """
        Check if a contact has an email address
        """
        return contact.email is not None and contact.email.strip() != ""

    def update_contact(self, contact_id: str, **kwargs) -> bool:
        """
        Update a contact's information
        """
        try:
            result = supabase_client.update(self.table_name, kwargs, {'id': contact_id})
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"Error updating contact: {e}")
            return False 