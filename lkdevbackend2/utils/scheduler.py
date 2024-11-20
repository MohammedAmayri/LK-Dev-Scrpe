from apscheduler.schedulers.blocking import BlockingScheduler
from main import fetch_and_update_menus

def schedule_tasks():
    scheduler = BlockingScheduler()

    # Schedule tasks based on menuPeriodicity
    # For simplicity, we'll assume daily updates at 9 AM
    scheduler.add_job(fetch_and_update_menus, 'cron', hour=9)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    schedule_tasks()
