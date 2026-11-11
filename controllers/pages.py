"""Páginas protegidas disponíveis nesta fase."""
from flask import Blueprint, render_template

from controllers.auth import login_required

pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/")
@login_required
def dashboard():
    return render_template("dashboard.html")
