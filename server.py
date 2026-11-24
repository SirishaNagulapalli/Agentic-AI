from mcp.server.fastmcp import FastMCP
from typing import Annotated, Dict, List, Optional
from pydantic import Field
from hrms import *
from utils import seed_services
from emails import EmailSender
import os
from dotenv import load_dotenv  

load_dotenv() # Load environment variables from .env file

email_sender = EmailSender(
        smtp_server="smtp.gmail.com",
        port=587,
        username=os.getenv("CB_EMAIL"),
        password=os.getenv("CB_EMAIL_PWD"),
        use_tls=True
    )


mcp = FastMCP("hr-assist")

employee_manager = EmployeeManager()
leave_manager = LeaveManager()
meeting_manager = MeetingManager()
ticket_manager = TicketManager()

seed_services(employee_manager, leave_manager, meeting_manager, ticket_manager)

@mcp.tool()
def add_employee(
    emp_name: Annotated[str, Field(description="Full name of the new employee")],
    email: Annotated[str, Field(description="Employee's email address")],
    manager_id: Annotated[Optional[str], Field(description="Employee ID of the manager. Leave empty if none.")] = None,
) -> str:
    """Add a new employee to the HRMS system. The employee ID is generated automatically.
    Returns a confirmation message."""
    emp = EmployeeCreate(
        emp_id=employee_manager.get_next_emp_id(),
        name=emp_name,
        manager_id=manager_id,
        email=email,
    )
    employee_manager.add_employee(emp)
    return f"Employee {emp_name} added successfully."


@mcp.tool()
def get_employee_details(
    name: Annotated[str, Field(description="Full name of the employee to look up")],
) -> Dict[str, str]:
    """Look up an employee by name and return their details, including employee ID and manager ID.
    Uses the first match if several employees share the name."""
    matches = employee_manager.search_employee_by_name(name)
    if not matches:
        raise ValueError(f"No employee found with name '{name}'.")
    return employee_manager.get_employee_details(matches[0])


@mcp.tool()
def send_email(
    to_emails: Annotated[List[str], Field(description="Recipient email addresses")],
    subject: Annotated[str, Field(description="Email subject line")],
    body: Annotated[str, Field(description="Email body text")],
    html: Annotated[bool, Field(description="Set true if the body is HTML")] = False,
) -> str:
    """Send an email to one or more recipients from the HR assistant's mailbox."""
    email_sender.send_email(subject, body, to_emails, from_email=email_sender.username, html=html)
    return "Email sent successfully."

@mcp.tool()
def schedule_meeting(employee_id: str, meeting_datetime: str, topic: str) -> str:
    """Schedule a meeting for an employee at a specified datetime with a given topic."""
    meeting_req = MeetingCreate(
        emp_id=employee_id, 
        meeting_dt=meeting_datetime, 
        topic=topic
    )
    return meeting_manager.schedule_meeting(meeting_req)

@mcp.prompt()
def onboard_new_employee(employee_name: str, manager_name: str) -> str:
    return (
        f"Onboard a new employee named {employee_name} reporting to {manager_name}.\n"
        "Steps:\n"
        f"1. Call get_employee_details for '{manager_name}' to get the manager's employee ID and email.\n"
        f"2. Call add_employee with the name, the email {employee_name.lower().replace(' ', '.')}@gmail.com, "
        "and the manager's ID.\n"
        "3. Call send_email to the new employee with a welcome message and next steps.\n"
        "4. Call send_email to the manager announcing the new hire.\n"
        "5. Raise tickets for a laptop, ID card and other equipment (once a ticket tool exists)."
        "6. Schedule an onboarding meeting with the new employee and manager (once a meeting tool exists)."
    )

if __name__ == "__main__":
    mcp.run(transport = "stdio")
