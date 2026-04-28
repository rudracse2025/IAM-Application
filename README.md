# 🏢 Enterprise Identity & Access Management (IAM) Application

A **secure, role-based employee onboarding platform** that automates the entire process from HR request submission through IT provisioning and dual-approval workflows.

> 📖 **For comprehensive documentation, see [README_COMPREHENSIVE.md](README_COMPREHENSIVE.md)**

## 🚀 Quick Start

### Key Features
✅ **Role-Based Access Control** - HR, IT Admin, CISO, Management roles  
✅ **4-Stage Onboarding Workflow** - Request → Provision → Dual Approval → Access  
✅ **Multi-Tenant Domain Isolation** - Complete data separation by organization  
✅ **Real-Time Dashboards** - Role-specific views and activity feeds  
✅ **Comprehensive Audit Trail** - Full compliance logging  
✅ **Secure & Compliant** - Password hashing, session management, CSRF protection  
✅ **Responsive Design** - Works on desktop, tablet, mobile

## 🏗️ Architecture

**4-Stage Workflow:**
1. 📝 HR submits employee request (PENDING_IT)
2. ⚙️ IT Admin provisions account/resources (PENDING_APPROVAL)
3. ✅ CISO & Management dual review and approval (APPROVED/REJECTED)
4. 🎉 Access provisioned, employee ready

**Data Security:**
- Domain-based multi-tenancy: Users see only their organization's data
- Role & domain dual enforcement: Access control at both levels
- Database-level filtering: Every query respects domain boundaries
- Complete audit trail: All actions logged with timestamp and actor

## 💻 Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12+, Flask 3.0.3 |
| Authentication | Flask-Login 0.6.3 |
| Database | SQLAlchemy 3.1.1 (MySQL/SQLite) |
| Security | Werkzeug 3.0.3 |
| Server | Gunicorn WSGI |
| Frontend | Jinja2, HTML5, CSS3 |

## 👥 User Roles

| Role | Responsibilities | Key Actions |
|------|------------------|------------|
| **HR** | Manage onboarding requests | Submit requests, track progress, view history |
| **IT Admin** | Provision user accounts | Configure licenses, security groups, routes to approval |
| **CISO** | Security review & approval | Verify compliance, approve/reject, audit access |
| **Management** | Business approval | Verify budget, business justification, approval decision |

## 🔐 Security & Multi-Tenancy

**Complete Domain Isolation:**
- ✅ User A from Domain A cannot see User B from Domain B
- ✅ Even IT Admin cannot cross domains
- ✅ Database queries enforce domain filters
- ✅ Audit trails isolated by domain
- ✅ CISO/Management approvals restricted to domain

## 🚀 Getting Started

### Installation

```bash
# Clone repository
git clone https://github.com/rudracse2025/IAM-Application.git
cd IAM-Application

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
SECRET_KEY=change-this-secret-key
DATABASE_URL=sqlite:///iam_app.db
EMPLOYEE_EMAIL_DOMAIN=bluvium.com
FLASK_ENV=development
EOF

# Initialize database
python3 -c "
from app import create_app
app = create_app()
with app.app_context():
    from models import db
    db.create_all()
    print('✅ Database initialized!')
"
```

### Running the Application

```bash
# Development server
python app.py

# Access at: http://127.0.0.1:5000
```

### Creating Test User

```python
from app import create_app
from models import db, User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    user = User(
        email="hr@bluvium.com",
        password_hash=generate_password_hash("password123"),
        role="HR",
        domain="bluvium.com"
    )
    db.session.add(user)
    db.session.commit()
    print("✅ User created: hr@bluvium.com / password123")
```

## 🗺️ Key Routes

| Route | Method | Access | Purpose |
|-------|--------|--------|---------|
| `/` | GET | Public | Landing page |
| `/features` | GET | Public | Feature documentation |
| `/signup` | POST | Public | Register account |
| `/login` | POST | Public | Login |
| `/dashboard` | GET | Authenticated | Role-specific dashboard |
| `/hr/requests/new` | POST | HR | Create new request |
| `/it/provision/<id>` | POST | IT Admin | Submit provisioning |
| `/approvals` | GET | CISO/Mgmt | View pending approvals |
| `/approvals/<id>/approve` | POST | CISO/Mgmt | Submit approval decision |
| `/status/<id>` | GET | Authenticated | View request status |
| `/history` | GET | Authenticated | View history |

## 🗄️ Data Model

**Core Tables:**
- `user` - Users with role and domain
- `employee_request` - Onboarding requests
- `provisioning` - IT account configuration
- `approval` - CISO & Management decisions
- `request_audit` - Complete action audit trail

**Key Features:**
- Domain field on all tables for multi-tenancy
- Foreign keys for referential integrity
- Audit trail for compliance

## 🔧 Configuration

**Database Options:**

