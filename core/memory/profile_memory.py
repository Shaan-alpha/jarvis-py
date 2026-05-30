import json
import os

from core.paths import user_data_dir


PROFILE_PATH = os.path.join(
    str(user_data_dir()),
    "data",
    "profile",
    "user_profile.json"
)


def load_profile():

    if not os.path.exists(
        PROFILE_PATH
    ):

        return {}

    with open(
        PROFILE_PATH,
        "r"
    ) as file:

        return json.load(file)


def save_profile(profile):

    os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)

    with open(
        PROFILE_PATH,
        "w"
    ) as file:

        json.dump(
            profile,
            file,
            indent=4
        )


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
