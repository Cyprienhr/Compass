from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from .models import AttendanceRecord
from employees.models import Employee, Category
from sites.models import ConstructionSite
from datetime import date
# Notification import removed - only payroll notifications are needed
from django.db.models import Sum, Count


@login_required
def attendance_list(request: HttpRequest) -> HttpResponse:
    if request.user.is_system_admin() or request.user.is_superuser:
        qs = AttendanceRecord.objects.select_related('employee', 'category').all()
    elif request.user.is_chief_engineer():
        # Chief engineers only see attendance records they created themselves
        qs = AttendanceRecord.objects.select_related('employee', 'category').filter(created_by=request.user)
    else:
        # Site engineers only see attendance from sites they're assigned to
        qs = AttendanceRecord.objects.select_related('employee', 'category').filter(employee__site__site_engineers=request.user)
    return render(request, 'attendance/attendance_list.html', {'records': qs})


@login_required
def attendance_summary(request: HttpRequest) -> HttpResponse:
    """Show attendance summary grouped by period type"""
    if request.user.is_system_admin() or request.user.is_superuser:
        qs = AttendanceRecord.objects.select_related('employee', 'category').all()
    elif request.user.is_chief_engineer():
        # Chief engineers only see attendance records they created themselves
        qs = AttendanceRecord.objects.select_related('employee', 'category').filter(created_by=request.user)
    else:
        # Site engineers only see attendance from sites they're assigned to
        qs = AttendanceRecord.objects.select_related('employee', 'category').filter(employee__site__site_engineers=request.user)
    
    # Group by period type
    summary = {}
    for period_type in ['DAILY', 'WEEKLY', 'BIWEEKLY', 'MONTHLY']:
        period_records = qs.filter(period_type=period_type)
        summary[period_type] = {
            'records': period_records,
            'total_count': period_records.count(),
            'total_amount': period_records.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'total_worked': period_records.aggregate(Sum('periods_worked'))['periods_worked__sum'] or 0
        }
    
    return render(request, 'attendance/attendance_summary.html', {'summary': summary})


