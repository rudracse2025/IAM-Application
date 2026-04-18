import csv
import io
import os
from datetime import datetime, timedelta
from functools import wraps

from dateutil import parser as date_parser
from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, redirect, render_template, request, url_for, flash, abort
from flask_cors import CORS
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from marshmallow import EXCLUDE, Schema, ValidationError, fields, validate
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

from models import (
    db,
    User,
    EmployeeRequest,
    Provisioning,
    Approval,
    RequestTimeline,
    AuditLog,
    Notification,
    Comment,
    RequestTemplate,
    ApprovalRule,
    RejectionReason,
)

load_dotenv()

ROLE_HR = "HR"
ROLE_IT = "IT_ADMIN"
ROLE_CISO = "CISO"
ROLE_MGMT = "MANAGEMENT"
ALL_ROLES = [ROLE_HR, ROLE_IT, ROLE_CISO, ROLE_MGMT]

ROLE_LABELS = {
    ROLE_HR: "HR",
    ROLE_IT: "IT Admin",
    ROLE_CISO: "CISO",
    ROLE_MGMT: "Management",
}

STATUS_DRAFT = "DRAFT"
STATUS_PENDING_IT = "PENDING_IT"
STATUS_PENDING_APPROVAL = "PENDING_APPROVAL"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"
STATUS_DELETED = "DELETED"
STATUS_VALUES = [STATUS_DRAFT, STATUS_PENDING_IT, STATUS_PENDING_APPROVAL, STATUS_APPROVED, STATUS_REJECTED, STATUS_DELETED]
PRIORITY_VALUES = ["LOW", "MEDIUM", "HIGH", "URGENT"]

APPROVAL_PENDING = "PENDING"
APPROVAL_APPROVED = "APPROVED"
APPROVAL_REJECTED = "REJECTED"

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 180
RATE_LIMIT_TRACKER = {}

ma = Marshmallow()
migrate = Migrate()


class UserSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        include_fk = True
        load_instance = False


class EmployeeRequestSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = EmployeeRequest
        include_fk = True
        load_instance = False


class ProvisioningSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Provisioning
        include_fk = True
        load_instance = False


class ApprovalSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Approval
        include_fk = True
        load_instance = False


class TimelineSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = RequestTimeline
        include_fk = True
        load_instance = False


class NotificationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Notification
        include_fk = True
        load_instance = False


class CommentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Comment
        include_fk = True
        load_instance = False


class RequestTemplateSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = RequestTemplate
        include_fk = True
        load_instance = False


class RequestCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    employee_name = fields.Str(required=True)
    employee_email = fields.Email(required=True)
    job_title = fields.Str(load_default=None, allow_none=True)
    department = fields.Str(load_default=None, allow_none=True)
    manager_id = fields.Int(load_default=None, allow_none=True)
    notes = fields.Str(load_default=None, allow_none=True)
    due_date = fields.DateTime(load_default=None, allow_none=True)
    priority = fields.Str(load_default="MEDIUM", validate=validate.OneOf(PRIORITY_VALUES))
    save_as_draft = fields.Bool(load_default=False)


class RequestUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    employee_name = fields.Str()
    employee_email = fields.Email()
    job_title = fields.Str(allow_none=True)
    department = fields.Str(allow_none=True)
    manager_id = fields.Int(allow_none=True)
    notes = fields.Str(allow_none=True)
    rejection_reason = fields.Str(allow_none=True)
    due_date = fields.DateTime(allow_none=True)
    priority = fields.Str(validate=validate.OneOf(PRIORITY_VALUES))
    status = fields.Str(validate=validate.OneOf(STATUS_VALUES))


class CommentCreateSchema(Schema):
    content = fields.Str(required=True, validate=validate.Length(min=1, max=5000))


class ApprovalDecisionSchema(Schema):
    decision = fields.Str(required=True, validate=validate.OneOf([APPROVAL_APPROVED, APPROVAL_REJECTED]))
    comments = fields.Str(load_default=None, allow_none=True)
    rejection_reason = fields.Str(load_default=None, allow_none=True)


class ProfileUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    full_name = fields.Str(allow_none=True)
    phone = fields.Str(allow_none=True)
    department = fields.Str(allow_none=True)
    profile_pic_url = fields.Str(allow_none=True)
    preferences = fields.Dict(keys=fields.Str(), values=fields.Raw(), allow_none=True)
    two_factor_enabled = fields.Bool()
    two_factor_method = fields.Str(allow_none=True)


