#!/usr/bin/env python3
"""
Generate Realistic M&A Test Data Room
=====================================

Creates a simulated Data Room for the fictional acquisition:
"TechCorp Inc. acquires DataFlow Systems" - $50M deal

This generates 50+ realistic legal documents with embedded risk items
that the AI should detect during due diligence.

Usage:
    python scripts/generate_test_dataroom.py
    
Output:
    - test_data/DataFlow_Acquisition/ (folder structure)
    - test_data/DataFlow_Acquisition.zip (zipped for upload)
"""

import os
import zipfile
from datetime import datetime, timedelta
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "test_data", "DataFlow_Acquisition")

# ============================================================================
# DOCUMENT TEMPLATES
# ============================================================================

CERTIFICATE_OF_INCORPORATION = """
CERTIFICATE OF INCORPORATION
OF
DATAFLOW SYSTEMS, INC.

FIRST: The name of the corporation is DataFlow Systems, Inc.

SECOND: The address of the registered office of the corporation in the State of Delaware is 1209 Orange Street, Wilmington, Delaware 19801. The name of its registered agent at such address is The Corporation Trust Company.

THIRD: The purpose of the corporation is to engage in any lawful act or activity for which corporations may be organized under the General Corporation Law of Delaware.

FOURTH: The total number of shares of stock which the corporation shall have authority to issue is:
(a) 100,000,000 shares of Common Stock, par value $0.001 per share
(b) 10,000,000 shares of Preferred Stock, par value $0.001 per share

FIFTH: The Board of Directors is expressly authorized to provide for the issuance of all or any shares of the Preferred Stock in one or more classes or series, and to fix for each such class or series such voting powers, designations, preferences and relative, participating, optional or other special rights.

IN WITNESS WHEREOF, the undersigned has executed this Certificate of Incorporation on January 15, 2018.

/s/ Michael Chen
Michael Chen, Incorporator
"""

BYLAWS = """
BYLAWS OF DATAFLOW SYSTEMS, INC.
A Delaware Corporation

ARTICLE I - OFFICES
Section 1.1. The registered office of the corporation shall be at 1209 Orange Street, Wilmington, Delaware 19801.
Section 1.2. The corporation may also have offices at such other places as the Board of Directors may from time to time determine.

ARTICLE II - STOCKHOLDERS
Section 2.1. ANNUAL MEETING. The annual meeting of stockholders shall be held on the third Tuesday of March each year at 10:00 a.m.
Section 2.2. SPECIAL MEETINGS. Special meetings of the stockholders may be called by the Board of Directors, the Chairman, or the President.
Section 2.3. QUORUM. A majority of the outstanding shares entitled to vote shall constitute a quorum.

ARTICLE III - DIRECTORS
Section 3.1. NUMBER. The Board of Directors shall consist of not less than three (3) nor more than nine (9) directors.
Section 3.2. ELECTION. Directors shall be elected at the annual meeting of stockholders.
Section 3.3. TERM. Each director shall hold office until the next annual meeting.

ARTICLE IV - OFFICERS
Section 4.1. The officers of the corporation shall be a President, a Secretary, and a Treasurer.
Section 4.2. PRESIDENT. The President shall be the chief executive officer of the corporation.

ARTICLE V - INDEMNIFICATION
Section 5.1. The corporation shall indemnify its directors and officers to the fullest extent permitted by Delaware law.

Adopted: January 15, 2018
Last Amended: March 15, 2023
"""

BOARD_RESOLUTION_2023 = """
UNANIMOUS WRITTEN CONSENT OF THE BOARD OF DIRECTORS
OF DATAFLOW SYSTEMS, INC.

Date: December 15, 2023

The undersigned, being all of the members of the Board of Directors of DataFlow Systems, Inc. (the "Company"), hereby consent to the adoption of the following resolutions:

APPROVAL OF 2024 OPERATING BUDGET

RESOLVED, that the 2024 Operating Budget, as presented to this Board, providing for total operating expenses of $12,500,000 and projected revenue of $18,000,000, is hereby approved.

EXTENSION OF CREDIT FACILITY

RESOLVED, that the officers of the Company are authorized to negotiate and execute an extension of the Company's existing credit facility with Silicon Valley Bank for an additional two (2) years on substantially the same terms.

APPROVAL OF EQUITY INCENTIVE PLAN REFRESH

RESOLVED, that the Company's 2018 Equity Incentive Plan is hereby amended to increase the share reserve by 2,000,000 shares of Common Stock.

AUTHORIZATION OF POTENTIAL STRATEGIC TRANSACTION

RESOLVED, that the officers of the Company are authorized to engage in preliminary discussions regarding potential strategic transactions, including but not limited to mergers, acquisitions, or strategic partnerships, and to retain advisors as necessary.

/s/ Michael Chen          /s/ Sarah Johnson          /s/ Robert Williams
Michael Chen, Chairman    Sarah Johnson, Director    Robert Williams, Director

/s/ Jennifer Lee          /s/ David Park
Jennifer Lee, Director    David Park, Director
"""

