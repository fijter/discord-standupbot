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


        for question in participation.standup.event.standup_type.questions.all():
            field_name = 'question_%d' % question.id
            self.fields[field_name] = forms.CharField(required=False, label=question.question, widget=forms.Textarea())
            if question.important:
                self.fields[field_name].help_text = 'This field is optional, please leave it empty if it does not apply!'

            if question.prefill_last_answer:
                lastans = prev_parti.answers.filter(question=question.prefill_last_answer).first()
                if lastans:
                    self.fields[field_name].initial = lastans.answer  

    def save(self):
        for question in self.participation.standup.event.standup_type.questions.all():
            field_name = 'question_%d' % question.id
            self.participation.answers.create(question=question, answer=self.cleaned_data[field_name])

        self.participation.completed = True
        self.participation.save()
        
        return True
