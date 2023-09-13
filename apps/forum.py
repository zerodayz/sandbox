from flask import (Flask, jsonify, redirect, render_template, request, session,
                   url_for, flash)

import apps.user as user_utils
from apps.apps import check_login

from models import db
from models import ForumPost, ForumComment, ForumCategory

import re


def get_last_5_posts_by_category(category_id):
    last_5_posts = (ForumPost.query.filter_by(category_id=category_id)
                    .order_by(ForumPost.date_created.desc())
                    .limit(5)
                    .all())

    return last_5_posts


def forum_search():
    search_query = request.args.get('query', '')
    page = request.args.get("page", 1, type=int)
    items_per_page = 10

    if not search_query:
        return redirect(url_for("forum_board"))
    search_query_bytes = search_query.encode("utf-8")

    posts = (ForumPost.query.filter(ForumPost.title.contains(search_query) | ForumPost.content
                                    .contains(search_query_bytes))
             .order_by(ForumPost.date_created.desc())
             .paginate(page=page, per_page=items_per_page))

    for post in posts.items:
        post.search = []
        search_indexes = []
        post.tmp = post.content.decode("utf-8").split()

        post.title = re.sub(search_query, "<mark>" + search_query + "</mark>",
                            post.title, flags=re.IGNORECASE)

        for i, word in enumerate(post.tmp):
            if re.search(search_query, word, re.IGNORECASE):
                search_indexes.append(i)

        for i in search_indexes:
            if i - 5 < 0:
                post.search.extend(post.tmp[0:i + 5])
            else:
                post.search.extend(post.tmp[i - 5:i + 5])

    try:
        post.search = " ".join(post.search)
        post.search = re.sub(search_query, "<mark>" + search_query + "</mark>", post.search, flags=re.IGNORECASE)
    except:
        pass

    return render_template("/forum/search.html", posts=posts, query=search_query, page=page,
                           items_per_page=items_per_page)


def forum_board():
    posts = ForumPost.query.all()
    categories = ForumCategory.query.all()
    return render_template("/forum/board.html", posts=posts, categories=categories,
                           get_last_5_posts_by_category=get_last_5_posts_by_category)


def create_post():
    if not check_login():
        return redirect(url_for("login"))

    user = user_utils.get_user_by_username(session["username"])
    category_id = request.args.get('category_id', 1, type=int)

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        category_id = request.form.get("category_id")
        encoded_content = content.encode("utf-8")
        user_id = user.id

        new_post = ForumPost(title=title, content=encoded_content, user_id=user_id, category_id=category_id)
        db.session.add(new_post)

        category = ForumCategory.query.get(category_id)
        if category:
            new_post.categories = category

        db.session.commit()

        return redirect(url_for("forum_board"))

    categories = ForumCategory.query.all()
    return render_template("/forum/post/create.html", categories=categories, category_id=category_id)


def view_category(category_id):
    if not check_login():
        return redirect(url_for("login"))

    user = user_utils.get_user_by_username(session["username"])
    category = ForumCategory.query.get_or_404(category_id)

    page = request.args.get("page", 1, type=int)
    items_per_page = 10

    posts = (ForumPost.query.filter_by(category_id=category_id)
             .order_by(ForumPost.date_created.desc())
             .paginate(page=page, per_page=items_per_page))

    return render_template("/forum/category/view.html", user=user, category=category, posts=posts)


def view_post(post_id):
    if not check_login():
        return redirect(url_for("login"))

    user = user_utils.get_user_by_username(session["username"])
    post = ForumPost.query.get_or_404(post_id)
    markdown_content = post.content.decode("utf-8")
    if request.method == "POST":
        content = request.form["content"]

        user_id = user.id

        new_comment = ForumComment(content=content, user_id=user_id, post=post)
        db.session.add(new_comment)
        db.session.commit()

        return redirect(url_for("view_post", post_id=post_id))

    return render_template("/forum/post/post.html", user=user, post=post, markdown_content=markdown_content)


def delete_post(post_id):
    if not check_login():
        return redirect(url_for("login"))

    user = user_utils.get_user_by_username(session["username"])
    post = ForumPost.query.get_or_404(post_id)

    if post.user_id == user.id:
        ForumComment.query.filter_by(post_id=post_id).delete()
        db.session.delete(post)
        db.session.commit()

    return redirect(url_for("forum_board"))


def delete_comment(comment_id):
    if not check_login():
        return redirect(url_for("login"))

    user = user_utils.get_user_by_username(session["username"])
    comment = ForumComment.query.get_or_404(comment_id)

    if comment.user_id == user.id:
        db.session.delete(comment)
        db.session.commit()

    return redirect(url_for("view_post", post_id=comment.post_id))


def create_category():
    if not check_login():
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form["name"]
        if ForumCategory.query.filter_by(name=name).first():
            flash("Category name already exists, please choose another name.", "danger")
            return render_template("/forum/category/create.html")

        user = user_utils.get_user_by_username(session["username"])
        color = request.form["color"]
        description = request.form["description"]
        new_category = ForumCategory(name=name, category_description=description, category_color=color, user_id=user.id)
        db.session.add(new_category)
        db.session.commit()
        flash("Category created successfully", "success")
        return redirect(url_for("forum_board"))

    return render_template("/forum/category/create.html")


def edit_category(category_id):
    if not check_login():
        return redirect(url_for("login"))

    category = ForumCategory.query.get_or_404(category_id)

    if request.method == "POST":
        name = request.form["name"]

        category.name = name
        db.session.commit()
        flash("Category edited successfully", "success")
        return redirect(url_for("forum_board"))

    return render_template("/forum/category/edit.html", category=category)


def delete_category(category_id):
    if not check_login():
        return redirect(url_for("login"))

    category = ForumCategory.query.get_or_404(category_id)

    posts = ForumPost.query.filter_by(category_id=category_id).all()
    for post in posts:
        ForumComment.query.filter_by(post_id=post.id).delete()
        db.session.delete(post)

    db.session.delete(category)
    db.session.commit()

    flash("Category deleted successfully", "success")
    return redirect(url_for("forum_board"))
