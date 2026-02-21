# Dataset Tools for Banking Data Assistant

This directory contains tools for generating and validating large-scale datasets for testing the AI Banking Data Assistant.

## 📁 Files

- **`DATASET_REQUIREMENTS.md`** - Comprehensive specification of dataset requirements
- **`DATASET_GENERATION_GUIDE.md`** - Quick reference for different generation methods
- **`generate_dataset.py`** - Python script to generate realistic banking datasets
- **`validate_dataset.py`** - Validation script to check data quality

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install faker numpy pandas
```

### 2. Generate a Dataset

```bash
# Small dataset (1K customers) - for quick testing
python generate_dataset.py --customers 1000 --output banking_1k.db

# Medium dataset (50K customers) - for QA/staging
python generate_dataset.py --customers 50000 --output banking_50k.db

# Large dataset (500K customers) - for production simulation
python generate_dataset.py --customers 500000 --output banking_500k.db

# Custom seed for different variations
python generate_dataset.py --customers 10000 --seed 12345 --output banking_custom.db
```

### 3. Validate the Dataset

```bash
python validate_dataset.py banking_1k.db
```

### 4. Use with Your AI Assistant

```bash
# Update backend configuration to use the new database
# Then start the server
uvicorn backend.main:app --reload
```

## 📊 Dataset Scales

| Scale | Customers | Accounts | Transactions | DB Size | Use Case |
|-------|-----------|----------|--------------|---------|----------|
| Small | 1,000 | ~2,500 | ~50,000 | ~5 MB | Quick testing |
| Medium | 10,000 | ~25,000 | ~500,000 | ~50 MB | Development |
| Large | 50,000 | ~125,000 | ~5M | ~500 MB | QA/Staging |
| XLarge | 500,000 | ~1.25M | ~50M | ~5 GB | Production sim |
| XXLarge | 5,000,000 | ~12.5M | ~500M | ~50 GB | Stress testing |

## 🎯 What Gets Generated

### Customers Table
- Realistic names (diverse, international)
- Unique email addresses
- Creation dates spanning 5 years
- Customer segments (VIP, regular, new, inactive, dormant)

### Accounts Table
- 1-10 accounts per customer (avg 2.5)
- Unique account numbers
- Log-normal balance distribution ($500 - $500,000)
- Account creation dates after customer creation

### Transactions Table
- Poisson distribution of transactions per account (avg 40)
- 55% credits, 45% debits
- Multi-modal amount distribution (micro to very large)
- Realistic temporal patterns (weekday/weekend, business hours)
- **Guaranteed balance consistency** (transactions sum to account balance)

## ✅ Validation Checks

The validation script checks:

1. **Referential Integrity**
   - All account.customer_id references exist
   - All transaction.account_id references exist

2. **Uniqueness Constraints**
   - All emails are unique
   - All account numbers are unique

3. **Temporal Consistency**
   - Accounts created after customers
   - Transactions created after accounts
   - No future-dated records

4. **Financial Consistency**
   - Account balances match transaction sums
   - All amounts are positive
   - No negative balances (unless intentional)

5. **Data Distributions**
   - Balance distributions look realistic
   - Transaction type ratios are reasonable
   - No excessive empty accounts

## 📖 Detailed Documentation

- **Full Requirements**: See `DATASET_REQUIREMENTS.md` for comprehensive specifications
- **Generation Methods**: See `DATASET_GENERATION_GUIDE.md` for alternative approaches
- **Custom Generation**: Modify `generate_dataset.py` to adjust distributions

## 💡 Tips

### Performance
- Use batch size 1000-10000 for optimal speed
- Disable foreign keys during bulk insert
- Create indexes AFTER data load
- VACUUM database after generation

### Quality
- Always validate after generation
- Test with sample queries before scaling up
- Use same random seed for reproducibility
- Keep generated datasets versioned

### Testing
- Start with 1K customers to verify correctness
- Scale gradually: 1K → 10K → 100K → 1M
- Benchmark query performance at each scale
- Document any custom patterns you add

## 🔧 Customization

To customize the data generation:

1. Edit `generate_dataset.py`:
   - Modify `avg_accounts_per_customer` (default: 2.5)
   - Modify `avg_transactions_per_account` (default: 40)
   - Change distribution parameters in `numpy.random.*` calls

2. Adjust date ranges:
   - Change `start_date='-5y'` to different time periods

3. Add custom fields:
   - Extend the schema in `models/schema.sql`
   - Update generation logic accordingly

## 📋 Example Workflow

```bash
# 1. Generate dataset
python generate_dataset.py --customers 10000 --output test_data.db

# 2. Validate
python validate_dataset.py test_data.db

# 3. Test queries (example)
sqlite3 test_data.db <<EOF
SELECT COUNT(*) as total_customers FROM customers;
SELECT COUNT(*) as total_accounts FROM accounts;
SELECT COUNT(*) as total_transactions FROM transactions;
SELECT AVG(balance) as avg_balance FROM accounts;
EOF

# 4. Use with AI assistant
# Update your backend configuration to point to test_data.db
# Start the server and test queries
```

## 🐛 Troubleshooting

### "ImportError: No module named 'faker'"
```bash
pip install faker numpy
```

### "Balance mismatch errors"
- This means transactions don't sum to account balance
- Re-run generation with a fresh database
- Check for concurrent modifications

### "Out of memory"
- Reduce batch size in script
- Generate in smaller chunks
- Use a machine with more RAM

### "Generation is slow"
- Ensure indexes are created AFTER data load
- Use batch inserts (already implemented)
- Disable foreign key checks during insert

### "Unique constraint violation"
- Clear Faker cache: `Faker.seed(new_seed)`
- Increase the pool of unique values
- Check for duplicate detection logic

## 🔗 Integration

### Update Backend Configuration

Edit your backend to use the generated database:

```python
# backend/db.py or backend/config.py
DATABASE_URL = "sqlite:///./banking_10k.db"
```

### Test with AI Assistant

```bash
# Start backend
uvicorn backend.main:app --reload

# Test query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show top 10 customers by total balance"}'
```

## 📊 Benchmarking

Track performance at different scales:

```bash
# Create benchmark script
for size in 1000 10000 50000 100000; do
    echo "Testing with $size customers..."
    python generate_dataset.py --customers $size --output bench_$size.db
    python validate_dataset.py bench_$size.db
    # Run your benchmark queries here
done
```

## 🎉 Success Criteria

Your dataset is production-ready when:

✅ All validation checks pass
✅ Query performance meets requirements
✅ Data distributions look realistic
✅ Edge cases are represented
✅ Balance calculations are 100% accurate
✅ Foreign key relationships are intact

---

**Need help?** Check the detailed requirements in `DATASET_REQUIREMENTS.md` or the generation guide in `DATASET_GENERATION_GUIDE.md`.

Happy dataset generation! 🚀
