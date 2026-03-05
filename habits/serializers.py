from rest_framework import serializers
from .models import Habit, HabitTracking, Category
from datetime import datetime
import json

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["_id", "name"]

class HabitSerializer(serializers.ModelSerializer):
    fully_completed_today = serializers.SerializerMethodField()
    is_today = serializers.SerializerMethodField()
    category = serializers.SlugRelatedField(
        queryset=Category.objects.all(), slug_field="name"
    )
    class Meta:
        model = Habit
        fields = ['id', 'user', 'name', 'category', 'frequency','duration', 'days', 'reminder_time', 'habit_type', 'created_at', 'updated_at', 'fully_completed_today', 'is_today']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_fully_completed_today(self, obj):
        today = datetime.today().date()
        completed_trackings = [t for t in obj.trackings.all() if t.completed]
        latest_tracking = max(completed_trackings, key=lambda t: t.date, default=None)
        if latest_tracking and latest_tracking.date == today:
            return True
        return False
    
    def get_is_today(self, obj):
        today = datetime.today()
        today_day_name = today.strftime("%a")
        today_day_number = today.day

        habit_days = obj.days
        if not isinstance(habit_days, list):
            habit_days = json.loads(habit_days)
        
        if (obj.frequency == "daily"
            or (obj.frequency == "weekly" and today_day_name in habit_days)
            or (obj.frequency == "monthly" and today_day_number in habit_days)
                ):
                    return True
        return False

class HabitTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitTracking
        fields = ['id', 'habit', 'date', 'completed']
        read_only_fields = ['id']