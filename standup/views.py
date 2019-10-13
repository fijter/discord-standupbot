from django.views.generic import FormView, TemplateView
from django.http import Http404
from django.urls import reverse
from . import models
from . import forms


class StandupFormView(FormView):
    template_name = 'standup_form.html'
    form_class = forms.StandupForm

    def form_valid(self, form):
        form.save()
        return super(StandupFormView, self).form_valid(form)

    def get_success_url(self):
        return reverse('standup_form_complete', kwargs={'token': self.kwargs.get('token')})

    def get_form_kwargs(self):
        kwargs = super(StandupFormView, self).get_form_kwargs()
        try:
            p = models.StandupParticipation.objects.get(single_use_token=self.kwargs.get('token'), completed=False)
        except models.StandupParticipation.DoesNotExist:
            raise Http404('Single use token not valid')
        kwargs['participation'] = p
        return kwargs


class StandupFormCompleteView(TemplateView):
    template_name = 'standup_form_complete.html'
