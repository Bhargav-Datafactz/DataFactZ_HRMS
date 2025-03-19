import os
import django
import pandas as pd
import openpyxl 
from django.core.management.base import BaseCommand
from datetime import datetime
from django.db import transaction, IntegrityError
# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "datafactz.settings")  # Adjust as necessary
django.setup()

from employee.models import Employee, EmployeeWorkInformation
from leave.models import LeaveRequest, LeaveType,AvailableLeave

from django.db.models import Sum

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

    # If it's already a datetime object, return the date part
    if isinstance(date_str, datetime):
        return date_str.date()

    # Try parsing with different date formats
    formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%b-%y", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(str(date_str), fmt).date()
        except ValueError:
            continue

    print(f"Warning: Unable to parse date: {date_str}")
    return None  # Return None if no format matches



def read_file(file_path):
    """Reads CSV or XLSX file and returns data as a list of dictionaries."""
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path, encoding="ISO-8859-1")
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
          
                employee_first_name = names[0]
                employee_last_name = names[1] if len(names) > 1 else ""
            else:
                employee_first_name = row.get("employee_first_name", "").strip()
                employee_last_name = row.get("employee_last_name", "").strip()

            if not employee_first_name:
                raise ValueError(f"Missing employee first name for email {row['email']}")
              
            employee, created = Employee.objects.update_or_create(
                email=normalize_email(row["email"]),
                defaults={
                    "badge_id": row.get("badge_id", ""),
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
                    "employee_first_name":row.get("employee_first_name"),
                    "employee_last_name":row.get("employee_last_name"),
                },
            )
              
            print(f"{'Created' if created else 'Updated'} Employee: {employee.employee_first_name}")
        except Exception as e:
            print(f"Error importing employee {row.get('email', 'Unknown')}: {e}")


