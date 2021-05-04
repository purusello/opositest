import random

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, ListView, TemplateView, FormView
from django.urls import reverse
from django.contrib import messages

from django.contrib.auth import authenticate, login, logout

from .forms import QuestionForm, EssayForm, CargarTestForm, ExportarTestForm, ExportarTestPDFForm, CargarTestJSONForm
from .models import Quiz, Category, Progress, Sitting, Question
from essay.models import Essay_Question
from multichoice.models import  Answer, MCQuestion
import csv
import io


from django.template import loader
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Frame, PageBreak
from reportlab.platypus.doctemplate import SimpleDocTemplate
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from cgi import escape

#from datetime import datetime

import codecs
import json



class QuizMarkerMixin(object):
    @method_decorator(login_required)
    @method_decorator(permission_required('quiz.view_sittings'))
    def dispatch(self, *args, **kwargs):
        return super(QuizMarkerMixin, self).dispatch(*args, **kwargs)


class SittingFilterTitleMixin(object):
    def get_queryset(self):
        queryset = super(SittingFilterTitleMixin, self).get_queryset()
        quiz_filter = self.request.GET.get('quiz_filter')
        if quiz_filter:
            queryset = queryset.filter(quiz__title__icontains=quiz_filter)

        return queryset


class QuizListView(ListView):
    model = Quiz

    def get_queryset(self):
        queryset = super(QuizListView, self).get_queryset()

        title_filter = self.request.GET.get('title_filter')
        if title_filter:
            queryset = queryset.filter(title__icontains=title_filter)

        category_filter = self.request.GET.get('category_filter')
        if category_filter:
            queryset = queryset.filter(category__category__icontains=category_filter)

        return queryset.filter(draft=False).order_by("title")



class QuizDetailView(DetailView):
    model = Quiz
    slug_field = 'url'

    @method_decorator(login_required(login_url='/login'))
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.draft and not request.user.has_perm('quiz.change_quiz'):
            raise PermissionDenied

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


class CategoriesListView(ListView):
    model = Category


class ViewQuizListByCategory(ListView):
    model = Quiz
    template_name = 'view_quiz_category.html'

    @method_decorator(login_required(login_url='/login'))
    def dispatch(self, request, *args, **kwargs):
        self.category = get_object_or_404(
            Category,
            category=self.kwargs['category_name']
        )

        return super(ViewQuizListByCategory, self).\
            dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ViewQuizListByCategory, self)\
            .get_context_data(**kwargs)

        context['category'] = self.category
        return context

    def get_queryset(self):
        queryset = super(ViewQuizListByCategory, self).get_queryset()
        return queryset.filter(category=self.category, draft=False)


class QuizUserProgressView(TemplateView):
    template_name = 'progress.html'

    @method_decorator(login_required(login_url='/login'))
    def dispatch(self, request, *args, **kwargs):
        return super(QuizUserProgressView, self)\
            .dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(QuizUserProgressView, self).get_context_data(**kwargs)
        progress, c = Progress.objects.get_or_create(user=self.request.user)
        context['cat_scores'] = progress.list_all_cat_scores
        context['exams'] = progress.show_exams()
        return context


class QuizMarkingList(QuizMarkerMixin, SittingFilterTitleMixin, ListView):
    model = Sitting

    def get_queryset(self):
        queryset = super(QuizMarkingList, self).get_queryset()\
                                               .filter(complete=True)

        queryset = queryset.filter(user=self.request.user)

        # Filter by user. I comment it that user only can see his Mark
        #user_filter = self.request.GET.get('user_filter')
        #if user_filter:
        #    queryset = queryset.filter(user__username__icontains=user_filter)

        orderbyList = ['quiz__title', '-end']
        return queryset.order_by(*orderbyList)

class QuizMarkingListOrder(QuizMarkerMixin, SittingFilterTitleMixin, ListView):
    model = Sitting


    def get_queryset(self):
        queryset = super(QuizMarkingListOrder, self).get_queryset()\
                                               .filter(complete=True)

        queryset = queryset.filter(user__username__icontains=self.request.user)

        order = str(self.request)

        if "orderend" in order:
            orderbyList = ['-end', 'quiz__title', ]
        else:
            if "orderquiz" in order:
                orderbyList = ['quiz__title', '-end', ]
            else:
                orderbyList = ['quiz__title', '-end', ]

        return queryset.order_by(*orderbyList)


