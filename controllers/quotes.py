"""Criação, visualização, histórico e status de orçamentos."""
import re
from io import BytesIO

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for

from controllers.auth import login_required
from models.client import list_clients
from models.product import list_products
from models.quote import (
    MAX_ITEM_QUANTITY,
    MAX_QUOTE_ITEMS,
    QUOTE_STATUSES,
    create_quote,
    get_quote,
    list_client_quotes,
    list_quotes,
    update_quote_status,
)
from pdf.generator import generate_quote_pdf

quotes_bp = Blueprint("quotes", __name__)
NOTES_LIMIT = 2000


def quote_form_values():
    selected_client_id = request.form.get("client_id", "").strip()
    product_ids = request.form.getlist("product_id")
    quantities = request.form.getlist("quantity")
    notes = request.form.get("notes", "").strip()
    errors = []

    try:
        client_id = int(selected_client_id)
        if client_id <= 0:
            raise ValueError
    except ValueError:
        client_id = None
        errors.append("Selecione um cliente.")

    if not product_ids or len(product_ids) != len(quantities):
        errors.append("Adicione pelo menos um item ao orçamento.")
    elif len(product_ids) > MAX_QUOTE_ITEMS:
        errors.append(f"O orçamento pode conter até {MAX_QUOTE_ITEMS} itens.")

    items = []
    for index, product_value in enumerate(product_ids[:MAX_QUOTE_ITEMS]):
        quantity_value = quantities[index].strip() if index < len(quantities) else ""
        try:
            product_id = int(product_value)
            if product_id <= 0:
                raise ValueError
        except ValueError:
            errors.append("Selecione um produto ou serviço para cada linha.")
            continue
        if not re.fullmatch(r"\d+", quantity_value):
            errors.append("As quantidades devem ser números inteiros positivos.")
            continue
        quantity = int(quantity_value)
        if not 1 <= quantity <= MAX_ITEM_QUANTITY:
            errors.append(f"Cada quantidade deve estar entre 1 e {MAX_ITEM_QUANTITY}.")
            continue
        items.append({"product_id": product_id, "quantity": quantity})

    if len(notes) > NOTES_LIMIT:
        errors.append(f"As observações podem ter até {NOTES_LIMIT} caracteres.")

    return {
        "client_id": client_id,
        "selected_client_id": selected_client_id,
        "product_ids": product_ids[:MAX_QUOTE_ITEMS] or [""],
        "quantities": quantities[:MAX_QUOTE_ITEMS] or ["1"],
        "notes": notes,
        "items": items,
        "errors": errors,
    }


@quotes_bp.get("/quotes")
@login_required
def index():
    quotes = list_quotes(current_app.config["DATABASE_PATH"])
    return render_template("quotes/list.html", quotes=quotes, client=None)


@quotes_bp.route("/quotes/new", methods=["GET", "POST"])
@login_required
def create():
    database_path = current_app.config["DATABASE_PATH"]
    clients = list_clients(database_path)
    products = list_products(database_path)
    if not clients or not products:
        return render_template(
            "quotes/no_catalog.html",
            has_clients=bool(clients),
            has_products=bool(products),
        )

    values = {
        "selected_client_id": "",
        "product_ids": [""],
        "quantities": ["1"],
        "notes": "",
    }
    if request.method == "POST":
        values = quote_form_values()
        if values["errors"]:
            for message in values["errors"]:
                flash(message, "error")
            return render_template(
                "quotes/form.html", clients=clients, products=products, values=values
            ), 422
        try:
            quote_id = create_quote(
                database_path,
                values["client_id"],
                values["notes"],
                values["items"],
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "quotes/form.html", clients=clients, products=products, values=values
            ), 422
        flash("Orçamento criado e salvo como Enviado.", "success")
        return redirect(url_for("quotes.detail", quote_id=quote_id))

    return render_template("quotes/form.html", clients=clients, products=products, values=values)


@quotes_bp.get("/quotes/<int:quote_id>")
@login_required
def detail(quote_id: int):
    result = get_quote(current_app.config["DATABASE_PATH"], quote_id)
    if result is None:
        abort(404)
    return render_template(
        "quotes/detail.html",
        quote=result["quote"],
        items=result["items"],
        statuses=QUOTE_STATUSES,
    )


@quotes_bp.get("/quotes/<int:quote_id>/pdf")
@login_required
def download_pdf(quote_id: int):
    result = get_quote(current_app.config["DATABASE_PATH"], quote_id)
    if result is None:
        abort(404)
    company = {
        "name": current_app.config["COMPANY_NAME"],
        "email": current_app.config["COMPANY_EMAIL"],
        "phone": current_app.config["COMPANY_PHONE"],
        "address": current_app.config["COMPANY_ADDRESS"],
    }
    pdf_bytes = generate_quote_pdf(
        result["quote"],
        result["items"],
        company,
        current_app.config["COMPANY_LOGO"],
    )
    response = send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"orcamento-{quote_id}.pdf",
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@quotes_bp.post("/quotes/<int:quote_id>/status")
@login_required
def status(quote_id: int):
    new_status = request.form.get("status", "")
    if new_status not in QUOTE_STATUSES:
        flash("Selecione um status válido.", "error")
    elif not update_quote_status(current_app.config["DATABASE_PATH"], quote_id, new_status):
        abort(404)
    else:
        flash("Status do orçamento atualizado.", "success")
    return redirect(url_for("quotes.detail", quote_id=quote_id))


@quotes_bp.get("/clients/<int:client_id>/quotes")
@login_required
def client_history(client_id: int):
    result = list_client_quotes(current_app.config["DATABASE_PATH"], client_id)
    if result is None:
        abort(404)
    return render_template(
        "quotes/list.html",
        quotes=result["quotes"],
        client=result["client"],
    )
