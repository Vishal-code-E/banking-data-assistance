# Quick Start: Dataset Generation Methods

This guide provides quick templates for generating your banking dataset.

## Method 1: Python with Faker (Recommended)

### Setup
```bash
pip install faker numpy pandas
```

### Basic Template
```python
from faker import Faker
import random
import sqlite3
from datetime import datetime, timedelta
import numpy as np

fake = Faker()
random.seed(42)  # For reproducibility
np.random.seed(42)

# Configuration
NUM_CUSTOMERS = 10000
AVG_ACCOUNTS_PER_CUSTOMER = 2.5
AVG_TRANSACTIONS_PER_ACCOUNT = 40

# Connect to database
conn = sqlite3.connect('banking_data.db')
cursor = conn.cursor()

# Load schema
with open('models/schema.sql', 'r') as f:
    cursor.executescript(f.read())

# 1. Generate Customers
customers = []
for i in range(NUM_CUSTOMERS):
    name = fake.name()
    email = fake.email()
    created_at = fake.date_time_between(start_date='-5y', end_date='now')
    
    cursor.execute(
        "INSERT INTO customers (name, email, created_at) VALUES (?, ?, ?)",
        (name, email, created_at)
    )
    customers.append({
        'id': cursor.lastrowid,
        'created_at': created_at
    })

# 2. Generate Accounts
accounts = []
for customer in customers:
    num_accounts = np.random.poisson(AVG_ACCOUNTS_PER_CUSTOMER) + 1
    num_accounts = min(num_accounts, 10)  # Cap at 10
    
    for _ in range(num_accounts):
        account_number = f"ACC{fake.random_number(digits=10)}"
        balance = np.random.lognormal(mean=9, sigma=1.5)  # Log-normal distribution
        created_at = fake.date_time_between(
            start_date=customer['created_at'], 
            end_date='now'
        )
        
        cursor.execute(
            "INSERT INTO accounts (customer_id, account_number, balance, created_at) VALUES (?, ?, ?, ?)",
            (customer['id'], account_number, balance, created_at)
        )
        accounts.append({
            'id': cursor.lastrowid,
            'created_at': created_at,
            'balance': balance
        })

# 3. Generate Transactions (ensuring balance consistency)
for account in accounts:
    num_transactions = np.random.poisson(AVG_TRANSACTIONS_PER_ACCOUNT)
    
    # Generate transactions that sum to account balance
    running_balance = 0
    
    for i in range(num_transactions):
        # Random transaction type and amount
        is_credit = random.random() < 0.55  # 55% credits
        
        if i == num_transactions - 1:
            # Last transaction: force balance to match
            amount = abs(account['balance'] - running_balance)
            transaction_type = 'credit' if account['balance'] > running_balance else 'debit'
        else:
            amount = np.random.lognormal(mean=4, sigma=2)  # ~$55 median
            transaction_type = 'credit' if is_credit else 'debit'
        
        created_at = fake.date_time_between(
            start_date=account['created_at'],
            end_date='now'
        )
        
        cursor.execute(
            "INSERT INTO transactions (account_id, type, amount, created_at) VALUES (?, ?, ?, ?)",
            (account['id'], transaction_type, amount, created_at)
        )
        
        if transaction_type == 'credit':
            running_balance += amount
        else:
            running_balance -= amount

conn.commit()
conn.close()

print("✅ Dataset generated successfully!")
```

---

## Method 2: SQL-Based Generation (SQLite)

For smaller datasets, pure SQL can work:

```sql
-- Generate customers using recursive CTE
WITH RECURSIVE cnt(x) AS (
    SELECT 1
    UNION ALL
    SELECT x+1 FROM cnt
    LIMIT 1000
)
INSERT INTO customers (name, email, created_at)
SELECT 
    'Customer ' || x,
    'customer' || x || '@email.com',
    datetime('2020-01-01', '+' || (x * 5) || ' days')
FROM cnt;

-- Generate accounts (2-3 per customer)
WITH RECURSIVE 
customers_list AS (SELECT id FROM customers),
cnt(x) AS (
    SELECT 1 UNION ALL SELECT x+1 FROM cnt LIMIT 3
)
INSERT INTO accounts (customer_id, account_number, balance, created_at)
SELECT 
    c.id,
    'ACC' || c.id || x,
    ABS(RANDOM() % 50000) + 1000.0,
    datetime('2020-01-01', '+' || ((c.id + x) * 3) || ' days')
FROM customers_list c, cnt
WHERE x <= (ABS(RANDOM() % 2) + 2);
```