class QuizMarkingDetail(QuizMarkerMixin, DetailView):
    model = Sitting

    @method_decorator(login_required(login_url='/login'))
    def post(self, request, *args, **kwargs):
        sitting = self.get_object()

        q_to_toggle = request.POST.get('qid', None)
        if q_to_toggle:
            q = Question.objects.get_subclass(id=int(q_to_toggle))
            if int(q_to_toggle) in sitting.get_incorrect_questions:
                sitting.remove_incorrect_question(q)
            else:
                sitting.add_incorrect_question(q)

        return self.get(request)

    def get_context_data(self, **kwargs):
        context = super(QuizMarkingDetail, self).get_context_data(**kwargs)
        context['questions'] =\
            context['sitting'].get_questions(with_answers=True)
        return context


class QuizTake(FormView):
    form_class = QuestionForm
    template_name = 'question.html'
    result_template_name = 'result.html'
    single_complete_template_name = 'single_complete.html'

    @method_decorator(login_required(login_url='/login'))
    def dispatch(self, request, *args, **kwargs):
        self.quiz = get_object_or_404(Quiz, url=self.kwargs['quiz_name'])
        if self.quiz.draft and not request.user.has_perm('quiz.change_quiz'):
            raise PermissionDenied

        try:
            self.logged_in_user = self.request.user.is_authenticated()
        except TypeError:
            self.logged_in_user = self.request.user.is_authenticated

        if self.logged_in_user:
            self.sitting = Sitting.objects.user_sitting(request.user,
                                                        self.quiz)
        else:
            self.sitting = self.anon_load_sitting()

        if self.sitting is False:
            return render(request, self.single_complete_template_name)

        return super(QuizTake, self).dispatch(request, *args, **kwargs)

    def get_form(self, *args, **kwargs):
        if self.logged_in_user:
            self.question = self.sitting.get_first_question()
            self.progress = self.sitting.progress()
        else:
            self.question = self.anon_next_question()
            self.progress = self.anon_sitting_progress()

        if self.question.__class__ is Essay_Question:
            form_class = EssayForm
        else:
            form_class = self.form_class

        return form_class(**self.get_form_kwargs())

    def get_form_kwargs(self):
        kwargs = super(QuizTake, self).get_form_kwargs()

        return dict(kwargs, question=self.question)

    def form_valid(self, form):
        if self.logged_in_user:
            self.form_valid_user(form)
            if self.sitting.get_first_question() is False:
                return self.final_result_user()
        else:
            self.form_valid_anon(form)
            if not self.request.session[self.quiz.anon_q_list()]:
                return self.final_result_anon()

        self.request.POST = {}

        return super(QuizTake, self).get(self, self.request)

    def get_context_data(self, **kwargs):
        context = super(QuizTake, self).get_context_data(**kwargs)
        context['question'] = self.question
        context['quiz'] = self.quiz
        if hasattr(self, 'previous'):
            context['previous'] = self.previous
        if hasattr(self, 'progress'):
            context['progress'] = self.progress
        return context

    def form_valid_user(self, form):
        progress, c = Progress.objects.get_or_create(user=self.request.user)
        guess = form.cleaned_data['answers']
        is_correct = self.question.check_if_correct(guess)

        if is_correct is True:
            self.sitting.add_to_score(1)
            progress.update_score(self.question, 1, 1)
        else:
            self.sitting.add_incorrect_question(self.question)
            progress.update_score(self.question, 0, 1)

        if self.quiz.answers_at_end is not True:
            self.previous = {'previous_answer': guess,
                             'previous_outcome': is_correct,
                             'previous_question': self.question,
                             'answers': self.question.get_answers(),
                             'question_type': {self.question
                                               .__class__.__name__: True}}
        else:
            self.previous = {}

        self.sitting.add_user_answer(self.question, guess)
        self.sitting.remove_first_question()

    def final_result_user(self):
        results = {
            'quiz': self.quiz,
            'score': self.sitting.get_current_score,
            'max_score': self.sitting.get_max_score,
            'percent': self.sitting.get_percent_correct,
            'sitting': self.sitting,
            'previous': self.previous,
        }

        self.sitting.mark_quiz_complete()

        if self.quiz.answers_at_end:
            results['questions'] =\
                self.sitting.get_questions(with_answers=True)
            results['incorrect_questions'] =\
                self.sitting.get_incorrect_questions

        if self.quiz.exam_paper is False:
            self.sitting.delete()

        return render(self.request, self.result_template_name, results)

    def anon_load_sitting(self):
        if self.quiz.single_attempt is True:
            return False

        if self.quiz.anon_q_list() in self.request.session:
            return self.request.session[self.quiz.anon_q_list()]
        else:
            return self.new_anon_quiz_session()

    def new_anon_quiz_session(self):
        """
        Sets the session variables when starting a quiz for the first time
        as a non signed-in user
        """
        self.request.session.set_expiry(259200)  # expires after 3 days
        questions = self.quiz.get_questions()
        question_list = [question.id for question in questions]

        if self.quiz.random_order is True:
            random.shuffle(question_list)

        if self.quiz.max_questions and (self.quiz.max_questions
                                        < len(question_list)):
            question_list = question_list[:self.quiz.max_questions]

        # session score for anon users
        self.request.session[self.quiz.anon_score_id()] = 0

        # session list of questions
        self.request.session[self.quiz.anon_q_list()] = question_list

        # session list of question order and incorrect questions
        self.request.session[self.quiz.anon_q_data()] = dict(
            incorrect_questions=[],
            order=question_list,
        )

        return self.request.session[self.quiz.anon_q_list()]

    def anon_next_question(self):
        next_question_id = self.request.session[self.quiz.anon_q_list()][0]
        return Question.objects.get_subclass(id=next_question_id)

    def anon_sitting_progress(self):
        total = len(self.request.session[self.quiz.anon_q_data()]['order'])
        answered = total - len(self.request.session[self.quiz.anon_q_list()])
        return (answered, total)

    def form_valid_anon(self, form):
        guess = form.cleaned_data['answers']
        is_correct = self.question.check_if_correct(guess)

        if is_correct:
            self.request.session[self.quiz.anon_score_id()] += 1
            anon_session_score(self.request.session, 1, 1)
        else:
            anon_session_score(self.request.session, 0, 1)
            self.request\
                .session[self.quiz.anon_q_data()]['incorrect_questions']\
                .append(self.question.id)

        self.previous = {}
        if self.quiz.answers_at_end is not True:
            self.previous = {'previous_answer': guess,
                             'previous_outcome': is_correct,
                             'previous_question': self.question,
                             'answers': self.question.get_answers(),
                             'question_type': {self.question
                                               .__class__.__name__: True}}

        self.request.session[self.quiz.anon_q_list()] =\
            self.request.session[self.quiz.anon_q_list()][1:]

    def final_result_anon(self):
        score = self.request.session[self.quiz.anon_score_id()]
        q_order = self.request.session[self.quiz.anon_q_data()]['order']
        max_score = len(q_order)
        percent = int(round((float(score) / max_score) * 100))
        session, session_possible = anon_session_score(self.request.session)
        if score is 0:
            score = "0"

        results = {
            'score': score,
            'max_score': max_score,
            'percent': percent,
            'session': session,
            'possible': session_possible
        }

        del self.request.session[self.quiz.anon_q_list()]

        if self.quiz.answers_at_end:
            results['questions'] = sorted(
                self.quiz.question_set.filter(id__in=q_order)
                                      .select_subclasses(),
                key=lambda q: q_order.index(q.id))

            results['incorrect_questions'] = (
                self.request
                    .session[self.quiz.anon_q_data()]['incorrect_questions'])

        else:
            results['previous'] = self.previous

        del self.request.session[self.quiz.anon_q_data()]

        return render(self.request, 'result.html', results)