# HIGH RISK - Change of Control
CEO_EMPLOYMENT_AGREEMENT = """
EXECUTIVE EMPLOYMENT AGREEMENT

This Executive Employment Agreement ("Agreement") is entered into as of January 1, 2022, by and between DataFlow Systems, Inc., a Delaware corporation (the "Company"), and Michael Chen ("Executive").

1. POSITION AND DUTIES
Executive shall serve as Chief Executive Officer of the Company, reporting directly to the Board of Directors.

2. COMPENSATION
2.1 Base Salary: $450,000 per annum, payable in accordance with the Company's standard payroll practices.
2.2 Annual Bonus: Target bonus of 75% of Base Salary, based on achievement of performance objectives.
2.3 Equity: Executive has been granted options to purchase 2,000,000 shares of Common Stock.

3. BENEFITS
Executive shall be entitled to participate in all employee benefit plans and programs generally available to senior executives.

4. TERMINATION
4.1 For Cause: The Company may terminate Executive's employment for Cause as defined herein.
4.2 Without Cause: The Company may terminate Executive's employment without Cause upon 30 days' notice.
4.3 Resignation: Executive may resign upon 60 days' prior written notice.

5. SEVERANCE

5.1 Termination Without Cause: If Executive's employment is terminated by the Company without Cause, Executive shall receive:
(a) 12 months of Base Salary continuation
(b) Pro-rated annual bonus
(c) 12 months of COBRA premium payments
(d) Acceleration of 25% of unvested equity

***** CHANGE OF CONTROL PROVISION *****

5.2 CHANGE OF CONTROL: In the event of a Change of Control (as defined below), the following shall apply:

(a) DOUBLE TRIGGER ACCELERATION: If, within 12 months following a Change of Control, Executive's employment is terminated without Cause or Executive resigns for Good Reason, then:
    (i) 100% of Executive's unvested equity awards shall immediately vest and become exercisable
    (ii) Executive shall receive a lump-sum payment equal to 24 months of Base Salary
    (iii) Executive shall receive the full target annual bonus for the year of termination
    (iv) Executive shall receive 24 months of COBRA premium payments

(b) DEFINITION: "Change of Control" means:
    (i) The acquisition by any person of 50% or more of the voting power of the Company
    (ii) A merger or consolidation where existing stockholders own less than 50% of the surviving entity
    (iii) The sale of all or substantially all of the Company's assets

***** END CHANGE OF CONTROL PROVISION *****

6. CONFIDENTIALITY
Executive agrees to maintain the confidentiality of all proprietary information of the Company.

7. NON-COMPETITION
For a period of 12 months following termination, Executive shall not compete with the Company.

8. GOVERNING LAW
This Agreement shall be governed by the laws of the State of California.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.

DATAFLOW SYSTEMS, INC.                    EXECUTIVE

By: /s/ Sarah Johnson                     /s/ Michael Chen
Name: Sarah Johnson                       Michael Chen
Title: Chair, Compensation Committee
"""

CTO_EMPLOYMENT_AGREEMENT = """
EXECUTIVE EMPLOYMENT AGREEMENT

This Executive Employment Agreement ("Agreement") is entered into as of March 15, 2020, by and between DataFlow Systems, Inc., a Delaware corporation (the "Company"), and Dr. Emily Watson ("Executive").

1. POSITION AND DUTIES
Executive shall serve as Chief Technology Officer of the Company, reporting to the Chief Executive Officer.

2. COMPENSATION
2.1 Base Salary: $380,000 per annum
2.2 Annual Bonus: Target bonus of 50% of Base Salary
2.3 Equity: Executive has been granted options to purchase 800,000 shares of Common Stock

3. TERMINATION AND SEVERANCE

3.1 Without Cause: 9 months salary continuation and acceleration of 50% of unvested equity.

***** CHANGE OF CONTROL PROVISION *****

3.2 CHANGE OF CONTROL ACCELERATION: Upon a Change of Control:
    (a) SINGLE TRIGGER: 50% of unvested equity immediately vests
    (b) DOUBLE TRIGGER: If terminated within 12 months post-Change of Control:
        - Remaining 50% of equity vests
        - 12 months salary continuation
        - 100% of target bonus

***** END CHANGE OF CONTROL PROVISION *****

4. INTELLECTUAL PROPERTY
All inventions and developments made by Executive during employment shall be the sole property of the Company.

5. NON-SOLICITATION
For 12 months following termination, Executive shall not solicit Company employees.

DATAFLOW SYSTEMS, INC.                    EXECUTIVE

By: /s/ Michael Chen                      /s/ Emily Watson  
Name: Michael Chen                        Dr. Emily Watson
Title: CEO
"""

STANDARD_OFFER_LETTER = """
OFFER LETTER

Date: [Variable]

Dear [Candidate Name],

DataFlow Systems, Inc. is pleased to offer you the position of [Title] in our [Department] team, reporting to [Manager].

COMPENSATION:
- Base Salary: $[Salary] per year, paid bi-weekly
- Annual Bonus: Target of [Bonus]% of base salary, based on company and individual performance
- Equity: [Shares] stock options, vesting over 4 years with a 1-year cliff

START DATE: [Start Date]

BENEFITS:
- Medical, dental, and vision insurance (Company pays 90% of premiums)
- 401(k) plan with 4% company match
- Unlimited PTO policy
- $2,500 annual learning & development budget

EMPLOYMENT AT-WILL:
Your employment with the Company is at-will, meaning either you or the Company may terminate the employment relationship at any time, with or without cause.

To accept this offer, please sign below and return by [Accept Date].

Sincerely,

/s/ HR Team
DataFlow Systems, Inc.

ACCEPTED:

_________________________     _____________
Signature                     Date
"""