'''
def import_leave_history(csv_file_path):
    """
    Optimized import of leave history from a CSV (Excel) file using email as the identifier.
    Expected columns:
      - employee_email
      - leave_type
      - start_date (YYYY-MM-DD)
      - end_date (YYYY-MM-DD)
      - status
      - start_breakdown
      - end_breakdown
    This version pre-fetches data and uses bulk operations.
    """
    import pandas as pd
    from django.db import transaction

    try:
        data = pd.read_excel(csv_file_path, dtype=str).fillna("")
     

    except Exception as e:
        print(f"❌ Failed to read CSV: {e}")
        return
    
    # 1. Build employee mapping using email
    employee_emails = data["employee_email"].str.strip().str.lower().unique().tolist()
    existing_employees = Employee.objects.filter(email__in=employee_emails)
    employees_dict = {emp.email.lower(): emp for emp in existing_employees}

    # 2. Build leave type mapping using leave type name
    csv_leave_types = data["leave_type"].str.strip().unique().tolist()
    existing_leave_types = LeaveType.objects.filter(name__in=csv_leave_types)
    leave_types_dict = {lt.name: lt for lt in existing_leave_types}

    # 3. Prepare rows to process. We create a composite key using employee email,
    # leave type, start_date and end_date.
    rows_to_process = []
    for index, row in data.iterrows():
        email = row.get("employee_email", "").strip().lower()
        if not email:
            print(f"Skipping row {index+1}: Missing employee_email.")
            continue

        employee = employees_dict.get(email)
        if not employee:
            print(f"Skipping row {index+1}: Employee with email '{email}' not found in DB.")
            continue

        leave_type_name = row.get("leave_type", "").strip()
        if not leave_type_name:
            print(f"Skipping row {index+1}: Missing leave_type.")
            continue

        # Create leave type on the fly if not already in our dict.
        if leave_type_name not in leave_types_dict:
            leave_type_obj, _ = LeaveType.objects.get_or_create(name=leave_type_name)
            leave_types_dict[leave_type_name] = leave_type_obj
        else:
            leave_type_obj = leave_types_dict[leave_type_name]

        # Parse dates.
        start_date_str = row.get("start_date", "").strip()
        end_date_str = row.get("end_date", "").strip()
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)
        if not start_date or not end_date:
            print(f"Skipping row {index+1}: Invalid dates (start: '{start_date_str}', end: '{end_date_str}').")
            continue
        if start_date > end_date:
            print(f"Skipping row {index+1}: start_date ({start_date}) is after end_date ({end_date}).")
            continue

        status = row.get("status", "").strip().lower() or "pending"
        start_date_breakdown = row.get("start_date_breakdown", "full_day").strip().lower().replace(" ", "_")[:30]
        end_date_breakdown = row.get("end_date_breakdown", "full_day").strip().lower().replace(" ", "_")[:30]
                # ✅ Extract `requested_days` directly from the file
        try:
            requested_days = float(row.get("requested_days", 0) or 0)
        except ValueError:
            print(f"Skipping row {index+1}: Invalid requested_days value '{row.get('requested_days')}'.")
            continue


        # Create a composite key based on email and leave type (as a name), plus dates.
        key = f"{email}-{leave_type_name}-{start_date}-{end_date}"
        rows_to_process.append({
            "key": key,
            "employee": employee,
            "leave_type": leave_type_obj,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "start_breakdown": start_date_breakdown,
            "end_breakdown": end_date_breakdown,
            "requested_days": requested_days,
            "row_index": index + 1,  # For logging
        })

    if not rows_to_process:
        print("No valid leave history records to process.")
        return

    # 4. Fetch existing leave requests in bulk for the involved employees.
    existing_leave_requests = LeaveRequest.objects.filter(employee_id__email__in=employee_emails)
    existing_map = {}
    for lr in existing_leave_requests:
        comp_key = f"{lr.employee_id.email.lower()}-{lr.leave_type_id.name}-{lr.start_date}-{lr.end_date}"
        existing_map[comp_key] = lr

    # 5. Separate records into ones that need updating vs. new ones.
    new_leave_requests = []
    update_leave_requests = []
    for row in rows_to_process:
        key = row["key"]
        if key in existing_map:
            lr = existing_map[key]
            lr.status = row["status"]
            #lr.start_date_breakdown = row["start_date_breakdown"]
            #lr.end_date_breakdown = row["end_date_breakdown"]
            #lr.requested_days = row["requested_days"]
            
        else:
            lr = LeaveRequest(
                employee_id=row["employee"],
                leave_type_id=row["leave_type"],
                start_date=row["start_date"],
                end_date=row["end_date"],
                status=row["status"],
            
                start_date_breakdown = row.get("start_date_breakdown", "full_day").strip().lower().replace(" ", "_")[:30],
                end_date_breakdown = row.get("end_date_breakdown", "full_day").strip().lower().replace(" ", "_")[:30],
                requested_days=row["requested_days"],

            )
            new_leave_requests.append(lr)
        #print("Columns read by Pandas:", data.columns.tolist())
    # 6. Perform bulk operations inside a single transaction.
    with transaction.atomic():
        if new_leave_requests:
            LeaveRequest.objects.bulk_create(new_leave_requests, batch_size=1000)
        if update_leave_requests:
            LeaveRequest.objects.bulk_update(
                update_leave_requests,
                ["status", "start_date_breakdown", "end_date_breakdown","requested_days"],
                batch_size=5400
            )
    available_leave = AvailableLeave.objects.get(
        employee_id=employee,
        leave_type_id=leave_type_obj,
    )

    if available_leave:
        # Increment the period leave counter
        available_leave.period_leaves_taken += requested_days
        
        # Subtract the imported leave days from available_days, ensuring it doesn't drop below zero
        available_leave.available_days = max(available_leave.available_days - requested_days, 0)
        
        # Recalculate total leave days (for example, as available_days plus any carryforward)
        available_leave.total_leave_days = available_leave.available_days + available_leave.carryforward_days

        available_leave.save()
        print(f"✅ Updated period leaves taken for {employee.email}: {available_leave.period_leaves_taken}")
    else:
        print(f"⚠️ Still no available leave record for {employee.email}, skipping update.")

                
    
    total_processed = len(new_leave_requests) + len(update_leave_requests)
    print(f"\n✅ Finished import: {total_processed} leave records processed.")
'''
def import_leave_history(csv_file_path):
    """
    Optimized import of leave history from a CSV (Excel) file using email as the identifier.
    Expected columns:
      - employee_email
      - leave_type
      - start_date (YYYY-MM-DD)
      - end_date (YYYY-MM-DD)
      - status
      - start_breakdown
      - end_breakdown
    This version pre-fetches data and uses bulk operations.
    """
    import pandas as pd
    from django.db import transaction

    try:
        data = pd.read_excel(csv_file_path, dtype=str).fillna("")
     

    except Exception as e:
        print(f"❌ Failed to read CSV: {e}")
        return
    
    # 1. Build employee mapping using email
    employee_emails = data["employee_email"].str.strip().str.lower().unique().tolist()
    existing_employees = Employee.objects.filter(email__in=employee_emails)
    employees_dict = {emp.email.lower(): emp for emp in existing_employees}

    # 2. Build leave type mapping using leave type name
    csv_leave_types = data["leave_type"].str.strip().unique().tolist()
    existing_leave_types = LeaveType.objects.filter(name__in=csv_leave_types)
    leave_types_dict = {lt.name: lt for lt in existing_leave_types}

    # 3. Prepare rows to process. We create a composite key using employee email,
    # leave type, start_date and end_date.
    rows_to_process = []
    for index, row in data.iterrows():
        email = row.get("employee_email", "").strip().lower()
        if not email:
            print(f"Skipping row {index+1}: Missing employee_email.")
            continue

        employee = employees_dict.get(email)
        if not employee:
            print(f"Skipping row {index+1}: Employee with email '{email}' not found in DB.")
            continue

        leave_type_name = row.get("leave_type", "").strip()
        if not leave_type_name:
            print(f"Skipping row {index+1}: Missing leave_type.")
            continue

        # Create leave type on the fly if not already in our dict.
        if leave_type_name not in leave_types_dict:
            leave_type_obj, _ = LeaveType.objects.get_or_create(name=leave_type_name)
            leave_types_dict[leave_type_name] = leave_type_obj
        else:
            leave_type_obj = leave_types_dict[leave_type_name]

        # Parse dates.
        start_date_str = row.get("start_date", "").strip()
        end_date_str = row.get("end_date", "").strip()
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)
        if not start_date or not end_date:
            print(f"Skipping row {index+1}: Invalid dates (start: '{start_date_str}', end: '{end_date_str}').")
            continue
        if start_date > end_date:
            print(f"Skipping row {index+1}: start_date ({start_date}) is after end_date ({end_date}).")
            continue

        status = row.get("status", "").strip().lower() or "pending"
        start_date_breakdown = row.get("start_date_breakdown", "full_day").strip().lower().replace(" ", "_")[:30]
        end_date_breakdown = row.get("end_date_breakdown", "full_day").strip().lower().replace(" ", "_")[:30]
                # ✅ Extract `requested_days` directly from the file
        try:
            requested_days = float(row.get("requested_days", 0) or 0)
        except ValueError:
            print(f"Skipping row {index+1}: Invalid requested_days value '{row.get('requested_days')}'.")
            continue


        # Create a composite key based on email and leave type (as a name), plus dates.
        key = f"{email}-{leave_type_name}-{start_date}-{end_date}"
        rows_to_process.append({
            "key": key,
            "employee": employee,
            "leave_type": leave_type_obj,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "start_breakdown": start_date_breakdown,
            "end_breakdown": end_date_breakdown,
            "requested_days": requested_days,
            "row_index": index + 1,  # For logging
        })

    if not rows_to_process:
        print("No valid leave history records to process.")
        return

    # 4. Fetch existing leave requests in bulk for the involved employees.
    existing_leave_requests = LeaveRequest.objects.filter(employee_id__email__in=employee_emails)
    existing_map = {}
    for lr in existing_leave_requests:
        comp_key = f"{lr.employee_id.email.lower()}-{lr.leave_type_id.name}-{lr.start_date}-{lr.end_date}"
        existing_map[comp_key] = lr

    # 5. Separate records into ones that need updating vs. new ones.
    available_leave_updates = {}
    new_leave_requests = []
    update_leave_requests = []
    pairs_to_update = set()
    for row in rows_to_process:
        key = row["key"]
        pairs_to_update.add((employee, leave_type_obj))
        leave_type_obj = row["leave_type"]
        employee = row["employee"]
        if key in existing_map:
            lr = existing_map[key]
            lr.status = row["status"]
            #lr.start_date_breakdown = row["start_date_breakdown"]
            #lr.end_date_breakdown = row["end_date_breakdown"]
            #lr.requested_days = row["requested_days"]
            
            
        else:
            lr = LeaveRequest(
                employee_id=row["employee"],
                leave_type_id=row["leave_type"],
                start_date=row["start_date"],
                end_date=row["end_date"],
                status=row["status"],
            
                start_date_breakdown = row.get("start_date_breakdown", "full_day").strip().lower().replace(" ", "_")[:30],
                end_date_breakdown = row.get("end_date_breakdown", "full_day").strip().lower().replace(" ", "_")[:30],
                requested_days=row["requested_days"],

            )
            new_leave_requests.append(lr)
        '''
        try:
            employee = row["employee"]
            leave_type_obj = row["leave_type"]
            requested_days = row["requested_days"]
            leave_type = LeaveType.objects.get(name=leave_type_name)
            leave_type_leaves = leave_type.total_days  
            available_leave, created = AvailableLeave.objects.get_or_create(
                employee_id=employee,
                leave_type_id=leave_type_obj,
                defaults={
                    "available_days": leave_type_obj.total_days,  # or your desired default
                    "carryforward_days": 0,
                    "period_leaves_taken": 0,
                },
            )
            print(f"Employee: {employee.email}, LeaveType: {leave_type_obj.name}, Created: {created}, Current period_leaves_taken: {available_leave.period_leaves_taken}")
            available_leave.available_days = leave_type_leaves
            available_leave.total_leave_days = available_leave.carryforward_days + available_leave.available_days 
            available_leave.period_leaves_taken += requested_days
            available_leave.total_leave_days = available_leave.total_leave_days - available_leave.period_leaves_taken
            available_leave.available_days = available_leave.available_days - available_leave.period_leaves_taken
            available_leave.save()
            print(f"Updated period_leaves_taken: {available_leave.period_leaves_taken}")
        except AvailableLeave.DoesNotExist:
            print(f"⚠️ No available leave found for {employee.email} and {LeaveType.name}. Skipping period_leaves_taken update.")
        '''
        try:
            employee = row["employee"]
            leave_type_obj = row["leave_type"]
            requested_days = row["requested_days"]
            total_leave_days = leave_type_obj.total_days  # from the LeaveType object

            available_leave, created = AvailableLeave.objects.get_or_create(
                employee_id=employee,
                leave_type_id=leave_type_obj,
                defaults={
                    "available_days": total_leave_days,
                    "carryforward_days": 0,
                    "period_leaves_taken": 0,
                    "total_leave_days": total_leave_days,
                },
            )

            # Cumulatively update period_leaves_taken.
            available_leave.period_leaves_taken += requested_days

            # Calculate new available days ensuring it does not drop below zero.
            new_available = total_leave_days - available_leave.period_leaves_taken
            available_leave.available_days = max(new_available, 0)

            # Recalculate total leave days (carryforward plus available).
            available_leave.total_leave_days = available_leave.carryforward_days + available_leave.available_days

            available_leave.save()
            print(f"Employee: {employee.email}, LeaveType: {leave_type_obj.name}, Created: {created}, Updated period_leaves_taken: {available_leave.period_leaves_taken}")
        except Exception as ex:
            print(f"Error updating AvailableLeave for {employee.email} and {leave_type_obj.name}: {ex}")
        #print("Columns read by Pandas:", data.columns.tolist())
    # 6. Perform bulk operations inside a single transaction.
    
    from django.db.models import Sum
    with transaction.atomic():
        if new_leave_requests:
            LeaveRequest.objects.bulk_create(new_leave_requests, batch_size=1000)

        if update_leave_requests:
            LeaveRequest.objects.bulk_update(
                update_leave_requests,
                ["status", "start_date_breakdown", "end_date_breakdown","requested_days"],
                batch_size=5400
            )
    total_processed = len(new_leave_requests) + len(update_leave_requests)
    print(f"\n✅ Finished import: {total_processed} leave records processed.")

