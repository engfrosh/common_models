from django.contrib.contenttypes import fields
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import datetime

import pytz
from dateutil import rrule
from django.conf import settings as django_settings
from django.template.defaultfilters import date
from dateutil.rrule import (
    DAILY,
    FR,
    HOURLY,
    MINUTELY,
    MO,
    MONTHLY,
    SA,
    SECONDLY,
    SU,
    TH,
    TU,
    WE,
    WEEKLY,
    YEARLY,
)

freq_dict_order = {
    "YEARLY": 0,
    "MONTHLY": 1,
    "WEEKLY": 2,
    "DAILY": 3,
    "HOURLY": 4,
    "MINUTELY": 5,
    "SECONDLY": 6,
}
param_dict_order = {
    "byyearday": 1,
    "bymonth": 1,
    "bymonthday": 2,
    "byweekno": 2,
    "byweekday": 3,
    "byhour": 4,
    "byminute": 5,
    "bysecond": 6,
}


class EventManager(models.Manager):
    def get_for_object(self, content_object, distinction="", inherit=True):
        return EventRelation.objects.get_events_for_object(
            content_object, distinction, inherit
        )


class Event(models.Model):
    """
    This model stores meta data for a date.  You can relate this data to many
    other models.
    """

    start = models.DateTimeField(_("start"), db_index=True)
    end = models.DateTimeField(
        _("end"),
        db_index=True,
        help_text=_("The end time must be later than the start time."),
    )
    title = models.CharField(_("title"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    creator = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("creator"),
        related_name="creator",
    )
    created_on = models.DateTimeField(_("created on"), auto_now_add=True)
    updated_on = models.DateTimeField(_("updated on"), auto_now=True)
    rule = models.ForeignKey(
        "Rule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("rule"),
        help_text=_("Select '----' for a one time only event."),
    )
    end_recurring_period = models.DateTimeField(
        _("end recurring period"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("This date is ignored for one time only events."),
    )
    calendar = models.ForeignKey(
        "Calendar", on_delete=models.CASCADE, verbose_name=_("calendar")
    )
    color_event = models.CharField(_("Color event"), blank=True, max_length=10)
    objects = EventManager()

    class Meta:
        verbose_name = _("event")
        verbose_name_plural = _("events")

    def __str__(self):
        return self.title + ": " + str(date(self.start, django_settings.DATE_FORMAT)) + \
               " - " + str(date(self.end, django_settings.DATE_FORMAT))

    @property
    def seconds(self):
        return (self.end - self.start).total_seconds()

    @property
    def minutes(self):
        return float(self.seconds) / 60

    @property
    def hours(self):
        return float(self.seconds) / 3600

    def get_absolute_url(self):
        return reverse("event", args=[self.id])

    def get_rrule_object(self, tzinfo):
        if self.rule is None:
            return
        params = self._event_params()
        frequency = self.rule.rrule_frequency()
        if timezone.is_naive(self.start):
            dtstart = self.start
        else:
            dtstart = self.start.astimezone(tzinfo).replace(tzinfo=None)

        if self.end_recurring_period is None:
            until = None
        elif timezone.is_naive(self.end_recurring_period):
            until = self.end_recurring_period
        else:
            until = self.end_recurring_period.astimezone(tzinfo).replace(tzinfo=None)

        return rrule.rrule(frequency, dtstart=dtstart, until=until, **params)

    def _create_occurrence(self, start, end=None):
        if end is None:
            end = start + (self.end - self.start)
        return Occurrence(
            event=self, start=start, end=end, original_start=start, original_end=end
        )

    def get_occurrence(self, date):
        use_naive = timezone.is_naive(date)
        tzinfo = datetime.timezone.utc
        if timezone.is_naive(date):
            date = timezone.make_aware(date, tzinfo)
        if date.tzinfo:
            tzinfo = date.tzinfo
        rule = self.get_rrule_object(tzinfo)
        if rule:
            next_occurrence = rule.after(
                date.astimezone(tzinfo).replace(tzinfo=None), inc=True
            )
            next_occurrence = pytz.timezone(str(tzinfo)).localize(next_occurrence)
        else:
            next_occurrence = self.start
        if next_occurrence == date:
            try:
                return Occurrence.objects.get(event=self, original_start=date)
            except Occurrence.DoesNotExist:
                if use_naive:
                    next_occurrence = timezone.make_naive(next_occurrence, tzinfo)
                return self._create_occurrence(next_occurrence)

    def _get_occurrence_list(self, start, end):
        """
        Returns a list of occurrences that fall completely or partially inside
        the timespan defined by start (inclusive) and end (exclusive)
        """
        if self.rule is not None:
            duration = self.end - self.start
            use_naive = timezone.is_naive(start)

            # Use the timezone from the start date
            tzinfo = datetime.timezone.utc
            if start.tzinfo:
                tzinfo = start.tzinfo

            # Limit timespan to recurring period
            occurrences = []
            if self.end_recurring_period and self.end_recurring_period < end:
                end = self.end_recurring_period

            start_rule = self.get_rrule_object(tzinfo)
            start = start.replace(tzinfo=None)
            if timezone.is_aware(end):
                end = end.astimezone(tzinfo).replace(tzinfo=None)

            o_starts = []

            # Occurrences that start before the timespan but ends inside or after timespan
            closest_start = start_rule.before(start, inc=False)
            if closest_start is not None and closest_start + duration > start:
                o_starts.append(closest_start)

            # Occurrences starts that happen inside timespan (end-inclusive)
            occs = start_rule.between(start, end, inc=True)
            # The occurrence that start on the end of the timespan is potentially
            # included above, lets remove if thats the case.
            if len(occs) > 0:
                if occs[-1] == end:
                    occs.pop()
            # Add the occurrences found inside timespan
            o_starts.extend(occs)

            # Create the Occurrence objects for the found start dates
            for o_start in o_starts:
                o_start = pytz.timezone(str(tzinfo)).localize(o_start)
                if use_naive:
                    o_start = timezone.make_naive(o_start, tzinfo)
                o_end = o_start + duration
                occurrence = self._create_occurrence(o_start, o_end)
                if occurrence not in occurrences:
                    occurrences.append(occurrence)
            return occurrences
        else:
            # check if event is in the period
            if self.start < end and self.end > start:
                return [self._create_occurrence(self.start)]
            else:
                return []

    def _occurrences_after_generator(self, after=None):
        """
        returns a generator that produces unpresisted occurrences after the
        datetime ``after``. (Optionally) This generator will return up to
        ``max_occurrences`` occurrences or has reached ``self.end_recurring_period``, whichever is smallest.
        """

        tzinfo = datetime.timezone.utc
        if after is None:
            after = timezone.now()
        elif not timezone.is_naive(after):
            tzinfo = after.tzinfo
        rule = self.get_rrule_object(tzinfo)
        if rule is None:
            if self.end > after:
                yield self._create_occurrence(self.start, self.end)
            return
        date_iter = iter(rule)
        difference = self.end - self.start
        loop_counter = 0
        for o_start in date_iter:
            o_start = pytz.timezone(str(tzinfo)).localize(o_start)
            o_end = o_start + difference
            if o_end > after:
                yield self._create_occurrence(o_start, o_end)

            loop_counter += 1

    @property
    def event_start_params(self):
        start = self.start
        params = {
            "byyearday": start.timetuple().tm_yday,
            "bymonth": start.month,
            "bymonthday": start.day,
            "byweekno": start.isocalendar()[1],
            "byweekday": start.weekday(),
            "byhour": start.hour,
            "byminute": start.minute,
            "bysecond": start.second,
        }
        return params

    @property
    def event_rule_params(self):
        return self.rule.get_params()

    def _event_params(self):
        freq_order = freq_dict_order[self.rule.frequency]
        rule_params = self.event_rule_params
        start_params = self.event_start_params
        event_params = {}

        if len(rule_params) == 0:
            return event_params

        for param in rule_params:
            # start date influences rule params
            if (
                param in param_dict_order
                and param_dict_order[param] > freq_order
                and param in start_params
            ):
                sp = start_params[param]
                if sp == rule_params[param] or (
                    hasattr(rule_params[param], "__iter__") and sp in rule_params[param]
                ):
                    event_params[param] = [sp]
                else:
                    event_params[param] = rule_params[param]
            else:
                event_params[param] = rule_params[param]

        return event_params

    @property
    def event_params(self):
        event_params = self._event_params()
        start = self.effective_start
        empty = False
        if not start:
            empty = True
        elif self.end_recurring_period and start > self.end_recurring_period:
            empty = True
        return event_params, empty

    @property
    def effective_start(self):
        if self.pk and self.end_recurring_period:
            occ_generator = self._occurrences_after_generator(self.start)
            try:
                return next(occ_generator).start
            except StopIteration:
                pass
        elif self.pk:
            return self.start
        return None

    @property
    def effective_end(self):
        if self.pk and self.end_recurring_period:
            params, empty = self.event_params
            if empty or not self.effective_start:
                return None
            elif self.end_recurring_period:
                occ = None
                occ_generator = self._occurrences_after_generator(self.start)
                for occ in occ_generator:
                    pass
                return occ.end
        elif self.pk:
            return datetime.datetime.max
        return None


class EventRelationManager(models.Manager):
    """
    >>> import datetime
    >>> EventRelation.objects.all().delete()
    >>> CalendarRelation.objects.all().delete()
    >>> data = {
    ...         'title': 'Test1',
    ...         'start': datetime.datetime(2008, 1, 1),
    ...         'end': datetime.datetime(2008, 1, 11)
    ...        }
    >>> Event.objects.all().delete()
    >>> event1 = Event(**data)
    >>> event1.save()
    >>> data['title'] = 'Test2'
    >>> event2 = Event(**data)
    >>> event2.save()
    >>> user1 = User(username='alice')
    >>> user1.save()
    >>> user2 = User(username='bob')
    >>> user2.save()
    >>> event1.create_relation(user1, 'owner')
    >>> event1.create_relation(user2, 'viewer')
    >>> event2.create_relation(user1, 'viewer')
    """

    # Currently not supported
    # Multiple level reverse lookups of generic relations appears to be
    # unsupported in Django, which makes sense.
    #
    # def get_objects_for_event(self, event, model, distinction=None):
    #     '''
    #     returns a queryset full of instances of model, if it has an EventRelation
    #     with event, and distinction
    #     >>> event = Event.objects.get(title='Test1')
    #     >>> EventRelation.objects.get_objects_for_event(event, User, 'owner')
    #     [<User: alice>]
    #     >>> EventRelation.objects.get_objects_for_event(event, User)
    #     [<User: alice>, <User: bob>]
    #     '''
    #     if distinction:
    #         dist_q = Q(eventrelation__distinction = distinction)
    #     else:
    #         dist_q = Q()
    #     ct = ContentType.objects.get_for_model(model)
    #     return model.objects.filter(
    #         dist_q,
    #         eventrelation__content_type = ct,
    #         eventrelation__event = event
    #     )

    def get_events_for_object(self, content_object, distinction="", inherit=True):
        """
        returns a queryset full of events, that relate to the object through, the
        distinction

        If inherit is false it will not consider the calendars that the events
        belong to. If inherit is true it will inherit all of the relations and
        distinctions that any calendar that it belongs to has, as long as the
        relation has inheritable set to True.  (See Calendar)

        >>> event = Event.objects.get(title='Test1')
        >>> user = User.objects.get(username = 'alice')
        >>> EventRelation.objects.get_events_for_object(user, 'owner', inherit=False)
        [<Event: Test1: Tuesday, Jan. 1, 2008-Friday, Jan. 11, 2008>]


        Now if there is a Calendar
        >>> calendar = Calendar(name = 'MyProject')
        >>> calendar.save()

        And an event that belongs to that calendar
        >>> event = Event.objects.get(title='Test2')
        >>> calendar.events.add(event)
        """
        ct = ContentType.objects.get_for_model(type(content_object))
        if distinction:
            dist_q = Q(eventrelation__distinction=distinction)
            cal_dist_q = Q(calendar__calendarrelation__distinction=distinction)
        else:
            dist_q = Q()
            cal_dist_q = Q()
        if inherit:
            inherit_q = Q(
                cal_dist_q,
                calendar__calendarrelation__content_type=ct,
                calendar__calendarrelation__object_id=content_object.id,
                calendar__calendarrelation__inheritable=True,
            )
        else:
            inherit_q = Q()
        event_q = Q(
            dist_q,
            eventrelation__content_type=ct,
            eventrelation__object_id=content_object.id,
        )
        return Event.objects.filter(inherit_q | event_q)

    def create_relation(self, event, content_object, distinction=""):
        """
        Creates a relation between event and content_object.
        See EventRelation for help on distinction.
        """
        return EventRelation.objects.create(
            event=event, distinction=distinction, content_object=content_object
        )


class EventRelation(models.Model):
    """
    This is for relating data to an Event, there is also a distinction, so that
    data can be related in different ways.  A good example would be, if you have
    events that are only visible by certain users, you could create a relation
    between events and users, with the distinction of 'visibility', or
    'ownership'.

    event: a foreign key relation to an Event model.
    content_type: a foreign key relation to ContentType of the generic object
    object_id: the id of the generic object
    content_object: the generic foreign key to the generic object
    distinction: a string representing a distinction of the relation, User could
    have a 'viewer' relation and an 'owner' relation for example.

    DISCLAIMER: while this model is a nice out of the box feature to have, it
    may not scale well.  If you use this keep that in mind.
    """

    event = models.ForeignKey(Event, on_delete=models.CASCADE, verbose_name=_("event"))
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.IntegerField(db_index=True)
    content_object = fields.GenericForeignKey("content_type", "object_id")
    distinction = models.CharField(_("distinction"), max_length=20)

    objects = EventRelationManager()

    class Meta:
        verbose_name = _("event relation")
        verbose_name_plural = _("event relations")

    def __str__(self):
        return "{}({})-{}".format(
            self.event.title, self.distinction, self.content_object
        )


class Occurrence(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, verbose_name=_("event"))
    title = models.CharField(_("title"), max_length=255, blank=True)
    description = models.TextField(_("description"), blank=True)
    start = models.DateTimeField(_("start"), db_index=True)
    end = models.DateTimeField(_("end"), db_index=True)
    cancelled = models.BooleanField(_("cancelled"), default=False)
    original_start = models.DateTimeField(_("original start"))
    original_end = models.DateTimeField(_("original end"))
    created_on = models.DateTimeField(_("created on"), auto_now_add=True)
    updated_on = models.DateTimeField(_("updated on"), auto_now=True)

    class Meta:
        verbose_name = _("occurrence")
        verbose_name_plural = _("occurrences")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        event = kwargs.get("event", None)
        if not self.title and event:
            self.title = event.title
        if not self.description and event:
            self.description = event.description

    def moved(self):
        return self.original_start != self.start or self.original_end != self.end

    moved = property(moved)

    def move(self, new_start, new_end):
        self.start = new_start
        self.end = new_end
        self.save()

    def cancel(self):
        self.cancelled = True
        self.save()

    def uncancel(self):
        self.cancelled = False
        self.save()

    @property
    def seconds(self):
        return (self.end - self.start).total_seconds()

    @property
    def minutes(self):
        return float(self.seconds) / 60

    @property
    def hours(self):
        return float(self.seconds) / 3600

    def get_absolute_url(self):
        if self.pk is not None:
            return reverse(
                "occurrence",
                kwargs={"occurrence_id": self.pk, "event_id": self.event_id},
            )
        return reverse(
            "occurrence_by_date",
            kwargs={
                "event_id": self.event_id,
                "year": self.start.year,
                "month": self.start.month,
                "day": self.start.day,
                "hour": self.start.hour,
                "minute": self.start.minute,
                "second": self.start.second,
            },
        )

    def get_cancel_url(self):
        if self.pk is not None:
            return reverse(
                "cancel_occurrence",
                kwargs={"occurrence_id": self.pk, "event_id": self.event_id},
            )
        return reverse(
            "cancel_occurrence_by_date",
            kwargs={
                "event_id": self.event_id,
                "year": self.start.year,
                "month": self.start.month,
                "day": self.start.day,
                "hour": self.start.hour,
                "minute": self.start.minute,
                "second": self.start.second,
            },
        )

    def get_edit_url(self):
        if self.pk is not None:
            return reverse(
                "edit_occurrence",
                kwargs={"occurrence_id": self.pk, "event_id": self.event_id},
            )
        return reverse(
            "edit_occurrence_by_date",
            kwargs={
                "event_id": self.event_id,
                "year": self.start.year,
                "month": self.start.month,
                "day": self.start.day,
                "hour": self.start.hour,
                "minute": self.start.minute,
                "second": self.start.second,
            },
        )

    def __str__(self):
        return str(date(self.start, django_settings.DATE_FORMAT)) + " to " + \
               str(date(self.end, django_settings.DATE_FORMAT))

    def __lt__(self, other):
        return self.end < other.end

    def __hash__(self):
        if not self.pk:
            raise TypeError("Model instances without primary key value are unhashable")
        return hash(self.pk)

    def __eq__(self, other):
        return (
            isinstance(other, Occurrence)
            and self.original_start == other.original_start
            and self.original_end == other.original_end
        )


class CalendarManager(models.Manager):
    """
    >>> user1 = User(username='tony')
    >>> user1.save()
    """

    def get_calendar_for_object(self, obj, distinction=""):
        """
        This function gets a calendar for an object.  It should only return one
        calendar.  If the object has more than one calendar related to it (or
        more than one related to it under a distinction if a distinction is
        defined) an AssertionError will be raised.  If none are returned it will
        raise a DoesNotExistError.

        >>> user = User.objects.get(username='tony')
        >>> try:
        ...     Calendar.objects.get_calendar_for_object(user)
        ... except Calendar.DoesNotExist:
        ...     print("failed")
        ...
        failed

        Now if we add a calendar it should return the calendar

        >>> calendar = Calendar(name='My Cal')
        >>> calendar.save()
        >>> calendar.create_relation(user)
        >>> Calendar.objects.get_calendar_for_object(user)
        <Calendar: My Cal>

        Now if we add one more calendar it should raise an AssertionError
        because there is more than one related to it.

        If you would like to get more than one calendar for an object you should
        use get_calendars_for_object (see below).
        >>> calendar = Calendar(name='My 2nd Cal')
        >>> calendar.save()
        >>> calendar.create_relation(user)
        >>> try:
        ...     Calendar.objects.get_calendar_for_object(user)
        ... except AssertionError:
        ...     print("failed")
        ...
        failed
        """
        calendar_list = self.get_calendars_for_object(obj, distinction)
        if len(calendar_list) == 0:
            raise Calendar.DoesNotExist("Calendar does not exist.")
        elif len(calendar_list) > 1:
            raise AssertionError("More than one calendars were found.")
        else:
            return calendar_list[0]

    def get_or_create_calendar_for_object(self, obj, distinction="", name=None):
        """
        >>> user = User(username="jeremy")
        >>> user.save()
        >>> calendar = Calendar.objects.get_or_create_calendar_for_object(user, name = "Jeremy's Calendar")
        >>> calendar.name
        "Jeremy's Calendar"
        """
        try:
            return self.get_calendar_for_object(obj, distinction)
        except Calendar.DoesNotExist:
            if name is None:
                calendar = self.model(name=str(obj))
            else:
                calendar = self.model(name=name)
            calendar.slug = slugify(calendar.name)
            calendar.save()
            calendar.create_relation(obj, distinction)
            return calendar

    def get_calendars_for_object(self, obj, distinction=""):
        """
        This function allows you to get calendars for a specific object

        If distinction is set it will filter out any relation that doesnt have
        that distinction.
        """
        ct = ContentType.objects.get_for_model(obj)
        if distinction:
            dist_q = Q(calendarrelation__distinction=distinction)
        else:
            dist_q = Q()
        return self.filter(
            dist_q,
            calendarrelation__content_type=ct,
            calendarrelation__object_id=obj.id,
        )


class Calendar(models.Model):
    """
    This is for grouping events so that batch relations can be made to all
    events.  An example would be a project calendar.

    name: the name of the calendar
    events: all the events contained within the calendar.
    >>> calendar = Calendar(name = 'Test Calendar')
    >>> calendar.save()
    >>> data = {
    ...         'title': 'Recent Event',
    ...         'start': datetime.datetime(2008, 1, 5, 0, 0),
    ...         'end': datetime.datetime(2008, 1, 10, 0, 0)
    ...        }
    >>> event = Event(**data)
    >>> event.save()
    >>> calendar.events.add(event)
    >>> data = {
    ...         'title': 'Upcoming Event',
    ...         'start': datetime.datetime(2008, 1, 1, 0, 0),
    ...         'end': datetime.datetime(2008, 1, 4, 0, 0)
    ...        }
    >>> event = Event(**data)
    >>> event.save()
    >>> calendar.events.add(event)
    >>> data = {
    ...         'title': 'Current Event',
    ...         'start': datetime.datetime(2008, 1, 3),
    ...         'end': datetime.datetime(2008, 1, 6)
    ...        }
    >>> event = Event(**data)
    >>> event.save()
    >>> calendar.events.add(event)
    """

    name = models.CharField(_("name"), max_length=200)
    slug = models.SlugField(_("slug"), max_length=200, unique=True)
    objects = CalendarManager()

    class Meta:
        verbose_name = _("calendar")
        verbose_name_plural = _("calendars")

    def __str__(self):
        return self.name

    @property
    def events(self):
        return self.event_set

    def create_relation(self, obj, distinction="", inheritable=True):
        """
        Creates a CalendarRelation between self and obj.

        if Inheritable is set to true this relation will cascade to all events
        related to this calendar.
        """
        CalendarRelation.objects.create_relation(self, obj, distinction, inheritable)

    def get_recent(self, amount=5):
        """
        This shortcut function allows you to get events that have started
        recently.

        amount is the amount of events you want in the queryset. The default is
        5.
        """
        return self.events.order_by("-start").filter(start__lt=timezone.now())[:amount]

    def get_absolute_url(self):
        return reverse("fullcalendar", kwargs={"calendar_slug": self.slug})


class CalendarRelationManager(models.Manager):
    def create_relation(
        self, calendar, content_object, distinction="", inheritable=True
    ):
        """
        Creates a relation between calendar and content_object.
        See CalendarRelation for help on distinction and inheritable
        """
        return CalendarRelation.objects.create(
            calendar=calendar, distinction=distinction, content_object=content_object
        )


class CalendarRelation(models.Model):
    """
    This is for relating data to a Calendar, and possible all of the events for
    that calendar, there is also a distinction, so that the same type or kind of
    data can be related in different ways.  A good example would be, if you have
    calendars that are only visible by certain users, you could create a
    relation between calendars and users, with the distinction of 'visibility',
    or 'ownership'.  If inheritable is set to true, all the events for this
    calendar will inherit this relation.

    calendar: a foreign key relation to a Calendar object.
    content_type: a foreign key relation to ContentType of the generic object
    object_id: the id of the generic object
    content_object: the generic foreign key to the generic object
    distinction: a string representing a distinction of the relation, User could
    have a 'veiwer' relation and an 'owner' relation for example.
    inheritable: a boolean that decides if events of the calendar should also
    inherit this relation

    DISCLAIMER: while this model is a nice out of the box feature to have, it
    may not scale well.  If you use this, keep that in mind.
    """

    calendar = models.ForeignKey(
        Calendar, on_delete=models.CASCADE, verbose_name=_("calendar")
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.IntegerField(db_index=True)
    content_object = fields.GenericForeignKey("content_type", "object_id")
    distinction = models.CharField(_("distinction"), max_length=20)
    inheritable = models.BooleanField(_("inheritable"), default=True)

    objects = CalendarRelationManager()

    class Meta:
        verbose_name = _("calendar relation")
        verbose_name_plural = _("calendar relations")

    def __str__(self):
        return "{} - {}".format(self.calendar, self.content_object)


freqs = (
    ("YEARLY", _("Yearly")),
    ("MONTHLY", _("Monthly")),
    ("WEEKLY", _("Weekly")),
    ("DAILY", _("Daily")),
    ("HOURLY", _("Hourly")),
    ("MINUTELY", _("Minutely")),
    ("SECONDLY", _("Secondly")),
)


class Rule(models.Model):
    """
    This defines a rule by which an event will recur.  This is defined by the
    rrule in the dateutil documentation.

    * name - the human friendly name of this kind of recursion.
    * description - a short description describing this type of recursion.
    * frequency - the base recurrence period
    * param - extra params required to define this type of recursion. The params
      should follow this format:

        param = [rruleparam:value;]*
        rruleparam = see list below
        value = int[,int]*

      The options are: (documentation for these can be found at
      https://dateutil.readthedocs.io/en/stable/rrule.html#module-dateutil.rrule
        ** count
        ** bysetpos
        ** bymonth
        ** bymonthday
        ** byyearday
        ** byweekno
        ** byweekday
        ** byhour
        ** byminute
        ** bysecond
        ** byeaster
    """

    name = models.CharField(_("name"), max_length=32)
    description = models.TextField(_("description"))
    frequency = models.CharField(_("frequency"), choices=freqs, max_length=10)
    params = models.TextField(_("params"), blank=True)

    _week_days = {"MO": MO, "TU": TU, "WE": WE, "TH": TH, "FR": FR, "SA": SA, "SU": SU}

    class Meta:
        verbose_name = _("rule")
        verbose_name_plural = _("rules")

    def rrule_frequency(self):
        compatibility_dict = {
            "DAILY": DAILY,
            "MONTHLY": MONTHLY,
            "WEEKLY": WEEKLY,
            "YEARLY": YEARLY,
            "HOURLY": HOURLY,
            "MINUTELY": MINUTELY,
            "SECONDLY": SECONDLY,
        }
        return compatibility_dict[self.frequency]

    def _weekday_or_number(self, param):
        """
        Receives a rrule parameter value, returns a upper case version
        of the value if its a weekday or an integer if its a number
        """
        try:
            return int(param)
        except (TypeError, ValueError):
            uparam = str(param).upper()
            if uparam in Rule._week_days:
                return Rule._week_days[uparam]

    def get_params(self):
        """
        >>> rule = Rule(params = "count:1;bysecond:1;byminute:1,2,4,5")
        >>> rule.get_params()
        {'count': 1, 'byminute': [1, 2, 4, 5], 'bysecond': 1}
        """
        params = self.params.split(";")
        param_dict = []
        for param in params:
            param = param.split(":")
            if len(param) != 2:
                continue

            param = (
                str(param[0]).lower(),
                [
                    x
                    for x in [self._weekday_or_number(v) for v in param[1].split(",")]
                    if x is not None
                ],
            )

            if len(param[1]) == 1:
                param_value = self._weekday_or_number(param[1][0])
                param = (param[0], param_value)
            param_dict.append(param)
        return dict(param_dict)

    def __str__(self):
        """Human readable string for Rule"""
        return "Rule {} params {}".format(self.name, self.params)
