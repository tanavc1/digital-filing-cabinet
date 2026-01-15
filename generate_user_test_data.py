
import os
import zipfile
from datetime import datetime

# Define the "Poisoned" and "Clean" Document Content
DOCS = {
    "MSA_HighRisk_VendorA.txt": """
MASTER SERVICES AGREEMENT

This Master Services Agreement ("Agreement") is entered into between Acme Corp ("Customer") and Evil Corp ("Supplier").

1. TERM AND TERMINATION.
This Agreement shall commence on the Effective Date and continue for 5 years.
Change of Control: This Agreement shall automatically terminate upon a Change of Control of Customer. (RISK: HIGH)

2. ASSIGNMENT.
Customer may not assign this Agreement to any Affiliate or third party without the prior written consent of Supplier, which consent may be withheld in Supplier's sole and absolute discretion.

3. LIMITATION OF LIABILITY.
Supplier's total aggregate liability for all claims arising under this Agreement shall not exceed one hundred dollars ($100). (RISK: CRITICAL)

4. NON-COMPETE.
During the Term and for a period of ten (10) years thereafter, Customer agrees not to hire, solicit, or engage any employee of Supplier.

5. GOVERNING LAW.
This Agreement shall be governed by the laws of Antarctica.
""",

    "Lease_Clean_Office.txt": """
COMMERCIAL OFFICE LEASE

This Lease is made between Landlord Inc and Acme Corp.

1. PREMISES.
Suite 100, 123 Main St.

2. TERM.
The Initial Term shall be 36 months containing an option to renew for one additional 36-month period upon 6 months prior written notice.

3. ASSIGNMENT.
Tenant may assign this Lease to a successor entity or Affiliate upon written notice to Landlord, provided such assignee assumes all obligations herein. (Standard)

4. GOVERNING LAW.
State of New York.
""",

    "NDA_Standard_VendorB.txt": """
NON-DISCLOSURE AGREEMENT

1. CONFIDENTIAL INFORMATION.
"Confidential Information" means all non-public information disclosed by one party to the other.

2. OBLIGATIONS.
Recipient shall use Confidential Information solely for the Purpose of evaluating a business relationship.

3. TERM.
The obligations of confidentiality shall survive for 3 years from disclosure.

4. GOVERNING LAW.
State of Delaware.
"""
}

def generate_zip():
    output_filename = "demo_data_pack.zip"
    print(f"Generating {output_filename}...")
    
    with zipfile.ZipFile(output_filename, 'w') as zf:
        for filename, content in DOCS.items():
            # Add file to zip
            zf.writestr(filename, content)
            print(f"  - Added {filename}")
            
    print(f"\\n✅ SUCCESS: {output_filename} created.")
    print(f"Use this ZIP file to test the 'Data Room Import' feature.")

if __name__ == "__main__":
    generate_zip()
