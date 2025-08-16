from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from .models import Notification
from django.contrib import messages


@login_required
def notification_list(request: HttpRequest) -> HttpResponse:
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    return render(request, 'notifications/notification_list.html', {'notifications': notifications})


@login_required
def notification_mark_read(request: HttpRequest, notif_id: int) -> HttpResponse:
    notif = get_object_or_404(Notification, id=notif_id, recipient=request.user)
    notif.is_read = True
    notif.save()
    messages.success(request, 'Notification marked as read')
    return redirect('notification_list')
