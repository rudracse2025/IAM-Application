# IAM Application

A Flask-based Identity and Access Management (IAM) workflow app for employee onboarding and access provisioning.

The system routes requests through HR, IT Admin, and business/security approvers with role-based access rules and status tracking.

## Features

- Role-based authentication for `HR`, `IT_ADMIN`, `CISO`, and `MANAGEMENT`
- Secure password hashing using Werkzeug
- Domain-based request isolation for multi-organization usage
- HR request creation for new employee onboarding
- IT provisioning stage with user ID, license, and security group assignment
- Dual-approval process (CISO + Management)
- Automatic final decision logic:
  - request becomes `APPROVED` when both CISO and Management approve
  - request becomes `REJECTED` if either approver rejects
- Per-role dashboard filtering (each role sees relevant work items)
- Individual request status view
- Flash-message feedback for user actions

## Tech Stack

- Backend: Python, Flask
- ORM: Flask-SQLAlchemy / SQLAlchemy
- Authentication: Flask-Login
- Password Security: Werkzeug
- Database Drivers: PyMySQL (for MySQL), SQLite (optional for local/dev)
- Templates/UI: Jinja2, HTML, CSS
- Env Management: python-dotenv
- Production Server Option: Gunicorn

## User Roles and Flow

1. HR submits a new employee access request (`PENDING_IT`)
2. IT Admin provisions the account/resources (`PENDING_APPROVAL`)
3. CISO and Management review and approve/reject
4. Final state becomes `APPROVED` or `REJECTED`

## Data Model

The application includes these core models:

- `User`: login identity, role, domain
- `EmployeeRequest`: onboarding request and current status
- `Provisioning`: IT provisioning details linked to a request
- `Approval`: approver decision records per request

## Routes (Key Endpoints)

| Route | Method(s) | Access | Purpose |
|---|---|---|---|
| `/` | GET | Public | Landing page |
| `/signup` | GET, POST | Public | Register user |
| `/login` | GET, POST | Public | Authenticate user |
| `/logout` | GET | Logged-in users | Logout |
| `/dashboard` | GET | Logged-in users | Role-specific dashboard |
| `/hr/requests/new` | GET, POST | HR | Create employee request |
| `/it/provision/<request_id>` | GET, POST | IT Admin | Submit provisioning details |
| `/approvals` | GET | CISO, Management | View pending approvals |
| `/approvals/<request_id>/approve` | POST | CISO, Management | Save decision |
| `/status/<request_id>` | GET | Logged-in users | View request status |

## Project Structure

```text
IAM-Application/
├── app.py
├── models.py
├── requirements.txt
├── templates/
├── static/
└── instance/
```

## Setup and Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file in the project root:

```env
SECRET_KEY=change-this-secret
DATABASE_URL=mysql+pymysql://iam_user:iam_pass@localhost:3306/iam_app
```

Notes:
- If `DATABASE_URL` is not set, the app defaults to MySQL at `mysql+pymysql://iam_user:iam_pass@localhost:3306/iam_app`
- For quick local development without MySQL, you can run with SQLite:

```bash
DATABASE_URL=sqlite:///iam_app.db python3 app.py
```

### 3. Start the app

```bash
python3 app.py
```

The app runs at `http://127.0.0.1:5000` in development mode.

## Security and Access Control

- Passwords are stored as hashes, not plaintext
- Route-level role checks enforce least-privilege access
- Requests are filtered by user domain for tenant separation
- Unauthorized role access returns `403`

## Current Limitations

- No audit trail/event log
- No email notifications for workflow transitions
- No bulk request operations
- No REST API layer (HTML form workflow only)

## Future Enhancements

- Add audit logging for compliance and traceability
- Add email or chat notifications on status changes
- Add administrative reporting and analytics
- Integrate with AD/LDAP/SSO providers
- Add automated tests and CI pipeline
