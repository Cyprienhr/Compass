from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from .models import ConstructionSite
from users.models import User


@login_required
def site_list(request: HttpRequest) -> HttpResponse:
    if request.user.is_system_admin() or request.user.is_superuser or request.user.is_chief_engineer():
        qs = ConstructionSite.objects.select_related('chief_engineer').prefetch_related('site_engineers').all()
    else:
        qs = ConstructionSite.objects.select_related('chief_engineer').prefetch_related('site_engineers').filter(site_engineers=request.user)
    return render(request, 'sites/site_list.html', {'sites': qs})


@login_required
def site_create(request: HttpRequest) -> HttpResponse:
    if not (request.user.is_system_admin() or request.user.is_chief_engineer() or request.user.is_superuser):
        return redirect('dashboard')
    if request.method == 'POST':
        name = request.POST.get('name')
        location = request.POST.get('location', '')
        description = request.POST.get('description', '')
        chief_id = request.POST.get('chief_engineer')
        chief = User.objects.filter(id=chief_id).first() if chief_id else None
        site = ConstructionSite.objects.create(
            name=name,
            location=location,
            description=description,
            chief_engineer=chief,
        )
        messages.success(request, 'Site registered successfully')
        return redirect('site_list')
    chiefs = User.objects.filter(role=User.Roles.CHIEF_ENGINEER)
    return render(request, 'sites/site_form.html', {'chiefs': chiefs})


@login_required
def site_assign(request: HttpRequest, site_id: int) -> HttpResponse:
    site = get_object_or_404(ConstructionSite, id=site_id)
    if not (request.user.is_system_admin() or request.user.is_chief_engineer() or request.user.is_superuser):
        return redirect('dashboard')
    if request.method == 'POST':
        engineer_ids = request.POST.getlist('engineers')
        engineers = User.objects.filter(id__in=engineer_ids, role=User.Roles.SITE_ENGINEER)
        site.site_engineers.set(engineers)
        site.save()
        messages.success(request, 'Engineers assigned')
        return redirect('site_list')
    engineers = User.objects.filter(role=User.Roles.SITE_ENGINEER)
    return render(request, 'sites/site_assign.html', {'site': site, 'engineers': engineers})


@login_required
def site_edit(request: HttpRequest, site_id: int) -> HttpResponse:
    site = get_object_or_404(ConstructionSite, id=site_id)
    # Chief can edit only own sites; Admin can edit all
    if not (request.user.is_system_admin() or request.user.is_superuser or (request.user.is_chief_engineer() and site.chief_engineer_id == request.user.id)):
        return redirect('site_list')
    if request.method == 'POST':
        site.name = request.POST.get('name', site.name)
        site.location = request.POST.get('location', site.location)
        site.description = request.POST.get('description', site.description)
        chief_id = request.POST.get('chief_engineer')
        if chief_id:
            chief = User.objects.filter(id=chief_id, role=User.Roles.CHIEF_ENGINEER).first()
            site.chief_engineer = chief
        site.is_active = request.POST.get('status', 'active') == 'active'
        site.save()
        messages.success(request, 'Site updated')
        return redirect('site_list')
    chiefs = User.objects.filter(role=User.Roles.CHIEF_ENGINEER)
    return render(request, 'sites/site_form.html', {'chiefs': chiefs, 'site': site})


@login_required
def site_delete(request: HttpRequest, site_id: int) -> HttpResponse:
    site = get_object_or_404(ConstructionSite, id=site_id)
    if not (request.user.is_system_admin() or request.user.is_superuser or (request.user.is_chief_engineer() and site.chief_engineer_id == request.user.id)):
        return redirect('site_list')
    if request.method == 'POST':
        site.delete()
        messages.success(request, 'Site deleted')
        return redirect('site_list')
    # Fallback: redirect without deleting
    return redirect('site_list')

# Create your views here.
