# Procurement Policy

## Supplier selection scoring

When a reorder is triggered, every mapped supplier for the material is scored:

    Total Score = 0.40 x supplier rating
                + 0.30 x price score
                + 0.30 x lead time score

- **Supplier rating** (0 to 1) reflects delivery history and quality.
- **Price score** = 1 − (unit price / highest quoted price among candidates);
  the cheapest supplier scores highest.
- **Lead time score** = 1 − (lead time / longest lead time among candidates);
  the fastest supplier scores highest.

The supplier with the highest total score is recommended. Only suppliers with a
rating of at least **0.60** are eligible; if no supplier passes the threshold,
all mapped suppliers are considered as a fallback.

## Urgency rule for planned orders

For future-dated (planned) orders raised from the 90-day projection:

- If the projected ROP breach is **within the supplier lead time** (the order is
  urgent), pick the **fastest** eligible supplier.
- Otherwise pick the **cheapest** eligible supplier.

## Order quantity

The standard order quantity is the **EOQ** (economic order quantity), never less
than the supplier's minimum order quantity. Do not round EOQ down below the
minimum order quantity.

## Purchase order approval limits

- Orders up to INR 100,000: planner may approve directly.
- Orders from INR 100,000 to INR 500,000: procurement manager approval required.
- Orders above INR 500,000: plant head approval required.
- Emergency (stockout) orders may be approved one level lower than normal but
  must be ratified at the correct level within 3 working days.

## Purchase order lifecycle

Planned → Open → Confirmed → Delivered.
A PO is **overdue** when today is past its expected delivery date and it has not
been delivered. Overdue POs must be chased with the supplier within 24 hours.

## Single-sourcing restriction

A-class materials must have at least two mapped suppliers. Single-sourced
A-class materials are a supply risk and must be flagged to the sourcing team.
