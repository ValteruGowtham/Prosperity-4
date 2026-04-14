# Prosperity 4 - Round 1 Trading Algorithm

## 📊 **Best Performance: +1,296 XIRECS (v2.0)**

---

## 📁 **Project Structure**

```
Prosperity 4/
│
├── 📖 README.md                          # This file - project overview
│
├── 🤖 algorithms/                        # Trading algorithm implementations
│   ├── round1_trader.py                  # v1.0 - Original (FAILED: -395 XIRECS)
│   ├── round1_trader_v2.py               # v2.0 - Osmium only ✅ (BEST: +1,296 XIRECS)
│   └── round1_trader_v3.py               # v3.0 - Both products (MIXED: +741 XIRECS)
│
├── 🧪 tests/                             # Test suites for algorithms
│   ├── test_round1_trader.py             # Tests for v1.0
│   ├── test_v2.py                        # Tests for v2.0
│   └── test_v3.py                        # Tests for v3.0
│
├── 🔍 analysis/                          # Data analysis scripts
│   ├── analyze_round1_data.py            # Initial Round 1 data exploration
│   ├── analyze_round1_corrected.py       # Corrected statistical analysis
│   ├── analyze_performance.py            # Performance breakdown (v1.0)
│   ├── deep_analysis.py                  # Deep dive into v1.0 failure
│   ├── final_diagnosis.py                # Root cause identification
│   ├── analyze_pepper_deep.py            # Pepper behavioral analysis
│   ├── pepper_forensic.py                # Forensic analysis of v3.0 Pepper
│   ├── pepper_smoking_gun.py             # Smoking gun: adverse selection
│   └── analyze_v3.py                     # v3.0 performance analysis
│
├──  docs/                              # Documentation & reports
│   ├── notes.md                          # Platform rules & guidelines
│   ├── ROUND1_README.md                  # v1.0 strategy documentation
│   ├── ROUND1_V2_FIX.md                  # v2.0 fix documentation
│   ├── ROUND1_V3_STRATEGY.md             # v3.0 strategy documentation
│   ├── PERFORMANCE_ANALYSIS.md           # v1.0 performance breakdown
│   └── PEPPER_ANALYSIS_COMPLETE.md       # Complete Pepper analysis
│
├── 📈 round1/                            # Round 1 data & results
│   ├── ROUND1/                           # Historical market data
│   │   ├── prices_round_1_day_-2.csv
│   │   ├── prices_round_1_day_-1.csv
│   │   ├── prices_round_1_day_0.csv
│   │   ├── trades_round_1_day_-2.csv
│   │   ├── trades_round_1_day_-1.csv
│   │   └── trades_round_1_day_0.csv
│   ├── 119569.json                       # v1.0 results (-395 XIRECS)
│   ├── 119569.log                        # v1.0 detailed logs
│   ├── 121250.json                       # v2.0 results (+1,296 XIRECS)
│   ├── 121250.log                        # v2.0 detailed logs
│   ├── 123540.json                       # v3.0 results (+741 XIRECS)
│   ├── 123540.log                        # v3.0 detailed logs
│   ├── img.png                           # v1.0 PnL chart
│   ├── img2.png                          # v2.0 PnL chart
│   └── img3.png                          # v3.0 PnL chart
│
└── Tutorial round/                       # Tutorial round materials
    ├── README.md                         # Tutorial strategy docs
    ├── trader.py                         # Tutorial round algorithm
    ├── Data Sets/                        # Tutorial historical data
    └── Performance Analysis/             # Tutorial performance charts
```

---

## 🎯 **Quick Start**

### **For Competition: Use v2.0**

```bash
# Upload this file to Prosperity platform
algorithms/round1_trader_v2.py
```

**Expected Result:** +1,296 XIRECS ✅

### **Run Tests Locally**

```bash
# Test v2.0 algorithm
python3 tests/test_v2.py

# Test v3.0 algorithm
python3 tests/test_v3.py
```

### **Analyze Performance**

```bash
# Analyze Round 1 data
python3 analysis/analyze_round1_corrected.py

# Analyze Pepper behavior
python3 analysis/pepper_smoking_gun.py

# Analyze v3.0 results
python3 analysis/analyze_v3.py
```

---

## 📊 **Version Performance Summary**

| Version | File | Strategy | Osmium | Pepper | **Total** | Status |
|---------|------|----------|--------|--------|-----------|--------|
| **v1.0** | `algorithms/round1_trader.py` | Both products (mean-reversion) | +1,296 | -1,692 | **-395** ❌ | Failed |
| **v2.0** | `algorithms/round1_trader_v2.py` | Osmium only | +1,296 | 0 | **+1,296** ✅ | **BEST** |
| **v3.0** | `algorithms/round1_trader_v3.py` | Both (conservative) | +1,297 | -556 | **+741** ⚠️ | Mixed |

---

## 🔑 **Key Learnings**

### **ASH_COATED_OSMIUM: Easy Profit** ✅
- Mean-reversion market making works perfectly
- Tight spreads (4 points half-spread)
- Large orders (10 units)
- **Result: +1,296 XIRECS consistently**

### **INTARIAN_PEPPER_ROOT: Unwinnable** ❌
- 99.4% adverse selection rate (bots have information)
- Steady upward trend (+0.08% per 100 ticks)
- Bots asymmetrically trade against us
- **Result: Always loses money (-556 to -1,692)**

### **Critical Insight**
```
Market making fails on trending assets with informed counterparties.
Bots know the trend direction and selectively trade against us.
```

---

## 📚 **Documentation Guide**

### **Start Here:**
1. `docs/notes.md` - Platform rules and guidelines
2. `docs/ROUND1_V2_FIX.md` - Why v2.0 works

### **Understanding the Failure:**
3. `docs/PERFORMANCE_ANALYSIS.md` - v1.0 breakdown
4. `docs/PEPPER_ANALYSIS_COMPLETE.md` - Complete Pepper analysis

### **Algorithm Details:**
5. `docs/ROUND1_README.md` - v1.0 strategy
6. `docs/ROUND1_V3_STRATEGY.md` - v3.0 strategy

---

## 🚀 **Next Steps**

1. ✅ **Upload v2.0** to Prosperity platform
2. ✅ **Monitor results** (should be ~+1,296 XIRECS)
3. ⚠️ **Don't trade Pepper** - it's unwinnable
4. 💡 **Focus on optimizing Osmium** if needed

---

## 📞 **Support**

For questions about the algorithm or analysis:
- Check `docs/` folder for detailed explanations
- Run analysis scripts in `analysis/` to reproduce findings
- Review test files in `tests/` for algorithm behavior

---

**Last Updated:** April 2026  
**Best Version:** v2.0 (`algorithms/round1_trader_v2.py`)  
**Expected PnL:** +1,296 XIRECS ✅
