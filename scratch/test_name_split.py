import sys
import os

# Add backend to path to import functions if possible, or just redefine for testing
def split_beneficiary_name(raw_name):
    """
    Splits a full name string into (lastname, firstname, middlename).
    Supports:
    - 'AQUINO, ALTHEA Y.'
    - 'ALTHEA Y AQUINO'
    """
    raw_name = str(raw_name).strip()
    if not raw_name: return "", "", ""
    
    if ',' in raw_name:
        # Format: Lastname, Firstname [Middlename]
        parts = raw_name.split(',', 1)
        lastname = parts[0].strip().upper()
        first_and_middle = parts[1].strip() if len(parts) > 1 else ""
        fn_parts = first_and_middle.split()
        if len(fn_parts) > 1:
            middlename = fn_parts[-1].upper()
            firstname = ' '.join(fn_parts[:-1]).upper()
        else:
            firstname = first_and_middle.upper()
            middlename = ""
        return lastname, firstname, middlename
    else:
        # Format: [First] [Middle] [Last] (No comma)
        parts = raw_name.split()
        if len(parts) >= 3:
            lastname = parts[-1].upper()
            middlename = parts[-2].upper()
            firstname = ' '.join(parts[:-2]).upper()
            return lastname, firstname, middlename
        elif len(parts) == 2:
            return parts[1].upper(), parts[0].upper(), ""
        else:
            return parts[0].upper(), "", ""

test_cases = [
    "AQUINO, ALTHEA Y.",
    "ALTHEA Y AQUINO",
    "ALTHEA AQUINO",
    "ALTHEA Y. AQUINO",
    "MARIA CORAZON DE LA CRUZ",
    "DE LA CRUZ, MARIA CORAZON",
    "JUAN",
]

print(f"{'Input':<30} | {'Lastname':<15} | {'Firstname':<20} | {'Middlename':<10}")
print("-" * 85)
for tc in test_cases:
    ln, fn, mn = split_beneficiary_name(tc)
    print(f"{tc:<30} | {ln:<15} | {fn:<20} | {mn:<10}")
