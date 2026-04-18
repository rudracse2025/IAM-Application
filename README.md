### **1. Project Purpose**
The **IAM Application** is an **Identity and Access Management system** that manages the complete employee onboarding and access provisioning workflow. It streamlines how companies grant system access to new employees through a multi-role approval process.

---

### **2. Core Components**

#### **A. Technology Stack**
- **Backend**: Python Flask (web framework)
- **Database**: MySQL (user data storage)
- **Frontend**: HTML/CSS/Jinja2 templates
- **Authentication**: Flask-Login with password hashing (Werkzeug)
- **ORM**: SQLAlchemy (database management)

---

### **3. User Roles & Responsibilities**

The application implements **4 distinct user roles**, each with specific permissions:

| Role | Responsibility | Workflow Step |
|------|-----------------|---------------|
| **HR** | Creates employee access requests | Step 1: Submits new requests |
| **IT Admin** | Provisions system access & resources | Step 2: Configures IT setup |
| **CISO** | Security approval authority | Step 3: Reviews security |
| **Management** | Business approval authority | Step 3: Reviews business need |

---

### **4. Database Models**

The app uses **4 main database tables**:

```
User
├── id (Primary Key)
├── email (unique identifier)
├── password_hash (encrypted password)
├── role (HR, IT_ADMIN, CISO, MANAGEMENT)
├── domain (company/organization domain)
└── created_at (timestamp)

EmployeeRequest
├── id (Primary Key)
├── domain (which domain/company)
├── requested_by (HR user ID - foreign key to User)
├── employee_name (new employee name)
├── employee_email (new employee email)
├── status (PENDING_IT → PENDING_APPROVAL → APPROVED/REJECTED)
└── created_at (timestamp)

Provisioning
├── id (Primary Key)
├── request_id (links to EmployeeRequest)
├── created_by (IT Admin user ID)
├── it_user_id (system username assigned)
├── license_type (software licenses granted)
├── security_groups (access groups assigned)
└── created_at (timestamp)

Approval
├── id (Primary Key)
├── request_id (links to EmployeeRequest)
├── approver_id (CISO or Management user ID)
├── role (who approved: CISO or MANAGEMENT)
├── status (APPROVED or REJECTED)
└── created_at (timestamp)
```

---

### **5. Application Workflow - Request Lifecycle**

```
┌─────────────────────────────────────────────────────────────────┐
│                    EMPLOYEE ACCESS REQUEST FLOW                   │
└─────────────────────────────────────────────────────────────────┘

     HR EMPLOYEE                IT ADMIN              APPROVERS
        (Step 1)                  (Step 2)           (Step 3)
          ▼                         ▼                  ▼

    1. HR creates                2. IT provisions   3. CISO & Management
       access request               system access       approve/reject
       - Employee name
       - Employee email
       Status: PENDING_IT
            │
            │ (HR submits)
            ▼
    Request visible in
    IT Admin's dashboard
            │
            │ (IT configures)
            ▼
       IT fills in:
       - System username
       - License type
       - Security groups
       Status: PENDING_APPROVAL
            │
            │ (IT submits)
            ▼
    Request visible to
    CISO & Management
            │
            ├──────────────────┐
            │ (Both approve)   │ (Either rejects)
            ▼                  ▼
    Status: APPROVED    Status: REJECTED
    (Access granted)    (Request denied)
```

---

### **6. Key Features**

#### **A. Authentication & Security**
- ✅ User registration with email validation
- ✅ Passwords hashed using Werkzeug security
- ✅ Session-based login management (Flask-Login)
- ✅ Role-based access control (RBAC)
- ✅ Unauthorized access returns 403 Forbidden error

#### **B. Request Management**
- ✅ HR creates new employee requests
- ✅ Prevents duplicate email registrations
- ✅ Tracks request status through workflow stages
- ✅ Domain-based isolation (multi-tenant support)

