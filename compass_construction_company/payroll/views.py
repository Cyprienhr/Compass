from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from .models import PayrollRecord
from employees.models import Employee
from datetime import date, datetime
from attendance.models import AttendanceRecord
from notifications.models import Notification
import re


@login_required
def payroll_list(request: HttpRequest) -> HttpResponse:
    # Scope attendance by permissions (initial default)
    if request.user.is_system_admin() or request.user.is_superuser:
        attendance_qs = AttendanceRecord.objects.select_related('employee', 'employee__site').all()
    elif request.user.is_chief_engineer():
        # Chief engineers see their own (self-recorded) attendance by default
        attendance_qs = AttendanceRecord.objects.select_related('employee', 'employee__site').filter(created_by=request.user)
    else:
        # Site engineers only see payroll from sites they're assigned to
        attendance_qs = AttendanceRecord.objects.select_related('employee', 'employee__site').filter(employee__site__site_engineers=request.user)

    # Determine selected date; default to today
    selected_date_param = request.GET.get('date')
    selected_date = None
    
    def parse_date(date_string):
        """Parse date from various formats"""
        if not date_string:
            return None
        try:
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        except ValueError:
            pass
        try:
            return datetime.strptime(date_string, '%b. %d, %Y').date()
        except ValueError:
            pass
        try:
            return datetime.strptime(date_string, '%b %d, %Y').date()
        except ValueError:
            pass
        try:
            return datetime.strptime(date_string, '%d %b %Y').date()
        except ValueError:
            pass
        date_pattern = r'(\d{4})-(\d{1,2})-(\d{1,2})'
        match = re.search(date_pattern, date_string)
        if match:
            try:
                y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                return date(y, m, d)
            except ValueError:
                pass
        return None
    
    if selected_date_param:
        selected_date = parse_date(selected_date_param)
    if not selected_date:
        selected_date = date.today()
    selected_date_str = selected_date.isoformat()
    
    # Check if this is a chief engineer accessing from a notification
    is_from_notification = False
    if request.user.is_chief_engineer() and selected_date_param:
        notification_exists = Notification.objects.filter(
            recipient=request.user,
            notification_type='PAYROLL_SUBMISSION',
            related_date=selected_date
        ).exists()
        if notification_exists:
            is_from_notification = True
            # Do not change queryset here; banner only. Site view controls queryset below.

    # Chief engineer view toggles (own vs site engineers, optional site filter)
    chief_sites = []
    view_type = 'own'
    selected_site_id = None
    requires_site = False
    if request.user.is_chief_engineer():
        from sites.models import ConstructionSite
        chief_sites = ConstructionSite.objects.filter(chief_engineer=request.user).order_by('name')
        view_type = request.GET.get('view', 'own')  # 'own' or 'site'
        selected_site_id = request.GET.get('site_id')
        if view_type == 'own' and not is_from_notification:
            attendance_qs = AttendanceRecord.objects.select_related('employee', 'employee__site').filter(created_by=request.user)
        elif view_type == 'site':
            if selected_site_id:
                attendance_qs = AttendanceRecord.objects.select_related('employee', 'employee__site').filter(employee__site_id=selected_site_id)
            else:
                # Do not mix sites - require explicit site selection
                attendance_qs = AttendanceRecord.objects.none()
                requires_site = True

    # Aggregation for the selected date
    day_records = attendance_qs.filter(date=selected_date)
    by_employee = {}
    site_engineer_set = {}
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
        for eng in rec.employee.site.site_engineers.all():
            site_engineer_set[eng.id] = eng

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

    day_total = sum(r['amount'] for r in date_rows) if date_rows else 0.0
    site_engineers = list(site_engineer_set.values())

    is_chief_review = request.user.is_chief_engineer() and selected_date_param

    ctx = {
        'date_rows': date_rows,
        'selected_date': selected_date_str,
        'day_total': day_total,
        'site_engineers': site_engineers,
        'is_chief_review': is_chief_review,
        'is_from_notification': is_from_notification,
        'chief_sites': chief_sites,
        'view_type': view_type,
        'selected_site_id': selected_site_id,
        'requires_site': requires_site,
    }
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


@login_required
def payroll_submit_to_chief(request: HttpRequest) -> HttpResponse:
    """Submit payroll list to chief engineer for review"""
    if request.method != 'POST':
        return redirect('payroll_list')
    
    selected_date_str = request.POST.get('date')
    try:
        y, m, d = [int(x) for x in selected_date_str.split('-')]
        selected_date = date(y, m, d)
    except Exception:
        messages.error(request, 'Invalid date')
        return redirect('payroll_list')
    
    user = request.user
    
    # Get employees for this date to determine sites
    if user.is_system_admin() or user.is_superuser:
        attendance_qs = AttendanceRecord.objects.select_related('employee', 'employee__site').filter(date=selected_date)
    elif user.is_chief_engineer():
        attendance_qs = AttendanceRecord.objects.select_related('employee', 'employee__site').filter(
            date=selected_date, employee__site__chief_engineer=user
        )
    else:
        attendance_qs = AttendanceRecord.objects.select_related('employee', 'employee__site').filter(
            date=selected_date, employee__site__site_engineers=user
        )
    
    if not attendance_qs.exists():
        messages.error(request, 'No attendance records found for this date')
        return redirect(f"/payroll/?date={selected_date}")
    
    # Group by site and notify chief engineers
    sites_notified = set()
    for rec in attendance_qs:
        site = rec.employee.site
        if site.id not in sites_notified and site.chief_engineer:
            sites_notified.add(site.id)
            
            # Create notification for chief engineer
            Notification.objects.create(
                recipient=site.chief_engineer,
                sender=user,
                title=f'Payroll Submission - {selected_date}',
                message=f'Payroll list submitted by {user.get_full_name() or user.username} for {site.name} on {selected_date}. Total employees: {attendance_qs.filter(employee__site=site).count()}.',
                notification_type='PAYROLL_SUBMISSION',
                related_date=selected_date,
                related_site=site.name,
            )
    
    if sites_notified:
        messages.success(request, f'Payroll submitted to {len(sites_notified)} chief engineer(s) for review')
    else:
        messages.warning(request, 'No chief engineers found for the sites')
    
    return redirect(f"/payroll/?date={selected_date}")


@login_required
def payroll_reply_from_chief(request: HttpRequest) -> HttpResponse:
    """Chief engineer replies to payroll submission"""
    if request.method != 'POST':
        return redirect('notification_list')
    
    notification_id = request.POST.get('notification_id')
    reply_message = request.POST.get('reply_message', '').strip()
    
    if not reply_message:
        messages.error(request, 'Reply message is required')
        return redirect('notification_list')
    
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user,
            notification_type='PAYROLL_SUBMISSION'
        )
    except Notification.DoesNotExist:
        messages.error(request, 'Notification not found')
        return redirect('notification_list')
    
    # Create reply notification for the original sender
    Notification.objects.create(
        recipient=notification.sender,
        sender=request.user,
        title=f'Payroll Reply - {notification.related_date}',
        message=f'Chief Engineer {request.user.get_full_name() or request.user.username} replied to your payroll submission for {notification.related_site} on {notification.related_date}: "{reply_message}"',
        notification_type='PAYROLL_REPLY',
        related_date=notification.related_date,
        related_site=notification.related_site,
    )
    
    messages.success(request, 'Reply sent successfully')
    return redirect('notification_list')
