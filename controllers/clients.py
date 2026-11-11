"""Cadastro, busca, edição e exclusão de clientes."""
import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for, abort

from controllers.auth import login_required
from models.client import create_client, delete_client, get_client, list_clients, update_client

clients_bp = Blueprint("clients", __name__, url_prefix="/clients")

CLIENT_LIMITS = {"name": 120, "email": 254, "phone": 40, "company": 120, "notes": 2000}


def validate_client_form(form):
    values = {field: form.get(field, "").strip() for field in CLIENT_LIMITS}
    errors = {}
    if not values["name"]:
        errors["name"] = "Informe o nome do cliente."
    elif len(values["name"]) > CLIENT_LIMITS["name"]:
        errors["name"] = f"O nome deve ter até {CLIENT_LIMITS['name']} caracteres."
    if values["email"] and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", values["email"]):
        errors["email"] = "Informe um e-mail válido."
    for field, limit in CLIENT_LIMITS.items():
        if field != "name" and len(values[field]) > limit:
            errors[field] = f"Este campo deve ter até {limit} caracteres."
    return values, errors


@clients_bp.get("")
@login_required
def index():
    search = request.args.get("q", "").strip()[:120]
    clients = list_clients(current_app.config["DATABASE_PATH"], search)
    return render_template("clients/list.html", clients=clients, search=search)


@clients_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    values = {field: "" for field in CLIENT_LIMITS}
    if request.method == "POST":
        values, errors = validate_client_form(request.form)
        if errors:
            for message in errors.values():
                flash(message, "error")
            return render_template("clients/form.html", client=values, editing=False), 422
        create_client(current_app.config["DATABASE_PATH"], values)
        flash("Cliente cadastrado com sucesso.", "success")
        return redirect(url_for("clients.index"))
    return render_template("clients/form.html", client=values, editing=False)


@clients_bp.route("/<int:client_id>/edit", methods=["GET", "POST"])
@login_required
def edit(client_id: int):
    client = get_client(current_app.config["DATABASE_PATH"], client_id)
    if client is None:
        abort(404)
    if request.method == "POST":
        values, errors = validate_client_form(request.form)
        if errors:
            for message in errors.values():
                flash(message, "error")
            return render_template("clients/form.html", client=values, editing=True), 422
        update_client(current_app.config["DATABASE_PATH"], client_id, values)
        flash("Dados do cliente atualizados.", "success")
        return redirect(url_for("clients.index"))
    return render_template("clients/form.html", client=client, editing=True)


@clients_bp.post("/<int:client_id>/delete")
@login_required
def delete(client_id: int):
    result = delete_client(current_app.config["DATABASE_PATH"], client_id)
    if result == "deleted":
        flash("Cliente excluído.", "success")
    elif result == "linked":
        flash("Este cliente está vinculado a um orçamento e não pode ser excluído.", "error")
    else:
        abort(404)
    return redirect(url_for("clients.index"))
