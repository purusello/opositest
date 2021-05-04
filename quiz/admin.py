from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.utils.translation import ugettext_lazy as _

from .models import Quiz, Category, SubCategory, Progress, Question, Sitting
from multichoice.models import MCQuestion, Answer
from true_false.models import TF_Question
from essay.models import Essay_Question

from django.core.cache import cache

class AnswerInline(admin.TabularInline):
    model = Answer


    """
    below is from
    http://stackoverflow.com/questions/11657682/
    django-admin-interface-using-horizontal-filter-with-
    inline-manytomany-field
    """


class QuizAdminForm(forms.ModelForm):

    class Meta:
        model = Quiz
        exclude = []

    # Check if the result is already cached
    questions_results = cache.get('questions_results') # Returns None if not cached earlier

    # If the result is None, then query the database and set the cache
    if questions_results is None:
        questions_results = Question.objects.all()
        try:
            cache.set('questions_results', questions_results)
        except:
            print("se ha producido exception en question_result")

    questions = forms.ModelMultipleChoiceField(
        queryset=questions_results,#Question.objects.all().select_subclasses(),
        required=False,
        label=_("Questions"),
        widget=FilteredSelectMultiple(
            verbose_name=_("Questions"),
            is_stacked=False))

    def __init__(self, *args, **kwargs):
        super(QuizAdminForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['questions'].initial =\
                self.instance.question_set.all().select_subclasses()

    def save(self, commit=True):
        quiz = super(QuizAdminForm, self).save(commit=False)
        quiz.save()
        quiz.question_set.set(self.cleaned_data['questions'])
        self.save_m2m()
        return quiz

def create_new_test(modeladmin, request, queryset):
    for quiz in queryset:
        from datetime  import datetime
        ahora = datetime.now()
        fecha = ahora.strftime("%Y-%m-%d %H-%M:%S")

        q = Quiz(title= fecha  + ' Test automatico', url='testauto'+fecha,
                 category=quiz.category,
                 random_order=True,
                 answers_at_end=False,
                 exam_paper=True,
                 single_attempt=False
                 )
        break
    q.save()
    for quiz in queryset:
        for question in quiz.get_questions():
            question.quiz.add(q)


    create_new_test.short_description = 'Crear test basado en test seleccionados'

class QuizAdmin(admin.ModelAdmin):
    form = QuizAdminForm

    list_display = ('title', 'category', )
    list_filter = ('category',)
    search_fields = ('title', )
    actions = [create_new_test, ]


class CategoryAdmin(admin.ModelAdmin):
    search_fields = ('category', )


class SubCategoryAdmin(admin.ModelAdmin):
    search_fields = ('sub_category', )
    list_display = ('sub_category', 'category',)
    list_filter = ('category',)


class MCQuestionAdmin(admin.ModelAdmin):
    list_display = ('content', 'category','sub_category' )
    list_filter = ('category','sub_category','quiz')
    fields = ('content', 'category', 'sub_category',
              'figure', 'quiz', 'explanation', 'answer_order')

    search_fields = ('content', 'explanation')
    filter_horizontal = ('quiz',)

    inlines = [AnswerInline]


class ProgressAdmin(admin.ModelAdmin):
    """
    to do:
            create a user section
    """
    search_fields = ('user', 'score', )


class TFQuestionAdmin(admin.ModelAdmin):
    list_display = ('content', 'category', )
    list_filter = ('category',)
    fields = ('content', 'category', 'sub_category',
              'figure', 'quiz', 'explanation', 'correct',)

    search_fields = ('content', 'explanation')
    filter_horizontal = ('quiz',)


class EssayQuestionAdmin(admin.ModelAdmin):
    list_display = ('content', 'category', )
    list_filter = ('category',)
    fields = ('content', 'category', 'sub_category', 'quiz', 'explanation', )
    search_fields = ('content', 'explanation')
    filter_horizontal = ('quiz',)


class SittingAdmin(admin.ModelAdmin):
    list_display =('user','quiz', 'start','end','current_score')
    list_filter = ('complete',)
    search_fields = ('user__username','quiz__title',)

admin.site.register(Quiz, QuizAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(SubCategory, SubCategoryAdmin)
admin.site.register(MCQuestion, MCQuestionAdmin)
admin.site.register(Progress, ProgressAdmin)
admin.site.register(TF_Question, TFQuestionAdmin)
admin.site.register(Essay_Question, EssayQuestionAdmin)



admin.site.register(Sitting, SittingAdmin)
