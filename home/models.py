# -*- coding: utf-8 -*-
from django.db import models
from datetime import datetime, timedelta
from django.core.validators import RegexValidator, MinLengthValidator, EmailValidator, MaxValueValidator, MinValueValidator
from django.utils.translation import ugettext as _

import calendar
# # 地域テーブル
class Region(models.Model):
	code = models.CharField(max_length=25, unique=True)
	name = models.CharField(max_length=254)

	def __unicode__(self):
		return self.name

	def __str__(self):
		return self.name

# # 最寄り駅テーブル
class NearestStation(models.Model):
	code = models.CharField(max_length=25, unique=True)
	name = models.CharField(max_length=254)

	def __unicode__(self):
		return self.name

	def __str__(self):
		return self.name

# ソートキーテーブル
SORT_KEY = (('store_id', 'Store Code'), ('region__code', 'Region'), ('nearest_station__code', 'Nearest Station'));
class Sortkey(models.Model):
	sorttype = models.CharField(default='001', max_length=25, editable=False, unique=True)
	key1 = models.CharField(max_length=25, choices= SORT_KEY, default='region__code')
	key2 = models.CharField(max_length=25, choices=SORT_KEY, default='store_id')

	def __str__(self):
		return 'Sort key. Click to edit'

class Store(models.Model):
	id = models.AutoField(primary_key=True, unique=True)
	store_id = models.CharField(_('Store Code'), max_length=254, unique=True, validators=[MinLengthValidator(1)])
	name = models.TextField(_('Store Name'), max_length=508, validators=[MinLengthValidator(1)])
	phone = models.CharField(_('Phone'), max_length=15, \
				validators=[
					RegexValidator(
						regex='^[0-9]+(-?[0-9]+)+$',
						message='電話番号を正しく入力してください。',
						code='invalid_phone'
					),
				])
	mail = models.EmailField(verbose_name = _('Email'), validators=[
			EmailValidator(message='メールアドレスを正しく入力してください。')
		])
	image = models.ImageField(_('Store Image'), upload_to = 'static/upload/', blank=True)
	display = models.BooleanField(_('Store Display'), default=True)

	access = models.TextField(_('Store Access'), max_length=500, blank=True)
	comment = models.TextField(_('Store comment'), max_length=500, blank=True)

	region = models.ForeignKey(Region, null=True, blank=True)
	nearest_station = models.ForeignKey(NearestStation, null=True, blank=True)

	created = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.store_id + ' ・ ' + self.name

	def store_time_range(self, working_day, working_holiday):
		open_hr = 21
		close_hr = 8
		time_range = range(8, 22)
		for day in working_day:
			for i in time_range:
				available_slot = getattr(day, "hour_"+str(i))
				if available_slot != None and available_slot > 0:
					if i < open_hr:
						open_hr = i
					if i > close_hr:
						close_hr = i
		for day in working_holiday:
			for i in time_range:
				available_slot = getattr(day, "hour_"+str(i))
				if available_slot != None and available_slot > 0:
					if i < open_hr:
						open_hr = i
					if i > close_hr:
						close_hr = i
		return range(open_hr,close_hr+1)

	def generate_booking_matrix(self, working_day, schedule_list, working_holiday,
								days_range, time_range, holiday_default_list):
		# declare a hash table mat which keys are hours, values are working days and its status
		mat = {
			"8": {}, "9": {}, "10": {}, "11": {}, "12": {},
			"13": {}, "14": {}, "15": {}, "16": {}, "17": {},
			"18": {}, "19": {}, "20": {}, "21": {}, "holiday": {}
		}
		today = datetime.now().date()
		holiday_default = None

		# populate all booked slot from schedule table into hash table mat, if
		# a time slot is booked with hour=h, day=d, then hash table with key = h,
		# value = d will accept a child object with attributes book = 1
		for booked_day in schedule_list:
			date_str = booked_day.date.strftime("%d/%m/%Y")
			if date_str in mat[str(booked_day.hour)]:
				mat[str(booked_day.hour)][booked_day.date.strftime("%d/%m/%Y")]["book"] += 1
			else:
				mat[str(booked_day.hour)][booked_day.date.strftime("%d/%m/%Y")] = {"book": 1}

		# populate all avalable slot in working day to hash table, each available slot with
		# hour=h, weekday=wd, we will find current dates maps with weekday and set
		# child object new attributes available = 1

		for index,day in enumerate(working_day):
			day_str = days_range[index].strftime("%d/%m/%Y")
			weekday_index = int(days_range[index].strftime("%w")) - 1
			if weekday_index == -1:
				weekday_index = 6
			day = working_day[weekday_index]
			check_day_off = day.is_dayoff(time_range)
			for i in time_range:
				available_slot = getattr(day, "hour_"+str(i))
				if check_day_off == True:
					if day_str in mat[str(i)]:
						mat[str(i)][day_str]["dayoff"] = 1
					else:
						mat[str(i)][day_str] = {"dayoff": 1}
					if index < 7:
						next_day_str = days_range[index+7].strftime("%d/%m/%Y")
						if next_day_str in mat[str(i)]:
							mat[str(i)][next_day_str]["dayoff"] = 1
						else:
							mat[str(i)][next_day_str] = {"dayoff": 1}

				if available_slot != None and available_slot > 0:
					if not day_str in mat[str(i)]:
						mat[str(i)][day_str] = {}
					if days_range[index] > today:
						mat[str(i)][day_str]["available"] = available_slot
					if index < 7:
						next_day_str = days_range[index+7].strftime("%d/%m/%Y")
						if not next_day_str in mat[str(i)]:
							mat[str(i)][next_day_str] = {}
						if days_range[index+7] > today:
							mat[str(i)][next_day_str]["available"] = available_slot

		holiday_default = working_day[7]
		# populate available slot in holiday default list
		for day in holiday_default_list:
			day_str = day.date.strftime("%d/%m/%Y")
			mat["holiday"][day_str] = 1
			for i in time_range:
				available_slot = getattr(holiday_default, "hour_"+str(i))
				if day_str in mat[str(i)]:
					mat[str(i)][day_str]["holiday"] = 1
					if available_slot != None and available_slot > 0 and day.date>today and mat[str(i)][day_str].get("dayoff") != True:
						mat[str(i)][day_str]["holiday_available"] = available_slot
				elif available_slot != None and available_slot > 0:
					mat[str(i)][day_str] = {"holiday": 1, "holiday_available": available_slot}

		# populate available slot in holiday working to hash table
		for day in working_holiday:
			day_str = day.date.strftime("%d/%m/%Y")
			mat["holiday"][day.date.strftime("%d/%m/%Y")] = 1
			for i in time_range:
				available_slot = getattr(day, "hour_"+str(i))
				if day.is_dayoff(time_range) == False and not day_str in mat[str(i)]:
					mat[str(i)][day_str] = {}
				if day_str in mat[str(i)]:
					mat[str(i)][day_str]["holiday"] = 1
					if available_slot != None and available_slot > 0 and day.date>today:
						mat[str(i)][day_str]["holiday_available"] = available_slot

		return mat


	def get_store_code(self):
		return self.store_id

	def __unicode__(self):
		return self.name