def import_leave_allocation(file_path):
    """Automatically allocates leaves based on LeaveType and carryforward data."""
    data = read_file(file_path)

    for row in data:
        try:
            with transaction.atomic():  # Ensures atomic transactions
                employee_email = row.get("employee_email", "").strip().lower()
                leave_type_name = row.get("leave_type", "").strip()
                carryforward_days = float(row.get("carryforward_days", 0) or 0)  # Carryforward from previous year

                # Get Employee
                try:
                    employee = Employee.objects.get(email=employee_email)
                except Employee.DoesNotExist:
                    print(f"Skipping: Employee {employee_email} not found.")
                    continue

                # Get Leave Type
                try:
                    leave_type = LeaveType.objects.get(name=leave_type_name)
                    leave_type_leaves = leave_type.total_days  # ✅ Use correct field name
                except LeaveType.DoesNotExist:
                    print(f"Skipping: Leave Type {leave_type_name} not found.")
                    continue

                # Get or Create AvailableLeave Entry
                available_leave, created = AvailableLeave.objects.get_or_create(
                    employee_id=employee, leave_type_id=leave_type
                )

                # ✅ Automatically allocate leave type leaves and carryforward leaves
                available_leave.available_days = leave_type_leaves  # Assign leave type default quota
                available_leave.carryforward_days = carryforward_days
                available_leave.total_leave_days = available_leave.available_days + available_leave.carryforward_days

                available_leave.save()  # Save with new values

                print(f"Updated {employee_email}: {available_leave.total_leave_days} total leaves assigned.")

        except Exception as e:
            print(f"Error processing {row.get('employee_email', 'Unknown')}: {e}")


if __name__ == "__main__":
    import sys
    '''
    if len(sys.argv) < 2:
        print("Usage: python script.py <employee_file> <leave_file>")
        sys.exit(1)
    '''
    #employee_file = sys.argv[1]
    leave_file = sys.argv[1]
    #import_employees(employee_file)
    
    import_leave_history(leave_file)
    #import_leave_allocation(leave_file)