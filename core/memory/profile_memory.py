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


def get_profile_context():

    profile = load_profile()

    if not profile:

        return ""

    context = []

    for key, value in profile.items():

        context.append(
            f"{key}: {value}"
        )

    return "\n".join(context)