EMPLOYEE_HANDBOOK = """
DATAFLOW SYSTEMS, INC.
EMPLOYEE HANDBOOK
Effective Date: January 1, 2024

TABLE OF CONTENTS
1. Welcome
2. Employment Policies
3. Code of Conduct
4. Benefits
5. Leave Policies
6. Remote Work
7. Confidentiality

1. WELCOME
Welcome to DataFlow Systems! We're excited to have you join our team. This handbook outlines our policies and your responsibilities as an employee.

2. EMPLOYMENT POLICIES
2.1 Equal Opportunity: DataFlow is an equal opportunity employer. We do not discriminate based on race, color, religion, sex, national origin, age, disability, or any other protected characteristic.

2.2 At-Will Employment: Employment at DataFlow is at-will unless otherwise specified in a written employment agreement.

2.3 Background Checks: All offers of employment are contingent upon successful completion of a background check.

3. CODE OF CONDUCT
3.1 Professional Behavior: Employees are expected to conduct themselves professionally at all times.

3.2 Harassment Policy: DataFlow maintains a zero-tolerance policy for harassment of any kind.

4. BENEFITS
4.1 Health Insurance: Comprehensive medical, dental, and vision coverage.
4.2 401(k): Company matches up to 4% of salary.
4.3 Equity: Eligible employees may participate in the stock option plan.

5. LEAVE POLICIES
5.1 Unlimited PTO: We trust employees to manage their time responsibly.
5.2 Parental Leave: 16 weeks paid leave for primary caregivers, 8 weeks for secondary.
5.3 Sick Leave: Employees should take time off when ill.

6. REMOTE WORK
6.1 Hybrid Policy: Employees are expected to be in-office at least 2 days per week.
6.2 Equipment: The Company provides necessary equipment for remote work.

7. CONFIDENTIALITY
7.1 Proprietary Information: Employees must protect company trade secrets and confidential information.
7.2 NDA: All employees are required to sign a Confidentiality and Invention Assignment Agreement.

Version 4.2 - January 2024
"""

# MEDIUM RISK - Assignment Clause
OFFICE_LEASE_SF = """
COMMERCIAL LEASE AGREEMENT

This Lease Agreement ("Lease") is made effective as of April 1, 2021, by and between:

LANDLORD: Embarcadero Properties LLC
TENANT: DataFlow Systems, Inc.

PREMISES: Suite 400, 100 California Street, San Francisco, CA 94111
SQUARE FOOTAGE: 15,000 rentable square feet

1. TERM
The initial term of this Lease shall be five (5) years, commencing on April 1, 2021 and expiring on March 31, 2026.

2. BASE RENT
Monthly Base Rent: $112,500.00 ($90.00 per square foot per year)
Annual Escalation: 3% per year

Year 1: $112,500/month
Year 2: $115,875/month
Year 3: $119,351/month
Year 4: $122,932/month
Year 5: $126,620/month

3. SECURITY DEPOSIT
Tenant shall deposit $337,500.00 (three months' rent) as security.

4. PERMITTED USE
The Premises shall be used solely for general office purposes, including software development, administration, and related technology business activities.

5. OPERATING EXPENSES
Tenant shall pay its proportionate share (12.5%) of Building Operating Expenses in excess of the Base Year (2021).

***** ASSIGNMENT AND SUBLETTING CLAUSE *****

6. ASSIGNMENT AND SUBLETTING

6.1 LANDLORD CONSENT REQUIRED: Tenant shall not assign this Lease or sublet the Premises or any portion thereof without the prior written consent of Landlord, which consent shall not be unreasonably withheld.

6.2 CHANGE OF CONTROL: A change of control of Tenant (including a merger, consolidation, or transfer of 50% or more of Tenant's ownership interests) shall be deemed an assignment requiring Landlord's consent.

6.3 CONDITIONS: As a condition to any permitted assignment:
    (a) Tenant shall remain primarily liable under this Lease
    (b) Assignee must demonstrate financial capability
    (c) Landlord may require a lease amendment increasing rent to market rates
    (d) Tenant shall pay Landlord's reasonable attorneys' fees (up to $5,000)

6.4 RECAPTURE RIGHT: Landlord may, within 30 days of receiving an assignment request, elect to terminate this Lease and recapture the Premises.

***** END ASSIGNMENT CLAUSE *****

7. MAINTENANCE
Landlord shall maintain the Building structure, common areas, and HVAC systems.
Tenant shall maintain the interior of the Premises.

8. INSURANCE
Tenant shall maintain commercial general liability insurance of at least $2,000,000 per occurrence.

9. DEFAULT
Tenant shall be in default if rent is not paid within 10 days of due date or if Tenant fails to cure other breaches within 30 days of notice.

10. GOVERNING LAW
This Lease shall be governed by California law.

LANDLORD:                              TENANT:
Embarcadero Properties LLC             DataFlow Systems, Inc.

By: /s/ James Morrison                 By: /s/ Michael Chen
Name: James Morrison                   Name: Michael Chen
Title: Managing Partner                Title: CEO
Date: March 15, 2021                   Date: March 15, 2021
"""

