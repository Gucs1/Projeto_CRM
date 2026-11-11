"""Páginas protegidas disponíveis nesta fase."""
from flask import Blueprint, current_app, render_template

from controllers.auth import login_required
from models.quote import get_dashboard_data

pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/")
@login_required
def dashboard():
    data = get_dashboard_data(current_app.config["DATABASE_PATH"])
    return render_template("dashboard.html", quote_counts=data["counts"], recent_quotes=data["recent"])
