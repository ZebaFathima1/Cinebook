from . import views
from django.urls import path

urlpatterns = [
    path('', views.home, name='home'),

    path('movie/<int:id>/', views.movie_detail, name='movie_detail'),

    path('showtime/', views.show_select, name='show_select'),

    path('seats/<int:show_id>/', views.seat_view, name='seat_view'),

    path('bookedseats/', views.bookedseats, name='bookedseats'),

    path('checkout/', views.checkout, name='checkout'),

    path('mybookings/', views.userbookings, name='mybookings'),

    path('cancel/<int:id>/', views.cancelbooking, name='cancelbooking'),
]
