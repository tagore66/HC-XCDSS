"""
HC-XCDSS Development Admin Reset & Bootstrap Utility

Usage:
  Set environment variables in your environment or .env:
    ADMIN_EMAIL=your_admin_email@domain.com
    ADMIN_PASSWORD=your_secure_password
    ADMIN_NAME="Platform Administrator"

  Then run:
    .venv\Scripts\python scripts/reset_admin.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv()

from src.db.migration import ensure_admin_account
from src.db.session import SessionLocal
from src.db.models.user import User, UserRole

def main():
    print("=" * 60)
    print("HC-XCDSS Admin Account Bootstrap & Reset Utility")
    print("=" * 60)

    admin_email = os.getenv("ADMIN_EMAIL", "admin@hcxcdss.org").strip().lower()
    admin_name = os.getenv("ADMIN_NAME", "Platform Administrator").strip()

    if not os.getenv("ADMIN_PASSWORD"):
        print("[NOTICE] ADMIN_PASSWORD environment variable not set.")
        print("Default development credentials from ensure_admin_account will be used if creating new.")
    
    print(f"Target Admin Email: {admin_email}")
    print(f"Target Admin Name:  {admin_name}")
    print("Applying admin credentials...")

    ensure_admin_account(reset_if_exists=True)

    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if admin_user and admin_user.role == UserRole.ADMIN:
            print("[SUCCESS] Admin account verified in database:")
            print(f"  - User ID:   {admin_user.id}")
            print(f"  - Email:     {admin_user.email}")
            print(f"  - Full Name: {admin_user.full_name}")
            print(f"  - Role:      {admin_user.role.value}")
            print(f"  - Active:    {admin_user.is_active}")
        else:
            print("[ERROR] Could not confirm admin account in database.")
    finally:
        db.close()

    print("=" * 60)

if __name__ == "__main__":
    main()