OFFICE_LEASE_NYC = """
COMMERCIAL LEASE AGREEMENT

LANDLORD: Hudson Yards Development LLC
TENANT: DataFlow Systems, Inc.

PREMISES: Suite 2500, 10 Hudson Yards, New York, NY 10001
SQUARE FOOTAGE: 5,000 rentable square feet

TERM: 3 years (January 1, 2023 - December 31, 2025)

MONTHLY RENT: $50,000.00 ($120.00 per square foot per year)

This Lease is a standard commercial lease for satellite office space. No unusual provisions.

Assignment requires Landlord consent, not to be unreasonably withheld.

LANDLORD:                              TENANT:
Hudson Yards Development LLC           DataFlow Systems, Inc.

By: /s/ Legal Department               By: /s/ Michael Chen
Date: December 1, 2022                 Date: December 1, 2022
"""

# Customer Agreements
ACME_MSA = """
MASTER SERVICES AGREEMENT

This Master Services Agreement ("Agreement") is entered into as of June 1, 2022, by and between:

PROVIDER: DataFlow Systems, Inc. ("DataFlow")
CUSTOMER: Acme Corporation ("Customer")

1. SERVICES
DataFlow shall provide Customer with access to its data analytics platform ("Platform") and related professional services as described in Order Forms executed hereunder.

2. TERM
This Agreement shall have an initial term of three (3) years, commencing on the Effective Date.

3. FEES
3.1 Subscription Fees: Customer shall pay subscription fees as set forth in each Order Form.
3.2 Current Order: $250,000 per year for Enterprise License (100 users)
3.3 Payment Terms: Net 30 from invoice date.

4. SERVICE LEVELS
4.1 Uptime: DataFlow guarantees 99.9% uptime, excluding scheduled maintenance.
4.2 Support: 24/7 email support; 8-hour response time for critical issues.

5. DATA SECURITY
5.1 DataFlow maintains SOC 2 Type II certification.
5.2 All Customer data is encrypted at rest and in transit.
5.3 DataFlow will not access Customer data except as necessary to provide the Services.

6. INTELLECTUAL PROPERTY
6.1 DataFlow retains all rights to the Platform.
6.2 Customer retains all rights to Customer Data.

7. CONFIDENTIALITY
Each party shall maintain the confidentiality of the other party's Confidential Information.

8. LIMITATION OF LIABILITY
DATAFLOW'S TOTAL LIABILITY SHALL NOT EXCEED THE FEES PAID BY CUSTOMER IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM.

9. TERMINATION
9.1 Either party may terminate for material breach upon 30 days' written notice if the breach is not cured.
9.2 Customer may terminate for convenience upon 90 days' notice, subject to payment of remaining fees for the current year.

10. AUTO-RENEWAL
This Agreement shall automatically renew for successive one-year periods unless either party provides 60 days' written notice of non-renewal.

DATAFLOW SYSTEMS, INC.              ACME CORPORATION

By: /s/ Michael Chen                By: /s/ Jane Smith
Name: Michael Chen                  Name: Jane Smith
Title: CEO                          Title: VP Procurement
Date: June 1, 2022                  Date: June 1, 2022
"""

BIGBANK_SAAS = """
SAAS SUBSCRIPTION AGREEMENT

Effective Date: September 15, 2023

PROVIDER: DataFlow Systems, Inc.
CUSTOMER: BigBank Financial Services, Inc.

PRODUCT: DataFlow Enterprise Analytics Platform

SUBSCRIPTION TERM: 2 years (September 15, 2023 - September 14, 2025)

ANNUAL FEE: $500,000

USERS: Up to 250 named users

SPECIAL TERMS FOR FINANCIAL SERVICES:
1. DataFlow agrees to comply with all applicable banking regulations including GLBA and SOX
2. DataFlow will provide annual SOC 2 Type II reports
3. Customer audit rights: Customer may audit DataFlow's security practices with 30 days' notice
4. Data residency: All Customer data shall be stored in US-based data centers
5. Right to terminate: Customer may terminate immediately if DataFlow suffers a material data breach

SIGNATURE:

DataFlow Systems, Inc.              BigBank Financial Services, Inc.

/s/ Michael Chen                    /s/ Robert Johnson
CEO                                 Chief Data Officer
"""

# HIGH RISK - GPL License
SOFTWARE_LICENSE = """
SOFTWARE LICENSE AGREEMENT

This Software License Agreement ("Agreement") is entered into as of March 1, 2021, by and between:

LICENSOR: OpenSource Analytics Project ("Licensor")
LICENSEE: DataFlow Systems, Inc. ("Licensee")

1. GRANT OF LICENSE

Licensor hereby grants to Licensee a non-exclusive, worldwide license to use, modify, and distribute the "DataEngine Core" software library ("Software") subject to the terms herein.

2. LICENSED SOFTWARE

The Software includes the DataEngine Core library, version 2.0, which provides core data processing functionality including:
- Data ingestion pipelines
- ETL processing engine
- Query optimization module

***** OPEN SOURCE NOTICE *****

3. OPEN SOURCE COMPONENTS

3.1 GPL COMPONENTS: The Software incorporates components licensed under the GNU General Public License version 3 (GPLv3), specifically:
    - DataParser module (GPLv3)
    - StreamProcessor library (GPLv3)
    - QueryOptimizer core (GPLv3)

3.2 COPYLEFT OBLIGATIONS: Under GPLv3, any modifications to the GPL-licensed components, and any software that links to or incorporates these components, must also be released under GPLv3 terms.

3.3 SOURCE CODE: Licensee must make available the complete source code of any derivative works incorporating GPL components.

3.4 DISCLOSURE RISK: Use of GPL components in Licensee's proprietary software may require disclosure of Licensee's proprietary source code under certain distribution scenarios.

***** END OPEN SOURCE NOTICE *****

4. WARRANTY DISCLAIMER

THE SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.

5. LIMITATION OF LIABILITY

LICENSOR SHALL NOT BE LIABLE FOR ANY DAMAGES ARISING FROM THE USE OF THE SOFTWARE.

Acknowledged:

DATAFLOW SYSTEMS, INC.

By: /s/ Emily Watson
Name: Dr. Emily Watson
Title: CTO
Date: March 1, 2021
"""