WORKING_DAY = (
	('Mo', _('Monday')),
	('Tu', _('Tuesday')),
	('We', _('Wednesday')),
	('Th', _('Thursday')),
	('Fr', _('Friday')),
	('Sa', _('Saturday')),
	('Su', _('Sunday')),
	('Ho', _('Holiday'))
)

class WorkingDay(models.Model):
	store = models.ForeignKey(Store)
	type = models.CharField(max_length=2, choices=WORKING_DAY, verbose_name=_('Type'))

	hour_8 = models.IntegerField(blank=True, null=True, verbose_name=_('8'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_9 = models.IntegerField(blank=True, null=True, verbose_name=_('9'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_10 = models.IntegerField(blank=True, null=True, verbose_name=_('10'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_11 = models.IntegerField(blank=True, null=True, verbose_name=_('11'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_12 = models.IntegerField(blank=True, null=True, verbose_name=_('12'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_13 = models.IntegerField(blank=True, null=True, verbose_name=_('13'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_14 = models.IntegerField(blank=True, null=True, verbose_name=_('14'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_15 = models.IntegerField(blank=True, null=True, verbose_name=_('15'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_16 = models.IntegerField(blank=True, null=True, verbose_name=_('16'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_17 = models.IntegerField(blank=True, null=True, verbose_name=_('17'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_18 = models.IntegerField(blank=True, null=True, verbose_name=_('18'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_19 = models.IntegerField(blank=True, null=True, verbose_name=_('19'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_20 = models.IntegerField(blank=True, null=True, verbose_name=_('20'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_21 = models.IntegerField(blank=True, null=True, verbose_name=_('21'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])

	def is_dayoff(self,time_range):
		for i in time_range:
			available_slot = getattr(self, "hour_"+str(i))
			if available_slot != None and available_slot > 0:
				return False
		return True

	class Meta:
		unique_together = (('store', 'type'), )

	def __str__(self):
		return _(self.type)

class HolidayWorking(models.Model):
	store = models.ForeignKey(Store, verbose_name=_('Store'))
	date = models.DateField(_('holiday date'))

	hour_8 = models.IntegerField(blank=True, null=True, verbose_name=_('8'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_9 = models.IntegerField(blank=True, null=True, verbose_name=_('9'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_10 = models.IntegerField(blank=True, null=True, verbose_name=_('10'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_11 = models.IntegerField(blank=True, null=True, verbose_name=_('11'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_12 = models.IntegerField(blank=True, null=True, verbose_name=_('12'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_13 = models.IntegerField(blank=True, null=True, verbose_name=_('13'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_14 = models.IntegerField(blank=True, null=True, verbose_name=_('14'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_15 = models.IntegerField(blank=True, null=True, verbose_name=_('15'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_16 = models.IntegerField(blank=True, null=True, verbose_name=_('16'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_17 = models.IntegerField(blank=True, null=True, verbose_name=_('17'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_18 = models.IntegerField(blank=True, null=True, verbose_name=_('18'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_19 = models.IntegerField(blank=True, null=True, verbose_name=_('19'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_20 = models.IntegerField(blank=True, null=True, verbose_name=_('20'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])
	hour_21 = models.IntegerField(blank=True, null=True, verbose_name=_('21'), \
	validators=[ \
            MaxValueValidator(99, "枠を正しく入力してください。"), \
            MinValueValidator(0, "枠を正しく入力してください。") \
        ])

	class Meta:
		unique_together = (('store', 'date'), )

	def is_dayoff(self,time_range):
		dayoff = True
		for i in time_range:
			if getattr(self, "hour_"+str(i)) == 1:
				return False
		return dayoff

	def __str__(self):
		return _(str(self.date))

class Schedule(models.Model):
	store = models.ForeignKey(Store)
	date = models.DateField('schedule date')
	hour = models.IntegerField()
	name = models.CharField(max_length=254)
	phone = models.CharField(max_length=15,\
				validators=[
					RegexValidator(
						regex='^[0-9]+(-?[0-9]+)+$',
						message='電話番号を正しく入力してください。',
						code='invalid_phone'
					),
				])
	email = models.EmailField()
	symptom = models.TextField(max_length=500, blank=True)

class Holiday(models.Model):
	date = models.DateField('holiday')
	def __unicode__(self):
		return self.date.strftime("%d/%m/%Y")
