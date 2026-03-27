import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os

plt.style.use('seaborn-v0_8-whitegrid')
os.makedirs("images", exist_ok=True)

COLORS = {
    'primary':   '#2E86AB',
    'secondary': '#A8DADC',
    'accent':    '#E63946',
    'neutral':   '#457B9D',
}

df = pd.read_csv("data/job_market.csv")

print("=" * 45)
print("DATA QUALITY REPORT")
print("=" * 45)
print(f"Records loaded     : {len(df)}")
print(f"Columns            : {df.shape[1]}")
print(f"Duplicate rows     : {df.duplicated().sum()}")

print("\nMissing values:")
missing = df.isnull().sum()
missing = missing[missing > 0]
for col, n in missing.items():
    print(f"  {col:<25} {n:>3} missing ({n / len(df):.0%})")

print(f"\nUnique job titles  : {df['job_title'].nunique()}")
print(f"Job type values    : {df['job_type'].dropna().unique().tolist()}")

# DATA CLEANING
df.columns = df.columns.str.strip().str.lower()

# Job type cleaning
df['job_type'] = df['job_type'].astype(str).str.replace('-', ' ').str.strip().str.title()
valid_job_types = ['Full Time', 'Part Time', 'Contract', 'Remote']
df = df[df['job_type'].isin(valid_job_types)]

# Remove non-tech roles
non_tech_keywords = [
    'Mechanic', 'Driver', 'Marketing', 'Hr', 'Restaurant',
    'Social Media', 'Procurement', 'Content', 'Finance',
    'Account Manager'
]

before = len(df)

mask_non_tech = df['job_title'].str.contains('|'.join(non_tech_keywords), case=False, na=False)
removed_df = df[mask_non_tech]
df = df[~mask_non_tech]

print("\nExamples of removed roles:")
print(removed_df['job_title'].head(5).to_string(index=False))

print(f"\nNon-tech roles removed : {before - len(df)}")
print(f"Clean records          : {len(df)}")

# Salary cleaning
df = df.dropna(subset=['salary_min', 'salary_max'])
df['salary_min'] = pd.to_numeric(df['salary_min'], errors='coerce')
df['salary_max'] = pd.to_numeric(df['salary_max'], errors='coerce')
df['salary'] = (df['salary_min'] + df['salary_max']) / 2
df = df.dropna(subset=['salary'])

# Experience cleaning
df['experience_required'] = pd.to_numeric(df['experience_required'], errors='coerce')

def bucket_experience(x):
    if pd.isna(x): return 'Unknown'
    elif x <= 2: return '0-2 years'
    elif x <= 5: return '3-5 years'
    elif x <= 9: return '6-9 years'
    else: return '10+ years'

df['experience_level'] = df['experience_required'].apply(bucket_experience)

# SKILLS NORMALISATION
missing_skills_pct = df['skills'].isna().mean() * 100
print(f"\nMissing skills after filter : {missing_skills_pct:.1f}%")

df['skills'] = df['skills'].fillna('unknown').str.lower().str.strip()

skill_map = {
    'ml': 'machine learning',
    'ai': 'artificial intelligence',
    'js': 'javascript'
}

def normalize_skill(skill):
    skill = skill.strip()
    return skill_map.get(skill, skill)

df['skills_list'] = df['skills'].str.split(',')

skills_df = df.explode('skills_list')
skills_df['skills_list'] = skills_df['skills_list'].apply(normalize_skill)
skills_df['skills_list'] = skills_df['skills_list'].str.strip()
skills_df = skills_df[skills_df['skills_list'] != 'unknown']

# CORE ANALYSIS
top_roles = df['job_title'].value_counts().head(10)
top_skills = skills_df['skills_list'].value_counts().head(15)

salary_by_role = df.groupby('job_title')['salary'].mean().sort_values(ascending=False).head(10)
salary_by_skill = skills_df.groupby('skills_list')['salary'].mean().sort_values(ascending=False).head(10)

exp_order = ['0-2 years', '3-5 years', '6-9 years', '10+ years']
salary_by_exp = (
    df[df['experience_level'] != 'Unknown']
    .groupby('experience_level')['salary']
    .mean()
    .reindex(exp_order)
)

# Sweet spot
top_demand_set = set(top_skills.head(10).index)
top_pay_set = set(salary_by_skill.head(10).index)
sweet_spot = top_demand_set & top_pay_set

# STATISTICAL VALIDATION
salary_stats = df.groupby('job_title')['salary'].agg(['mean', 'std', 'count'])
salary_stats['cv'] = salary_stats['std'] / salary_stats['mean']

