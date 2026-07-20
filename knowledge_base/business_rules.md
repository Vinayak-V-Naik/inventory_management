# Business Rules and Model Reference

## ABC classification

Materials are ranked by annual spend (annual demand x unit cost), and classified
by cumulative share of total spend:

- **A** — materials within the top 70% of cumulative spend (highest value).
- **B** — the next 20% (up to 90% cumulative).
- **C** — the remaining 10%.

A-class materials get the tightest monitoring, dual sourcing and monthly cycle
counts.

## EOQ (Economic Order Quantity)

    EOQ = sqrt( (2 x annual demand x ordering cost) / holding cost per unit )

where holding cost per unit = unit cost x holding cost percentage. The dynamic
EOQ replaces annual demand with the actual last-12-months consumption when sales
history exists. EOQ is never below the supplier minimum order quantity, and
never below 1.

## Demand forecasting model

- Algorithm: **Ridge regression**, one model per material.
- Features: month index, calendar month, lag-1/lag-2/lag-3 monthly consumption,
  and 3-month rolling average.
- Output: next 3 months of demand (Month +1, +2, +3). Multi-month forecasts feed
  each prediction back as the next lag.
- Materials with fewer than ~6 months of history are not forecast.
- Model quality is tracked per material with R-squared and MAE.

## Lead time prediction model

- Algorithm: **Linear regression** on delivered purchase orders.
- Features: supplier, order quantity, order month, supplier rating, order value,
  promised lead time days.
- Output: predicted actual lead time in days, used for the dynamic safety stock
  and reorder point.

## Stockout risk levels (90-day projection)

The projection simulates stock day by day using forecast consumption:

- **CRITICAL** — projected stockout occurs within the replenishment lead time
  (an order placed today would arrive too late).
- **HIGH** — ROP breach within 15 days.
- **MEDIUM** — ROP breach within 30 days.
- **LOW** — ROP breach later than 30 days but within the 90-day window.
- **SAFE** — no ROP breach projected in 90 days.

**Order-by date** = projected breach date minus the predicted lead time. Orders
placed by this date should arrive before the breach.

## Currency and units

All monetary values are Indian Rupees (INR). Stock quantities use each
material's unit of measure (units, sets, kg).
