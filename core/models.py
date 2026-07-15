from django.db import models

class IslamicMilestone(models.Model):
    EVENT_CHOICES = [
        ('MUHARRAM', '1st of Muharram (Islamic New Year)'),
        ('RAMADAN', '1st of Ramadan (Month of Fasting)'),
        ('EID_FITR', 'Eid al-Fitr (1st of Shawwal)'),
        ('EID_ADHA', 'Eid al-Adha (10th of Dhul Hijjah)'),
        ('MILAD', 'Milad un-Nabi (12th of Rabi al-Awwal)'),
    ]

    year = models.IntegerField()
    event_key = models.CharField(max_length=20, choices=EVENT_CHOICES)
    expected_gregorian_date = models.DateField()
    
    # Astronomical parameters calculated for Delhi coordinates
    moon_age_at_sunset = models.FloatField(help_text="Age in hours since conjunction")
    illumination_percentage = models.FloatField(help_text="Percentage illuminated")
    lag_time_minutes = models.FloatField(help_text="Minutes between sunset and moonset")
    
    # Sighting Verdict
    is_visible_in_delhi = models.BooleanField(default=False)
    visibility_grade = models.CharField(max_length=1, choices=[('A','A'), ('B','B'), ('C','C'), ('D','D')])

    def get_event_key_display(self):
        return dict(self.EVENT_CHOICES).get(self.event_key, self.event_key)

    def __str__(self):
        return f"{self.get_event_key_display()} ({self.year}) - Delhi"