def anon_session_score(session, to_add=0, possible=0):
    """
    Returns the session score for non-signed in users.
    If number passed in then add this to the running total and
    return session score.

    examples:
        anon_session_score(1, 1) will add 1 out of a possible 1
        anon_session_score(0, 2) will add 0 out of a possible 2
        x, y = anon_session_score() will return the session score
                                    without modification

    Left this as an individual function for unit testing
    """
    if "session_score" not in session:
        session["session_score"], session["session_score_possible"] = 0, 0

    if possible > 0:
        session["session_score"] += to_add
        session["session_score_possible"] += possible

    return session["session_score"], session["session_score_possible"]

def handle_uploaded_file(f):
    with open('some/file/name.txt', 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def index(request):
    return render(request, 'index.html', {})


def login_user(request):

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'You have successfully logged in')
            return redirect("index")
        else:
            messages.success(request, 'Error logging in')
            return redirect('login')
    else:
        return render(request, 'login.html', {})


def logout_user(request):
    logout(request)
    messages.success(request, 'You have been logged out!')
    print('logout function working')
    return redirect('login')


@login_required(login_url='/login' )
def importarCSV(request):


    if request.method=='POST':
        formulario = CargarTestForm(request.POST, request.FILES)

        if formulario.is_valid():
            if not (formulario.cleaned_data['test'] or formulario.cleaned_data['nuevoTest']):
                messages.error(request, 'Debe seleccionar un test o introducir un nombre para uno nuevo')
                return HttpResponseRedirect(reverse("importarCSV"))
            csv_file = request.FILES['archivo']

            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'El archivo no es tipo csv')
                return HttpResponseRedirect(reverse("importarCSV"))
            # if file is too large, return
            if csv_file.multiple_chunks():
                messages.error(request, "Archivo demasiado grande (%.2f MB)." % (csv_file.size / (1000 * 1000),))
                return HttpResponseRedirect(reverse("importarCSV"))

            if (formulario.cleaned_data['test']):
                q = formulario.cleaned_data['test']
            else:
                q = Quiz(title=formulario.cleaned_data['nuevoTest'], url=formulario.cleaned_data['nuevoTest'],
                         category=formulario.cleaned_data['categoria'],
                         random_order=True,
                         answers_at_end=False,
                         exam_paper=True,
                         single_attempt=False
                         )
                q.save()

            reader = csv.DictReader(io.StringIO(csv_file.read().decode('utf-8-sig')), delimiter=';',
                                    quotechar=formulario.cleaned_data['encapsulado'])           #'|')
            for row in reader:
                try:

                    m = MCQuestion(content=row['pregunta'])
                    m.save()
                    m.quiz.add(q)

                    c1 = Answer(content=row['r1'])#.replace(';','.').replace('"','·'))
                    c2 = Answer(content=row['r2'])#.replace(';','.').replace('"','·'))
                    c3 = Answer(content=row['r3'])#.replace(';','.').replace('"','·'))
                    c4 = Answer(content=row['r4'])#.replace(';','.').replace('"','·'))
                    if row['correcta'] == "1":
                        c1.correct = True
                    elif row['correcta'] == "2":
                        c2.correct = True
                    elif row['correcta'] == "3":
                        c3.correct = True
                    elif row['correcta'] == "4":
                        c4.correct = True
                    m.answer_order = 'random'

                    m.explanation = ''
                    try:
                        m.explanation =  row['explicacion']#.replace(';','.').replace('"','·')
                    except Exception as e:
                        messages.error(request, "La pregunta " + row['pregunta'] + " no tiene explicacion")

                    # if row['imagen'] != '' and row['imagen'] is not None:
                    #     try:
                    #         m.figure =  'uploads/' + datetime.now().strftime("%Y/%m/%d/") + row['imagen']
                    #     except Exception as e:
                    #         messages.error(request, 'error cargando imagen: ' + repr(e))

                    c1.question = m
                    c2.question = m
                    c3.question = m
                    c4.question = m
                    m.category = formulario.cleaned_data['categoria']
                    m.sub_category = formulario.cleaned_data['subcategoria']
                    m.save()
                    c1.save()
                    c2.save()
                    c3.save()
                    c4.save()
                except Exception as e:
                    messages.error(request, "Error importando pregunta " + repr(e))
                    return HttpResponseRedirect(reverse("importarCSV"))


            messages.info(request, "Fichero cargado correctamente")


    else:

        formulario = CargarTestForm()

    context = {'formulario': formulario}
    return render(request, 'importacsv2.html',context)

