import json
import os


PROFILE_PATH = (
    "data/profile/user_profile.json"
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