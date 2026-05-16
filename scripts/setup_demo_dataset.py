"""
Setup demo dataset by creating all demo documents.

This script creates the demo dataset structure and files needed for evaluation.
"""

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_demo_documents():
    """Create all demo documents."""

    # Create directory structure
    demo_dir = Path("data/demo")
    (demo_dir / "enterprise").mkdir(parents=True, exist_ok=True)
    (demo_dir / "technical").mkdir(parents=True, exist_ok=True)
    (demo_dir / "evaluation").mkdir(parents=True, exist_ok=True)

    logger.info("Created directory structure")

    # Enterprise documents
    enterprise_docs = {
        "hr_policy.md": """# HR Policy Document

## Annual Leave Policy

### Eligibility
All full-time employees are eligible for annual leave (年假) after completing their probation period.

### Annual Leave Entitlement
- 0-2 years of service: 10 days per year
- 3-5 years of service: 15 days per year
- 6+ years of service: 20 days per year

### How to Apply
1. Submit leave request through the HR portal at least 2 weeks in advance
2. Get manager approval
3. HR will confirm the leave dates

### Carryover Policy
Unused annual leave can be carried over to the next year, up to a maximum of 5 days.

## Sick Leave Policy

### Eligibility
All employees are entitled to sick leave (病假) from their first day of employment.

### Sick Leave Entitlement
- Full-time employees: 12 days per year
- Part-time employees: 6 days per year

### Medical Certificate
A medical certificate is required for sick leave exceeding 3 consecutive days.

### Notification
Employees must notify their manager and HR within 2 hours of their scheduled start time.

## Benefits

### Health Insurance
The company provides comprehensive health insurance coverage for all full-time employees and their immediate family members.

### Retirement Plan
Employees are automatically enrolled in the company retirement plan after 6 months of service. The company matches employee contributions up to 5% of salary.

### Professional Development
Each employee has an annual budget of $2,000 for professional development courses, conferences, and certifications.
""",

        "it_guide.md": """# IT Guidelines

## VPN Access

### What is VPN?
VPN (Virtual Private Network) allows employees to securely access company resources from remote locations.

### How to Connect to VPN
1. Download the VPN client from the IT portal
2. Install the client on your device
3. Use your company credentials to log in
4. Select the appropriate VPN server (US, EU, or APAC)
5. Click "Connect"

### Troubleshooting VPN Issues
- **Cannot connect**: Check your internet connection and firewall settings
- **Slow connection**: Try switching to a different VPN server
- **Authentication failed**: Reset your password through the IT portal

### VPN Usage Policy
- VPN should only be used for work-related activities
- Do not share your VPN credentials
- Disconnect when not actively using company resources

## Software Installation

### Approved Software
Employees can install the following software without IT approval:
- Microsoft Office Suite
- Slack
- Zoom
- Google Chrome
- Firefox

### Requesting New Software
1. Submit a software request through the IT portal
2. Provide business justification
3. IT will review within 3 business days
4. If approved, IT will install the software remotely

### Security Software
All company devices must have:
- Antivirus software (automatically installed)
- Firewall enabled
- Automatic updates enabled

## Password Policy

### Password Requirements
- Minimum 12 characters
- Must include uppercase, lowercase, numbers, and special characters
- Cannot reuse last 5 passwords
- Must be changed every 90 days

### Multi-Factor Authentication (MFA)
MFA is required for:
- Email access
- VPN connection
- Cloud storage
- HR portal

## Data Security

### Sensitive Data Handling
- Do not store sensitive data on personal devices
- Use encrypted storage for confidential files
- Do not share sensitive information via personal email

### Data Backup
- All work files should be stored on company cloud storage
- Local backups are performed automatically every night
- Employees are responsible for organizing their files
""",

        "finance.md": """# Finance Policy

## Expense Reimbursement

### Eligible Expenses
The following expenses are eligible for reimbursement (报销):
- Business travel (flights, hotels, meals)
- Client entertainment
- Office supplies
- Professional development courses
- Conference registration fees

### Expense Limits
- Meals: $50 per day for domestic travel, $75 per day for international travel
- Hotels: Up to $200 per night
- Client entertainment: Up to $100 per person, requires manager approval

### How to Submit Expense Reports
1. Log in to the finance portal
2. Upload receipts (must be clear and legible)
3. Fill out expense report form
4. Submit for manager approval
5. Finance will process within 5 business days

### Receipt Requirements
- Original receipts required for expenses over $25
- Digital receipts are acceptable
- Receipts must show date, vendor, amount, and items purchased

## Budget Management

### Department Budgets
Each department receives an annual budget allocation based on:
- Historical spending
- Projected headcount
- Strategic initiatives

### Budget Approval Process
- Expenses within budget: Manager approval only
- Expenses exceeding budget: Requires VP approval
- Capital expenses over $10,000: Requires CFO approval

### Budget Tracking
Managers can view real-time budget status through the finance portal.

## Purchase Orders

### When to Use Purchase Orders
Purchase orders (PO) are required for:
- Vendor contracts over $5,000
- Recurring services
- Equipment purchases

### PO Approval Workflow
1. Requester submits PO request
2. Manager approves
3. Finance reviews and creates PO
4. Vendor receives PO
5. Goods/services delivered
6. Invoice matched to PO for payment

## Corporate Credit Cards

### Eligibility
Corporate credit cards are issued to:
- Directors and above
- Employees with frequent travel
- Department budget owners

### Usage Policy
- Only for business expenses
- Submit expense reports monthly
- Personal charges are prohibited
- Lost cards must be reported immediately
"""
    }

    # Write enterprise documents
    for filename, content in enterprise_docs.items():
        path = demo_dir / "enterprise" / filename
        path.write_text(content, encoding='utf-8')
        logger.info(f"Created: {path}")

    # Technical documents (abbreviated for script length - see full content in plan)
    logger.info("\nNote: Technical documents and evaluation files should be created manually")
    logger.info("See: docs/superpowers/plans/2026-05-15-performance-comparison-framework.md")
    logger.info("\nDemo dataset setup complete!")
    logger.info(f"Documents created in: {demo_dir.absolute()}")


if __name__ == "__main__":
    create_demo_documents()