@login_required(login_url='/login' )
def importarJSON(request):


    if request.method=='POST':
        formulario = CargarTestJSONForm(request.POST, request.FILES)

        if formulario.is_valid():
            if not (formulario.cleaned_data['test'] or formulario.cleaned_data['nuevoTest']):
                messages.error(request, 'Debe seleccionar un test o introducir un nombre para uno nuevo')
                return HttpResponseRedirect(reverse("importarJSON"))
            json_file = request.FILES['archivo']

            if not json_file.name.endswith('.json'):
                messages.error(request, 'El archivo no es tipo Json')
                return HttpResponseRedirect(reverse("importarJSON"))
            # if file is too large, return
            if json_file.multiple_chunks():
                messages.error(request, "Archivo demasiado grande (%.2f MB)." % (csv_file.size / (1000 * 1000),))
                return HttpResponseRedirect(reverse("importarJSON"))

            if (formulario.cleaned_data['test']):
                q = formulario.cleaned_data['test']
            else:
                q = Quiz(title=formulario.cleaned_data['nuevoTest'], url=formulario.cleaned_data['nuevoTest'],
                         category=formulario.cleaned_data['categoria'],
                         random_order=True,
                         answers_at_end=False,
                         exam_paper=True,
                         single_attempt=False
                         )
                q.save()

            #reader = csv.DictReader(io.StringIO(json_file.read().decode('utf-8-sig')), delimiter=';',
            #                        quotechar=formulario.cleaned_data['encapsulado'])           #'|')
            #for row in reader:
            #print(json_file)

            try:
                data = json.load(json_file)
                for preg in data['preguntas']:
                    #print('Pregunta:', preg['pregunta'])
                    #print('Respuesta:', preg['respuesta'])
                    #print('Explicación:', preg['explicacion'])
                    #print('')

                    m = MCQuestion(content=preg['pregunta'])
                    m.save()
                    m.quiz.add(q)



                    c1 = Answer(content=preg['opciones'][0])
                    c2 = Answer(content=preg['opciones'][1])
                    c3 = Answer(content=preg['opciones'][2])
                    c4 = Answer(content=preg['opciones'][3])

                    if preg['respuesta'] == 1:
                        c1.correct = True
                    elif preg['respuesta'] == 2:
                        c2.correct = True
                    elif preg['respuesta'] == 3:
                        c3.correct = True
                    elif preg['respuesta'] == 4:
                        c4.correct = True

                    m.answer_order = 'random'

                    m.explanation =  preg['explicacion']

                    c1.question = m
                    c2.question = m
                    c3.question = m
                    c4.question = m


                    m.category = formulario.cleaned_data['categoria']
                    m.sub_category = formulario.cleaned_data['subcategoria']
                    m.save()
                    c1.save()
                    c2.save()
                    c3.save()
                    c4.save()
            except Exception as e:
                messages.error(request, "Error importando pregunta " + repr(e))
                return HttpResponseRedirect(reverse("importarJSON"))


            messages.info(request, "Fichero cargado correctamente")


    else:

        formulario = CargarTestJSONForm()

    context = {'formulario': formulario}
    return render(request, 'importacsv2.html',context)