Development (SQLite):
```bash
export DATABASE_URL=sqlite:///iam_app.db
```

Production (MySQL):
```bash
export DATABASE_URL=mysql+pymysql://user:pass@host:3306/iam_app
```

**Environment Variables:**
- `SECRET_KEY` - Flask secret (change for production!)
- `DATABASE_URL` - Database connection string
- `EMPLOYEE_EMAIL_DOMAIN` - For generated email addresses
- `FLASK_ENV` - `development` or `production`
- `FLASK_DEBUG` - Enable debug mode (dev only)

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

## 📚 Documentation

For detailed documentation, see:
- **[README_COMPREHENSIVE.md](README_COMPREHENSIVE.md)** - Full guides, examples, and architecture
- **`/features`** page in the application - Interactive feature overview
- **`/dashboard`** - Role-specific interface after login

The comprehensive guide includes:
- ✅ Complete architecture diagrams
- ✅ Detailed end-to-end workflow
- ✅ Role-based usage guides
- ✅ Database schema documentation
- ✅ Deployment instructions
- ✅ API endpoint reference
- ✅ Troubleshooting guide
- ✅ Performance optimization tips

## 🚀 Production Deployment

### Using Gunicorn

```bash
pip install gunicorn
export DATABASE_URL=mysql+pymysql://user:pass@host:3306/db
export SECRET_KEY=$(openssl rand -hex 32)
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Using Docker

```bash
docker build -t iam-app .
docker run -p 8000:8000 \
  -e DATABASE_URL=mysql+pymysql://... \
  -e SECRET_KEY=your-secret-key \
  iam-app
```

### With Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 🐛 Troubleshooting

**Q: Module not found error?**  
A: Install dependencies: `pip install -r requirements.txt`

**Q: Database connection error?**  
A: Check DATABASE_URL env var and MySQL server is running

**Q: TemplateNotFound error?**  
A: Ensure running from project root: `cd /workspaces/IAM-Application`

**Q: Login fails?**  
A: Create a user first (see "Creating Test User" section above)

See [README_COMPREHENSIVE.md](README_COMPREHENSIVE.md#-troubleshooting) for more solutions.

## 💡 Example Workflow

```
1. HR Sign Up
   → Email: hr@company.com
   → Password: secure123
   → Role: HR
   → Domain: company.com

2. HR Login & Submit Request
   → Employee: John Smith
   → Email: john.smith@company.com
   → Job: Engineer
   → Status: PENDING_IT

3. IT Admin Reviews & Provisions
   → Create user ID: john.smith
   → Assign license: M365 E5
   → Configure groups: Engineering, Remote
   → Status: PENDING_APPROVAL

4. CISO Reviews Security
   → Check compliance
   → Verify access levels
   → Decision: APPROVED

5. Management Reviews Budget
   → Check business justification
   → Verify cost
   → Decision: APPROVED

6. ✅ Employee Access Granted
   → User account activated
   → All resources available
   → Status: APPROVED
```

## 📊 Features Highlights

| Feature | Benefit |
|---------|---------|
| 🔐 Role-Based Access | Granular control per position |
| 📋 4-Stage Workflow | Automated, organized process |
| 🏢 Domain Isolation | Complete multi-tenant separation |
| 📊 Real-Time Dashboard | See what matters to your role |
| ✅ Dual Approval | Security & Business review |
| 📝 Audit Trail | Full compliance logging |
| 📱 Responsive UI | Works everywhere |
| 🌐 Multi-Organization | Support multiple companies |

## 🔒 Security Features

- ✅ Werkzeug password hashing (PBKDF2)
- ✅ Flask-Login session management
- ✅ CSRF protection on forms
- ✅ Database-level access control
- ✅ Domain-based data isolation
- ✅ Complete audit logging
- ✅ Role & domain dual enforcement

## 📞 Support

- 📖 **Documentation**: See [README_COMPREHENSIVE.md](README_COMPREHENSIVE.md)
- 🐛 **Issues**: Report on [GitHub Issues](https://github.com/rudracse2025/IAM-Application/issues)
- 💬 **Features**: Visit `/features` page in application
- 📧 **Contact**: developer@companyiam.com

## 🤝 Contributing

Contributions welcome! Please:
1. Fork repository
2. Create feature branch
3. Make changes following PEP 8
4. Submit pull request

## 📄 License

MIT License - See LICENSE file for details

## ✨ Credits

Built with:
- 🐍 **Python** & **Flask** - Web framework
- 🗄️ **SQLAlchemy** - ORM
- 🔐 **Werkzeug** - Security utilities
- 👤 **Flask-Login** - Authentication

---

**Version:** 1.0.0 | **Status:** ✅ Production Ready | **Last Updated:** April 28, 2026

> 📖 **New to the application?** Start with the [comprehensive documentation](README_COMPREHENSIVE.md) for detailed guides!
