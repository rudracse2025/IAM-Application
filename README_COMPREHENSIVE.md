# 🏢 Enterprise Identity & Access Management (IAM) Application

A **secure, role-based employee onboarding platform** that automates the entire process from HR request submission through IT provisioning and dual-approval workflows. Built with Flask, SQLAlchemy, and modern security practices.

**Live Demo:** http://127.0.0.1:5000  
**Repository:** https://github.com/rudracse2025/IAM-Application

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Architecture](#architecture)
4. [Technology Stack](#technology-stack)
5. [User Roles & Workflows](#user-roles--workflows)
6. [End-to-End Process](#end-to-end-process)
7. [Security & Compliance](#security--compliance)
8. [Data Model](#data-model)
9. [Installation & Setup](#installation--setup)
10. [Running the Application](#running-the-application)
11. [Configuration](#configuration)
12. [API Routes](#api-routes)
13. [Usage Guide by Role](#usage-guide-by-role)
14. [Database Management](#database-management)
15. [Deployment](#deployment)
16. [Contributing](#contributing)

---

## 🎯 Overview

The IAM Application is an enterprise-grade **Identity and Access Management system** designed to streamline and secure the employee onboarding process. It implements a four-stage approval workflow with role-based access control, comprehensive audit trails, and complete data isolation by domain (multi-tenancy).

### Problem Solved
Organizations need a secure, auditable way to:
- ✅ Manage employee access requests
- ✅ Enforce dual approval (security + business) requirements
- ✅ Automate IT provisioning workflows
- ✅ Maintain complete audit trails for compliance
- ✅ Isolate data across multiple business units/domains

---

## 🚀 Key Features

### 🔐 Role-Based Access Control
- **4 Distinct User Roles**: HR, IT Admin, CISO, Management
- Role-specific dashboards with tailored workflows
- Granular permission controls at role and domain levels
- Automatic role-based data filtering

### 📋 Complete Onboarding Workflow
1. **HR Request Submission** - Create and track employee onboarding requests
2. **IT Provisioning** - Configure user accounts, licenses, and security groups
3. **Dual Security Approvals** - CISO reviews compliance; Management approves budget
4. **Access Provisioned** - Automatic employee account activation

### 🏢 Multi-Tenant Domain Isolation
- **Complete data segregation** by organization domain
- Users from Domain A **cannot see** users/requests from Domain B
- Database-level enforcement of tenant boundaries
- Shared infrastructure with isolated data (true SaaS model)

### 📊 Real-Time Dashboard & Monitoring
- **HR**: Submission shortcuts, request history, activity feed
- **IT Admin**: Provisioning queue, approval tracking, activity logs
- **CISO**: Pending approvals, security audit trail, compliance events
- **Management**: Business approval queue, SLA tracking, activity dashboard

### ✅ Comprehensive Audit Trail
- Every action logged with timestamp, actor, and details
- Event types: REQUEST_CREATED, REQUEST_PROVISIONED, APPROVAL_DECISION, REQUEST_APPROVED, REQUEST_REJECTED
- Full compliance reporting and historical analysis
- Isolated audit logs per domain

### 🔒 Security & Compliance
- Secure password hashing (Werkzeug)
- Session management with Flask-Login
- CSRF protection on forms
- Database-level access enforcement
- Complete activity audit logging
- Role-domain dual enforcement

### 📱 Responsive Design
- Works on desktop, tablet, and mobile
- Modern UI with gradients and animations
- Quick-action shortcuts for power users
- Error handling and user feedback

### 🌐 Multi-Organization Support
- Support for multiple business domains/organizations
- Each domain has independent users, requests, and approvals
- Shared infrastructure with complete data isolation

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│               Web Browser (User Interface)                   │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/HTTPS
┌─────────────────────▼───────────────────────────────────────┐
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Flask Web Application                   │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │  Route Handlers & Controllers                 │  │   │
│  │  │  - /                                           │  │   │
│  │  │  - /login, /signup, /logout                   │  │   │
│  │  │  - /dashboard                                 │  │   │
│  │  │  - /hr/requests/new                           │  │   │
│  │  │  - /it/provision/<id>                         │  │   │
│  │  │  - /approvals, /approvals/<id>/approve        │  │   │
│  │  │  - /status/<id>, /history, /features          │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                        │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │  Business Logic & Helper Functions            │  │   │
│  │  │  - build_dashboard_hero(role)                 │  │   │
│  │  │  - build_dashboard_actions(role)              │  │   │
│  │  │  - build_activity_feed(role, domain, user_id) │  │   │
│  │  │  - Workflow state management                  │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                        │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │  Authentication & Authorization               │  │   │
│  │  │  - Flask-Login session management             │  │   │
│  │  │  - Role & domain verification                 │  │   │
│  │  │  - Permission enforcement                     │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         SQLAlchemy ORM Layer                         │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │  Models (SQLAlchemy Declarative)              │  │   │
│  │  │  - User                                        │  │   │
│  │  │  - EmployeeRequest                            │  │   │
│  │  │  - Provisioning                               │  │   │
│  │  │  - Approval                                   │  │   │
│  │  │  - RequestAudit                               │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                        │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │  Query & Filter Operations                    │  │   │
│  │  │  - Domain-level filtering                     │  │   │
│  │  │  - Role-based access filtering                │  │   │
│  │  │  - Relationship loading & joins               │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────┬──────────────────────────────────────────┘
                  │ SQL Queries
┌─────────────────▼──────────────────────────────────────────┐
│         Database Layer (MySQL or SQLite)                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Tables (with domain isolation)                   │    │
│  │  ┌──────────────────────┐   ┌─────────────────┐  │    │
│  │  │ users                │   │ employee_       │  │    │
│  │  │                      │   │ requests        │  │    │
│  │  │ - id (PK)           │   │                 │  │    │
│  │  │ - email             │   │ - id (PK)       │  │    │
│  │  │ - role              │   │ - domain ⭐      │  │    │
│  │  │ - domain ⭐          │   │ - requested_by  │  │    │
│  │  │ - created_at        │   │ - status        │  │    │
│  │  └──────────────────────┘   │ - employee_*   │  │    │
│  │                             │ - created_at   │  │    │
│  │  ┌──────────────────────┐   └─────────────────┘  │    │
│  │  │  provisioning        │   ┌─────────────────┐  │    │
│  │  │                      │   │ approvals       │  │    │
│  │  │ - id (PK)           │   │                 │  │    │
│  │  │ - request_id (FK)   │   │ - id (PK)       │  │    │
│  │  │ - created_by        │   │ - request_id    │  │    │
│  │  │ - it_user_id        │   │ - approver_id   │  │    │
│  │  │ - license_type      │   │ - role          │  │    │
│  │  │ - security_groups   │   │ - status        │  │    │
│  │  │ - created_at        │   │ - created_at    │  │    │
│  │  └──────────────────────┘   └─────────────────┘  │    │
│  │                             ┌─────────────────┐  │    │
│  │                             │ request_audit   │  │    │
│  │                             │ (Audit Trail)   │  │    │
│  │                             │                 │  │    │
│  │                             │ - id (PK)       │  │    │
│  │                             │ - request_id    │  │    │
│  │                             │ - event_type    │  │    │
│  │                             │ - actor_id      │  │    │
│  │                             │ - actor_role    │  │    │
│  │                             │ - created_at    │  │    │
│  │                             └─────────────────┘  │    │
│  │                                                   │    │
│  │  ⭐ = Domain field (multi-tenancy enforcement)   │    │
│  └────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

---

## 💻 Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Backend** | Python | 3.12+ | Core application logic |
| **Web Framework** | Flask | 3.0.3 | HTTP request handling, routing |
| **Authentication** | Flask-Login | 0.6.3 | Session management, user auth |
| **ORM** | SQLAlchemy | 3.1.1 | Database abstraction layer |
| **Database Drivers** | PyMySQL | 1.1.1 | MySQL connectivity |
| **Security** | Werkzeug | 3.0.3 | Password hashing, utilities |
| **Environment** | python-dotenv | 1.0.1 | Configuration management |
| **Server** | Gunicorn | - | WSGI application server |
| **Frontend** | Jinja2, HTML, CSS | - | Templates and styling |
| **Database** | MySQL (prod), SQLite (dev) | 5.7+ | Data persistence |

### Frontend Stack
- **Template Engine**: Jinja2
- **Styling**: Custom CSS with responsive grid layout
- **Animations**: CSS transitions and hover effects
- **Design**: Modern gradients, cards, and shadows

---

## 👥 User Roles & Workflows

### 1. 👤 HR (Human Resources) Role

**Responsibilities:**
- Submit new employee onboarding requests
- Track request progress through workflow
- View all submitted requests and their status
- Quick actions for high-frequency tasks

**Dashboard Includes:**
- **Hero Banner**: "Submit employee requests for onboarding"
- **Quick Actions**: New Request, View Queue
- **Main Table**: All your submitted requests with status indicators
- **Spotlight Panel**: 4 most recent requests
- **Activity Feed**: Recent submissions and status updates

**Key Actions:**
- ✅ Create new employee onboarding request with employee details
- ✅ Submit request to IT for provisioning
- ✅ Track status through IT provisioning and dual approvals
- ✅ View history of all submitted requests

**Data Visibility:**
- Can see only requests submitted by themselves
- Can see all employees within their domain
- Cannot see requests from other domains

---

### 2. ⚙️ IT Admin (Information Technology) Role

**Responsibilities:**
- Review and provision user accounts
- Assign licenses and security groups
- Configure access controls
- Manage IT queue and track approvals
- Route provisioning to approvers

**Dashboard Includes:**
- **Hero Banner**: "Manage IT provisioning queue"
- **Quick Actions**: Provision New User, View Approvals
- **Main Table**: All pending provisioning requests
- **Spotlight Panel**: 4 most recent provisioned users
- **Activity Feed**: Provisioning completions and pending items

**Key Actions:**
- ✅ Review pending HR requests in provisioning queue
- ✅ Create user ID and email accounts
- ✅ Assign Microsoft 365 licenses (E3, E5, or Business Premium)
- ✅ Configure security group memberships
- ✅ Set password reset and MFA requirements
- ✅ Submit for dual approval from CISO and Management

**Data Visibility:**
- Can see all pending employee requests for their domain
- Can see provisioning details for all users
- Can see approval status
- Cannot see requests from other domains

---

### 3. 🔒 CISO (Chief Information Security Officer) Role

**Responsibilities:**
- Review access requests for security compliance
- Evaluate risk and enforce security policies
- Approve or reject requests based on security criteria
- Track and report on security decisions
- Monitor access compliance

**Dashboard Includes:**
- **Hero Banner**: "Review pending security approvals"
- **Quick Actions**: Review Approvals, View History
- **Main Table**: All pending requests requiring CISO approval
- **Spotlight Panel**: 4 most recent approval decisions
- **Activity Feed**: Recent approval decisions and security events

**Key Actions:**
- ✅ Review requests pending CISO approval
- ✅ Assess security risk and compliance impact
- ✅ Approve requests meeting security criteria
- ✅ Reject requests with security concerns
- ✅ Add security review remarks

**Data Visibility:**
- Can see all pending approvals for their domain
- Can see complete request details and provisioning configuration
- Can see approval decisions from other approvers
- Can see activity audit trail
- Cannot view requests/data from other domains

---

### 4. 📊 Management Role

**Responsibilities:**
- Review access requests from business perspective
- Verify business justification and budget allocation
- Approve or reject requests based on business criteria
- Track and report on business decisions
- Monitor approval SLAs

**Dashboard Includes:**
- **Hero Banner**: "Review pending business approvals"
- **Quick Actions**: Review Approvals, View Exceptions
- **Main Table**: All pending requests requiring Management approval
- **Spotlight Panel**: 4 most recent approval decisions
- **Activity Feed**: Recent approvals and budget impact

**Key Actions:**
- ✅ Review requests pending Management approval
- ✅ Verify business justification
- ✅ Check budgetary compliance
- ✅ Approve requests meeting business criteria
- ✅ Reject requests for business reasons
- ✅ Add management remarks

**Data Visibility:**
- Can see all pending approvals for their domain
- Can see complete request details and cost implications
- Can see approval decisions from CISO
- Can see activity audit trail
- Cannot view requests/data from other domains

---

## 📊 End-to-End Process

### Stage 1: HR Submits Request 📝
```
HR Department
    ↓
   [/hr/requests/new]
    ↓
 Enters Employee Details:
   • Name & Email
   • Job Title
   • Work Mode (Onsite/Hybrid/Remote)
   • License Type (M365 E3/E5/Business)
    ↓
 Request Created with Status: PENDING_IT
    ↓
 Automatically routed to IT Admin
```

**Request Status**: `PENDING_IT`

---

### Stage 2: IT Provisions Access ⚙️
```
IT Admin
    ↓
   [/it/provision/<request_id>]
    ↓
 Configure User Account:
   • Create user ID
   • Assign email account
   • Configure licenses
   • Set security groups
   • Configure MFA & password reset
    ↓
 Submit for Dual Approval
    ↓
 Request Status: PENDING_APPROVAL
    ↓
 Routed to CISO & Management (parallel)
```

**Request Status**: `PENDING_APPROVAL`

---

### Stage 3: Dual Security Approvals ✅🔐
```
CISO Review (Parallel)        Management Review (Parallel)
    ↓                              ↓
[/approvals]              [/approvals]
    ↓                              ↓
Security Assessment         Business Assessment
    ↓                              ↓
Approve/Reject             Approve/Reject
    ↓                              ↓
    └────────────┬─────────────────┘
                 ↓
        Both Must Approve:
        - CISO: ✅ APPROVED
        - Management: ✅ APPROVED
                 ↓
        Final Status: APPROVED
                 ↓
        Employee Access Granted ✅
```

**Possible Outcomes:**
- ✅ Both approve → **APPROVED** (access granted)
- ❌ Either rejects → **REJECTED** (request denied)
- ⏳ Waiting for second approval

---

### Stage 4: Access Provisioned & Complete 🎉
```
System
    ↓
 User Account Fully Activated
 - Email account live
 - Licenses assigned
 - Security groups configured
 - MFA enabled
    ↓
 Notification sent to:
 - Employee
 - Manager
 - HR & IT
    ↓
 Employee Can Access:
 - Microsoft 365
 - Corporate VPN
 - Internal Systems
    ↓
 Status: APPROVED ✅
```

**Request Status**: `APPROVED`

---

## 🔐 Security & Compliance

### 🛡️ Authentication & Authorization
- **Secure Password Hashing**: Werkzeug PBKDF2 with salt
- **Session Management**: Flask-Login with secure cookies
- **Role-Based Access Control**: Four distinct roles with separate permissions
- **Domain-Based Isolation**: Users only see their domain's data
- **Dual-Layer Access**: Role AND domain must match for data access

### 🔒 Data Isolation & Multi-Tenancy

Every user, request, and record is tagged with a domain identifier. The system enforces complete data separation:

1. **Complete Data Isolation by Domain**
   - User A from Domain A cannot see any data from Domain B
   - Database queries filter by domain for every operation
   - All UI displays respect domain boundaries

2. **Role-Based Access ≠ Cross-Domain Access**
   - Even IT Admin cannot access other domains
   - CISO permissions apply only within their domain
   - Management approval restricted to domain

3. **Request Privacy & Confidentiality**
   - HR requests visible only to domain members
   - Employee information isolated by domain
   - No cross-domain employee searches

4. **Isolated Audit Trails**
   - Each domain has separate audit logs
   - Activity trails show only domain-specific events
   - Compliance reports per domain

5. **Database-Level Enforcement**
   - Domain filters applied at SQLAlchemy query level
   - Direct database access would require domain match
   - All WHERE clauses include domain condition

### 📋 Audit Trail & Compliance

Every action is logged to `RequestAudit` table:
- Event Type (REQUEST_CREATED, REQUEST_PROVISIONED, APPROVAL_DECISION, REQUEST_APPROVED, REQUEST_REJECTED)
- Actor ID, Email, Role
- Timestamp (UTC)
- Detailed description
- Domain identifier

**Use Cases:**
- Compliance reporting (SOC 2, ISO 27001)
- Forensic analysis
- User action history
- Approval tracking
- Security incident investigation

### ✅ Form Protection
- CSRF tokens on all POST forms
- Werkzeug security utilities
- Input validation on all fields

---

## 🗄️ Data Model

### User Model
```python
class User(UserMixin, db.Model):
    id: int (Primary Key)
    email: str (Unique)
    password_hash: str (Hashed with Werkzeug)
    role: str (HR | IT_ADMIN | CISO | MANAGEMENT)
    domain: str (Organization domain) ⭐
    created_at: datetime
```

### EmployeeRequest Model
```python
class EmployeeRequest(db.Model):
    id: int (Primary Key)
    domain: str (Organization domain) ⭐
    requested_by: int (FK → User.id)
    first_name: str
    middle_name: str
    last_name: str
    employee_name: str
    employee_email: str
    gender: str (Male | Female | Other | Prefer not to say)
    job_title: str
    work_mode: str (Onsite | Hybrid | Remote)
    work_location: str
    company_email: str (Auto-generated)
    status: str (PENDING_IT | PENDING_APPROVAL | APPROVED | REJECTED)
    created_at: datetime
```

### Provisioning Model
```python
class Provisioning(db.Model):
    id: int (Primary Key)
    request_id: int (FK → EmployeeRequest.id)
    created_by: int (FK → User.id, IT Admin)
    it_user_id: str (e.g., "john.doe")
    license_type: str (M365 Business Premium | M365 E3 | M365 E5)
    security_groups: str (e.g., "Sales,Engineer,Remote")
    assign_license: bool
    password_reset_required: bool
    block_user: bool
    mfa_reset_required: bool
    mailbox_creation_required: bool
    account_access_action: str (NONE | ENABLE | DISABLE)
    created_at: datetime
```

### Approval Model
```python
class Approval(db.Model):
    id: int (Primary Key)
    request_id: int (FK → EmployeeRequest.id)
    approver_id: int (FK → User.id)
    role: str (CISO | MANAGEMENT)
    status: str (PENDING | APPROVED | REJECTED)
    remarks: str (Optional decision notes)
    created_at: datetime
```

### RequestAudit Model (Audit Trail)
```python
class RequestAudit(db.Model):
    id: int (Primary Key)
    request_id: int (FK → EmployeeRequest.id)
    event_type: str (REQUEST_CREATED | REQUEST_PROVISIONED | 
                     APPROVAL_DECISION | REQUEST_APPROVED | 
                     REQUEST_REJECTED)
    actor_id: int (FK → User.id)
    actor_email: str
    actor_role: str (HR | IT_ADMIN | CISO | MANAGEMENT)
    details: str (Event description)
    created_at: datetime
```

### Relationships
```
User ──── (1:N) ──── EmployeeRequest (requested_by)
User ──── (1:N) ──── Provisioning (created_by)
User ──── (1:N) ──── Approval (approver_id)
User ──── (1:N) ──── RequestAudit (actor_id)

EmployeeRequest ──── (1:1) ──── Provisioning
EmployeeRequest ──── (1:N) ──── Approval
EmployeeRequest ──── (1:N) ──── RequestAudit
```

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.12+
- MySQL 5.7+ (for production) OR SQLite (for development)
- Git
- pip (Python package manager)

### Step 1: Clone the Repository

```bash
git clone https://github.com/rudracse2025/IAM-Application.git
cd IAM-Application
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Using venv
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# OR using conda
conda create -n iam-app python=3.12
conda activate iam-app
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment

Create a `.env` file in the project root:

```env
# Secret key for Flask sessions (change this!)
SECRET_KEY=your-very-secret-key-change-this

# Database URL (choose one)
# For production MySQL:
DATABASE_URL=mysql+pymysql://iam_user:iam_pass@localhost:3306/iam_app

# For development SQLite:
DATABASE_URL=sqlite:///iam_app.db

# Employee email domain
EMPLOYEE_EMAIL_DOMAIN=bluvium.com

# Flask environment
FLASK_ENV=development
FLASK_DEBUG=True
```

### Step 5: Initialize Database

```bash
# Set environment variables
export FLASK_APP=app.py
export DATABASE_URL=sqlite:///iam_app.db

# Create tables
python3 -c "
from app import create_app
app = create_app()
with app.app_context():
    from models import db
    db.create_all()
    print('✅ Database initialized!')
"
```

---

## 🚀 Running the Application

### Development Server

```bash
# Using Flask built-in server
export FLASK_APP=app.py
export DATABASE_URL=sqlite:///iam_app.db
flask run

# OR using Python directly
python app.py
```

The application will be available at: **http://127.0.0.1:5000**

### Production Server (Using Gunicorn)

```bash
# Install Gunicorn (already in requirements.txt)
pip install gunicorn

# Run with Gunicorn
export DATABASE_URL=mysql+pymysql://iam_user:iam_pass@localhost:3306/iam_app
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Docker (Optional)

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```

```bash
docker build -t iam-app .
docker run -p 8000:8000 \
  -e DATABASE_URL=mysql+pymysql://... \
  -e SECRET_KEY=your-secret \
  iam-app
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ | - | Flask session secret (change for production!) |
| `DATABASE_URL` | ❌ | `mysql+pymysql://iam_user:iam_pass@localhost:3306/iam_app` | Database connection string |
| `EMPLOYEE_EMAIL_DOMAIN` | ❌ | `bluvium.com` | Domain for generated employee emails |
| `FLASK_ENV` | ❌ | `production` | `development` or `production` |
| `FLASK_DEBUG` | ❌ | `False` | Enable Flask debug mode (dev only) |
| `SQLALCHEMY_ECHO` | ❌ | `False` | Log SQL queries (debug mode) |

### Database Configuration

**Development (SQLite):**
```bash
export DATABASE_URL=sqlite:///iam_app.db
```

**Production (MySQL):**
```bash
export DATABASE_URL=mysql+pymysql://username:password@host:3306/database_name
```

### First Test Credentials

After initialization, you can create test users:

```python
from app import create_app
from models import db, User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    # Create HR user
    hr_user = User(
        email="hr@bluvium.com",
        password_hash=generate_password_hash("password123"),
        role="HR",
        domain="bluvium.com"
    )
    db.session.add(hr_user)
    
    # Create IT Admin
    it_user = User(
        email="it@bluvium.com",
        password_hash=generate_password_hash("password123"),
        role="IT_ADMIN",
        domain="bluvium.com"
    )
    db.session.add(it_user)
    
    db.session.commit()
    print("✅ Test users created!")
```

---

## 🔗 API Routes

### Public Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Landing page with feature overview |
| `/features` | GET | Detailed features, workflow, and security documentation |
| `/signup` | GET, POST | User registration form |
| `/login` | GET, POST | User login |

### Authenticated Routes

| Route | Method | Access | Purpose |
|-------|--------|--------|---------|
| `/dashboard` | GET | All roles | Role-specific dashboard |
| `/logout` | GET | All roles | Logout user |
| `/history` | GET | All roles | View request history |
| `/status/<request_id>` | GET | All roles | View individual request status |

### HR-Specific Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/hr/requests/new` | GET | Show new request form |
| `/hr/requests/new` | POST | Submit new employee request |

### IT Admin Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/it/provision/<request_id>` | GET | Show provisioning form |
| `/it/provision/<request_id>` | POST | Submit provisioning details |

### Approval Routes (CISO & Management)

| Route | Method | Purpose |
|-------|--------|---------|
| `/approvals` | GET | View pending approvals |
| `/approvals/<request_id>/approve` | POST | Submit approval decision |

---

## 📖 Usage Guide by Role

### 👤 For HR Users

**Login:**
1. Navigate to http://127.0.0.1:5000/login
2. Enter your email and password
3. Click "Sign In"

**Submit New Request:**
1. Click "Dashboard" from navbar
2. Click "New Request" button
3. Fill in employee details:
   - Employee Full Name
   - Email Address
   - Job Title
   - Work Mode (Onsite/Hybrid/Remote)
   - Microsoft 365 License Type
4. Click "Submit Request"
5. Request is automatically sent to IT

**Track Request:**
1. Go to Dashboard
2. View "My Requests" table
3. Click on any request to see status
4. Status will update as:
   - PENDING_IT → (IT provisioning)
   - PENDING_APPROVAL → (Awaiting CISO & Management)
   - APPROVED → (Complete!)
   - REJECTED → (Need to resubmit)

**View History:**
1. Click "History" from navbar
2. See all your past submissions and outcomes
3. Click any request for details

---

### ⚙️ For IT Admin Users

**Login:**
1. Navigate to http://127.0.0.1:5000/login
2. Enter IT Admin credentials
3. Click "Sign In"

**Review Provisioning Queue:**
1. Go to Dashboard
2. Scroll to "Pending Provisioning" section
3. See all requests from HR waiting for provisioning

**Provision User:**
1. Click on a request or "Provision Now" button
2. Fill in provisioning details:
   - User ID (e.g., "john.doe")
   - Password (auto-generated)
   - License Type confirmation
   - Security Groups (e.g., "Sales", "Remote Access")
   - MFA settings
   - Mailbox configuration
3. Click "Submit for Approval"
4. Request moves to approval stage (CISO + Management)

**Track Approvals:**
1. Go to Dashboard
2. See "Pending Approvals" section
3. Track CISO and Management responses
4. When both approve: Request status → APPROVED

---

### 🔒 For CISO Users

**Login:**
1. Navigate to http://127.0.0.1:5000/login
2. Enter CISO credentials
3. Click "Sign In"

**Review Pending Approvals:**
1. Go to Dashboard or click "Approvals"
2. See all requests awaiting CISO approval
3. Each shows employee details and IT provisioning config

**Review for Security Compliance:**
1. Click on a request
2. Review provisioning details:
   - License type (cost control)
   - Security group memberships
   - MFA enablement
   - Access controls
3. Assess security impact
4. Verify domain/business unit alignment

**Make Approval Decision:**
1. Click "Approve" or "Reject"
2. Optional: Add security remarks
3. Submit decision
4. Logged to audit trail

**View Audit Trail:**
1. Go to Dashboard
2. Scroll to "Recent Security Events"
3. See all recent approval decisions
4. Filter by event type or date

---

### 📊 For Management Users

**Login:**
1. Navigate to http://127.0.0.1:5000/login
2. Enter Management credentials
3. Click "Sign In"

**Review Pending Approvals:**
1. Go to Dashboard or click "Approvals"
2. See all requests awaiting Management approval
3. Employee details and IT provisioning shown

**Review for Business Compliance:**
1. Click on a request
2. Review details:
   - Employee role and job title
   - License tier and cost
   - Provisioning scope
3. Verify budget and business justification
4. Check if similar roles have same access

**Make Approval Decision:**
1. Click "Approve" or "Reject"
2. Optional: Add business remarks
3. Submit decision
4. If both CISO and Management approved → access granted automatically

**Approval SLA:**
- Requests should be reviewed within 48 hours
- Dashboard shows aging requests

---

## 🗄️ Database Management

### Creating Database (MySQL)

```bash
mysql -u root -p

CREATE DATABASE iam_app;
CREATE USER 'iam_user'@'localhost' IDENTIFIED BY 'iam_pass';
GRANT ALL PRIVILEGES ON iam_app.* TO 'iam_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Initialize Tables

```python
from app import create_app
from models import db

app = create_app()
with app.app_context():
    db.create_all()
    print("✅ All tables created successfully!")
```

### Reset Database (WARNING: Deletes all data)

```python
from app import create_app
from models import db

app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()
    print("✅ Database reset!")
```

### Export Data

```bash
# Export all data to CSV
mysqldump -u iam_user -p iam_app > backup_$(date +%Y%m%d).sql

# Or using Python
python3 scripts/export_data.py
```

### Backup & Restore

```bash
# Backup
mysqldump -u iam_user -p iam_app > iam_app_backup.sql

# Restore
mysql -u iam_user -p iam_app < iam_app_backup.sql
```

---

## 🚀 Deployment

### Heroku Deployment

```bash
# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Set environment variables
heroku config:set SECRET_KEY=your-secret-key
heroku config:set DATABASE_URL=mysql+pymysql://...

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

### AWS Deployment (EC2 + RDS)

```bash
# 1. Create EC2 instance
# 2. Create RDS MySQL database
# 3. SSH into EC2

ssh -i key.pem ec2-user@your-instance.amazonaws.com

# 4. Clone repo and setup
git clone https://github.com/rudracse2025/IAM-Application.git
cd IAM-Application

# 5. Setup environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Create .env with RDS credentials
echo "DATABASE_URL=mysql+pymysql://admin:password@your-rds-endpoint:3306/iam_app" >> .env
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env

# 7. Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:80 app:app
```

### Nginx Configuration (Reverse Proxy)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL/TLS with Let's Encrypt

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --nginx -d your-domain.com

# Auto-renewal
sudo certbot renew --dry-run
```

---

## 📝 Project Structure

```
IAM-Application/
│
├── app.py                          # Flask application factory & route handlers
├── models.py                       # SQLAlchemy ORM models
├── requirements.txt                # Python dependencies
├── README.md                       # Quick start guide
├── README_COMPREHENSIVE.md         # This comprehensive documentation
│
├── templates/                      # Jinja2 HTML templates
│   ├── base.html                  # Base layout with navbar
│   ├── index.html                 # Landing page
│   ├── features.html              # Features & workflow documentation
│   ├── login.html                 # User login form
│   ├── signup.html                # User registration form
│   ├── dashboard.html             # Role-specific dashboard
│   ├── hr_request.html            # HR new request form
│   ├── it_provision.html          # IT provisioning form
│   ├── approvals.html             # Approval queue view
│   ├── status.html                # Individual request status view
│   └── history.html               # Request history view
│
├── static/                        # Static files
│   ├── css/
│   │   └── style.css             # All CSS styling
│   └── images/
│       └── (application images)
│
├── instance/                      # Instance-specific files
│   └── iam_app.db                # SQLite database (dev only)
│
└── scripts/                       # Utility scripts (optional)
    ├── seed_database.py          # Create test data
    └── export_data.py            # Export database to CSV
```

---

## 🐛 Troubleshooting

### Issue: "No module named 'flask'"
**Solution:** Install requirements
```bash
pip install -r requirements.txt
```

### Issue: "DatabaseError: Could not connect to MySQL server"
**Solution:** Check credentials and connection
```bash
# Test MySQL connection
mysql -u iam_user -p -h localhost
# Use SQLite for dev
export DATABASE_URL=sqlite:///iam_app.db
```

### Issue: "TemplateNotFound: base.html"
**Solution:** Ensure you're running from project root
```bash
cd /workspaces/IAM-Application
export PYTHONPATH=/workspaces/IAM-Application
python app.py
```

### Issue: Tables not created
**Solution:** Initialize database
```python
from app import create_app
from models import db
app = create_app()
with app.app_context():
    db.create_all()
```

### Issue: Login fails
**Solution:** Create user first
```python
from app import create_app
from models import db, User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    user = User(
        email="test@bluvium.com",
        password_hash=generate_password_hash("password"),
        role="HR",
        domain="bluvium.com"
    )
    db.session.add(user)
    db.session.commit()
```

---

## 📊 Performance Considerations

### Database Indexing
```sql
-- Add indexes for frequently queried fields
CREATE INDEX idx_user_domain ON user(domain);
CREATE INDEX idx_employee_request_domain ON employee_request(domain);
CREATE INDEX idx_employee_request_status ON employee_request(status);
CREATE INDEX idx_approval_request_id ON approval(request_id);
CREATE INDEX idx_audit_request_id ON request_audit(request_id);
```

### Query Optimization
- Domain filters applied at ORM layer reduce data loads
- Use relationships efficiently to avoid N+1 queries
- Cache frequently accessed data (static content, role configs)

### Load Testing
```bash
# Using Apache Bench
ab -n 1000 -c 10 http://127.0.0.1:5000/

# Using Locust
pip install locust
locust -f locustfile.py
```

---

## 🔄 Contributing

We welcome contributions! Here's how:

### 1. Fork Repository
```bash
git clone https://github.com/your-username/IAM-Application.git
cd IAM-Application
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Follow PEP 8 style guide
- Add tests for new features
- Update documentation

### 3. Commit & Push
```bash
git add .
git commit -m "feat: Add your feature description"
git push origin feature/your-feature-name
```

### 4. Create Pull Request
- Open PR on GitHub
- Describe changes clearly
- Link related issues

### Code Style
```python
# Follow PEP 8
- 4 spaces indentation
- Max 79 characters per line
- Docstrings for all functions
- Type hints where possible
```

---

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 📞 Support & Contact

- **Issues**: Report on [GitHub Issues](https://github.com/rudracse2025/IAM-Application/issues)
- **Email**: developer@companyiam.com
- **Documentation**: See `/features` page in the application

---

## 🎉 Acknowledgments

- Built with **Flask** - The Python web framework
- **SQLAlchemy** - SQL toolkit and ORM
- **Flask-Login** - User session management
- **Werkzeug** - WSGI utilities and security
- Community contributors and testers

---

## 📚 Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Flask-Login Guide](https://flask-login.readthedocs.io/)
- [OWASP Security Guidelines](https://owasp.org/)
- [SOC 2 Compliance](https://www.aicpa.org/soc2/)

---

**Last Updated:** April 28, 2026  
**Version:** 1.0.0  
**Status:** ✅ Production Ready

---

Made with ❤️ by the IAM Application Team