def _api_error(message, code, status_code, details=None):
    payload = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return jsonify(payload), status_code


def _now():
    return datetime.utcnow()


def _parse_date(value):
    if not value:
        return None
    return date_parser.parse(value)


def _clean_rate_limit():
    cutoff = _now() - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
    stale_keys = []
    for key, timestamps in RATE_LIMIT_TRACKER.items():
        RATE_LIMIT_TRACKER[key] = [t for t in timestamps if t >= cutoff]
        if not RATE_LIMIT_TRACKER[key]:
            stale_keys.append(key)
    for key in stale_keys:
        RATE_LIMIT_TRACKER.pop(key, None)


def _record_audit(action, entity_type, entity_id=None, metadata=None):
    actor_id = current_user.id if current_user.is_authenticated else None
    db.session.add(
        AuditLog(
            user_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            audit_metadata=metadata or {},
            created_at=_now(),
        )
    )


def _record_timeline(request_id, from_status, to_status, comment=None):
    db.session.add(
        RequestTimeline(
            request_id=request_id,
            changed_by=current_user.id if current_user.is_authenticated else None,
            from_status=from_status,
            to_status=to_status,
            comment=comment,
            created_at=_now(),
        )
    )


def _notify_users(users, title, message, category="INFO"):
    for user in users:
        db.session.add(
            Notification(
                user_id=user.id,
                title=title,
                message=message,
                category=category,
                created_at=_now(),
            )
        )


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://iam_user:iam_pass@localhost:3306/iam_app",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    user_schema = UserSchema()
    request_schema = EmployeeRequestSchema()
    request_list_schema = EmployeeRequestSchema(many=True)
    provisioning_schema = ProvisioningSchema()
    approval_schema = ApprovalSchema(many=True)
    timeline_schema = TimelineSchema(many=True)
    notification_schema = NotificationSchema(many=True)
    comment_schema = CommentSchema(many=True)
    template_schema = RequestTemplateSchema(many=True)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.before_request
    def api_rate_limit():
        if not request.path.startswith("/api/"):
            return None
        _clean_rate_limit()
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
        key = f"{ip}:{request.path}"
        bucket = RATE_LIMIT_TRACKER.setdefault(key, [])
        now = _now()
        bucket.append(now)
        if len(bucket) > RATE_LIMIT_MAX_REQUESTS:
            return _api_error("Rate limit exceeded", "RATE_LIMIT_EXCEEDED", 429)
        return None

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        if request.path.startswith("/api/"):
            return _api_error("Validation failed", "VALIDATION_ERROR", 400, error.messages)
        return str(error), 400

    @app.errorhandler(404)
    def handle_not_found(_error):
        if request.path.startswith("/api/"):
            return _api_error("Resource not found", "NOT_FOUND", 404)
        return "Not Found", 404

    @app.errorhandler(403)
    def handle_forbidden(_error):
        if request.path.startswith("/api/"):
            return _api_error("Forbidden", "FORBIDDEN", 403)
        return "Forbidden", 403

    @app.errorhandler(500)
    def handle_server_error(_error):
        if request.path.startswith("/api/"):
            return _api_error("Internal server error", "INTERNAL_ERROR", 500)
        return "Internal server error", 500

    def role_required(*roles):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if current_user.role not in roles:
                    abort(403)
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def can_access_request(req):
        if req.domain != current_user.domain:
            return False
        if current_user.role == ROLE_HR:
            return req.requested_by == current_user.id
        return True

    def base_request_query(include_deleted=False):
        query = EmployeeRequest.query.filter_by(domain=current_user.domain)
        if current_user.role == ROLE_HR:
            query = query.filter_by(requested_by=current_user.id)
        if not include_deleted:
            query = query.filter(EmployeeRequest.deleted_at.is_(None))
        return query

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            email = request.form.get("email").strip().lower()
            password = request.form.get("password")
            role = request.form.get("role")
            domain = request.form.get("domain").strip().lower()

            if not email or not password or not role or not domain:
                flash("All fields are required.", "danger")
                return redirect(url_for("signup"))

            if role not in ALL_ROLES:
                flash("Invalid role.", "danger")
                return redirect(url_for("signup"))

            if User.query.filter_by(email=email).first():
                flash("Email already registered.", "danger")
                return redirect(url_for("signup"))

            user = User(
                email=email,
                role=role,
                domain=domain,
                password_hash=generate_password_hash(password),
                created_at=_now(),
                updated_at=_now(),
                preferences={"notifications": True, "theme": "light"},
            )
            db.session.add(user)
            # flush first so user.id exists before creating related audit rows in same transaction
            db.session.flush()
            _record_audit("user_signup", "User", user.id, {"email": email, "role": role})
            db.session.commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))

        return render_template("signup.html", roles=ROLE_LABELS)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email").strip().lower()
            password = request.form.get("password")

            user = User.query.filter_by(email=email).first()
            if not user or not user.is_active or not check_password_hash(user.password_hash, password):
                flash("Invalid credentials.", "danger")
                return redirect(url_for("login"))

            user.last_login = _now()
            user.updated_at = _now()
            login_user(user)
            _record_audit("user_login", "User", user.id)
            db.session.commit()
            return redirect(url_for("dashboard"))

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        _record_audit("user_logout", "User", current_user.id)
        db.session.commit()
        logout_user()
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        domain = current_user.domain
        if current_user.role == ROLE_HR:
            requests_data = (
                EmployeeRequest.query.filter_by(domain=domain, requested_by=current_user.id)
                .filter(EmployeeRequest.deleted_at.is_(None))
                .order_by(EmployeeRequest.created_at.desc())
                .all()
            )
        elif current_user.role == ROLE_IT:
            requests_data = (
                EmployeeRequest.query.filter_by(domain=domain, status=STATUS_PENDING_IT)
                .filter(EmployeeRequest.deleted_at.is_(None))
                .order_by(EmployeeRequest.created_at.desc())
                .all()
            )
        else:
            requests_data = (
                EmployeeRequest.query.filter_by(domain=domain, status=STATUS_PENDING_APPROVAL)
                .filter(EmployeeRequest.deleted_at.is_(None))
                .order_by(EmployeeRequest.created_at.desc())
                .all()
            )
        return render_template("dashboard.html", requests=requests_data, role=current_user.role)

    @app.route("/hr/requests/new", methods=["GET", "POST"])
    @login_required
    @role_required(ROLE_HR)
    def hr_new_request():
        if request.method == "POST":
            name = request.form.get("employee_name")
            email = request.form.get("employee_email")
            if not name or not email:
                flash("Employee name and email are required.", "danger")
                return redirect(url_for("hr_new_request"))

            req = EmployeeRequest(
                domain=current_user.domain,
                requested_by=current_user.id,
                employee_name=name,
                employee_email=email,
                status=STATUS_PENDING_IT,
                created_at=_now(),
                updated_at=_now(),
                priority="MEDIUM",
            )
            db.session.add(req)
            db.session.flush()
            _record_timeline(req.id, None, STATUS_PENDING_IT, "Request created by HR")
            it_users = User.query.filter_by(domain=current_user.domain, role=ROLE_IT, is_active=True).all()
            _notify_users(it_users, "New provisioning request", f"Request #{req.id} is pending IT action.", "REQUEST")
            _record_audit("request_created", "EmployeeRequest", req.id)
            db.session.commit()
            flash("Request submitted to IT Admin.", "success")
            return redirect(url_for("dashboard"))

        return render_template("hr_request.html")

    @app.route("/it/provision/<int:request_id>", methods=["GET", "POST"])
    @login_required
    @role_required(ROLE_IT)
    def it_provision(request_id):
        req = (
            EmployeeRequest.query.filter_by(id=request_id, domain=current_user.domain)
            .filter(EmployeeRequest.deleted_at.is_(None))
            .first_or_404()
        )
        if req.status != STATUS_PENDING_IT:
            flash("Request is not pending IT provisioning.", "warning")
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            user_id = request.form.get("it_user_id")
            license_type = request.form.get("license_type")
            security_groups = request.form.get("security_groups")
            if not user_id or not license_type:
                flash("User ID and license are required.", "danger")
                return redirect(url_for("it_provision", request_id=request_id))

            provisioning = Provisioning(
                request_id=req.id,
                created_by=current_user.id,
                it_user_id=user_id,
                license_type=license_type,
                security_groups=security_groups,
                status="SUBMITTED_APPROVAL",
                created_at=_now(),
                updated_at=_now(),
                deployment_details={},
                resource_allocation={},
            )
            previous = req.status
            req.status = STATUS_PENDING_APPROVAL
            req.updated_at = _now()
            db.session.add(provisioning)
            _record_timeline(req.id, previous, STATUS_PENDING_APPROVAL, "Provisioning completed and sent for approval")
            approvers = User.query.filter(User.domain == current_user.domain, User.role.in_([ROLE_CISO, ROLE_MGMT]), User.is_active.is_(True)).all()
            _notify_users(approvers, "Approval required", f"Request #{req.id} is pending approval.", "APPROVAL")
            _record_audit("request_provisioned", "EmployeeRequest", req.id)
            db.session.commit()
            flash("Provisioning submitted for approval.", "success")
            return redirect(url_for("dashboard"))

        return render_template("it_provision.html", request_item=req)

    @app.route("/approvals")
    @login_required
    @role_required(ROLE_CISO, ROLE_MGMT)
    def approvals():
        requests_pending = (
            EmployeeRequest.query.filter_by(domain=current_user.domain, status=STATUS_PENDING_APPROVAL)
            .filter(EmployeeRequest.deleted_at.is_(None))
            .order_by(EmployeeRequest.created_at.desc())
            .all()
        )
        return render_template("approvals.html", requests=requests_pending)

    @app.route("/approvals/<int:request_id>/approve", methods=["POST"])
    @login_required
    @role_required(ROLE_CISO, ROLE_MGMT)
    def approve_request(request_id):
        req = (
            EmployeeRequest.query.filter_by(id=request_id, domain=current_user.domain)
            .filter(EmployeeRequest.deleted_at.is_(None))
            .first_or_404()
        )
        decision = request.form.get("decision")
        comments = request.form.get("comments")
        if decision not in [APPROVAL_APPROVED, APPROVAL_REJECTED]:
            flash("Invalid decision.", "danger")
            return redirect(url_for("approvals"))

        existing = Approval.query.filter_by(request_id=req.id, approver_id=current_user.id).first()
        if existing:
            existing.status = decision
            existing.comments = comments
            existing.decision_timestamp = _now()
            existing.updated_at = _now()
        else:
            approval = Approval(
                request_id=req.id,
                approver_id=current_user.id,
                role=current_user.role,
                status=decision,
                comments=comments,
                decision_timestamp=_now(),
                created_at=_now(),
                updated_at=_now(),
            )
            db.session.add(approval)

        approvals_data = Approval.query.filter_by(request_id=req.id).all()
        roles_approved = {a.role for a in approvals_data if a.status == APPROVAL_APPROVED}
        roles_rejected = {a.role for a in approvals_data if a.status == APPROVAL_REJECTED}
        old_status = req.status

        if roles_rejected:
            req.status = STATUS_REJECTED
            req.rejection_reason = comments
        elif ROLE_CISO in roles_approved and ROLE_MGMT in roles_approved:
            req.status = STATUS_APPROVED

        req.updated_at = _now()
        if req.status != old_status:
            _record_timeline(req.id, old_status, req.status, comments)
            owner = User.query.get(req.requested_by)
            if owner:
                _notify_users([owner], "Request decision updated", f"Request #{req.id} is now {req.status}.", "REQUEST")
        _record_audit("request_approved", "EmployeeRequest", req.id, {"decision": decision})
        db.session.commit()
        flash("Decision saved.", "success")
        return redirect(url_for("approvals"))

    @app.route("/status/<int:request_id>")
    @login_required
    def request_status(request_id):
        req = (
            EmployeeRequest.query.filter_by(id=request_id, domain=current_user.domain)
            .filter(EmployeeRequest.deleted_at.is_(None))
            .first_or_404()
        )
        return render_template("status.html", request_item=req)

    @app.route("/api/requests", methods=["GET"])
    @login_required
    def api_list_requests():
        include_deleted = request.args.get("include_deleted", "false").lower() == "true"
        query = base_request_query(include_deleted=include_deleted)

        status = request.args.get("status")
        priority = request.args.get("priority")
        department = request.args.get("department")
        q = request.args.get("q")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        sort_by = request.args.get("sort_by", "created_at")
        sort_order = request.args.get("sort_order", "desc")
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)

        if status:
            query = query.filter(EmployeeRequest.status == status)
        if priority:
            query = query.filter(EmployeeRequest.priority == priority)
        if department:
            query = query.filter(EmployeeRequest.department == department)
        if q:
            like = f"%{q.strip()}%"
            query = query.filter(
                or_(
                    EmployeeRequest.employee_name.ilike(like),
                    EmployeeRequest.employee_email.ilike(like),
                    EmployeeRequest.job_title.ilike(like),
                    EmployeeRequest.department.ilike(like),
                    EmployeeRequest.notes.ilike(like),
                )
            )
        if start_date:
            query = query.filter(EmployeeRequest.created_at >= _parse_date(start_date))
        if end_date:
            query = query.filter(EmployeeRequest.created_at <= _parse_date(end_date))

        sortable = {
            "id": EmployeeRequest.id,
            "created_at": EmployeeRequest.created_at,
            "updated_at": EmployeeRequest.updated_at,
            "due_date": EmployeeRequest.due_date,
            "priority": EmployeeRequest.priority,
            "status": EmployeeRequest.status,
        }
        sort_col = sortable.get(sort_by, EmployeeRequest.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        if request.args.get("export", "").lower() == "csv":
            rows = query.all()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["id", "employee_name", "employee_email", "status", "priority", "department", "created_at"])
            for item in rows:
                writer.writerow(
                    [
                        item.id,
                        item.employee_name,
                        item.employee_email,
                        item.status,
                        item.priority,
                        item.department or "",
                        item.created_at.isoformat() if item.created_at else "",
                    ]
                )
            response = make_response(output.getvalue())
            response.headers["Content-Type"] = "text/csv"
            response.headers["Content-Disposition"] = "attachment; filename=requests.csv"
            return response

        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return jsonify(
            {
                "items": request_list_schema.dump(items),
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page,
                },
            }
        )

    @app.route("/api/requests", methods=["POST"])
    @login_required
    @role_required(ROLE_HR)
    def api_create_request():
        payload = RequestCreateSchema().load(request.get_json(silent=True) or {})
        status = STATUS_DRAFT if payload.get("save_as_draft") else STATUS_PENDING_IT

        req = EmployeeRequest(
            domain=current_user.domain,
            requested_by=current_user.id,
            employee_name=payload["employee_name"],
            employee_email=payload["employee_email"],
            job_title=payload.get("job_title"),
            department=payload.get("department"),
            manager_id=payload.get("manager_id"),
            notes=payload.get("notes"),
            due_date=payload.get("due_date"),
            priority=payload.get("priority", "MEDIUM"),
            status=status,
            created_at=_now(),
            updated_at=_now(),
        )
        db.session.add(req)
        # flush before timeline/audit so request_id is available on related rows
        db.session.flush()
        _record_timeline(req.id, None, status, "Request created via API")
        _record_audit("request_created_api", "EmployeeRequest", req.id)
        if status == STATUS_PENDING_IT:
            it_users = User.query.filter_by(domain=current_user.domain, role=ROLE_IT, is_active=True).all()
            _notify_users(it_users, "New provisioning request", f"Request #{req.id} is pending IT action.", "REQUEST")
        db.session.commit()
        return jsonify({"item": request_schema.dump(req)}), 201

    @app.route("/api/requests/<int:request_id>", methods=["GET"])
    @login_required
    def api_get_request(request_id):
        req = EmployeeRequest.query.filter_by(id=request_id).first_or_404()
        if not can_access_request(req) or req.deleted_at:
            abort(404)
        data = request_schema.dump(req)
        data["timeline_count"] = RequestTimeline.query.filter_by(request_id=req.id).count()
        data["comment_count"] = Comment.query.filter_by(request_id=req.id).filter(Comment.deleted_at.is_(None)).count()
        return jsonify({"item": data})

    @app.route("/api/requests/<int:request_id>", methods=["PATCH"])
    @login_required
    def api_patch_request(request_id):
        req = EmployeeRequest.query.filter_by(id=request_id).first_or_404()
        if not can_access_request(req) or req.deleted_at:
            abort(404)
        if current_user.role == ROLE_HR and req.requested_by != current_user.id:
            abort(403)

        payload = RequestUpdateSchema().load(request.get_json(silent=True) or {})
        old_status = req.status
        for key, value in payload.items():
            setattr(req, key, value)
        req.updated_at = _now()
        if req.status != old_status:
            _record_timeline(req.id, old_status, req.status, payload.get("notes"))
        _record_audit("request_updated_api", "EmployeeRequest", req.id, {"fields": list(payload.keys())})
        db.session.commit()
        return jsonify({"item": request_schema.dump(req)})

    @app.route("/api/requests/<int:request_id>", methods=["DELETE"])
    @login_required
    def api_delete_request(request_id):
        req = EmployeeRequest.query.filter_by(id=request_id).first_or_404()
        if not can_access_request(req):
            abort(404)
        if current_user.role == ROLE_HR and req.requested_by != current_user.id:
            abort(403)
        if req.deleted_at:
            return jsonify({"item": request_schema.dump(req)})
        old_status = req.status
        req.deleted_at = _now()
        req.status = STATUS_DELETED
        req.updated_at = _now()
        _record_timeline(req.id, old_status, STATUS_DELETED, "Soft deleted")
        _record_audit("request_soft_deleted", "EmployeeRequest", req.id)
        db.session.commit()
        return jsonify({"item": request_schema.dump(req)})

    @app.route("/api/requests/<int:request_id>/timeline", methods=["GET"])
    @login_required
    def api_request_timeline(request_id):
        req = EmployeeRequest.query.filter_by(id=request_id).first_or_404()
        if not can_access_request(req):
            abort(404)
        timeline_entries = RequestTimeline.query.filter_by(request_id=request_id).order_by(RequestTimeline.created_at.asc()).all()
        return jsonify({"items": timeline_schema.dump(timeline_entries)})

    @app.route("/api/requests/<int:request_id>/comments", methods=["GET"])
    @login_required
    def api_request_comments(request_id):
        req = EmployeeRequest.query.filter_by(id=request_id).first_or_404()
        if not can_access_request(req):
            abort(404)
        comments = (
            Comment.query.filter_by(request_id=request_id)
            .filter(Comment.deleted_at.is_(None))
            .order_by(Comment.created_at.asc())
            .all()
        )
        return jsonify({"items": comment_schema.dump(comments)})

    @app.route("/api/requests/<int:request_id>/comments", methods=["POST"])
    @login_required
    def api_add_comment(request_id):
        req = EmployeeRequest.query.filter_by(id=request_id).first_or_404()
        if not can_access_request(req):
            abort(404)
        payload = CommentCreateSchema().load(request.get_json(silent=True) or {})
        comment = Comment(
            request_id=request_id,
            user_id=current_user.id,
            content=payload["content"],
            created_at=_now(),
            updated_at=_now(),
        )
        db.session.add(comment)
        db.session.flush()
        _record_audit("comment_added", "Comment", comment.id, {"request_id": request_id})
        db.session.commit()
        return jsonify({"item": CommentSchema().dump(comment)}), 201

    @app.route("/api/approvals", methods=["GET"])
    @login_required
    @role_required(ROLE_CISO, ROLE_MGMT)
    def api_approvals():
        items = (
            EmployeeRequest.query.filter_by(domain=current_user.domain, status=STATUS_PENDING_APPROVAL)
            .filter(EmployeeRequest.deleted_at.is_(None))
            .order_by(EmployeeRequest.created_at.desc())
            .all()
        )
        return jsonify({"items": request_list_schema.dump(items)})

    @app.route("/api/approvals/<int:request_id>", methods=["POST"])
    @login_required
    @role_required(ROLE_CISO, ROLE_MGMT)
    def api_approve_request(request_id):
        req = (
            EmployeeRequest.query.filter_by(id=request_id, domain=current_user.domain)
            .filter(EmployeeRequest.deleted_at.is_(None))
            .first_or_404()
        )
        payload = ApprovalDecisionSchema().load(request.get_json(silent=True) or {})

        existing = Approval.query.filter_by(request_id=req.id, approver_id=current_user.id).first()
        if existing:
            existing.status = payload["decision"]
            existing.comments = payload.get("comments")
            existing.decision_timestamp = _now()
            existing.updated_at = _now()
        else:
            db.session.add(
                Approval(
                    request_id=req.id,
                    approver_id=current_user.id,
                    role=current_user.role,
                    status=payload["decision"],
                    comments=payload.get("comments"),
                    decision_timestamp=_now(),
                    created_at=_now(),
                    updated_at=_now(),
                )
            )

        approvals_data = Approval.query.filter_by(request_id=req.id).all()
        approved_roles = {a.role for a in approvals_data if a.status == APPROVAL_APPROVED}
        rejected_roles = {a.role for a in approvals_data if a.status == APPROVAL_REJECTED}
        old_status = req.status
        if rejected_roles:
            req.status = STATUS_REJECTED
            req.rejection_reason = payload.get("rejection_reason") or payload.get("comments")
        elif ROLE_CISO in approved_roles and ROLE_MGMT in approved_roles:
            req.status = STATUS_APPROVED
        req.updated_at = _now()

        if req.status != old_status:
            _record_timeline(req.id, old_status, req.status, payload.get("comments"))
            owner = User.query.get(req.requested_by)
            if owner:
                _notify_users([owner], "Request status updated", f"Request #{req.id}: {req.status}", "APPROVAL")
        _record_audit("approval_decision", "EmployeeRequest", req.id, {"decision": payload["decision"]})
        db.session.commit()
        return jsonify({"item": request_schema.dump(req)})

    @app.route("/api/approvals/<int:request_id>/history", methods=["GET"])
    @login_required
    def api_approval_history(request_id):
        req = EmployeeRequest.query.filter_by(id=request_id, domain=current_user.domain).first_or_404()
        if not can_access_request(req):
            abort(404)
        records = Approval.query.filter_by(request_id=request_id).order_by(Approval.created_at.asc()).all()
        return jsonify({"items": approval_schema.dump(records)})

    @app.route("/api/approvals/bulk", methods=["POST"])
    @login_required
    @role_required(ROLE_CISO, ROLE_MGMT)
    def api_bulk_approvals():
        payload = request.get_json(silent=True) or {}
        request_ids = payload.get("request_ids", [])
        decision = payload.get("decision")
        if not isinstance(request_ids, list) or not request_ids:
            return _api_error("request_ids must be a non-empty list", "VALIDATION_ERROR", 400)
        if decision not in [APPROVAL_APPROVED, APPROVAL_REJECTED]:
            return _api_error("Invalid decision", "VALIDATION_ERROR", 400)

        updated = []
        for request_id in request_ids:
            req = (
                EmployeeRequest.query.filter_by(id=request_id, domain=current_user.domain)
                .filter(EmployeeRequest.deleted_at.is_(None))
                .first()
            )
            if not req:
                continue
            old_status = req.status
            if decision == APPROVAL_REJECTED:
                req.status = STATUS_REJECTED
            else:
                req.status = STATUS_APPROVED
            req.updated_at = _now()
            db.session.add(
                Approval(
                    request_id=req.id,
                    approver_id=current_user.id,
                    role=current_user.role,
                    status=decision,
                    comments=payload.get("comments"),
                    decision_timestamp=_now(),
                    created_at=_now(),
                    updated_at=_now(),
                )
            )
            _record_timeline(req.id, old_status, req.status, "Bulk approval operation")
            updated.append(req.id)

        _record_audit("approval_bulk_decision", "EmployeeRequest", None, {"request_ids": updated, "decision": decision})
        db.session.commit()
        return jsonify({"updated_request_ids": updated, "count": len(updated)})

    @app.route("/api/users/profile", methods=["GET"])
    @login_required
    def api_get_profile():
        return jsonify({"item": user_schema.dump(current_user)})

    @app.route("/api/users/profile", methods=["PATCH"])
    @login_required
    def api_patch_profile():
        payload = ProfileUpdateSchema().load(request.get_json(silent=True) or {})
        for key, value in payload.items():
            setattr(current_user, key, value)
        current_user.updated_at = _now()
        _record_audit("profile_updated", "User", current_user.id, {"fields": list(payload.keys())})
        db.session.commit()
        return jsonify({"item": user_schema.dump(current_user)})

    @app.route("/api/users/<int:user_id>", methods=["GET"])
    @login_required
    def api_get_user(user_id):
        user = User.query.filter_by(id=user_id, domain=current_user.domain).first_or_404()
        return jsonify({"item": user_schema.dump(user)})

    @app.route("/api/dashboard/stats", methods=["GET"])
    @login_required
    def api_dashboard_stats():
        base = EmployeeRequest.query.filter_by(domain=current_user.domain).filter(EmployeeRequest.deleted_at.is_(None))
        if current_user.role == ROLE_HR:
            base = base.filter_by(requested_by=current_user.id)
        stats = {
            "total_requests": base.count(),
            "pending_it": base.filter(EmployeeRequest.status == STATUS_PENDING_IT).count(),
            "pending_approval": base.filter(EmployeeRequest.status == STATUS_PENDING_APPROVAL).count(),
            "approved": base.filter(EmployeeRequest.status == STATUS_APPROVED).count(),
            "rejected": base.filter(EmployeeRequest.status == STATUS_REJECTED).count(),
            "overdue": base.filter(
                EmployeeRequest.due_date.is_not(None),
                EmployeeRequest.due_date < _now(),
                EmployeeRequest.status.in_([STATUS_PENDING_IT, STATUS_PENDING_APPROVAL]),
            ).count(),
            "unread_notifications": Notification.query.filter_by(user_id=current_user.id, is_read=False).count(),
        }
        return jsonify({"item": stats})

    @app.route("/api/notifications", methods=["GET"])
    @login_required
    def api_notifications():
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)
        query = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return jsonify(
            {
                "items": notification_schema.dump(items),
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page,
                },
            }
        )

    @app.route("/api/notifications/<int:notification_id>/read", methods=["POST"])
    @login_required
    def api_notification_read(notification_id):
        notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
        notification.is_read = True
        notification.read_at = _now()
        db.session.commit()
        return jsonify({"item": NotificationSchema().dump(notification)})

    @app.route("/api/search", methods=["GET"])
    @login_required
    def api_search():
        q = (request.args.get("q") or "").strip()
        if not q:
            return _api_error("Query parameter q is required", "VALIDATION_ERROR", 400)
        like = f"%{q}%"
        query = base_request_query(include_deleted=False).filter(
            or_(
                EmployeeRequest.employee_name.ilike(like),
                EmployeeRequest.employee_email.ilike(like),
                EmployeeRequest.job_title.ilike(like),
                EmployeeRequest.department.ilike(like),
                EmployeeRequest.notes.ilike(like),
                EmployeeRequest.rejection_reason.ilike(like),
            )
        )
        results = query.order_by(EmployeeRequest.updated_at.desc()).limit(100).all()
        return jsonify({"items": request_list_schema.dump(results), "count": len(results)})

    @app.route("/api/request-templates", methods=["GET", "POST"])
    @login_required
    @role_required(ROLE_HR)
    def api_request_templates():
        if request.method == "GET":
            items = RequestTemplate.query.filter_by(domain=current_user.domain, is_active=True).all()
            return jsonify({"items": template_schema.dump(items)})

        payload = request.get_json(silent=True) or {}
        name = payload.get("name")
        template_data = payload.get("template_data")
        if not name or not isinstance(template_data, dict):
            return _api_error("name and template_data are required", "VALIDATION_ERROR", 400)

        template = RequestTemplate(
            name=name,
            description=payload.get("description"),
            created_by=current_user.id,
            domain=current_user.domain,
            template_data=template_data,
            created_at=_now(),
            updated_at=_now(),
        )
        db.session.add(template)
        db.session.flush()
        _record_audit("template_created", "RequestTemplate", template.id)
        db.session.commit()
        return jsonify({"item": RequestTemplateSchema().dump(template)}), 201

    @app.route("/api/config/approval-rules", methods=["GET"])
    @login_required
    def api_approval_rules():
        items = ApprovalRule.query.filter_by(domain=current_user.domain, is_active=True).all()
        return jsonify({"items": [dict(id=i.id, name=i.name, conditions=i.conditions, approver_roles=i.approver_roles) for i in items]})

    @app.route("/api/config/rejection-reasons", methods=["GET"])
    @login_required
    def api_rejection_reasons():
        items = RejectionReason.query.filter_by(is_active=True).all()
        return jsonify({"items": [dict(id=i.id, code=i.code, reason=i.reason) for i in items]})

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
