"""Pure resolution of the four Allure custom-field values from CLI flags + config defaults,
and the pre-flight that decides whether the looked-up values are already in use in the project.
stdlib-only, no network: the orchestrator performs the lookups and feeds the results in."""

from plan_parser import E2E_SCOPE, normalise_scope

# Fields whose value must already exist in the project. `Suite` is absent on purpose:
# Allure creates Suite values on the fly, so it is composed and never looked up.
VERIFIED_FIELDS = ("Story", "Component", "Feature")

# Under the e2e test scope the Feature is the scope itself, decided here — before Gate 0b's
# by-value lookup — so the pre-flight verifies the value that actually ships.
E2E_FEATURE = "e2e scope"

_FLAG = {"Story": "--story-field", "Component": "--component", "Feature": "--feature"}
_CONFIG_KEY = {"Story": "story", "Component": "component", "Feature": "feature"}


def _clean(value):
    return value.strip() if isinstance(value, str) else ""


def resolve_custom_fields(config, *, story_key, story_title, story_field=None, component=None, feature=None, scope=None):
    """Resolve Suite/Story/Component/Feature: a flag beats the `testops.custom_fields` default.
    Returns {"fields": {name: value} for every value we have, "missing": [names], "errors": [msgs]}.
    A value that is absent or blank is reported, never guessed or defaulted to a placeholder.
    Under `scope="e2e"` the Feature is forced to the scope's own value; an explicitly passed
    `feature` then states a different intent from the scope and is reported as an error."""
    defaults = (config.get("testops") or {}).get("custom_fields") or {}
    flags = {"Story": story_field, "Component": component, "Feature": feature}

    fields, missing, errors = {}, [], []

    title = _clean(story_title)
    key = _clean(story_key)
    if title and key:
        fields["Suite"] = "[{}] {}".format(key, title)
    else:
        missing.append("Suite")
        errors.append("Suite cannot be composed: the Jira story key and title are both required "
                      "(got key {!r}, title {!r})".format(story_key, story_title))

    e2e = normalise_scope(scope) == E2E_SCOPE
    if e2e and _clean(feature):
        errors.append("--feature {!r} conflicts with scope {!r}, which sets Feature {!r} — "
                      "drop --feature or change the scope"
                      .format(_clean(feature), E2E_SCOPE, E2E_FEATURE))

    for name in VERIFIED_FIELDS:
        if e2e and name == "Feature":
            fields[name] = E2E_FEATURE
            continue
        value = _clean(flags[name]) or _clean(defaults.get(_CONFIG_KEY[name]))
        if value:
            fields[name] = value
        else:
            missing.append(name)
            errors.append("{} has no value — pass {} or set testops.custom_fields.{} in config.json"
                          .format(name, _FLAG[name], _CONFIG_KEY[name]))
    return {"fields": fields, "missing": missing, "errors": errors}


def _hit_count(result):
    """A lookup result is either a count or the returned list of cases. Anything else is no proof."""
    if isinstance(result, bool):
        return 0
    if isinstance(result, int):
        return max(result, 0)
    if isinstance(result, (list, tuple)):
        return len(result)
    if isinstance(result, dict):
        return _hit_count(result.get("content", result.get("totalElements", 0)))
    return 0


def _unverified(name, value, project_name):
    return ("{} '{}' — no existing test case in project {} uses this value. If it exists in "
            "Allure but is unused, re-run with --allow-unverified-fields."
            .format(name, value, project_name or "?"))


def check_field_values(fields, lookups, project_name="", allow_unverified=False):
    """Pre-flight over one by-value lookup result per verified field. A hit proves the value is
    in use; zero hits proves nothing more than that, so the report says what was checked.
    Unverified values abort by default and become warnings under `allow_unverified`.
    `Suite` is never looked up."""
    errors, warnings, checked = [], [], []
    for name in VERIFIED_FIELDS:
        if name not in fields:
            continue
        checked.append(name)
        if _hit_count(lookups.get(name)) < 1:
            message = _unverified(name, fields[name], project_name)
            if allow_unverified:
                warnings.append(message)
            else:
                errors.append(message)
    return {"ok": not errors, "errors": errors, "warnings": warnings, "checked": checked}
