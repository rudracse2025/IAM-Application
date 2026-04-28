import os
import re
import csv
from io import StringIO
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, request, flash, abort, Response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect, text
from dotenv import load_dotenv

from models import db, User, EmployeeRequest, Provisioning, Approval, RequestAudit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

ROLE_HR = "HR"
ROLE_IT = "IT_ADMIN"
ROLE_CISO = "CISO"
ROLE_MGMT = "MANAGEMENT"

ROLE_LABELS = {
    ROLE_HR: "HR",
    ROLE_IT: "IT Admin",
    ROLE_CISO: "CISO",
    ROLE_MGMT: "Management",
}

GENDER_OPTIONS = ("Male", "Female", "Other", "Prefer not to say")
WORK_MODE_OPTIONS = ("Onsite", "Hybrid", "Remote")
LICENSE_OPTIONS = ("M365 Business Premium", "M365 E3", "M365 E5")
ACCOUNT_ACCESS_OPTIONS = ("NONE", "ENABLE", "DISABLE")

STATUS_PENDING_IT = "PENDING_IT"
STATUS_PENDING_APPROVAL = "PENDING_APPROVAL"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"

APPROVAL_PENDING = "PENDING"
APPROVAL_APPROVED = "APPROVED"
APPROVAL_REJECTED = "REJECTED"

