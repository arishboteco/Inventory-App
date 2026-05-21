from django import forms

from inventory.forms.base import StyledFormMixin


class DummyForm(StyledFormMixin, forms.Form):
    a_text = forms.CharField()
    a_date = forms.DateField()
    a_select = forms.ChoiceField(choices=[("1", "One"), ("2", "Two")])
    a_multi = forms.MultipleChoiceField(
        choices=[("x", "X"), ("y", "Y")], widget=forms.SelectMultiple
    )


def test_styled_form_mixin_adds_predictive_to_selects():
    f = DummyForm()
    # text input shouldn't have predictive
    assert "predictive" not in (f.fields["a_text"].widget.attrs.get("class") or "")
    assert f.fields["a_date"].widget.input_type == "date"
    assert f.fields["a_date"].widget.attrs.get("type") == "date"
    assert "%d/%m/%Y" in f.fields["a_date"].input_formats
    # select widgets should have predictive
    assert "predictive" in (f.fields["a_select"].widget.attrs.get("class") or "")
    assert "predictive" in (f.fields["a_multi"].widget.attrs.get("class") or "")
