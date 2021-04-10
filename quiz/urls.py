try:
    from django.conf.urls import url
except ImportError:
    from django.urls import re_path as url

from django.contrib import admin
from django.urls import path

from django.conf.urls.static import static
from django.conf import settings


from .views import QuizListView, CategoriesListView, \
    ViewQuizListByCategory, QuizUserProgressView, QuizMarkingList, \
    QuizMarkingDetail, QuizDetailView, QuizTake, index, login_user, logout_user, importarCSV, \
    exportarTestCSV, exportarTestPDF, QuizMarkingListOrder


urlpatterns = [

    url(regex=r'^$', view=index, name='index'),
    url(regex=r'^login/$', view=login_user, name='login'),
    url(regex=r'^logout/$', view=logout_user, name='logout'),
    path('admin/', admin.site.urls),



    #url(r'^upload/csv/$', upload_csv, name='upload_csv'),
    #
    # url(r'^$',
    #     view=QuizListView.as_view(),
    #     name='quiz_index'),




    url(r'^cargacsv/$', view=importarCSV, name='importarCSV'),

    url(r'^exportacsv/$', view=exportarTestCSV, name='exportarTestCSV'),

    url(r'^exportapdf/$', view=exportarTestPDF, name='exportarTestPDF'),

    url(regex=r'^quizzes/$',
        view=QuizListView.as_view(),
        name='quiz_index'),

    url(r'^category/$',
        view=CategoriesListView.as_view(),
        name='quiz_category_list_all'),

    url(r'^category/(?P<category_name>[\w|\W-]+)/$',
        view=ViewQuizListByCategory.as_view(),
        name='quiz_category_list_matching'),

    url(r'^progress/$',
        view=QuizUserProgressView.as_view(),
        name='quiz_progress'),

    url(r'^marking/$',
        view=QuizMarkingList.as_view(),
        name='quiz_marking'),

    url(r'^marking/(?P<pk>[\d.]+)/$',
        view=QuizMarkingDetail.as_view(),
        name='quiz_marking_detail'),

    url(r'^marking/(?P<order>[\w.]+)$',
        view=QuizMarkingListOrder.as_view(),
        name='quiz_marking_ordering'),

    #  passes variable 'quiz_name' to quiz_take view
    url(r'^(?P<slug>[\w-]+)/$',
        view=QuizDetailView.as_view(),
        name='quiz_start_page'),

    url(r'^(?P<quiz_name>[\w-]+)/take/$',
        view=QuizTake.as_view(),
        name='quiz_question'),


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
