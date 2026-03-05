import base64
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from jwt.exceptions import JWTDecodeError
from jwt import JWT, jwk_from_dict
from rest_framework import status
from rest_framework.response import Response
from django.utils.dateparse import parse_date
from django.db.models import Q


class CustomJWTAuthentication(BaseAuthentication):

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]

        User = get_user_model()

        try:
            payload = self.decode_token(token)
            user_id = payload.get('id')

            if not user_id:
                raise AuthenticationFailed('Invalid token: User ID not found')

            user = User.objects.get(id=user_id)

            return (user, token)

        except JWTDecodeError:
            raise AuthenticationFailed('Invalid token')
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')

    def decode_token(self, token):
        jwt_instance = JWT()
        secret_key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()).decode()
        payload = jwt_instance.decode(token, jwk_from_dict({'k': secret_key, 'kty': 'oct'}))
        return payload


from rest_framework import generics, permissions, status
from .models import Habit, HabitTracking, Category
from .serializers import HabitSerializer, HabitTrackingSerializer, CategorySerializer
from rest_framework.views import APIView
from datetime import datetime
import json
import traceback
from rest_framework import serializers

class HabitListView(generics.ListAPIView):
    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [CustomJWTAuthentication]

    def get_queryset(self):
        return Habit.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class HabitListCreateView(generics.ListCreateAPIView):
    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [CustomJWTAuthentication]

    def get_queryset(self):
        date_param = self.request.query_params.get("date")
        if date_param:
            try:
                selected_date = datetime.strptime(date_param, "%Y-%m-%d")
            except ValueError:
                selected_date = datetime.today()
        else:
            selected_date = datetime.today()

        day_name = selected_date.strftime("%a")
        day_number = selected_date.day
        user = self.request.user
        habits = Habit.objects.filter(user=user)

        filtered_habits = []
        for habit in habits:
            try:
                habit_created_at = habit.created_at
                if selected_date.date() < habit_created_at.date():
                    continue
                
                completed_count = sum(1 for t in habit.trackings.all() if t.completed)

                habit_days = habit.days
                if not isinstance(habit_days, list):
                    habit_days = json.loads(habit_days)

                fully_completed_date = None

                if completed_count >= habit.duration:
                    all_trackings = habit.trackings.filter().order_by("date")
                    completed_trackings = [t for t in all_trackings if t.completed]
                    
                    for i in range(len(completed_trackings)):
                        count = sum(1 for t in completed_trackings[:i + 1])
                        if count >= habit.duration:
                            fully_completed_date = completed_trackings[i].date
                            break

                    if fully_completed_date and fully_completed_date.strftime("%Y-%m-%d") != date_param:
                        continue

                if (
                    habit.frequency == "daily"
                    or (habit.frequency == "weekly" and day_name in habit_days)
                    or (habit.frequency == "monthly" and day_number in habit_days)
                ):
                    habit.completed_count = completed_count
                    filtered_habits.append(habit)
                else:
                    habit.completed_count = completed_count
                    filtered_habits.append(habit)

            except Exception as e:
                traceback.print_exc()

        return filtered_habits
    
    def perform_create(self, serializer):
        user = self.request.user

        if not user.is_pro:
            habit_count = Habit.objects.filter(user=user).count()
            if habit_count >= 5:
                raise serializers.ValidationError({
                    "message": "You have reached the habit limit for the Basic plan. Upgrade to Pro to add more habits."
                })

        category_name = self.request.data.get("category")
        if category_name:
            category, created = Category.objects.get_or_create(name=category_name)
            serializer.save(user=user, category=category)
        else:
            serializer.save(user=user)


        
class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [CustomJWTAuthentication]

    def get_queryset(self):
        return Category.objects.all()


class HabitRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [CustomJWTAuthentication]

    def get_queryset(self):
        return Habit.objects.filter(user=self.request.user)