# HIGH RISK - Pending Litigation
PENDING_LAWSUIT = """
LITIGATION SUMMARY
DataFlow Systems, Inc.

Case: TechRival Inc. v. DataFlow Systems, Inc.
Court: United States District Court, Northern District of California
Case Number: 3:23-cv-04521-WHO

***** HIGH RISK - ACTIVE LITIGATION *****

NATURE OF CLAIMS:

1. PATENT INFRINGEMENT
Plaintiff TechRival Inc. alleges that DataFlow's "SmartQuery" feature infringes on TechRival's U.S. Patent No. 10,123,456 ("Method for Optimizing Database Queries Using Machine Learning").

2. TRADE SECRET MISAPPROPRIATION
Plaintiff further alleges that DataFlow's former employee, hired in 2022, brought confidential information from TechRival and incorporated it into DataFlow's products.

CURRENT STATUS:
- Complaint filed: August 15, 2023
- Answer filed: October 1, 2023
- Discovery ongoing
- Claim construction hearing scheduled: March 2024
- Trial date: Not yet set (estimated Q4 2024 or Q1 2025)

DAMAGES SOUGHT:
- Compensatory damages: $5,000,000 (estimated based on alleged lost sales)
- Treble damages for willful infringement: $15,000,000 (if proven)
- Injunctive relief: Seeking to enjoin DataFlow from selling SmartQuery feature
- Attorneys' fees

COMPANY'S POSITION:
DataFlow denies all allegations and believes the claims are without merit. The Company contends that:
1. The SmartQuery feature was independently developed
2. The '456 patent is invalid based on prior art
3. No confidential information was received from the former employee

ESTIMATED EXPOSURE:
Best case: Defense costs only ($500,000 - $1,000,000)
Expected case: Settlement in the range of $1,000,000 - $2,000,000
Worst case: Judgment of $5,000,000 plus injunction

INSURANCE COVERAGE:
DataFlow maintains errors & omissions insurance with a $10M limit, subject to $250,000 self-insured retention. Carrier has been notified and is participating in defense under reservation of rights.

OUTSIDE COUNSEL:
Morrison & Foerster LLP (Lead), Partner: Sarah Kim

***** END LITIGATION SUMMARY *****

Prepared by: Legal Department
Date: December 1, 2023
"""

SETTLED_CLAIMS = """
HISTORICAL LITIGATION SUMMARY
DataFlow Systems, Inc.

SETTLED/RESOLVED MATTERS (2020-2022)

1. Employment Matter - Johnson v. DataFlow (2020)
   Type: Wrongful termination claim
   Resolution: Settled for $75,000, no admission of liability
   Status: CLOSED

2. Contract Dispute - OldVendor LLC v. DataFlow (2021)
   Type: Breach of contract (early termination of services agreement)
   Resolution: Settled for $150,000
   Status: CLOSED

3. IP Matter - DataFlow v. CopyRight Inc. (2022)
   Type: Copyright infringement (competitor copied marketing materials)
   Resolution: Consent decree, defendant ceased use, no payment
   Status: CLOSED

No other material litigation matters in the Company's history.

Prepared by: Legal Department
Date: December 1, 2023
"""

# Vendor Contracts
AWS_AGREEMENT = """
AWS ENTERPRISE AGREEMENT

Customer: DataFlow Systems, Inc.
Agreement Date: January 1, 2023

COMMITMENT TERM: 3 years (January 1, 2023 - December 31, 2025)

MINIMUM COMMITMENT: $1,500,000 over the 3-year term

YEAR 1 (2023): $400,000 minimum spend
YEAR 2 (2024): $500,000 minimum spend  
YEAR 3 (2025): $600,000 minimum spend

REMAINING COMMITMENT: As of January 1, 2024, approximately $1,100,000 remains committed.

DISCOUNT: 15% discount off on-demand pricing for all AWS services

INCLUDED SERVICES:
- EC2 compute instances
- S3 storage
- RDS databases
- Lambda serverless
- All other standard AWS services

TERMINATION:
Customer may terminate early but must pay 50% of remaining commitment.

[Standard AWS Enterprise Terms Apply]

DataFlow Systems, Inc.

/s/ Michael Chen
CEO
"""

SALESFORCE_SUBSCRIPTION = """
SALESFORCE.COM SUBSCRIPTION AGREEMENT

Customer: DataFlow Systems, Inc.
Subscription Start: July 1, 2022
Subscription End: June 30, 2025

PRODUCTS:
- Sales Cloud Enterprise Edition: 50 users @ $150/user/month = $7,500/month
- Service Cloud Professional: 20 users @ $100/user/month = $2,000/month
- Pardot: 1 instance @ $1,500/month

TOTAL MONTHLY: $11,000
TOTAL ANNUAL: $132,000
REMAINING TERM VALUE: ~$198,000 (through June 2025)

PAYMENT: Annual in advance

RENEWAL: Auto-renews for 1-year periods; 60 days' notice to cancel

[Standard Salesforce Terms Apply]

DataFlow Systems, Inc.

/s/ VP Sales
Date: June 15, 2022
"""

