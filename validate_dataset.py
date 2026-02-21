#!/usr/bin/env python3
"""
Dataset Validation Script for Banking Data Assistant
Validates data quality, referential integrity, and distributions
"""

import sqlite3
import sys
from datetime import datetime
from typing import Dict, List, Tuple


class DatasetValidator:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict = {}
    
    def run_all_checks(self) -> bool:
        """Run all validation checks"""
        print(f"🔍 Validating dataset: {self.db_path}\n")
        
        # Basic counts
        self.check_record_counts()
        
        # Referential integrity
        self.check_foreign_keys()
        
        # Uniqueness constraints
        self.check_unique_constraints()
        
        # Temporal consistency
        self.check_temporal_consistency()
        
        # Financial consistency
        self.check_balance_consistency()
        
        # Data distributions
        self.check_distributions()
        
        # Print results
        self.print_results()
        
        return len(self.errors) == 0
    
    def check_record_counts(self):
        """Check basic record counts"""
        print("📊 Record Counts:")
        
        cursor = self.conn.cursor()
        
        # Customers
        customer_count = cursor.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        self.stats['customers'] = customer_count
        print(f"   Customers: {customer_count:,}")
        
        # Accounts
        account_count = cursor.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        self.stats['accounts'] = account_count
        print(f"   Accounts: {account_count:,}")
        
        # Transactions
        transaction_count = cursor.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        self.stats['transactions'] = transaction_count
        print(f"   Transactions: {transaction_count:,}")
        
        # Ratios
        if customer_count > 0:
            accounts_per_customer = account_count / customer_count
            print(f"   Avg Accounts/Customer: {accounts_per_customer:.2f}")
            self.stats['accounts_per_customer'] = accounts_per_customer
        
        if account_count > 0:
            transactions_per_account = transaction_count / account_count
            print(f"   Avg Transactions/Account: {transactions_per_account:.2f}")
            self.stats['transactions_per_account'] = transactions_per_account
        
        print()
    
    def check_foreign_keys(self):
        """Verify foreign key relationships"""
        print("🔗 Foreign Key Integrity:")
        
        cursor = self.conn.cursor()
        
        # Check accounts.customer_id -> customers.id
        orphaned_accounts = cursor.execute("""
            SELECT COUNT(*) 
            FROM accounts a 
            LEFT JOIN customers c ON a.customer_id = c.id 
            WHERE c.id IS NULL
        """).fetchone()[0]
        
        if orphaned_accounts > 0:
            self.errors.append(f"Found {orphaned_accounts} orphaned accounts (invalid customer_id)")
        else:
            print(f"   ✅ All accounts have valid customer_id")
        
        # Check transactions.account_id -> accounts.id
        orphaned_transactions = cursor.execute("""
            SELECT COUNT(*) 
            FROM transactions t 
            LEFT JOIN accounts a ON t.account_id = a.id 
            WHERE a.id IS NULL
        """).fetchone()[0]
        
        if orphaned_transactions > 0:
            self.errors.append(f"Found {orphaned_transactions} orphaned transactions (invalid account_id)")
        else:
            print(f"   ✅ All transactions have valid account_id")
        
        print()
    
    def check_unique_constraints(self):
        """Check uniqueness constraints"""
        print("🔑 Uniqueness Constraints:")
        
        cursor = self.conn.cursor()
        
        # Check customers.email uniqueness
        duplicate_emails = cursor.execute("""
            SELECT COUNT(*) 
            FROM (
                SELECT email, COUNT(*) as cnt 
                FROM customers 
                GROUP BY email 
                HAVING cnt > 1
            )
        """).fetchone()[0]
        
        if duplicate_emails > 0:
            self.errors.append(f"Found {duplicate_emails} duplicate email addresses")
        else:
            print(f"   ✅ All customer emails are unique")
        
        # Check accounts.account_number uniqueness
        duplicate_accounts = cursor.execute("""
            SELECT COUNT(*) 
            FROM (
                SELECT account_number, COUNT(*) as cnt 
                FROM accounts 
                GROUP BY account_number 
                HAVING cnt > 1
            )
        """).fetchone()[0]
        
        if duplicate_accounts > 0:
            self.errors.append(f"Found {duplicate_accounts} duplicate account numbers")
        else:
            print(f"   ✅ All account numbers are unique")
        
        print()
    
    def check_temporal_consistency(self):
        """Check date/time consistency"""
        print("📅 Temporal Consistency:")
        
        cursor = self.conn.cursor()
        
        # Check accounts.created_at >= customers.created_at
        invalid_account_dates = cursor.execute("""
            SELECT COUNT(*) 
            FROM accounts a 
            JOIN customers c ON a.customer_id = c.id 
            WHERE a.created_at < c.created_at
        """).fetchone()[0]
        
        if invalid_account_dates > 0:
            self.errors.append(f"Found {invalid_account_dates} accounts created before their customer")
        else:
            print(f"   ✅ All accounts created after their customer")
        
        # Check transactions.created_at >= accounts.created_at
        invalid_transaction_dates = cursor.execute("""
            SELECT COUNT(*) 
            FROM transactions t 
            JOIN accounts a ON t.account_id = a.id 
            WHERE t.created_at < a.created_at
        """).fetchone()[0]
        
        if invalid_transaction_dates > 0:
            self.errors.append(f"Found {invalid_transaction_dates} transactions before account creation")
        else:
            print(f"   ✅ All transactions created after their account")
        
        # Check for future dates
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        future_customers = cursor.execute(
            "SELECT COUNT(*) FROM customers WHERE created_at > ?", 
            (current_date,)
        ).fetchone()[0]
        
        future_accounts = cursor.execute(
            "SELECT COUNT(*) FROM accounts WHERE created_at > ?", 
            (current_date,)
        ).fetchone()[0]
        
        future_transactions = cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE created_at > ?", 
            (current_date,)
        ).fetchone()[0]
        
        if future_customers + future_accounts + future_transactions > 0:
            self.warnings.append(f"Found future dates: {future_customers} customers, {future_accounts} accounts, {future_transactions} transactions")
        else:
            print(f"   ✅ No future-dated records")
        
        print()
    
    def check_balance_consistency(self):
        """Verify account balances match transaction sums"""
        print("💰 Financial Consistency:")
        
        cursor = self.conn.cursor()
        
        # Calculate balances from transactions
        mismatched = cursor.execute("""
            SELECT 
                a.id,
                a.account_number,
                a.balance as declared_balance,
                COALESCE(SUM(CASE WHEN t.type='credit' THEN t.amount ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN t.type='debit' THEN t.amount ELSE 0 END), 0) as calculated_balance,
                ABS(a.balance - (
                    COALESCE(SUM(CASE WHEN t.type='credit' THEN t.amount ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN t.type='debit' THEN t.amount ELSE 0 END), 0)
                )) as difference
            FROM accounts a
            LEFT JOIN transactions t ON a.id = t.account_id
            GROUP BY a.id, a.account_number, a.balance
            HAVING ABS(difference) > 0.10
        """).fetchall()
        
        if len(mismatched) > 0:
            self.errors.append(f"Found {len(mismatched)} accounts with balance mismatches")
            print(f"   ❌ {len(mismatched)} accounts have incorrect balances")
            
            # Show first 5 examples
            for i, row in enumerate(mismatched[:5]):
                print(f"      - Account {row[1]}: Declared ${row[2]:.2f}, Calculated ${row[3]:.2f}, Diff ${row[4]:.2f}")
            
            if len(mismatched) > 5:
                print(f"      ... and {len(mismatched) - 5} more")
        else:
            print(f"   ✅ All account balances match transaction sums")
        
        # Check for negative amounts
        negative_transactions = cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE amount <= 0"
        ).fetchone()[0]
        
        if negative_transactions > 0:
            self.errors.append(f"Found {negative_transactions} transactions with zero or negative amounts")
        else:
            print(f"   ✅ All transaction amounts are positive")
        
        print()
    
    def check_distributions(self):
        """Check data distributions look reasonable"""
        print("📈 Data Distributions:")
        
        cursor = self.conn.cursor()
        
        # Account balance distribution
        balance_stats = cursor.execute("""
            SELECT 
                MIN(balance) as min_balance,
                AVG(balance) as avg_balance,
                MAX(balance) as max_balance,
                COUNT(*) as total_accounts
            FROM accounts
        """).fetchone()
        
        print(f"   Account Balances:")
        print(f"      Min: ${balance_stats[0]:,.2f}")
        print(f"      Avg: ${balance_stats[1]:,.2f}")
        print(f"      Max: ${balance_stats[2]:,.2f}")
        
        # Transaction amount distribution
        transaction_stats = cursor.execute("""
            SELECT 
                MIN(amount) as min_amount,
                AVG(amount) as avg_amount,
                MAX(amount) as max_amount,
                COUNT(*) as total_transactions
            FROM transactions
        """).fetchone()
        
        print(f"   Transaction Amounts:")
        print(f"      Min: ${transaction_stats[0]:,.2f}")
        print(f"      Avg: ${transaction_stats[1]:,.2f}")
        print(f"      Max: ${transaction_stats[2]:,.2f}")
        
        # Transaction type distribution
        type_dist = cursor.execute("""
            SELECT 
                type,
                COUNT(*) as count,
                SUM(amount) as total_amount
            FROM transactions
            GROUP BY type
        """).fetchall()
        
        print(f"   Transaction Types:")
        total_txns = sum(row[1] for row in type_dist)
        for row in type_dist:
            percentage = (row[1] / total_txns * 100) if total_txns > 0 else 0
            print(f"      {row[0].capitalize()}: {row[1]:,} ({percentage:.1f}%), Total: ${row[2]:,.2f}")
        
        # Check for accounts with no transactions
        empty_accounts = cursor.execute("""
            SELECT COUNT(*) 
            FROM accounts a 
            LEFT JOIN transactions t ON a.id = t.account_id 
            WHERE t.id IS NULL
        """).fetchone()[0]
        
        if empty_accounts > 0:
            percentage = (empty_accounts / balance_stats[3] * 100) if balance_stats[3] > 0 else 0
            print(f"   ⚠️  {empty_accounts} accounts ({percentage:.1f}%) have no transactions")
            if empty_accounts / balance_stats[3] > 0.2:  # More than 20%
                self.warnings.append(f"{percentage:.1f}% of accounts have no transactions (expected <20%)")
        
        print()
    
    def print_results(self):
        """Print validation summary"""
        print("\n" + "="*60)
        print("VALIDATION RESULTS")
        print("="*60)
        
        if len(self.errors) == 0 and len(self.warnings) == 0:
            print("✅ ALL CHECKS PASSED!")
            print("\nDataset is valid and ready to use.")
        else:
            if len(self.errors) > 0:
                print(f"❌ FAILED: {len(self.errors)} error(s) found\n")
                for i, error in enumerate(self.errors, 1):
                    print(f"{i}. {error}")
            
            if len(self.warnings) > 0:
                print(f"\n⚠️  WARNINGS: {len(self.warnings)} warning(s)\n")
                for i, warning in enumerate(self.warnings, 1):
                    print(f"{i}. {warning}")
        
        print("\n" + "="*60)
        print()
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_dataset.py <database_file.db>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    
    validator = DatasetValidator(db_path)
    
    try:
        success = validator.run_all_checks()
        validator.close()
        
        sys.exit(0 if success else 1)
    
    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        validator.close()
        sys.exit(1)


if __name__ == "__main__":
    main()
