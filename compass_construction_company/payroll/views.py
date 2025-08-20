from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from .models import PayrollRecord
from employees.models import Employee
from datetime import date
from attendance.models import AttendanceRecord


@login_required
def payroll_list(request: HttpRequest) -> HttpResponse:
    # Scope attendance by permissions
    if request.user.is_system_admin() or request.user.is_superuser:
        attendance_qs = AttendanceRecord.objects.select_related('employee', 'employee__site')
    elif request.user.is_chief_engineer():
        attendance_qs = AttendanceRecord.objects.select_related('employee', 'employee__site').filter(employee__site__chief_engineer=request.user)
    else:
        attendance_qs = AttendanceRecord.objects.select_related('employee', 'employee__site').filter(employee__site__site_engineers=request.user)

    # Determine selected date; default to today
    selected_date_param = request.GET.get('date')
    selected_date = None
    if selected_date_param:
        try:
            y, m, d = [int(x) for x in selected_date_param.split('-')]
            selected_date = date(y, m, d)
        except Exception:
            selected_date = None
    if not selected_date:
        selected_date = date.today()
    selected_date_str = selected_date.isoformat()

    # Aggregation for the selected date
    day_records = attendance_qs.filter(date=selected_date)
    by_employee = {}
    for rec in day_records:
        emp_id = rec.employee_id
        if emp_id not in by_employee:
            by_employee[emp_id] = {
                'employee': rec.employee,
                'total_amount': 0.0,
                'total_deducted': 0.0,
                'total_bonus': 0.0,
            }
        by_employee[emp_id]['total_amount'] += float(rec.total_amount)
        by_employee[emp_id]['total_deducted'] += float(rec.deducted or 0)
        by_employee[emp_id]['total_bonus'] += float(rec.bonus or 0)

    date_rows = []
    for emp_id, info in by_employee.items():
        pr = PayrollRecord.objects.filter(employee_id=emp_id, date=selected_date).select_related('employee', 'category').first()
        date_rows.append({
            'employee': info['employee'],
            'amount': info['total_amount'],
            'deducted': info['total_deducted'],
            'bonus': info['total_bonus'],
            'date': selected_date,
            'record': pr,
        })

    ctx = {'date_rows': date_rows, 'selected_date': selected_date_str}
    return render(request, 'payroll/payroll_list.html', ctx)


@login_required
def payroll_upsert_for_date(request: HttpRequest) -> HttpResponse:
    if request.method != 'POST':
        return redirect('payroll_list')

    try:
        employee_id = int(request.POST.get('employee'))
        selected_date_str = request.POST.get('date')
        status = request.POST.get('payment_status', 'PENDING')
        signature_flag = (request.POST.get('signature') == 'true')
        y, m, d = [int(x) for x in selected_date_str.split('-')]
        selected_date = date(y, m, d)
    except Exception:
        messages.error(request, 'Invalid data provided')
        return redirect('payroll_list')

    employee = get_object_or_404(Employee, id=employee_id)
    # Permission
    user = request.user
    if user.is_system_admin() or user.is_superuser:
        allowed = True
    elif user.is_chief_engineer():
        allowed = (employee.site.chief_engineer_id == user.id)
    else:
        allowed = employee.site.site_engineers.filter(id=user.id).exists()
    if not allowed:
        messages.error(request, 'Not authorized for this employee')
        return redirect('payroll_list')

    att_qs = AttendanceRecord.objects.filter(employee_id=employee_id, date=selected_date)
    if not att_qs.exists():
        messages.error(request, 'No attendance found for that date')
        return redirect(f"/payroll/?date={selected_date}")
    total_amount = sum(float(a.total_amount) for a in att_qs)

    record, created = PayrollRecord.objects.get_or_create(
        employee=employee,
        date=selected_date,
        defaults={
            'category': employee.category,
            'amount': total_amount,
            'deducted': 0,
            'bonus': 0,
            'signature': signature_flag,
            'payment_status': status,
        }
    )
    if not created:
        record.category = employee.category
        record.amount = total_amount
        record.deducted = record.deducted or 0
        record.bonus = record.bonus or 0
        record.payment_status = status
        if signature_flag:
            record.signature = True
        record.save()

    messages.success(request, 'Payroll updated for the selected date')
    return redirect(f"/payroll/?date={selected_date}")


@login_required
def payroll_bulk_upsert_for_date(request: HttpRequest) -> HttpResponse:
    if request.method != 'POST':
        return redirect('payroll_list')

    selected_date_str = request.POST.get('date')
    try:
        y, m, d = [int(x) for x in selected_date_str.split('-')]
        selected_date = date(y, m, d)
    except Exception:
        messages.error(request, 'Invalid date')
        return redirect('payroll_list')

    employee_ids = request.POST.getlist('employee_ids')
    user = request.user
    updated_count = 0

    for eid_str in employee_ids:
        try:
            eid = int(eid_str)
        except Exception:
            continue
        employee = Employee.objects.filter(id=eid).select_related('site', 'category').first()
        if not employee:
            continue
        # Permission check per employee
        if user.is_system_admin() or user.is_superuser:
            allowed = True
        elif user.is_chief_engineer():
            allowed = (employee.site.chief_engineer_id == user.id)
        else:
            allowed = employee.site.site_engineers.filter(id=user.id).exists()
        if not allowed:
            continue

        status = request.POST.get(f'payment_status_{eid}', 'PENDING')
        signature_flag = (request.POST.get(f'signature_{eid}') == 'true') or (request.POST.get(f'signature_{eid}') == 'on')

        att_qs = AttendanceRecord.objects.filter(employee_id=eid, date=selected_date)
        if not att_qs.exists():
            continue
        total_amount = sum(float(a.total_amount) for a in att_qs)

        record, created = PayrollRecord.objects.get_or_create(
            employee=employee,
            date=selected_date,
            defaults={
                'category': employee.category,
                'amount': total_amount,
                'deducted': 0,
                'bonus': 0,
                'signature': signature_flag,
                'payment_status': status,
            }
        )
        if not created:
            record.category = employee.category
            record.amount = total_amount
            record.deducted = record.deducted or 0
            record.bonus = record.bonus or 0
            record.payment_status = status
            if signature_flag:
                record.signature = True
            record.save()
        updated_count += 1

    messages.success(request, f'Saved payroll for {updated_count} employee(s) on {selected_date}')
    return redirect(f"/payroll/?date={selected_date}")
