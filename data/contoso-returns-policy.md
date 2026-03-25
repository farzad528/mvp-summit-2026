# Contoso Insurance — Claims and Returns Policy

**Effective Date**: January 1, 2026  
**Policy Version**: 4.2  
**Applies To**: All Contoso Insurance product lines

## 1. General Return Policy

All insured product returns must be initiated within **30 calendar days** of the original purchase date. The purchase date is defined as the date on the original receipt or invoice, not the delivery date.

### 1.1 Required Documentation

Every return claim must include:
- Original receipt or proof of purchase (digital copies accepted)
- Claim form (Form CR-100) completed in full
- Photo documentation of the item condition (minimum 3 photos)
- Serial number verification for electronics over $500

### 1.2 Condition Requirements

Items must be in one of the following conditions:
- **Like New**: Unopened, original packaging intact — full refund eligible
- **Good**: Opened but undamaged, all accessories present — full refund eligible
- **Fair**: Minor cosmetic wear, fully functional — 80% refund eligible
- **Defective**: Manufacturing defect confirmed — full refund plus shipping reimbursement

## 2. Refund Calculations

### 2.1 Standard Refund Windows

| Days Since Purchase | Refund Percentage | Applies To |
|---|---|---|
| 0-14 days | 100% | All conditions |
| 15-30 days | 100% for Like New/Good, 80% for Fair | Non-defective items |
| 31-60 days | 50% store credit only | Requires manager approval |
| 61+ days | No refund | Exception: warranty claims |

### 2.2 Electronics-Specific Rules

Electronics over $500 have additional requirements:
- Must include original charger and cables
- Factory reset must be completed (verified by technician)
- Activation lock must be disabled
- Restocking fee of 15% applies after day 14 unless defective

### 2.3 Defective Item Exceptions

Items confirmed defective by Contoso-certified technician:
- Full refund regardless of time window (up to 1 year from purchase)
- Shipping costs reimbursed
- No restocking fee
- Expedited processing (5 business days vs standard 10)

## 3. Escalation Criteria

Claims must be escalated to a supervisor when ANY of these conditions apply:

- Claim value exceeds **$2,500**
- Customer has filed **3 or more claims** in the past 12 months
- Item is flagged in the **recall database**
- Return reason is "safety concern"
- Customer requests exception to standard policy
- Claim involves **international purchase** (different tax jurisdiction)
- Item is a **bundle or kit** where only partial items are returned

## 4. Fraud Detection Rules

The following patterns trigger automatic fraud review:
- Same serial number claimed by multiple customers
- More than 5 claims from the same address in 90 days
- Claim photo metadata location doesn't match customer address
- Receipt total doesn't match item price in system
- Return initiated within 2 hours of purchase (potential receipt recycling)

## 5. Special Categories

### 5.1 Perishable Goods
- Must be reported within 48 hours of delivery
- Photo evidence of damage or spoilage required
- No return shipping — item should be disposed of safely
- Automatic full refund if reported within window

### 5.2 Custom/Personalized Items
- Non-returnable unless defective
- Defective custom items receive store credit, not refund
- 60-day window for defect reporting on custom items

### 5.3 Subscription Services
- Pro-rated refund based on unused portion
- Must cancel before next billing cycle
- Refund processed within 10 business days
- Annual subscriptions: 30-day satisfaction guarantee for full refund

## 6. Processing Timelines

| Claim Type | Processing Time | Payment Method |
|---|---|---|
| Standard return | 10 business days | Original payment method |
| Defective item | 5 business days | Original payment method |
| Store credit | 2 business days | Contoso credit account |
| International | 15 business days | Wire transfer or original method |
| Escalated claim | 15 business days | Determined by supervisor |

## 7. API Integration Notes

For developers integrating with the Contoso Claims API:
- All claims must be submitted via POST /api/v2/claims
- Authentication: OAuth 2.0 with client credentials
- Rate limit: 100 requests per minute per API key
- Webhook notifications available for status changes
- Sandbox environment: sandbox.contoso-claims.com
