# Large-Scale Dataset Requirements for Banking Data Assistant

## 📊 Overview
This document outlines the dataset specifications needed to test the Banking Data Assistant at scale. The system currently has 3 tables: **customers**, **accounts**, and **transactions**.

---

## 🎯 Dataset Scale Recommendations

### Small Scale (Development/Testing)
- **Customers**: 1,000
- **Accounts**: 2,500 (avg 2.5 accounts per customer)
- **Transactions**: 50,000 (avg 20 transactions per account)
- **Database Size**: ~5-10 MB

### Medium Scale (Staging/QA)
- **Customers**: 50,000
- **Accounts**: 125,000 (avg 2.5 accounts per customer)
- **Transactions**: 5,000,000 (avg 40 transactions per account)
- **Database Size**: ~500 MB - 1 GB

### Large Scale (Production Simulation)
- **Customers**: 500,000
- **Accounts**: 1,250,000 (avg 2.5 accounts per customer)
- **Transactions**: 50,000,000 (avg 40 transactions per account)
- **Database Size**: ~5-10 GB

### Enterprise Scale (Stress Testing)
- **Customers**: 5,000,000
- **Accounts**: 12,500,000 (avg 2.5 accounts per customer)
- **Transactions**: 500,000,000+ (avg 40 transactions per account)
- **Database Size**: ~50-100 GB

---

## 📋 Table 1: CUSTOMERS

### Schema
```sql
CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Data Distribution Requirements

#### 1. **Names** (Realistic & Diverse)
- **First Names**: 500+ unique first names
  - Mix of: Common (John, Mary, Michael), Modern (Aiden, Sophia), International (Raj, Wei, Ahmed, Sofia)
  - Distribution: 60% common, 30% modern, 10% international
  
- **Last Names**: 1000+ unique surnames
  - Mix of: Smith, Johnson, Williams, Garcia, Martinez, Chen, Patel, etc.
  - Regional diversity: US (40%), European (30%), Asian (20%), Other (10%)

- **Full Name Pattern**: `{First} {Last}` or `{First} {Middle} {Last}`
  - 70% have middle names
  - Avoid duplicates unless intentional (for testing duplicate detection)

#### 2. **Email Addresses**
- **Format**: `{name_variant}@{domain}`
  - Name variants: firstname.lastname, firstlast, f.lastname, firstname123, etc.
  - Domains: Mix of gmail.com (30%), yahoo.com (15%), outlook.com (15%), custom domains (40%)
  - **MUST BE UNIQUE** - Primary constraint

- **Email Patterns**:
  - 60%: `firstname.lastname@domain.com`
  - 20%: `firstname_lastname@domain.com`
  - 10%: `firstnamelastname@domain.com`
  - 10%: `firstname.lastname+tag@domain.com`

#### 3. **Created At** (Temporal Distribution)
- **Date Range**: 2015-01-01 to 2026-02-21 (11 years)
- **Distribution**: 
  - 2015-2018: 20% (early adopters)
  - 2019-2021: 30% (growth phase)
  - 2022-2024: 35% (peak growth)
  - 2025-2026: 15% (recent customers)

- **Seasonality**: Slight peaks in January (New Year) and September (back to school)
- **Time of Day**: Business hours weighted (9 AM - 5 PM): 70%, Off-hours: 30%

#### 4. **Customer Segments** (for realistic queries)
Create distinct customer personas:
- **VIP Customers**: 5% - High balances (>$100,000), multiple accounts
- **Regular Customers**: 60% - Medium balances ($5,000-$50,000), 1-3 accounts
- **New Customers**: 20% - Low balances (<$5,000), 1 account, recent sign-up
- **Inactive Customers**: 10% - Old sign-up, minimal transactions, low balance
- **Dormant Customers**: 5% - No transactions in last 12 months

---

## 📋 Table 2: ACCOUNTS

### Schema
```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    account_number TEXT NOT NULL UNIQUE,
    balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);
