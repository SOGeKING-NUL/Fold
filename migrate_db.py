"""
Database Migration Script
=========================
Run this to create/update the database schema with Clerk support.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from api.db.connection import reset_database_schema

if __name__ == "__main__":
    print("Creating database schema with Clerk support...")
    reset_database_schema()
    print("✅ Database schema created successfully!")
    print("✅ Tables created: users, accounts, payment_profiles, journal_transactions, journal_media, ledger_entries, ingestion_events")
    print("✅ Clerk fields added: clerk_user_id, email, full_name, avatar_url")
