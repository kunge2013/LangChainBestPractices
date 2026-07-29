import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from datetime import datetime

# Load data
df = pd.read_csv("/root/data/sales_data.csv")
df["Date"] = pd.to_datetime(df["Date"])

# ---- Analysis ----
total_revenue = df["Revenue"].sum()
total_units = df["Units Sold"].sum()
avg_revenue_per_sale = df["Revenue"].mean()
best_product = df.groupby("Product")["Revenue"].sum().idxmax()
best_product_rev = df.groupby("Product")["Revenue"].sum().max()
product_breakdown = df.groupby("Product").agg({"Units Sold": "sum", "Revenue": "sum"}).sort_values("Revenue", ascending=False)
daily_trend = df.groupby("Date")[["Units Sold", "Revenue"]].sum()

# ---- Plot ----
fig, axes = plt.subplots(2, 2, figsize=(14, 10), gridspec_kw={"hspace": 0.35, "wspace": 0.3})
fig.suptitle("Sales Dashboard — August 2025", fontsize=18, fontweight="bold", y=0.98)

# Color palette
colors = ["#4C72B0", "#55A868", "#C44E52"]

# 1. Revenue by Product (horizontal bar)
ax = axes[0, 0]
prods = product_breakdown.index.tolist()
revs = product_breakdown["Revenue"].values
bars = ax.barh(prods[::-1], revs[::-1], color=colors[:len(prods)][::-1], edgecolor="white", height=0.5)
for bar, val in zip(bars, revs[::-1]):
    ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height()/2, f"${val:.0f}", va="center", fontsize=11, fontweight="bold")
ax.set_xlabel("Revenue ($)", fontsize=11)
ax.set_title("Revenue by Product", fontsize=13, fontweight="bold")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.xaxis.set_major_formatter(mticker.StrMethodFormatter("${x:,.0f}"))

# 2. Units Sold by Product
ax = axes[0, 1]
units = product_breakdown["Units Sold"].values
bars = ax.bar(prods[::-1], units[::-1], color=colors[:len(prods)][::-1], edgecolor="white", width=0.5)
for bar, val in zip(bars, units[::-1]):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15, f"{int(val)}", ha="center", fontsize=11, fontweight="bold")
ax.set_ylabel("Units Sold", fontsize=11)
ax.set_title("Units Sold by Product", fontsize=13, fontweight="bold")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# 3. Daily Revenue Trend
ax = axes[1, 0]
dates = daily_trend.index
ax.plot(dates, daily_trend["Revenue"], marker="o", linewidth=2.5, color="#4C72B0", markersize=8, zorder=5)
ax.fill_between(dates, daily_trend["Revenue"], alpha=0.15, color="#4C72B0")
ax.set_xlabel("Date", fontsize=11)
ax.set_ylabel("Revenue ($)", fontsize=11)
ax.set_title("Daily Revenue Trend", fontsize=13, fontweight="bold")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%b %d"))
ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:,.0f}"))
for x, y in zip(dates, daily_trend["Revenue"]):
    ax.annotate(f"${y:.0f}", (x, y), textcoords="offset points", xytext=(0, 12), ha="center", fontsize=9)

# 4. Revenue Share (donut)
ax = axes[1, 1]
wedges, texts, autotexts = ax.pie(
    revs[::-1], labels=prods[::-1], autopct="%1.1f%%",
    colors=colors[:len(prods)][::-1], startangle=90,
    wedgeprops={"width": 0.5, "edgecolor": "white", "linewidth": 2},
    textprops={"fontsize": 11}
)
for t in autotexts:
    t.set_fontweight("bold")
    t.set_color("white")
ax.set_title("Revenue Share", fontsize=13, fontweight="bold")

plt.savefig("/root/data/sales_analysis_plot.png", dpi=200, bbox_inches="tight")
plt.close()

# ---- Report ----
report = f"""SALES ANALYSIS REPORT
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
{'='*50}

OVERVIEW
--------
Date Range:     {df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}
Total Revenue:  ${total_revenue:,.2f}
Total Units:    {total_units}
Avg Revenue/Sale: ${avg_revenue_per_sale:,.2f}

PRODUCT BREAKDOWN
-----------------
{product_breakdown.to_string()}

TOP PERFORMER
-------------
{best_product} — ${best_product_rev:,.2f} in revenue

DAILY SALES
-----------
{daily_trend.to_string()}

{'='*50}
End of Report
"""

with open("/root/data/sales_analysis_report.txt", "w") as f:
    f.write(report)

print("Plot saved to /root/data/sales_analysis_plot.png")
print("Report saved to /root/data/sales_analysis_report.txt")
print("\n--- Report Preview ---")
print(report)