```

### Data Distribution Requirements

#### 1. **Customer-to-Account Ratio**
- **Distribution**:
  - 30% of customers: 1 account
  - 40% of customers: 2 accounts
  - 20% of customers: 3 accounts
  - 7% of customers: 4 accounts
  - 3% of customers: 5+ accounts (up to 10 max)

#### 2. **Account Numbers**
- **Format**: `ACC{CUSTOMER_ID}{SEQUENCE}` or `{BANK_CODE}{RANDOM_10_DIGITS}`
  - Example: `ACC10011`, `BNK1234567890`
  - **MUST BE UNIQUE** - Primary constraint
  
- **Pattern Options**:
  - 50%: Sequential with customer ID prefix
  - 30%: Random 10-digit numbers
  - 20%: Branch code + sequential (e.g., `BR001-000123456`)

#### 3. **Balance Distribution** (Realistic Banking Data)
- **Overall Distribution** (Log-Normal):
  - Median: $8,000
  - Mean: $25,000
  - 10th percentile: $500
  - 90th percentile: $75,000
  - 99th percentile: $500,000

- **By Account Type** (Simulated):
  - **Checking Accounts** (60%): $500 - $50,000
  - **Savings Accounts** (30%): $1,000 - $100,000
  - **Investment Accounts** (10%): $5,000 - $1,000,000

- **Balance Ranges**:
  - $0 - $1,000: 15%
  - $1,001 - $5,000: 25%
  - $5,001 - $20,000: 30%
  - $20,001 - $100,000: 20%
  - $100,001 - $500,000: 8%
  - $500,001+: 2%

#### 4. **Created At**
- **Date Range**: Should be >= customer's created_at
- **Distribution**:
  - 60%: Same day as customer creation (primary account)
  - 30%: Within 1 year of customer creation
  - 10%: 1+ years after customer creation (additional accounts)

#### 5. **Account States** (Implied by balance)
- Active accounts: balance > $100 (85%)
- Low-balance accounts: $0.01 - $100 (10%)
- Zero-balance accounts: $0.00 (5%)

---

## 📋 Table 3: TRANSACTIONS

### Schema
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('credit', 'debit')),
    amount DECIMAL(15, 2) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);
```

### Data Distribution Requirements

#### 1. **Transactions per Account**
- **Distribution** (Poisson/Negative Binomial):
  - 5%: 0-5 transactions (dormant)
  - 15%: 6-20 transactions (low activity)
  - 40%: 21-50 transactions (normal)
  - 25%: 51-100 transactions (active)
  - 10%: 101-200 transactions (very active)
  - 5%: 201+ transactions (power users, up to 1,000)

#### 2. **Transaction Type Distribution**
- **Overall**: 55% Credit, 45% Debit (slightly positive cash flow)
- **By Account Balance**:
  - High balance (>$50k): 60% Credit, 40% Debit
  - Medium balance ($5k-$50k): 55% Credit, 45% Debit
  - Low balance (<$5k): 50% Credit, 50% Debit

#### 3. **Amount Distribution** (Multi-Modal)
- **Micro Transactions** (<$50): 30%
  - Coffee, snacks, parking: $1 - $50
  - Distribution: Exponential with mean $15
  
- **Small Transactions** ($50-$500): 40%
  - Groceries, gas, utilities: $50 - $500
  - Distribution: Log-normal with median $150
  
- **Medium Transactions** ($500-$5,000): 20%
  - Rent, electronics, travel: $500 - $5,000
  - Distribution: Log-normal with median $1,500
  
- **Large Transactions** ($5,000-$50,000): 8%
  - Car, tuition, home improvement: $5,000 - $50,000
  - Distribution: Log-normal with median $15,000
  
- **Very Large Transactions** (>$50,000): 2%
  - Real estate, business: $50,000 - $500,000
  - Distribution: Heavy-tailed

#### 4. **Temporal Patterns** (Realistic Banking Behavior)