class HabitTrackingListCreateView(generics.ListCreateAPIView):
    serializer_class = HabitTrackingSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [CustomJWTAuthentication]

    def get_queryset(self):
        queryset = HabitTracking.objects.filter(habit__user=self.request.user)
        date_param = self.request.query_params.get("date")

        if date_param:
            try:
                selected_date = parse_date(date_param)
                if selected_date:
                    return queryset.filter(Q(date__lte=selected_date))
            except ValueError:
                pass
            
        return queryset

    def perform_create(self, serializer):
        habit_id = self.request.data.get('habit')
        date = self.request.data.get('date')  
        completed = self.request.data.get('completed') 

        if not habit_id or not date:
            return Response(
                {"detail": "Both 'habit' and 'date' fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            habit = Habit.objects.get(id=habit_id, user=self.request.user)
        except Habit.DoesNotExist:
            return Response(
                {"detail": "Habit not found or does not belong to the user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            habit_tracking = HabitTracking.objects.get(habit=habit, date=date)
            habit_tracking.completed = completed
            habit_tracking.save()
            serializer.instance = habit_tracking
        except HabitTracking.DoesNotExist:
            serializer.save(habit=habit, user=self.request.user)


from django.utils.timezone import now, timedelta

class HabitProgressView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [CustomJWTAuthentication]

    def get(self, request, *args, **kwargs):
        last_7_days = [now().date() - timedelta(days=i) for i in range(7)]
        progress = []

        for day in last_7_days:
            habit_trackings = HabitTracking.objects.filter(user=request.user, date=day)

            total_habits = habit_trackings.count()

            completed_count = sum(1 for habit in habit_trackings if habit.completed)

            progress.append({
                "date": day.strftime("%Y-%m-%d"),
                "completed": completed_count,
                "total": total_habits
            })

        return Response({"progress": progress})


class HabitSearchView(generics.ListAPIView):
    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [CustomJWTAuthentication]

    def get_queryset(self):
        query = self.request.query_params.get("q", "")
        exact_match = self.request.query_params.get("exact_match", "false").lower() == "true"

        if query:
            if exact_match:
                return Habit.objects.filter(name__iexact=query, user=self.request.user)
            return Habit.objects.filter(name__icontains=query, user=self.request.user)
        
        return Habit.objects.none()
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"detail": "No habits found."}, status=404)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    
from collections import defaultdict

class HabitStatsView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, habit_id):
        habit = Habit.objects.filter(id=habit_id, user=request.user).first()
        if not habit:
            return Response({"error": "Habit not found"}, status=404)

        habit_tracking = HabitTracking.objects.filter(habit=habit).order_by("date")

        completed_days = sum(1 for entry in habit_tracking if entry.completed)
        total_days = habit.duration
        
        success_rate = (completed_days / total_days * 100) if total_days > 0 else 0
        
        completion_data = [
            {"date": record.date.isoformat(), "completed": record.completed}
            for record in habit_tracking
        ]

        weekly_data = defaultdict(int)
        for entry in habit_tracking:
            if entry.completed:
                week = f"{entry.date.year}-W{entry.date.strftime('%U')}"
                weekly_data[week] += 1

        weekly_completions = [{"week": week, "count": count} for week, count in sorted(weekly_data.items())]

        monthly_completions = []
        monthly_data = defaultdict(int)
        for entry in habit_tracking:
            if entry.completed:
                month = entry.date.replace(day=1)
                monthly_data[month] += 1

        monthly_completions = [
            {"month": month.isoformat(), "count": count} 
            for month, count in sorted(monthly_data.items())
        ]

        max_streak = self.calculate_max_streak(habit_tracking)

        return Response({
            "completion_data": completion_data,
            "success_rate": round(success_rate, 2),
            "max_streak": max_streak,
            "weekly_completions": weekly_completions,
            "monthly_completions": monthly_completions
        })

    def calculate_max_streak(self, habit_tracking):
        max_streak = 0
        current_streak = 0
        last_date = None

        for record in habit_tracking:
            if record.completed:
                if last_date and record.date == last_date + timedelta(days=1):
                    current_streak += 1
                else:
                    current_streak = 1

                max_streak = max(max_streak, current_streak)
                last_date = record.date 
            else:
                current_streak = 0
                last_date = None 

        return max_streak
    
from collections import Counter

class HabitCompletionStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        user_habits = HabitTracking.objects.filter(habit__user=user)
        trackings = [t for t in user_habits if t.habit.user == user and t.completed]

        habit_counts = Counter([t.habit.name for t in trackings])

        habit_list = [{"habit": habit, "total": count} for habit, count in habit_counts.items()]

        return Response({"habits": habit_list})

class HabitConsistencyStatsView(APIView):
    def get(self, request):
        user = request.user
        period = request.GET.get("period", "week")

        if period == "week":
            start_date = now().date() - timedelta(days=6)
        elif period == "month":
            start_date = now().date() - timedelta(days=29)
        else:
            return Response({"error": "Invalid period parameter"}, status=400)

        end_date = now().date()

        user_habits = Habit.objects.filter(user=user)

        date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

        expected_trackings = [(habit, date) for habit in user_habits for date in date_range]

        
        actual_trackings = HabitTracking.objects.filter(
            habit__user=user, 
            date__gte=start_date, 
            date__lte=end_date
        )

        completed_habits = sum(1 for habit, date in expected_trackings if actual_trackings.filter(habit=habit, date=date, completed=True).exists())

        total_habits = len(expected_trackings)

        consistency_rate = (completed_habits / total_habits) * 100 if total_habits > 0 else 0

        return Response(
            {
                "completed": completed_habits,
                "not_completed": total_habits - completed_habits,
                "consistency_rate": consistency_rate,
            }
        )

class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"message": "Account deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class DeleteAllDataView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        Habit.objects.filter(user=user).delete()
        return Response({"message": "All habits and progress deleted"}, status=status.HTTP_204_NO_CONTENT)
