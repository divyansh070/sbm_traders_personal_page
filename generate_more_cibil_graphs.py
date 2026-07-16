import matplotlib.pyplot as plt
import numpy as np
import os

output_dir = "/Users/divyanshverma/.gemini/antigravity-ide/brain/9c11bb68-aeb9-469d-8840-c0c9c64a8ab3"
plt.style.use('dark_background')

# 1. Inactivity Weight V1 Graph
days_inactive = np.linspace(0, 100, 100)
weights = [2.0, 10.0]
plt.figure(figsize=(9, 4.5))
for w in weights:
    scores = np.maximum(100, 1000 - (days_inactive * w))
    plt.plot(days_inactive, scores, label=f'Inactivity Weight = {w}', linewidth=2.5)
plt.title('Dynamic (V1): Score vs. Days Inactive', fontsize=14, color='#00e5ff', fontweight='bold', pad=10)
plt.xlabel('Days Inactive', fontsize=12)
plt.ylabel('V1 Score', fontsize=12)
plt.legend(fontsize=11)
plt.grid(color='#444444', linestyle='--', linewidth=0.5)
plt.axhline(y=400, color='#ff4444', linestyle=':', label='Defaulter Line (400)', linewidth=2)
plt.savefig(os.path.join(output_dir, 'v1_inactivity_impact.png'), bbox_inches='tight', dpi=150, facecolor='#121212')

# 2. Gold Limit V2 Graph (Assumes standard +100 volume boost, average limit 15)
median_delays = np.linspace(0, 20, 100)
gold_limits = [4, 10]
plt.figure(figsize=(9, 4.5))
for gl in gold_limits:
    scores = []
    for d in median_delays:
        if d <= gl:
            base = 600
        elif d <= 15:
            base = 500
        else:
            base = max(300, 400 - (d - 15) * 10)
        scores.append(base + 100) # add +100 standard volume
    plt.plot(median_delays, scores, label=f'Gold Limit = {gl}', linewidth=2.5)
plt.title('Standard (V2): Score vs. Median Delay (Gold Limit Shift)', fontsize=14, color='#00e5ff', fontweight='bold', pad=10)
plt.xlabel('Median Delay (Days)', fontsize=12)
plt.ylabel('V2 Final Score (Standard Volume)', fontsize=12)
plt.legend(fontsize=11)
plt.grid(color='#444444', linestyle='--', linewidth=0.5)
plt.axhline(y=700, color='#ffd700', linestyle=':', label='Gold Class Line (700)', linewidth=2)
plt.savefig(os.path.join(output_dir, 'v2_gold_limit_impact.png'), bbox_inches='tight', dpi=150, facecolor='#121212')

# 3. Average Limit V2 Graph (Assumes standard +100 volume boost, gold limit 4, penalty mult 10)
avg_limits = [15, 30]
median_delays = np.linspace(0, 40, 100)
plt.figure(figsize=(9, 4.5))
for al in avg_limits:
    scores = []
    for d in median_delays:
        if d <= 4:
            base = 600
        elif d <= al:
            base = 500
        else:
            base = max(300, 400 - (d - al) * 10)
        scores.append(base + 100)
    plt.plot(median_delays, scores, label=f'Average Limit = {al}', linewidth=2.5)
plt.title('Standard (V2): Score vs. Median Delay (Avg Limit Shift)', fontsize=14, color='#00e5ff', fontweight='bold', pad=10)
plt.xlabel('Median Delay (Days)', fontsize=12)
plt.ylabel('V2 Final Score (Standard Volume)', fontsize=12)
plt.legend(fontsize=11)
plt.grid(color='#444444', linestyle='--', linewidth=0.5)
plt.axhline(y=600, color='#00cc66', linestyle=':', label='Average Class Line (600)', linewidth=2)
plt.savefig(os.path.join(output_dir, 'v2_avg_limit_impact.png'), bbox_inches='tight', dpi=150, facecolor='#121212')

# 4. Decay Mult V2 Graph
days_inactive = np.linspace(90, 290, 100) # Starts at decay start 90
decay_mults = [0.5, 2.0]
plt.figure(figsize=(9, 4.5))
for m in decay_mults:
    penalties = (days_inactive - 90) * m
    plt.plot(days_inactive, penalties, label=f'Decay Mult = {m}', linewidth=2.5)
plt.title('Standard (V2): Penalty vs. Days Inactive (Ghosting)', fontsize=14, color='#00e5ff', fontweight='bold', pad=10)
plt.xlabel('Days Inactive', fontsize=12)
plt.ylabel('Penalty Points (Subtracted)', fontsize=12)
plt.legend(fontsize=11)
plt.grid(color='#444444', linestyle='--', linewidth=0.5)
plt.savefig(os.path.join(output_dir, 'v2_decay_mult_impact.png'), bbox_inches='tight', dpi=150, facecolor='#121212')

print("Extra graphs generated successfully.")
