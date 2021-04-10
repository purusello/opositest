from django import forms
from django.forms.widgets import RadioSelect, Textarea
from .models import Category, Quiz, SubCategory
from multichoice.models import MCQuestion



class QuestionForm(forms.Form):
    def __init__(self, question, *args, **kwargs):
        super(QuestionForm, self).__init__(*args, **kwargs)
        choice_list = [x for x in question.get_answers_list()]
        self.fields["answers"] = forms.ChoiceField(choices=choice_list,
                                                   widget=RadioSelect)


class EssayForm(forms.Form):
    def __init__(self, question, *args, **kwargs):
        super(EssayForm, self).__init__(*args, **kwargs)
        self.fields["answers"] = forms.CharField(
            widget=Textarea(attrs={'style': 'width:100%'}))


class CargarTestForm(forms.Form):


    listaCategorias = Category.objects.all().order_by('category')
    listaSubcategorias = SubCategory.objects.all().order_by('sub_category')
    listaTest = Quiz.objects.all().order_by('title')



    ENCAPSULADO = (
        ("|", "| (pipeline)"),
        ("#", "# (almohadilla)"),
        ("~", "~ (el rabo de la ... eñe)"),
    )

    nuevoTest = forms.CharField(required=False)
    test = forms.ModelChoiceField(label="Test existente", queryset=listaTest, required=False)
    categoria = forms.ModelChoiceField(label="Categoría", queryset=listaCategorias)
    subcategoria = forms.ModelChoiceField(label="Subcategoría", queryset=listaSubcategorias)
    encapsulado = forms.ChoiceField(label="Encapsulador", choices=ENCAPSULADO, required=True)
    archivo = forms.FileField()



class ExportarTestForm(forms.Form):

    listaTest = Quiz.objects.all().order_by('title')




    ENCAPSULADO = (
        ("|", "| (pipeline)"),
        ("#", "# (almohadilla)"),
        ("~", "~ (el rabo de la ... eñe)"),
    )

    test = forms.ModelChoiceField(label="Test existente", queryset=listaTest, required=False)
    encapsulado = forms.ChoiceField(label="Encapsulador", choices=ENCAPSULADO, required=True)


class ExportarTestPDFForm(forms.Form):

    listaTest = Quiz.objects.all().order_by('title')

    test = forms.ModelChoiceField(label="Test existente", queryset=listaTest, required=False)