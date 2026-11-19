"""FB-04: donors create, edit and withdraw listings (FR-02)."""
from flask import Blueprint, render_template

from .auth import role_required
from .db import get_db

bp = Blueprint("listings", __name__, url_prefix="/listings")


@bp.route("/new", methods=("GET", "POST"))
@role_required("donor")
def create_listing():
    return render_template("listings/listings.html")