@login_required(login_url='/login' )
def exportarTestCSV(request):


    def add_pregunta(pregunta):
        csv_data["data"].append(pregunta)

    if request.method == 'POST':
        formulario = ExportarTestForm(request.POST, request.FILES)

        if formulario.is_valid():
            if not (formulario.cleaned_data['test'] ):
                messages.error(request, 'Debe seleccionar un test ')
                return HttpResponseRedirect(reverse("exportarTestCSV"))

            q = formulario.cleaned_data['test']

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename=' + q.title + '.csv'

            csv_data = {"data": []}

            pregunta = {}
            pregunta["pregunta"] = "pregunta"
            pregunta["r1"] = 'r1'
            pregunta["r2"] = 'r2'
            pregunta["r3"] = 'r3'
            pregunta["r4"] = 'r4'
            pregunta["correcta"] = 'correcta'
            pregunta["explicacion"] = 'explicacion'
            add_pregunta(pregunta)

            encapsulado = formulario.cleaned_data['encapsulado']

            MCQSet = Question.objects.filter(quiz=q)
            if MCQSet:
                # The cache is used for subsequent iteration.
                for mcq in MCQSet:
                    answerSet = Answer.objects.filter(question=mcq)
                    respuestas = []
                    i = 0
                    for ans in answerSet:
                        i = i + 1
                        respuestas.append(ans.content)
                        if ans.correct:
                            correcta = i

                    encapsulado

                    pregunta = {}
                    pregunta["pregunta"] = encapsulado+ mcq.content + encapsulado #.replace(';','.').replace('"','·')
                    pregunta["r1"] = encapsulado + respuestas[0] + encapsulado #.replace(';','.').replace('"','·')
                    pregunta["r2"] = encapsulado + respuestas[1] + encapsulado #.replace(';','.').replace('"','·')
                    pregunta["r3"] = encapsulado + respuestas[2] + encapsulado #.replace(';','.').replace('"','·')
                    pregunta["r4"] = encapsulado + respuestas[3] + encapsulado #.replace(';','.').replace('"','·')
                    pregunta["correcta"] = correcta
                    pregunta["explicacion"] = encapsulado + mcq.explanation + encapsulado #.replace(';','.').replace('"','·')
                    add_pregunta(pregunta)


            t = loader.get_template('plantilla.txt')


            response.write(codecs.BOM_UTF8)
            response.write(t.render(csv_data))


            return response



    else:

        formulario = ExportarTestForm()

    context = {'formulario': formulario}
    return render(request, 'exportacsv.html',context)


