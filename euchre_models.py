from django.db import models
from datetime import datetime
from django.contrib.postgres.fields import ArrayField

class EuchreCard(models.Model):
    suit = models.CharField('Suit', max_length=1)
    rank = models.IntegerField('rank')
    player = models.ForeignKey('EuchrePlayer', related_name='card', on_delete=models.CASCADE, null=True)
    played = models.BooleanField('Played', default=False)

class EuchreTrick(models.Model):
    opener = models.ForeignKey('EuchreCard', related_name='trick_opener', on_delete=models.CASCADE)
    highest = models.ForeignKey('EuchreCard', related_name='trick', on_delete=models.CASCADE, null=True)
    selection = models.BooleanField('Trump Selection', default=False)

class EuchrePlayer(models.Model):
    id = models.PositiveBigIntegerField("Player's Discord ID", primary_key=True)
    team = models.ForeignKey('EuchreTeam',  on_delete=models.CASCADE, null=True)
    wins = models.IntegerField('Wins', default=0)
    losses = models.IntegerField('Losses', default=0)
    
    @property
    def can_follow_suit(self, game):
        trick = game.current_trick
        opener = trick.opener
        cards = list(EuchreCard.objects.filter(player=self, suit=opener.suit, played=False))
        if len(cards) > 0:
            return True
        return False

class EuchreTeam(models.Model):
    id = models.AutoField("Team ID", primary_key=True)
    game = models.ForeignKey('EuchreGame', on_delete=models.CASCADE, null=True)
    # Stores the player who is going alone if there is one
    going_alone = models.ForeignKey('EuchrePlayer', on_delete=models.CASCADE, null=True)
    tricks_won = models.IntegerField('Tricks Won', default=0)

    @property
    def is_going_alone(self):
        return self.going_alone is not None


class EuchreGame(models.Model):
    start = models.DateTimeField('Time Started', default=datetime.now)
    end = models.DateTimeField('Time Finished', default=None, null=True)
    dealer = models.ForeignKey('EuchrePlayer', on_delete=models.CASCADE)
    next_dealer = models.ForeignKey('EuchrePlayer', related_name='next_dealer', on_delete=models.CASCADE)
    trump = models.CharField('Suit', max_length=1)
    current_trick = models.ForeignKey('EuchreTrick', on_delete=models.CASCADE)
    winner = models.ForeignKey('EuchreTeam', related_name='game_winner', on_delete=models.CASCADE, null=True)
    declarer = models.ForeignKey('EuchreTeam', related_name='game_declarer', on_delete=models.CASCADE, null=True)

    @property
    def is_completed(self) -> bool:
        return self.end is not None
    
    def compute_dealers(self, current) -> EuchrePlayer:
        """Computes who the dealer should be after the next dealer, also used for declaring trumps"""
        dealer_team = current.team
        team_members = EuchrePlayer.objects.filter(team=dealer_team)
        new_dealer = team_members.exclude(id=current.id).first()
        return new_dealer

    @property
    def points(self):
        if winner.is_going_alone:
            # if they are going alone then they must be the declarer
            if winner.tricks_won == 5:
                return 4
            else:
                return 1
        if winner != declarer:
            return 2
        else:
            if winner.tricks_won == 5:
                return 2
            else:
                return 1

    def check_for_winner(self) -> bool:
        """
        Checks if a team has won and updates the completion info
        Note: Only returns True when the game is COMPLETED
        """
        teams = list(EuchreTeam.objects.filter(game=self))
        if teams[0].tricks_won == 5:
            self.winner = teams[0]
        elif teams[1].tricks_won == 5:
            self.winner = teams[1]
        elif teams[0].tricks_won >= 3 and teams[1].tricks_won > 0:
            self.winner = teams[0]
        elif teams[1].tricks_won >= 3 and teams[0].tricks_won > 0:
            self.winner = teams[1]

        if self.winner is not None:
            self.save()
            return True
        return False
