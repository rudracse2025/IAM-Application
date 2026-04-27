from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin


db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    domain = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime)


class EmployeeRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(255), nullable=False)
    requested_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    first_name = db.Column(db.String(255))
    middle_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    employee_name = db.Column(db.String(255), nullable=False)
    employee_email = db.Column(db.String(255), nullable=False)
    gender = db.Column(db.String(50))
    job_title = db.Column(db.String(255))
    work_mode = db.Column(db.String(50))
    work_location = db.Column(db.String(255))
    company_email = db.Column(db.String(255))
    status = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime)


class Provisioning(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("employee_request.id"), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    it_user_id = db.Column(db.String(255), nullable=False)
    license_type = db.Column(db.String(255), nullable=False)
    security_groups = db.Column(db.Text)
    assign_license = db.Column(db.Boolean)
    password_reset_required = db.Column(db.Boolean)
    block_user = db.Column(db.Boolean)
    mfa_reset_required = db.Column(db.Boolean)
    mailbox_creation_required = db.Column(db.Boolean)
    account_access_action = db.Column(db.String(20))
    created_at = db.Column(db.DateTime)


class Approval(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("employee_request.id"), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime)


class RequestAudit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("employee_request.id"), nullable=False)
    event_type = db.Column(db.String(80), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    actor_email = db.Column(db.String(255))
    actor_role = db.Column(db.String(50))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False)
