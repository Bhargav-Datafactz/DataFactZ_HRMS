import calendar
import datetime as dt
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from dateutil.relativedelta import relativedelta

today = datetime.now()


def leave_reset():
    from leave.models import LeaveType
    print(f"leave_reset() function executed at {datetime.now()}") 
    today_date = today.date()
    leave_types = LeaveType.objects.filter(reset=True)

    # Looping through filtered leave types with reset is true
    for leave_type in leave_types:
        # #Looping through all available leaves
        available_leaves = leave_type.employee_available_leave.all()
        if not available_leaves.exists():
            print("No available leaves found.")
        for available_leave in available_leaves:
            reset_date = available_leave.reset_date
            expired_date = available_leave.expired_date
            print(f"Checking leave reset for employee {available_leave.employee_id} with reset date {reset_date}")  # ✅ Debugging
            if reset_date == today_date:
                print(f"Resetting leave for {available_leave.employee_id} on {today_date}")  # ✅ Debugging
                available_leave.update_carryforward()
                # new_reset_date = available_leave.set_reset_date(assigned_date=today_date,available_leave = available_leave)
                new_reset_date = available_leave.set_reset_date(
                    assigned_date=today_date, available_leave=available_leave
                )
                available_leave.reset_date = new_reset_date
                available_leave.period_leaves_taken = 0
                available_leave.save()
            if expired_date == today_date:
                new_expired_date = available_leave.set_expired_date(
                    available_leave=available_leave, assigned_date=today_date
                )
                available_leave.expired_date = new_expired_date
                available_leave.save()
            else:
                 print(f"No reset required for {available_leave.employee_id}")  # ✅ Debugging

scheduler = BackgroundScheduler()
if not scheduler.running:
    scheduler.add_job(leave_reset, "interval", minutes=1)
    scheduler.start()
    print("Scheduler started...")

