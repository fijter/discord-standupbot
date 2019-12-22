from django import forms
from . import models


class StandupForm(forms.Form):
    
    def __init__(self, *args, **kwargs):
        participation = kwargs.pop('participation')
        self.participation = participation
        super(StandupForm, self).__init__(*args, **kwargs)

        standup = self.participation.standup
        prev_parti = models.StandupParticipation.objects.filter(
            standup__event__standup_type=standup.event.standup_type,
            standup__event__channel=standup.event.channel,
            completed=True,
            user=self.participation.user
        ).exclude(id=self.participation.id).order_by('-id').first()
        
        answers = {}

        if self.participation.completed:
            answers = dict([(a.question, a.answer) for a in self.participation.answers.all()])

        for question in participation.standup.event.standup_type.questions.all():
            field_name = 'question_%d' % question.id
            self.fields[field_name] = forms.CharField(required=False, label=question.question, initial=answers.get(question), widget=forms.Textarea())
            if question.important:
                self.fields[field_name].help_text = 'This field is optional, please leave it empty if it does not apply!'

            if question.prefill_last_answer and prev_parti and not self.participation.completed:
                lastans = prev_parti.answers.filter(question=question.prefill_last_answer).first()
                if lastans:
                    self.fields[field_name].initial = lastans.answer  

    def save(self):
        for question in self.participation.standup.event.standup_type.questions.all():
            field_name = 'question_%d' % question.id
            ans, created = self.participation.answers.get_or_create(question=question, defaults={'answer': self.cleaned_data[field_name]})
            if not created:
                ans.answer = self.cleaned_data[field_name]
                ans.save()

        self.participation.completed = True
        self.participation.save()
        
        return True
