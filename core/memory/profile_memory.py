import os

from core.paths import user_data_dir

from core.utils.jsonio import (
    read_json,
    write_json_atomic,
)


PROFILE_PATH = os.path.join(
    str(user_data_dir()),
    "data",
    "profile",
    "user_profile.json"
)


def load_profile():

    return read_json(PROFILE_PATH, default={})


def save_profile(profile):

    write_json_atomic(PROFILE_PATH, profile)


def update_profile(
    key,
    value
):

    profile = load_profile()

    profile[key] = value

    save_profile(profile)


LIKES_MAX = 10


def remember_profile(key, value):
    """Store one captured detail. 'likes' accumulates (newest last)."""

    profile = load_profile()

    if key == "likes":

        likes = profile.get("likes", [])

        if isinstance(likes, str):

            likes = [likes]

        likes = [like for like in likes if like != value] + [value]

        profile["likes"] = likes[-LIKES_MAX:]

    else:

        profile[key] = value

    save_profile(profile)


def delete_profile_key(key):

    profile = load_profile()

    if key not in profile:

        return False

    profile.pop(key)

    save_profile(profile)

    return True


def get_profile_context():

    profile = load_profile()

    lines = []

    for key, value in profile.items():

        if isinstance(value, list):

            value = ", ".join(value)

        lines.append(f"{key.replace('_', ' ')}: {value}")

    return "\n".join(lines)
