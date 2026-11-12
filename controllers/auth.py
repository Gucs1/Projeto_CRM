"""Rotas de login e logout."""
from functools import wraps

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from models.user import (
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    clear_login_failures,
    create_user,
    get_user_by_username,
    login_is_rate_limited,
    record_login_failure,
    rotate_user_session,
)

auth_bp = Blueprint("auth", __name__)
TERMS_VERSION = "2026-11-12"


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.get("current_user") is None:
            session.clear()
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped_view


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.get("current_user") is not None:
        return redirect(url_for("pages.dashboard"))

    if request.method == "POST":
        username = request.form.get("email", request.form.get("username", "")).strip()
        password = request.form.get("password", "")
        database_path = current_app.config["DATABASE_PATH"]
        remote_address = request.remote_addr or "unknown"
        if login_is_rate_limited(database_path, remote_address):
            flash("Muitas tentativas. Aguarde 15 minutos e tente novamente.", "error")
            return render_template("login.html", mode="login", email=username), 429

        user = get_user_by_username(database_path, username)

        if (user is not None and 0 < len(password) <= MAX_PASSWORD_LENGTH
                and check_password_hash(user["password_hash"], password)):
            session_token = rotate_user_session(database_path, user["id"])
            clear_login_failures(database_path, remote_address)
            session.clear()
            session["user_id"] = user["id"]
            session["session_token"] = session_token
            session.permanent = request.form.get("remember") == "on"
            flash("Acesso realizado com sucesso.", "success")
            return redirect(url_for("pages.dashboard"))

        record_login_failure(database_path, remote_address)
        if login_is_rate_limited(database_path, remote_address):
            flash("Muitas tentativas. Aguarde 15 minutos e tente novamente.", "error")
            return render_template("login.html", mode="login", email=username), 429
        flash("Usuário ou senha inválidos. Confira os dados e tente novamente.", "error")

    return render_template("login.html", mode="login", email="")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if g.get("current_user") is not None:
        return redirect(url_for("pages.dashboard"))

    email = request.form.get("email", "").strip()[:254]
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        accepted_terms = request.form.get("terms_accepted") == "on"

        if not accepted_terms:
            flash("Aceite os termos para criar sua conta.", "error")
        elif len(password) < MIN_PASSWORD_LENGTH or len(password) > MAX_PASSWORD_LENGTH:
            flash("A senha deve ter entre 12 e 128 caracteres.", "error")
        elif password != confirm_password:
            flash("As senhas não conferem.", "error")
        else:
            try:
                user_id = create_user(
                    current_app.config["DATABASE_PATH"], email, password, TERMS_VERSION
                )
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                session_token = rotate_user_session(
                    current_app.config["DATABASE_PATH"], user_id
                )
                session.clear()
                session["user_id"] = user_id
                session["session_token"] = session_token
                session.permanent = True
                flash("Sua conta foi criada. Bem-vindo ao CRM!", "success")
                return redirect(url_for("pages.dashboard"))

    return render_template("login.html", mode="register", email=email)


@auth_bp.get("/legal")
def legal():
    return render_template("legal.html", terms_version=TERMS_VERSION)


@auth_bp.post("/logout")
@login_required
def logout():
    if g.current_user is not None:
        rotate_user_session(current_app.config["DATABASE_PATH"], g.current_user["id"])
    session.clear()
    flash("Você saiu do sistema.", "success")
    return redirect(url_for("auth.login"))
