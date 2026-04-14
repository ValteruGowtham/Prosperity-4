# Round 1 Performance Analysis Results

## 📊 Final Result: **-395.44 XIRECS** ❌

### Breakdown by Product:
| Product | PnL | Status |
|---------|-----|--------|
| ASH_COATED_OSMIUM | **+1,296.56** | ✅ Profitable |
| INTARIAN_PEPPER_ROOT | **-1,692.00** | ❌ Major Losses |

### 📈 PnL Curve Analysis (from screenshot):
- **Early game (0-30K)**: Steady climb to +300 XIRECS
- **Mid game (30K-60K)**: Reached peak of ~+430 XIRECS
- **Late game (60K-100K)**: **Catastrophic decline** to -395 XIRECS
- **Pattern**: Classic "give back all profits + more" scenario

### 🔍 Root Cause Analysis:

**INTARIAN_PEPPER_ROOT is the problem:**
- 890 negative PnL events vs 8 positive events
- Price trended from 11,998 → 12,099 (+101 points)
- We lost -1,692 XIRECS on an upward trending product

**What went wrong:**
1. ❌ Our "trend following" strategy is actually **fighting the trend**
2. ❌ We're likely accumulating **short positions** as price goes up
3. ❌ Mark-to-market losses on short position as price rises
4. ❌ Position limit of 40 shorts = massive losses when price runs +100 points

**ASH_COATED_OSMIUM worked well:**
- Mean reversion strategy is correct
- +1,296 XIRECS profit shows tight spread market making works
- 498 positive vs 433 negative events (healthy ratio)

### 💡 What Needs to Fix:

**For INTARIAN_PEPPER_ROOT:**
1. **Detect trend direction properly** - we're going short in uptrend!
2. **Long bias in uptrends** - should be buying, not selling
3. **Wider stops** or **trend-following momentum**
4. **Reduce position size** until strategy works
5. **Consider**: Maybe Pepper is mean-reverting on longer timescales?

**Questions to investigate:**
- Is the trend actually upward or does it reverse?
- Are we placing orders at wrong prices?
- Is the EMA tracking too slow?
- Are we getting adverse selection from informed traders?

### Next Steps:
1. Analyze actual trade execution (when did we buy/sell?)
2. Check position history (were we short during uptrend?)
3. Revise Pepper strategy completely
4. Consider simpler approach: just market make with wider spreads
5. Or: follow trend with LONG bias only
