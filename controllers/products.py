"""Cadastro, edição e exclusão de produtos e serviços."""
from decimal import Decimal, InvalidOperation
import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for, abort

from controllers.auth import login_required
from models.product import create_product, delete_product, get_product, list_products, update_product

products_bp = Blueprint("products", __name__, url_prefix="/products")
PRODUCT_NAME_LIMIT = 120
DESCRIPTION_LIMIT = 2000


def parse_unit_price(value: str) -> int:
    """Converte preço decimal em centavos, aceitando vírgula ou ponto decimal."""
    normalized = value.strip().replace("R$", "").replace(" ", "")
    if not normalized:
        raise ValueError("Informe o preço unitário.")
    if len(normalized) > 32:
        raise ValueError("O preço informado é muito longo.")
    grouped_brl = re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?", normalized)
    decimal_number = re.fullmatch(r"\d+(?:[,.]\d{1,2})?", normalized)
    if grouped_brl:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif decimal_number:
        normalized = normalized.replace(",", ".")
    else:
        raise ValueError("Informe um preço válido com até duas casas decimais.")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError("Informe um preço válido, como 125,00.") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("O preço deve ser um valor igual ou maior que zero.")
    if amount.as_tuple().exponent < -2:
        raise ValueError("O preço pode ter no máximo duas casas decimais.")
    if amount > Decimal("92233720368547758.07"):
        raise ValueError("O preço informado ultrapassa o limite aceito pelo sistema.")
    return int(amount * 100)


def validate_product_form(form):
    values = {
        "name": form.get("name", "").strip(),
        "description": form.get("description", "").strip(),
    }
    errors = {}
    if not values["name"]:
        errors["name"] = "Informe o nome do produto ou serviço."
    elif len(values["name"]) > PRODUCT_NAME_LIMIT:
        errors["name"] = f"O nome deve ter até {PRODUCT_NAME_LIMIT} caracteres."
    if len(values["description"]) > DESCRIPTION_LIMIT:
        errors["description"] = f"A descrição deve ter até {DESCRIPTION_LIMIT} caracteres."
    try:
        values["unit_price_cents"] = parse_unit_price(form.get("unit_price", ""))
    except ValueError as exc:
        errors["unit_price"] = str(exc)
    return values, errors


def price_for_form(cents: int) -> str:
    return f"{cents // 100},{cents % 100:02d}"


@products_bp.get("")
@login_required
def index():
    products = list_products(current_app.config["DATABASE_PATH"])
    return render_template("products/list.html", products=products)


@products_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    product = {"name": "", "description": "", "unit_price": ""}
    if request.method == "POST":
        values, errors = validate_product_form(request.form)
        product = {**values, "unit_price": request.form.get("unit_price", "").strip()}
        if errors:
            for message in errors.values():
                flash(message, "error")
            return render_template("products/form.html", product=product, editing=False), 422
        create_product(current_app.config["DATABASE_PATH"], values)
        flash("Produto ou serviço cadastrado com sucesso.", "success")
        return redirect(url_for("products.index"))
    return render_template("products/form.html", product=product, editing=False)


@products_bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit(product_id: int):
    product = get_product(current_app.config["DATABASE_PATH"], product_id)
    if product is None:
        abort(404)
    if request.method == "POST":
        values, errors = validate_product_form(request.form)
        form_product = {**values, "unit_price": request.form.get("unit_price", "").strip()}
        if errors:
            for message in errors.values():
                flash(message, "error")
            return render_template("products/form.html", product=form_product, editing=True), 422
        update_product(current_app.config["DATABASE_PATH"], product_id, values)
        flash("Produto ou serviço atualizado.", "success")
        return redirect(url_for("products.index"))
    return render_template(
        "products/form.html",
        product={**dict(product), "unit_price": price_for_form(product["unit_price_cents"])},
        editing=True,
    )


@products_bp.post("/<int:product_id>/delete")
@login_required
def delete(product_id: int):
    result = delete_product(current_app.config["DATABASE_PATH"], product_id)
    if result == "deleted":
        flash("Produto ou serviço excluído.", "success")
    elif result == "linked":
        flash("Este produto está vinculado a um orçamento e não pode ser excluído.", "error")
    else:
        abort(404)
    return redirect(url_for("products.index"))
