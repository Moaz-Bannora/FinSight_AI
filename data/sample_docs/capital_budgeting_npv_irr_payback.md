# Capital Budgeting Notes: NPV, IRR, Payback, and Scenario Analysis

## Purpose

Capital budgeting is the process of deciding whether a long-term project, investment, or asset purchase is financially worthwhile. Common examples include buying equipment, opening a new branch, launching a product, replacing machinery, or investing in software.

## Net Present Value

Net Present Value, or NPV, measures how much value a project creates after discounting future cash flows back to today. The core formula is:

$$NPV = \sum_{t=0}^{n}\frac{CF_t}{(1+r)^t}$$

Where:

- $CF_t$ is the cash flow in period $t$.
- $r$ is the discount rate.
- $t=0$ usually represents the initial investment.
- A positive NPV means the project is expected to create value under the stated assumptions.
- A negative NPV means the project is expected to destroy value under the stated assumptions.

## NPV Example: Equipment Purchase

A company pays USD 10,000 today for equipment. The equipment is expected to generate USD 4,000 per year for three years. The discount rate is 10%.

$$NPV=-10{,}000+\frac{4{,}000}{1.10}+\frac{4{,}000}{1.10^2}+\frac{4{,}000}{1.10^3}$$

The NPV is approximately USD -52.59. This project is almost break-even, but slightly negative under the assumptions.

## NPV Example: Store Expansion

A store expansion costs USD 25,000 today and is expected to generate USD 9,000 per year for four years. The discount rate is 12%.

$$NPV=-25{,}000+\sum_{t=1}^{4}\frac{9{,}000}{(1.12)^t}$$

The NPV is approximately USD 2,336.14. This suggests that the expansion may create value, assuming the cash-flow forecasts are realistic.

## Internal Rate of Return

Internal Rate of Return, or IRR, is the discount rate that makes NPV equal to zero:

$$0 = \sum_{t=0}^{n}\frac{CF_t}{(1+IRR)^t}$$

IRR is useful because it expresses project attractiveness as a percentage return. However, IRR can be misleading when projects have unusual cash-flow patterns, multiple sign changes, or very different project sizes.

## Payback Period

Payback period measures how long it takes for cumulative cash inflows to recover the initial investment. It is easy to understand, but it ignores the time value of money unless discounted payback is used.

Example:

- Initial investment: USD 12,000
- Annual cash inflow: USD 4,000
- Payback period: 3 years

Payback is useful for liquidity and risk screening, but it should not replace NPV.

## Scenario Analysis

Scenario analysis tests how project value changes under different assumptions.

Common scenarios:

- Base case: the expected forecast.
- Optimistic case: higher sales, better margins, or lower costs.
- Pessimistic case: lower demand, delays, or higher expenses.

Scenario analysis helps identify which assumptions matter most.

## Sensitivity Analysis

Sensitivity analysis changes one assumption at a time, such as discount rate, sales volume, price, cost, or terminal value.

If a small change in one assumption causes NPV to move from strongly positive to strongly negative, the project is sensitive to that assumption and should be reviewed carefully.

## Common Mistakes

- Treating NPV as certain instead of assumption-based.
- Ignoring working capital investment.
- Forgetting taxes or maintenance costs.
- Using an unrealistic discount rate.
- Comparing projects only by IRR when project sizes differ.
- Ignoring strategic value, operational risk, and capacity constraints.

## Interpretation Guide

NPV is usually the strongest capital budgeting rule because it estimates value creation in currency units. IRR is useful as a return percentage, payback is useful for liquidity risk, and scenario analysis is useful for understanding uncertainty.
