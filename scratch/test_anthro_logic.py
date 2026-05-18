import sys
import os

# Add backend to path
backend_path = "/media/heathcliff/MyFiles/HAPAG APPROVED BASELINE-20260410T035243Z-3-001/backend"
sys.path.append(backend_path)

from anthro_utils import calculate_anthro_stats

test_cases = [
    {"age": 37, "gender": "GIRL", "weight": 14, "height": 85, "label": "Child < 5y (User's Case)"},
    {"age": 12, "gender": "BOY", "weight": 9.6, "height": 75.6, "label": "1 year old Boy"},
    {"age": 120, "gender": "GIRL", "weight": 32.5, "height": 138.6, "label": "10 year old Girl"},
]

print(f"{'Label':<25} | {'Age':<3} | {'BMI-f':<7} | {'BMI-s':<11} | {'WFA-s':<11} | {'HFA-s':<11}")
print("-" * 80)

for tc in test_cases:
    res = calculate_anthro_stats(tc['age'], tc['gender'], tc['weight'], tc['height'])
    print(f"{tc['label']:<25} | {tc['age']:<3} | {res['bmifa_figure']:<7} | {str(res['bmifa_status']):<11} | {str(res['wfa_status']):<11} | {str(res['hfa_status']):<11}")
