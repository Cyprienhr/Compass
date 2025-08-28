from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from .models import Employee, Category
from sites.models import ConstructionSite
from django.http import JsonResponse


@login_required
def employee_list(request: HttpRequest) -> HttpResponse:
    if request.user.is_system_admin() or request.user.is_superuser:
        qs = Employee.objects.select_related('category', 'site').all()
    elif request.user.is_chief_engineer():
        # Chief engineers only see employees they created themselves
        qs = Employee.objects.select_related('category', 'site').filter(created_by=request.user)
    else:
        # Site engineers only see employees from sites they're assigned to
        qs = Employee.objects.select_related('category', 'site').filter(site__site_engineers=request.user)
    return render(request, 'employees/employee_list.html', {'employees': qs})


@login_required
def employee_create(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        national_id = request.POST.get('national_id')
        contact = request.POST.get('contact', '')
        site_id = request.POST.get('site')
        category_id = request.POST.get('category')
        site = get_object_or_404(ConstructionSite, id=site_id)
        category = get_object_or_404(Category, id=category_id)
        Employee.objects.create(
            full_name=full_name,
            national_id=national_id,
            contact=contact,
            site=site,
            category=category,
            created_by=request.user,
        )
        messages.success(request, 'Employee registered')
        return redirect('employee_list')
    # Allowed sites depend on role
    if request.user.is_system_admin() or request.user.is_superuser:
        sites = ConstructionSite.objects.all()
    elif request.user.is_chief_engineer():
        sites = ConstructionSite.objects.filter(chief_engineer=request.user)
    else:
        sites = ConstructionSite.objects.filter(site_engineers=request.user)
    categories = Category.objects.all()
    return render(request, 'employees/employee_form.html', {'sites': sites, 'categories': categories})


@login_required
def employee_toggle_active(request: HttpRequest, employee_id: int) -> HttpResponse:
    employee = get_object_or_404(Employee, id=employee_id)
    # Permission: Admins, site chief, or assigned site engineers only
    user = request.user
    allowed = False
    if user.is_system_admin() or user.is_superuser or user.is_chief_engineer():
        if user.is_chief_engineer():
            allowed = (employee.site.chief_engineer_id == user.id)
        else:
            allowed = True
    else:
        allowed = employee.site.site_engineers.filter(id=user.id).exists()
    if not allowed:
        messages.error(request, 'Not authorized to update this employee')
        return redirect('employee_list')
    employee.is_active = not employee.is_active
    employee.save()
    messages.success(request, 'Employee status updated')
    return redirect('employee_list')


@login_required
def employee_edit(request: HttpRequest, employee_id: int) -> HttpResponse:
    employee = get_object_or_404(Employee, id=employee_id)
    # Permission: Admins, site chief, or assigned site engineers only
    user = request.user
    allowed = False
    if user.is_system_admin() or user.is_superuser or user.is_chief_engineer():
        if user.is_chief_engineer():
            allowed = (employee.site.chief_engineer_id == user.id)
        else:
            allowed = True
    else:
        allowed = employee.site.site_engineers.filter(id=user.id).exists()
    if not allowed:
        return redirect('employee_list')
    
    if request.method == 'POST':
        employee.full_name = request.POST.get('full_name', employee.full_name)
        employee.national_id = request.POST.get('national_id', employee.national_id)
        employee.contact = request.POST.get('contact', employee.contact)
        site_id = request.POST.get('site')
        category_id = request.POST.get('category')
        if site_id:
            site = get_object_or_404(ConstructionSite, id=site_id)
            employee.site = site
        if category_id:
            category = get_object_or_404(Category, id=category_id)
            employee.category = category
        employee.save()
        messages.success(request, 'Employee updated successfully')
        return redirect('employee_list')
    
    # Allowed sites depend on role
    if user.is_system_admin() or user.is_superuser:
        sites = ConstructionSite.objects.all()
    elif user.is_chief_engineer():
        sites = ConstructionSite.objects.filter(chief_engineer=user)
    else:
        sites = ConstructionSite.objects.filter(site_engineers=user)
    categories = Category.objects.all()
    return render(request, 'employees/employee_form.html', {'employee': employee, 'sites': sites, 'categories': categories})


@login_required
def employee_delete(request: HttpRequest, employee_id: int) -> HttpResponse:
    employee = get_object_or_404(Employee, id=employee_id)
    # Permission: Admins, site chief, or assigned site engineers only
    user = request.user
    allowed = False
    if user.is_system_admin() or user.is_superuser or user.is_chief_engineer():
        if user.is_chief_engineer():
            allowed = (employee.site.chief_engineer_id == user.id)
        else:
            allowed = True
    else:
        allowed = employee.site.site_engineers.filter(id=user.id).exists()
    if not allowed:
        return redirect('employee_list')
    
    if request.method == 'POST':
        employee.delete()
        messages.success(request, 'Employee deleted successfully')
        return redirect('employee_list')
    return redirect('employee_list')


@login_required
def employee_json(request: HttpRequest, employee_id: int) -> HttpResponse:
    e = get_object_or_404(Employee, id=employee_id)
    data = {
        'id': e.id,
        'full_name': e.full_name,
        'national_id': e.national_id,
        'contact': e.contact,
        'category': e.category.name if e.category else None,
        'site': e.site.name if e.site else None,
        'is_active': e.is_active,
    }
    return JsonResponse(data)


@login_required
def category_list(request: HttpRequest) -> HttpResponse:
    categories = Category.objects.all()
    return render(request, 'employees/category_list.html', {'categories': categories})


@login_required
def category_create(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        Category.objects.create(name=name, description=description)
        messages.success(request, 'Category created')
        return redirect('category_list')
    return render(request, 'employees/category_form.html')
