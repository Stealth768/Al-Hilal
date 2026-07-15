from django.shortcuts import render
from django.http import JsonResponse
from .models import IslamicMilestone
from .astronomy_engine import calculate_moon_visibility, find_gregorian_date_for_islamic, build_hijri_calendar_for_year
import datetime
import json


def home_view(request):
    return render(request, 'core/index.html')


def index(request):
    return render(request, 'hilal/index.html')


def dashboard(request):
    return render(request, 'hilal/dashboard.html')

def prayer_times(request):
    return render(request, 'hilal/prayer.html')

from django.shortcuts import render
from .models import IslamicMilestone
import datetime

def _resolve_visibility_based_date(selected_year, event_key, candidate_date):
    if event_key == 'EID_FITR' and selected_year == 2026:
        for offset in range(0, 7):
            try_date = candidate_date + datetime.timedelta(days=offset)
            vis = calculate_moon_visibility(try_date)
            if vis and vis.get('is_visible'):
                return try_date + datetime.timedelta(days=1)
    return candidate_date


def build_milestones_for_year(selected_year):
    # Hardcode geographical tracking points for Delhi
    delhi_lat = "28.6139"
    delhi_lon = "77.2090"
    zoom_level = "12"
    elevation = "324.0"
    map_type = "2"

    # 1. FIXED DICTIONARY: This now acts as the absolute source of truth for historical/known dates
    if selected_year == 2025:
        dates = {'EID_FITR': '2025.03.30', 'EID_ADHA': '2025.06.06', 'MUHARRAM': '2025.06.26'}
    elif selected_year == 2026:
        dates = {'EID_FITR': '2026.03.20', 'EID_ADHA': '2026.05.28', 'MUHARRAM': '2026.06.16'} # Fixed to 28th
    elif selected_year == 2027:
        dates = {'EID_FITR': '2027.03.09', 'EID_ADHA': '2027.05.16', 'MUHARRAM': '2027.06.06'}
    else:
        dates = {'EID_FITR': f'{selected_year}.03.20', 'EID_ADHA': f'{selected_year}.05.27', 'MUHARRAM': f'{selected_year}.06.16'}

    events_display = {
        'EID_FITR': ('Eid al-Fitr', 10, 1),
        'EID_ADHA': ('Bakra Eid (Eid al-Adha)', 12, 10),
        'MUHARRAM': ('Muharram (Islamic New Year)', 1, 1)
    }

    milestones_data = []
    from .models import IslamicMilestone as IM

    for event_key, cfg in events_display.items():
        label, isl_month, isl_day = cfg

        
        manual_date = dates.get(event_key)
        
        if manual_date:
            date_iso = manual_date.replace('.', '-')
            source = 'manual'
            db_entry = IM.objects.filter(year=selected_year, event_key=event_key).first()
            if db_entry:
                is_visible = db_entry.is_visible_in_delhi
                grade = db_entry.visibility_grade or 'D'
                moon_age = db_entry.moon_age_at_sunset
                illumination = db_entry.illumination_percentage
                lag = db_entry.lag_time_minutes
            else:
                is_visible = event_key in ['EID_FITR', 'EID_ADHA']
                grade = 'A' if event_key == 'EID_ADHA' else ('C' if event_key == 'EID_FITR' else 'D')
                moon_age, illumination, lag = None, None, None
        
        
        else:
            db_entry = IM.objects.filter(year=selected_year, event_key=event_key).first()
            if db_entry and db_entry.expected_gregorian_date:
                date_iso = db_entry.expected_gregorian_date.isoformat()
                source = 'observed'
                is_visible = db_entry.is_visible_in_delhi
                grade = db_entry.visibility_grade or 'D'
                moon_age = db_entry.moon_age_at_sunset
                illumination = db_entry.illumination_percentage
                lag = db_entry.lag_time_minutes
            else:
                try:
                    event_date = find_gregorian_date_for_islamic(selected_year, isl_month, isl_day)
                except Exception:
                    event_date = None

                if event_date is None:
                    date_iso = f"{selected_year}-03-20"
                    source = 'fallback'
                else:
                    date_iso = event_date.isoformat()
                    source = 'calculated'

                is_visible = event_key in ['EID_FITR', 'EID_ADHA']
                grade = 'A' if event_key == 'EID_ADHA' else ('C' if event_key == 'EID_FITR' else 'D')
                moon_age, illumination, lag = None, None, None

        
        if moon_age is None:
            try:
                current_date_obj = datetime.date.fromisoformat(date_iso)
                resolved_date_obj = _resolve_visibility_based_date(selected_year, event_key, current_date_obj)
                if resolved_date_obj != current_date_obj:
                    date_iso = resolved_date_obj.isoformat()

                vis = calculate_moon_visibility(date_iso)
            except Exception:
                vis = None

            if vis:
                is_visible = vis.get('is_visible', False)
                grade = vis.get('visibility_grade', 'D')
                moon_age = vis.get('moon_age_hours')
                illumination = vis.get('illumination_pct')
                lag = vis.get('lag_time_minutes')
            else:
                is_visible = False
                grade = 'D'

        
        url_date_format = date_iso.replace('-', '.')
        moon_url = f"https://mooncalc.org/#/28.6139,77.2090,12/2026.05.28/now/324.0/2"
        sun_url = f"https://suncalc.org/#/28.6139,77.2090,12/2026.05.28/now/324.0/2"

        milestones_data.append({
            'name': label,
            'date': date_iso,
            'is_visible': bool(is_visible),
            'grade': grade,
            'mooncalc_url': moon_url,
            'suncalc_url': sun_url,
            'moon_age_hours': moon_age,
            'illumination_pct': illumination,
            'lag_time_minutes': lag,
            'source': source,
        })

    return milestones_data


def hilal(request):
    # Capture what year the user selected (Defaults to 2026 if they just arrived)
    selected_year = int(request.GET.get('year', 2026))

    # Build milestones for the selected year
    milestones_data = build_milestones_for_year(selected_year)

    context = {
        'selected_year': selected_year,
        'milestones': milestones_data,
        'milestones_json': json.dumps(milestones_data),
        'available_years': [2025, 2026, 2027],
    }
    return render(request, 'hilal/hilal.html', context)


def about(request):
    return render(request, 'hilal/about.html')


def calender(request):
    # Allow calendar to receive a year parameter and return server-side milestones
    selected_year = int(request.GET.get('year', 2026))
    milestones_data = build_milestones_for_year(selected_year)
    hijri_calendar = build_hijri_calendar_for_year(selected_year)
    context = {
        'selected_year': selected_year,
        'milestones': milestones_data,
        'milestones_json': json.dumps(milestones_data),
        'hijri_calendar_json': json.dumps(hijri_calendar),
    }
    return render(request, 'hilal/calender.html', context)


def milestones_api(request):
    # Simple GET JSON API to retrieve milestones for a given year
    try:
        year = int(request.GET.get('year', datetime.datetime.utcnow().year))
    except Exception:
        year = datetime.datetime.utcnow().year
    data = build_milestones_for_year(year)
    return JsonResponse({'year': year, 'milestones': data})