@login_required(login_url='/login' )
def exportarTestPDF(request):



    if request.method == 'POST':
        formulario = ExportarTestPDFForm(request.POST, request.FILES)

        if formulario.is_valid():
            if not (formulario.cleaned_data['test'] ):
                messages.error(request, 'Debe seleccionar un test ')
                return HttpResponseRedirect(reverse("exportarTestPDF"))


            objects_to_draw = []
            style = ParagraphStyle('normal')
            style.firstLineIndent = 5
            style.spaceBefore = 1
            letras = ['a','b','c','d','Falta la respuesta']
            correcta = []

            q = formulario.cleaned_data['test']

            p = Paragraph('Nombre del Test: ' + q.title, style)
            objects_to_draw.append(p)
            objects_to_draw.append(Spacer(1, 0.2 * inch))

            MCQSet = Question.objects.filter(quiz=q).order_by("?")
            if MCQSet:
                i = 0
                for mcq in MCQSet:
                    i = i + 1
                    p = Paragraph(str(i) + ". " + mcq.content, style)
                    objects_to_draw.append(p)
                    objects_to_draw.append(Spacer(1, 0.2 * inch))
                    answerSet = Answer.objects.filter(question=mcq).order_by("?")
                    #respuestas = []
                    j = 0
                    respuesta = False;
                    for ans in answerSet:

                        #respuestas.append(ans.content)
                        # The cache is used for subsequent iteration.
                        p = Paragraph( letras[j]+') ' + escape(ans.content), style)
                        objects_to_draw.append(p)
                        objects_to_draw.append(Spacer(1, 0.2 * inch))
                        j = j + 1
                        if ans.correct:
                            correcta.append(j)
                            respuesta = True
                    #writer.writerow([mcq.content, respuestas[0], respuestas[1], respuestas[2], respuestas[3],"Here's a quote"])
                    objects_to_draw.append(Spacer(1, 0.2 * inch))
                    if ( not respuesta) :
                        correcta.append(5)
            #salto de página
            objects_to_draw.append(PageBreak())







            doc = SimpleDocTemplate('/tmp/doctemplate.pdf')


            p = Paragraph("RESPUESTAS", style)
            objects_to_draw.append(p)
            p = Paragraph("---------------------------------------------------------------", style)
            objects_to_draw.append(p)

            i = 0
            for j in correcta:
                i = i + 1
                p = Paragraph(str(i) + ": " + letras[j - 1] + ') ', style)
                objects_to_draw.append(p)

            # # Two Columns
            # frame1 = Frame(doc.leftMargin, doc.bottomMargin, doc.width / 2 - 6, doc.height, id='col1')
            # frame2 = Frame(doc.leftMargin + doc.width / 2 + 6, doc.bottomMargin, doc.width / 2 - 6, doc.height,
            #                id='col2')
            #
            # doc.addPageTemplates([platypus.PageTemplate(id='TwoCol', frames=[frame1, frame2]), ])

            doc.build(objects_to_draw)

            fs = FileSystemStorage("/tmp")
            with fs.open("doctemplate.pdf") as pdf:
                response = HttpResponse(pdf, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="'+ q.title + '.pdf"'
                return response


            return response



    else:

        formulario = ExportarTestPDFForm()

    context = {'formulario': formulario}
    return render(request, 'exportapdf.html',context)