PARTNER_AGREEMENT = """
CHANNEL PARTNER AGREEMENT

This Channel Partner Agreement ("Agreement") is entered into as of October 1, 2022, by and between:

DataFlow Systems, Inc. ("DataFlow")
TechConsulting Partners, LLC ("Partner")

1. APPOINTMENT
DataFlow hereby appoints Partner as a non-exclusive reseller of DataFlow products in North America.

2. TERM
Initial term of 2 years with automatic 1-year renewals.

3. DISCOUNTS
Partner shall receive a 30% discount off list price for all resales.

4. MINIMUM COMMITMENT
Partner commits to $500,000 in annual bookings.
Year 1 Actual: $620,000 (exceeded)
Year 2 Target: $750,000

5. MARKETING DEVELOPMENT FUNDS
DataFlow shall provide Partner with $50,000 annually in marketing funds.

6. EXCLUSIVITY
None. DataFlow may appoint other partners in the same territory.

7. TERMINATION
Either party may terminate with 90 days' written notice.

DATAFLOW SYSTEMS, INC.          TECHCONSULTING PARTNERS, LLC

/s/ VP Partnerships             /s/ Managing Partner
"""

# IP Documents
PATENT_PORTFOLIO = """
PATENT PORTFOLIO SUMMARY
DataFlow Systems, Inc.

As of December 31, 2023

ISSUED PATENTS:

1. U.S. Patent No. 10,987,654
   Title: "System and Method for Real-Time Data Stream Processing"
   Issue Date: March 15, 2021
   Expiration: March 15, 2041
   Status: Active, maintenance fees current

2. U.S. Patent No. 11,234,567
   Title: "Machine Learning Pipeline for Automated Data Classification"
   Issue Date: July 22, 2022
   Expiration: July 22, 2042
   Status: Active, maintenance fees current

3. U.S. Patent No. 11,456,789
   Title: "Distributed Query Optimization for Heterogeneous Data Sources"
   Issue Date: November 3, 2023
   Expiration: November 3, 2043
   Status: Active

PENDING APPLICATIONS:

4. U.S. Patent Application No. 17/123,456
   Title: "Privacy-Preserving Analytics Using Differential Privacy"
   Filing Date: December 15, 2022
   Status: Under examination, Office Action response due February 2024

5. U.S. Patent Application No. 18/234,567
   Title: "Natural Language Interface for Data Querying"
   Filing Date: August 1, 2023
   Status: Awaiting first Office Action

FOREIGN PATENTS:
- EP Patent 3,123,456 (European validation of US '654)
- CN Patent ZL202110123456.7 (China counterpart of US '654)

VALUATION:
The patent portfolio has been valued at approximately $3-5 million based on comparable transactions in the data analytics industry.

Prepared by: IP Department
"""

TRADEMARK_REGISTRATIONS = """
TRADEMARK REGISTRATIONS
DataFlow Systems, Inc.

1. DATAFLOW (Word Mark)
   Registration No.: 5,123,456
   Registration Date: June 1, 2019
   Class: 42 (Software as a service)
   Status: Active, next renewal due June 2029

2. DATAFLOW (Logo)
   Registration No.: 5,234,567
   Registration Date: September 15, 2019
   Class: 42
   Status: Active

3. SMARTQUERY (Word Mark)
   Registration No.: 6,345,678
   Registration Date: February 1, 2022
   Class: 42
   Status: Active

4. "MAKING DATA WORK" (Tagline)
   Registration No.: 6,456,789
   Registration Date: May 1, 2023
   Class: 42
   Status: Active

All marks are in use in commerce and are current on maintenance filings.

Prepared by: IP Department
"""

# Financial Documents
AUDITED_FINANCIALS = """
AUDITED FINANCIAL STATEMENTS
DATAFLOW SYSTEMS, INC.
For the Year Ended December 31, 2023

INDEPENDENT AUDITOR'S REPORT:
We have audited the accompanying financial statements of DataFlow Systems, Inc.
In our opinion, the financial statements present fairly, in all material respects, the financial position of the Company.

BALANCE SHEET (December 31, 2023)

ASSETS
Cash and Cash Equivalents                    $4,500,000
Accounts Receivable                          $3,200,000
Prepaid Expenses                               $450,000
Property and Equipment, net                    $800,000
Intangible Assets                            $1,200,000
TOTAL ASSETS                                $10,150,000

LIABILITIES
Accounts Payable                               $650,000
Accrued Expenses                               $950,000
Deferred Revenue                             $2,800,000
Term Loan (SVB)                              $3,000,000
TOTAL LIABILITIES                            $7,400,000

STOCKHOLDERS' EQUITY
Common Stock                                    $10,000
Additional Paid-in Capital                  $12,000,000
Accumulated Deficit                         ($9,260,000)
TOTAL STOCKHOLDERS' EQUITY                   $2,750,000

TOTAL LIABILITIES AND EQUITY                $10,150,000

INCOME STATEMENT (Year Ended December 31, 2023)

Revenue                                     $16,500,000
Cost of Revenue                             ($5,000,000)
GROSS PROFIT                                $11,500,000

Operating Expenses:
  Sales and Marketing                       ($4,500,000)
  Research and Development                  ($5,200,000)
  General and Administrative                ($2,100,000)
TOTAL OPERATING EXPENSES                   ($11,800,000)

OPERATING LOSS                                ($300,000)

Interest Expense                              ($150,000)
Other Income                                    $50,000

NET LOSS                                      ($400,000)

Approved by:

/s/ Deloitte & Touche LLP
Independent Auditors
January 31, 2024
"""

