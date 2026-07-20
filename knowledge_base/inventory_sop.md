# Inventory Standard Operating Procedure (SOP)

## Stock status definitions

Every material is classified into exactly one status, checked in this order:

- **STOCKOUT** — current stock is zero. Production is at immediate risk.
- **CRITICAL** — current stock is at or below safety stock. Escalate to the
  procurement manager the same day.
- **REORDER** — current stock is at or below the reorder point (ROP). A purchase
  order should be raised unless one is already open.
- **OVERSTOCK** — current stock is at or above 2.5 times the reorder point.
  Review for excess working capital; pause further ordering.
- **NORMAL** — stock is between the reorder point and the overstock threshold.

## Safety stock policy

Safety stock is calculated as:

    Safety Stock = 1.65 x demand standard deviation x sqrt(lead time in days)

The z-score of 1.65 corresponds to a **95% service level** — the company accepts
a 5% probability of stockout during the replenishment lead time. Demand standard
deviation is estimated as 25% of average daily demand (sigma factor 0.25).

## Reorder point policy

    Reorder Point (ROP) = (average daily demand x lead time in days) + safety stock

When ML models are available, the lead time used is the **predicted** lead time
from the lead-time regression model rather than the supplier's nominal lead time,
and average daily demand comes from the demand forecast model. This is called the
dynamic ROP. If models are unavailable the static formula (annual demand / 365,
nominal lead time) applies.

## Reorder procedure

1. A reorder is triggered when current stock falls to or below the ROP **and**
   there is no open purchase order for the material.
2. The system recommends the best supplier and an order quantity equal to the
   economic order quantity (EOQ).
3. Planners review the recommendation on the Procurement Plan page and raise a
   Planned PO. A Planned PO becomes Open once approved, then Confirmed by the
   supplier, then Delivered on receipt.
4. If stock is CRITICAL and the recommended supplier's lead time is longer than
   the days of stock remaining, choose the fastest supplier instead of the
   cheapest and flag the order as urgent.

## Cycle counting

- A-class materials: count monthly.
- B-class materials: count quarterly.
- C-class materials: count twice a year.
Discrepancies above 2% of book stock must be investigated before adjusting.

## Data recency

All rolling analytics (consumption, EOQ, forecasts) use the most recent
**12 months** of history. Older history is kept for reference but excluded
from planning calculations.
