import matplotlib.pyplot as plt
import numpy as np
import os

output_dir = "/Users/divyanshverma/.gemini/antigravity-ide/brain/9c11bb68-aeb9-469d-8840-c0c9c64a8ab3"

plt.style.use('dark_background')

# 1. Delay Weight V1 Graph
delays = np.linspace(0, 50, 100)
weights = [10, 20, 40]
plt.figure(figsize=(9, 5))
for w in weights:
    scores = np.maximum(100, 1000 - (delays * w))
    plt.plot(delays, scores, label=f'Delay Weight = {w}', linewidth=2.5)
plt.title('Dynamic (V1): Score vs. Average Delay', fontsize=16, color='#00e5ff', fontweight='bold', pad=15)
plt.xlabel('Average Delay (Days)', fontsize=12, labelpad=10)
plt.ylabel('V1 Score', fontsize=12, labelpad=10)
plt.legend(fontsize=11)
plt.grid(color='#444444', linestyle='--', linewidth=0.5)
plt.axhline(y=400, color='#ff4444', linestyle=':', label='Defaulter Line (400)', linewidth=2)
plt.savefig(os.path.join(output_dir, 'v1_delay_impact.png'), bbox_inches='tight', dpi=150, facecolor='#121212')

# 2. Volume Boost V2 Graph
sales = np.logspace(3, 7, 100) # 1k to 10M
boost_mults = [10, 25, 50]
plt.figure(figsize=(9, 5))
for m in boost_mults:
    bonuses = np.log10(sales) * m
    plt.plot(sales, bonuses, label=f'Volume Boost Mult = {m}', linewidth=2.5)
plt.title('Standard (V2): Bonus Points vs. Total Lifetime Sales', fontsize=16, color='#00e5ff', fontweight='bold', pad=15)
plt.xlabel('Total Sales (₹)', fontsize=12, labelpad=10)
plt.ylabel('V2 Score Bonus Points', fontsize=12, labelpad=10)
plt.xscale('log')
plt.legend(fontsize=11)
plt.grid(color='#444444', linestyle='--', linewidth=0.5)
plt.savefig(os.path.join(output_dir, 'v2_volume_impact.png'), bbox_inches='tight', dpi=150, facecolor='#121212')

# 3. Delay Penalty Mult V2 Graph
excess_delays = np.linspace(0, 60, 100)
penalties_mult = [5.0, 10.0, 20.0]
plt.figure(figsize=(9, 5))
for m in penalties_mult:
    penalties = excess_delays * m
    plt.plot(excess_delays, penalties, label=f'Delay Penalty Mult = {m}', linewidth=2.5)
plt.title('Standard (V2): Penalty Points vs. Excess Median Delay', fontsize=16, color='#00e5ff', fontweight='bold', pad=15)
plt.xlabel('Excess Median Delay (Days past Average Limit)', fontsize=12, labelpad=10)
plt.ylabel('Penalty Points (Subtracted)', fontsize=12, labelpad=10)
plt.legend(fontsize=11)
plt.grid(color='#444444', linestyle='--', linewidth=0.5)
plt.savefig(os.path.join(output_dir, 'v2_penalty_impact.png'), bbox_inches='tight', dpi=150, facecolor='#121212')

print("Graphs generated successfully.")