@login_required
def attendance_create(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        # Common attendance fields
        category_id = int(request.POST.get('category'))
        amount = int(request.POST.get('amount') or 0)
        period_type = request.POST.get('period_type')
        periods_worked = int(request.POST.get('periods_worked') or 1)
        deducted = request.POST.get('deducted') or 0
        bonus = request.POST.get('bonus') or 0
        rec_date = request.POST.get('date') or date.today()
        signature = (request.POST.get('signature') == 'true')

        user = request.user
        new_employee_flag = request.POST.get('new_employee') in ['true', 'on', '1']

        if new_employee_flag:
            # Creating a new employee inline
            full_name = (request.POST.get('new_full_name') or '').strip()
            national_id = (request.POST.get('new_national_id') or '').strip()
            contact = (request.POST.get('new_contact') or '').strip()
            site_id = request.POST.get('new_site')

            if not full_name or not national_id or not site_id:
                messages.error(request, 'Please provide full name, national ID and site for the new employee.')
                return redirect('attendance_create')

            # Permission based on selected site
            site = get_object_or_404(ConstructionSite, id=int(site_id))
            allowed = False
            if user.is_system_admin() or user.is_superuser:
                allowed = True
            elif user.is_chief_engineer():
                allowed = (site.chief_engineer_id == user.id)
            else:
                allowed = site.site_engineers.filter(id=user.id).exists()
            if not allowed:
                messages.error(request, 'Not authorized to add employees for this site')
                return redirect('attendance_list')

            # Create the employee
            employee = Employee.objects.create(
                full_name=full_name,
                national_id=national_id,
                contact=contact,
                site=site,
                category_id=category_id,
                created_by=user,
            )
        else:
            # Using existing employee
            employee_id = int(request.POST.get('employee'))
            employee = get_object_or_404(Employee, id=employee_id)
            # Permission: Admins, site chief, or assigned site engineers only
            allowed = False
            if user.is_system_admin() or user.is_superuser or user.is_chief_engineer():
                # Chiefs can record for their sites only
                if user.is_chief_engineer():
                    allowed = (employee.site.chief_engineer_id == user.id)
                else:
                    allowed = True
            else:
                allowed = employee.site.site_engineers.filter(id=user.id).exists()
            if not allowed:
                messages.error(request, 'Not authorized to record attendance for this employee')
                return redirect('attendance_list')

        category = get_object_or_404(Category, id=category_id)
        AttendanceRecord.objects.create(
            employee=employee,
            category=category,
            amount=amount,
            period_type=period_type,
            periods_worked=periods_worked,
            deducted=deducted,
            bonus=bonus,
            date=rec_date,
            signature=signature,
            created_by=user,
        )
        # Removed chief engineer notification - only payroll notifications are needed
        messages.success(request, 'Attendance recorded successfully')
        return redirect('attendance_list')

    # Narrow employees and sites by accessible permissions
    if request.user.is_system_admin() or request.user.is_superuser:
        employees = Employee.objects.all()
        sites = ConstructionSite.objects.all()
    elif request.user.is_chief_engineer():
        employees = Employee.objects.filter(site__chief_engineer=request.user)
        sites = ConstructionSite.objects.filter(chief_engineer=request.user)
    else:
        employees = Employee.objects.filter(site__site_engineers=request.user)
        sites = ConstructionSite.objects.filter(site_engineers=request.user)
    categories = Category.objects.all()
    return render(request, 'attendance/attendance_form.html', {
        'employees': employees,
        'categories': categories,
        'sites': sites,
        'period_choices': AttendanceRecord.PERIOD_CHOICES,
    })


@login_required
def attendance_edit(request: HttpRequest, record_id: int) -> HttpResponse:
    record = get_object_or_404(AttendanceRecord, id=record_id)
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
        return redirect('attendance_list')
    
    if request.method == 'POST':
        # record.employee_id = int(request.POST.get('employee'))
        # record.category_id = int(request.POST.get('category'))
        # record.amount = request.POST.get('amount')
        # record.period_type = request.POST.get('period_type')
        # record.periods_worked = int(request.POST.get('periods_worked'))
        # record.deducted = request.POST.get('deducted') or 0
        # record.bonus = request.POST.get('bonus') or 0
        # record.date = request.POST.get('date') or date.today()
        # record.signature = (request.POST.get('signature') == 'true')
        # record.save()
        # messages.success(request, 'Attendance record updated successfully')
        # return redirect('attendance_list')
        employee_id = request.POST.get("employee")
        category_id = request.POST.get("category")
        periods_worked = request.POST.get("periods_worked")

        if not employee_id or not category_id or not periods_worked:
            messages.error(request, "Please fill in all required fields.")
            return redirect("attendance_edit", record_id=record.id)

        record.employee_id = int(employee_id)
        record.category_id = int(category_id)
        record.periods_worked = int(periods_worked)
        record.period_type = request.POST.get("period_type")
        record.amount = float(request.POST.get("amount") or 0)
        record.deducted = float(request.POST.get("deducted") or 0)
        record.bonus = float(request.POST.get("bonus") or 0)
        record.date = request.POST.get("date") or None
        record.signature = request.POST.get("signature") == "true"

        record.save()
        messages.success(request, "Attendance updated successfully!")
        return redirect("attendance_list")

    
    # Narrow employees by accessible sites
    if user.is_system_admin() or user.is_superuser:
        employees = Employee.objects.all()
    elif user.is_chief_engineer():
        employees = Employee.objects.filter(site__chief_engineer=user)
    else:
        employees = Employee.objects.filter(site__site_engineers=user)
    categories = Category.objects.all()
    return render(request, 'attendance/attendance_form.html', {
        'record': record,
        'employees': employees,
        'categories': categories,
        'period_choices': AttendanceRecord.PERIOD_CHOICES,
    })


@login_required
def attendance_delete(request: HttpRequest, record_id: int) -> HttpResponse:
    record = get_object_or_404(AttendanceRecord, id=record_id)
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
        return redirect('attendance_list')
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Attendance record deleted successfully')
        return redirect('attendance_list')
    return redirect('attendance_list')


@login_required
def get_latest_attendance(request: HttpRequest, employee_id: int) -> JsonResponse:
    """Get the latest attendance record for an employee to auto-fill payroll form"""
    try:
        # Get the latest attendance record for the employee
        latest_attendance = AttendanceRecord.objects.filter(
            employee_id=employee_id
        ).order_by('-date', '-created_at').first()
        
        if not latest_attendance:
            return JsonResponse({'error': 'No attendance records found for this employee'}, status=404)
        
        # Return the data needed for payroll
        data = {
            'amount': float(latest_attendance.amount),
            'deducted': float(latest_attendance.deducted),
            'bonus': float(latest_attendance.bonus),
            'total_amount': float(latest_attendance.total_amount),
            'period_type': latest_attendance.period_type,
            'periods_worked': latest_attendance.periods_worked,
            'date': latest_attendance.date.strftime('%Y-%m-%d'),
            'category_id': latest_attendance.category.id if latest_attendance.category else None,
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
