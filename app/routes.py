from datetime import datetime, timezone
import urllib.request
import urllib.parse
import json

from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from slugify import slugify

from app.extensions import db
from app.models import User, Post, Tag
from app.forms import LoginForm, RegistrationForm, PostForm
from app.decorators import author_required, admin_required
from app.utils import render_markdown


def register_routes(app):
    def _verify_recaptcha(response_token):
        """Returns True if reCAPTCHA response is valid."""
        secret = current_app.config["RECAPTCHA_SECRET_KEY"]
        payload = urllib.parse.urlencode(
            {
                "secret": secret,
                "response": response_token,
                "remoteip": request.remote_addr,
            }
        ).encode()
        try:
            with urllib.request.urlopen(
                "https://www.google.com/recaptcha/api/siteverify",
                data=payload,
                timeout=5,
            ) as resp:
                result = json.loads(resp.read())
                return result.get("success", False)
        except Exception:
            return False

    def _unique_slug(title: str) -> str:
        base = slugify(title)
        slug = base
        counter = 1
        while Post.query.filter_by(slug=slug).first():
            slug = f"{base}-{counter}"
            counter += 1
        return slug

    def _sync_tags(post: Post, tags_raw: str) -> None:
        """Parse comma-separated tag string and update post.tags."""
        post.tags = []
        if not tags_raw:
            return
        for name in {t.strip().lower() for t in tags_raw.split(",") if t.strip()}:
            tag = Tag.query.filter_by(name=name).first() or Tag(name=name)
            db.session.add(tag)
            post.tags.append(tag)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        form = RegistrationForm()
        if form.validate_on_submit():
            is_first_user = User.query.count() == 0
            user = User(
                username=form.username.data,
                email=form.email.data,
                role="admin" if is_first_user else form.role.data,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash(
                f"Account created! {'You are the admin.' if is_first_user else 'You can now log in.'}",
                "success",
            )
            return redirect(url_for("login"))

        return render_template("auth/register.html", form=form, title="Register")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        form = LoginForm()
        if form.validate_on_submit():
            recaptcha_token = request.form.get("g-recaptcha-response", "")
            if not recaptcha_token:
                flash("Please complete the reCAPTCHA.", "danger")
                return render_template("auth/login.html", form=form, title="Log In")
            if not _verify_recaptcha(recaptcha_token):
                flash("reCAPTCHA verification failed. Please try again.", "danger")
                return render_template("auth/login.html", form=form, title="Log In")

            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember.data)
                next_page = request.args.get("next")
                flash(f"Welcome back, {user.username}!", "success")
                return redirect(next_page or url_for("index"))
            flash("Invalid email or password.", "danger")

        return render_template("auth/login.html", form=form, title="Log In")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for("index"))

    @app.route("/")
    def index():
        page = request.args.get("page", 1, type=int)
        tag_filter = request.args.get("tag")
        query = Post.query.filter_by(published=True).order_by(Post.created_at.desc())
        if tag_filter:
            query = query.join(Post.tags).filter(Tag.name == tag_filter)
        posts = query.paginate(page=page, per_page=8, error_out=False)
        tags = Tag.query.order_by(Tag.name).all()
        return render_template(
            "index.html", posts=posts, tags=tags, tag_filter=tag_filter, title="Home"
        )

    @app.route("/post/<slug>")
    def post_detail(slug):
        post = Post.query.filter_by(slug=slug).first_or_404()
        if not post.published and (
            not current_user.is_authenticated
            or (current_user.id != post.author_id and not current_user.is_admin())
        ):
            abort(404)
        return render_template("post.html", post=post, title=post.title)

    @app.route("/create", methods=["GET", "POST"])
    @login_required
    @author_required
    def create_post():
        form = PostForm()
        if form.validate_on_submit():
            slug = _unique_slug(form.title.data)
            post = Post(
                title=form.title.data,
                slug=slug,
                body_md=form.body_md.data,
                body_html=render_markdown(form.body_md.data),
                author_id=current_user.id,
                published=form.published.data,
            )
            _sync_tags(post, form.tags.data)
            db.session.add(post)
            db.session.commit()
            flash("Post created successfully!", "success")
            return redirect(url_for("post_detail", slug=post.slug))

        return render_template(
            "editor.html", form=form, title="New Post", action="create"
        )

    @app.route("/edit/<int:post_id>", methods=["GET", "POST"])
    @login_required
    def edit_post(post_id):
        post = Post.query.get_or_404(post_id)
        if current_user.id != post.author_id and not current_user.is_admin():
            abort(403)

        form = PostForm(obj=post)
        if request.method == "GET":
            form.tags.data = ", ".join(t.name for t in post.tags)

        if form.validate_on_submit():
            post.title = form.title.data
            post.body_md = form.body_md.data
            post.body_html = render_markdown(form.body_md.data)
            post.published = form.published.data
            post.updated_at = datetime.now(timezone.utc)
            _sync_tags(post, form.tags.data)
            db.session.commit()
            flash("Post updated!", "success")
            return redirect(url_for("post_detail", slug=post.slug))

        return render_template(
            "editor.html", form=form, title="Edit Post", post=post, action="edit"
        )

    @app.route("/delete/<int:post_id>", methods=["POST"])
    @login_required
    def delete_post(post_id):
        post = Post.query.get_or_404(post_id)
        if current_user.id != post.author_id and not current_user.is_admin():
            abort(403)
        db.session.delete(post)
        db.session.commit()
        flash("Post deleted.", "info")
        return redirect(url_for("index"))

    @app.route("/my-posts")
    @login_required
    def my_posts():
        posts = (
            Post.query.filter_by(author_id=current_user.id)
            .order_by(Post.created_at.desc())
            .all()
        )
        return render_template("my_posts.html", posts=posts, title="My Posts")

    @app.route("/admin/dashboard")
    @login_required
    @admin_required
    def dashboard():
        users = User.query.order_by(User.created_at.desc()).all()
        posts = Post.query.order_by(Post.created_at.desc()).all()
        return render_template(
            "admin/dashboard.html", users=users, posts=posts, title="Admin Dashboard"
        )

    @app.route("/admin/user/<int:user_id>/role", methods=["POST"])
    @login_required
    @admin_required
    def change_role(user_id):
        user = User.query.get_or_404(user_id)
        new_role = request.form.get("role")
        if new_role not in ("reader", "author", "admin"):
            abort(400)
        user.role = new_role
        db.session.commit()
        flash(f"{user.username}'s role changed to {new_role}.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/admin/user/<int:user_id>/delete", methods=["POST"])
    @login_required
    @admin_required
    def delete_user(user_id):
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        flash(f"User {user.username!r} deleted.", "info")
        return redirect(url_for("dashboard"))

    @app.route("/admin/post/<int:post_id>/toggle", methods=["POST"])
    @login_required
    @admin_required
    def toggle_published(post_id):
        post = Post.query.get_or_404(post_id)
        post.published = not post.published
        db.session.commit()
        state = "published" if post.published else "unpublished"
        flash(f"Post '{post.title}' {state}.", "success")
        return redirect(url_for("dashboard"))