**Note**: SQL method is limited for complex distributions.

---

## Method 3: Mockaroo (GUI Tool)

1. Visit https://www.mockaroo.com/
2. Define schema for each table
3. Set relationships
4. Download as SQL or CSV
5. Import into SQLite

**Limitations**: 
- Free tier: 1,000 rows max
- Paid: Up to 1M rows

---

## Method 4: CSV Import

If you have CSVs from another source:

```bash
# customers.csv, accounts.csv, transactions.csv

sqlite3 banking_data.db <<EOF
.mode csv
.import customers.csv customers
.import accounts.csv accounts
.import transactions.csv transactions
EOF
```

---

## Method 5: Realistic Dataset from Kaggle

Search for existing banking datasets:

1. **Berka Dataset** (Czech Bank): https://www.kaggle.com/datasets/berka/czech-bank-account
2. **Bank Marketing**: https://www.kaggle.com/datasets/henriqueyamahata/bank-marketing
3. **Credit Card Transactions**: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud

**Note**: You'll need to transform these to match your schema.

---

## Batch Generation for Large Datasets

For 1M+ records, use batch insertion:

```python
# Batch insert (faster)
batch_size = 10000
customer_batch = []

for i in range(NUM_CUSTOMERS):
    customer_batch.append((
        fake.name(),
        fake.email(),
        fake.date_time_between(start_date='-5y', end_date='now')
    ))
    
    if len(customer_batch) >= batch_size:
        cursor.executemany(
            "INSERT INTO customers (name, email, created_at) VALUES (?, ?, ?)",
            customer_batch
        )
        customer_batch = []

# Insert remaining
if customer_batch:
    cursor.executemany(
        "INSERT INTO customers (name, email, created_at) VALUES (?, ?, ?)",
        customer_batch
    )

conn.commit()
```

---

## Performance Tips

1. **Disable foreign keys during bulk insert**:
```python
cursor.execute("PRAGMA foreign_keys = OFF")
# ... insert data ...
cursor.execute("PRAGMA foreign_keys = ON")
```

2. **Use transactions**:
```python
cursor.execute("BEGIN TRANSACTION")
# ... many inserts ...
cursor.execute("COMMIT")
```

3. **Add indexes AFTER data load**:
```python
# Load all data first
# Then create indexes
cursor.execute("CREATE INDEX idx_accounts_customer_id ON accounts(customer_id)")
```

4. **VACUUM after bulk insert**:
```python
conn.execute("VACUUM")
```

---

## Validation

After generation, always validate:

```bash
python validate_dataset.py banking_data.db
```

---

## Recommended Workflow

1. **Start Small**: Generate 1K customers first
2. **Validate**: Run validation script
3. **Test Queries**: Try your AI assistant queries
4. **Scale Up**: Generate 10K, 100K, 1M
5. **Benchmark**: Measure query performance
6. **Optimize**: Add indexes, tune distributions

---

## Example: Complete 10K Customer Dataset

See `generate_dataset.py` (create this file based on Method 1)

```bash
# Generate
python generate_dataset.py --customers 10000 --output banking_10k.db

# Validate
python validate_dataset.py banking_10k.db

# Test
python test_queries.py banking_10k.db
```

---

## Need Help?

- **Distribution issues?** → Use numpy's random distributions
- **Performance slow?** → Use batch inserts and disable indexes during load
- **Balance mismatch?** → Generate transactions forward from 0 to target balance
- **Too much memory?** → Generate in chunks, write to disk incrementally

Good luck! 🚀
