from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.db import IntegrityError

from .models import User
from sites.models import ConstructionSite


def index(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'index.html')


@csrf_protect
def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Invalid credentials or inactive account.')
    else:
        # Ensure any prior messages don't leak onto the login screen
        from django.contrib import messages as _messages
        list(_messages.get_messages(request))
    return render(request, 'users/login.html')


def logout_view(request: HttpRequest) -> HttpResponse:
    # Proactively clear any queued messages before logout to avoid leakage
    list(messages.get_messages(request))
    logout(request)
    return redirect('login')


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    user: User = request.user  # type: ignore
    if user.is_system_admin():
        template = 'users/dashboards/admin_dashboard.html'
    elif user.is_chief_engineer():
        template = 'users/dashboards/chief_dashboard.html'
    else:
        template = 'users/dashboards/site_dashboard.html'
    return render(request, template)


# System Admin - user management views
@login_required
def user_list(request: HttpRequest) -> HttpResponse:
    # Admin & Chief: all Site Engineers; Admin also sees other roles
    if not request.user.is_authenticated:
        return redirect('dashboard')
    if request.user.is_superuser or request.user.is_system_admin():
        users = User.objects.all().order_by('id')
    elif hasattr(request.user, 'is_chief_engineer') and request.user.is_chief_engineer():
        users = User.objects.filter(role=User.Roles.SITE_ENGINEER).order_by('id')
    else:
        return redirect('dashboard')
    return render(request, 'users/admin/user_list.html', {'users': users})


@login_required
def user_create(request: HttpRequest) -> HttpResponse:
    # System Admin can create any role; Chief Engineer can only create Site Engineers
    is_admin = request.user.is_superuser or request.user.is_system_admin()
    is_chief = request.user.is_authenticated and hasattr(request.user, 'is_chief_engineer') and request.user.is_chief_engineer()
    if not (is_admin or is_chief):
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role') or User.Roles.SITE_ENGINEER
        if is_chief:
            role = User.Roles.SITE_ENGINEER
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        national_id = request.POST.get('national_id', '')
        is_active = request.POST.get('status', 'active') == 'active'
        # Validate unique username
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists. Please choose another.')
            roles = User.Roles.choices if is_admin else [(User.Roles.SITE_ENGINEER, 'Site Engineer')]
            available_sites = ConstructionSite.objects.all() if is_admin else ConstructionSite.objects.filter(chief_engineer=request.user)
            return render(request, 'users/admin/user_form.html', {'roles': roles, 'sites': available_sites})
        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                role=role,
                first_name=first_name,
                last_name=last_name,
                email=email,
            )
        except IntegrityError:
            messages.error(request, 'Username already exists. Please choose another.')
            roles = User.Roles.choices if is_admin else [(User.Roles.SITE_ENGINEER, 'Site Engineer')]
            available_sites = ConstructionSite.objects.all() if is_admin else ConstructionSite.objects.filter(chief_engineer=request.user)
            return render(request, 'users/admin/user_form.html', {'roles': roles, 'sites': available_sites})
        user.phone = phone
        user.national_id = national_id
        user.is_active = is_active
        user.save()
        # Optional site assignment if created by Chief/Admin
        if role == User.Roles.SITE_ENGINEER:
            site_ids = request.POST.getlist('sites')
            if site_ids:
                # Chiefs can only assign their own sites
                site_qs = ConstructionSite.objects.all()
                if is_chief:
                    site_qs = site_qs.filter(chief_engineer=request.user)
                assigned = site_qs.filter(id__in=site_ids)
                user.assigned_sites.set(assigned)
        messages.success(request, 'User created successfully')
        return redirect('user_list') if is_admin else redirect('dashboard')
    roles = User.Roles.choices if is_admin else [(User.Roles.SITE_ENGINEER, 'Site Engineer')]
    # Provide sites for Chiefs to assign upon creation
    available_sites = None
    if is_admin:
        available_sites = ConstructionSite.objects.all()
    elif is_chief:
        available_sites = ConstructionSite.objects.filter(chief_engineer=request.user)
    return render(request, 'users/admin/user_form.html', {'roles': roles, 'sites': available_sites})


