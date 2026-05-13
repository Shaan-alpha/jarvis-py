# data/profile/

Jarvis stores your profile here in `user_profile.json`. This is your
own data — gitignored.

## Auto-managed

The app populates this file as you talk to Jarvis. Phrases that match
the regex patterns in `core/memory/profile_extractor.py` get captured:

| You say | Stored as |
|---|---|
| "my name is …" | `name` |
| "i am preparing for …" | `goal` |
| "my favorite programming language is …" | `favorite_language` |
| "i like …" | `likes` |

## Manual seed

You can also seed it yourself. Create `user_profile.json` next to this
README, e.g.:

```json
{
    "name": "Your Name",
    "role": "Engineering Student",
    "college": "Your College",
    "interests": ["AI", "Backend Development"]
}
```

Jarvis injects this into every LLM prompt so it knows who it's talking
to (greeting, context grounding).
