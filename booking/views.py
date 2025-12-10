from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import user_passes_test

from staff.models import film, banner, show
from .models import booking
from accounts.views import user_login_required

from datetime import date, datetime, timedelta, timezone
import random
import string


# ---------------- Home ----------------
def home(request):
    movies = film.objects.all()
    banners = banner.objects.all()
    return render(request,"index.html", {'films': movies,'banners':banners})


# ---------------- Movie Detail ----------------
def movie_detail(request,id):
    film_obj = get_object_or_404(film, id=id)
    shows = show.objects.filter(movie=id, end_date__gte=date.today())
    return render(request,"movie_detail.html", {
        'film': film_obj,
        'showtimes': shows
    })


# ---------------- Showtime Selection ----------------
@user_passes_test(user_login_required, login_url='/accounts/usersignin')
def show_select(request):
    selected_date = request.GET.get('date')

    if not selected_date:
        selected_date = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')

    selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()

    shows = show.objects.filter(
        start_date__lte=selected_date_obj,
        end_date__gte=selected_date_obj,
        movie__isnull=False
    ).select_related('movie').order_by('movie_id','showtime')

    return render(request,"show_selection.html", {
        'shows': shows,
        'date': selected_date
    })


# ---------------- Seat Layout Page ----------------
@user_passes_test(user_login_required, login_url='/accounts/usersignin')
def seat_view(request, show_id):
    show_obj = get_object_or_404(show, id=show_id)
    return render(request, "seats.html", {"show": show_obj})


# ---------------- Ajax booked seats ----------------
def bookedseats(request):
    if request.method == 'GET':
        show_id = request.GET.get('show_id')
        show_date = request.GET.get('show_date')

        seats = booking.objects.filter(
            show=show_id,
            show_date=show_date
        ).values_list('seat_num', flat=True)

        return HttpResponse(",".join(seats))

    return HttpResponse("Invalid request")


# ---------------- Book Tickets (Main Fix) ----------------
@user_passes_test(user_login_required, login_url='/accounts/usersignin')
def checkout(request):

    if request.method == "POST":
        show_date_str = request.POST.get('showdate')
        seats = request.POST.get('seats')
        show_id = request.POST.get('showid')

        if not show_date_str or not seats or not show_id:
            return render(request,"checkout.html",{'error': "Missing booking info"})

        show_obj = get_object_or_404(show, id=show_id)
        show_date_obj = datetime.strptime(show_date_str, '%Y-%m-%d').date()

        num_seats = len(seats.split(","))
        total_amount = show_obj.price * num_seats

        booking_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        booking.objects.create(
            booking_code=booking_code,
            user=request.user,
            show=show_obj,
            seat_num=seats,
            num_seats=num_seats,
            total=total_amount,
            show_date=show_date_obj,
            booked_date=datetime.now(timezone.utc)
        )

        # ✅ CRITICAL FIX: Redirect to My Bookings
        return HttpResponseRedirect('/mybookings?ack=success')

    return render(request,"checkout.html")


# ---------------- My Bookings ----------------
@user_passes_test(user_login_required, login_url='/accounts/usersignin')
def userbookings(request):

    bookings = booking.objects.filter(
        user=request.user
    ).select_related('show','show__movie').order_by('-booked_date')

    return render(request,"bookings.html", {
        'data': bookings
    })


# ---------------- Cancel Booking ----------------
@user_passes_test(user_login_required, login_url='/accounts/usersignin')
def cancelbooking(request,id):

    book_obj = get_object_or_404(booking, id=id)
    book_obj.delete()

    return HttpResponseRedirect('/mybookings?ack=cancelled')