#### **C. Role-Based Dashboard**
Each role sees different requests:
- **HR**: Only their own submitted requests
- **IT Admin**: Requests pending IT provisioning
- **CISO/Management**: Requests pending approval

#### **D. Approval Logic**
- ✅ Both CISO **AND** Management must approve
- ✅ If either rejects, entire request is rejected
- ✅ Approvers can change their decision
- ✅ Only one approval per person per request

#### **E. User Experience**
- ✅ Flash messages for success/error feedback
- �� Automatic redirection after actions
- ✅ Request status tracking page
- ✅ Responsive navigation bar

---

### **7. API Routes (Endpoints)**

| Route | Method | Role Requirement | Function |
|-------|--------|------------------|----------|
| `/` | GET | Public | Home page |
| `/signup` | GET/POST | Public | User registration |
| `/login` | GET/POST | Public | User authentication |
| `/logout` | GET | Authenticated | End session |
| `/dashboard` | GET | Authenticated | Role-specific view |
| `/hr/requests/new` | GET/POST | HR | Create new request |
| `/it/provision/<id>` | GET/POST | IT Admin | Configure access |
| `/approvals` | GET | CISO/Management | View pending approvals |
| `/approvals/<id>/approve` | POST | CISO/Management | Approve/reject request |
| `/status/<id>` | GET | Authenticated | View request status |

---

### **8. Configuration**

The app uses environment variables (via `.env` file):

```env
SECRET_KEY=your-secret-key          # Flask session encryption
DATABASE_URL=mysql+pymysql://...    # MySQL connection string
```

Default MySQL setup:
- **Host**: localhost
- **Port**: 3306
- **Database**: iam_app
- **User**: iam_user
- **Password**: iam_pass

---

### **9. Security Features**

✅ **Password Hashing**: Werkzeug hashes passwords (not stored in plaintext)
✅ **Session Management**: Flask-Login manages secure sessions
✅ **Role-Based Access**: Decorators enforce role requirements
✅ **CSRF Protection**: Form data validated
✅ **Database Isolation**: Queries filtered by user domain
✅ **Request Validation**: All inputs checked before processing

---

### **10. Use Case Scenario**

**Scenario: New employee "john.doe@company.com" needs access**

```
Day 1 - HR Submits Request
├─ HR logs in and navigates to "Create New Request"
├─ Enters: Name="John Doe", Email="john.doe@company.com"
├─ Request created with status: PENDING_IT
└─ Request appears in IT Admin's dashboard

Day 2 - IT Admin Provisions
├─ IT Admin logs in and views pending requests
├─ Clicks on John's request
├─ Fills in: Username="jdoe", License="Microsoft Office", Groups="Developers"
├─ Submits provisioning
└─ Request status changes to: PENDING_APPROVAL

Day 3 - Approvals
├─ CISO logs in and approves (security check OK)
├─ Management logs in and approves (business need confirmed)
├─ Both approved → Request status becomes: APPROVED
└─ John Doe now has full system access!

Alternative (Day 3 - Rejection):
├─ CISO reviews and finds security issue
├─ CISO rejects the request
└─ Request status becomes: REJECTED (John doesn't get access)
```

---

### **11. Current Limitations & Future Improvements**

⚠️ **Current Limitations**:
- No audit logging for compliance tracking
- No email notifications to users
- No bulk provisioning support
- Limited error handling
- No API documentation

✨ **Suggested Improvements**:
- Add email notifications at each stage
- Implement API endpoints for integrations
- Add activity audit logs
- Support for approval workflows with deadlines
- Integration with Active Directory/LDAP
- Batch import of employee requests

---

### **Summary**

The **IAM Application** is a **multi-role, workflow-based access management system** that automates employee onboarding by routing requests through HR → IT Admin → Approvers. It ensures **secure, auditable access provisioning** through role-based controls and multi-approval requirements, making it ideal for mid-to-large organizations needing standardized access management processes.
