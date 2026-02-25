from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager

post_tags = db.Table(
    "post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("post.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="reader")  # reader | author | admin
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    posts = db.relationship("Post", backref="author", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_author_or_admin(self) -> bool:
        return self.role in ("author", "admin")

    def __repr__(self) -> str:
        return f"<User {self.username!r} [{self.role}]>"

@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))

class Tag(db.Model):
    __tablename__ = "tag"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Tag {self.name!r}>"

class Post(db.Model):
    __tablename__ = "post"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    body_md = db.Column(db.Text, nullable=False, default="")
    body_html = db.Column(db.Text, nullable=False, default="")
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    tags = db.relationship("Tag", secondary=post_tags, lazy="subquery", backref=db.backref("posts", lazy=True))

    def __repr__(self) -> str:
        return f"<Post {self.title!r}>"