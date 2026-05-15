from flask import redirect, render_template, request

from app.models.user import User
from app.config.database import db

def get_all_users():
    users = User.query.all()

    return render_template(
        "users/index.html",
        users=users
    )

def create_form():
    return render_template(
        "users/create.html",
    )

def create_user():
    fullname = request.form["fullname"]
    username = request.form["username"]

    user = User(
            fullname=fullname, 
            username=username,
            score=0
        )
    db.session.add(user)
    db.session.commit()

    return redirect("/")

def edit_form(id):
    user = User.query.get_or_404(id)

    return render_template(
        "users/edit.html",
        user=user
    )

def update_user():
    user = User.query.get_or_404(id)
    user.fullname = request.form["fullname"]
    user.username = request.form["username"]

    db.session.commit()
    return redirect("/users")

def delete_user(id):
    user = User.query.get_or_404(id)

    db.session.delete(user)
    db.session.commit()

    return redirect("/users")