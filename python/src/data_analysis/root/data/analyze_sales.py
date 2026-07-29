import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from datetime import datetime

# Load data
df = pd.read_csv('/root/data/sales_data.csv')
df['Date'] = pd.to_datetime(df['Date'])

# --- Analysis ---
total_revenue = df['Revenue'].sum()
total_units = df['Units Sold'].sum()
avg_revenue_per_unit = total_revenue / total_units if total_units > 0 else 0
product_summary = df.groupby('Product').agg(
    Total_Units=('Units Sold', 'sum'),
    Total_Revenue=('Revenue', 'sum'),
    Avg_Revenue_Per_Unit=('Revenue', 'mean')
).reset_index()
product_summary['Revenue_Share'] = (product_summary['Total_Revenue'] / total_revenue * 100).round(1)
best_product = product_summary.loc[product_summary['Total_Revenue'].idxmax()]
daily_trend = df.sort_values('Date')

# --- Beautiful Plot ---
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Sales Data Analysis Dashboard', fontsize=18, fontweight='bold', color='#1a1a2e', y=0.98)

colors = ['#e94560', '#0f3460', '#533483', '#16213e', '#e94560']

# 1. Revenue by Product (Bar Chart)
ax1 = axes[0, 0]
bars = ax1.barh(product_summary['Product'], product_summary['Total_Revenue'], 
                color=['#e94560', '#0f3460', '#533483'], edgecolor='white', linewidth=1.5, height=0.5)
for bar, val in zip(bars, product_summary['Total_Revenue']):
    ax1.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2, 
             f'${val:.0f}', va='center', fontweight='bold', fontsize=11)
ax1.set_xlabel('Total Revenue ($)', fontsize=10, fontweight='bold')
ax1.set_title('Revenue by Product', fontsize=13, fontweight='bold', color='#16213e')
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.set_xlim(0, max(product_summary['Total_Revenue']) * 1.3)

# 2. Units Sold by Product (Donut Chart)
ax2 = axes[0, 1]
wedges, texts, autotexts = ax2.pie(product_summary['Total_Units'], 
                                    labels=product_summary['Product'],
                                    autopct='%1.1f%%', startangle=90,
                                    colors=['#e94560', '#0f3460', '#533483'],
                                    wedgeprops=dict(width=0.5, edgecolor='white', linewidth=2))
for autotext in autotexts:
    autotext.set_fontweight('bold')
    autotext.set_fontsize(10)
ax2.set_title('Units Sold Distribution', fontsize=13, fontweight='bold', color='#16213e')

# 3. Daily Revenue Trend (Line + Area)
ax3 = axes[1, 0]
ax3.fill_between(daily_trend['Date'], daily_trend['Revenue'], alpha=0.2, color='#e94560')
ax3.plot(daily_trend['Date'], daily_trend['Revenue'], marker='o', color='#e94560', 
         linewidth=2.5, markersize=7, markerfacecolor='white', markeredgewidth=2, markeredgecolor='#e94560')
for _, row in daily_trend.iterrows():
    ax3.annotate(f"${row['Revenue']:.0f}", (row['Date'], row['Revenue']), 
                 textcoords="offset points", xytext=(0, 12), ha='center', 
                 fontsize=8, fontweight='bold', color='#16213e')
ax3.set_ylabel('Revenue ($)', fontsize=10, fontweight='bold')
ax3.set_title('Daily Revenue Trend', fontsize=13, fontweight='bold', color='#16213e')
ax3.spines['top'].set_visible(False)
ax3.spines['right'].set_visible(False)
plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')

# 4. Revenue Share (Horizontal Bar)
ax4 = axes[1, 1]
bars4 = ax4.barh(product_summary['Product'], product_summary['Revenue_Share'],
                 color=['#533483', '#0f3460', '#e94560'], edgecolor='white', linewidth=1.5, height=0.5)
for bar, val in zip(bars4, product_summary['Revenue_Share']):
    ax4.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
             f'{val:.1f}%', va='center', fontweight='bold', fontsize=11)
ax4.set_xlabel('Revenue Share (%)', fontsize=10, fontweight='bold')
ax4.set_title('Revenue Share by Product', fontsize=13, fontweight='bold', color='#16213e')
ax4.spines['top'].set_visible(False)
ax4.spines['right'].set_visible(False)
ax4.set_xlim(0, max(product_summary['Revenue_Share']) * 1.3)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig('/root/data/sales_analysis_plot.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()

# --- Save Report ---
report = f"""SALES DATA ANALYSIS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*50}

OVERVIEW
--------
Total Revenue:      ${total_revenue:,.2f}
Total Units Sold:   {total_units}
Avg Revenue/Unit:   ${avg_revenue_per_unit:.2f}
Date Range:         {df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}

PRODUCT PERFORMANCE
-------------------
{product_summary.to_string(index=False)}

KEY INSIGHTS
------------
• Best Performing Product: {best_product['Product']} (${best_product['Total_Revenue']:.0f} revenue, {best_product['Total_Units']} units)
• Revenue Leader Share: {best_product['Revenue_Share']}% of total revenue
• Daily Average Revenue: ${total_revenue / len(df):.2f}

FILES GENERATED
---------------
• Plot: /root/data/sales_analysis_plot.png
• Report: /root/data/sales_analysis_report.txt
"""

with open('/root/data/sales_analysis_report.txt', 'w') as f:
    f.write(report)

print(report)
print("✅ Plot saved to /root/data/sales_analysis_plot.png")
print("✅ Report saved to /root/data/sales_analysis_report.txt")
