from django.test import TestCase
from .models import Puzzle, TeamPuzzleActivity, Team, PuzzleStream, PuzzleGuess, VerificationPhoto, initialize_scav
from django.contrib.auth.models import Group


class ScavUnorderedTests(TestCase):
    @classmethod
    def setUpClass(self):
        super(ScavUnorderedTests, self).setUpClass()
        self.test1 = PuzzleStream.objects.create(name="Test1", default=True)
        self.test4 = PuzzleStream.objects.create(name="Test4", default=False)
        self.test2 = PuzzleStream.objects.create(name="Test2", default=False)
        self.test3 = PuzzleStream.objects.create(name="Test3", default=True, enabled=False)

        self.test41 = Puzzle.objects.create(name="Test4-1", answer="abcd,efgh", order=1, stream=self.test4)
        self.test21 = Puzzle.objects.create(name="Test2-1", answer="test", order=1.7, stream=self.test2,
                                            require_photo_upload=False, stream_puzzle=self.test41)
        self.test22 = Puzzle.objects.create(name="Test2-2", answer="test3", order=2.0, stream=self.test2)
        self.test13 = Puzzle.objects.create(name="Test1-3", answer="b", order=1005, stream=self.test1)
        self.test12 = Puzzle.objects.create(name="Test1-2", answer="a", order=1.0, stream=self.test1)
        self.test11 = Puzzle.objects.create(name="Test1-1", answer="test2", order=0.5, stream=self.test1,
                                            stream_branch=self.test2)
        self.test31 = Puzzle.objects.create(name="Test3-1", answer="test", order=2, stream=self.test3)
        group1 = Group.objects.create(name="T1")
        group2 = Group.objects.create(name="T2")
        self.team1 = Team.objects.create(group=group1, display_name="T1")
        self.team2 = Team.objects.create(group=group2, display_name="T2")
        initialize_scav()

    def test_initialize(self):
        activities = TeamPuzzleActivity.objects.all()
        self.assertEqual(len(activities), 2)
        for act in activities:
            valid = act.puzzle == self.test11 and (act.team == self.team1 or act.team == self.team2)
            self.assertTrue(valid)

    def test_active_viewable(self):
        self.assertTrue(self.test11.is_active_for_team(self.team1))
        self.assertTrue(self.test11.is_viewable_for_team(self.team1))
        try:
            self.assertFalse(self.test12.is_active_for_team(self.team1))
        except:  # noqa: E722
            pass
        try:
            self.assertFalse(self.test12.is_viewable_for_team(self.team1))
        except:  # noqaL E722
            pass
        self.assertFalse(self.test11.is_completed_for_team(self.team1))

    def test_guess(self):
        activity = self.test11.puzzle_activity_from_team(self.team1)
        # activity = TeamPuzzleActivity.objects.filter(team=self.team1, puzzle=self.test11).first()
        self.assertTrue(activity.is_active)
        self.assertFalse(activity.is_completed)
        self.assertFalse(activity.is_verified)

        self.assertFalse(self.test11.check_team_guess(self.team1, 'a'*150)[0])
        self.assertFalse(self.test11.check_team_guess(self.team1, 'test')[0])
        guess = PuzzleGuess.objects.all()
        self.assertEqual(len(guess), 1)  # Over 100 chars doesn't fit in model so it doesn't count
        guess = guess.first()
        self.assertEqual(guess.value, "test")
        self.assertEqual(guess.activity, TeamPuzzleActivity.objects.filter(team=self.team1, puzzle=self.test11).first())
        self.assertEqual(self.test11.check_team_guess(self.team1, "test2"), (True, False, None, True))
        activity = self.test11.puzzle_activity_from_team(self.team1)
        self.assertFalse(activity.is_active)
        self.assertTrue(activity.is_completed)
        self.assertFalse(activity.is_verified)

        photo = VerificationPhoto(approved=False, photo=None)
        photo.save()

        activity.verification_photo = photo
        activity.save()
        try:
            self.assertFalse(self.test12.is_active_for_team(self.team1))
        except:  # noqa: E722
            pass
        try:
            self.assertFalse(self.test12.is_viewable_for_team(self.team1))
        except:  # noqa: E722
            pass
        self.assertFalse(self.test11.is_active_for_team(self.team1))
        self.assertTrue(self.test11.is_viewable_for_team(self.team1))
        photo.approve()
        self.assertFalse(activity.is_active)
        self.assertTrue(activity.is_completed)
        self.assertTrue(activity.is_verified)
        self.assertEqual(len(TeamPuzzleActivity.objects.filter(team=self.team1)), 3)
        self.assertNotEqual(TeamPuzzleActivity.objects.filter(team=self.team1, puzzle=self.test12).first(), None)
        self.assertNotEqual(TeamPuzzleActivity.objects.filter(team=self.team1, puzzle=self.test21).first(), None)

        self.assertTrue(self.test12.check_team_guess(self.team1, "a", bypass=True)[0])
        self.assertNotEqual(TeamPuzzleActivity.objects.filter(team=self.team1, puzzle=self.test13).first(), None)

        result = self.test21.check_team_guess(self.team1, "test")
        self.assertTrue(result[0])
        self.assertNotEqual(result[2], None)
        self.assertNotEqual(TeamPuzzleActivity.objects.filter(team=self.team1, puzzle=self.test41).first(), None)

        self.team1 = Team.objects.filter(group=Group.objects.filter(name="T1"))