**Date Distribution**:
- **Range**: Between account.created_at and 2026-02-21
- **Frequency**: More recent transactions are more common
  - Last 30 days: 15%
  - Last 90 days: 25%
  - Last 6 months: 30%
  - Last 1 year: 20%
  - Older than 1 year: 10%

**Monthly Patterns**:
- Higher activity: January (bills), June (summer), November-December (holidays)
- Lower activity: February, August

**Weekly Patterns**:
- Monday-Friday: 70%
- Saturday-Sunday: 30%

**Daily Patterns** (Time of Day):
- 00:00-06:00: 3% (automated payments, online transactions)
- 06:00-09:00: 10% (morning routine)
- 09:00-12:00: 25% (business hours)
- 12:00-15:00: 20% (lunch, afternoon)
- 15:00-18:00: 22% (evening shopping)
- 18:00-21:00: 15% (dinner, entertainment)
- 21:00-00:00: 5% (late night)

#### 5. **Transaction Coherence** (Balance Validation)
**CRITICAL**: Transactions must result in the current account balance!

- **Method 1** (Forward Generation):
  1. Start with balance = $0
  2. Generate transactions chronologically
  3. Update balance: `balance = balance + credit - debit`
  4. Final balance should match `accounts.balance`

- **Method 2** (Backward Generation):
  1. Start with final balance from `accounts.balance`
  2. Generate transactions in reverse chronological order
  3. Ensure balance never goes negative during reconstruction

- **Validation**:
  ```sql
  -- This should equal accounts.balance for each account_id
  SELECT account_id, 
         SUM(CASE WHEN type='credit' THEN amount ELSE 0 END) - 
         SUM(CASE WHEN type='debit' THEN amount ELSE 0 END) as calculated_balance
  FROM transactions
  GROUP BY account_id;
  ```

#### 6. **Transaction Patterns** (for AI Testing)
Include realistic transaction sequences:

- **Salary Deposits**: Monthly credit of $3,000-$10,000 on 1st or 15th
- **Recurring Bills**: Same amount debits monthly (rent, utilities, subscriptions)
- **ATM Withdrawals**: Round amounts ($20, $40, $60, $100, $200)
- **Online Shopping**: Small-medium debits with irregular patterns
- **Transfers**: Paired transactions (large credit/debit on same day)
- **Refunds**: Small credit 5-30 days after corresponding debit
- **Fraudulent Patterns** (for anomaly detection):
  - Multiple small transactions in quick succession
  - Unusual locations/times
  - Large withdrawals after periods of inactivity

---

## 🔍 Data Quality Requirements

### 1. **Referential Integrity**
- ✅ Every `accounts.customer_id` must exist in `customers.id`
- ✅ Every `transactions.account_id` must exist in `accounts.id`
- ✅ No orphaned records

### 2. **Temporal Consistency**
- ✅ `accounts.created_at` >= `customers.created_at`
- ✅ `transactions.created_at` >= `accounts.created_at`
- ✅ All dates <= 2026-02-21 (current date)

### 3. **Financial Consistency**
- ✅ Account balance = SUM(credits) - SUM(debits)
- ✅ All amounts > 0
- ✅ Balances can be >= 0 (allow overdrafts if realistic)

### 4. **Uniqueness Constraints**
- ✅ `customers.email` - 100% unique
- ✅ `accounts.account_number` - 100% unique
- ✅ No duplicate primary keys

### 5. **Realistic Distributions**
- ✅ No perfectly uniform distributions (use normal, log-normal, Pareto)
- ✅ Include outliers (0.1% extreme values)
- ✅ Include edge cases (0 balances, new accounts, old accounts)

---

## 🧪 Test Query Categories

Your dataset should support these query types:

### 1. **Aggregation Queries**
- Total balance by customer
- Average transaction amount by type
- Monthly transaction volume
- Top 10 customers by balance

### 2. **Filtering Queries**
- Customers with balance > $X
- Transactions in date range
- Accounts created in last N days
- High-value transactions (>$10,000)

