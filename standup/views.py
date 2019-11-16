from django.views.generic import FormView, TemplateView, ListView
from django.http import Http404
from django.urls import reverse
from . import models
from . import forms


class HomeView(ListView):
    template_name = 'standups.html'
    model = models.Standup
    paginate_by = 50
    paginate_orphans = 4
    context_object_name = 'standups'
    queryset = models.Standup.objects.filter(event__standup_type__private=False).order_by('-created_at')


class StandupFormView(FormView):
    template_name = 'standup_form.html'
    form_class = forms.StandupForm

    def form_valid(self, form):
        form.save()
        return super(StandupFormView, self).form_valid(form)

    def get_success_url(self):
        p = models.StandupParticipation.objects.get(single_use_token=self.kwargs.get('token'))
        if p.standup.event.standup_type.private:
            return p.get_private_url()
        else:
            return p.standup.get_public_url()

    def get_form_kwargs(self):
        kwargs = super(StandupFormView, self).get_form_kwargs()
        try:
            p = models.StandupParticipation.objects.get(single_use_token=self.kwargs.get('token'), completed=False)
        except models.StandupParticipation.DoesNotExist:
            raise Http404('Single use token not valid')
        kwargs['participation'] = p
        return kwargs
    
    def get_context_data(self, *args, **kwargs):
        context = super(StandupFormView, self).get_context_data(**kwargs)
        standup = models.Standup.objects.filter(
            participants__single_use_token=self.kwargs['token']
        ).first()

        if not standup:
            raise Http404('Standup not found!')
        
        context['standup'] = standup
        return context


class PublicStandupView(TemplateView):
    template_name = 'standup.html'

    def get_context_data(self, **kwargs):
        context = super(PublicStandupView, self).get_context_data(**kwargs)
        standup = models.Standup.objects.filter(
            standup_date=kwargs['date'], 
            event__standup_type__private=False, 
            event__channel__slug=kwargs['channel'], 
            event__channel__server__slug=kwargs['server'],
            event__standup_type__command_name=kwargs['standup_type']
        ).first()

        if not standup:
            raise Http404('Standup not found!')
        
        context['standup'] = standup
        return context


class PrivateStandupView(TemplateView):
    template_name = 'standup.html'

    def get_context_data(self, **kwargs):
        context = super(PrivateStandupView, self).get_context_data(**kwargs)
        standup = models.Standup.objects.filter(
            participants__single_use_token=kwargs['token']
        ).first()

        if not standup:
            raise Http404('Standup not found!')
        
        context['standup'] = standup
        return context
