from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
from typing import List
from django_unixdatetimefield import UnixDateTimeField


class Ticket(models.Model):
    id = models.AutoField('Ticket ID', primary_key=True)
    title = models.CharField('Title', max_length=200)
    body = models.TextField('Body', max_length=3000)
    status = models.IntegerField('Status', choices=[
        (0, 'NEW'),
        (1, 'IN PROGRESS'),
        (2, 'MORE INFO'),
        (3, 'CLOSED')
    ], default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    opened = UnixDateTimeField('Time Opened', default=datetime.now)

    @property
    def is_open(self) -> bool:
        return self.status != 3

    @property
    def get_comments(self) -> List:
        return list(TicketComment.objects.filter(ticket=self).order_by('index'))

    @property
    def get_current_index(self) -> int:
        comments = self.get_comments
        if len(comments) == 0:
            return 0
        else:
            return comments[-1].index + 1

    def create_comment(self, user: User, body: str):
        index = self.get_current_index
        comment = TicketComment(index=index, user=user, body=body, ticket=self)
        comment.save()
        return comment


class TicketComment(models.Model):
    index = models.IntegerField('Index')
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = UnixDateTimeField('Time Created', default=datetime.now)
    body = models.TextField('Body', max_length=3000)
