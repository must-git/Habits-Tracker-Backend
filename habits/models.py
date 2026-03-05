from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import JSONField
from django.core.exceptions import ValidationError
from djongo import models

User = get_user_model()

class Category(models.Model):
    _id = models.ObjectIdField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Habit(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    HABIT_TYPE_CHOICES = [
        ('Good', 'Good Habit'),
        ('Bad', 'Bad Habit'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habits')
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='daily')
    duration = models.IntegerField(blank=True, null=True)
    days = JSONField(default=list)
    reminder_time = models.TimeField(blank=True, null=True)
    habit_type = models.CharField(max_length=10, choices=HABIT_TYPE_CHOICES, default='Good')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.habit_type})"
    
    def clean(self):
        if self.frequency == 'weekly':
            if not self.days or not all(day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] for day in self.days):
                raise ValidationError("For weekly habits, you must select at least one valid day of the week.")
        elif self.frequency == 'monthly':
            if not self.days or not all(isinstance(day, int) and 1 <= day <= 31 for day in self.days):
                raise ValidationError("For monthly habits, you must select at least one valid date of the month (1–31).")
        elif self.frequency == 'daily':
            self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

class HabitTracking(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='trackings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habit_trackings', null=True, blank=True)
    date = models.DateField()
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.habit.name} - {self.date} ({'Avoided' if self.habit.habit_type == 'Bad' else 'Completed'})"