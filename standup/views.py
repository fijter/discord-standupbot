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
    
    def get_queryset(self, bypass=False):
        qs = models.Standup.objects.filter(event__standup_type__private=False).order_by('-created_at')

        if bypass:
            return qs

        if self.request.GET.get('server'):
            qs = qs.filter(event__channel__server__slug=self.request.GET.get('server'))
        if self.request.GET.get('channel'):
            qs = qs.filter(event__channel__slug=self.request.GET.get('channel'))

        return qs

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        context['channels'] = set(self.get_queryset(bypass=True).values_list('event__channel__slug', 'event__channel__server__slug').order_by('event__channel__server__slug', 'event__channel__slug'))
        if self.request.GET.get('channel') and self.request.GET.get('server'):
            context['channel'] = models.Channel.objects.get(slug=self.request.GET.get('channel'), server__slug=self.request.GET.get('server'))
        return context


class PrivateHomeView(ListView):
    template_name = 'private_standups.html'
    model = models.StandupParticipation
    paginate_by = 50
    paginate_orphans = 4
    context_object_name = 'participations'

    def get_queryset(self, bypass=False):
        try:
            p = models.StandupParticipation.objects.get(single_use_token=self.kwargs.get('token'))
        except models.StandupParticipation.DoesNotExist:
            return self.model.objects.none()

        qs = self.model.objects.filter(user=p.user).order_by('-created_at').distinct()
        
        if bypass:
            return qs

        if self.request.GET.get('server'):
            qs = qs.filter(standup__event__channel__server__slug=self.request.GET.get('server'))
        if self.request.GET.get('channel'):
            qs = qs.filter(standup__event__channel__slug=self.request.GET.get('channel'))

        return qs
    
    def get_context_data(self, **kwargs):
        context = super(PrivateHomeView, self).get_context_data(**kwargs)
        context['channels'] = set(self.get_queryset(bypass=True).values_list('standup__event__channel__slug', 'standup__event__channel__server__slug')\
            .order_by('standup__event__channel__server__slug', 'standup__event__channel__slug'))
        if self.request.GET.get('channel') and self.request.GET.get('server'):
            context['channel'] = models.Channel.objects.get(slug=self.request.GET.get('channel'), server__slug=self.request.GET.get('server'))
        return context


class StandupFormView(FormView):
    template_name = 'standup_form.html'
    form_class = forms.StandupForm

    def form_valid(self, form):
        form.save()
        return super(StandupFormView, self).form_valid(form)

    def get_success_url(self):
        p = models.StandupParticipation.objects.get(single_use_token=self.kwargs.get('token'))
        if p.standup.event.standup_type.private:
            return p.get_home_url()
        else:
            return p.standup.get_public_url()

    def get_form_kwargs(self):
        kwargs = super(StandupFormView, self).get_form_kwargs()
        try:
            p = models.StandupParticipation.objects.get(single_use_token=self.kwargs.get('token'))
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
        context['token'] = kwargs['token']
        context['participation'] = models.StandupParticipation.objects.get(single_use_token=kwargs['token'])
        return context