print("\nSalary Statistics (Top 10):")
print(salary_stats.sort_values(by='mean', ascending=False).head(10).round(2))

# Outliers
q1 = df['salary'].quantile(0.25)
q3 = df['salary'].quantile(0.75)
iqr = q3 - q1

outliers = df[(df['salary'] < (q1 - 1.5 * iqr)) | (df['salary'] > (q3 + 1.5 * iqr))]
print(f"\nPotential salary outliers: {len(outliers)}")

# LOCATION ANALYSIS
print("\nTop Locations by Job Count:")
print(df['location'].value_counts().head(10))

print("\nTop Locations by Salary:")
print(df.groupby('location')['salary'].mean().sort_values(ascending=False).head(10))

# VISUALISATIONS
def add_bar_labels(ax, fmt='${:,.0f}'):
    for p in ax.patches:
        height = p.get_height()
        ax.text(
            p.get_x() + p.get_width() / 2,
            height,
            fmt.format(height),
            ha='center', va='bottom', fontsize=8
        )

def format_salary_axis(ax):
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f'${x/1000:.0f}K')
    )

# Chart 1: Top Skills
fig, ax = plt.subplots(figsize=(11, 6))
ax.bar(top_skills.index, top_skills.values, color=COLORS['primary'])
ax.set_title("Top Skills")
ax.set_xticklabels(top_skills.index, rotation=40, ha='right')
plt.tight_layout()
plt.savefig("images/top_skills.png")
plt.close()

# Chart 2: Salary by Role
fig, ax = plt.subplots(figsize=(11, 6))
ax.bar(salary_by_role.index, salary_by_role.values, color=COLORS['neutral'])
format_salary_axis(ax)
ax.set_title("Top Paying Roles")
ax.set_xticklabels(salary_by_role.index, rotation=40, ha='right')
plt.tight_layout()
plt.savefig("images/top_salaries_by_role.png")
plt.close()

# Chart 3: Salary by Experience
fig, ax = plt.subplots()
ax.bar(salary_by_exp.index, salary_by_exp.values, color=COLORS['secondary'])
format_salary_axis(ax)
ax.set_title("Salary by Experience")
plt.tight_layout()
plt.savefig("images/salary_by_experience.png")
plt.close()

# Chart 4: Top Paying Skills
fig, ax = plt.subplots(figsize=(11, 6))
ax.bar(salary_by_skill.index, salary_by_skill.values, color=COLORS['accent'])
format_salary_axis(ax)
ax.set_xticklabels(salary_by_skill.index, rotation=40, ha='right')
plt.tight_layout()
plt.savefig("images/top_paying_skills.png")
plt.close()

# 15. CHART 5 — SWEET SPOT
# =========================
 
sweet_skills = sorted(sweet_spot)
sweet_data = pd.DataFrame({
    'demand': [skills_df['skills_list'].value_counts().get(s, 0) for s in sweet_skills],
    'salary': [skills_df.groupby('skills_list')['salary'].mean().get(s, 0) for s in sweet_skills]
}, index=sweet_skills).sort_values('salary', ascending=False)
 
fig, ax1 = plt.subplots(figsize=(9, 5))
ax2 = ax1.twinx()
 
x = range(len(sweet_data))
bars = ax1.bar(x, sweet_data['salary'], color=COLORS['primary'], alpha=0.85,
               edgecolor='white', linewidth=0.8, label='Avg Salary')
ax2.plot(x, sweet_data['demand'], color=COLORS['accent'], marker='o',
         linewidth=2, markersize=8, label='Job Listings')
 
format_salary_axis(ax1)
ax1.set_ylabel("Average Salary (USD)", fontsize=11, color=COLORS['primary'])
ax2.set_ylabel("Number of Job Listings", fontsize=11, color=COLORS['accent'])
ax1.set_xticks(list(x))
ax1.set_xticklabels(sweet_data.index, rotation=20, ha='right', fontsize=11)
ax1.set_title("Sweet Spot Skills — High Demand & High Pay", fontsize=14, fontweight='bold', pad=15)
ax1.set_ylim(0, sweet_data['salary'].max() * 1.2)
ax2.set_ylim(0, sweet_data['demand'].max() * 1.4)
 
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=9)
plt.tight_layout()
plt.savefig("images/sweet_spot_skills.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved: images/sweet_spot_skills.png")
df.to_csv("data/cleaned_job_market.csv", index=False)
