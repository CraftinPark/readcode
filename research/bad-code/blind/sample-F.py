from datetime import datetime
from flask import (
    render_template,
    flash,
    redirect,
    url_for,
    request,
    g,
    jsonify,
    current_app,
)
from flask_login import current_user, login_required
from app import db
from app.main.forms import EditProfileForm, CreateResourceForm
from app.models import User, Resource
from app.main import bp


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@bp.route("/", methods=["GET", "POST"])
@bp.route("/index", methods=["GET", "POST"])
@login_required
def index():

    return render_template("index.html")


@bp.route("/explore")
@login_required
def explore():
    page = request.args.get("page", 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config["POSTS_PER_PAGE"], False
    )
    next_url = url_for("main.explore", page=posts.next_num) if posts.has_next else None
    prev_url = url_for("main.explore", page=posts.prev_num) if posts.has_prev else None
    return render_template(
        "index.html",
        title="Explore",
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url,
    )


@bp.route("/user/<username>")
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get("page", 1, type=int)

    return render_template("user.html", user=user)


@bp.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Your changes have been saved.")
        return redirect(url_for("main.edit_profile"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template("edit_profile.html", title="Edit Profile", form=form)


@bp.route("/resources", methods=["GET", "POST"])
@login_required
def list_resources():
    """
    List all resources for a user
    """
    resources = current_user.resources

    return render_template(
        "resources.html", resources=resources, title="Resources", user=current_user
    )


@bp.route("/resources/add", methods=["GET", "POST"])
@login_required
def create_resource():
    form = CreateResourceForm()
    if form.validate_on_submit():
        print(form)
        print(form.name.data)
        print(form.description.data)
        resource = Resource(
            name=form.name.data,
            description=form.description.data,
            user_id=current_user.id,
        )
        try:

            db.session.add(resource)
            db.session.commit()
            flash("Resource added.")
        except:
            flash("error adding resource. :(")
        return redirect(url_for("main.list_resources"))
    elif request.method == "GET":
        # load editing data into form
        pass
    return render_template(
        "create_resource.html", title="Add a bookable resource", form=form
    )


@bp.route("/resources/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_resource(id):
    """
    Edit a resource
    """
    # check_admin()

    # add_department = False

    resource = Resource.query.get_or_404(id)
    # form = CreateResourceForm(obj=resource)
    form = CreateResourceForm()
    print(form)
    if form.validate_on_submit():
        resource.name = form.name.data
        resource.description = form.description.data
        db.session.commit()
        flash("You have successfully edited the resource.")

        # redirect to the resource page
        return redirect(url_for("main.list_resources"))

    form.description.data = resource.description
    form.name.data = resource.name

    # return render_template('create_resource.html', resource=resource, title='Resources', user=current_user)
    return render_template(
        "create_resource.html", title="Edit a bookable resource", form=form
    )


@bp.route("/resources/delete/<int:id>", methods=["GET", "POST"])
@login_required
def delete_resource(id):
    """
    Delete a resource from the database
    """
    # check_admin()
    try:
        resource = Resource.query.get_or_404(id)
        db.session.delete(resource)
        db.session.commit()
        flash("You have successfully deleted the resource.")

    except:
        flash("error deleting resource. :(")

    # redirect to the resources page
    return redirect(url_for("main.list_resources"))


@bp.route("/follow/<username>")
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("User {} not found.".format(username))
        return redirect(url_for("index"))
    if user == current_user:
        flash("You cannot follow yourself!")
        return redirect(url_for("main.user", username=username))
    current_user.follow(user)
    db.session.commit()
    flash("You are following {}!".format(username))
    return redirect(url_for("main.user", username=username))


@bp.route("/unfollow/<username>")
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("User {} not found.".format(username))
        return redirect(url_for("main.index"))
    if user == current_user:
        flash("You cannot unfollow yourself!")
        return redirect(url_for("main.user", username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash("You are not following {}.".format(username))
    return redirect(url_for("main.user", username=username))
