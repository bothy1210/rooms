"""Form helpers shared by apps whose forms take typed names instead of drop-downs."""
import re

from django import forms


def typed_input(placeholder, options_id):
    """A text box that suggests existing names (from a <datalist>) but accepts any."""
    return forms.TextInput(attrs={"class": "form-control", "placeholder": placeholder,
                                  "list": options_id, "autocomplete": "off"})


def new_code(model, name, max_length=10, **scope):
    """A short code for a record that was typed in rather than set up beforehand:
    initials of a several-word name, the first letters of a one-word name,
    numbered if it is already taken."""
    words = [w for w in re.findall(r"[A-Za-z0-9]+", name)
             if w.lower() not in {"of", "and", "the", "for", "faculty", "department"}]
    base = ("".join(w[0] for w in words) if len(words) > 1 else "".join(words)[:4]).upper()
    base = base[:max_length - 1] or "X"   # leave room for a number suffix
    code, n = base, 2
    while model.objects.filter(code__iexact=code, **scope).exists():
        code, n = f"{base}{n}", n + 1
    return code
