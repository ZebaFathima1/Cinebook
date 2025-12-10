from multiprocessing import context
from django.shortcuts import HttpResponseRedirect, render
from django.http import HttpResponse
from django.forms import formset_factory,modelformset_factory
from staff.models import *
from datetime import datetime, date,time,timezone
from django.views.generic.list import ListView
from accounts.views import is_user, user_login_required
from django.contrib.auth.decorators import (user_passes_test)
from .models import *

from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string


def home(request):
    movies = film.objects.filter().values_list('id','movie_name','url', named=True)
    banners = banner.objects.filter().select_related().values_list('movie__id','movie__movie_name','url', named=True)
    return render(request,"index.html", context={'films': movies,'banners':banners})

def movie_detail(request,id):
    context = {}
    context['film'] = film.objects.get(id = id) 
    context ['showtimes'] = show.objects.filter(movie=id,end_date__gte=date.today()).all().values_list('id','showtime',named=True)
    return render(request,"movie_detail.html",context)

@user_passes_test(user_login_required, login_url='/accounts/usersignin')
def show_select(request):
    # Initialize variables
    res_dict = {}
    date = None
    shows = []
    
    # If no date provided, set default to tomorrow
    from datetime import date as dt_date, timedelta
    if request.method == "GET" and 'date' in request.GET and request.GET['date']:
        date = request.GET['date']
    else:
        # Default to tomorrow if no date provided
        date = (dt_date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Convert date string to date object for proper comparison
    try:
        from datetime import datetime
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    except:
        date_obj = dt_date.today() + timedelta(days=1)
        date = date_obj.strftime('%Y-%m-%d')
    
    # Get shows for the selected date
    # Show must have: start_date <= selected_date <= end_date
    # Also filter out shows with null dates or null movies
    shows = show.objects.filter(
        end_date__gte=date_obj, 
        start_date__lte=date_obj,
        movie__isnull=False
    ).exclude(
        start_date__isnull=True,
        end_date__isnull=True
    ).select_related('movie').order_by('movie_id','showtime').values_list('id','price','showtime','movie','movie__url','movie__movie_name',named=True)
    
    # Grouping shows rows by movie and appending showitmes in a list
    for s in shows:
        # legend of fields: showid 0, price 1, showtime 2, movieid 3, movieurl 4, moviename 5,
        movie_name = s[5] if s[5] else "Unknown Movie"
        if(movie_name not in res_dict.keys()): 
            #movie doesn't exist in dict
            res_dict[movie_name]={'url':s[4] if s[4] else '', 'price':s[1], 'showtimes':{s[0]:s[2]}, 'movieid':s[3]}
        else: 
            #movie already exists
            res_dict[movie_name]['showtimes'][s[0]]=s[2]            
        
    # Add debug info for staff users
    debug_info = None
    if request.user.is_staff:
        from staff.models import show as ShowModel
        all_shows = ShowModel.objects.all().select_related('movie')[:10]
        debug_info = []
        for s in all_shows:
            debug_info.append({
                'movie': s.movie.movie_name if s.movie else 'No Movie',
                'start_date': s.start_date,
                'end_date': s.end_date,
                'showtime': s.showtime,
                'in_range': (s.start_date and s.end_date and s.start_date <= date_obj <= s.end_date) if s.start_date and s.end_date else False
            })
    
    return render(request,"show_selection.html",context = {'films':res_dict,'date':date,'shows':shows,'debug_info':debug_info})


def bookedseats(request):
    """
    AJAX seat booking info retrival view funciton
    """
    if request.method == 'GET':
           show_id = request.GET['show_id']
           show_date = request.GET['show_date']
           seats = booking.objects.filter(show=show_id,show_date=show_date).values('seat_num')
           booked = ""
           for s in seats:
            booked+=s['seat_num']+","
           return HttpResponse(booked[:-1])
    else:
           return HttpResponse("Request method is not a GET")


def sendEmail(request,message):
    """
    Function to send Email
    """
    template ="Hello "+request.user.username+'\n'+message

    user_email = request.user.email

    email = EmailMessage(
        'Tickets Confirmation Email',
        template,
        settings.EMAIL_HOST_USER,
        [user_email],
    )

    email.fail_silently = False
    email.send()
    return True


def checkout(request):
    context = {}
    if (request.method == "POST"):
        try:
            show_date_str = request.POST.get('showdate', '')
            seats = request.POST.get('seats', '')
            show_id = request.POST.get('showid', '')
            
            # Validate inputs
            if not show_date_str or not seats or not show_id:
                context['error'] = "Missing required information. Please try again."
                return render(request,"checkout.html",context)
            
            # Validate that seats were selected
            if not seats.strip():
                context['error'] = "Please select at least one seat to book."
                return render(request,"checkout.html",context)
            
            # Convert show_date string to date object
            from datetime import datetime as dt
            try:
                show_date_obj = dt.strptime(show_date_str, '%Y-%m-%d').date()
            except:
                context['error'] = "Invalid date format. Please try again."
                return render(request,"checkout.html",context)
            
            # Get Show id
            try:
                showinfo = show.objects.get(id=show_id)
            except show.DoesNotExist:
                context['error'] = "Show not found. Please try again."
                return render(request,"checkout.html",context)
            
            num_seats = len(seats.split(","))
            total = showinfo.price * num_seats
            
            # Generate unique booking code
            import random
            import string
            booking_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            # Create booking
            booking_obj = booking.objects.create(
                booking_code=booking_code,
                user=request.user,
                show=showinfo,
                show_date=show_date_obj,  # Use date object, not string
                booked_date=datetime.now(timezone.utc),
                seat_num=seats,
                num_seats=num_seats,
                total=total
            )
            
            # Verify booking was saved and appears in user's bookings
            saved_booking = booking.objects.get(id=booking_obj.id)
            user_bookings_count = booking.objects.filter(user=request.user).count()
            print(f"Booking saved successfully! ID: {saved_booking.id}, Code: {saved_booking.booking_code}")
            print(f"Total bookings for user: {user_bookings_count}")
            
            # Verify it's in My Bookings
            context['in_my_bookings'] = True
            context['total_user_bookings'] = user_bookings_count
            
            # Verify booking was saved and appears in user's bookings
            saved_booking = booking.objects.get(id=booking_obj.id)
            user_bookings_count = booking.objects.filter(user=request.user).count()
            print(f"Booking saved successfully! ID: {saved_booking.id}, Code: {saved_booking.booking_code}")
            print(f"Total bookings for user: {user_bookings_count}")
            
            # Verify it's in My Bookings
            context['in_my_bookings'] = True
            context['total_user_bookings'] = user_bookings_count
            
            context["film"] = film.objects.get(movie_name = showinfo.movie) 
            context['sdate'] = show_date_str  # Keep string for display
            context['seats'] = seats
            context['show'] = showinfo
            context['booking_code'] = booking_code
            context['num_seats'] = num_seats
            context['total'] = total
            context['booking_id'] = booking_obj.id
            context['booking_saved'] = True  # Flag to show success
            
            message="\nYour tickets are successsfully booked. Here are the details. \nBooking Code: {}\nThe movie is {}. \nThe show is on {}. \nThe show starts at {}. \nYour seat numbers are {}. \nTotal Amount: ${}\n\nThank you,\nCinebook".format(booking_code, context["film"], show_date_str, showinfo.showtime, seats, total)
            try:
                sendEmail(request,message)
            except:
                pass  # Continue even if email fails
                
        except Exception as e:
            import traceback
            print(f"Error in checkout: {e}")
            print(traceback.format_exc())
            context['error'] = f"Error processing booking: {str(e)}. Please try again or contact support."
            return render(request,"checkout.html",context)
        
    return render(request,"checkout.html",context)

@user_passes_test(user_login_required, login_url='/accounts/usersignin')
def userbookings(request):
    msg=""
    if(request.method == "GET" and len(request.GET)!=0):
        msg = request.GET.get('ack', '')

    # Get all bookings for the current user, ordered by most recent first
    booking_table = booking.objects.filter(user=request.user).select_related('show', 'show__movie').order_by('-booked_date').values_list('id','show_date','booked_date','show__movie__movie_name','show__movie__url','show__showtime','total','seat_num','booking_code','num_seats',named=True)
    
    # Debug: Print booking count
    print(f"User: {request.user.username}")
    print(f"Total bookings found: {booking_table.count()}")
    
    context = {
        'data':booking_table,
        'msg':msg,
        'booking_count': booking_table.count()
    }
    return render(request,"bookings.html",context)

@user_passes_test(user_login_required, login_url='/accounts/usersignin')
def cancelbooking(request,id):
    bobj =  booking.objects.get(id=id)
    message="\nYour tickets are succcessfully Cancelled. Here are the details.\nYour show info{}\nYour Show date {}\nYour seats\n\nThank you,\nCinebook".format(bobj.show,bobj.show_date,bobj.seat_num)
    ack = "Your tickets {} for {} are cancelled successfully".format(bobj.seat_num,bobj.show)
    bobj.delete()
    sendEmail(request,message)
    
    return HttpResponseRedirect("/mybookings?ack="+ack)

