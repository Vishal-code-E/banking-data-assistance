#!/usr/bin/env python3
"""
Banking Dataset Generator
Generates realistic banking data for testing the AI Banking Assistant
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from faker import Faker
    import numpy as np
except ImportError:
    print("❌ Missing required packages. Install with:")
    print("   pip install faker numpy")
    sys.exit(1)


class BankingDatasetGenerator:
    def __init__(self, output_path: str, num_customers: int = 10000, seed: int = 42):
        self.output_path = output_path
        self.num_customers = num_customers
        self.seed = seed
        
        # Initialize random generators
        self.fake = Faker()
        Faker.seed(seed)
        np.random.seed(seed)
        
        # Configuration
        self.avg_accounts_per_customer = 2.5
        self.avg_transactions_per_account = 40
        
        # Database connection
        self.conn = None
        self.cursor = None
    
    def connect_db(self):
        """Connect to database and load schema"""
        print(f"📁 Creating database: {self.output_path}")
        
        # Remove existing database
        Path(self.output_path).unlink(missing_ok=True)
        
        self.conn = sqlite3.connect(self.output_path)
        self.cursor = self.conn.cursor()
        
        # Load schema
        schema_path = Path(__file__).parent / 'models' / 'schema.sql'
        if schema_path.exists():
            print(f"📋 Loading schema from {schema_path}")
            with open(schema_path, 'r') as f:
                # Execute only CREATE/PRAGMA statements, skip INSERT
                schema_sql = f.read()
                # Split by semicolon and filter
                statements = schema_sql.split(';')
                create_only = []
                for statement in statements:
                    statement = statement.strip()
                    if statement and not statement.upper().startswith('INSERT'):
                        create_only.append(statement)
                
                self.cursor.executescript(';\n'.join(create_only) + ';')
            
            # Clear any sample data that might have been inserted
            self.cursor.execute("DELETE FROM transactions")
            self.cursor.execute("DELETE FROM accounts")
            self.cursor.execute("DELETE FROM customers")
            self.conn.commit()
        else:
            print(f"⚠️  Schema file not found, creating basic schema")
            self.create_basic_schema()
    
    def create_basic_schema(self):
        """Create basic schema if schema.sql not found"""
        self.cursor.executescript("""
            PRAGMA foreign_keys = ON;
            
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                account_number TEXT NOT NULL UNIQUE,
                balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('credit', 'debit')),
                amount DECIMAL(15, 2) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );
        """)
    
    def generate_customers(self):
        """Generate customer records"""
        print(f"\n👥 Generating {self.num_customers:,} customers...")
        
        # Disable foreign keys for faster insertion
        self.cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Insert customers one by one to get proper IDs
        customers = []
        
        for i in range(self.num_customers):
            name = self.fake.name()
            email = self.fake.unique.email()
            created_at = self.fake.date_time_between(start_date='-5y', end_date='now')
            
            self.cursor.execute(
                "INSERT INTO customers (name, email, created_at) VALUES (?, ?, ?)",
                (name, email, created_at)
            )
            
            customers.append({
                'id': self.cursor.lastrowid,
                'created_at': created_at
            })
            
            if (i + 1) % 10000 == 0:
                print(f"   ✓ {i + 1:,} customers created")
                self.conn.commit()
        
        self.conn.commit()
        print(f"   ✅ {len(customers):,} customers created")
        
        return customers
    
    def generate_accounts(self, customers):
        """Generate account records"""
        print(f"\n💳 Generating accounts...")
        
        accounts = []
        total_accounts = 0
        
        for customer in customers:
            # Number of accounts per customer (Poisson distribution)
            num_accounts = min(np.random.poisson(self.avg_accounts_per_customer) + 1, 10)
            
            for _ in range(num_accounts):
                account_number = f"ACC{self.fake.unique.random_number(digits=10, fix_len=True)}"
                
                # Log-normal distribution for balance (realistic)
                balance = max(0, np.random.lognormal(mean=9, sigma=1.5))
                
                # Account created between customer creation and now
                created_at = self.fake.date_time_between(
                    start_date=customer['created_at'],
                    end_date='now'
                )
                
                self.cursor.execute(
                    "INSERT INTO accounts (customer_id, account_number, balance, created_at) VALUES (?, ?, ?, ?)",
                    (customer['id'], account_number, round(balance, 2), created_at)
                )
                
                accounts.append({
                    'id': self.cursor.lastrowid,
                    'created_at': created_at,
                    'balance': balance
                })
                
                total_accounts += 1
                
                if total_accounts % 10000 == 0:
                    print(f"   ✓ {total_accounts:,} accounts created")
                    self.conn.commit()
        
        self.conn.commit()
        print(f"   ✅ {total_accounts:,} accounts created")
        
        return accounts
    
    def generate_transactions(self, accounts):
        """Generate transaction records that sum to account balance"""
        print(f"\n💸 Generating transactions...")
        
        total_transactions = 0
        
        for idx, account in enumerate(accounts):
            # Number of transactions per account
            num_transactions = max(1, np.random.poisson(self.avg_transactions_per_account))
            
            # Generate transactions that sum to account balance
            target_balance = account['balance']
            running_balance = 0
            
            for i in range(num_transactions):
                # Last transaction ensures balance matches
                if i == num_transactions - 1:
                    remaining = target_balance - running_balance
                    if abs(remaining) < 0.01:  # Already balanced
                        continue
                    if remaining > 0:
                        amount = remaining
                        transaction_type = 'credit'
                    else:
                        amount = abs(remaining)
                        transaction_type = 'debit'
                else:
                    # Random transaction
                    amount = max(1, np.random.lognormal(mean=4, sigma=2))
                    transaction_type = 'credit' if np.random.random() < 0.55 else 'debit'
                
                # Random timestamp between account creation and now
                created_at = self.fake.date_time_between(
                    start_date=account['created_at'],
                    end_date='now'
                )
                
                self.cursor.execute(
                    "INSERT INTO transactions (account_id, type, amount, created_at) VALUES (?, ?, ?, ?)",
                    (account['id'], transaction_type, round(amount, 2), created_at)
                )
                
                # Update running balance
                if transaction_type == 'credit':
                    running_balance += amount
                else:
                    running_balance -= amount
                
                total_transactions += 1
                
                if total_transactions % 50000 == 0:
                    print(f"   ✓ {total_transactions:,} transactions created")
                    self.conn.commit()
            
            if (idx + 1) % 10000 == 0:
                print(f"   ✓ Processed {idx + 1:,} accounts")
                self.conn.commit()
        
        self.conn.commit()
        print(f"   ✅ {total_transactions:,} transactions created")
        
        return total_transactions
    
    def create_indexes(self):
        """Create indexes for performance"""
        print(f"\n🔍 Creating indexes...")
        
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_customer_id ON accounts(customer_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON transactions(account_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)")
        
        print(f"   ✅ Indexes created")
    
    def vacuum(self):
        """Optimize database"""
        print(f"\n🧹 Optimizing database...")
        self.cursor.execute("PRAGMA foreign_keys = ON")
        self.cursor.execute("VACUUM")
        print(f"   ✅ Database optimized")
    
    def generate(self):
        """Main generation workflow"""
        start_time = datetime.now()
        
        print("="*60)
        print("BANKING DATASET GENERATOR")
        print("="*60)
        print(f"Target: {self.num_customers:,} customers")
        print(f"Random seed: {self.seed}")
        print(f"Output: {self.output_path}")
        print()
        
        try:
            # Connect and setup
            self.connect_db()
            
            # Generate data
            customers = self.generate_customers()
            accounts = self.generate_accounts(customers)
            num_transactions = self.generate_transactions(accounts)
            
            # Optimize
            self.create_indexes()
            self.vacuum()
            
            # Summary
            duration = (datetime.now() - start_time).total_seconds()
            
            print("\n" + "="*60)
            print("GENERATION COMPLETE")
            print("="*60)
            print(f"✅ Customers: {len(customers):,}")
            print(f"✅ Accounts: {len(accounts):,}")
            print(f"✅ Transactions: {num_transactions:,}")
            print(f"⏱️  Duration: {duration:.1f} seconds")
            print(f"📁 Database: {self.output_path}")
            
            # File size
            file_size = Path(self.output_path).stat().st_size / (1024 * 1024)
            print(f"💾 File size: {file_size:.2f} MB")
            print()
            print("Next steps:")
            print(f"  1. Validate: python validate_dataset.py {self.output_path}")
            print(f"  2. Test with AI assistant")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ Error during generation: {e}")
            raise
        
        finally:
            if self.conn:
                self.conn.close()


def main():
    parser = argparse.ArgumentParser(description="Generate banking dataset for AI testing")
    parser.add_argument(
        '--customers',
        type=int,
        default=10000,
        help='Number of customers to generate (default: 10000)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='banking_data.db',
        help='Output database file (default: banking_data.db)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    
    args = parser.parse_args()
    
    generator = BankingDatasetGenerator(
        output_path=args.output,
        num_customers=args.customers,
        seed=args.seed
    )
    
    generator.generate()


if __name__ == "__main__":
    main()