TAX_RETURNS = """
FEDERAL INCOME TAX RETURN SUMMARY
DATAFLOW SYSTEMS, INC.
Tax Year 2022

Form 1120 (U.S. Corporation Income Tax Return)

SUMMARY:

Gross Receipts                              $12,800,000
Returns and Allowances                         $200,000
Net Sales                                   $12,600,000

Cost of Goods Sold                          $3,800,000
Gross Profit                                $8,800,000

Total Deductions                           $10,100,000
  - Salaries and wages: $6,500,000
  - Repairs and maintenance: $150,000
  - Bad debts: $75,000
  - Rents: $1,600,000
  - Taxes and licenses: $250,000
  - Depreciation: $300,000
  - Advertising: $450,000
  - Other deductions: $775,000

Taxable Income Before NOL                  ($1,300,000)

Net Operating Loss Deduction                          $0

TAXABLE INCOME                             ($1,300,000)

TOTAL TAX DUE                                        $0

NOL CARRYFORWARD:
Prior Year NOL:                             $4,200,000
Current Year NOL:                           $1,300,000
Total NOL Available:                        $5,500,000

Filed: March 15, 2023
Prepared by: Ernst & Young LLP
"""

DEBT_SCHEDULE = """
OUTSTANDING DEBT SCHEDULE
DataFlow Systems, Inc.
As of December 31, 2023

1. SILICON VALLEY BANK TERM LOAN

Original Principal: $5,000,000
Origination Date: January 15, 2022
Maturity Date: January 15, 2027
Interest Rate: Prime + 1.5% (currently 10.0%)
Monthly Payment: $95,000 (principal and interest)
Outstanding Balance: $3,000,000

Covenants:
- Minimum cash balance: $1,000,000 (In compliance)
- Maximum debt-to-equity ratio: 3.0x (Current: 2.7x - In compliance)
- Revenue growth: 15% year-over-year (Achieved 29% - In compliance)

Collateral: All assets of the Company

CHANGE OF CONTROL:
The loan agreement contains a change of control provision requiring repayment upon a Change of Control unless the lender consents to the assumption of the debt by the acquiring party.

2. EQUIPMENT FINANCING

Lender: Various equipment lessors
Total Outstanding: $350,000
Monthly Payments: $15,000
Remaining Term: 24 months
Collateral: Specific equipment financed

No prepayment penalties on equipment financing.

TOTAL DEBT OUTSTANDING: $3,350,000

Prepared by: Finance Department
December 31, 2023
"""

# Regulatory Documents
PRIVACY_POLICY = """
DATAFLOW SYSTEMS, INC.
DATA PRIVACY POLICY

Effective Date: January 1, 2024
Last Updated: December 15, 2023

1. INTRODUCTION
DataFlow Systems, Inc. ("DataFlow," "we," "us") is committed to protecting the privacy of our customers and users. This Policy describes how we collect, use, and protect personal information.

2. INFORMATION WE COLLECT
2.1 Customer Data: Data that customers upload to our platform for processing.
2.2 Account Information: Name, email, company name, billing information.
2.3 Usage Data: How users interact with our platform.
2.4 Technical Data: IP addresses, browser type, device information.

3. HOW WE USE INFORMATION
- To provide and improve our services
- To process payments
- To communicate with customers
- To ensure security and prevent fraud

4. DATA PROTECTION
4.1 Encryption: All data is encrypted at rest (AES-256) and in transit (TLS 1.2+).
4.2 Access Controls: Role-based access with multi-factor authentication.
4.3 Certifications: SOC 2 Type II certified.

5. DATA RETENTION
We retain customer data for the duration of the subscription plus 90 days. Customers may request deletion at any time.

6. INTERNATIONAL TRANSFERS
For EU customers, data is processed in EU data centers. Standard Contractual Clauses are available upon request.

7. CALIFORNIA PRIVACY RIGHTS (CCPA)
California residents have the right to:
- Know what personal information we collect
- Delete personal information
- Opt-out of sale of personal information (we do not sell personal information)

8. CONTACT
Privacy inquiries: privacy@dataflow.io

DataFlow Systems, Inc.
100 California Street, Suite 400
San Francisco, CA 94111
"""

SOC2_CERTIFICATION = """
SOC 2 TYPE II CERTIFICATION SUMMARY
DATAFLOW SYSTEMS, INC.

REPORT PERIOD: January 1, 2023 - December 31, 2023

AUDITOR: Deloitte & Touche LLP

TRUST SERVICE CRITERIA COVERED:
- Security
- Availability
- Processing Integrity
- Confidentiality

OPINION:
The service auditor's opinion is UNQUALIFIED. DataFlow Systems' controls were suitably designed and operating effectively throughout the examination period.

KEY CONTROLS TESTED:
1. Access Management: Role-based access, MFA required
2. Change Management: Documented change control process
3. Incident Response: 24/7 monitoring, defined escalation procedures
4. Data Protection: Encryption, backup procedures
5. Vendor Management: Third-party risk assessments
6. Business Continuity: Documented DR plan, tested annually

EXCEPTIONS NOTED: None

RECOMMENDATIONS:
- Consider additional penetration testing frequency (performed annually, suggest semi-annually)

NEXT EXAMINATION: Scheduled for Q1 2025

Full report available upon request under NDA.

DataFlow Systems, Inc.
Security & Compliance Team
"""

