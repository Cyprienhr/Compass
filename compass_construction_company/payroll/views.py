from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from .models import PayrollRecord
from employees.models import Employee, Category
from datetime import date
from notifications.models import Notification


@login_required
def payroll_list(request: HttpRequest) -> HttpResponse:
    if request.user.is_system_admin() or request.user.is_superuser:
        qs = PayrollRecord.objects.select_related('employee', 'category').all()
    elif request.user.is_chief_engineer():
        qs = PayrollRecord.objects.select_related('employee', 'category').filter(employee__site__chief_engineer=request.user)
    else:
        qs = PayrollRecord.objects.select_related('employee', 'category').filter(employee__site__site_engineers=request.user)
    return render(request, 'payroll/payroll_list.html', {'records': qs})


@login_required
def payroll_create(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        employee_id = int(request.POST.get('employee'))
        category_id = int(request.POST.get('category'))
        amount = request.POST.get('amount')
        deducted = request.POST.get('deducted') or 0
        bonus = request.POST.get('bonus') or 0
        rec_date = request.POST.get('date') or date.today()
        signature = (request.POST.get('signature') == 'true')
        payment_status = request.POST.get('payment_status', 'PENDING')
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
            messages.error(request, 'Not authorized to create payroll for this employee')
            return redirect('payroll_list')
        category = get_object_or_404(Category, id=category_id)
        record = PayrollRecord.objects.create(
            employee=employee,
            category=category,
            amount=amount,
            deducted=deducted,
            bonus=bonus,
            date=rec_date,
            signature=signature,
            payment_status=payment_status,
        )
        # Notify chief engineer if available
        chief = getattr(employee.site, 'chief_engineer', None)
        if chief:
            Notification.objects.create(
                recipient=chief,
                title='New Payroll Record',
                message=f'Payroll prepared for {employee.full_name} on {rec_date}.'
            )
        messages.success(request, f'Payroll record created for {record.employee.full_name}')
        return redirect('payroll_list')
    if request.user.is_system_admin() or request.user.is_superuser:
        employees = Employee.objects.all()
    elif request.user.is_chief_engineer():
        employees = Employee.objects.filter(site__chief_engineer=request.user)
    else:
        employees = Employee.objects.filter(site__site_engineers=request.user)
    categories = Category.objects.all()
    return render(request, 'payroll/payroll_form.html', {'employees': employees, 'categories': categories})


@login_required
def payroll_edit(request: HttpRequest, record_id: int) -> HttpResponse:
    record = get_object_or_404(PayrollRecord, id=record_id)
    # Permission: Admins, site chief, or assigned site engineers only
    user = request.user
    allowed = False
    if user.is_system_admin() or user.is_superuser or user.is_chief_engineer():
        if user.is_chief_engineer():
            allowed = (record.employee.site.chief_engineer_id == user.id)
        else:
            allowed = True
    else:
        allowed = record.employee.site.site_engineers.filter(id=user.id).exists()
    if not allowed:
        return redirect('payroll_list')
    
    if request.method == 'POST':
        record.employee_id = int(request.POST.get('employee'))
        record.category_id = int(request.POST.get('category'))
        record.amount = request.POST.get('amount')
        record.deducted = request.POST.get('deducted') or 0
        record.bonus = request.POST.get('bonus') or 0
        record.date = request.POST.get('date') or date.today()
        record.signature = (request.POST.get('signature') == 'true')
        record.payment_status = request.POST.get('payment_status', 'PENDING')
        record.save()
        messages.success(request, 'Payroll record updated successfully')
        return redirect('payroll_list')
    
    # Narrow employees by accessible sites
    if user.is_system_admin() or user.is_superuser:
        employees = Employee.objects.all()
    elif user.is_chief_engineer():
        employees = Employee.objects.filter(site__chief_engineer=user)
    else:
        employees = Employee.objects.filter(site__site_engineers=user)
    categories = Category.objects.all()
    return render(request, 'payroll/payroll_form.html', {
        'record': record,
        'employees': employees,
        'categories': categories,
    })


@login_required
def payroll_delete(request: HttpRequest, record_id: int) -> HttpResponse:
    record = get_object_or_404(PayrollRecord, id=record_id)
    # Permission: Admins, site chief, or assigned site engineers only
    user = request.user
    allowed = False
    if user.is_system_admin() or user.is_superuser or user.is_chief_engineer():
        if user.is_chief_engineer():
            allowed = (record.employee.site.chief_engineer_id == user.id)
        else:
            allowed = True
    else:
        allowed = record.employee.site.site_engineers.filter(id=user.id).exists()
    if not allowed:
        return redirect('payroll_list')
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Payroll record deleted successfully')
        return redirect('payroll_list')
    return redirect('payroll_list')


@login_required
def payroll_update_status(request: HttpRequest, record_id: int) -> HttpResponse:
    if not (request.user.is_system_admin() or request.user.is_chief_engineer() or request.user.is_superuser):
        return redirect('dashboard')
    record = get_object_or_404(PayrollRecord, id=record_id)
    if request.method == 'POST':
        status = request.POST.get('payment_status')
        if status in dict(PayrollRecord._meta.get_field('payment_status').choices):
            record.payment_status = status
            record.save()
            messages.success(request, 'Payment status updated')
    return redirect('payroll_list')


@login_required
def payroll_sign(request: HttpRequest, record_id: int) -> HttpResponse:
    # Allow Site Engineers (on that site), Chief Engineer of the site, and Admins to toggle signature
    record = get_object_or_404(PayrollRecord, id=record_id)
    user = request.user
    allowed = False
    if user.is_system_admin() or user.is_superuser or user.is_chief_engineer():
        allowed = True
    else:
        # Site Engineer assigned to the employee's site
        allowed = record.employee.site.site_engineers.filter(id=user.id).exists()
    if not allowed:
        return redirect('payroll_list')
    record.signature = not record.signature
    record.save()
    messages.success(request, 'Payroll signature updated')
    return redirect('payroll_list')
