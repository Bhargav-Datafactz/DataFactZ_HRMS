import os
import django
import pandas as pd
import openpyxl 
from django.core.management.base import BaseCommand
from datetime import datetime

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")  # Adjust as necessary
django.setup()

from employee.models import Employee, EmployeeWorkInformation
from leave.models import LeaveRequest, LeaveType

import unicodedata
import re

def normalize_email(email):
    """Cleans and normalizes emails to prevent encoding mismatches."""
    if not email:
        return None
    email = email.strip().lower()
    email = unicodedata.normalize("NFKC", email)  # Normalize Unicode characters
    email = re.sub(r'\s+', '', email)  # Remove spaces within
    email = email.replace("\xa0", "")  # Remove non-breaking spaces
    email = email.replace("\r", "").replace("\n", "")  # Remove newlines
    return email

def parse_date(date_str):
    """Converts a date string to a datetime object. Handles multiple formats."""
    if pd.isna(date_str) or not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(date_str), fmt).date()
        except ValueError:
            continue
    return None


def read_file(file_path):
    """Reads CSV or XLSX file and returns data as a list of dictionaries."""
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path, dtype=str)
    elif file_path.endswith(".xlsx"):
        df = pd.read_excel(file_path, dtype=str)
    else:
        raise ValueError("Unsupported file format. Please provide a .csv or .xlsx file.")
    df.columns = [col.lower().strip() for col in df.columns]
    return df.to_dict(orient="records")


def import_employees(employee_file):
    """Imports employee data."""
    data = read_file(employee_file)
    for row in data:
        try:
            # Split full name if necessary
            first_name, last_name = "", ""
            if "employee_full_name" in row and row["employee_full_name"]:
                names = row["employee_full_name"].strip().split(" ", 1)
          
                first_name = names[0]
                last_name = names[1] if len(names) > 1 else ""
            else:
                first_name = row.get("first name", "").strip()
                last_name = row.get("last name", "").strip()

            if not first_name:
                raise ValueError(f"Missing employee first name for email {row['email']}")
              
            employee, created = Employee.objects.update_or_create(
                email=normalize_email(row["email"]),
                defaults={
                    "badge_id": row.get("badge_id", "").strip(),
                    "phone": str(row.get("phone", "")).strip(),
                    "dob": parse_date(row.get("dob")),
                    "gender": row.get("gender", "male"),
                    "qualification": row.get("qualification"),
                    "experience": float(row.get("experience", 0) or 0),  # Ensure it's a float
                    "address": row.get("address"),
                    "country": row.get("country"),
                    "state": row.get("state"),
                    "city": row.get("city"),
                    "zip": row.get("zip"),
                },
            )
              
            print(f"{'Created' if created else 'Updated'} Employee: {employee.employee_first_name}")
        except Exception as e:
            print(f"Error importing employee {row.get('email', 'Unknown')}: {e}")


def import_leave_history(leave_file):
    """Imports leave history data."""
    data = read_file(leave_file)
    for row in data:
        try:
            if "employee_email" not in row:
                raise ValueError("Missing employee email in leave history")

            try:
                employee = Employee.objects.get(email=row["employee_email"].strip().lower())
            except Employee.DoesNotExist:
                print(f"Skipping leave record: Employee with email {row['employee_email']} not found.")
                continue

            leave_type, _ = LeaveType.objects.get_or_create(name=row["leave_type"].strip())
            leave_request, created = LeaveRequest.objects.update_or_create(
                employee_id=employee,
                leave_type_id=leave_type,
                start_date=parse_date(row["start_date"]),
                end_date=parse_date(row["end_date"]),
                defaults={
                    "status": row["status"],
                },
            )
            print(f"{'Created' if created else 'Updated'} LeaveRequest for {employee.email}")
        except Exception as e:
            print(f"Error importing leave history {row.get('employee_email', 'Unknown')}: {e}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python script.py <employee_file> <leave_file>")
        sys.exit(1)

    employee_file = sys.argv[1]
    leave_file = sys.argv[2]
    import_employees(employee_file)
    import_leave_history(leave_file)
