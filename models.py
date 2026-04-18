from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import JSONType


db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    domain = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    department = db.Column(db.String(255))
    profile_pic_url = db.Column(db.String(500))
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    preferences = db.Column(JSONType, nullable=False, default=lambda: {})
    two_factor_enabled = db.Column(db.Boolean, nullable=False, default=False)
    two_factor_method = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)


class EmployeeRequest(db.Model):
    __tablename__ = "employee_request"

    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(255), nullable=False)
    requested_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    employee_name = db.Column(db.String(255), nullable=False)
    employee_email = db.Column(db.String(255), nullable=False)
    job_title = db.Column(db.String(255))
    department = db.Column(db.String(255))
    manager_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    notes = db.Column(db.Text)
    rejection_reason = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    priority = db.Column(db.String(20), nullable=False, default="MEDIUM")
    status = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)


class Provisioning(db.Model):
    __tablename__ = "provisioning"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("employee_request.id"), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    it_user_id = db.Column(db.String(255), nullable=False)
    license_type = db.Column(db.String(255), nullable=False)
    security_groups = db.Column(db.Text)
    status = db.Column(db.String(50), nullable=False, default="PENDING")
    deployment_details = db.Column(JSONType, nullable=False, default=lambda: {})
    resource_allocation = db.Column(JSONType, nullable=False, default=lambda: {})
    mfa_enforced = db.Column(db.Boolean, nullable=False, default=False)
    security_baseline_applied = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Approval(db.Model):
    __tablename__ = "approval"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("employee_request.id"), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    comments = db.Column(db.Text)
    decision_timestamp = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class RequestTimeline(db.Model):
    __tablename__ = "request_timeline"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("employee_request.id"), nullable=False, index=True)
    changed_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    from_status = db.Column(db.String(50))
    to_status = db.Column(db.String(50), nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    action = db.Column(db.String(100), nullable=False, index=True)
    entity_type = db.Column(db.String(100), nullable=False)
    entity_id = db.Column(db.Integer)
    audit_metadata = db.Column(JSONType, nullable=False, default=lambda: {})
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class Notification(db.Model):
    __tablename__ = "notification"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default="INFO")
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime)


class Comment(db.Model):
    __tablename__ = "comment"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("employee_request.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)


class RequestTemplate(db.Model):
    __tablename__ = "request_template"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    domain = db.Column(db.String(255), nullable=False, index=True)
    template_data = db.Column(JSONType, nullable=False, default=lambda: {})
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ApprovalRule(db.Model):
    __tablename__ = "approval_rule"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    domain = db.Column(db.String(255), nullable=False, index=True)
    conditions = db.Column(JSONType, nullable=False, default=lambda: {})
    approver_roles = db.Column(JSONType, nullable=False, default=lambda: [])
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class RejectionReason(db.Model):
    __tablename__ = "rejection_reason"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    reason = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