@login_required
def user_edit(request: HttpRequest, user_id: int) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('dashboard')
    target = get_object_or_404(User, id=user_id)
    is_admin = request.user.is_superuser or request.user.is_system_admin()
    is_chief = hasattr(request.user, 'is_chief_engineer') and request.user.is_chief_engineer()
    if not (is_admin or (is_chief and target.role == User.Roles.SITE_ENGINEER and target.assigned_sites.filter(chief_engineer=request.user).exists())):
        return redirect('dashboard')
    if request.method == 'POST':
        target.first_name = request.POST.get('first_name', target.first_name)
        target.last_name = request.POST.get('last_name', target.last_name)
        target.email = request.POST.get('email', target.email)
        target.phone = request.POST.get('phone', target.phone)
        role = request.POST.get('role')
        if is_admin:
            if role in dict(User.Roles.choices):
                target.role = role
        else:
            # Chief can only set Site Engineer role
            target.role = User.Roles.SITE_ENGINEER
        password = request.POST.get('password')
        if password:
            target.set_password(password)
        target.national_id = request.POST.get('national_id', target.national_id)
        target.is_active = request.POST.get('status', 'active') == 'active'
        target.save()
        messages.success(request, 'User updated successfully')
        return redirect('user_list')
    roles = User.Roles.choices if is_admin else [(User.Roles.SITE_ENGINEER, 'Site Engineer')]
    return render(request, 'users/admin/user_form.html', {'user_obj': target, 'roles': roles})


@login_required
def user_activate(request: HttpRequest, user_id: int) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('dashboard')
    target = get_object_or_404(User, id=user_id)
    is_admin = request.user.is_superuser or request.user.is_system_admin()
    is_chief = hasattr(request.user, 'is_chief_engineer') and request.user.is_chief_engineer()
    if not (is_admin or (is_chief and target.role == User.Roles.SITE_ENGINEER and target.assigned_sites.filter(chief_engineer=request.user).exists())):
        return redirect('dashboard')
    target.is_active = True
    target.save()
    messages.success(request, 'User activated')
    return redirect('user_list')


@login_required
def user_deactivate(request: HttpRequest, user_id: int) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('dashboard')
    target = get_object_or_404(User, id=user_id)
    is_admin = request.user.is_superuser or request.user.is_system_admin()
    is_chief = hasattr(request.user, 'is_chief_engineer') and request.user.is_chief_engineer()
    if not (is_admin or (is_chief and target.role == User.Roles.SITE_ENGINEER and target.assigned_sites.filter(chief_engineer=request.user).exists())):
        return redirect('dashboard')
    target.is_active = False
    target.save()
    messages.success(request, 'User deactivated')
    return redirect('user_list')


@login_required
def user_delete(request: HttpRequest, user_id: int) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('dashboard')
    target = get_object_or_404(User, id=user_id)
    is_admin = request.user.is_superuser or request.user.is_system_admin()
    is_chief = hasattr(request.user, 'is_chief_engineer') and request.user.is_chief_engineer()
    if not (is_admin or (is_chief and target.role == User.Roles.SITE_ENGINEER and target.assigned_sites.filter(chief_engineer=request.user).exists())):
        return redirect('dashboard')
    target.delete()
    messages.success(request, 'User deleted')
    return redirect('user_list')


@login_required
def account_profile(request: HttpRequest) -> HttpResponse:
    user: User = request.user  # type: ignore
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', user.phone)
        user.national_id = request.POST.get('national_id', user.national_id)
        user.save()
        messages.success(request, 'Profile updated')
        return redirect('account_profile')
    return render(request, 'users/account/profile.html')


@login_required
def account_overview(request: HttpRequest) -> HttpResponse:
    return render(request, 'users/account/overview.html')


@login_required
def account_password(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        current = request.POST.get('current_password')
        new1 = request.POST.get('new_password')
        new2 = request.POST.get('confirm_password')
        if not request.user.check_password(current):
            messages.error(request, 'Current password is incorrect')
        elif new1 != new2:
            messages.error(request, 'Passwords do not match')
        else:
            request.user.set_password(new1)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed')
            return redirect('account_password')
    return render(request, 'users/account/password.html')
