"""FB-12: administrators approve or reject organisation accounts (FR-01)."""
import logging
from typing import Any

from flask import Blueprint, abort, flash, g, redirect, render_template, url_for

from .auth import role_required
from .db import get_db

bp = Blueprint("admin", __name__, url_prefix="/admin")
log = logging.getLogger(__name__)

DECISIONS = {"approve": "approved", "reject": "rejected"}


@bp.route("/accounts")
@role_required("admin")
def accounts() -> str:
    # Pending accounts first, so the admin sees what needs a decision.
    users = get_db().execute(
        "SELECT id, email, org_name, role, status, created_at FROM users"
        " WHERE role != 'admin'"
        " ORDER BY status = 'pending' DESC, created_at"
    ).fetchall()
    return render_template("admin/accounts.html", users=users)


@bp.route("/accounts/<int:user_id>/<decision>", methods=("POST",))
@role_required("admin")
def decide(user_id: int, decision: str) -> Any:
    if decision not in DECISIONS:
        abort(404)
    db = get_db()
    # LEARN: "role != 'admin'" in the WHERE clause means this route can never
    # change another admin's account, even if someone edits the user id in the URL.
    cur = db.execute(
        "UPDATE users SET status = ? WHERE id = ? AND role != 'admin'",
        (DECISIONS[decision], user_id),
    )
    if cur.rowcount == 0:
        abort(404)
    db.commit()
    log.info("Admin %s set user %s to %s", g.user["id"], user_id, DECISIONS[decision])
    flash(f"Account {DECISIONS[decision]}.")
    return redirect(url_for("admin.accounts"))
