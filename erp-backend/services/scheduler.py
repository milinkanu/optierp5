import asyncio
import os
import logging
from datetime import date, datetime
from uuid import UUID
from sqlalchemy import text
from utils.db_invoice import engine
from services.recurring_invoice_service import trigger_invoice_generation, MOCK_RECURRING_PROFILES

logger = logging.getLogger("finops.scheduler")
logger.setLevel(logging.INFO)

scheduler_task = None
is_running = False

async def scheduler_loop():
    global is_running
    is_running = True
    logger.info("FOS Recurring Invoice Background Scheduler started.")
    
    while is_running:
        try:
            current_date = date.today()
            
            if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
                # Mock Mode
                due_profiles = []
                for profile_id, profile in MOCK_RECURRING_PROFILES.items():
                    if profile['status'] == 'active' and profile['next_run_date'] <= current_date:
                        due_profiles.append(profile)
                        
                for p in due_profiles:
                    try:
                        logger.info(f"Generating recurring invoice for profile {p['profile_name']} (MOCK MODE)")
                        trigger_invoice_generation(p['profile_id'], p['company_id'], p['created_by'], current_date)
                    except Exception as ex:
                        logger.error(f"Failed to generate recurring invoice for profile {p['profile_id']}: {str(ex)}")
            
            else:
                # Database Mode
                with engine.begin() as conn:
                    due = conn.execute(
                        text('SELECT profile_id, company_id, created_by, profile_name FROM recurring_invoice_profiles WHERE status = \'active\' AND next_run_date <= :current_date AND (end_date IS NULL OR end_date >= :current_date)'),
                        {'current_date': current_date}
                    ).fetchall()
                    
                    due_rows = [dict(r._mapping) if hasattr(r, '_mapping') else dict(r) for r in due]
                    
                for r in due_rows:
                    try:
                        logger.info(f"Generating recurring invoice for profile {r['profile_name']} (DATABASE MODE)")
                        trigger_invoice_generation(UUID(r['profile_id']), UUID(r['company_id']), UUID(r['created_by']), current_date)
                    except Exception as ex:
                        logger.error(f"Failed to generate recurring invoice for profile {r['profile_id']}: {str(ex)}")
                        
        except Exception as e:
            logger.error(f"Error in scheduler run: {str(e)}")
            
        # Run every 60 seconds (or faster in local testing if needed)
        await asyncio.sleep(60)

def start_scheduler():
    global scheduler_task
    if scheduler_task is None:
        scheduler_task = asyncio.create_task(scheduler_loop())

def stop_scheduler():
    global is_running, scheduler_task
    is_running = False
    if scheduler_task:
        scheduler_task.cancel()
        scheduler_task = None
    logger.info("FOS Recurring Invoice Background Scheduler stopped.")
