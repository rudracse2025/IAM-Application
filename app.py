import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

from models import db, User, EmployeeRequest, Provisioning, Approval

load_dotenv()

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

STATUS_PENDING_IT = "PENDING_IT"
STATUS_PENDING_APPROVAL = "PENDING_APPROVAL"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"

APPROVAL_PENDING = "PENDING"
APPROVAL_APPROVED = "APPROVED"
APPROVAL_REJECTED = "REJECTED"


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
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

    def role_required(*roles):
        def decorator(func):
            def wrapper(*args, **kwargs):
                if current_user.role not in roles:
                    abort(403)
                return func(*args, **kwargs)
            wrapper.__name__ = func.__name__
            return wrapper
        return decorator

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

            if User.query.filter_by(email=email).first():
                flash("Email already registered.", "danger")
                return redirect(url_for("signup"))

            user = User(
                email=email,
                role=role,
                domain=domain,
                password_hash=generate_password_hash(password),
                created_at=datetime.utcnow(),
            )
            db.session.add(user)
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
            if not user or not check_password_hash(user.password_hash, password):
                flash("Invalid credentials.", "danger")
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
            requests = EmployeeRequest.query.filter_by(domain=domain, status=STATUS_PENDING_APPROVAL).order_by(EmployeeRequest.created_at.desc()).all()
        return render_template("dashboard.html", requests=requests, role=current_user.role)

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
                created_at=datetime.utcnow(),
            )
            db.session.add(req)
            db.session.commit()
            flash("Request submitted to IT Admin.", "success")
            return redirect(url_for("dashboard"))

        return render_template("hr_request.html")

    @app.route("/it/provision/<int:request_id>", methods=["GET", "POST"])
    @login_required
    @role_required(ROLE_IT)
    def it_provision(request_id):
        req = EmployeeRequest.query.filter_by(id=request_id, domain=current_user.domain).first_or_404()
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
                created_at=datetime.utcnow(),
            )
            req.status = STATUS_PENDING_APPROVAL
            db.session.add(provisioning)
            db.session.commit()
            flash("Provisioning submitted for approval.", "success")
            return redirect(url_for("dashboard"))

        return render_template("it_provision.html", request_item=req)

    @app.route("/approvals")
    @login_required
    @role_required(ROLE_CISO, ROLE_MGMT)
    def approvals():
        requests_pending = EmployeeRequest.query.filter_by(domain=current_user.domain, status=STATUS_PENDING_APPROVAL).order_by(EmployeeRequest.created_at.desc()).all()
        return render_template("approvals.html", requests=requests_pending)

    @app.route("/approvals/<int:request_id>/approve", methods=["POST"])
    @login_required
    @role_required(ROLE_CISO, ROLE_MGMT)
    def approve_request(request_id):
        req = EmployeeRequest.query.filter_by(id=request_id, domain=current_user.domain).first_or_404()
        decision = request.form.get("decision")
        if decision not in [APPROVAL_APPROVED, APPROVAL_REJECTED]:
            flash("Invalid decision.", "danger")
            return redirect(url_for("approvals"))

        existing = Approval.query.filter_by(request_id=req.id, approver_id=current_user.id).first()
        if existing:
            existing.status = decision
            existing.created_at = datetime.utcnow()
        else:
            approval = Approval(
                request_id=req.id,
                approver_id=current_user.id,
                role=current_user.role,
                status=decision,
                created_at=datetime.utcnow(),
            )
            db.session.add(approval)

        db.session.commit()

        approvals = Approval.query.filter_by(request_id=req.id).all()
        roles_approved = {a.role for a in approvals if a.status == APPROVAL_APPROVED}
        roles_rejected = {a.role for a in approvals if a.status == APPROVAL_REJECTED}

        if roles_rejected:
            req.status = STATUS_REJECTED
        elif ROLE_CISO in roles_approved and ROLE_MGMT in roles_approved:
            req.status = STATUS_APPROVED

        db.session.commit()
        flash("Decision saved.", "success")
        return redirect(url_for("approvals"))

    @app.route("/status/<int:request_id>")
    @login_required
    def request_status(request_id):
        req = EmployeeRequest.query.filter_by(id=request_id, domain=current_user.domain).first_or_404()
        return render_template("status.html", request_item=req)

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
