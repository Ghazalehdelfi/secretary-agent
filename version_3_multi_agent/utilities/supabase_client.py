import os
import logging
from typing import Dict, Any, List
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class SupabaseClient:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
    
    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a single record into a table"""
        try:
            result = self.client.table(table).insert(data).execute()
            if result.data:
                return result.data[0]
            return {}
        except Exception as e:
            logger.error(f"Error inserting into {table}: {e}")
            raise
    
    def insert_many(self, table: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Insert multiple records into a table"""
        try:
            result = self.client.table(table).insert(data).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error inserting many into {table}: {e}")
            raise
    
    def select(self, table: str, columns: str = "*", filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Select records from a table with optional filters"""
        try:
            query = self.client.table(table).select(columns)
            
            if filters:
                for key, value in filters.items():
                    if isinstance(value, (list, tuple)):
                        query = query.in_(key, value)
                    else:
                        query = query.eq(key, value)
            
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error selecting from {table}: {e}")
            raise
    
    def update(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update records in a table"""
        try:
            query = self.client.table(table).update(data)
            
            for key, value in filters.items():
                query = query.eq(key, value)
            
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error updating {table}: {e}")
            raise
    
    def delete(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete records from a table"""
        try:
            query = self.client.table(table).delete()
            
            for key, value in filters.items():
                query = query.eq(key, value)
            
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error deleting from {table}: {e}")
            raise

# Global instance
supabase_client = SupabaseClient() 