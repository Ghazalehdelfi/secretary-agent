# =============================================================================
# utilities/phonebook.py
# =============================================================================
# 📞 Purpose:
# This file defines the PhoneBook class and Contact dataclass for managing
# contact information in the A2A system. The phonebook provides contact
# lookup, storage, and management functionality with integration to the
# Supabase database for persistence.
#
# ✅ Features:
# - Contact lookup by name (first, last, or full name)
# - Contact storage and retrieval from database
# - Agent association for A2A communication
# - Email address management
# - Contact CRUD operations (Create, Read, Update, Delete)
# - Fuzzy name matching for lookups
#
# 🔧 Dependencies:
# - Supabase client for database operations
# - Python dataclasses for data structures
# =============================================================================

import os
import logging
from typing import List, Optional
from dataclasses import dataclass

from utilities.supabase_client import supabase_client

# Set up logging for this module
logger = logging.getLogger(__name__)


@dataclass
class Contact:
    """
    📞 Contact: Data structure for contact information.
    
    This dataclass represents a contact in the phonebook system with
    personal information and optional agent/email associations for
    communication.
    
    Attributes:
        id (str): Unique identifier for the contact
        first_name (str): Contact's first name
        last_name (str): Contact's last name
        agent_name (Optional[str]): Name of the contact's A2A agent (if available)
        agent_url (Optional[str]): URL of the contact's A2A agent (if available)
        email (Optional[str]): Contact's email address (if available)
    """
    id: str
    first_name: str
    last_name: str
    agent_name: Optional[str] = None
    agent_url: Optional[str] = None
    email: Optional[str] = None


class PhoneBook:
    """
    📞 PhoneBook: Contact management system with database integration.
    
    This class provides comprehensive contact management functionality
    including lookup, storage, and retrieval operations. It integrates
    with Supabase for persistent storage and supports both agent-based
    and email-based communication methods.
    
    The phonebook supports fuzzy name matching for lookups and provides
    methods to check contact capabilities (agent availability, email
    availability) for routing communication appropriately.
    
    Attributes:
        table_name (str): Database table name for contacts
    """

    def __init__(self):
        """Initialize the PhoneBook with database configuration."""
        self.table_name = 'contacts'

    def lookup(self, name: str) -> Optional[Contact]:
        """
        Look up a contact by name using fuzzy matching.
        
        This method searches for contacts by first name, last name, or
        full name using case-insensitive partial matching. It returns
        the first matching contact found.
        
        Args:
            name (str): Name to search for (can be first, last, or full name)
            
        Returns:
            Optional[Contact]: Contact object if found, None otherwise
            
        Example:
            >>> phonebook = PhoneBook()
            >>> contact = phonebook.lookup("John")
            >>> if contact:
            ...     print(f"Found: {contact.first_name} {contact.last_name}")
        """
        try:
            # Retrieve all contacts from database
            result = supabase_client.select(
                self.table_name,
                columns="id, first_name, last_name, agent_name, agent_url, email"
            )
            
            # Perform fuzzy name matching
            search_term = name.lower()
            for row in result:
                first_name = row['first_name'].lower() if row['first_name'] else ""
                last_name = row['last_name'].lower() if row['last_name'] else ""
                full_name = f"{first_name} {last_name}".strip()
                
                # Check if search term matches any part of the name
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
            logger.error(f"Error looking up contact '{name}': {e}")
            return None

    def get_all_contacts(self) -> List[Contact]:
        """
        Retrieve all contacts from the database.
        
        Returns:
            List[Contact]: List of all contacts in the phonebook
            
        Example:
            >>> phonebook = PhoneBook()
            >>> contacts = phonebook.get_all_contacts()
            >>> for contact in contacts:
            ...     print(f"{contact.first_name} {contact.last_name}")
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
        Add a new contact to the phonebook.
        
        This method creates a new contact with a unique ID and stores it
        in the database. All fields except first_name and last_name are optional.
        
        Args:
            first_name (str): Contact's first name
            last_name (str): Contact's last name
            agent_name (str, optional): Name of the contact's A2A agent
            agent_url (str, optional): URL of the contact's A2A agent
            email (str, optional): Contact's email address
            
        Returns:
            bool: True if contact was added successfully, False otherwise
            
        Example:
            >>> phonebook = PhoneBook()
            >>> success = phonebook.add_contact(
            ...     "John", "Doe", 
            ...     agent_name="john_agent",
            ...     agent_url="http://localhost:5001",
            ...     email="john.doe@example.com"
            ... )
        """
        try:
            # Generate unique contact ID
            contact_id = os.urandom(8).hex()
            contact_data = {
                'id': contact_id,
                'first_name': first_name,
                'last_name': last_name,
                'agent_name': agent_name,
                'agent_url': agent_url,
                'email': email
            }
            
            # Insert contact into database
            result = supabase_client.insert(self.table_name, contact_data)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error adding contact '{first_name} {last_name}': {e}")
            return False

    def remove_contact(self, contact_id: str) -> bool:
        """
        Remove a contact from the phonebook by ID.
        
        Args:
            contact_id (str): Unique identifier of the contact to remove
            
        Returns:
            bool: True if contact was removed successfully, False otherwise
            
        Example:
            >>> phonebook = PhoneBook()
            >>> success = phonebook.remove_contact("contact_123")
        """
        try:
            result = supabase_client.delete(self.table_name, {'id': contact_id})
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"Error removing contact '{contact_id}': {e}")
            return False

    def has_agent(self, contact: Contact) -> bool:
        """
        Check if a contact has an associated A2A agent.
        
        This method checks if the contact has both an agent name and URL,
        indicating they can communicate via the A2A protocol.
        
        Args:
            contact (Contact): Contact to check
            
        Returns:
            bool: True if contact has an agent, False otherwise
            
        Example:
            >>> contact = Contact("1", "John", "Doe", agent_name="john_agent", agent_url="http://localhost:5001")
            >>> has_agent = phonebook.has_agent(contact)
        """
        return contact.agent_name is not None and contact.agent_url is not None

    def has_email(self, contact: Contact) -> bool:
        """
        Check if a contact has a valid email address.
        
        This method checks if the contact has a non-empty email address
        for email-based communication.
        
        Args:
            contact (Contact): Contact to check
            
        Returns:
            bool: True if contact has an email, False otherwise
            
        Example:
            >>> contact = Contact("1", "John", "Doe", email="john@example.com")
            >>> has_email = phonebook.has_email(contact)
        """
        return contact.email is not None and contact.email.strip() != ""

    def update_contact(self, contact_id: str, **kwargs) -> bool:
        """
        Update a contact's information in the database.
        
        This method allows updating any contact field by providing keyword
        arguments. Only the specified fields will be updated.
        
        Args:
            contact_id (str): Unique identifier of the contact to update
            **kwargs: Fields to update (first_name, last_name, agent_name, agent_url, email)
            
        Returns:
            bool: True if contact was updated successfully, False otherwise
            
        Example:
            >>> phonebook = PhoneBook()
            >>> success = phonebook.update_contact(
            ...     "contact_123",
            ...     email="new.email@example.com",
            ...     agent_url="http://new-agent:5002"
            ... )
        """
        try:
            result = supabase_client.update(self.table_name, kwargs, {'id': contact_id})
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"Error updating contact '{contact_id}': {e}")
            return False 