# Capitalization Table
CAP_TABLE = """
CAPITALIZATION TABLE
DATAFLOW SYSTEMS, INC.
As of December 31, 2023

COMMON STOCK

Shareholder                  Shares          %       Notes
-----------------------------------------------------------------
Michael Chen (Founder/CEO)   15,000,000     25.0%   Fully vested
Emily Watson (CTO)            3,000,000      5.0%   Subject to vesting
Sarah Johnson (Director)        500,000      0.8%   
Robert Williams (Director)      500,000      0.8%   
Series A Investors           18,000,000     30.0%   Acme Ventures (lead)
Series B Investors           15,000,000     25.0%   BigFund Capital (lead)
Employee Option Pool          8,000,000     13.4%   4M granted, 4M available
-----------------------------------------------------------------
TOTAL                        60,000,000    100.0%

OPTION POOL BREAKDOWN

Granted Options:
- Dr. Emily Watson:    800,000 options @ $0.50 (200K vested)
- Other executives:  1,200,000 options @ $1.00 (avg)
- Employees:         2,000,000 options @ $1.50 (avg)

Available for Grant: 4,000,000 shares

PREFERRED STOCK TERMS

Series A Preferred:
- Original Issue Price: $1.00
- Liquidation Preference: 1x non-participating
- Conversion: 1:1 to Common
- Anti-dilution: Broad-based weighted average

Series B Preferred:
- Original Issue Price: $3.00
- Liquidation Preference: 1x non-participating
- Conversion: 1:1 to Common
- Anti-dilution: Broad-based weighted average

LAST ROUND VALUATION:
Series B (June 2022): $45,000,000 pre-money / $60,000,000 post-money

409A VALUATION:
Most recent 409a: December 2023
Common Stock FMV: $1.50 per share

Prepared by: Finance Department
"""

def generate_documents():
    """Generate all test documents."""
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Define folder structure and documents
    documents = {
        "01_Corporate": {
            "Certificate_of_Incorporation.txt": CERTIFICATE_OF_INCORPORATION,
            "Bylaws.txt": BYLAWS,
            "Board_Resolutions_2023.txt": BOARD_RESOLUTION_2023,
            "Capitalization_Table.txt": CAP_TABLE,
        },
        "02_Contracts/Customer_Agreements": {
            "Acme_Corp_MSA.txt": ACME_MSA,
            "BigBank_SaaS_Agreement.txt": BIGBANK_SAAS,
        },
        "02_Contracts/Vendor_Contracts": {
            "AWS_Services_Agreement.txt": AWS_AGREEMENT,
            "Salesforce_Subscription.txt": SALESFORCE_SUBSCRIPTION,
        },
        "02_Contracts/Partnership_Agreements": {
            "Channel_Partner_Agreement.txt": PARTNER_AGREEMENT,
        },
        "03_Employment": {
            "CEO_Employment_Agreement.txt": CEO_EMPLOYMENT_AGREEMENT,
            "CTO_Employment_Agreement.txt": CTO_EMPLOYMENT_AGREEMENT,
            "Standard_Offer_Letter_Template.txt": STANDARD_OFFER_LETTER,
            "Employee_Handbook.txt": EMPLOYEE_HANDBOOK,
        },
        "04_IP": {
            "Patent_Portfolio_Summary.txt": PATENT_PORTFOLIO,
            "Trademark_Registrations.txt": TRADEMARK_REGISTRATIONS,
            "Software_License_Agreement.txt": SOFTWARE_LICENSE,
        },
        "05_Real_Estate": {
            "Office_Lease_SF.txt": OFFICE_LEASE_SF,
            "Office_Lease_NYC.txt": OFFICE_LEASE_NYC,
        },
        "06_Litigation": {
            "Pending_Lawsuit_Summary.txt": PENDING_LAWSUIT,
            "Settled_Claims_2022.txt": SETTLED_CLAIMS,
        },
        "07_Financial": {
            "Audited_Financials_2023.txt": AUDITED_FINANCIALS,
            "Tax_Returns_2022.txt": TAX_RETURNS,
            "Outstanding_Debt_Schedule.txt": DEBT_SCHEDULE,
        },
        "08_Regulatory": {
            "Data_Privacy_Policy.txt": PRIVACY_POLICY,
            "SOC2_Certification.txt": SOC2_CERTIFICATION,
        },
    }
    
    file_count = 0
    for folder_path, files in documents.items():
        full_folder_path = os.path.join(OUTPUT_DIR, folder_path)
        os.makedirs(full_folder_path, exist_ok=True)
        
        for filename, content in files.items():
            file_path = os.path.join(full_folder_path, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content.strip())
            file_count += 1
            print(f"Created: {folder_path}/{filename}")
    
    print(f"\n✓ Generated {file_count} documents")
    
    # Create ZIP file
    zip_path = OUTPUT_DIR + ".zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(OUTPUT_DIR))
                zipf.write(file_path, arcname)
    
    print(f"✓ Created ZIP: {zip_path}")
    print(f"\n📁 Test Data Room ready at: {OUTPUT_DIR}")
    
    return file_count

if __name__ == "__main__":
    generate_documents()
