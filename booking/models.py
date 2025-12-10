from django.db import models
from staff.models import show
from accounts.models import Account


class Booking(models.Model):   # Capital B (Django convention)
    booking_code = models.CharField(max_length=100)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    show = models.ForeignKey(show, on_delete=models.CASCADE)
    seat_num = models.CharField(max_length=25, blank=True, null=True)
    num_seats = models.PositiveSmallIntegerField(blank=True, null=True)
    total = models.IntegerField(blank=True, null=True)
    show_date = models.DateField(null=True, blank=True)
    booked_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.seat_num} @ {self.show_date} - {self.show.movie.movie_name}"