OVERDUE_APPROVAL_HOURS = 48
AGING_REQUEST_DAYS = 3


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["EMPLOYEE_EMAIL_DOMAIN"] = os.getenv("EMPLOYEE_EMAIL_DOMAIN", "bluvium.com")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://iam_user:iam_pass@localhost:3306/iam_app",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    def normalize_email_part(value):
        return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())

    def build_company_email(first_name, last_name):
        first = normalize_email_part(first_name)
        last = normalize_email_part(last_name)
        if not first or not last:
            return None
        return f"{first}.{last}@{app.config['EMPLOYEE_EMAIL_DOMAIN']}"

    def sync_schema():
        inspector = inspect(db.engine)
        preparer = db.engine.dialect.identifier_preparer
        tables = (EmployeeRequest.__table__, Provisioning.__table__, Approval.__table__, RequestAudit.__table__)

        with db.engine.begin() as conn:
            for table in tables:
                existing_columns = {column["name"] for column in inspector.get_columns(table.name)}
                for column in table.columns:
                    if column.name in existing_columns:
                        continue
                    ddl = (
                        f"ALTER TABLE {preparer.quote(table.name)} "
                        f"ADD COLUMN {preparer.quote(column.name)} {column.type.compile(dialect=db.engine.dialect)}"
                    )
                    conn.execute(text(ddl))

    with app.app_context():
        db.create_all()
        sync_schema()

    def role_required(*roles):
        def decorator(func):
            def wrapper(*args, **kwargs):
                if current_user.role not in roles:
                    abort(403)
                return func(*args, **kwargs)
            wrapper.__name__ = func.__name__
            return wrapper
        return decorator

    def fetch_approval_map(request_ids):
        if not request_ids:
            return {}

        approval_rows = Approval.query.filter(Approval.request_id.in_(request_ids)).order_by(Approval.created_at.desc()).all()
        approval_map = {}

        for approval in approval_rows:
            role_bucket = approval_map.setdefault(
                approval.request_id,
                {
                    ROLE_CISO: APPROVAL_PENDING,
                    ROLE_MGMT: APPROVAL_PENDING,
                    "remarks": {ROLE_CISO: "", ROLE_MGMT: ""},
                },
            )
            if approval.role not in (ROLE_CISO, ROLE_MGMT):
                continue
            if role_bucket[approval.role] == APPROVAL_PENDING:
                role_bucket[approval.role] = approval.status
                role_bucket["remarks"][approval.role] = (approval.remarks or "").strip()

        return approval_map

    def build_tracking_entry(req, approval_map, provisioned_ids):
        approval_state = approval_map.get(
            req.id,
            {
                ROLE_CISO: APPROVAL_PENDING,
                ROLE_MGMT: APPROVAL_PENDING,
                "remarks": {ROLE_CISO: "", ROLE_MGMT: ""},
            },
        )
        ciso_state = approval_state.get(ROLE_CISO, APPROVAL_PENDING)
        mgmt_state = approval_state.get(ROLE_MGMT, APPROVAL_PENDING)
        rejected_by = None
        if ciso_state == APPROVAL_REJECTED:
            rejected_by = "CISO"
        elif mgmt_state == APPROVAL_REJECTED:
            rejected_by = "Management"

        it_done = req.id in provisioned_ids or req.status in (STATUS_PENDING_APPROVAL, STATUS_APPROVED, STATUS_REJECTED)

        if req.status == STATUS_PENDING_IT:
            pending_from = "IT Admin provisioning"
        elif req.status == STATUS_PENDING_APPROVAL:
            missing = []
            if ciso_state != APPROVAL_APPROVED:
                missing.append("CISO")
            if mgmt_state != APPROVAL_APPROVED:
                missing.append("Management")
            pending_from = " / ".join(missing) + " approval"
        elif req.status == STATUS_APPROVED:
            pending_from = "Completed"
        else:
            pending_from = f"Rejected by {rejected_by or 'Approver'}"

        def state_for_approval(approval_status):
            if approval_status == APPROVAL_APPROVED:
                return "done"
            if approval_status == APPROVAL_REJECTED:
                return "rejected"
            return "pending"

        steps = [
            {"label": "HR", "state": "done"},
            {"label": "IT", "state": "done" if it_done else "pending"},
            {"label": "CISO", "state": state_for_approval(ciso_state)},
            {"label": "Management", "state": state_for_approval(mgmt_state)},
            {
                "label": "Final",
                "state": "done" if req.status == STATUS_APPROVED else ("rejected" if req.status == STATUS_REJECTED else "pending"),
            },
        ]

        return {
            "pending_from": pending_from,
            "steps": steps,
            "ciso": ciso_state,
            "management": mgmt_state,
            "remarks": approval_state.get("remarks", {ROLE_CISO: "", ROLE_MGMT: ""}),
        }

    def build_tracking_map(requests):
        request_ids = [req.id for req in requests]
        approval_map = fetch_approval_map(request_ids)
        provisioned_ids = {
            row.request_id
            for row in db.session.query(Provisioning.request_id).filter(Provisioning.request_id.in_(request_ids)).all()
        } if request_ids else set()

        return {req.id: build_tracking_entry(req, approval_map, provisioned_ids) for req in requests}

    def build_dashboard_hero(role):
        if role == ROLE_HR:
            return {
                "eyebrow": "HR command center",
                "title": "Open onboarding requests faster and keep every handoff visible.",
                "subtitle": "Create requests, track the IT queue, and review the latest activity in one place.",
                "primary_label": "+ New employee request",
                "primary_href": url_for("hr_new_request"),
                "secondary_label": "View history",
                "secondary_href": url_for("history"),
            }

        if role == ROLE_IT:
            return {
                "eyebrow": "IT provisioning hub",
                "title": "Work your queue with a live provisioning log beside it.",
                "subtitle": "See pending tasks, audit events, and the requests waiting for approval without switching screens.",
                "primary_label": "Open queue",
                "primary_href": "#requests-table",
                "secondary_label": "View history",
                "secondary_href": url_for("history"),
            }

        if role == ROLE_CISO:
            return {
                "eyebrow": "Security approval console",
                "title": "Review decisions with the full approval trail in view.",
                "subtitle": "Monitor open approvals, previous decisions, and the latest audit entries for your domain.",
                "primary_label": "Pending approvals",
                "primary_href": url_for("approvals"),
                "secondary_label": "View history",
                "secondary_href": url_for("history"),
            }

        return {
            "eyebrow": "Management approval console",
            "title": "Stay on top of approvals, exceptions, and request aging.",
            "subtitle": "Use the dashboard to review the current queue and the decision log for your domain.",
            "primary_label": "Pending approvals",
            "primary_href": url_for("approvals"),
            "secondary_label": "View history",
            "secondary_href": url_for("history"),
        }

    def build_dashboard_actions(role):
        if role == ROLE_HR:
            return [
                {
                    "label": "Create employee request",
                    "description": "Kick off a new onboarding case with company email preview.",
                    "href": url_for("hr_new_request"),
                    "tone": "action-blue",
                },
                {
                    "label": "Review request history",
                    "description": "Filter previous HR submissions and export CSV if needed.",
                    "href": url_for("history"),
                    "tone": "action-slate",
                },
                {
                    "label": "Track pending approvals",
                    "description": "See which requests are waiting on IT, CISO, or Management.",
                    "href": "#requests-table",
                    "tone": "action-amber",
                },
            ]

        if role == ROLE_IT:
            return [
                {
                    "label": "Open provisioning queue",
                    "description": "Jump into the oldest IT requests first.",
                    "href": "#requests-table",
                    "tone": "action-blue",
                },
                {
                    "label": "View audit trail",
                    "description": "Inspect recent provisioning events and decision outcomes.",
                    "href": url_for("history"),
                    "tone": "action-slate",
                },
                {
                    "label": "Review escalations",
                    "description": "Spot requests that have already moved into approval.",
                    "href": url_for("approvals"),
                    "tone": "action-amber",
                },
            ]

        if role == ROLE_CISO:
            return [
                {
                    "label": "Approve pending items",
                    "description": "Work through requests that are waiting on your decision.",
                    "href": url_for("approvals"),
                    "tone": "action-rose",
                },
                {
                    "label": "Inspect approval logs",
                    "description": "See the latest approval decisions and remarks.",
                    "href": url_for("history"),
                    "tone": "action-slate",
                },
                {
                    "label": "Open status view",
                    "description": "Review the full workflow for any request in your domain.",
                    "href": url_for("dashboard") + "#requests-table",
                    "tone": "action-blue",
                },
            ]

        return [
            {
                "label": "Approve pending items",
                "description": "Clear the current domain queue and keep the workflow moving.",
                "href": url_for("approvals"),
                "tone": "action-green",
            },
            {
                "label": "Inspect decision history",
                "description": "Review previous approvals, rejections, and remarks.",
                "href": url_for("history"),
                "tone": "action-slate",
            },
            {
                "label": "Open request status board",
                "description": "Use the dashboard table to inspect request progress.",
                "href": "#requests-table",
                "tone": "action-blue",
            },
        ]

    def build_activity_feed(role, domain, user_id):
        query = db.session.query(RequestAudit, EmployeeRequest).join(
            EmployeeRequest,
            RequestAudit.request_id == EmployeeRequest.id,
        ).filter(EmployeeRequest.domain == domain)

        if role == ROLE_HR:
            query = query.filter(EmployeeRequest.requested_by == user_id)
            title = "HR activity feed"
            empty_message = "Your latest request submissions and workflow updates will appear here."
        elif role == ROLE_IT:
            title = "IT operations log"
            empty_message = "Provisioning and approval events for your domain will appear here."
        elif role == ROLE_CISO:
            title = "CISO approval log"
            empty_message = "Recent decisions and approval comments will appear here."
        else:
            title = "Management decision log"
            empty_message = "Recent approvals, rejections, and audit events will appear here."

        audits = query.order_by(RequestAudit.created_at.desc()).limit(8).all()

        event_meta = {
            "REQUEST_CREATED": ("Request created", "action-blue"),
            "REQUEST_PROVISIONED": ("Provisioning submitted", "action-amber"),
            "APPROVAL_DECISION": ("Approval decision", "action-rose"),
            "REQUEST_APPROVED": ("Request approved", "action-green"),
            "REQUEST_REJECTED": ("Request rejected", "action-rose"),
        }

        items = []
        for audit, req in audits:
            label, tone = event_meta.get(audit.event_type, (audit.event_type.replace("_", " ").title(), "action-slate"))
            items.append(
                {
                    "time": audit.created_at.strftime("%b %d, %H:%M") if audit.created_at else "-",
                    "label": label,
                    "tone": tone,
                    "employee": req.employee_name,
                    "activity": audit.details or "-",
                    "actor": audit.actor_role or "System",
                    "request_status": req.status,
                }
            )

        return {
            "title": title,
            "empty_message": empty_message,
            "entries": items,
        }

    def build_csv_response(filename, headers, rows):
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        content = buffer.getvalue()
        return Response(
            content,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    def create_audit_entry(request_item, event_type, details):
        db.session.add(
            RequestAudit(
                request_id=request_item.id,
                event_type=event_type,
                actor_id=current_user.id if current_user.is_authenticated else None,
                actor_email=current_user.email if current_user.is_authenticated else None,
                actor_role=current_user.role if current_user.is_authenticated else None,
                details=details,
                created_at=datetime.utcnow(),
            )
        )

    def parse_history_filters():
        start_date_raw = (request.args.get("start_date") or "").strip()
        end_date_raw = (request.args.get("end_date") or "").strip()
        status_filter = (request.args.get("status") or "").strip().upper()
        employee_filter = (request.args.get("employee") or "").strip().lower()

        start_date = None
        end_date = None
        try:
            if start_date_raw:
                start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()
        except ValueError:
            start_date_raw = ""
        try:
            if end_date_raw:
                end_date = datetime.strptime(end_date_raw, "%Y-%m-%d").date()
        except ValueError:
            end_date_raw = ""

        if status_filter and status_filter not in (STATUS_PENDING_IT, STATUS_PENDING_APPROVAL, STATUS_APPROVED, STATUS_REJECTED):
            status_filter = ""

        return {
            "start_date": start_date,
            "end_date": end_date,
            "status": status_filter,
            "employee": employee_filter,
            "start_date_raw": start_date_raw,
            "end_date_raw": end_date_raw,
            "employee_raw": (request.args.get("employee") or "").strip(),
        }

    def apply_history_filters(rows, filters):
        filtered = []
        for row in rows:
            row_date_value = row.get("date") or ""
            row_date = None
            try:
                row_date = datetime.strptime(row_date_value[:10], "%Y-%m-%d").date()
            except ValueError:
                row_date = None

            if filters["start_date"] and row_date and row_date < filters["start_date"]:
                continue
            if filters["end_date"] and row_date and row_date > filters["end_date"]:
                continue
            if filters["status"] and row.get("request_status") != filters["status"]:
                continue

            haystack = " ".join([
                row.get("employee", ""),
                row.get("personal_email", ""),
                row.get("company_email", ""),
            ]).lower()
            if filters["employee"] and filters["employee"] not in haystack:
                continue

            filtered.append(row)

        return filtered

    def build_dashboard_widgets(role, requests, tracking_map):
        now = datetime.utcnow()
        overdue_cutoff = now - timedelta(hours=OVERDUE_APPROVAL_HOURS)
        aging_cutoff = now - timedelta(days=AGING_REQUEST_DAYS)

        pending_it = [req for req in requests if req.status == STATUS_PENDING_IT]
        pending_approval = [req for req in requests if req.status == STATUS_PENDING_APPROVAL]
        overdue_pending_approval = [
            req for req in pending_approval if req.created_at and req.created_at <= overdue_cutoff
        ]
        aging_requests = [
            req for req in requests if req.status in (STATUS_PENDING_IT, STATUS_PENDING_APPROVAL) and req.created_at and req.created_at <= aging_cutoff
        ]

        if role == ROLE_HR:
            return [
                {"label": "Pending With IT", "value": len(pending_it), "tone": "metric-blue", "desc": "Requests waiting for IT provisioning"},
                {"label": "Pending Approval", "value": len(pending_approval), "tone": "metric-orange", "desc": "Requests waiting for CISO/Management"},
                {"label": "Overdue Approvals", "value": len(overdue_pending_approval), "tone": "metric-orange", "desc": f"Older than {OVERDUE_APPROVAL_HOURS} hours"},
                {"label": "Aging Requests", "value": len(aging_requests), "tone": "metric-blue", "desc": f"Older than {AGING_REQUEST_DAYS} days"},
            ]

        if role == ROLE_IT:
            domain_pending_approval = EmployeeRequest.query.filter_by(
                domain=current_user.domain,
                status=STATUS_PENDING_APPROVAL,
            ).all()
            overdue_domain_approvals = [
                req for req in domain_pending_approval if req.created_at and req.created_at <= overdue_cutoff
            ]
            aging_it_queue = [
                req for req in pending_it if req.created_at and req.created_at <= aging_cutoff
            ]
            return [
                {"label": "IT Queue", "value": len(pending_it), "tone": "metric-blue", "desc": "Pending provisioning tasks"},
                {"label": "Aging IT Queue", "value": len(aging_it_queue), "tone": "metric-orange", "desc": f"Older than {AGING_REQUEST_DAYS} days"},
                {"label": "Overdue Approvals", "value": len(overdue_domain_approvals), "tone": "metric-orange", "desc": f"Domain approvals older than {OVERDUE_APPROVAL_HOURS} hours"},
                {"label": "Provisioned Today", "value": Provisioning.query.filter(
                    Provisioning.created_by == current_user.id,
                    Provisioning.created_at >= datetime(now.year, now.month, now.day),
                ).count(), "tone": "metric-green", "desc": "Requests provisioned by you today"},
            ]

        my_pending = []
        my_overdue = []
        role_key = ROLE_CISO if role == ROLE_CISO else ROLE_MGMT
        for req in requests:
            tracking = tracking_map.get(req.id, {})
            if tracking.get(role_key) == APPROVAL_PENDING:
                my_pending.append(req)
                if req.created_at and req.created_at <= overdue_cutoff:
                    my_overdue.append(req)

        return [
            {"label": "Awaiting Your Approval", "value": len(my_pending), "tone": "metric-orange", "desc": "Pending at your level"},
            {"label": "Overdue For You", "value": len(my_overdue), "tone": "metric-orange", "desc": f"Older than {OVERDUE_APPROVAL_HOURS} hours"},
            {"label": "Aging Approval Queue", "value": len([req for req in pending_approval if req.created_at and req.created_at <= aging_cutoff]), "tone": "metric-blue", "desc": f"Pending approvals older than {AGING_REQUEST_DAYS} days"},
            {"label": "Approved In Domain", "value": EmployeeRequest.query.filter_by(domain=current_user.domain, status=STATUS_APPROVED).count(), "tone": "metric-green", "desc": "Total approved requests"},
        ]

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/features")
    def features():
        return render_template("features.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            password = (request.form.get("password") or "").strip()
            role = (request.form.get("role") or "").strip()
            domain = (request.form.get("domain") or "").strip().lower()

            if not email or not password or not role or not domain:
                flash("All fields are required.", "danger")
                return redirect(url_for("signup"))

            if User.query.filter_by(email=email).first():
                flash("Credentails and User Already Exists", "danger")
                return redirect(url_for("signup"))

            user = User(
                email=email,
                role=role,
                domain=domain,
                password_hash=generate_password_hash(password),
                created_at=datetime.utcnow(),
            )
            try:
                db.session.add(user)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Credentails and User Already Exists", "danger")
                return redirect(url_for("signup"))

            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))

        return render_template("signup.html", roles=ROLE_LABELS)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            password = (request.form.get("password") or "").strip()

            if not email or not password:
                flash("Please enter both email and password.", "danger")
                return redirect(url_for("login"))

            user = User.query.filter_by(email=email).first()
            if not user:
                flash("User does not exist. Please sign up first.", "danger")
                return redirect(url_for("login"))

            if not check_password_hash(user.password_hash, password):
                flash("Invalid credentials. Please check your password.", "danger")
                return redirect(url_for("login"))

            login_user(user)
            return redirect(url_for("dashboard"))

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        domain = current_user.domain
        if current_user.role == ROLE_HR:
            requests = EmployeeRequest.query.filter_by(domain=domain, requested_by=current_user.id).order_by(EmployeeRequest.created_at.desc()).all()
        elif current_user.role == ROLE_IT:
            requests = EmployeeRequest.query.filter_by(domain=domain, status=STATUS_PENDING_IT).order_by(EmployeeRequest.created_at.desc()).all()
        else:
            requests = EmployeeRequest.query.filter_by(domain=domain).order_by(EmployeeRequest.created_at.desc()).all()
        tracking_map = build_tracking_map(requests)
        dashboard_widgets = build_dashboard_widgets(current_user.role, requests, tracking_map)
        dashboard_hero = build_dashboard_hero(current_user.role)
        dashboard_actions = build_dashboard_actions(current_user.role)
        activity_feed = build_activity_feed(current_user.role, domain, current_user.id)
        return render_template(
            "dashboard.html",
            requests=requests,
            role=current_user.role,
            tracking_map=tracking_map,
            dashboard_widgets=dashboard_widgets,
            dashboard_hero=dashboard_hero,
            dashboard_actions=dashboard_actions,
            activity_feed=activity_feed,
            spotlight_requests=requests[:4],
        )

    @app.route("/hr/requests/new", methods=["GET", "POST"])
    @login_required
    @role_required(ROLE_HR)
    def hr_new_request():
        if request.method == "POST":
            first_name = (request.form.get("first_name") or "").strip()
            middle_name = (request.form.get("middle_name") or "").strip()
            last_name = (request.form.get("last_name") or "").strip()
            employee_email = (request.form.get("employee_email") or "").strip().lower()
            gender = (request.form.get("gender") or "").strip()
            job_title = (request.form.get("job_title") or "").strip()
            work_mode = (request.form.get("work_mode") or "").strip()
            work_location = (request.form.get("work_location") or "").strip()

            if not first_name or not last_name or not employee_email or not gender or not job_title or not work_mode or not work_location:
                flash("First name, last name, personal email, gender, role, work mode, and work location are required.", "danger")
                return redirect(url_for("hr_new_request"))

            if gender not in GENDER_OPTIONS:
                flash("Please choose a valid gender option.", "danger")
                return redirect(url_for("hr_new_request"))

            if work_mode not in WORK_MODE_OPTIONS:
                flash("Please choose a valid work mode.", "danger")
                return redirect(url_for("hr_new_request"))

            employee_name = " ".join(part for part in [first_name, middle_name, last_name] if part)
            company_email = build_company_email(first_name, last_name)
            if not company_email:
                flash("Please enter a valid first and last name to generate the company email.", "danger")
                return redirect(url_for("hr_new_request"))

            req = EmployeeRequest(
                domain=current_user.domain,
                requested_by=current_user.id,
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                employee_name=employee_name,
                employee_email=employee_email,
                gender=gender,
                job_title=job_title,
                work_mode=work_mode,
                work_location=work_location,
                company_email=company_email,
                status=STATUS_PENDING_IT,
                created_at=datetime.utcnow(),
            )
            db.session.add(req)
            db.session.flush()
            create_audit_entry(
                req,
                "REQUEST_CREATED",
                f"HR created request for {req.employee_name} ({req.company_email}).",
            )
            db.session.commit()
            flash(f"Request submitted to IT Admin. Company email policy applied: {company_email}", "success")
            return redirect(url_for("dashboard"))

        return render_template("hr_request.html", company_domain=app.config["EMPLOYEE_EMAIL_DOMAIN"])

    @app.route("/it/provision/<int:request_id>", methods=["GET", "POST"])
    @login_required
    @role_required(ROLE_IT)
    def it_provision(request_id):
        req = EmployeeRequest.query.filter_by(id=request_id, domain=current_user.domain).first_or_404()
        if req.status != STATUS_PENDING_IT:
            flash("Request is not pending IT provisioning.", "warning")
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            user_id = (request.form.get("it_user_id") or "").strip()
            license_type = (request.form.get("license_type") or "").strip()
            security_groups = (request.form.get("security_groups") or "").strip()
            assign_license = request.form.get("assign_license") == "on"
            password_reset_required = request.form.get("password_reset_required") == "on"
            mfa_reset_required = request.form.get("mfa_reset_required") == "on"
            mailbox_creation_required = request.form.get("mailbox_creation_required") == "on"
            account_access_action = (request.form.get("account_access_action") or "NONE").strip().upper()
            if account_access_action not in ACCOUNT_ACCESS_OPTIONS:
                flash("Select a valid account access action.", "danger")
                return redirect(url_for("it_provision", request_id=request_id))

            block_user = account_access_action == "DISABLE"

            if not user_id:
                flash("User ID is required.", "danger")
                return redirect(url_for("it_provision", request_id=request_id))

            if assign_license and not license_type:
                flash("Select a Microsoft license when assigning one.", "danger")
                return redirect(url_for("it_provision", request_id=request_id))

            if not any([
                assign_license,
                password_reset_required,
                mfa_reset_required,
                mailbox_creation_required,
                account_access_action != "NONE",
            ]):
                flash("Select at least one IT action for this request.", "danger")
                return redirect(url_for("it_provision", request_id=request_id))

            provisioning = Provisioning(
                request_id=req.id,
                created_by=current_user.id,
                it_user_id=user_id,
                license_type=license_type,
                security_groups=security_groups,
                assign_license=assign_license,
                password_reset_required=password_reset_required,
                block_user=block_user,
                mfa_reset_required=mfa_reset_required,
                mailbox_creation_required=mailbox_creation_required,
                account_access_action=account_access_action,
                created_at=datetime.utcnow(),
            )
            req.status = STATUS_PENDING_APPROVAL
            db.session.add(provisioning)
            action_bits = []
            if assign_license:
                action_bits.append(f"License: {license_type}")
            if password_reset_required:
                action_bits.append("Password reset")
            if mfa_reset_required:
                action_bits.append("MFA reset")
            if mailbox_creation_required:
                action_bits.append("Mailbox creation")
            if account_access_action != "NONE":
                action_bits.append(f"Account: {account_access_action}")
            if security_groups:
                action_bits.append(f"Groups: {security_groups}")

            create_audit_entry(
                req,
                "REQUEST_PROVISIONED",
                "IT provisioning submitted. " + ", ".join(action_bits),
            )
            db.session.commit()
            flash("Provisioning submitted for approval.", "success")
            return redirect(url_for("dashboard"))

        return render_template("it_provision.html", request_item=req, license_options=LICENSE_OPTIONS)

    @app.route("/approvals")
    @login_required
    @role_required(ROLE_CISO, ROLE_MGMT)
    def approvals():
        requests_pending = EmployeeRequest.query.filter_by(domain=current_user.domain, status=STATUS_PENDING_APPROVAL).order_by(EmployeeRequest.created_at.desc()).all()
        tracking_map = build_tracking_map(requests_pending)
        my_approval_rows = Approval.query.filter(
            Approval.request_id.in_([req.id for req in requests_pending]),
            Approval.approver_id == current_user.id,
        ).all() if requests_pending else []
        my_remarks = {row.request_id: (row.remarks or "") for row in my_approval_rows}
        return render_template("approvals.html", requests=requests_pending, tracking_map=tracking_map, my_remarks=my_remarks)

    @app.route("/approvals/<int:request_id>/approve", methods=["POST"])
    @login_required
    @role_required(ROLE_CISO, ROLE_MGMT)
    def approve_request(request_id):
        req = EmployeeRequest.query.filter_by(id=request_id, domain=current_user.domain).first_or_404()
        decision = request.form.get("decision")
        remarks = (request.form.get("remarks") or "").strip()
        if decision not in [APPROVAL_APPROVED, APPROVAL_REJECTED]:
            flash("Invalid decision.", "danger")
            return redirect(url_for("approvals"))

        if decision == APPROVAL_REJECTED and not remarks:
            flash("Remarks are required when rejecting a request.", "danger")
            return redirect(url_for("approvals"))

        existing = Approval.query.filter_by(request_id=req.id, approver_id=current_user.id).first()
        if existing:
            existing.status = decision
            existing.remarks = remarks
            existing.created_at = datetime.utcnow()
        else:
            approval = Approval(
                request_id=req.id,
                approver_id=current_user.id,
                role=current_user.role,
                status=decision,
                remarks=remarks,
                created_at=datetime.utcnow(),
            )
            db.session.add(approval)

        db.session.commit()

        approvals = Approval.query.filter_by(request_id=req.id).all()
        previous_status = req.status
        roles_approved = {a.role for a in approvals if a.status == APPROVAL_APPROVED}
        roles_rejected = {a.role for a in approvals if a.status == APPROVAL_REJECTED}

        if roles_rejected:
            req.status = STATUS_REJECTED
        elif ROLE_CISO in roles_approved and ROLE_MGMT in roles_approved:
            req.status = STATUS_APPROVED

        create_audit_entry(
            req,
            "APPROVAL_DECISION",
            f"{current_user.role} marked request as {decision}. Remarks: {remarks or '-'}",
        )

        if previous_status != req.status:
            if req.status == STATUS_APPROVED:
                create_audit_entry(req, "REQUEST_APPROVED", "Request approved by both CISO and Management.")
            elif req.status == STATUS_REJECTED:
                create_audit_entry(req, "REQUEST_REJECTED", "Request rejected in approval stage.")

        db.session.commit()

        tracking_map = build_tracking_map([req])
        pending_from = tracking_map.get(req.id, {}).get("pending_from", "next approval stage")
        if req.status == STATUS_PENDING_APPROVAL:
            flash(f"Decision saved. Waiting for {pending_from}.", "success")
        elif req.status == STATUS_APPROVED:
            flash("Decision saved. Request is now approved by both CISO and Management.", "success")
        else:
            flash("Decision saved. Request has been rejected.", "success")
        return redirect(url_for("approvals"))

    @app.route("/status/<int:request_id>")
    @login_required
    def request_status(request_id):
        req = EmployeeRequest.query.filter_by(id=request_id, domain=current_user.domain).first_or_404()
        provisioning = Provisioning.query.filter_by(request_id=req.id).first()
        tracking_map = build_tracking_map([req])
        audits = RequestAudit.query.filter_by(request_id=req.id).order_by(RequestAudit.created_at.asc()).all()
        return render_template("status.html", request_item=req, provisioning=provisioning, tracking=tracking_map.get(req.id), audits=audits)

    @app.route("/history")
    @login_required
    def history():
        domain = current_user.domain
        role = current_user.role
        export_csv = request.args.get("export") == "csv"
        filters = parse_history_filters()

        if role == ROLE_HR:
            requests = EmployeeRequest.query.filter_by(domain=domain, requested_by=current_user.id).order_by(EmployeeRequest.created_at.desc()).all()
            tracking_map = build_tracking_map(requests)
            rows = []
            for req in requests:
                tracking = tracking_map.get(req.id, {})
                rows.append({
                    "date": req.created_at.strftime("%Y-%m-%d %H:%M") if req.created_at else "-",
                    "employee": req.employee_name,
                    "personal_email": req.employee_email,
                    "company_email": req.company_email or "-",
                    "activity": "Created request",
                    "status": req.status,
                    "request_status": req.status,
                    "pending_from": tracking.get("pending_from", "-"),
                    "remarks": "-",
                })
            title = "HR Activity History"
        elif role == ROLE_IT:
            provision_rows = db.session.query(Provisioning, EmployeeRequest).join(
                EmployeeRequest,
                Provisioning.request_id == EmployeeRequest.id,
            ).filter(
                EmployeeRequest.domain == domain,
                Provisioning.created_by == current_user.id,
            ).order_by(Provisioning.created_at.desc()).all()
            requests = [req for _, req in provision_rows]
            tracking_map = build_tracking_map(requests)
            rows = []
            for provisioning, req in provision_rows:
                tracking = tracking_map.get(req.id, {})
                actions = []
                if provisioning.assign_license:
                    actions.append("License")
                if provisioning.password_reset_required:
                    actions.append("Password reset")
                if provisioning.mfa_reset_required:
                    actions.append("MFA reset")
                if provisioning.mailbox_creation_required:
                    actions.append("Mailbox")
                if provisioning.account_access_action == "ENABLE":
                    actions.append("Enable account")
                elif provisioning.account_access_action == "DISABLE":
                    actions.append("Disable account")

                rows.append({
                    "date": provisioning.created_at.strftime("%Y-%m-%d %H:%M") if provisioning.created_at else "-",
                    "employee": req.employee_name,
                    "personal_email": req.employee_email,
                    "company_email": req.company_email or "-",
                    "activity": "Provisioned request",
                    "status": req.status,
                    "request_status": req.status,
                    "pending_from": tracking.get("pending_from", "-"),
                    "remarks": ", ".join(actions) if actions else "-",
                })
            title = "IT Activity History"
        else:
            approval_rows = db.session.query(Approval, EmployeeRequest).join(
                EmployeeRequest,
                Approval.request_id == EmployeeRequest.id,
            ).filter(
                EmployeeRequest.domain == domain,
                Approval.approver_id == current_user.id,
            ).order_by(Approval.created_at.desc()).all()
            requests = [req for _, req in approval_rows]
            tracking_map = build_tracking_map(requests)
            rows = []
            for approval, req in approval_rows:
                tracking = tracking_map.get(req.id, {})
                rows.append({
                    "date": approval.created_at.strftime("%Y-%m-%d %H:%M") if approval.created_at else "-",
                    "employee": req.employee_name,
                    "personal_email": req.employee_email,
                    "company_email": req.company_email or "-",
                    "activity": f"{approval.role} decision",
                    "status": f"{approval.status} (Request: {req.status})",
                    "request_status": req.status,
                    "pending_from": tracking.get("pending_from", "-"),
                    "remarks": (approval.remarks or "-").strip() or "-",
                })
            title = "Approval History"

        rows = apply_history_filters(rows, filters)

        if export_csv:
            headers = ["date", "employee", "personal_email", "company_email", "activity", "status", "pending_from", "remarks"]
            filename = f"{role.lower()}_history.csv"
            return build_csv_response(filename, headers, rows)

        return render_template(
            "history.html",
            history_rows=rows,
            history_title=title,
            filters=filters,
            status_options=[STATUS_PENDING_IT, STATUS_PENDING_APPROVAL, STATUS_APPROVED, STATUS_REJECTED],
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