### 3. **Join Queries**
- Customer transactions (customers → accounts → transactions)
- Account summary with customer details
- Transaction history for specific customer

### 4. **Analytical Queries**
- Customer lifetime value
- Transaction frequency analysis
- Balance trends over time
- Churn prediction data (inactive accounts)

### 5. **Edge Case Queries**
- Zero-balance accounts
- Accounts with no transactions
- Customers with multiple high-value accounts
- Unusual transaction patterns

---

## 🛠️ Data Generation Tools & Approaches

### Option 1: Python Script with Faker
```python
# Use libraries:
- faker (names, emails, dates)
- numpy/scipy (distributions)
- pandas (data manipulation)
- sqlite3 (database insertion)
```

### Option 2: Dedicated Tools
- **Mockaroo** - Online data generator (up to 1,000 rows free)
- **Databricks** - For very large datasets
- **Apache Spark** - For distributed generation
- **DBeaver Data Generator** - GUI-based tool

### Option 3: SQL-Based Generation
```sql
-- Use WITH RECURSIVE for large datasets
-- SQLite supports this for generating sequences
```

### Option 4: Real Banking Dataset (Anonymized)
- Kaggle banking datasets
- UCI Machine Learning Repository
- Synthesized.io (commercial)

---

## 📁 Recommended Dataset Files

Create these files for testing:

### 1. **Development**
- `banking_dev_1k.db` - 1K customers (Quick testing)
- `banking_dev_10k.db` - 10K customers (Integration tests)

### 2. **Staging**
- `banking_staging_50k.db` - 50K customers (QA testing)
- `banking_staging_100k.db` - 100K customers (Performance baseline)

### 3. **Production Simulation**
- `banking_prod_500k.db` - 500K customers (Load testing)
- `banking_prod_1m.db` - 1M customers (Stress testing)

### 4. **CSV Exports** (for flexibility)
- `customers.csv`
- `accounts.csv`
- `transactions.csv`

---

## 🎯 Success Criteria

Your dataset is ready when:

1. ✅ All foreign keys resolve correctly
2. ✅ All account balances match transaction sums
3. ✅ Date ranges are realistic and consistent
4. ✅ Distributions look natural (plot histograms!)
5. ✅ Query performance is acceptable (<1s for simple queries on 1M records)
6. ✅ Edge cases are represented (zeros, nulls where allowed, extremes)
7. ✅ Data passes validation script (create one!)

---

## 📊 Validation Script Template

```python
import sqlite3

def validate_dataset(db_path):
    conn = sqlite3.connect(db_path)
    
    # Check 1: Referential integrity
    # Check 2: Balance consistency
    # Check 3: Date consistency
    # Check 4: Uniqueness constraints
    # Check 5: Distribution sanity
    
    conn.close()
```

---

## 💡 Pro Tips

1. **Start Small**: Generate 1K customers first, validate thoroughly, then scale up
2. **Use Seeds**: Set random seeds for reproducibility
3. **Profile Performance**: Test query speed at each scale level
4. **Version Control**: Tag each dataset version (v1.0, v2.0)
5. **Compress Large Files**: Use `gzip` for CSVs, `VACUUM` for SQLite
6. **Document Anomalies**: If you add intentional edge cases, document them
7. **Test Incrementally**: Don't generate 1M records in one go - batch it
8. **Monitor Memory**: Large datasets can exhaust RAM during generation
9. **Use Indexes**: Apply the indexes from schema.sql for performance
10. **Backup**: Keep raw CSV files even after loading to DB

---

## 🚀 Next Steps

1. Choose your generation method (Python recommended)
2. Start with 1K customer dataset
3. Validate with sample queries from your AI assistant
4. Scale to 50K, 500K, 1M+ as needed
5. Create benchmark queries for performance testing
6. Document any custom patterns or business rules you add

Good luck with your dataset generation! 🎉
